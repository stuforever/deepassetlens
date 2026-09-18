# -*- coding: utf-8 -*-
"""批8 8.2：4coding 唯一默认种子（幂等）。

③目录=app LLMConnectionConfig（llm_admin /llm-connections CRUD 面）。
- name='4coding' 行（用户既有默认，dt_llm_sync.py L28 注释实证）→ is_default=True；
- 其余全部 is_default=False（全目录唯一）；
- 4coding 行不存在→raise SystemExit（停下问用户，不代造）；
- 同源同值断言：主链 get_chat_model('chat') 解析=4coding 行（chat 主链数据面已读③）；
- 幂等：重复运行 no-op（default 已唯一指向 4coding 时零写入）。
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\gitcangku\deepassetlens\backend")

import os

os.chdir(r"D:\gitcangku\deepassetlens\backend")

from app.core.database import SessionLocal
from app.models.base import LLMConnectionConfig

NAME = "4coding"


def main() -> int:
    db = SessionLocal()
    try:
        rows = db.query(LLMConnectionConfig).all()
        target = [r for r in rows if r.name == NAME]
        if not target:
            print(f"BLOCKER: ③目录无 name={NAME!r} 行（用户既有选择，不代造）——停下问用户")
            return 2
        tgt = target[0]
        others = [r for r in rows if r.id != tgt.id]
        already = tgt.is_default and not any(r.is_default for r in others)
        if already:
            print(f"already: {NAME!r} 已是全目录唯一默认（no-op）")
        else:
            tgt.is_default = True
            for r in others:
                r.is_default = False
            db.commit()
            print(f"seeded: {NAME!r} is_default=True，其余 {len(others)} 行 False")
        # 同源同值断言：主链 chat 解析=4coding
        from app.services.llm_client import get_default_llm_connection

        conn = get_default_llm_connection("chat")
        if conn is None:
            print("ASSERT FAIL: 主链 chat 未解析到任何③连接")
            return 1
        ok = conn.id == tgt.id
        print(
            "assert chat-main-chain==4coding: "
            + ("OK" if ok else f"FAIL (resolved id={conn.id} name={conn.name!r})")
        )
        return 0 if ok else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
