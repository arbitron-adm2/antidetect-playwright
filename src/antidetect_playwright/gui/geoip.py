"""GeoIP utilities for IP detection and geolocation."""

import asyncio
import logging
from typing import Optional
import aiohttp

logger = logging.getLogger(__name__)


class GeoIPInfo:
    """GeoIP information."""

    def __init__(self, ip: str, country_code: str, timezone: str, city: str = ""):
        self.ip = ip
        self.country_code = country_code.upper() if country_code else "XX"
        self.timezone = timezone or "UTC"
        self.city = city


async def get_current_ip_info() -> Optional[GeoIPInfo]:
    """Get current public IP and geolocation info."""
    try:
        async with aiohttp.ClientSession() as session:
            # Use ip-api.com free API (no key required, 45 req/min limit)
            async with session.get(
                "http://ip-api.com/json/?fields=status,message,country,countryCode,timezone,city,query",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return GeoIPInfo(
                            ip=data.get("query", ""),
                            country_code=data.get("countryCode", "XX"),
                            timezone=data.get("timezone", "UTC"),
                            city=data.get("city", "")
                        )
                    else:
                        logger.warning(f"GeoIP API error: {data.get('message')}")
    except asyncio.TimeoutError:
        logger.warning("GeoIP request timed out")
    except Exception as e:
        logger.warning(f"Failed to get GeoIP info: {e}")
    
    return None
