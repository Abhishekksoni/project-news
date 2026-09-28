# Project News Aggregator & Intelligence Engine

A fast, scalable news aggregation, deduplication, and AI-powered decision intelligence engine built with Python 3.12 and `uv`. It collects, normalizes, deduplicates, classifies, and analyzes technology developments, AI/ML research breakthroughs, engineering blogs, GitHub repositories, Hugging Face models, and startup innovations across 22+ multi-platform feeds.

Powered by a **locally fine-tuned LoRA model** on Apple Silicon Metal GPU (`mps`), based on [`AlexWortega/openjev`](https://huggingface.co/AlexWortega/openjev) (Qwen 3.5 0.8B) with a custom 4-role classification head achieving **83.16% validation accuracy**.

---

## 🚀 Key Features

* **Unified 4-Role Decision Schema:** Strongly typed `NewsItem` model powered by Pydantic V2 with multi-role scoring (`ai_researcher`, `ai_engineer`, `startup_innovations`, `noise`), confidence breakdowns, and duplicate tracking.
* **Multi-Source Ingestion Suite (22+ Feeds):**
  * **Hugging Face Hub & Daily Papers:** Ingests trending open-weight models and daily research papers with asynchronous `README.md` summary extraction (sanitizing Markdown badges and HTML tags).
  * **GitHub Trending (Python & AI):** Scrapes top daily trending repositories with real-time star counts, language tags, and project descriptions.
  * **Hacker News Best Stream:** Fetches top-voted stories from `https://news.ycombinator.com/best`, resolves OpenGraph metadata, and falls back to top substantive community comments.
  * **AlphaXiv SDK:** Ingests trending research preprints with author lists and abstracts.
  * **Top Tier Research & Engineering Blogs:** OpenAI, Google AI, Microsoft Research, NVIDIA Developer, AWS ML, Berkeley BAIR, MIT News, Claude & Anthropic Updates, Medium AI/ML, Simon Willison, Chip Huyen, Latent Space, Sebastian Raschka, and KDnuggets.
  * **Universal RSS / Atom Engine:** High-concurrency parser with BeautifulSoup HTML stripping, social-bot user agents (`Slackbot`/`Discordbot`) to bypass Cloudflare bot guards on OpenAI (`images.ctfassets.net`) and Substack, plus category fallback banners.
* **Sub-Millisecond MinHash LSH Deduplication:**
  * Detects near-duplicate stories and syndicated press releases using **Locality Sensitive Hashing (LSH)** and **MinHash signatures** (`datasketch`, $Jaccard \ge 0.75$).
  * Flags duplicate articles while preserving the original parent reference (`duplicate_of`).
* **Fine-Tuned 4-Role Decision Engine (`AlexWortega/openjev` LoRA):**
  * Local in-process sequence classification running on Apple Silicon Metal GPU (`mps`) or remote OpenJev endpoints.
  * High-accuracy 1-pass inference with calibrated probability distributions across all 4 roles.
* **Interactive Dataset Audit & Label Editor (`dataset/audit_review.html`):**
  * Visual review tool with category filter tabs (`All`, `Research`, `Engineering`, `Startups`, `Noise`).
  * In-place dropdown selector to correct any labels on the fly.
  * Instant export of updated `train.jsonl` and `val.jsonl` splits.
* **SQLite Storage & Query Layer:**
  * Persistent storage with indexed queries by source, category, role, confidence, and publication date.
* **Separated 3-Section Quality Dashboard (`report.html`):**
  * **📰 Curated News & Papers:** Filter by role tabs (`🔬 Research`, `🧑‍💻 Engineer`, `🚀 Startups`, `🗑️ Noise`), publisher, or keyword search with interactive role score progress bars.
  * **🔥 Trending GitHub Repos:** Dedicated repository showcase eliminating clutter from the editorial news feed.
  * **🤗 Trending Hugging Face Models:** Dedicated model hub showcase with clean plain-text descriptions.

---

## 🛠️ Tech Stack & Requirements

* **Runtime:** Python `>= 3.12`
* **Package Manager:** `uv`
* **Acceleration:** Apple Silicon Metal GPU (`mps`) or NVIDIA CUDA (`cuda`)
* **Core Libraries:**
  * `torch` & `transformers`: Neural sequence classification pipeline.
  * `peft`: Parameter-Efficient Fine-Tuning (LoRA) for lightweight local model adapters.
  * `datasketch`: MinHash & Locality Sensitive Hashing (LSH) for $O(1)$ deduplication.
  * `beautifulsoup4`: HTML parsing, tag sanitization, and embedded image extraction.
  * `googlenewsdecoder`: Unpacks Google News redirected URLs into canonical publisher links.
  * `feedparser`: RSS 2.0 and Atom feed ingestion.
  * `httpx`: High-performance asynchronous and synchronous HTTP client.
  * `pydantic`: Schema validation and type serialization.
  * `alphaxiv-py`: Public client for AlphaXiv research discovery.
  * `scikit-learn` & `evaluate`: Evaluation metrics (accuracy, weighted F1).
  * `python-dotenv`: Environment configuration management.

---

## 📁 Project Architecture

```text
project-news/
├── pyproject.toml                     # Dependencies and project configuration
├── README.md                          # Comprehensive project documentation
├── news.db                            # SQLite database file (auto-created on run)
├── report.html                        # Interactive visual inspection dashboard
├── export_report.py                   # Exporter for the 3-section quality dashboard
├── test_jev.py                        # Benchmark & test script for 4-role inference
├── models/
│   └── fine_tuned_openjev_4role/      # Saved LoRA adapter & tokenizer weights (83.16% acc)
├── dataset/
│   ├── train.jsonl                    # 80% training dataset split
│   ├── val.jsonl                      # 20% validation dataset split
│   └── audit_review.html              # Visual category filter and dataset label editor
├── scripts/
│   ├── build_dataset.py               # Historical DB extractor & dataset generator
│   └── train_openjev.py               # LoRA fine-tuning training script on MPS
├── src/
│   ├── main.py                        # Pipeline orchestrator (Ingest -> Dedup -> Score -> Persist)
│   ├── classification/
│   │   ├── __init__.py
│   │   └── jev_client.py              # OpenJev / LoRA 4-role classification client
│   ├── deduplication/
│   │   ├── __init__.py
│   │   └── minhash_lsh.py             # MinHash + LSH Near-Duplicate Engine
│   ├── models/
│   │   ├── __init__.py
│   │   └── news.py                    # Pydantic NewsItem model with 4-role scoring
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── alphaxiv.py                # AlphaXiv research papers collector
│   │   ├── github_trending.py         # GitHub Trending Python & AI repositories
│   │   ├── hackernews.py              # Hacker News Best stories + comments collector
│   │   ├── huggingface.py             # HF Daily Papers & Trending Models (async README extraction)
│   │   └── rss.py                     # Generic RSS engine with Cloudflare bypass & image extraction
│   └── storage/
│       ├── __init__.py
│       └── database.py                # SQLite storage layer with indexing & deduplication
└── tests/
```

---

## 📊 Unified Data Model (`NewsItem`)

Located in [`src/models/news.py`](file:///Users/abhisheksoni/project-news/src/models/news.py):

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `str` | Unique identifier (e.g. `hf_model_Edge0_Audio8`, `gh_vllm-project_vllm`, `hn_12345`, `rss_sha256`) |
| `title` | `str` | Headline, paper title, or repository name |
| `url` | `str` | Canonical link to original article, paper, or repository |
| `source` | `str` | Source publisher name (e.g. `OpenAI Blog`, `Hugging Face Model Hub`, `GitHub Trending`) |
| `source_type` | `str` | Source stream category (`article`, `hf_model`, `github_repo`, `research`, `community`) |
| `published_at` | `datetime \| None` | Standardized UTC publication timestamp |
| `author` | `str \| None` | Author or creator name(s) |
| `description` | `str \| None` | Sanitized plain-text description, abstract, or README summary |
| `category` | `str \| None` | Topic category tag (e.g. `ai_research`, `ai_engineering`, `startup_innovation`) |
| `image_url` | `str \| None` | Article image, OpenGraph preview, or curated category fallback banner |
| `is_duplicate` | `bool` | `True` if flagged as a near-duplicate of an earlier article |
| `duplicate_of` | `str \| None` | ID of the original article if marked as duplicate |
| `primary_role` | `str \| None` | Top predicted audience role (`ai_researcher`, `ai_engineer`, `startup_innovations`, `noise`) |
| `confidence` | `float` | Decision confidence score ($0.0 \to 1.0$) |
| `researcher_score` | `float` | Relevance probability for AI/ML Researchers ($0.0 \to 1.0$) |
| `engineer_score` | `float` | Relevance probability for AI Engineers & Builders ($0.0 \to 1.0$) |
| `startup_score` | `float` | Relevance probability for Startups & Innovators ($0.0 \to 1.0$) |
| `irrelevant_score` | `float` | Probability that item is non-technical/noise ($0.0 \to 1.0$) |
| `collected_at` | `datetime` | UTC timestamp of ingestion |

---

## 📡 Curated Sources Configured (22+ Feeds)

### 1. Dedicated AI Hubs & Developer Streams
* **Hugging Face Model Hub:** Trending open-weight models with asynchronous `README.md` plain-text extraction.
* **Hugging Face Daily Papers:** Curated daily research papers from HF Hub.
* **GitHub Trending (Python & AI):** Top trending repositories with daily star metrics.
* **AlphaXiv:** Trending research discovery explore feed.
* **Hacker News:** Top stories and technical discussions from `https://news.ycombinator.com/best`.

### 2. Core AI / ML Research & Lab Blogs
* **OpenAI Blog:** `https://openai.com/news/rss.xml` (with official Contentful banner extraction)
* **Google AI Blog:** `https://blog.google/technology/ai/rss/`
* **Microsoft Research Blog:** `https://www.microsoft.com/en-us/research/blog/feed/`
* **MIT News - AI:** `https://news.mit.edu/rss/topic/artificial-intelligence2`
* **Berkeley AI Research (BAIR):** `https://bair.berkeley.edu/blog/feed.xml`
* **Hugging Face Blog:** `https://huggingface.co/blog/feed.xml`
* **KDnuggets:** `https://www.kdnuggets.com/feed`

### 3. Top AI Engineering, Developer & Cloud Feeds
* **Claude & Anthropic Updates:** News & research tracker for Anthropic & Claude Code releases.
* **NVIDIA Developer Blog:** `https://developer.nvidia.com/blog/feed`
* **AWS Machine Learning Blog:** `https://aws.amazon.com/blogs/machine-learning/feed/`
* **Simon Willison Weblog:** `https://simonwillison.net/atom/entries/`
* **Chip Huyen AI Blog:** `https://huyenchip.com/feed.xml`
* **Latent Space (Substack):** `https://www.latent.space/feed`
* **Ahead of AI (Sebastian Raschka):** `https://magazine.sebastianraschka.com/feed`

### 4. Medium AI / ML Feeds
* **Towards Data Science (Medium):** `https://towardsdatascience.com/feed`
* **Medium AI Feed:** `https://medium.com/feed/tag/artificial-intelligence`
* **Medium ML Feed:** `https://medium.com/feed/tag/machine-learning`

### 5. Tech News, Startups & DeepTech
* **TechCrunch AI:** `https://techcrunch.com/category/artificial-intelligence/feed/`
* **TechCrunch Startups:** `https://techcrunch.com/category/startups/feed/`
* **VentureBeat AI & Tech:** `https://venturebeat.com/feed/`
* **IIT Innovations & Startups:** Aggregated query for IIT startup and research breakthroughs.
* **Top IITs Research (Madras, Bombay, Delhi, Kanpur):** Patent, research, and incubation stream.

---

## 🤖 4-Role Decision Engine & Fine-Tuning

Located in [`src/classification/jev_client.py`](file:///Users/abhisheksoni/project-news/src/classification/jev_client.py):

Every ingested article is evaluated across 4 target roles:
1. **🔬 AI Researcher (`ai_researcher`):** Focuses on model architectures, pretraining, loss functions, benchmarks, mathematical formulations, and foundational papers.
2. **🧑‍💻 AI Engineer (`ai_engineer`):** Focuses on inference engines (`vLLM`, `llama.cpp`), fine-tuning (`LoRA`, `Unsloth`), quantization, toolchains, APIs, SDKs, and deployment optimizations.
3. **🚀 Startup & Innovation (`startup_innovations`):** Focuses on funding rounds, VC investments, product launches, market trends, enterprise adoption, and DeepTech spin-offs.
4. **🗑️ Noise / Irrelevant (`noise`):** Filters out non-technical articles, general interest stories, consumer tech lifestyle, or generic opinion pieces.

### Fine-Tuning Workflow:
1. **Build Dataset:**
   ```bash
   PYTHONPATH=src uv run python scripts/build_dataset.py
   ```
2. **Inspect & Edit Labels Visually:**
   Open `dataset/audit_review.html` in your browser to filter by category, adjust any labels with dropdowns, and export.
3. **Train LoRA Adapter on Apple Silicon (MPS):**
   ```bash
   PYTHONPATH=src uv run python scripts/train_openjev.py
   ```
   * Result: **83.16% Validation Accuracy** / **0.8185 Weighted F1**.
   * Saved directly to `./models/fine_tuned_openjev_4role`.
4. **Test Live Inference:**
   ```bash
   PYTHONPATH=src uv run python test_jev.py
   ```

---

## 🔍 Deduplication Engine (MinHash & LSH)

Located in [`src/deduplication/minhash_lsh.py`](file:///Users/abhisheksoni/project-news/src/deduplication/minhash_lsh.py):

* **Shingling:** Breaks normalized text (`title + description`) into word 3-grams.
* **MinHash Signatures (`num_perm=128`):** Hashes shingles into compact 128-integer fingerprints.
* **Locality Sensitive Hashing (LSH):** Groups similar signatures into hash buckets for $O(1)$ query time at a Jaccard threshold of $\ge 0.75$.
* **Deduplication Linking:** Retains the canonical first article and flags subsequent duplicates with `duplicate_of = original_id`.

---

## ⚙️ Setup & Execution

### 1. Install Dependencies
```bash
uv sync
```

### 2. Run the Full Ingestion & Decision Pipeline
Fetch all 22+ sources, run MinHash deduplication, score articles across 4 roles using the local fine-tuned model, persist to SQLite, and automatically update the dashboard:
```bash
PYTHONPATH=src uv run python src/main.py
```

### 3. Open the Interactive Quality Dashboard
```bash
open report.html
```
