# Project News: Multi-Source Aggregator & Decision Pipeline

A lightweight, single-node news aggregation, deduplication, and classification pipeline built with Python 3.12, `uv`, and SQLite. It ingests technical news, preprints, repositories, and models across multi-platform sources, applies batch-level MinHash LSH deduplication, and persists articles with SQLite indexing and interactive quality dashboard reporting.

---

## 🏗️ Architecture & Pipeline Flow

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Multi-Platform Feeds                            │
│  ArXiv / AlphaXiv • Hugging Face • GitHub • Hacker News • Tech Blogs  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ (Async / ThreadPool Ingestion)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│               MinHash LSH Batch Deduplication (Jaccard ≥ 0.75)         │
│               SHA-256 Canonical URL Primary Key Filter                 │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ (Filtered Unique Articles)
                                   ▼
┌──────────────────────────────────┴─────────────────────────────────────┐
│    SQLite Database (news.db)     │   Visual Quality Dashboard (report.html)
└──────────────────────────────────┴─────────────────────────────────────┘
```

---

## 🎯 Target Audience Roles

1. **`ai_researcher` (🔬 AI_ML Researcher):** Novel ML research papers, deep learning theory, model architectures, mathematical algorithms, training loss formulations, benchmarks, and preprints.
2. **`ai_engineer` (🧑‍💻 Software / AI Engineer):** Practical software engineering, AI engineering, developer tooling, Python packages, APIs, SDKs, LLM frameworks, agent orchestration, inference kernels, runtime deployment, and repositories.
3. **`startup_innovations` (🚀 Innovation and Startups):** Technology startups, venture capital funding, product launches, founder stories, entrepreneurship, acquisitions, commercial AI market developments, business innovations, and industry tech trends.

---

## 📊 Database Schema (`news_items` Table)

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `TEXT PRIMARY KEY` | Stable hash ID (`rss_<hash>`, `hf_paper_<id>`, etc.) |
| `title` | `TEXT` | Article title |
| `url` | `TEXT` | Canonical target URL |
| `source` | `TEXT` | Feed or source publisher name |
| `source_type` | `TEXT` | Ingestion channel (`rss`, `hf_paper`, `hf_model`, `github_repo`, `alphaxiv`, `hackernews`) |
| `published_at` | `TEXT` | ISO publication timestamp |
| `author` | `TEXT` | Author or creator attribution |
| `description` | `TEXT` | Plain-text content excerpt or abstract |
| `category` | `TEXT` | Feed category metadata |
| `image_url` | `TEXT` | Thumbnail, OpenGraph image, or category fallback |
| `is_duplicate` | `INTEGER` | `0` = unique, `1` = duplicate |
| `duplicate_of` | `TEXT` | Parent article ID if duplicate |
| `primary_role` | `TEXT` | Assigned role (`ai_researcher`, `ai_engineer`, `startup_innovations`) |
| `confidence` | `REAL` | Confidence score ($0.0 \to 1.0$) |
| `researcher_score`| `REAL` | Score for *AI_ML Researcher* |
| `engineer_score`  | `REAL` | Score for *Software / AI Engineer* |
| `startup_score`   | `REAL` | Score for *Innovation and Startups* |
| `collected_at`    | `TEXT` | ISO timestamp of database insertion |

---

## 📁 Repository Layout

```text
project-news/
├── pyproject.toml                     # Dependencies and environment config
├── README.md                          # Project documentation
├── news.db                            # SQLite database
├── report.html                        # Visual quality dashboard
├── export_report.py                   # Standalone dashboard generator
├── dataset/
│   ├── train.jsonl                    # Balanced training samples
│   ├── val.jsonl                      # Balanced validation samples
│   ├── test.jsonl                     # Balanced held-out test samples
│   └── audit_review.html              # Interactive visual dataset explorer
├── scripts/
│   ├── build_dataset.py               # Dataset extractor & split generator
│   └── generate_audit_html.py         # Visual audit review HTML compiler
└── src/
    ├── main.py                        # Pipeline orchestrator (Ingest -> Dedup -> Persist -> Report)
    ├── classification/
    │   ├── __init__.py
    │   └── taxonomy.py                # Centralized 3-role label definitions
    ├── deduplication/
    │   ├── __init__.py
    │   └── minhash_lsh.py             # MinHash LSH deduplication module
    ├── models/
    │   ├── __init__.py
    │   └── news.py                    # Pydantic NewsItem model
    ├── sources/                       # Feed-specific collectors (RSS, HF, GitHub, AlphaXiv, HN)
    └── storage/
        ├── __init__.py
        └── database.py                # SQLite layer with indexing
```

---

## ⚙️ Setup & Execution

### 1. Environment Setup
```bash
# Install all dependencies into virtual environment
uv sync
```

### 2. Run the Ingestion Pipeline
Collects from all sources, deduplicates with MinHash LSH, persists to SQLite, and updates `report.html`:
```bash
PYTHONPATH=src uv run python src/main.py
```

### 3. Inspect Dashboard
```bash
open report.html
```
