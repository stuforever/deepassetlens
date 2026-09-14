# -*- coding: utf-8 -*-
"""专家地基①（2026-09-12 spec §八）：隔离命名空间单点收口。

①期只写有消费者的函数；将来加租户=改本模块（Q4 判据）；②期 per-user 记忆树在此追加。
收口执行令：新函数必须是 thread_id 三段键的唯一构造处（endpoint.py L74 与
data_intelligence_misc.py L145 的内联拼接均改走此处）。
"""
from pathlib import Path
from typing import Dict, List

_DATA_ROOT = Path(__file__).resolve().parent.parent.parent / "data"


def thread_id(user: str, expert_id: str, thread_id: str) -> str:
    """checkpoint 键 + 会话锁键 + 清除记忆端点（三消费点）。"""
    return f"{user}:{expert_id}:{thread_id}"


def _roots(card_paths: List[str]) -> List[Path]:
    """卡声明路径→data/ 下物理根目录集合（"/skills/"→data/skills；
    "/memory/AGENTS.md"→data/memory——文件取其根，等值现状两根）。"""
    out = set()
    for p in card_paths or []:
        parts = [seg for seg in str(p).split("/") if seg]
        if parts:
            out.add(_DATA_ROOT / parts[0])
    return sorted(out)


def skills_roots(card: Dict) -> List[Path]:
    return _roots(card.get("skills"))


def memory_roots(card: Dict) -> List[Path]:
    return _roots(card.get("memory"))
