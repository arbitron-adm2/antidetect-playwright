"""Proxy utilities - ping, geo detection, parsing."""

import asyncio
import logging
import aiohttp
import re
from datetime import datetime

from .models import ProxyConfig, ProxyType

logger = logging.getLogger(__name__)


async def ping_proxy(proxy: ProxyConfig, timeout: float = 10.0) -> int:
    """Ping proxy and return latency in ms. Returns -1 if failed."""
    if not proxy.enabled or not proxy.host:
        return -1

    proxy_url = proxy.to_url()
    if not proxy_url:
        return -1

    try:
        start = asyncio.get_event_loop().time()

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://httpbin.org/ip",
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status == 200:
                    end = asyncio.get_event_loop().time()
                    return int((end - start) * 1000)
    except Exception as e:
        logger.debug("Ping failed: %s", e)

    return -1


async def detect_proxy_geo(proxy: ProxyConfig) -> dict:
    """Detect proxy location using IP geolocation.

    Returns dict with:
    - country_code
    - country_name
    - city
    - timezone
    - ip
    """
    if not proxy.enabled or not proxy.host:
        return {}

    proxy_url = proxy.to_url()
    if not proxy_url:
        return {}

    try:
        async with aiohttp.ClientSession() as session:
            # Use ip-api.com for geolocation
            async with session.get(
                "http://ip-api.com/json/?fields=status,country,countryCode,city,timezone,query",
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return {
                            "country_code": data.get("countryCode", ""),
                            "country_name": data.get("country", ""),
                            "city": data.get("city", ""),
                            "timezone": data.get("timezone", ""),
                            "ip": data.get("query", ""),
                        }
    except Exception as e:
        logger.debug("Geo detection failed: %s", e)

    return {}


def parse_proxy_string(text: str) -> ProxyConfig | None:
    """Parse proxy from various string formats.

    Supported formats:
    - host:port
    - host:port:user:pass
    - user:pass@host:port
    - protocol://host:port
    - protocol://user:pass@host:port
    """
    text = text.strip()
    if not text:
        return None

    proxy_type = ProxyType.HTTP  # Default
    host = ""
    port = 0
    username = ""
    password = ""

    # Check for protocol prefix
    if "://" in text:
        match = re.match(r"(\w+)://(.+)", text)
        if match:
            proto = match.group(1).lower()
            text = match.group(2)
            if proto in ("http", "https", "socks4", "socks5"):
                proxy_type = ProxyType(proto)

    # Check for user:pass@host:port format
    if "@" in text:
        match = re.match(r"([^:]+):([^@]+)@([^:]+):(\d+)", text)
        if match:
            username = match.group(1)
            password = match.group(2)
            host = match.group(3)
            port = int(match.group(4))
    else:
        # host:port or host:port:user:pass
        parts = text.split(":")
        if len(parts) >= 2:
            host = parts[0]
            port = int(parts[1])
            if len(parts) >= 4:
                username = parts[2]
                password = parts[3]

    if host and port:
        return ProxyConfig(
            enabled=True,
            proxy_type=proxy_type,
            host=host,
            port=port,
            username=username,
            password=password,
        )

    return None


def parse_proxy_list(text: str) -> list[ProxyConfig]:
    """Parse multiple proxies from text (one per line)."""
    proxies = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            proxy = parse_proxy_string(line)
            if proxy:
                proxies.append(proxy)
    return proxies
