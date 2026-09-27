"""Hugging Face Daily Papers and Trending Models collector with detailed README extraction."""

import asyncio
from datetime import datetime, timezone
import hashlib
import re
from typing import Any
from bs4 import BeautifulSoup
import httpx

from models.news import NewsItem

HF_PAPERS_API = "https://huggingface.co/api/daily_papers"
HF_TRENDING_MODELS_API = "https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=10"
FALLBACK_HF_IMAGE = "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=800&auto=format&fit=crop&q=60"


def _clean_readme_description(raw_md: str) -> str | None:
    """Extract the first meaningful, human-written description from a Hugging Face model README and strip all markdown artifacts."""
    if not raw_md or not raw_md.strip():
        return None

    # 1. Remove YAML frontmatter
    text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", raw_md, flags=re.DOTALL)

    # 2. Parse HTML tags (stripping script/img/svg)
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup(["script", "style", "img", "svg"]):
        tag.decompose()
    text = soup.get_text(separator=" ")

    # 3. Clean markdown syntax and badges
    text = re.sub(r"\[!\[.*?\]\(.*?\)\]\(.*?\)", "", text)  # nested badges
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)              # images
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)          # links to plain text
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)    # code blocks
    text = re.sub(r"`([^`]+)`", r"\1", text)                 # inline code

    # 4. Remove blockquotes, backslashes, bold/italic markers, and stray symbols
    text = re.sub(r"(^|\s)>\s*", r"\1 ", text)              # blockquotes '>'
    text = re.sub(r"\\([~*_\-\[\]\(\)])", r"\1", text)       # escaped symbols like \~
    text = text.replace("\\", "")                            # stray backslashes
    text = re.sub(r"\*{1,3}", "", text)                      # bold / italics ** or *
    text = re.sub(r"_{1,3}", "", text)                       # bold / italics __ or _
    text = re.sub(r"[#~`>]", "", text)                       # headers, tildes, backticks, quotes

    # 5. Filter and select descriptive paragraphs
    paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 30]
    valid_paras = []
    for p in paragraphs:
        p_clean = re.sub(r"\s+", " ", p).strip()
        # Skip headers, licenses, install instructions, table rows
        if p_clean.startswith(("|", "©", "License:", "Tags:", "pip install", "git clone", "python -m", "http")):
            continue
        if len(p_clean) > 35:
            valid_paras.append(p_clean)

    if valid_paras:
        combined = " ".join(valid_paras[:2])
        # Final clean
        combined = re.sub(r"\s+", " ", combined).strip()
        if len(combined) > 340:
            combined = combined[:340].rsplit(" ", 1)[0] + "..."
        return combined

    return None


async def _fetch_single_model_description(client: httpx.AsyncClient, model_id: str) -> str | None:
    """Fetch and parse model README.md asynchronously."""
    readme_url = f"https://huggingface.co/{model_id}/raw/main/README.md"
    try:
        resp = await client.get(readme_url, timeout=6.0)
        if resp.status_code == 200:
            return _clean_readme_description(resp.text)
    except Exception:
        pass
    return None


async def fetch_hf_daily_papers(limit: int = 10) -> list[NewsItem]:
    """Fetch top daily research papers curated on Hugging Face."""
    news_items = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(HF_PAPERS_API)
            if resp.status_code != 200:
                return []
            data = resp.json()

            for item in data[:limit]:
                paper = item.get("paper", {})
                title = paper.get("title", "").strip()
                summary = paper.get("summary", "").strip()
                arxiv_id = paper.get("id", "")
                authors_list = [a.get("name", "") for a in paper.get("authors", []) if a.get("name")]
                author_str = ", ".join(authors_list[:3]) if authors_list else "Hugging Face Daily Papers"
                upvotes = paper.get("upvotes", 0)

                url = f"https://huggingface.co/papers/{arxiv_id}" if arxiv_id else f"https://arxiv.org/abs/{arxiv_id}"
                
                # Image thumbnail if provided by HF media
                media_url = item.get("mediaUrl") or item.get("thumbnail") or FALLBACK_HF_IMAGE
                
                # Published date
                pub_date_str = paper.get("publishedAt")
                published_at = datetime.now(timezone.utc)
                if pub_date_str:
                    try:
                        published_at = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                    except Exception:
                        pass

                clean_desc = summary if summary else f"Paper with {upvotes} community upvotes on Hugging Face."
                if len(clean_desc) > 350:
                    clean_desc = clean_desc[:350] + "..."

                item_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]

                news_items.append(
                    NewsItem(
                        id=f"hf_paper_{item_id}",
                        title=title,
                        url=url,
                        source="Hugging Face Daily Papers",
                        source_type="api",
                        published_at=published_at,
                        author=author_str,
                        description=clean_desc,
                        category="ai_research",
                        image_url=media_url,
                        collected_at=datetime.now(timezone.utc),
                    )
                )
    except Exception as e:
        print(f"[HF Daily Papers Error] {e}")

    return news_items


async def fetch_hf_trending_models(limit: int = 10) -> list[NewsItem]:
    """Fetch top trending AI open-weights models and checkpoints with real descriptions."""
    news_items = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(HF_TRENDING_MODELS_API)
            if resp.status_code != 200:
                return []
            models_data = resp.json()

            selected_models = models_data[:limit]

            # Fetch READMEs in parallel
            tasks = [
                _fetch_single_model_description(client, m.get("id", ""))
                for m in selected_models
            ]
            descriptions = await asyncio.gather(*tasks)

            for m, real_desc in zip(selected_models, descriptions):
                model_id = m.get("id", "")
                if not model_id:
                    continue
                downloads = m.get("downloads", 0)
                likes = m.get("likes", 0)
                pipeline = m.get("pipeline_tag", "AI Model")
                author = m.get("author", "Open Source AI")

                url = f"https://huggingface.co/{model_id}"
                title = f"{model_id} ({pipeline.replace('-', ' ').title()})"

                # Use real model README description, or fallback to metadata stats
                stats_line = f"{downloads:,} downloads · {likes:,} likes · {pipeline.replace('-', ' ').title()}"
                if real_desc:
                    final_desc = f"{real_desc} [{stats_line}]"
                else:
                    final_desc = f"Trending open-weights model on Hugging Face Hub with {stats_line}."

                item_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]

                news_items.append(
                    NewsItem(
                        id=f"hf_model_{item_id}",
                        title=title,
                        url=url,
                        source="Hugging Face Model Hub",
                        source_type="hf_model",
                        published_at=datetime.now(timezone.utc),
                        author=author,
                        description=final_desc,
                        category="ai_engineering",
                        image_url=FALLBACK_HF_IMAGE,
                        collected_at=datetime.now(timezone.utc),
                    )
                )
    except Exception as e:
        print(f"[HF Trending Models Error] {e}")

    return news_items
