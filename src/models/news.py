from datetime import UTC, datetime

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    id: str
    title: str
    url: str
    source: str
    source_type: str

    published_at: datetime | None = None
    author: str | None = None
    description: str | None = None
    category: str | None = None
    image_url: str | None = None

    # Deduplication metadata
    is_duplicate: bool = False
    duplicate_of: str | None = None

    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))