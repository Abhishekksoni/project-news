"""GitHub Trending AI & Python repositories collector."""

from datetime import datetime, timezone
import hashlib
from bs4 import BeautifulSoup
import httpx

from models.news import NewsItem

GITHUB_TRENDING_URL = "https://github.com/trending/python?since=weekly"
FALLBACK_GITHUB_IMAGE = "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=800&auto=format&fit=crop&q=60"


def fetch_github_trending(limit: int | None = None) -> list[NewsItem]:
    """Fetch weekly (7 days) trending Python and AI repositories from GitHub Trending."""
    news_items = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
            resp = client.get(GITHUB_TRENDING_URL)
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            rows = soup.find_all("article", class_="Box-row")
            if not rows:
                rows = soup.select(".Box-row")

            target_rows = rows if limit is None else rows[:limit]
            for row in target_rows:
                # Title and repo URL
                title_elem = row.find("h2") or row.find("h1")
                if not title_elem:
                    continue
                link_elem = title_elem.find("a")
                if not link_elem:
                    continue

                repo_path = link_elem.get("href", "").strip().strip("/")
                if not repo_path:
                    continue

                repo_url = f"https://github.com/{repo_path}"
                repo_name = repo_path.replace("/", " / ")

                # Description
                desc_elem = row.find("p")
                desc_text = desc_elem.get_text(strip=True) if desc_elem else "No description provided."

                # Star counts / stats
                stars_elem = row.select_one("span.d-inline-block.float-sm-right") or row.select_one("span.float-sm-right")
                stars_today = stars_elem.get_text(strip=True) if stars_elem else ""

                full_desc = f"{desc_text} ({stars_today})" if stars_today else desc_text
                if full_desc and len(full_desc) > 350:
                    full_desc = full_desc[:350].rsplit(" ", 1)[0] + "..."
                author = repo_path.split("/")[0] if "/" in repo_path else "GitHub"

                item_id = hashlib.sha256(repo_url.encode("utf-8")).hexdigest()[:16]

                news_items.append(
                    NewsItem(
                        id=f"gh_{item_id}",
                        title=f"{repo_name}: {desc_text[:90]}" if len(desc_text) > 0 else repo_name,
                        url=repo_url,
                        source="GitHub Trending (Python & AI)",
                        source_type="github_repo",
                        published_at=datetime.now(timezone.utc),
                        author=author,
                        description=full_desc,
                        category="ai_engineering",
                        image_url=FALLBACK_GITHUB_IMAGE,
                        collected_at=datetime.now(timezone.utc),
                    )
                )
    except Exception as e:
        print(f"[GitHub Trending Error] {e}")

    return news_items
