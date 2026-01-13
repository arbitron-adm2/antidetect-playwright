"""GeoIP utilities for IP detection and geolocation."""

import asyncio
import logging
from typing import Optional
import aiohttp

logger = logging.getLogger(__name__)

# Map obscure/regional timezones to standard/common ones
# These are timezones that might trigger fingerprint detection
TIMEZONE_NORMALIZATION: dict[str, str] = {
    # Russia - normalize regional zones to Moscow or major cities
    "Europe/Kirov": "Europe/Moscow",
    "Europe/Saratov": "Europe/Moscow",
    "Europe/Ulyanovsk": "Europe/Moscow",
    "Europe/Astrakhan": "Europe/Moscow",
    "Europe/Volgograd": "Europe/Moscow",
    "Europe/Samara": "Europe/Moscow",
    "Asia/Barnaul": "Asia/Novosibirsk",
    "Asia/Tomsk": "Asia/Novosibirsk",
    "Asia/Novokuznetsk": "Asia/Novosibirsk",
    "Asia/Chita": "Asia/Irkutsk",
    "Asia/Khandyga": "Asia/Yakutsk",
    "Asia/Ust-Nera": "Asia/Vladivostok",
    "Asia/Srednekolymsk": "Asia/Magadan",
    "Asia/Anadyr": "Asia/Kamchatka",
    # Ukraine
    "Europe/Zaporozhye": "Europe/Kyiv",
    "Europe/Uzhgorod": "Europe/Kyiv",
    # Kazakhstan
    "Asia/Qostanay": "Asia/Almaty",
    "Asia/Qyzylorda": "Asia/Almaty",
    "Asia/Atyrau": "Asia/Almaty",
    "Asia/Oral": "Asia/Almaty",
    "Asia/Aqtau": "Asia/Almaty",
    "Asia/Aqtobe": "Asia/Almaty",
    # USA - normalize to major metro zones
    "America/Indiana/Indianapolis": "America/New_York",
    "America/Indiana/Marengo": "America/New_York",
    "America/Indiana/Knox": "America/Chicago",
    "America/Indiana/Tell_City": "America/Chicago",
    "America/Indiana/Petersburg": "America/New_York",
    "America/Indiana/Vincennes": "America/New_York",
    "America/Indiana/Winamac": "America/New_York",
    "America/Indiana/Vevay": "America/New_York",
    "America/Kentucky/Louisville": "America/New_York",
    "America/Kentucky/Monticello": "America/New_York",
    "America/Detroit": "America/New_York",
    "America/Menominee": "America/Chicago",
    "America/North_Dakota/Center": "America/Chicago",
    "America/North_Dakota/New_Salem": "America/Chicago",
    "America/North_Dakota/Beulah": "America/Chicago",
    "America/Boise": "America/Denver",
    "America/Shiprock": "America/Denver",
    # Canada
    "America/Atikokan": "America/Toronto",
    "America/Nipigon": "America/Toronto",
    "America/Thunder_Bay": "America/Toronto",
    "America/Rainy_River": "America/Winnipeg",
    "America/Pangnirtung": "America/Toronto",
    "America/Iqaluit": "America/Toronto",
    "America/Rankin_Inlet": "America/Winnipeg",
    "America/Cambridge_Bay": "America/Edmonton",
    "America/Yellowknife": "America/Edmonton",
    "America/Inuvik": "America/Edmonton",
    "America/Dawson_Creek": "America/Vancouver",
    "America/Fort_Nelson": "America/Vancouver",
    "America/Creston": "America/Vancouver",
    # Brazil
    "America/Araguaina": "America/Sao_Paulo",
    "America/Bahia": "America/Sao_Paulo",
    "America/Belem": "America/Sao_Paulo",
    "America/Fortaleza": "America/Sao_Paulo",
    "America/Maceio": "America/Sao_Paulo",
    "America/Recife": "America/Sao_Paulo",
    "America/Santarem": "America/Sao_Paulo",
    # Australia
    "Australia/Lindeman": "Australia/Brisbane",
    "Australia/Broken_Hill": "Australia/Sydney",
    "Australia/Lord_Howe": "Australia/Sydney",
    "Australia/Currie": "Australia/Hobart",
    # Europe
    "Europe/Busingen": "Europe/Zurich",
    "Europe/Simferopol": "Europe/Moscow",
    "Europe/Mariehamn": "Europe/Helsinki",
    "Europe/Vatican": "Europe/Rome",
    "Europe/San_Marino": "Europe/Rome",
    "Europe/Monaco": "Europe/Paris",
    "Europe/Andorra": "Europe/Paris",
    "Europe/Vaduz": "Europe/Zurich",
    "Europe/Gibraltar": "Europe/London",
    "Europe/Jersey": "Europe/London",
    "Europe/Guernsey": "Europe/London",
    "Europe/Isle_of_Man": "Europe/London",
    # Asia
    "Asia/Urumqi": "Asia/Shanghai",
    "Asia/Kashgar": "Asia/Shanghai",
    "Asia/Hebron": "Asia/Jerusalem",
    "Asia/Gaza": "Asia/Jerusalem",
    "Asia/Famagusta": "Europe/Nicosia",
    # Africa
    "Africa/Ceuta": "Europe/Madrid",
    # Atlantic/Pacific islands
    "Pacific/Ponape": "Pacific/Guam",
    "Pacific/Kosrae": "Pacific/Guam",
    "Pacific/Chuuk": "Pacific/Guam",
}


def normalize_timezone(tz: str) -> str:
    """Normalize obscure timezone to a common one."""
    return TIMEZONE_NORMALIZATION.get(tz, tz)


class GeoIPInfo:
    """GeoIP information."""

    def __init__(
        self,
        ip: str,
        country_code: str,
        timezone: str,
        city: str = "",
        lat: float = 0.0,
        lon: float = 0.0,
        region_code: str = "",
    ):
        self.ip = ip
        self.country_code = country_code.upper() if country_code else "XX"
        # Don't normalize timezone - it must match IP location for fingerprint consistency
        self.timezone = timezone or "UTC"
        self.city = city
        self.lat = lat
        self.lon = lon
        self.region_code = region_code


async def get_current_ip_info(proxy_url: Optional[str] = None) -> Optional[GeoIPInfo]:
    """Get current public IP and geolocation info.

    Args:
        proxy_url: Optional proxy URL (e.g. "http://user:pass@host:port")
    """
    try:
        connector = None
        if proxy_url:
            from aiohttp_socks import ProxyConnector

            connector = ProxyConnector.from_url(proxy_url)

        async with aiohttp.ClientSession(connector=connector) as session:
            # Use ip-api.com free API (no key required, 45 req/min limit)
            # Request all fields needed for fingerprint spoofing
            async with session.get(
                "http://ip-api.com/json/?fields=status,message,country,countryCode,region,city,lat,lon,timezone,query",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return GeoIPInfo(
                            ip=data.get("query", ""),
                            country_code=data.get("countryCode", "XX"),
                            timezone=data.get("timezone", "UTC"),
                            city=data.get("city", ""),
                            lat=data.get("lat", 0.0),
                            lon=data.get("lon", 0.0),
                            region_code=data.get("region", ""),
                        )
                    else:
                        logger.warning(f"GeoIP API error: {data.get('message')}")
    except asyncio.TimeoutError:
        logger.warning("GeoIP request timed out")
    except Exception as e:
        logger.warning(f"Failed to get GeoIP info: {e}")

    return None
