# -*- coding: utf-8 -*-
"""engine_errors.py - 引擎错误分类（批1：结构化判据）

6 类 error_class 随结果返回，供 SkillPolicy「表/catalog 不存在才允许一次受控降级」
的结构化判定（替代字符串匹配），也让前端/日志按类聚合故障：

    CONNECTION   -- 连不上（Doris 2003/2013、requests 网络错、duckdb ATTACH 失败）
    AUTH         -- 认证/权限（pymysql 1045、HTTP 401/403）
    SYNTAX       -- SQL 语法/列名错误（pymysql 1064/1054、duckdb ParserException、sqlglot）
    TABLE_MISSING-- 表/catalog 不存在（pymysql 1146、duckdb CatalogException）
    TIMEOUT      -- 查询/上游超时（Doris 3024/1317、requests Timeout、DuckDB 120s 护栏）
    UPSTREAM_API -- 上游 API 异常（HTTP 5xx/解析失败等，可重试但非语法问题）
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

ERROR_CLASSES = ("CONNECTION", "AUTH", "SYNTAX", "TABLE_MISSING", "TIMEOUT", "UPSTREAM_API")
DEFAULT_CLASS = "UPSTREAM_API"


class EngineError(Exception):
    """带结构化分类的引擎执行错误。

    Attributes:
        cls: 六类之一（ERROR_CLASSES）。
        message: 人类可读错误信息。
        detail: 可选附加上下文（如表名、HTTP 状态码）。
    """

    def __init__(self, cls: str, message: str, detail: Optional[str] = None):
        super().__init__(message)
        self.cls = cls if cls in ERROR_CLASSES else DEFAULT_CLASS
        self.message = message
        self.detail = detail

    def to_result(self) -> Dict[str, Any]:
        out = {"error": self.message, "error_class": self.cls}
        if self.detail:
            out["error_detail"] = self.detail
        return out


# --------------------------------------------------------------------------- #
# 按错误来源分类
# --------------------------------------------------------------------------- #

def classify_pymysql_error(e: Exception) -> str:
    """pymysql 异常 -> error_class（按 errno 映射）。"""
    errno = getattr(e, "args", None)
    code = errno[0] if isinstance(errno, (tuple, list)) and errno else None
    try:
        if code is not None:
            code = int(code)
    except Exception:
        code = None
    if code in (1045, 1044, 1698):
        return "AUTH"
    if code in (2003, 2002, 2006, 2013):
        return "CONNECTION"
    if code in (3024, 1317, 1205):   # query_timeout / interrupted / lock wait
        return "TIMEOUT"
    if code == 1146:
        return "TABLE_MISSING"
    if code in (1064, 1054, 1149, 1060):
        return "SYNTAX"
    # 无 errno 时按文本兜底
    msg = str(e)
    if "timeout" in msg.lower() or "interrupted" in msg.lower():
        return "TIMEOUT"
    if "doesn't exist" in msg or "1146" in msg or "not exist" in msg.lower():
        return "TABLE_MISSING"
    if "syntax" in msg.lower() or "unknown column" in msg.lower() or "1064" in msg or "1054" in msg:
        return "SYNTAX"
    if "access denied" in msg.lower() or "1045" in msg or "401" in msg or "403" in msg:
        return "AUTH"
    if "connect" in msg.lower() or "2003" in msg or "2013" in msg:
        return "CONNECTION"
    return DEFAULT_CLASS


def classify_requests_error(e: Exception) -> str:
    """requests 异常 -> error_class。"""
    try:
        import requests
        if isinstance(e, requests.exceptions.Timeout):
            return "TIMEOUT"
        if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout)):
            return "CONNECTION"
        if isinstance(e, requests.exceptions.HTTPError):
            code = getattr(e.response, "status_code", None)
            if code in (401, 403):
                return "AUTH"
            return "UPSTREAM_API"
        if isinstance(e, requests.exceptions.RequestException):
            return "CONNECTION"
    except Exception:
        pass
    msg = str(e).lower()
    if "timeout" in msg:
        return "TIMEOUT"
    if "401" in msg or "403" in msg or "unauthor" in msg or "forbidden" in msg:
        return "AUTH"
    if "connect" in msg:
        return "CONNECTION"
    return DEFAULT_CLASS


def classify_duckdb_error(e: Exception) -> str:
    """duckdb / sqlglot 异常 -> error_class。"""
    try:
        import duckdb
        if isinstance(e, duckdb.CatalogException):
            return "TABLE_MISSING"
        if isinstance(e, duckdb.ParserException):
            return "SYNTAX"
    except Exception:
        pass
    try:
        import sqlglot
        if isinstance(e, sqlglot.errors.SqlglotError):
            return "SYNTAX"
    except Exception:
        pass
    # requests 网络/超时（_call_api 抛出的 EngineError 已分类，这里兜底）
    return classify_requests_error(e)


def classify_by_message(err: str) -> str:
    """按错误文本兜底分类（sql_executor / 通用路径用）。"""
    if not err:
        return DEFAULT_CLASS
    low = err.lower()
    if "timeout" in low or "statement_timeout" in low or "execution_timeout" in low or "interrupted" in low:
        return "TIMEOUT"
    if "doesn't exist" in low or "1146" in low or "not exist" in low or "no such table" in low \
            or "unknown table" in low or "catalog" in low and "not found" in low:
        return "TABLE_MISSING"
    if "syntax" in low or "unknown column" in low or "1064" in low or "1054" in low \
            or "parse" in low or "parser" in low:
        return "SYNTAX"
    if "access denied" in low or "1045" in low or "401" in low or "403" in low \
            or "unauthor" in low or "forbidden" in low or "permission" in low:
        return "AUTH"
    if "connect" in low or "2003" in low or "2013" in low or "connection refused" in low \
            or "network" in low:
        return "CONNECTION"
    return DEFAULT_CLASS


def apply_error_class(result: Dict[str, Any]) -> Dict[str, Any]:
    """给含 error 的结果补 error_class（已有则保留），返回原 dict。

    用法：两个引擎 execute 出口统一调用，确保 6 类判据随结果返回。
    """
    if isinstance(result, dict) and result.get("error") and not result.get("error_class"):
        result["error_class"] = classify_by_message(str(result["error"]))
    return result


def wrap_engine_exception(e: Exception, prefix: str = "") -> Dict[str, Any]:
    """把任意引擎异常转成标准错误结果 dict（含 error_class）。

    按异常类型自动分类：pymysql -> requests -> 文本兜底。
    """
    if isinstance(e, EngineError):
        out = e.to_result()
    else:
        cls = DEFAULT_CLASS
        try:
            import pymysql
            if isinstance(e, pymysql.MySQLError):
                cls = classify_pymysql_error(e)
        except Exception:
            pass
        if cls == DEFAULT_CLASS:
            cls = classify_requests_error(e)
        if cls == DEFAULT_CLASS:
            cls = classify_by_message(str(e))
        out = {"error": str(e), "error_class": cls}
    if prefix:
        out["error"] = f"{prefix}{out['error']}"
    return out
