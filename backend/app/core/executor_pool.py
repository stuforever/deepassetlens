"""
执行器线程池
用于将同步执行（DB/SQL/HTTP）放到后台线程中运行，避免阻塞主事件循环
"""

import concurrent.futures
from typing import Callable, Any
import functools

# 全局线程池（IO 密集型任务：数据库查询、HTTP 请求）
_io_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=20,
    thread_name_prefix="io_worker"
)

# CPU 密集型任务线程池（Python 沙箱执行）
_cpu_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=8,
    thread_name_prefix="cpu_worker"
)


def run_in_thread(func: Callable, *args, use_cpu_pool: bool = False, **kwargs) -> concurrent.futures.Future:
    """
    将同步函数放到线程池中执行

    Args:
        func: 要执行的函数
        use_cpu_pool: 是否使用 CPU 密集型线程池（Python 执行等）
    """
    pool = _cpu_executor if use_cpu_pool else _io_executor
    return pool.submit(func, *args, **kwargs)


def shutdown_executors(wait: bool = True):
    """关闭所有线程池（应用关闭时调用）"""
    _io_executor.shutdown(wait=wait)
    _cpu_executor.shutdown(wait=wait)


def get_executor_stats() -> dict:
    """获取线程池统计信息"""
    io_active = len(getattr(_io_executor, '_threads', set()))
    cpu_active = len(getattr(_cpu_executor, '_threads', set()))
    return {
        "io_pool": {
            "max_workers": _io_executor._max_workers,
            "active": io_active,
        },
        "cpu_pool": {
            "max_workers": _cpu_executor._max_workers,
            "active": cpu_active,
        },
    }
