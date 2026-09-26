"""Generic RSS/Atom feed parser with robust image extraction and HTML cleaning."""

from datetime import datetime, timezone
import hashlib
import html
import re

from bs4 import BeautifulSoup
import feedparser

from models.news import NewsItem

# Curated fallback images by category to ensure high visual quality
FALLBACK_IMAGES: dict[str, str] = {
    "ai_research": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=800&auto=format&fit=crop&q=60",
    "iit_startups": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=800&auto=format&fit=crop&q=60",
    "iit_research": "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=800&auto=format&fit=crop&q=60",
    "machine_learning": "https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=800&auto=format&fit=crop&q=60",
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


def _extract_image_url(entry: dict, content_html: str | None, category: str | None) -> str | None:
    """
    Extract best available image from media RSS tags, enclosures, or embedded HTML img tags.
    Falls back to a curated category image if none is found.
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

    # 3. enclosures (e.g. podcasts or direct image links)
    enclosures = entry.get("enclosures")
    if enclosures:
        for enclosure in enclosures:
            if isinstance(enclosure, dict):
                enc_type = enclosure.get("type", "")
                enc_href = enclosure.get("href", "")
                if enc_type.startswith("image/") or enc_href.endswith((".png", ".jpg", ".jpeg", ".webp")):
                    return enc_href

    # 4. Parse embedded <img> tag in HTML content/summary
    if content_html:
        soup = BeautifulSoup(content_html, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            src = img["src"]
            if src.startswith("http"):
                return src

    # 5. Fallback curated category image
    return FALLBACK_IMAGES.get(category or "default", FALLBACK_IMAGES["default"])


def fetch_rss(
    feed_url: str,
    source_name: str,
    category: str | None = None,
    limit: int = 20,
) -> list[NewsItem]:
    feed = feedparser.parse(
        feed_url,
        agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)",
    )

    news_items = []

    for entry in feed.entries[:limit]:
        title = entry.get("title", "").strip()
        url = entry.get("link", "").strip()

        if not title or not url:
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

        # Raw HTML content sources (summary vs content)
        raw_summary = entry.get("summary", "")
        raw_content = ""
        if "content" in entry and entry["content"]:
            raw_content = entry["content"][0].get("value", "")

        combined_html = raw_content or raw_summary

        # Clean plain text description
        clean_description = _clean_html_text(raw_summary or raw_content)

        # If description is identical to title (common in Google News RSS), use snippet or default
        if clean_description and clean_description.lower() == title.lower():
            clean_description = f"Latest update on {title} from {source_name}."

        # Extract image or fallback
        image_url = _extract_image_url(entry, combined_html, category)

        # Author extraction
        author = entry.get("author") or entry.get("dc_creator")

        # Stable ID based on URL
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