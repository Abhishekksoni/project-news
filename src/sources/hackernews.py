from datetime import datetime, timezone
from bs4 import BeautifulSoup
import httpx

from models.news import NewsItem

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

                url = story.get("url")
                if not url:
                    url = f"https://news.ycombinator.com/item?id={story_id}"

                published_at = None
                if story.get("time"):
                    published_at = datetime.fromtimestamp(
                        story["time"],
                        tz=timezone.utc,
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
                    image_url=HN_FALLBACK_IMAGE,
                    collected_at=datetime.now(timezone.utc),
                )

                news_items.append(item)
            except Exception:
                continue

    return news_items