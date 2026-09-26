from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup

from models.news import NewsItem
from sources.rss import _fetch_og_image

BASE_URL = "https://hacker-news.firebaseio.com/v0"
HN_FALLBACK_IMAGE = "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=800&auto=format&fit=crop&q=60"


def fetch_hacker_news(limit: int = 20) -> list[NewsItem]:
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{BASE_URL}/topstories.json")
        response.raise_for_status()

        story_ids = response.json()[:limit]

        news_items = []

        for story_id in story_ids:
            try:
                response = client.get(f"{BASE_URL}/item/{story_id}.json")
                response.raise_for_status()
                story = response.json()

                if not story or story.get("type") != "story":
                    continue

                raw_url = story.get("url")
                is_external = bool(raw_url and not raw_url.startswith("https://news.ycombinator.com"))
                url = raw_url if raw_url else f"https://news.ycombinator.com/item?id={story_id}"

                published_at = None
                if story.get("time"):
                    published_at = datetime.fromtimestamp(
                        story["time"],
                        tz=UTC,
                    )

                # Clean description from text or points/comments metadata
                raw_text = story.get("text")
                if raw_text:
                    soup = BeautifulSoup(raw_text, "html.parser")
                    description = soup.get_text(separator=" ", strip=True)
                else:
                    points = story.get("score", 0)
                    comments = story.get("descendants", 0)
                    description = f"Hacker News community discussion with {points} points and {comments} comments."

                # Attempt to extract OpenGraph primary image from external link
                image_url = None
                if is_external:
                    image_url = _fetch_og_image(url)

                if not image_url:
                    image_url = HN_FALLBACK_IMAGE

                item = NewsItem(
                    id=f"hn_{story_id}",
                    title=story.get("title", ""),
                    url=url,
                    source="Hacker News",
                    source_type="community",
                    published_at=published_at,
                    author=story.get("by"),
                    description=description,
                    category="tech_community",
                    image_url=image_url,
                    collected_at=datetime.now(UTC),
                )

                news_items.append(item)
            except Exception:
                continue

    return news_items