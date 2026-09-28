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

    # Decision classification metadata (3 Roles: ai_ml, startup_innovations, noise)
    primary_role: str | None = None
    confidence: float = 0.0
    aiml_score: float = 0.0
    startup_score: float = 0.0
    noise_score: float = 0.0
    # Backward compatibility aliases
    researcher_score: float = 0.0
    engineer_score: float = 0.0
    irrelevant_score: float = 0.0

    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))