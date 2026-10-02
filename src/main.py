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
    },
    {
        "name": "Berkeley AI Research (BAIR)",
        "url": "https://bair.berkeley.edu/blog/feed.xml",
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
    },
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/news/rss.xml",
    },
    {
        "name": "Google AI Blog",
        "url": "https://blog.google/technology/ai/rss/",
    },
    {
        "name": "Microsoft Research Blog",
        "url": "https://www.microsoft.com/en-us/research/blog/feed/",
    },
    {
        "name": "KDnuggets",
        "url": "https://www.kdnuggets.com/feed",
    },

    # 2. TechCrunch & VentureBeat AI Feeds
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
    },

    # 3. Top AI Engineering, Developer & Cloud Feeds
    {
        "name": "NVIDIA Developer Blog",
        "url": "https://developer.nvidia.com/blog/feed",
    },
    {
        "name": "AWS Machine Learning Blog",
        "url": "https://aws.amazon.com/blogs/machine-learning/feed/",
    },
    {
        "name": "Simon Willison Weblog",
        "url": "https://simonwillison.net/atom/entries/",
    },
    {
        "name": "Latent Space (Substack)",
        "url": "https://www.latent.space/feed",
    },
    {
        "name": "Ahead of AI (Sebastian Raschka)",
        "url": "https://magazine.sebastianraschka.com/feed",
    },

    # 4. Medium AI / ML Feeds
    {
        "name": "Towards Data Science (Medium)",
        "url": "https://towardsdatascience.com/feed",
    },
]


def fetch_all_rss(limit_per_feed: int | None = None):
    all_items = []
    with ThreadPoolExecutor(max_workers=14) as executor:
        futures = [
            executor.submit(
                fetch_rss,
                feed_url=f["url"],
                source_name=f["name"],
                category=f.get("category"),
                limit=limit_per_feed,
                max_age_days=7,
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
    print(f"1. Fetching from {len(FEEDS)} RSS feeds, HF Daily Papers, HF Models, GitHub Trending, AlphaXiv & Hacker News (7-day window with safety ceilings)...")

    # Fetch all sources concurrently with 7-day filter and safety ceilings
    rss_task = asyncio.to_thread(fetch_all_rss, limit_per_feed=30)
    hf_papers_task = fetch_hf_daily_papers(limit=25)
    hf_models_task = fetch_hf_trending_models(limit=25)
    gh_task = asyncio.to_thread(fetch_github_trending, limit=25)
    alphaxiv_task = fetch_alphaxiv(sort="Hot", interval="7 Days", limit=30)
    hn_task = fetch_hacker_news(limit=30)

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

    # Step 3: Fast 4-Role Decision Classification (Jev AI with DB Cache)
    print("3. Checking DB cache & scoring new articles across 4 roles using Jev AI...")
    from classification.jev_client import classify_with_jev
    from storage.database import get_classified_items_map

    cached_classifications = get_classified_items_map()
    total_unique = sum(1 for item in raw_items if not item.is_duplicate)
    new_to_score = sum(
        1 for item in raw_items if not item.is_duplicate and item.id not in cached_classifications
    )
    already_cached = total_unique - new_to_score

    print(f"   Total Unique Articles:       {total_unique}")
    print(f"   Already in DB (Cached):      {already_cached} (0 API calls, $0.00)")
    print(f"   Brand New Items to Classify: {new_to_score}\n")

    cached_count = 0
    new_scored_count = 0

    for item in raw_items:
        if not item.is_duplicate:
            # Hugging Face Model Hub and GitHub Repos have dedicated streams and don't need Jev classification
            is_dedicated = (
                item.source in ["Hugging Face Model Hub", "GitHub Trending (Python & AI)"]
                or "github" in item.source.lower()
                or "model hub" in item.source.lower()
            )
            if is_dedicated:
                item.primary_role = "hf_model" if "model hub" in item.source.lower() or "hugging" in item.source.lower() else "github_repo"
                item.confidence = 1.0
                item.researcher_score = 0.0
                item.engineer_score = 0.0
                item.startup_score = 0.0
                item.noise_score = 0.0
                item.irrelevant_score = 0.0
                cached_count += 1
            elif item.id in cached_classifications:
                cached = cached_classifications[item.id]
                item.primary_role = cached["primary_role"]
                item.confidence = cached["confidence"]
                item.researcher_score = cached["researcher_score"]
                item.engineer_score = cached["engineer_score"]
                item.startup_score = cached["startup_score"]
                item.noise_score = cached["noise_score"]
                item.irrelevant_score = cached["irrelevant_score"]
                cached_count += 1
            else:
                res = classify_with_jev(item.title, item.description or "", item.source)
                item.primary_role = res.primary_role
                item.confidence = res.confidence
                item.researcher_score = res.researcher_score
                item.engineer_score = res.engineer_score
                item.startup_score = res.startup_score
                item.noise_score = res.noise_score
                item.irrelevant_score = res.noise_score
                new_scored_count += 1
                if new_scored_count % 25 == 0 or new_scored_count == new_to_score:
                    print(f"   Classified {new_scored_count}/{new_to_score} new articles with Jev AI...")

    print(f"   Completed: {cached_count} loaded from DB cache, {new_scored_count} newly classified with Jev AI.\n")

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
        if item.primary_role:
            print(f"   Role: {item.primary_role} (Conf: {int(item.confidence * 100)}%)")
        print(f"   URL: {item.url}")
        if item.published_at:
            print(f"   Date: {item.published_at.strftime('%Y-%m-%d %H:%M')}")
        if item.description:
            print(f"   Description: {item.description[:120]}...")


if __name__ == "__main__":
    main()