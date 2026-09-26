import asyncio
from concurrent.futures import ThreadPoolExecutor

from deduplication.minhash_lsh import NewsDeduplicator
from sources.alphaxiv import fetch_alphaxiv
from sources.hackernews import fetch_hacker_news
from sources.rss import fetch_rss
from storage.database import (
    get_news_items,
    get_total_count,
    init_db,
    save_news_items,
)

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

    # 2. Industry Blogs, Substack & Medium
    {
        "name": "Simon Willison Weblog",
        "url": "https://simonwillison.net/atom/entries/",
        "category": "tech_blogs",
    },
    {
        "name": "Towards Data Science (Medium)",
        "url": "https://towardsdatascience.com/feed",
        "category": "data_science",
    },
    {
        "name": "The Sequence (Substack)",
        "url": "https://thesequence.substack.com/feed",
        "category": "ai_research",
    },
    {
        "name": "Latent Space (Substack)",
        "url": "https://www.latent.space/feed",
        "category": "ai_engineering",
    },
    {
        "name": "One Useful Thing (Substack)",
        "url": "https://www.oneusefulthing.org/feed",
        "category": "ai_insights",
    },

    # 3. IITs & Indian DeepTech / Startup Innovation Feeds
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


def fetch_all_rss(limit_per_feed: int = 5):
    all_items = []
    with ThreadPoolExecutor(max_workers=12) as executor:
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
    print(f"1. Fetching {len(FEEDS)} RSS feeds, AlphaXiv, and Hacker News...")

    # Fetch concurrently
    rss_task = asyncio.to_thread(fetch_all_rss, limit_per_feed=5)
    alphaxiv_task = fetch_alphaxiv(sort="Hot", interval="3 Days", limit=5)
    hn_task = asyncio.to_thread(fetch_hacker_news, limit=10)

    rss_items, alphaxiv_items, hn_items = await asyncio.gather(
        rss_task, alphaxiv_task, hn_task
    )

    all_raw_items = rss_items + alphaxiv_items + hn_items
    print(f"   Collected {len(all_raw_items)} raw items in total.\n")
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

    # Step 3: Save to SQLite
    print("3. Persisting articles into SQLite database...")
    save_news_items(raw_items)
    stats = get_total_count()
    print(
        f"   Database Status -> Total: {stats['total']} | Unique: {stats['unique']} | Duplicates: {stats['duplicates']}\n"
    )

    # Step 4: Show Sample Duplicates Detected
    if duplicates:
        print("=" * 70)
        print("SAMPLE DUPLICATES DETECTED:")
        print("=" * 70)
        for i, dup in enumerate(duplicates[:5], start=1):
            parent = next((u for u in uniques if u.id == dup.duplicate_of), None)
            print(f"{i}. Duplicate: [{dup.source}] {dup.title}")
            print(
                f"   Matched To: [{parent.source if parent else 'Stored Item'}] {parent.title if parent else dup.duplicate_of}"
            )
            print()

    # Step 5: Show Latest Stream Summary
    unique_db_items = get_news_items(limit=15, only_unique=True)
    print("=" * 70)
    print(f"LATEST UNIQUE NEWS STREAM ({len(unique_db_items)} displayed)")
    print("=" * 70)
    for i, item in enumerate(unique_db_items, start=1):
        print(f"\n{i}. [{item.source}] {item.title}")
        print(f"   Category: {item.category} | Source Type: {item.source_type}")
        print(f"   URL: {item.url}")
        if item.published_at:
            print(f"   Date: {item.published_at}")
        if item.image_url:
            print(f"   Image: {item.image_url[:80]}...")
        if item.description:
            print(f"   Description: {item.description[:120]}...")


if __name__ == "__main__":
    main()