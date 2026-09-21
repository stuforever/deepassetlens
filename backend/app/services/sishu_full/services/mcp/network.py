"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / cloud metadata
    ipaddress.ip_network("fe80::/10"),  # link-local v6
]

# Additionally blocked for user-supplied URLs: everything that points back at
# the deployment itself or its private network.
_STRICT_EXTRA_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),  # carrier-grade NAT / tailscale
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),  # unique-local v6
]


def _normalize_addr(
    addr: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Normalize IPv6-mapped IPv4 addresses (``::ffff:169.254.x.x``) to IPv4."""
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        return addr.ipv4_mapped
    return addr


def _is_blocked(
    addr: ipaddress.IPv4Address | ipaddress.IPv6Address,
    *,
    strict: bool,
) -> bool:
    normalized = _normalize_addr(addr)
    networks = _BLOCKED_NETWORKS + (_STRICT_EXTRA_NETWORKS if strict else [])
    return any(normalized in net for net in networks)


def validate_mcp_url(url: str, *, strict: bool = False) -> tuple[bool, str]:
    """Validate a remote MCP server URL: scheme, hostname, resolved IPs.

    ``strict`` applies the self-service posture (see the module docstring): a
    user-supplied URL may not resolve to loopback or a private range.

    Returns ``(ok, error_message)``; ``error_message`` is empty when ok.
    """
    try:
        parsed = urlparse(url)
    except Exception as exc:
        return False, str(exc)

    if parsed.scheme not in ("http", "https"):
        return False, f"Only http/https allowed, got {parsed.scheme or 'none'!r}"
    hostname = parsed.hostname
    if not hostname:
        return False, "Missing hostname"

    try:
        infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        return False, f"Cannot resolve hostname: {hostname}"

    for info in infos:
        try:
            addr = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if _is_blocked(addr, strict=strict):
            return False, (
                f"Blocked: {hostname} resolves to a disallowed address ({addr}). "
                "A server you configure yourself must be reachable on the public internet."
                if strict
                else f"Blocked: {hostname} resolves to link-local/metadata address {addr}"
            )
    return True, ""


async def validate_mcp_url_async(url: str, *, strict: bool = False) -> tuple[bool, str]:
    """:func:`validate_mcp_url` off the event loop.

    The check resolves DNS with a blocking call, which on a slow or dead
    resolver stalls for seconds. On the event loop that is not one slow request
    — it is every request in the process, so any caller already inside async
    code uses this.
    """
    import asyncio

    return await asyncio.to_thread(validate_mcp_url, url, strict=strict)


__all__ = ["validate_mcp_url", "validate_mcp_url_async"]
