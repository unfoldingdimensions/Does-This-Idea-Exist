"""Outbound-request guard (SSRF defense-in-depth) for server-side fetches.

Blocks requests to non-public addresses — private, loopback, link-local,
CGNAT, reserved, multicast, etc. — checked on the *resolved* IP of every hop
(the initial URL and each redirect target), and caps response size so a
hostile remote can't make the server buffer unbounded bodies.

Used by the website-fetch seed path (enrich/website) and the verification
liveness checks (verify). Additive: callers keep their existing signatures;
a blocked target raises BlockedAddressError (a ValueError, so the existing
loud-400/502 error paths handle it unchanged).
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx

MAX_BYTES = 2_000_000  # 2 MB cap on any fetched body
MAX_REDIRECTS = 5


class BlockedAddressError(ValueError):
    """Target (or a redirect hop) is not a public http(s) address."""


def _hostname_blocked(host: str) -> bool:
    h = host.lower().rstrip(".")
    if h in ("localhost", "localhost.localdomain"):
        return True
    if h.endswith((".local", ".internal", ".lan", ".home")) or h == "localhost":
        return True
    return False


def _ip_blocked(ip: str) -> bool:
    """True when the address is not globally routable (SSRF-relevant ranges)."""
    try:
        addr = ipaddress.ip_address(ip.split("%")[0])
    except ValueError:
        return True  # unparseable → treat as blocked, never fetch
    if addr.version == 6 and addr.ipv4_mapped:
        addr = addr.ipv4_mapped  # ::ffff:127.0.0.1 → 127.0.0.1
    # is_global covers private, loopback, link-local, CGNAT, documentation,
    # multicast, reserved and unspecified ranges in one call.
    return not addr.is_global


def check_target(url: str) -> None:
    """Validate scheme, hostname and every resolved address of one target.

    Raises BlockedAddressError when the target is not a public http(s) URL.
    """
    if not url.startswith(("http://", "https://")):
        raise BlockedAddressError(f"not an http(s) URL: {url[:80]!r}")
    host = urlparse(url).hostname or ""
    if not host:
        raise BlockedAddressError(f"no host in URL: {url[:80]!r}")
    if _hostname_blocked(host):
        raise BlockedAddressError(f"blocked internal hostname: {host}")
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise BlockedAddressError(f"could not resolve host: {host}") from exc
    for info in infos:
        ip = info[4][0]
        if _ip_blocked(ip):
            raise BlockedAddressError(f"blocked non-public address {ip} for {host}")


def safe_get(
    url: str,
    *,
    headers: dict | None = None,
    timeout: float = 25.0,
    max_bytes: int = MAX_BYTES,
    max_redirects: int = MAX_REDIRECTS,
) -> httpx.Response:
    """GET with the SSRF guard: validates every redirect hop, caps body size.

    Returns the final (non-redirect) response. Raises BlockedAddressError for
    non-public targets and oversized bodies.
    """
    client = httpx.Client(follow_redirects=False, timeout=timeout)
    try:
        current = url
        for _ in range(max_redirects + 1):
            check_target(current)
            with client.stream("GET", current, headers=headers) as r:
                loc = r.headers.get("location")
                if r.status_code in (301, 302, 303, 307, 308) and loc:
                    current = str(httpx.URL(current).join(loc))
                    continue
                # Final response — read with a hard size cap. iter_raw() keeps
                # the encoded bytes so the reconstructed response (with its
                # original Content-Encoding header) decodes exactly once.
                body = bytearray()
                for chunk in r.iter_raw():
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        raise BlockedAddressError(
                            f"response exceeds {max_bytes} bytes ({url[:80]})"
                        )
                return httpx.Response(
                    status_code=r.status_code,
                    headers=r.headers,
                    content=bytes(body),
                    request=r.request,
                )
        raise BlockedAddressError(f"too many redirects from {url[:80]}")
    finally:
        client.close()
