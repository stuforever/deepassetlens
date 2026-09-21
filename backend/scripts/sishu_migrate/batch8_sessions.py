# -*- coding: utf-8 -*-
"""三轨M14(批8) 8.2：会话四表全量迁移（chat_history.db→PG 协议 E v2 幂等+双账+游标）。

源=vendor sqlite（sessions 267/messages 558/turns 291/turn_events 1319083）。
幂等：ON CONFLICT DO NOTHING（PK 复用 vendor id）。
payload 打包：capability/events/attachments/metadata 源列 → JSONB 单文档。
"""
import sys, sqlite3, json
sys.path.insert(0, ".")
import os
os.environ.setdefault("DT_TUTOR_WORKSPACE_ROOT", "data/experts/tutor/workspace")
from sqlalchemy import text
from app.services.sishu.services.path_service import get_path_service
from app.services.sishu_data.pg import engine
from app.services.sishu_data.cursor import append_asset_hashes, sha256_of


def _clean(s):
    return (s or "").replace(chr(0), "")


def main() -> int:
    db_path = get_path_service().get_chat_history_db().resolve()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    DOMAIN = "batch8_sessions"
    src = {t2: conn.execute(f"SELECT COUNT(*) FROM {t2}").fetchone()[0]
           for t2 in ["sessions", "messages", "turns", "turn_events"]}

    n_s = 0
    for r in conn.execute("SELECT id, title, created_at, updated_at FROM sessions"):
        with engine.begin() as c:
            c.execute(text("""
                INSERT INTO sishu_sessions (session_id, user_id, title, created_at, updated_at)
                VALUES (:s, 'local-admin', :t,
                        to_timestamp(GREATEST(:ca, 1)), to_timestamp(GREATEST(:ua, 1)))
                ON CONFLICT (session_id) DO NOTHING"""),
                {"s": r["id"], "t": _clean(r["title"]),
                 "ca": float(r["created_at"] or 0), "ua": float(r["updated_at"] or 0)})
        n_s += 1

    n_m = 0
    batch = []
    for r in conn.execute("SELECT id, session_id, role, content, capability, events_json, attachments_json, metadata_json, created_at, parent_message_id FROM messages ORDER BY id"):
        batch.append(dict(r))
        if len(batch) >= 500:
            with engine.begin() as c:
                for r2 in batch:
                    payload = json.dumps({
                        "capability": _clean(r2["capability"]), "events": _clean(r2["events_json"]),
                        "attachments": _clean(r2["attachments_json"]), "metadata": _clean(r2["metadata_json"]),
                        "parent_message_id": r2["parent_message_id"],
                    }, ensure_ascii=False).replace(chr(0), "")
                    c.execute(text("""
                        INSERT INTO sishu_messages (id, session_id, seq, role, content, payload, created_at)
                        VALUES (:i, :s, :q, :ro, :ct, CAST(:pl AS JSONB), to_timestamp(GREATEST(:ca,1)))
                        ON CONFLICT (id) DO NOTHING"""),
                        {"i": r2["id"], "s": r2["session_id"], "q": r2["id"] % 100000,
                         "ro": r2["role"], "ct": _clean(r2["content"])[:500000],
                         "pl": payload, "ca": float(r2["created_at"] or 0)})
            n_m += len(batch)
            batch = []
    if batch:
        with engine.begin() as c:
            for r2 in batch:
                payload = json.dumps({
                    "capability": _clean(r2["capability"]), "events": _clean(r2["events_json"]),
                    "attachments": _clean(r2["attachments_json"]), "metadata": _clean(r2["metadata_json"]),
                    "parent_message_id": r2["parent_message_id"],
                }, ensure_ascii=False).replace(chr(0), "")
                c.execute(text("""
                    INSERT INTO sishu_messages (id, session_id, seq, role, content, payload, created_at)
                    VALUES (:i, :s, :q, :ro, :ct, CAST(:pl AS JSONB), to_timestamp(GREATEST(:ca,1)))
                    ON CONFLICT (id) DO NOTHING"""),
                    {"i": r2["id"], "s": r2["session_id"], "q": r2["id"] % 100000,
                     "ro": r2["role"], "ct": _clean(r2["content"])[:500000],
                     "pl": payload, "ca": float(r2["created_at"] or 0)})
        n_m += len(batch)

    n_t = 0
    for r in conn.execute("SELECT id, session_id, capability, status, error, created_at, updated_at, finished_at FROM turns"):
        payload = json.dumps({"capability": _clean(r["capability"]), "status": r["status"],
                              "error": _clean(r["error"]), "finished_at": r["finished_at"]}).replace(chr(0), "")
        with engine.begin() as c:
            c.execute(text("""
                INSERT INTO sishu_turns (turn_id, session_id, seq, payload, created_at, updated_at)
                VALUES (:t, :s, :q, CAST(:pl AS JSONB), to_timestamp(GREATEST(:ca,1)), to_timestamp(GREATEST(:ua,1)))
                ON CONFLICT (turn_id) DO NOTHING"""),
                {"t": r["id"], "s": r["session_id"], "q": n_t,
                 "pl": payload, "ca": float(r["created_at"] or 0), "ua": float(r["updated_at"] or 0)})
        n_t += 1

    n_e = 0
    batch = []
    for r in conn.execute("SELECT id, turn_id, seq, type, source, stage, content, metadata_json, created_at FROM turn_events ORDER BY id"):
        batch.append(dict(r))
        if len(batch) >= 2000:
            with engine.begin() as c:
                for r2 in batch:
                    payload = json.dumps({"source": _clean(r2["source"]), "stage": _clean(r2["stage"]),
                                          "content": _clean(r2["content"])[:100000],
                                          "metadata": _clean(r2["metadata_json"])}, ensure_ascii=False).replace(chr(0), "")
                    c.execute(text("""
                        INSERT INTO sishu_turn_events (id, turn_id, seq, event_type, payload, created_at)
                        VALUES (:i, :t, :q, :et, CAST(:pl AS JSONB), to_timestamp(GREATEST(:ca,1)))
                        ON CONFLICT (id) DO NOTHING"""),
                        {"i": r2["id"], "t": r2["turn_id"], "q": r2["seq"] or 0,
                         "et": r2["type"] or "unknown", "pl": payload,
                         "ca": float(r2["created_at"] or 0)})
            n_e += len(batch)
            batch = []
    if batch:
        with engine.begin() as c:
            for r2 in batch:
                payload = json.dumps({"source": _clean(r2["source"]), "stage": _clean(r2["stage"]),
                                      "content": _clean(r2["content"])[:100000],
                                      "metadata": _clean(r2["metadata_json"])}, ensure_ascii=False).replace(chr(0), "")
                c.execute(text("""
                    INSERT INTO sishu_turn_events (id, turn_id, seq, event_type, payload, created_at)
                    VALUES (:i, :t, :q, :et, CAST(:pl AS JSONB), to_timestamp(GREATEST(:ca,1)))
                    ON CONFLICT (id) DO NOTHING"""),
                    {"i": r2["id"], "t": r2["turn_id"], "q": r2["seq"] or 0,
                     "et": r2["type"] or "unknown", "pl": payload,
                     "ca": float(r2["created_at"] or 0)})
        n_e += len(batch)
    conn.close()

    with engine.connect() as c:
        pg = {t2: c.execute(text(f"SELECT count(*) FROM sishu_{t2}")).scalar()
              for t2 in ["sessions", "messages", "turns", "turn_events"]}
    checks = {k: (src[k], pg[k]) for k in src}
    append_asset_hashes(DOMAIN, [{"key": "chat_history.db", "mime": "application/x-sqlite3",
                                  "size": db_path.stat().st_size, "sha256": sha256_of(db_path.read_bytes())}])

    with engine.begin() as c:
        c.execute(text("""
            INSERT INTO sishu_migration_cursor (domain, last_id, rows_done, updated_at)
            VALUES (:d, :l, :r, now())
            ON CONFLICT (domain) DO UPDATE SET last_id=EXCLUDED.last_id, rows_done=EXCLUDED.rows_done, updated_at=now()"""),
            {"d": DOMAIN, "l": f"s={n_s},m={n_m},t={n_t},e={n_e}", "r": n_s + n_m + n_t + n_e})
    ok = all(v[0] == v[1] for v in checks.values())
    print("对账:", checks)
    print(f"OK={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
