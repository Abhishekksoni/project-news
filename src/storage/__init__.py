from .database import (
    get_connection,
    get_duplicates,
    get_news_item_by_id,
    get_news_items,
    get_total_count,
    init_db,
    save_news_item,
    save_news_items,
)

__all__ = [
    "get_connection",
    "get_duplicates",
    "get_news_item_by_id",
    "get_news_items",
    "get_total_count",
    "init_db",
    "save_news_item",
    "save_news_items",
]
