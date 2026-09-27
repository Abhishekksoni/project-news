import asyncio
from concurrent.futures import ThreadPoolExecutor

from deduplication.minhash_lsh import NewsDeduplicator
from sources.alphaxiv import fetch_alphaxiv
from sources.github_trending import fetch_github_trending
from sources.hackernews import fetch_hacker_news
from sources.huggingface import fetch_hf_daily_papers, fetch_hf_trending_models
from sources.rss import fetch_rss
from storage.database import (
    get_news_items,
    get_total_count,
    init_db,
    save_news_items,
)
import sys
from pathlib import Path

# Add project root to sys.path so root modules like export_report are accessible
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from export_report import generate_html_report
except ImportError:
    generate_html_report = None

FEEDS = [
    # 1. Core AI / ML Research & Lab Blogs
    {
        "name": "MIT News - AI",
        "url": "https://news.mit.edu/rss/topic/artificial-intelligence2",
        "category": "ai_research",
    },
    {
        "name": "Berkeley AI Research (BAIR)",
        "url": "https://bair.berkeley.edu/blog/feed.xml",
        "category": "ai_research",
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "category": "ai_research",
    },
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/news/rss.xml",
        "category": "ai_research",
    },
    {
        "name": "Google AI Blog",
        "url": "https://blog.google/technology/ai/rss/",
        "category": "ai_research",
    },
    {
        "name": "KDnuggets",
        "url": "https://www.kdnuggets.com/feed",
        "category": "machine_learning",
    },

    # 2. TechCrunch & VentureBeat (AI, Startups, VC & Deals)
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "category": "startup_innovation",
    },
    {
        "name": "TechCrunch Startups",
        "url": "https://techcrunch.com/category/startups/feed/",
        "category": "startup_innovation",
    },
    {
        "name": "VentureBeat AI & Tech",
        "url": "https://venturebeat.com/feed/",
        "category": "startup_innovation",
    },

    # 3. Top AI Engineering Blogs & Substacks
    {
        "name": "Simon Willison Weblog",
        "url": "https://simonwillison.net/atom/entries/",
        "category": "ai_engineering",
    },
    {
        "name": "Chip Huyen AI Blog",
        "url": "https://huyenchip.com/feed.xml",
        "category": "ai_engineering",
    },
    {
        "name": "Latent Space (Substack)",
        "url": "https://www.latent.space/feed",
        "category": "ai_engineering",
    },
    {
        "name": "Ahead of AI (Sebastian Raschka)",
        "url": "https://magazine.sebastianraschka.com/feed",
        "category": "ai_research",
    },
    {
        "name": "Towards Data Science (Medium)",
        "url": "https://towardsdatascience.com/feed",
        "category": "data_science",
    },

    # 4. IITs & Indian DeepTech / Startup Innovation Feeds
    {
        "name": "IIT Innovations & Startups",
        "url": "https://news.google.com/rss/search?q=IIT+(startup+OR+innovation+OR+research+OR+invention)&hl=en-IN&gl=IN&ceid=IN:en",
        "category": "iit_startups",
    },
    {
        "name": "Top IITs Research (Madras/Bombay/Delhi/Kanpur)",
        "url": "https://news.google.com/rss/search?q=%22IIT+Madras%22+OR+%22IIT+Bombay%22+OR+%22IIT+Delhi%22+OR+%22IIT+Kanpur%22+(research+OR+startup+OR+patent)&hl=en-IN&gl=IN&ceid=IN:en",
        "category": "iit_research",
    },
    {
        "name": "YourStory Indian Startups",
        "url": "https://yourstory.com/feed",
        "category": "indian_startups",
    },
]


def fetch_all_rss(limit_per_feed: int = 6):
    all_items = []
    with ThreadPoolExecutor(max_workers=14) as executor:
        futures = [
            executor.submit(
                fetch_rss,
                feed_url=f["url"],
                source_name=f["name"],
                category=f["category"],
                limit=limit_per_feed,
            )
            for f in FEEDS
        ]
        for f in futures:
            try:
                items = f.result()
                all_items.extend(items)
            except Exception as e:
                print(f"Error fetching feed: {e}")
    return all_items


async def collect_all_sources() -> list:
    print(f"1. Fetching {len(FEEDS)} RSS feeds, HF Daily Papers, HF Models, GitHub Trending, AlphaXiv & Hacker News...")

    # Fetch all sources concurrently
    rss_task = asyncio.to_thread(fetch_all_rss, limit_per_feed=6)
    hf_papers_task = fetch_hf_daily_papers(limit=8)
    hf_models_task = fetch_hf_trending_models(limit=8)
    gh_task = asyncio.to_thread(fetch_github_trending, limit=10)
    alphaxiv_task = fetch_alphaxiv(sort="Hot", interval="3 Days", limit=6)
    hn_task = asyncio.to_thread(fetch_hacker_news, limit=12)

    (
        rss_items,
        hf_papers,
        hf_models,
        gh_items,
        alphaxiv_items,
        hn_items,
    ) = await asyncio.gather(
        rss_task,
        hf_papers_task,
        hf_models_task,
        gh_task,
        alphaxiv_task,
        hn_task,
    )

    all_raw_items = rss_items + hf_papers + hf_models + gh_items + alphaxiv_items + hn_items
    print(f"   Collected {len(all_raw_items)} raw items in total across all feeds.\n")
    return all_raw_items


def main():
    init_db()

    # Step 1: Collect from all sources
    raw_items = asyncio.run(collect_all_sources())

    # Step 2: MinHash LSH Deduplication
    print("2. Running MinHash LSH Near-Duplicate Detection (threshold=0.75)...")
    deduplicator = NewsDeduplicator(threshold=0.75)
    uniques, duplicates = deduplicator.deduplicate_batch(raw_items)

    print(f"   Unique Articles:    {len(uniques)}")
    print(f"   Duplicate Articles: {len(duplicates)}\n")

    # Step 3: Fast 4-Role Decision Classification (Rune 26B-A4B)
    print("3. Scoring articles across 4 roles (Researcher, Engineer, Startup, Irrelevant)...")
    from classification.rune_client import classify_with_rune

    def _score_item(item):
        if not item.is_duplicate:
            res = classify_with_rune(item.title, item.description or "", item.source)
            item.primary_role = res.primary_role
            item.confidence = res.confidence
            item.researcher_score = res.researcher_score
            item.engineer_score = res.engineer_score
            item.startup_score = res.startup_score
            item.irrelevant_score = res.irrelevant_score
        return item

    with ThreadPoolExecutor(max_workers=8) as executor:
        raw_items = list(executor.map(_score_item, raw_items))

    # Step 4: Save to SQLite
    print("4. Persisting articles into SQLite database...")
    save_news_items(raw_items)
    stats = get_total_count()
    print(
        f"   Database Status -> Total: {stats['total']} | Unique: {stats['unique']} | Duplicates: {stats['duplicates']}\n"
    )

    # Step 5: Regenerate HTML Report
    if generate_html_report:
        print("5. Generating interactive HTML quality dashboard (report.html)...")
        report_path = generate_html_report("report.html")
        print(f"   Interactive Dashboard ready at: {report_path}\n")

    # Step 6: Show Latest Stream Summary
    unique_db_items = get_news_items(limit=10, only_unique=True)
    print("=" * 70)
    print(f"LATEST UNIQUE NEWS STREAM ({len(unique_db_items)} displayed)")
    print("=" * 70)
    for i, item in enumerate(unique_db_items, start=1):
        print(f"\n{i}. [{item.source}] {item.title}")
        print(f"   Role: {item.primary_role} (Conf: {int(item.confidence * 100)}%) | Category: {item.category}")
        print(f"   URL: {item.url}")
        if item.published_at:
            print(f"   Date: {item.published_at.strftime('%Y-%m-%d %H:%M')}")
        if item.description:
            print(f"   Description: {item.description[:120]}...")


if __name__ == "__main__":
    main()