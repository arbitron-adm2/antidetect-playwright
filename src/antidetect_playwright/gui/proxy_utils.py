"""Proxy utilities - ping, geo detection, parsing."""

import asyncio
import logging
import aiohttp
import re
import ipaddress
from datetime import datetime
from typing import Optional

from .models import ProxyConfig, ProxyType

logger = logging.getLogger(__name__)


class ProxyValidationError(ValueError):
    """Raised when proxy validation fails."""

    pass


def validate_proxy_config(proxy: ProxyConfig) -> tuple[bool, Optional[str]]:
    """Validate proxy configuration.

    Args:
        proxy: Proxy configuration to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not proxy.enabled:
        return True, None

    # Validate host
    if not proxy.host:
        return False, "Proxy host is required"

    # Check if host is valid IP or domain
    try:
        # Try parsing as IP
        ipaddress.ip_address(proxy.host)
    except ValueError:
        # Not an IP, check if valid domain
        domain_pattern = re.compile(
            r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
        )
        if not domain_pattern.match(proxy.host):
            return False, f"Invalid proxy host: {proxy.host}"

    # Validate port
    if not (1 <= proxy.port <= 65535):
        return False, f"Invalid port number: {proxy.port} (must be 1-65535)"

    # Validate credentials if present
    if proxy.username and not proxy.password:
        return False, "Password required when username is provided"

    if proxy.password and not proxy.username:
        return False, "Username required when password is provided"

    # Validate username/password characters
    if proxy.username:
        if re.search(r"[\s@:]", proxy.username):
            return False, "Username contains invalid characters (space, @, :)"

    return True, None


async def ping_proxy(proxy: ProxyConfig, timeout: float = 10.0) -> int:
    """Ping proxy and return latency in ms. Returns -1 if failed.

    Args:
        proxy: Proxy configuration
        timeout: Request timeout in seconds

    Returns:
        Latency in milliseconds, or -1 if failed
    """
    # Validate proxy first
    is_valid, error = validate_proxy_config(proxy)
    if not is_valid:
        logger.error(f"Invalid proxy configuration: {error}")
        return -1

    if not proxy.enabled or not proxy.host:
        return -1

    proxy_url = proxy.to_url()
    if not proxy_url:
        logger.error("Failed to convert proxy to URL")
        return -1

    try:
        start = asyncio.get_event_loop().time()

        connector = aiohttp.TCPConnector(ssl=False, limit=1)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                "http://httpbin.org/ip",
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status == 200:
                    end = asyncio.get_event_loop().time()
                    latency = int((end - start) * 1000)
                    logger.debug(f"Proxy {proxy.host}:{proxy.port} ping: {latency}ms")
                    return latency
                else:
                    logger.warning(f"Proxy returned status {response.status}")
                    return -1
    except asyncio.TimeoutError:
        logger.debug(f"Proxy {proxy.host}:{proxy.port} timeout after {timeout}s")
        return -1
    except aiohttp.ClientProxyConnectionError as e:
        logger.debug(f"Proxy connection error: {e}")
        return -1
    except Exception as e:
        logger.debug(
            f"Ping failed for {proxy.host}:{proxy.port}: {type(e).__name__}: {e}"
        )
        return -1


async def detect_proxy_geo(proxy: ProxyConfig) -> dict:
    """Detect proxy location using IP geolocation.

    Args:
        proxy: Proxy configuration

    Returns:
        Dict with geo data:
        - country_code: ISO country code
        - country_name: Full country name
        - city: City name
        - timezone: Timezone string
        - ip: Detected IP address
    """
    # Validate proxy first
    is_valid, error = validate_proxy_config(proxy)
    if not is_valid:
        logger.error(f"Invalid proxy for geo detection: {error}")
        return {}

    if not proxy.enabled or not proxy.host:
        return {}

    proxy_url = proxy.to_url()
    if not proxy_url:
        logger.error("Failed to convert proxy to URL for geo detection")
        return {}

    try:
        connector = aiohttp.TCPConnector(ssl=False, limit=1)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Use ip-api.com for geolocation (free tier)
            async with session.get(
                "http://ip-api.com/json/?fields=status,country,countryCode,city,timezone,query",
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        result = {
                            "country_code": data.get("countryCode", ""),
                            "country_name": data.get("country", ""),
                            "city": data.get("city", ""),
                            "timezone": data.get("timezone", ""),
                            "ip": data.get("query", ""),
                        }
                        logger.info(
                            f"Detected proxy location: {result['country_code']} - {result['city']}"
                        )
                        return result
                    else:
                        logger.warning(f"Geo API returned status: {data.get('status')}")
                else:
                    logger.warning(f"Geo API returned HTTP {response.status}")
    except asyncio.TimeoutError:
        logger.debug(f"Geo detection timeout for {proxy.host}:{proxy.port}")
    except Exception as e:
        logger.debug(
            f"Geo detection failed for {proxy.host}:{proxy.port}: {type(e).__name__}: {e}"
        )

    return {}


def parse_proxy_string(text: str) -> ProxyConfig | None:
    """Parse proxy from various string formats.

    Supported formats:
    - host:port
    - host:port:user:pass
    - user:pass@host:port
    - protocol://host:port
    - protocol://user:pass@host:port

    Args:
        text: Proxy string to parse

    Returns:
        ProxyConfig if valid, None otherwise

    Raises:
        ProxyValidationError: If proxy format is invalid
    """
    text = text.strip()
    if not text:
        return None

    proxy_type = ProxyType.HTTP  # Default
    host = ""
    port = 0
    username = ""
    password = ""

    try:
        # Check for protocol prefix
        if "://" in text:
            match = re.match(r"(\w+)://(.+)", text)
            if match:
                proto = match.group(1).lower()
                text = match.group(2)
                if proto in ("http", "https", "socks4", "socks5"):
                    proxy_type = ProxyType(proto)
                else:
                    raise ProxyValidationError(f"Unsupported protocol: {proto}")

        # Check for user:pass@host:port format
        if "@" in text:
            match = re.match(r"([^:]+):([^@]+)@([^:]+):(\d+)", text)
            if match:
                username = match.group(1)
                password = match.group(2)
                host = match.group(3)
                port = int(match.group(4))
            else:
                raise ProxyValidationError(f"Invalid auth format: {text}")
        else:
            # host:port or host:port:user:pass
            parts = text.split(":")
            if len(parts) >= 2:
                host = parts[0]
                try:
                    port = int(parts[1])
                except ValueError:
                    raise ProxyValidationError(f"Invalid port number: {parts[1]}")

                if len(parts) >= 4:
                    username = parts[2]
                    password = parts[3]
                elif len(parts) == 3:
                    raise ProxyValidationError(
                        "Incomplete credentials (need both username and password)"
                    )
            else:
                raise ProxyValidationError(f"Invalid format: {text}")

        if host and port:
            proxy = ProxyConfig(
                enabled=True,
                proxy_type=proxy_type,
                host=host,
                port=port,
                username=username,
                password=password,
            )

            # Validate the created proxy
            is_valid, error = validate_proxy_config(proxy)
            if not is_valid:
                raise ProxyValidationError(error or "Unknown validation error")

            return proxy
        else:
            raise ProxyValidationError("Missing host or port")

    except ProxyValidationError:
        raise
    except Exception as e:
        logger.debug(f"Failed to parse proxy string '{text}': {e}")
        raise ProxyValidationError(f"Failed to parse proxy: {e}")


def parse_proxy_list(text: str) -> tuple[list[ProxyConfig], list[str]]:
    """Parse multiple proxies from text (one per line).

    Args:
        text: Multi-line proxy list

    Returns:
        Tuple of (parsed_proxies, error_lines)
        - parsed_proxies: Successfully parsed proxies
        - error_lines: Lines that failed to parse
    """
    proxies = []
    errors = []

    for line_num, line in enumerate(text.strip().split("\n"), start=1):
        line = line.strip()
        if line and not line.startswith("#"):
            try:
                proxy = parse_proxy_string(line)
                if proxy:
                    proxies.append(proxy)
            except ProxyValidationError as e:
                error_msg = f"Line {line_num}: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)
            except Exception as e:
                error_msg = f"Line {line_num}: Unexpected error: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

    logger.info(f"Parsed {len(proxies)} proxies, {len(errors)} errors")
    return proxies, errors
