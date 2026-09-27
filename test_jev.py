"""Test script for Jev AI classification across the 3 target user roles."""

import json
import sqlite3
from classification.jev_client import build_jev_request, classify_with_jev


def test_jev_on_sample_news():
    conn = sqlite3.connect("news.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Grab representative samples across research, engineering, and startups
    samples = []
    
    # 1. Research sample (AlphaXiv or BAIR)
    row = c.execute("SELECT * FROM news_items WHERE source LIKE '%AlphaXiv%' OR source LIKE '%BAIR%' LIMIT 1").fetchone()
    if row:
        samples.append(dict(row))

    # 2. Engineering / Tooling sample (Hacker News or Hugging Face)
    row = c.execute("SELECT * FROM news_items WHERE (source LIKE '%Hacker News%' OR source LIKE '%Hugging Face%') AND title LIKE '%wrapper%' OR title LIKE '%LLM%' LIMIT 1").fetchone()
    if row:
        samples.append(dict(row))
    else:
        row = c.execute("SELECT * FROM news_items WHERE source LIKE '%Hacker News%' LIMIT 1").fetchone()
        if row:
            samples.append(dict(row))

    # 3. Startup & Innovation sample (IIT or YourStory)
    row = c.execute("SELECT * FROM news_items WHERE source LIKE '%IIT%' OR source LIKE '%YourStory%' LIMIT 1").fetchone()
    if row:
        samples.append(dict(row))

    print("=" * 80)
    print(" JEV AI (SYSTEM ONE) - 3-ROLE CLASSIFICATION & SCORE TEST")
    print("=" * 80)

    for i, item in enumerate(samples, 1):
        title = item["title"]
        description = item["description"]
        source = item["source"]

        print(f"\n[{i}] ARTICLE: {title}")
        print(f"    Source: {source}")
        print(f"    Snippet: {description[:110]}...")

        # 1. Show Candidate Role Targets
        payload = build_jev_request(title, description, source)
        print("\n    📝 Candidate Roles Evaluated:")
        print(f"       Targets: {payload['parameters']['candidate_labels']}")

        # 2. Run Classification
        result = classify_with_jev(title, description, source)

        print("\n    🎯 JEV DECISION & PROBABILITIES:")
        print(f"       Mode: {'🟢 Live API' if result.is_live_api else '🟡 Local Test Mode'}")
        print(f"       Primary Role:        👉 {result.primary_role.upper()} (Confidence: {result.confidence * 100:.1f}%)")
        print("       Role Probabilities: ", json.dumps(result.role_probabilities))
        print("       Individual Scores (0.0 - 1.0):")
        print(f"         1. 🔬 AI / ML Researcher:       {result.researcher_score:.2f}")
        print(f"         2. 🧑‍💻 AI Engineer / Developer:  {result.engineer_score:.2f}")
        print(f"         3. 🚀 Startup & Innovation:     {result.startup_score:.2f}")
        print("-" * 80)


if __name__ == "__main__":
    test_jev_on_sample_news()
