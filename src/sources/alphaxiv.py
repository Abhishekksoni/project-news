from datetime import UTC, datetime

from alphaxiv import AlphaXivClient

from models.news import NewsItem

ALPHAXIV_FALLBACK_IMAGE = "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=800&auto=format&fit=crop&q=60"


async def fetch_alphaxiv(
    sort: str = "Hot",
    interval: str = "7 Days",
    limit: int = 10,
) -> list[NewsItem]:
    news_items = []

    async with AlphaXivClient() as client:
        papers = await client.explore.feed(
            sort=sort,
            interval=interval,
            limit=limit,
        )

        for paper in papers:
            authors_str = ", ".join(paper.authors) if paper.authors else None
            categories_str = ", ".join(paper.topics) if paper.topics else "ai_research"
            img = paper.image_url if paper.image_url else ALPHAXIV_FALLBACK_IMAGE

            item = NewsItem(
                id=f"alphaxiv_{paper.paper_id}",
                title=paper.title,
                url=f"https://www.alphaxiv.org/abs/{paper.paper_id}",
                source="AlphaXiv",
                source_type="research",
                published_at=paper.publication_date,
                author=authors_str,
                description=paper.summary or paper.abstract or None,
                category=categories_str,
                image_url=img,
                collected_at=datetime.now(UTC),
            )

            news_items.append(item)

    return news_items