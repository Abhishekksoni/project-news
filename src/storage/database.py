"""SQLite database storage layer for Project News with deduplication support."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.news import NewsItem

# Default database location in the project root
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "news.db"


def get_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Create and return a SQLite connection configured for row access."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    """Initialize the SQLite database and create tables if they do not exist."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS news_items (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                source TEXT NOT NULL,
                source_type TEXT NOT NULL,
                published_at TEXT,
                author TEXT,
                description TEXT,
                category TEXT,
                image_url TEXT,
                is_duplicate INTEGER DEFAULT 0,
                duplicate_of TEXT,
                primary_role TEXT,
                confidence REAL DEFAULT 0.0,
                researcher_score REAL DEFAULT 0.0,
                engineer_score REAL DEFAULT 0.0,
                startup_score REAL DEFAULT 0.0,
                noise_score REAL DEFAULT 0.0,
                irrelevant_score REAL DEFAULT 0.0,
                collected_at TEXT NOT NULL
            )
            """
        )

        # Migration helpers
        cursor.execute("PRAGMA table_info(news_items)")
        columns = {row["name"] for row in cursor.fetchall()}
        if "is_duplicate" not in columns:
            cursor.execute(
                "ALTER TABLE news_items ADD COLUMN is_duplicate INTEGER DEFAULT 0"
            )
        if "duplicate_of" not in columns:
            cursor.execute(
                "ALTER TABLE news_items ADD COLUMN duplicate_of TEXT"
            )
        if "primary_role" not in columns:
            cursor.execute(
                "ALTER TABLE news_items ADD COLUMN primary_role TEXT"
            )
        if "confidence" not in columns:
            cursor.execute(
                "ALTER TABLE news_items ADD COLUMN confidence REAL DEFAULT 0.0"
            )
        if "researcher_score" not in columns:
            cursor.execute(
                "ALTER TABLE news_items ADD COLUMN researcher_score REAL DEFAULT 0.0"
            )
        if "engineer_score" not in columns:
            cursor.execute(
                "ALTER TABLE news_items ADD COLUMN engineer_score REAL DEFAULT 0.0"
            )
        if "startup_score" not in columns:
            cursor.execute(
                "ALTER TABLE news_items ADD COLUMN startup_score REAL DEFAULT 0.0"
            )
        if "noise_score" not in columns:
            cursor.execute(
                "ALTER TABLE news_items ADD COLUMN noise_score REAL DEFAULT 0.0"
            )
        if "irrelevant_score" not in columns:
            cursor.execute(
                "ALTER TABLE news_items ADD COLUMN irrelevant_score REAL DEFAULT 0.0"
            )

        # Indexes for fast querying
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_source ON news_items (source)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_category ON news_items (category)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_primary_role ON news_items (primary_role)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_published_at ON news_items (published_at DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_is_duplicate ON news_items (is_duplicate)"
        )
        conn.commit()


def save_news_item(item: NewsItem, db_path: Path | str = DEFAULT_DB_PATH) -> bool:
    """
    Save a single NewsItem.
    Returns True if a new record was inserted, False if it already existed.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO news_items (
                id, title, url, source, source_type,
                published_at, author, description, category, image_url,
                is_duplicate, duplicate_of, primary_role, confidence,
                researcher_score, engineer_score, startup_score, noise_score, irrelevant_score, collected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.id,
                item.title,
                item.url,
                item.source,
                item.source_type,
                item.published_at.isoformat() if item.published_at else None,
                item.author,
                item.description,
                item.category,
                item.image_url,
                1 if item.is_duplicate else 0,
                item.duplicate_of,
                item.primary_role,
                item.confidence,
                item.researcher_score,
                item.engineer_score,
                item.startup_score,
                getattr(item, 'noise_score', 0.0) or getattr(item, 'irrelevant_score', 0.0),
                getattr(item, 'noise_score', 0.0) or getattr(item, 'irrelevant_score', 0.0),
                item.collected_at.isoformat(),
            ),
        )
        conn.commit()
        return cursor.rowcount > 0


def save_news_items(
    items: list[NewsItem], db_path: Path | str = DEFAULT_DB_PATH
) -> int:
    """
    Save a batch of NewsItems using INSERT OR REPLACE.
    Returns the number of newly inserted items.
    """
    if not items:
        return 0

    init_db(db_path)

    records = [
        (
            item.id,
            item.title,
            item.url,
            item.source,
            item.source_type,
            item.published_at.isoformat() if item.published_at else None,
            item.author,
            item.description,
            item.category,
            item.image_url,
            1 if item.is_duplicate else 0,
            item.duplicate_of,
            item.primary_role,
            item.confidence,
            item.researcher_score,
            item.engineer_score,
            item.startup_score,
            getattr(item, 'noise_score', 0.0) or getattr(item, 'irrelevant_score', 0.0),
            getattr(item, 'noise_score', 0.0) or getattr(item, 'irrelevant_score', 0.0),
            item.collected_at.isoformat(),
        )
        for item in items
    ]

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT OR REPLACE INTO news_items (
                id, title, url, source, source_type,
                published_at, author, description, category, image_url,
                is_duplicate, duplicate_of, primary_role, confidence,
                researcher_score, engineer_score, startup_score, noise_score, irrelevant_score, collected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )
        conn.commit()
        inserted = cursor.rowcount if cursor.rowcount != -1 else len(items)

    # Automatically sync items to Supabase cloud database if configured
    try:
        import os
        import requests
        supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        if supabase_url and supabase_key:
            rest_url = f"{supabase_url}/rest/v1/news_items"
            headers = {
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            }
            sb_records = [
                {
                    "id": item.id,
                    "title": item.title,
                    "url": item.url,
                    "source": item.source,
                    "source_type": item.source_type,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                    "author": item.author,
                    "description": item.description,
                    "category": item.category,
                    "image_url": item.image_url,
                    "is_duplicate": bool(item.is_duplicate),
                    "duplicate_of": item.duplicate_of,
                    "primary_role": item.primary_role,
                    "confidence": float(item.confidence) if item.confidence is not None else 0.0,
                    "researcher_score": float(item.researcher_score) if item.researcher_score is not None else 0.0,
                    "engineer_score": float(item.engineer_score) if item.engineer_score is not None else 0.0,
                    "startup_score": float(item.startup_score) if item.startup_score is not None else 0.0,
                    "noise_score": float(getattr(item, 'noise_score', 0.0) or getattr(item, 'irrelevant_score', 0.0)),
                    "irrelevant_score": float(getattr(item, 'noise_score', 0.0) or getattr(item, 'irrelevant_score', 0.0)),
                    "collected_at": item.collected_at.isoformat() if item.collected_at else datetime.now(UTC).isoformat(),
                }
                for item in items
            ]
            # Chunk in batches of 50
            for i in range(0, len(sb_records), 50):
                chunk = sb_records[i:i + 50]
                requests.post(rest_url, headers=headers, json=chunk, timeout=10)
    except Exception as sb_err:
        print(f"   [Supabase Sync Warning]: {sb_err}")

    return inserted


def _row_to_news_item(row: sqlite3.Row) -> NewsItem:
    """Helper to convert a sqlite3.Row into a Pydantic NewsItem model."""
    published_at = (
        datetime.fromisoformat(row["published_at"])
        if row["published_at"]
        else None
    )
    collected_at = (
        datetime.fromisoformat(row["collected_at"])
        if row["collected_at"]
        else datetime.now(UTC)
    )

    columns = row.keys()
    noise_val = float(row["noise_score"]) if "noise_score" in columns and row["noise_score"] is not None else (
        float(row["irrelevant_score"]) if "irrelevant_score" in columns and row["irrelevant_score"] is not None else 0.0
    )

    return NewsItem(
        id=row["id"],
        title=row["title"],
        url=row["url"],
        source=row["source"],
        source_type=row["source_type"],
        published_at=published_at,
        author=row["author"],
        description=row["description"],
        category=row["category"],
        image_url=row["image_url"],
        is_duplicate=bool(row["is_duplicate"]) if "is_duplicate" in columns else False,
        duplicate_of=row["duplicate_of"] if "duplicate_of" in columns else None,
        primary_role=row["primary_role"] if "primary_role" in columns else None,
        confidence=float(row["confidence"]) if "confidence" in columns and row["confidence"] is not None else 0.0,
        researcher_score=float(row["researcher_score"]) if "researcher_score" in columns and row["researcher_score"] is not None else 0.0,
        engineer_score=float(row["engineer_score"]) if "engineer_score" in columns and row["engineer_score"] is not None else 0.0,
        startup_score=float(row["startup_score"]) if "startup_score" in columns and row["startup_score"] is not None else 0.0,
        noise_score=noise_val,
        irrelevant_score=noise_val,
        collected_at=collected_at,
    )


def get_news_items(
    limit: int | None = None,
    offset: int = 0,
    source: str | None = None,
    category: str | None = None,
    only_unique: bool = True,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> list[NewsItem]:
    """
    Retrieve news items with optional filtering by source, category, and deduplication status.
    If only_unique=True, duplicates are filtered out. If limit is None, all matching items are returned.
    """
    init_db(db_path)

    query = "SELECT * FROM news_items"
    conditions = []
    params: list[str | int] = []

    if only_unique:
        conditions.append("is_duplicate = 0")

    if source:
        conditions.append("source = ?")
        params.append(source)

    if category:
        conditions.append("category = ?")
        params.append(category)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Order by published_at (newest first), falling back to collected_at
    query += " ORDER BY COALESCE(published_at, collected_at) DESC"
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [_row_to_news_item(row) for row in rows]


def get_duplicates(db_path: Path | str = DEFAULT_DB_PATH) -> list[NewsItem]:
    """Retrieve all news items identified as duplicates."""
    init_db(db_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM news_items WHERE is_duplicate = 1 ORDER BY collected_at DESC")
        rows = cursor.fetchall()
        return [_row_to_news_item(row) for row in rows]


def get_news_item_by_id(
    item_id: str, db_path: Path | str = DEFAULT_DB_PATH
) -> NewsItem | None:
    """Retrieve a single news item by its unique ID."""
    init_db(db_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM news_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        return _row_to_news_item(row) if row else None


def get_total_count(db_path: Path | str = DEFAULT_DB_PATH) -> dict[str, int]:
    """Get total count of news items, unique items, and duplicate items."""
    init_db(db_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM news_items")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM news_items WHERE is_duplicate = 1")
        duplicates = cursor.fetchone()[0]

        return {
            "total": total,
            "unique": total - duplicates,
            "duplicates": duplicates,
        }


def get_classified_items_map(
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, dict[str, Any]]:
    """
    Retrieve a mapping of previously classified news item IDs and their cached decision scores.
    Enables incremental ingestion so existing articles are not re-sent to Jev AI.
    """
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, primary_role, confidence, researcher_score, engineer_score, startup_score, noise_score, irrelevant_score
            FROM news_items
            WHERE primary_role IS NOT NULL AND primary_role != ''
            """
        )
        rows = cursor.fetchall()
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            columns = row.keys()
            noise_val = float(row["noise_score"]) if "noise_score" in columns and row["noise_score"] is not None else (
                float(row["irrelevant_score"]) if "irrelevant_score" in columns and row["irrelevant_score"] is not None else 0.0
            )
            result[row["id"]] = {
                "primary_role": row["primary_role"],
                "confidence": float(row["confidence"]) if row["confidence"] is not None else 0.0,
                "researcher_score": float(row["researcher_score"]) if row["researcher_score"] is not None else 0.0,
                "engineer_score": float(row["engineer_score"]) if row["engineer_score"] is not None else 0.0,
                "startup_score": float(row["startup_score"]) if row["startup_score"] is not None else 0.0,
                "noise_score": noise_val,
                "irrelevant_score": noise_val,
            }
        return result
