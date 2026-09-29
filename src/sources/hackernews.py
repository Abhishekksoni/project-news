"""Hacker News 'Best' trending source ingestion (https://news.ycombinator.com/best) with external article metadata extraction and top comment fallback."""

import asyncio
from datetime import UTC, datetime
from functools import lru_cache
import html
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import httpx

from models.news import NewsItem

HN_BEST_STORIES_URL = "https://hacker-news.firebaseio.com/v0/beststories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item"
HN_FALLBACK_IMAGE = "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=800&auto=format&fit=crop&q=60"


def clean_text_formatting(text: str) -> str:
    """Strip markdown symbols, HTML entities, and formatting artifacts."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"\\([~*_\-\[\]\(\)])", r"\1", text)
    text = text.replace("\\", "")
    text = re.sub(r"\*{1,3}", "", text)
    text = re.sub(r"_{1,3}", "", text)
    text = re.sub(r"(^|\s)>\s*", r"\1 ", text)
    text = re.sub(r"[#~`>]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def _fetch_external_metadata(client: httpx.AsyncClient, url: str) -> tuple[str | None, str | None]:
    """
    Fetch external article page and extract:
    1. Real article description (og:description / meta description / first paragraph)
    2. Primary OpenGraph image
    """
    if not url or not url.startswith("http"):
        return None, None

    try:
        resp = await client.get(
            url,
            timeout=5.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        if resp.status_code != 200:
            return None, None

        soup = BeautifulSoup(resp.text[:100000], "html.parser")

        # 1. Extract Description
        desc = None
        og_desc = (
            soup.find("meta", property="og:description")
            or soup.find("meta", attrs={"name": "og:description"})
            or soup.find("meta", attrs={"name": "description"})
            or soup.find("meta", property="twitter:description")
            or soup.find("meta", attrs={"name": "twitter:description"})
        )
        if og_desc and og_desc.get("content"):
            desc = og_desc["content"].strip()

        if not desc or len(desc) < 35:
            # Look inside article or main body
            container = soup.find("article") or soup.find("main") or soup
            for p in container.find_all("p"):
                t = p.get_text(separator=" ", strip=True)
                if (
                    len(t) > 45
                    and not t.lower().startswith(("cookie", "javascript", "sign in", "subscribe", "september", "october", "november", "december", "january", "february", "march", "april", "may", "june", "july", "august"))
                    and not t.startswith("©")
                ):
                    desc = t
                    break

        if desc:
            desc = clean_text_formatting(desc)
            if len(desc) > 340:
                desc = desc[:340].rsplit(" ", 1)[0] + "..."

        # 2. Extract OpenGraph Image
        img_url = None
        og_img = (
            soup.find("meta", property="og:image")
            or soup.find("meta", attrs={"name": "og:image"})
            or soup.find("meta", property="twitter:image")
            or soup.find("meta", attrs={"name": "twitter:image"})
            or soup.find("link", rel="image_src")
        )
        if og_img:
            content = og_img.get("content") or og_img.get("href")
            if content and content.strip():
                raw_img = content.strip()
                if not raw_img.startswith("http"):
                    raw_img = urljoin(str(resp.url), raw_img)
                if raw_img.startswith("http"):
                    img_url = raw_img

        return desc, img_url
    except Exception:
        pass
    return None, None


async def _fetch_top_comment(client: httpx.AsyncClient, kids: list[int]) -> str | None:
    """Fetch top comment from Hacker News if external description is paywalled/blocked."""
    if not kids:
        return None
    for kid_id in kids[:2]:
        try:
            resp = await client.get(f"{HN_ITEM_URL}/{kid_id}.json", timeout=3.0)
            if resp.status_code == 200:
                c = resp.json()
                if c and c.get("text") and not c.get("deleted") and not c.get("dead"):
                    soup = BeautifulSoup(c["text"], "html.parser")
                    text = soup.get_text(separator=" ", strip=True)
                    clean_t = clean_text_formatting(text)
                    if len(clean_t) > 40:
                        if len(clean_t) > 320:
                            clean_t = clean_t[:320].rsplit(" ", 1)[0] + "..."
                        return f"Top Discussion: {clean_t}"
        except Exception:
            continue
    return None


async def _fetch_single_story(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    story_id: int,
    max_age_days: int = 7,
) -> NewsItem | None:
    """Fetch details for a single HN story within 7 days."""
    async with sem:
        try:
            resp = await client.get(f"{HN_ITEM_URL}/{story_id}.json", timeout=4.0)
            if resp.status_code != 200:
                return None
            story = resp.json()

            if not story or story.get("type") != "story":
                return None

            title = story.get("title", "").strip()
            if not title:
                return None

            raw_url = story.get("url")
            is_external = bool(raw_url and not raw_url.startswith("https://news.ycombinator.com"))
            url = raw_url if raw_url else f"https://news.ycombinator.com/item?id={story_id}"

            points = story.get("score", 0)
            comments = story.get("descendants", 0)
            author = story.get("by", "Hacker News")
            kids = story.get("kids", [])

            published_at = datetime.now(UTC)
            if story.get("time"):
                try:
                    published_at = datetime.fromtimestamp(story["time"], tz=UTC)
                    age_seconds = (datetime.now(UTC) - published_at).total_seconds()
                    if age_seconds > max_age_days * 86400:
                        return None
                except Exception:
                    pass

            ext_desc, ext_image = (
                await _fetch_external_metadata(client, url)
                if is_external
                else (None, None)
            )

            raw_text = story.get("text")
            if ext_desc and len(ext_desc) > 30:
                description = f"{ext_desc} [{points:,} points · {comments:,} comments]"
            elif raw_text:
                soup = BeautifulSoup(raw_text, "html.parser")
                clean_t = clean_text_formatting(soup.get_text(separator=" ", strip=True))
                description = f"{clean_t[:300]} [{points:,} points · {comments:,} comments]"
            else:
                # Try top comment fallback
                top_comment = await _fetch_top_comment(client, kids)
                if top_comment:
                    description = f"{top_comment} [{points:,} points · {comments:,} comments]"
                else:
                    domain = urlparse(url).netloc.replace("www.", "") if url else "Hacker News"
                    description = f"Trending discussion and analysis on {title} ({domain}). [{points:,} points · {comments:,} comments]"

            image_url = ext_image if ext_image else HN_FALLBACK_IMAGE

            if description and len(description) > 350:
                description = description[:350].rsplit(" ", 1)[0] + "..."

            return NewsItem(
                id=f"hn_{story_id}",
                title=title,
                url=url,
                source="Hacker News (Best)",
                source_type="community",
                published_at=published_at,
                author=author,
                description=description,
                category="tech_community",
                image_url=image_url,
                collected_at=datetime.now(UTC),
            )
        except Exception:
            return None


async def fetch_hacker_news(limit: int | None = 30, max_age_days: int = 7) -> list[NewsItem]:
    """
    Fetch the highest-voted, curated 'Best' stories from Hacker News (https://news.ycombinator.com/best) within 7 days.
    """
    try:
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
        async with httpx.AsyncClient(timeout=8.0, limits=limits) as client:
            resp = await client.get(HN_BEST_STORIES_URL)
            resp.raise_for_status()
            best_ids = resp.json()
            target_ids = best_ids[:limit] if limit is not None else best_ids[:40]

            sem = asyncio.Semaphore(25)
            tasks = [_fetch_single_story(client, sem, sid, max_age_days) for sid in target_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            news_items = [
                r for r in results
                if isinstance(r, NewsItem) and r is not None
            ]
            return news_items[:limit] if limit is not None else news_items
    except Exception as e:
        print(f"[Hacker News Best Error] {e}")
        return []