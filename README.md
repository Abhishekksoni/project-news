# Project News Aggregator

A fast, unified news aggregation engine built with Python 3.12 and `uv`. It collects and standardizes technology, AI/ML research breakthroughs, startup developments, and IIT innovations across multiple platforms (Hacker News API, AlphaXiv Explore Feed, and multi-source RSS feeds).

---

## 🚀 Key Features

* **Unified Data Contract:** Standardized `NewsItem` schema powered by Pydantic V2.
* **Multiple Source Adapters:**
  * **AlphaXiv Integration:** Fetches trending AI/ML research papers and metadata directly via the `alphaxiv-py` SDK.
  * **Hacker News API:** Fetches top & new tech community discussions directly from Firebase REST endpoints.
  * **Robust RSS Feed Engine:** High-concurrency RSS parser with custom User-Agent, image extraction (Media RSS, Thumbnails, Enclosures), and UTC datetime normalization.
* **Curated Content Streams:**
  * **Core AI / ML Research:** MIT AI, UC Berkeley BAIR, OpenAI, Google DeepMind, Hugging Face, KDnuggets.
  * **IIT & Indian DeepTech Innovations:** Real-time coverage of inventions, incubation centers, and startups from IIT Madras, IIT Bombay, IIT Delhi, IIT Kanpur, PIB Govt Science & Tech, and YourStory.
* **Concurrent Ingestion:** Parallel batch fetching using Python's `ThreadPoolExecutor` and `asyncio`.

---

## 🛠️ Tech Stack & Requirements

* **Python:** `>= 3.12`
* **Package Manager:** `uv`
* **Core Libraries:**
  * `alphaxiv-py`: Async SDK for AlphaXiv research discovery.
  * `feedparser`: RSS & Atom feed ingestion and normalization.
  * `httpx`: High-performance HTTP client.
  * `pydantic`: Data validation and schema enforcement.
  * `python-dotenv`: Environment configuration management.

---

## 📁 Project Architecture

```text
project-news/
├── pyproject.toml              # Dependencies and project configuration
├── README.md                   # Project documentation
├── news.db                     # SQLite database file (created on init)
├── src/
│   ├── main.py                 # Application runner & feed orchestrator
│   ├── deduplication/
│   │   ├── __init__.py
│   │   └── minhash_lsh.py      # MinHash + LSH Near-Duplicate Detection Engine
│   ├── models/
│   │   ├── __init__.py
│   │   └── news.py             # Pydantic NewsItem data model
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── alphaxiv.py         # AlphaXiv trending papers collector
│   │   ├── hackernews.py       # Hacker News Firebase API collector
│   │   └── rss.py              # Generic RSS engine with image & date parsing
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
| `url` | `str` | Direct link to original article/paper |
| `source` | `str` | Source publisher name (e.g. `AlphaXiv`, `MIT News - AI`, `Hacker News`) |
| `source_type` | `str` | Category of source (`research`, `community`, `rss`) |
| `published_at` | `datetime \| None` | Standardized UTC publication timestamp |
| `author` | `str \| None` | Author(s) or creator names |
| `description` | `str \| None` | Summary, excerpt, or paper abstract |
| `category` | `str \| None` | Topic tag (e.g. `ai_research`, `iit_startups`, `machine_learning`) |
| `image_url` | `str \| None` | Extracted banner or thumbnail image URL |
| `collected_at` | `datetime` | UTC timestamp of when the item was ingested |

---

## 🔌 Ingestion Sources

### 1. AlphaXiv Research Source ([`src/sources/alphaxiv.py`](file:///Users/abhisheksoni/project-news/src/sources/alphaxiv.py))
Connects to the AlphaXiv platform to fetch trending research papers.

* **Function:** `fetch_alphaxiv(sort="Hot", interval="7 Days", limit=10)`
* **Supported Sorts:** `"Hot"` (velocity/trending), `"Likes"`, `"GitHub"`, `"Twitter (X)"`
* **Supported Intervals:** `"3 Days"`, `"7 Days"`, `"30 Days"`, `"90 Days"`, `"All time"`
* **Auth:** Unauthenticated public explore feed (no API key required for public feeds).

### 2. Hacker News Source ([`src/sources/hackernews.py`](file:///Users/abhisheksoni/project-news/src/sources/hackernews.py))
Fetches real-time community discussions from Hacker News.

* **Function:** `fetch_hacker_news(limit=20)`
* **Endpoint:** Official Firebase REST API (`https://hacker-news.firebaseio.com/v0/`)

### 3. Universal RSS Engine ([`src/sources/rss.py`](file:///Users/abhisheksoni/project-news/src/sources/rss.py))
Universal parser capable of reading standard RSS 2.0 and Atom feeds.

* **Function:** `fetch_rss(feed_url, source_name, category=None, limit=20)`
* **Features:**
  * Browser `User-Agent` emulation to prevent 403 blocks.
  * Image extraction from `media:content`, `media:thumbnail`, and `enclosures`.
  * Deterministic 16-character SHA-256 hash IDs derived from URL.

---

## 📡 Curated Feeds Configured

### 1. Core AI / ML Research & Lab Blogs
* **MIT News - AI:** `https://news.mit.edu/rss/topic/artificial-intelligence2`
* **Berkeley AI Research (BAIR):** `https://bair.berkeley.edu/blog/feed.xml`
* **Hugging Face Blog:** `https://huggingface.co/blog/feed.xml`
* **OpenAI Blog:** `https://openai.com/news/rss.xml`
* **Google AI Blog:** `https://blog.google/technology/ai/rss/`
* **KDnuggets:** `https://www.kdnuggets.com/feed`

### 2. IITs & Indian DeepTech / Startup Innovation Feeds
* **IIT Innovations & Startups (Aggregated):** `https://news.google.com/rss/search?q=IIT+(startup+OR+innovation+OR+research+OR+invention)&hl=en-IN&gl=IN&ceid=IN:en`
* **Top IITs Research (Madras, Bombay, Delhi, Kanpur):** `https://news.google.com/rss/search?q=%22IIT+Madras%22+OR+%22IIT+Bombay%22+OR+%22IIT+Delhi%22+OR+%22IIT+Kanpur%22+(research+OR+startup+OR+patent)&hl=en-IN&gl=IN&ceid=IN:en`
* **PIB Science & Technology (Govt of India):** `https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1`
* **YourStory Indian Startups:** `https://yourstory.com/feed`

---

## ⚙️ Setup & Execution

### 1. Install Dependencies
Ensure you have `uv` installed, then run:

```bash
uv sync
```

### 2. Run the Aggregator
Run the main ingestion pipeline:

```bash
uv run python src/main.py
```
