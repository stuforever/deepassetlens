"""
服务端出站 URL 安全校验（F-SSRF 收口工具）

两个口径：
- validate_public_http_url(url)：面向「URL 受客户端输入/模型输出影响」的出站请求。
  校验 scheme 仅 http/https、host 非空，且解析出的 IP 不落在环回/私网/链路本地/
  保留网段（防探测内网与云元数据 169.254.169.254）。
- validate_http_url_shape(url)：面向管理员显式配置的内网目标（如自建 ES/Kafka），
  仅校验 scheme 与 host 形状，不限制私网网段。

违规统一抛 SsrfBlockedUrlError(ValueError)。域名解析失败的 URL 视为不可信。
"""
import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_ALLOWED_SCHEMES = ("http", "https")


class SsrfBlockedUrlError(ValueError):
    """URL 未通过出站安全校验。"""


def _reject(reason: str, url: str) -> None:
    raise SsrfBlockedUrlError(f"{reason}: {url[:200]}")


def _host_is_public(host: str) -> bool:
    """host 解析出的全部 IP 均不在保留/私网/环回/链路本地网段才算公网目标。"""
    candidate_ips = []
    try:
        candidate_ips.append(ipaddress.ip_address(host))
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None)
        except (socket.gaierror, UnicodeError) as exc:
            logger.warning("url_guard: 域名解析失败，按不可信处理 %s: %s", host, exc)
            return False
        for info in infos:
            try:
                candidate_ips.append(ipaddress.ip_address(info[4][0]))
            except ValueError:
                return False
    if not candidate_ips:
        return False
    for ip in candidate_ips:
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


def validate_public_http_url(url: str) -> str:
    """严格口径：仅放行公网 http(s) 目标。返回规范化后的 URL。"""
    parsed = urlparse(url or "")
    if parsed.scheme not in _ALLOWED_SCHEMES:
        _reject("仅允许 http/https 协议", url)
    host = parsed.hostname
    if not host:
        _reject("缺少目标主机", url)
    if not _host_is_public(host):
        _reject("目标主机不在公网网段（禁止环回/私网/链路本地/保留地址）", url)
    return url


def validate_http_url_shape(url: str) -> str:
    """宽松口径：仅校验 scheme 与 host 形状（允许内网目标，供管理员配置项使用）。"""
    parsed = urlparse(url or "")
    if parsed.scheme not in _ALLOWED_SCHEMES:
        _reject("仅允许 http/https 协议", url)
    if not parsed.hostname:
        _reject("缺少目标主机", url)
    return url
