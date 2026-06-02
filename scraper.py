import aiohttp
import asyncio
import logging
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from config import VISA_SOURCES

logger = logging.getLogger(__name__)


async def check_source(source: dict) -> dict | None:
    name = source["name"]
    url = source["url"]
    keywords = source.get("keywords", [])
    check_type = source.get("check_type", "keyword")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ru,en;q=0.9",
    }

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20), ssl=False) as resp:
                if resp.status != 200:
                    logger.warning("%s returned status %s", name, resp.status)
                    return None

                text = await resp.text()

                if check_type == "keyword":
                    soup = BeautifulSoup(text, "lxml")
                    page_text = soup.get_text(separator=" ", strip=True).lower()
                    found = [kw for kw in keywords if kw.lower() in page_text]
                    if found:
                        return {"source": name, "url": url, "found_keywords": found}
    except asyncio.TimeoutError:
        logger.warning("Timeout checking %s", name)
    except Exception as e:
        logger.exception("Error checking %s: %s", name, e)

    return None


async def check_all_sources() -> list[dict]:
    tasks = [check_source(s) for s in VISA_SOURCES]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    hits = []
    for r in results:
        if isinstance(r, dict):
            hits.append(r)
    return hits
