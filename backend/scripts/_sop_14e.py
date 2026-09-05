# -*- coding: utf-8 -*-
"""批14-E：加速器扩容 SOP 验收清单五条断言（加速器扩容SOP_20260821.md L97-101）执行脚本。

五条：
①同形查询二连：首跑（直查建数据面）→ try_serve 命中 accelerated=true 且带 data_as_of；
②手动刷新：refresh_accelerator 后 last_refresh_at 更新且目标表结果与源表一致；
③新鲜度标注：命中结果 data_as_of/data_snapshot_at/staleness_note 可见；
④非形状查询：try_serve 返回 None（未拦截，走原路径=正常）；
⑤跨 catalog 显式查询：未被错误拦截（try_serve None）。
"""
import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\gitcangku\deepassetlens\backend")

from app.services import engine_accelerator as ea
from app.services.doris_engine import execute_sql as doris_exec

ok_all = True


def check(idx, name, cond, detail=""):
    global ok_all
    print(f"{'PASS' if cond else 'FAIL'}  ①②③④⑤"[idx - 1] if False else f"[{idx}] {name}: {'PASS' if cond else 'FAIL'} {detail}")
    ok_all &= bool(cond)


accs = ea.list_accelerators(enabled_only=True)
print(f"启用的加速器: {len(accs)} 个")
for a in accs:
    print(f"  - {a['name']} target={a['target_db']}.{a['target_table']} agg_expr={a['agg_expr']} last_refresh_at={a.get('last_refresh_at')}")
if not accs:
    print("无启用加速器——SOP 前提不满足，退出（需要先建加速器）")
    sys.exit(1)

acc = accs[0]
src_tables = acc.get("source_tables") or []
src_table = src_tables[0] if src_tables else "dim_cst_inst_elec_cons"
probe_sql = f"SELECT {acc['agg_expr']} FROM {src_table}" if acc["agg_expr"] else f"SELECT * FROM {acc['target_db']}.{acc['target_table']}"
print(f"探针 SQL: {probe_sql}")

# --- ① 同形查询命中 ---
hit = ea.try_serve(probe_sql)
check(1, "同形查询 accelerated=true 且带 data_as_of",
      hit is not None and hit.get("accelerated") is True and hit.get("data_as_of"),
      f"data_as_of={hit.get('data_as_of') if hit else None}")

# --- ② 手动刷新：last_refresh_at 更新 + 结果与源表一致 ---
before = acc["last_refresh_at"]
time.sleep(1.1)
rf = ea.refresh_accelerator(acc["id"])
after = rf.get("last_refresh_at") or (ea.list_accelerators(enabled_only=True)[0]["last_refresh_at"])
check(2, "手动刷新 last_refresh_at 更新", after is not None and after != before, f"{before} -> {after}")
if hit is not None:
    # 源表直查 vs 目标表直查一致性
    src_res = doris_exec(probe_sql)
    tgt = hit.get("accelerator", {}).get("target_table", "")
    tgt_res = doris_exec(f"SELECT * FROM {acc['target_db']}.{tgt.split('.')[-1]}") if tgt else {"error": "no target"}
    same = (not src_res.get("error")) and (not tgt_res.get("error")) and \
           (src_res.get("rows") and tgt_res["rows"]
            and str(src_res["rows"][0][0]) == str(tgt_res["rows"][0][0]))
    check(2, "刷新后与源表一致", same, f"src={str(src_res.get('rows', [[]])[:1])[:60]} tgt={str(tgt_res.get('rows', [[]])[:1])[:60]}")

# --- ③ 新鲜度标注可见（重新命中） ---
hit2 = ea.try_serve(probe_sql)
meta = hit2.get("accelerator", {}) if hit2 else {}
check(3, "新鲜度标注命中可见",
      hit2 is not None and (hit2.get("data_as_of") or hit2.get("data_snapshot_at")) and "staleness_note" in meta,
      f"data_snapshot_at={hit2.get('data_snapshot_at') if hit2 else None} staleness={meta.get('staleness_note')}")

# --- ④ 非形状查询不拦截 ---
miss = ea.try_serve("SELECT 台区编号, 配变名称 FROM some_detail_table WHERE date='20260801'")
check(4, "非形状查询走原路径（未拦截）", miss is None, f"返回={miss}")

# --- ⑤ 跨 catalog 显式查询不拦截 ---
cross = ea.try_serve("SELECT COUNT(*) FROM pg_tupu.public.some_table")
check(5, "跨 catalog 显式查询未被拦截", cross is None, f"返回={cross}")

print(f"\n== SOP 五条: {'PASS' if ok_all else 'FAIL'} ==")
sys.exit(0 if ok_all else 1)
