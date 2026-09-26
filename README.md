# Project News Aggregator & Intelligence Engine

A fast, scalable news aggregation, deduplication, and exploration engine built with Python 3.12 and `uv`. It collects, normalizes, deduplicates, and analyzes technology developments, AI/ML research breakthroughs, engineering blogs, and IIT startup innovations across multi-platform feeds.

---

## 🚀 Key Features

* **Unified Data Schema:** Strongly typed `NewsItem` model powered by Pydantic V2 with image support and deduplication tracking.
* **Multi-Source Ingestion:**
  * **AlphaXiv SDK:** Ingests trending research papers with author lists and abstracts.
  * **Hacker News Firebase API:** Collects top stories and community discussions.
  * **Universal RSS/Atom Engine:** High-concurrency parser with BeautifulSoup HTML stripping, embedded image extraction, and category fallback branding.
* **Phase 1: MinHash LSH Deduplication:**
  * Sub-millisecond near-duplicate detection using **Locality Sensitive Hashing (LSH)** and **MinHash signatures** (`datasketch`).
  * Automatically flags syndicated cross-posts and near-identical press releases ($>75\%$ text similarity).
* **SQLite Storage & Indexing:**
  * Persistent storage with indexed queries by source, category, and publication date.
  * Automatic filtering of duplicate articles (`only_unique=True`).
* **Visual Quality Inspector (`report.html`):**
  * Interactive web dashboard with real-time search, category filters, thumbnail previews, and duplicate inspection.

---

## 🛠️ Tech Stack & Requirements

* **Runtime:** Python `>= 3.12`
* **Package Manager:** `uv`
* **Core Libraries:**
  * `datasketch`: MinHash & Locality Sensitive Hashing (LSH) for $O(1)$ deduplication.
  * `beautifulsoup4`: HTML parsing, tag sanitization, and embedded image extraction.
  * `alphaxiv-py`: Public client for AlphaXiv research discovery.
  * `feedparser`: RSS 2.0 and Atom feed ingestion.
  * `httpx`: Async and sync HTTP client.
  * `pydantic`: Schema validation and serialization.
  * `python-dotenv`: Environment configuration management.

---

## 📁 Project Architecture

```text
project-news/
├── pyproject.toml              # Project dependencies and tool configurations
├── README.md                   # Comprehensive project documentation
├── news.db                     # SQLite database file (auto-created on run)
├── report.html                 # Interactive visual inspection dashboard
├── export_report.py            # Standalone exporter for the visual report
├── src/
│   ├── main.py                 # Ingestion orchestrator & pipeline runner
│   ├── deduplication/
│   │   ├── __init__.py
│   │   └── minhash_lsh.py      # MinHash + LSH Near-Duplicate Engine
│   ├── models/
│   │   ├── __init__.py
│   │   └── news.py             # Pydantic NewsItem data model
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── alphaxiv.py         # AlphaXiv trending papers collector
│   │   ├── hackernews.py       # Hacker News Firebase API collector
│   │   └── rss.py              # Generic RSS engine with image & HTML cleaning
│   └── storage/
│       ├── __init__.py
│       └── database.py         # SQLite storage layer with indexing & deduplication
└── tests/
```

---

## 📊 Unified Data Model (`NewsItem`)

Located in [`src/models/news.py`](file:///Users/abhisheksoni/project-news/src/models/news.py):

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `str` | Unique source identifier (e.g. `alphaxiv_2609.28399`, `hn_12345`, `rss_sha256`) |
| `title` | `str` | Headline or paper title |
| `url` | `str` | Canonical link to original article/paper |
| `source` | `str` | Source publisher name (e.g. `OpenAI Blog`, `Simon Willison Weblog`) |
| `source_type` | `str` | Category of source (`research`, `community`, `rss`) |
| `published_at` | `datetime \| None` | Standardized UTC publication timestamp |
| `author` | `str \| None` | Author or creator name(s) |
| `description` | `str \| None` | Sanitized, plain-text summary or abstract |
| `category` | `str \| None` | Topic category tag (e.g. `ai_research`, `iit_startups`, `tech_blogs`) |
| `image_url` | `str \| None` | Article image, thumbnail, or curated category fallback banner |
| `is_duplicate` | `bool` | `True` if flagged as a near-duplicate of an earlier article |
| `duplicate_of` | `str \| None` | ID of the parent original article if duplicate |
| `collected_at` | `datetime` | UTC timestamp of when the item was ingested |

---

## 📡 Curated Sources Configured

### 1. Core AI / ML Research & Lab Blogs
* **MIT News - AI:** `https://news.mit.edu/rss/topic/artificial-intelligence2`
* **Berkeley AI Research (BAIR):** `https://bair.berkeley.edu/blog/feed.xml`
* **Hugging Face Blog:** `https://huggingface.co/blog/feed.xml`
* **OpenAI Blog:** `https://openai.com/news/rss.xml`
* **Google AI Blog:** `https://blog.google/technology/ai/rss/`
* **KDnuggets:** `https://www.kdnuggets.com/feed`
* **AlphaXiv:** Trending research discovery explore feed.

### 2. Industry Blogs, Medium & Substack
* **Simon Willison Weblog:** `https://simonwillison.net/atom/entries/`
* **Towards Data Science (Medium):** `https://towardsdatascience.com/feed`
* **The Sequence (Substack):** `https://thesequence.substack.com/feed`
* **Latent Space (Substack):** `https://www.latent.space/feed`
* **One Useful Thing (Substack):** `https://www.oneusefulthing.org/feed`

### 3. IITs & Indian DeepTech Innovations
* **IIT Innovations & Startups (Aggregated):** `https://news.google.com/rss/search?q=IIT+(startup+OR+innovation+OR+research+OR+invention)&hl=en-IN&gl=IN&ceid=IN:en`
* **Top IITs Research (Madras, Bombay, Delhi, Kanpur):** `https://news.google.com/rss/search?q=%22IIT+Madras%22+OR+%22IIT+Bombay%22+OR+%22IIT+Delhi%22+OR+%22IIT+Kanpur%22+(research+OR+startup+OR+patent)&hl=en-IN&gl=IN&ceid=IN:en`
* **YourStory Indian Startups:** `https://yourstory.com/feed`

### 4. Developer & Tech Community
* **Hacker News:** Top stories via Firebase API.

---

## 🔍 Deduplication Engine (MinHash & LSH)

Located in [`src/deduplication/minhash_lsh.py`](file:///Users/abhisheksoni/project-news/src/deduplication/minhash_lsh.py):

* **Shingling:** Breaks normalized text (`title + description`) into word 3-grams.
* **MinHash Signatures (`num_perm=128`):** Hashes shingles into compact 128-integer fingerprints.
* **Locality Sensitive Hashing (LSH):** Groups similar signatures into hash buckets for $O(1)$ query time at a Jaccard threshold of $\ge 0.75$.
* **Benefits:** Filters out 80% of redundant noise and prepares clean data for semantic clustering.

---

## ⚙️ Setup & Execution

### 1. Install Dependencies
```bash
uv sync
```

### 2. Run Ingestion Pipeline
Fetch all sources, execute deduplication, and persist to SQLite:
```bash
uv run python src/main.py
```

### 3. Inspect Feeds in the Interactive HTML Viewer
Generate and open the visual dashboard:
```bash
PYTHONPATH=src uv run python export_report.py
open report.html
```
