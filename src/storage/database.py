"""SQLite database storage layer for Project News with deduplication support."""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3

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
                collected_at TEXT NOT NULL
            )
            """
        )

        # Migration helper in case table existed without duplicate columns
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

        # Indexes for fast querying
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_source ON news_items (source)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_category ON news_items (category)"
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
            INSERT OR IGNORE INTO news_items (
                id, title, url, source, source_type,
                published_at, author, description, category, image_url,
                is_duplicate, duplicate_of, collected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                item.collected_at.isoformat(),
            ),
        )
        conn.commit()
        return cursor.rowcount > 0


def save_news_items(
    items: list[NewsItem], db_path: Path | str = DEFAULT_DB_PATH
) -> int:
    """
    Save a batch of NewsItems using INSERT OR IGNORE.
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
            item.collected_at.isoformat(),
        )
        for item in items
    ]

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT OR IGNORE INTO news_items (
                id, title, url, source, source_type,
                published_at, author, description, category, image_url,
                is_duplicate, duplicate_of, collected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )
        conn.commit()
        return cursor.rowcount if cursor.rowcount != -1 else len(items)


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
        else datetime.now(timezone.utc)
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
        is_duplicate=bool(row["is_duplicate"]) if "is_duplicate" in row.keys() else False,
        duplicate_of=row["duplicate_of"] if "duplicate_of" in row.keys() else None,
        collected_at=collected_at,
    )


def get_news_items(
    limit: int = 50,
    offset: int = 0,
    source: str | None = None,
    category: str | None = None,
    only_unique: bool = True,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> list[NewsItem]:
    """
    Retrieve news items with optional filtering by source, category, and deduplication status.
    If only_unique=True, duplicates are filtered out.
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
    query += " ORDER BY COALESCE(published_at, collected_at) DESC LIMIT ? OFFSET ?"
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
