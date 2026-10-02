import os
import sqlite3
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
    exit(1)

REST_URL = f"{SUPABASE_URL}/rest/v1/news_items"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

def migrate():
    print(f"Connecting to SQLite (news.db)...")
    if not os.path.exists("news.db"):
        print("Error: news.db not found!")
        return

    conn = sqlite3.connect("news.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM news_items")
    rows = cursor.fetchall()
    print(f"Found {len(rows)} items in SQLite news.db to migrate to Supabase.")

    batch = []
    batch_size = 50
    total_migrated = 0

    for r in rows:
        item = {
            "id": r["id"],
            "title": r["title"],
            "url": r["url"],
            "source": r["source"],
            "source_type": r["source_type"] if "source_type" in r.keys() else "rss",
            "published_at": r["published_at"] if r["published_at"] else None,
            "author": r["author"] if "author" in r.keys() else None,
            "description": r["description"] if "description" in r.keys() else None,
            "category": r["category"] if "category" in r.keys() else None,
            "image_url": r["image_url"] if "image_url" in r.keys() else None,
            "is_duplicate": bool(r["is_duplicate"]) if "is_duplicate" in r.keys() and r["is_duplicate"] is not None else False,
            "duplicate_of": r["duplicate_of"] if "duplicate_of" in r.keys() else None,
            "primary_role": r["primary_role"] if "primary_role" in r.keys() else None,
            "confidence": float(r["confidence"]) if "confidence" in r.keys() and r["confidence"] is not None else 0.0,
            "researcher_score": float(r["researcher_score"]) if "researcher_score" in r.keys() and r["researcher_score"] is not None else 0.0,
            "engineer_score": float(r["engineer_score"]) if "engineer_score" in r.keys() and r["engineer_score"] is not None else 0.0,
            "startup_score": float(r["startup_score"]) if "startup_score" in r.keys() and r["startup_score"] is not None else 0.0,
            "noise_score": float(r["noise_score"]) if "noise_score" in r.keys() and r["noise_score"] is not None else 0.0,
            "irrelevant_score": float(r["irrelevant_score"]) if "irrelevant_score" in r.keys() and r["irrelevant_score"] is not None else 0.0,
            "collected_at": r["collected_at"] if "collected_at" in r.keys() and r["collected_at"] else None,
        }
        batch.append(item)

        if len(batch) >= batch_size:
            res = requests.post(REST_URL, headers=HEADERS, json=batch)
            if res.status_code in [200, 201]:
                total_migrated += len(batch)
                print(f"   Migrated {total_migrated}/{len(rows)} items to Supabase...")
            else:
                print(f"   Error batch insert: HTTP {res.status_code} - {res.text}")
            batch = []

    if batch:
        res = requests.post(REST_URL, headers=HEADERS, json=batch)
        if res.status_code in [200, 201]:
            total_migrated += len(batch)
            print(f"   Migrated {total_migrated}/{len(rows)} items to Supabase...")
        else:
            print(f"   Error final batch insert: HTTP {res.status_code} - {res.text}")

    print(f"\nMigration complete! Total items uploaded: {total_migrated}")

if __name__ == "__main__":
    migrate()
