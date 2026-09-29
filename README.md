# Project News: Multi-Source Aggregator & 4-Role AI Intelligence Pipeline

A lightweight, high-performance news aggregation, deduplication, and AI-powered decision intelligence pipeline built with Python 3.12, `uv`, SQLite, and **TypeSafe AI Jev System One** (`jev-latest`).

It ingests technical news, preprints, code repositories, and foundation models across multi-platform sources, applies batch-level MinHash LSH deduplication, classifies stories across 4 audience roles using Jev AI with zero-cost incremental DB caching, and generates an interactive quality dashboard (`report.html`).

---

## 🏗️ Architecture & Pipeline Flow

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                Multi-Platform Feeds                                    │
│  arXiv / AlphaXiv • Hugging Face Papers & Models • GitHub Trending • Hacker News • RSS │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ (Async & ThreadPool Ingestion)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        MinHash LSH Batch Deduplication                                 │
│                   Jaccard Similarity ≥ 0.75 • SHA-256 Stable IDs                       │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ (Unique Articles)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                     Incremental Database Classification Cache                          │
│               • Existing in DB: Hydrate scores instantly ($0.00, 0 API calls)          │
│               • Brand New Articles: Score via TypeSafe Jev AI (jev-latest)             │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ (4-Role Probabilities: Researcher, Engineer, Startups, Noise)
                                            ▼
┌───────────────────────────────────────────┴────────────────────────────────────────────┐
│      SQLite Database (news.db)            │     Visual Quality Dashboard (report.html) │
│      Indexed storage with schema migrator │     Dual timestamps, role tabs & scores    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 4-Role Decision Taxonomy & AI Prompt Rubrics

Articles are evaluated autonomously by **TypeSafe AI Jev (`jev-latest`)** using dedicated prompt criteria for each role:

1. **`ai_researcher` (🔬 AI_ML Researcher):**
   - **Focus:** Scientific AI/ML research, theory, novel neural network architectures, mathematical loss formulations, training dynamics, scaling laws, benchmark evaluations, reinforcement learning theory, mechanistic interpretability, and academic preprints (arXiv, AlphaXiv, NeurIPS, ICML).
2. **`ai_engineer` (🧑‍💻 Software / AI Engineer):**
   - **Focus:** Practical software engineering and AI implementation, developer tooling, open-source repositories, Python packages, APIs, SDKs, LLM frameworks (LangChain, LlamaIndex), agent orchestration, inference acceleration & runtimes (vLLM, Ollama, llama.cpp, TensorRT), quantization, Docker/K8s, and production software architecture.
3. **`startup_innovations` (🚀 Innovation and Startups):**
   - **Focus:** Tech startups, venture capital funding rounds (Seed, Series A-D, IPOs), commercial AI product launches, founder stories, entrepreneurship, mergers & acquisitions, enterprise partnerships, business model innovations, executive moves, and commercial tech industry trends.
4. **`noise` (🗑️ Noise / Off-Topic):**
   - **Focus:** Content with no meaningful or direct value to researchers, engineers, or founders (e.g. general gadget gossip, entertainment, sports, politics, clickbait, repetitive or low-information content). Automatically excluded from the default "All Stories" view in the dashboard.

---

## ⚡ Key Features & Engineering Highlights

* **Autonomous Model Decisions (No Hardcoded Categories):** Feeds contain no pre-assigned categories. The decision engine evaluates each article purely based on title, clean description ($\le 350$ chars), source, and prompt rubrics.
* **Incremental Ingestion (Zero-Cost Re-runs):** Before calling the API, `get_classified_items_map()` checks SQLite. Previously classified articles hydrate scores from DB cache with $0.00 cost and 0 API calls. Only brand-new articles are sent to the model.
* **Cost-Efficient Unit Economics:** Jev System One charges $0.042 / MTok input with free output tokens, resulting in ~**$0.0073 USD (~₹0.61 INR) for a 250+ article batch** (< 1¢).
* **Universal OpenGraph Image Extraction:** Automatic scraping of high-res hero banners (`og:image` / `twitter:image`) for TechCrunch, MIT News, and lab blogs that lack RSS media enclosures.
* **Dual Timestamps:** Tracks both **Published Time** (from upstream feed) and **Fetched Time** (when ingested into Project News).

---

## 📊 Database Schema (`news_items` Table)

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `TEXT PRIMARY KEY` | Stable hash ID (`rss_<hash>`, `hf_paper_<id>`, `hn_<id>`, `gh_<hash>`, etc.) |
| `title` | `TEXT` | Article / repository / model title |
| `url` | `TEXT` | Canonical target URL |
| `source` | `TEXT` | Source publisher name (e.g. *TechCrunch AI*, *AlphaXiv*, *OpenAI Blog*) |
| `source_type` | `TEXT` | Channel type (`rss`, `hf_paper`, `hf_model`, `github_repo`, `alphaxiv`, `hackernews`) |
| `published_at` | `TEXT` | ISO publication timestamp from upstream source |
| `author` | `TEXT` | Author, creator, or organization attribution |
| `description` | `TEXT` | Plain-text content excerpt (capped at ~350 chars with ellipsis) |
| `category` | `TEXT` | Legacy category field (optional) |
| `image_url` | `TEXT` | OpenGraph hero image or thumbnail banner |
| `is_duplicate` | `INTEGER` | `0` = unique, `1` = duplicate |
| `duplicate_of` | `TEXT` | Parent article ID if duplicate |
| `primary_role` | `TEXT` | Winning audience role (`ai_researcher`, `ai_engineer`, `startup_innovations`, `noise`) |
| `confidence` | `REAL` | Model confidence score ($0.0 \to 1.0$) |
| `researcher_score`| `REAL` | Calibrated probability for *AI_ML Researcher* |
| `engineer_score`  | `REAL` | Calibrated probability for *Software / AI Engineer* |
| `startup_score`   | `REAL` | Calibrated probability for *Innovation and Startups* |
| `noise_score`     | `REAL` | Calibrated probability for *Noise / Off-Topic* |
| `irrelevant_score`| `REAL` | Backward-compatibility alias for `noise_score` |
| `collected_at`    | `TEXT` | ISO timestamp of database ingestion |

---

## 📁 Repository Layout

```text
project-news/
├── pyproject.toml                     # Project metadata and dependencies (managed via uv)
├── README.md                          # Pipeline documentation & architecture guide
├── news.db                            # SQLite database with automatic migrations
├── report.html                        # Generated interactive quality dashboard
├── export_report.py                   # HTML dashboard compiler (dual timestamps, role tabs)
├── test_jev.py                        # Standalone 4-role decision classification test script
├── .env                               # API keys (TypeSafe AI, AlphaXiv, Hugging Face)
└── src/
    ├── main.py                        # Pipeline orchestrator (Ingest -> Dedup -> Score -> Persist -> Report)
    ├── classification/
    │   ├── __init__.py
    │   ├── taxonomy.py                # 4-role definitions, prompt rubrics, and display names
    │   └── jev_client.py              # TypeSafe AI Jev System One client (POST /v1/systemone)
    ├── deduplication/
    │   ├── __init__.py
    │   └── minhash_lsh.py             # MinHash LSH deduplication module
    ├── models/
    │   ├── __init__.py
    │   └── news.py                    # Pydantic NewsItem model
    ├── sources/                       # Collectors: RSS, AlphaXiv, Hacker News, GitHub, Hugging Face
    │   ├── rss.py                     # Multi-feed RSS parser with OpenGraph hero scraper
    │   ├── alphaxiv.py                # AlphaXiv research feed collector
    │   ├── github_trending.py         # Trending Python & AI repos collector
    │   ├── hackernews.py              # HN Best stories with metadata scraping
    │   └── huggingface.py             # HF Daily Papers & Model Hub README extractors
    └── storage/
        ├── __init__.py
        └── database.py                # SQLite layer with indexing & classification cache
```

---

## ⚙️ Setup & Execution

### 1. Environment Setup

Create a `.env` file in the project root:
```ini
TYPESAFE_API_KEY=your_typesafe_api_key_here
ALPHAXIV_API_KEY=your_alphaxiv_api_key_here
HF_TOKEN=your_huggingface_token_here
```

Install dependencies using `uv`:
```bash
uv sync
```

### 2. Test the 4-Role Classification Engine
Runs a test across 4 sample articles (including off-topic noise detection):
```bash
PYTHONPATH=src uv run python test_jev.py
```

### 3. Run the Full Ingestion Pipeline
Fetches from all sources, deduplicates, caches/scores with Jev AI, persists to SQLite, and updates `report.html`:
```bash
PYTHONPATH=src uv run python src/main.py
```

### 4. Regenerate Dashboard Report
```bash
PYTHONPATH=src uv run python export_report.py
open report.html
```
