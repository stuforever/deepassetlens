# -*- coding: utf-8 -*-
"""v4批6 6.C：PG 版问题笔记本存储——vendor SQLiteSessionStore 笔记 12 方法面 1:1。

源语义=vendor services/session/sqlite_store.py notebook_entries/notebook_categories/
notebook_entry_categories 三表 + _serialize_notebook_entry 行形状（E-62⑥）：
- 表=sishu_notebook_entries（payload 全文档+typed 热列）/sishu_notebook_categories/
  sishu_notebook_entry_categories（批2 建族，本批扩列）。
- 会话标题：sqlite 期由 LEFT JOIN sessions 取；PG 期列名 session_title 冗余存储
  （6.2 迁移自 sqlite join 快照；新 upsert 写空串或 sishu_sessions 现值——批8 会话域
  迁移后改实连）。
- find_notebook_entry 的 turn_id 严格匹配（None→''legacy 桶）——防跨 turn 泄答案
  （vendor #487/#677 语义），1:1 保留。
访问名 get_sqlite_session_store() 与 vendor 同名——路由体零改。
"""
import json
import time
from typing import Any

from sqlalchemy import text

from app.services.sishu.compat.context import get_current_user_or_none
from app.services.sishu_data.pg import engine


def _scope_user() -> str:
    cu = get_current_user_or_none()
    if cu is None:
        return "local-admin"
    return getattr(getattr(cu, "scope", None), "user_id", "") or "local-admin"


def _serialize_entry(row: dict) -> dict[str, Any]:
    # 兼容双形状：PG payload=已序列化（options/user_answer_images 现值）；sqlite 裸行=JSON 串。
    options = row.get("options")
    if not isinstance(options, dict):
        raw = row.get("options_json")
        if isinstance(raw, str):
            try:
                options = json.loads(raw)
            except Exception:
                options = {}
        else:
            options = raw if isinstance(raw, dict) else {}
    options = options if isinstance(options, dict) else {}
    images = row.get("user_answer_images")
    if not isinstance(images, list):
        raw = row.get("user_answer_images_json")
        if isinstance(raw, str):
            try:
                loaded = json.loads(raw)
            except Exception:
                loaded = []
        else:
            loaded = raw if isinstance(raw, list) else []
        images = [r for r in loaded if isinstance(r, dict)] if isinstance(loaded, list) else []
    images = [r for r in images if isinstance(r, dict)]
    return {
        "id": int(row["id"]),
        "session_id": row.get("session_id") or "",
        "session_title": row.get("session_title") or "",
        "turn_id": row.get("turn_id") or "",
        "question_id": row.get("question_id") or "",
        "question": row.get("question") or "",
        "question_type": row.get("question_type") or "",
        "options": options,
        "correct_answer": row.get("correct_answer") or "",
        "explanation": row.get("explanation") or "",
        "difficulty": row.get("difficulty") or "",
        "user_answer": row.get("user_answer") or "",
        "user_answer_images": images,
        "is_correct": bool(row.get("is_correct")),
        "bookmarked": bool(row.get("bookmarked")),
        "followup_session_id": row.get("followup_session_id") or "",
        "ai_judgment": row.get("ai_judgment") or "",
        "created_at": float(row.get("created_at") or 0),
        "updated_at": float(row.get("updated_at") or 0),
    }


_ENTRY_COLS = ("session_id", "session_title", "turn_id", "question_id", "question",
               "question_type", "options_json", "correct_answer", "explanation",
               "difficulty", "user_answer", "user_answer_images_json", "is_correct",
               "bookmarked", "followup_session_id", "ai_judgment")


class PgNotebookSessionStore:
    """PG 单轨笔记本 store——vendor SQLiteSessionStore 笔记方法面 1:1。"""

    # ---------- entries ----------
    async def upsert_notebook_entries(self, session_id: str, items: list[dict[str, Any]]) -> int:
        """批量 upsert（UNIQUE(session_id, turn_id, question_id) 冲突即更新）。"""
        n = 0
        for item in items:
            doc = dict(item)
            doc.setdefault("session_id", session_id)
            doc["session_title"] = doc.get("session_title") or self._lookup_session_title(session_id)
            doc.setdefault("turn_id", "")
            doc.setdefault("question_id", "")
            doc.setdefault("question", "")
            doc.setdefault("question_type", "")
            doc.setdefault("options", {})
            doc.setdefault("correct_answer", "")
            doc.setdefault("explanation", "")
            doc.setdefault("difficulty", "")
            doc.setdefault("user_answer", "")
            doc.setdefault("user_answer_images", [])
            doc.setdefault("is_correct", False)
            doc.setdefault("bookmarked", False)
            doc.setdefault("followup_session_id", "")
            doc.setdefault("ai_judgment", "")
            now = time.time()
            payload = json.dumps(doc, ensure_ascii=False)
            with engine.begin() as c:
                row = c.execute(text("""
                    SELECT id FROM sishu_notebook_entries
                    WHERE user_id=:u AND session_id=:s
                      AND COALESCE(turn_id,'')=:t AND COALESCE(question_id,'')=:q
                    LIMIT 1"""),
                    {"u": _scope_user(), "s": session_id,
                     "t": doc.get("turn_id") or "", "q": doc.get("question_id") or ""}).fetchone()
                if row:
                    c.execute(text("""
                        UPDATE sishu_notebook_entries SET payload=CAST(:p AS JSONB),
                          session_title=:st, is_correct=:ic, bookmarked=:bm,
                          updated_at_epoch=:ua WHERE id=:id"""),
                        {"p": payload, "st": doc.get("session_title") or "",
                         "ic": bool(doc.get("is_correct")), "bm": bool(doc.get("bookmarked")),
                         "ua": now, "id": row[0]})
                else:
                    c.execute(text("""
                        INSERT INTO sishu_notebook_entries
                          (user_id, session_id, session_title, turn_id, question_id,
                           is_correct, bookmarked, created_at_epoch, updated_at_epoch, payload)
                        VALUES (:u, :s, :st, :t, :q, :ic, :bm, :ca, :ua, CAST(:p AS JSONB))"""),
                        {"u": _scope_user(), "s": session_id,
                         "st": doc.get("session_title") or "",
                         "t": doc.get("turn_id") or "", "q": doc.get("question_id") or "",
                         "ic": bool(doc.get("is_correct")), "bm": bool(doc.get("bookmarked")),
                         "ca": now, "ua": now, "p": payload})
            n += 1
        return n

    def _lookup_session_title(self, session_id: str) -> str:
        """会话标题现值（sishu_sessions 批8 迁移完成前多为空串——语义同 vendor 缺表）。"""
        try:
            with engine.connect() as c:
                row = c.execute(text(
                    "SELECT title FROM sishu_sessions WHERE session_id=:s LIMIT 1"),
                    {"s": session_id}).fetchone()
            return (row[0] or "") if row else ""
        except Exception:
            return ""

    async def list_notebook_entries(
        self,
        category_id: int | None = None,
        bookmarked: bool | None = None,
        is_correct: bool | None = None,
        limit: int = 50,
        offset: int = 0,
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        conds = ["n.user_id=:u"]
        params: dict[str, Any] = {"u": _scope_user()}
        join = ""
        if category_id is not None:
            join = " INNER JOIN sishu_notebook_entry_categories ec ON ec.entry_id = n.id"
            conds.append("ec.category_id = :cat")
            params["cat"] = category_id
        if bookmarked is not None:
            conds.append("n.bookmarked = :bm")
            params["bm"] = bool(bookmarked)
        if is_correct is not None:
            conds.append("n.is_correct = :ic")
            params["ic"] = bool(is_correct)
        if session_id is not None:
            conds.append("n.session_id = :sid")
            params["sid"] = session_id
        where = " WHERE " + " AND ".join(conds)
        with engine.connect() as c:
            total = int(c.execute(text(
                f"SELECT COUNT(*) FROM sishu_notebook_entries n{join}{where}"), params).scalar() or 0)
            rows = c.execute(text(
                f"SELECT n.payload, n.id, n.session_title FROM sishu_notebook_entries n{join}{where} "
                "ORDER BY n.created_at_epoch DESC LIMIT :lim OFFSET :off"),
                {**params, "lim": limit, "off": offset}).fetchall()
        items = []
        for r in rows:
            d = dict(r[0] or {})
            d["id"] = int(r[1])
            d["session_title"] = r[2] or d.get("session_title") or ""
            items.append(_serialize_entry(d))
        return {"items": items, "total": total}

    async def get_notebook_entry(self, entry_id: int) -> dict[str, Any] | None:
        with engine.connect() as c:
            row = c.execute(text(
                "SELECT payload, id, session_title FROM sishu_notebook_entries "
                "WHERE id=:i AND user_id=:u"),
                {"i": entry_id, "u": _scope_user()}).fetchone()
            if row is None:
                return None
            cats = c.execute(text("""
                SELECT cc.id, cc.name FROM sishu_notebook_categories cc
                INNER JOIN sishu_notebook_entry_categories ec ON ec.category_id = cc.id
                WHERE ec.entry_id = :i ORDER BY cc.name"""),
                {"i": entry_id}).fetchall()
        d = dict(row[0] or {})
        d["id"] = int(row[1])
        d["session_title"] = row[2] or d.get("session_title") or ""
        entry = _serialize_entry(d)
        entry["categories"] = [{"id": int(x[0]), "name": x[1]} for x in cats]
        return entry

    async def find_notebook_entry(
        self, session_id: str, question_id: str, turn_id: str | None = None,
    ) -> dict[str, Any] | None:
        # turn_id 严格匹配（None→''legacy 桶）——跨 turn 泄答案防线（vendor #487/#677）。
        with engine.connect() as c:
            row = c.execute(text("""
                SELECT payload, id, session_title FROM sishu_notebook_entries
                WHERE user_id=:u AND session_id=:s AND COALESCE(turn_id,'')=:t
                  AND COALESCE(question_id,'')=:q LIMIT 1"""),
                {"u": _scope_user(), "s": session_id,
                 "t": turn_id if turn_id is not None else "",
                 "q": question_id}).fetchone()
        if row is None:
            return None
        d = dict(row[0] or {})
        d["id"] = int(row[1])
        d["session_title"] = row[2] or d.get("session_title") or ""
        return _serialize_entry(d)

    async def update_notebook_entry(self, entry_id: int, updates: dict[str, Any]) -> bool:
        allowed = {"bookmarked", "followup_session_id", "user_answer", "is_correct", "ai_judgment"}
        fields = {k: v for k, v in updates.items() if k in allowed}
        if not fields:
            return False
        with engine.begin() as c:
            row = c.execute(text(
                "SELECT payload FROM sishu_notebook_entries WHERE id=:i AND user_id=:u"),
                {"i": entry_id, "u": _scope_user()}).fetchone()
            if row is None:
                return False
            doc = dict(row[0] or {})
            doc.update(fields)
            sets = ["payload=CAST(:p AS JSONB)", "updated_at_epoch=:ua"]
            params: dict[str, Any] = {"p": json.dumps(doc, ensure_ascii=False),
                                      "ua": time.time(), "i": entry_id, "u": _scope_user()}
            if "bookmarked" in fields:
                sets.append("bookmarked=:bm")
                params["bm"] = bool(fields["bookmarked"])
            if "is_correct" in fields:
                sets.append("is_correct=:ic")
                params["ic"] = bool(fields["is_correct"])
            c.execute(text(
                f"UPDATE sishu_notebook_entries SET {', '.join(sets)} WHERE id=:i AND user_id=:u"),
                params)
        return True

    async def delete_notebook_entry(self, entry_id: int) -> bool:
        with engine.begin() as c:
            n = c.execute(text(
                "DELETE FROM sishu_notebook_entries WHERE id=:i AND user_id=:u"),
                {"i": entry_id, "u": _scope_user()}).rowcount
        return n > 0

    # ---------- categories ----------
    async def create_category(self, name: str) -> dict[str, Any]:
        now = time.time()
        with engine.begin() as c:
            cur = c.execute(text(
                "INSERT INTO sishu_notebook_categories (user_id, name, created_at_epoch, payload) "
                "VALUES (:u, :n, :ca, CAST(:p AS JSONB)) RETURNING id"),
                {"u": _scope_user(), "n": name.strip(), "ca": now,
                 "p": json.dumps({"name": name.strip()}, ensure_ascii=False)})
            new_id = int(cur.scalar_one())
        return {"id": new_id, "name": name.strip(), "created_at": now}

    async def list_categories(self) -> list[dict[str, Any]]:
        with engine.connect() as c:
            rows = c.execute(text("""
                SELECT cc.id, cc.name, COALESCE(cc.created_at_epoch, 0),
                       COUNT(ec.entry_id) AS entry_count
                FROM sishu_notebook_categories cc
                LEFT JOIN sishu_notebook_entry_categories ec ON ec.category_id = cc.id
                WHERE cc.user_id = :u
                GROUP BY cc.id, cc.name, cc.created_at_epoch
                ORDER BY cc.name"""),
                {"u": _scope_user()}).fetchall()
        return [{"id": int(r[0]), "name": r[1], "created_at": float(r[2]),
                 "entry_count": int(r[3])} for r in rows]

    async def rename_category(self, category_id: int, name: str) -> bool:
        with engine.begin() as c:
            n = c.execute(text(
                "UPDATE sishu_notebook_categories SET name=:n WHERE id=:i AND user_id=:u"),
                {"n": name.strip(), "i": category_id, "u": _scope_user()}).rowcount
        return n > 0

    async def delete_category(self, category_id: int) -> bool:
        with engine.begin() as c:
            n = c.execute(text(
                "DELETE FROM sishu_notebook_categories WHERE id=:i AND user_id=:u"),
                {"i": category_id, "u": _scope_user()}).rowcount
        return n > 0

    async def add_entry_to_category(self, entry_id: int, category_id: int) -> bool:
        with engine.begin() as c:
            try:
                c.execute(text(
                    "INSERT INTO sishu_notebook_entry_categories (entry_id, category_id) "
                    "VALUES (:e, :c) ON CONFLICT DO NOTHING"),
                    {"e": entry_id, "c": category_id})
            except Exception:
                return False
        return True

    async def remove_entry_from_category(self, entry_id: int, category_id: int) -> bool:
        with engine.begin() as c:
            n = c.execute(text(
                "DELETE FROM sishu_notebook_entry_categories WHERE entry_id=:e AND category_id=:c"),
                {"e": entry_id, "c": category_id}).rowcount
        return n > 0


_instances: dict[int, PgNotebookSessionStore] = {}


def get_sqlite_session_store() -> PgNotebookSessionStore:
    """vendor 同名访问器（路由体零改）——返回 PG 单轨笔记本 store。"""
    key = id(engine)
    if key not in _instances:
        _instances[key] = PgNotebookSessionStore()
    return _instances[key]
