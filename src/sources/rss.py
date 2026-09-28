"""Generic RSS/Atom feed parser with robust image extraction, OpenGraph scraping, Google News URL decoding, and HTML cleaning."""

from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import html
import re

from bs4 import BeautifulSoup
import feedparser
from googlenewsdecoder import gnewsdecoder
import httpx

from models.news import NewsItem

# Curated fallback images by category to ensure high visual quality
FALLBACK_IMAGES: dict[str, str] = {
    "ai_research": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=800&auto=format&fit=crop&q=60",
    "iit_startups": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=800&auto=format&fit=crop&q=60",
    "iit_research": "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=800&auto=format&fit=crop&q=60",
    "machine_learning": "https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=800&auto=format&fit=crop&q=60",
    "data_science": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&auto=format&fit=crop&q=60",
    "ai_engineering": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&auto=format&fit=crop&q=60",
    "ai_insights": "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800&auto=format&fit=crop&q=60",
    "tech_blogs": "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=800&auto=format&fit=crop&q=60",
    "indian_startups": "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=800&auto=format&fit=crop&q=60",
    "community": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=800&auto=format&fit=crop&q=60",
    "default": "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=800&auto=format&fit=crop&q=60",
}


def _clean_html_text(raw_html: str | None) -> str | None:
    """Strip raw HTML tags and decode entities into clean text."""
    if not raw_html:
        return None

    # Parse with BeautifulSoup to eliminate HTML tags and scripts
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = html.unescape(text)
    # Collapse multiple whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None


from urllib.parse import urljoin


@lru_cache(maxsize=1024)
def _fetch_og_image(article_url: str) -> str | None:
    """Fetch OpenGraph or Twitter preview image directly from the article webpage using social bot headers to bypass Cloudflare/bot-guards."""
    if not article_url or not article_url.startswith("http"):
        return None

    try:
        with httpx.Client(
            timeout=3.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        ) as client:
            resp = client.get(article_url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text[:120000], "html.parser")
                og = (
                    soup.find("meta", property="og:image")
                    or soup.find("meta", attrs={"name": "og:image"})
                    or soup.find("meta", property="og:image:url")
                    or soup.find("meta", property="og:image:secure_url")
                    or soup.find("meta", property="twitter:image")
                    or soup.find("meta", attrs={"name": "twitter:image"})
                    or soup.find("meta", attrs={"name": "twitter:image:src"})
                    or soup.find("link", rel="image_src")
                )
                if og:
                    content = og.get("content") or og.get("href")
                    if content and content.strip():
                        raw_img = content.strip()
                        if not raw_img.startswith("http"):
                            raw_img = urljoin(str(resp.url), raw_img)
                        if raw_img.startswith("http"):
                            return raw_img
    except Exception:
        pass

    return None


@lru_cache(maxsize=1024)
def _resolve_canonical_url(url: str) -> str:
    """Resolve Google News redirection tokens to the real destination publisher URL."""
    if "news.google.com/rss/articles" in url or "news.google.com/articles" in url:
        try:
            decoded = gnewsdecoder(url)
            if isinstance(decoded, dict) and decoded.get("decoded_url"):
                return decoded["decoded_url"]
            elif isinstance(decoded, str) and decoded.startswith("http"):
                return decoded
        except Exception:
            pass
    return url


def _extract_image_url(
    entry: dict, content_html: str | None, article_url: str, category: str | None
) -> str | None:
    """
    Extract best available image from:
    1. Media RSS tags (media:content, media:thumbnail)
    2. Enclosures
    3. Embedded <img> in HTML summary/content
    4. OpenGraph <meta property="og:image"> scraped from article URL
    5. Curated category fallback banner
    """
    # 1. media:content
    media_content = entry.get("media_content")
    if media_content:
        for media in media_content:
            if isinstance(media, dict) and media.get("url"):
                return media["url"]

    # 2. media:thumbnail
    media_thumbnail = entry.get("media_thumbnail")
    if media_thumbnail:
        if isinstance(media_thumbnail, list) and len(media_thumbnail) > 0:
            first = media_thumbnail[0]
            if isinstance(first, dict) and first.get("url"):
                return first["url"]

    # 3. enclosures (direct image attachments)
    enclosures = entry.get("enclosures")
    if enclosures:
        for enclosure in enclosures:
            if isinstance(enclosure, dict):
                enc_type = enclosure.get("type", "")
                enc_href = enclosure.get("href", "")
                if enc_type.startswith("image/") or enc_href.endswith(
                    (".png", ".jpg", ".jpeg", ".webp", ".gif")
                ):
                    return enc_href

    # 4. Parse embedded <img> tag in HTML content/summary
    if content_html:
        soup = BeautifulSoup(content_html, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            src = img["src"]
            if src.startswith("http"):
                return src

    # 5. Scrape og:image only for primary blogs where OG provides high-res banners
    primary_og_domains = ("openai.com", "berkeley.edu", "latent.space", "simonwillison.net", "huyenchip.com", "sebastianraschka.com")
    if article_url and any(d in article_url for d in primary_og_domains):
        og_img = _fetch_og_image(article_url)
        if og_img:
            return og_img

    # 6. Fallback curated category image
    return FALLBACK_IMAGES.get(category or "default", FALLBACK_IMAGES["default"])


def fetch_rss(
    feed_url: str,
    source_name: str,
    category: str | None = None,
    limit: int | None = 30,
    max_age_days: int | None = 7,
) -> list[NewsItem]:
    feed = feedparser.parse(
        feed_url,
        agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)",
    )

    news_items = []

    for entry in feed.entries:
        if limit is not None and len(news_items) >= limit:
            break
        title = entry.get("title", "").strip()
        raw_url = entry.get("link", "").strip()

        if not title or not raw_url:
            continue

        # Published date
        published_at = None
        if entry.get("published_parsed"):
            published_at = datetime(
                *entry.published_parsed[:6],
                tzinfo=timezone.utc,
            )
        elif entry.get("updated_parsed"):
            published_at = datetime(
                *entry.updated_parsed[:6],
                tzinfo=timezone.utc,
            )

        # Filter out articles older than max_age_days if published_at is present
        if published_at and max_age_days is not None:
            age_seconds = (datetime.now(timezone.utc) - published_at).total_seconds()
            if age_seconds > max_age_days * 86400:
                continue

        # Resolve Google News redirection token to real publisher URL only for valid items
        url = _resolve_canonical_url(raw_url)

        # Raw HTML content sources (summary vs content)
        raw_summary = entry.get("summary", "")
        raw_content = ""
        if "content" in entry and entry["content"]:
            raw_content = entry["content"][0].get("value", "")

        combined_html = raw_content or raw_summary

        # Clean plain text description
        clean_description = _clean_html_text(raw_summary or raw_content)

        # If description is identical to title (common in Google News RSS), use snippet
        if clean_description and clean_description.lower() == title.lower():
            clean_description = f"Latest update on {title} from {source_name}."

        # Extract image: media RSS -> embedded img -> OpenGraph -> fallback
        image_url = _extract_image_url(entry, combined_html, url, category)

        # Author extraction
        author = entry.get("author") or entry.get("dc_creator")

        # Stable ID based on canonical URL
        item_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]

        item = NewsItem(
            id=f"rss_{item_id}",
            title=title,
            url=url,
            source=source_name,
            source_type="rss",
            published_at=published_at,
            author=author,
            description=clean_description,
            category=category,
            image_url=image_url,
            collected_at=datetime.now(timezone.utc),
        )

        news_items.append(item)

    return news_items