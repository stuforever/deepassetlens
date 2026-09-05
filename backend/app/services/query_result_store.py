"""query_result_store.py - 查询结果暂存柜（13-AB ④：data_result 派发的 result_ref 机制）。

职责：MCP 工具端截断前的全量数据暂存；SSE 路由层按 result_ref 取回派发前端。
淘汰：TTL 10min + 上限 64 条，双淘汰（取用时惰性清扫+每 put 触发）。
安全：uuid4 不可猜；同进程内存（跨会话需猜中 uuid，登记接受）。
"""
import os
import time
import uuid

# 批14-C：TTL/容量 env 旋钮（设计 §3.1）——默认值不变=零行为变化；TTL=5 的 e2e 剧本
# （设短 TTL 重启→提问→等过期→断言降级提示）据此可测，勾销 AB-4 豁免登记第一条。
_RESULT_TTL = int(os.getenv("TUPU_QRS_TTL_SECONDS", "600"))   # 10 分钟
_MAX_ENTRIES = int(os.getenv("TUPU_QRS_CAP", "64"))
_store: dict[str, tuple[float, dict]] = {}


def put(payload: dict) -> str:
    """全量数据进暂存柜；超限淘汰最旧；返回 uuid4 key。"""
    sweep()
    key = str(uuid.uuid4())
    _store[key] = (time.time(), payload)
    # 上限淘汰：最旧优先（ts 最小）
    if len(_store) > _MAX_ENTRIES:
        oldest = sorted(_store.items(), key=lambda kv: kv[1][0])[: len(_store) - _MAX_ENTRIES]
        for k, _ in oldest:
            _store.pop(k, None)
    return key


def get(key: str) -> dict | None:
    """TTL 内返回 payload；过期删 + None。"""
    item = _store.pop(key, None)
    if item is None:
        return None
    ts, payload = item
    if time.time() - ts > _RESULT_TTL:
        return None  # 过期：已删，不回填
    _store[key] = item  # 未过期：回填（pop 只是为原子取）
    return payload


def sweep() -> None:
    """惰性清扫过期项（put 时调用）。"""
    now = time.time()
    expired = [k for k, (ts, _) in _store.items() if now - ts > _RESULT_TTL]
    for k in expired:
        _store.pop(k, None)
