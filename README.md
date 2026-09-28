# Project News: Multi-Source Aggregator & Decision Pipeline

A lightweight, single-node news aggregation, deduplication, and classification pipeline built with Python 3.12, `uv`, and SQLite. It ingests technical news, preprints, repositories, and models across 22 multi-platform sources, applies batch-level MinHash LSH deduplication, and routes articles into 4 target audience roles using a locally fine-tuned LoRA model on Apple Silicon (`mps`).

---

## 🏗️ Architecture & Pipeline Flow

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        22 Multi-Platform Feeds                         │
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
┌────────────────────────────────────────────────────────────────────────┐
│              4-Role Decision Engine (OpenJev Qwen-0.8B LoRA)           │
│        Local in-process sequence classification on Apple MPS / CUDA    │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ (Role Scores & Softmax Confidence)
                                   ▼
┌──────────────────────────────────┴─────────────────────────────────────┐
│    SQLite Database (news.db)     │   Visual Quality Dashboard (report.html)
└──────────────────────────────────┴─────────────────────────────────────┘
```

---

## 🔬 Classification Model, Baselines & Evaluation

### Model Configuration
* **Base Model:** [`AlexWortega/openjev`](https://huggingface.co/AlexWortega/openjev) (`qwen3.5-0.8b-nli-v2s-long`, 0.8B parameters).
* **Adapter Architecture:** PEFT LoRA ($r=16, \alpha=32, \text{dropout}=0.05$) targeting attention projection modules (`q_proj`, `k_proj`, `v_proj`, `o_proj`).
* **Classification Head:** Linear sequence classification layer ($1024 \to 4$ logits) replacing the original 3-class NLI head.
* **Weights Footprint:** 4.3 MB (`adapter_model.safetensors`), loaded in-process with PyTorch FP16 on Apple Silicon MPS.

### Target Roles
1. **`ai_researcher` (🔬 AI & ML Research):** Theoretical ML, loss functions, scaling laws, new architectures, benchmark evaluations, and preprint papers.
2. **`ai_engineer` (🧑‍💻 AI & Software Engineering):** Production tooling, SDKs, inference runtimes (`vLLM`, `llama.cpp`, `Ollama`), APIs, quantization, and implementation guides.
3. **`startup_innovations` (🚀 Startups & Innovation):** Venture rounds (Seed/Series A-D), acquisitions, valuation milestones, and commercial product launches.
4. **`noise` (🗑️ Noise / Irrelevant):** Non-technical content, general lifestyle, sports, gaming, and consumer retail products.

---

### Empirical Baseline Comparison

Evaluated on the holdout validation set ($N = 95$, $80/20$ split):

| Model / Approach | Accuracy | Weighted F1 | Macro F1 | Notes / Failure Mode |
| :--- | :--- | :--- | :--- | :--- |
| **Majority Class Dummy** | 61.05% | 0.4626 | 0.1895 | Always predicts dominant class (`ai_engineer`). |
| **Pre-Training Zero-Shot NLI** | 22.11% | 0.0807 | 0.0905 | Unaligned random mapping without fine-tuning. |
| **TF-IDF + Logistic Regression (Standard)** | 75.79% | 0.7159 | 0.6033 | 5k n-gram features; biased towards majority class. |
| **TF-IDF + Logistic Regression (Balanced)** | 82.11% | **0.8248** | **0.8142** | Class-weighted loss; strong linear baseline. |
| **Fine-Tuned OpenJev LoRA (Epoch 3)** | **83.16%** | 0.8185 | 0.8053 | Transformer semantic representation ($L=0.5683$). |

---

### Per-Class Performance Breakdown & Confusion Matrix

#### Per-Class Metrics (Fine-Tuned OpenJev LoRA):
| Class | Support | Precision | Recall | F1-Score | Analysis |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ai_engineer`** | 58 | 0.8000 | **0.9655** | 0.8750 | Dominant class; high recall, acts as attractor for ambiguous items. |
| **`ai_researcher`** | 9 | 0.7778 | 0.7778 | 0.7778 | Consistent precision/recall on academic and paper summaries. |
| **`startup_innovations`** | 7 | **1.0000** | 0.8571 | **0.9231** | High precision on funding and venture announcements. |
| **`noise`** | 21 | **1.0000** | **0.4762** | 0.6452 | **Weakest class:** 11 noise samples misclassified into `ai_engineer`. |
| **Overall / Average** | **95** | **0.8568** | **0.8316** | **0.8185** | Macro avg: 0.8053; Accuracy: 83.16%. |

#### Confusion Matrix ($N=95$):
```text
                     Predicted Labels
                   Research   Engineer   Startup    Noise
Actual Research  │    7          2          0         0    │ (N=9)
Actual Engineer  │    2         56          0         0    │ (N=58)
Actual Startup   │    0          1          6         0    │ (N=7)
Actual Noise     │    0         11          0        10    │ (N=21)
```

> **Why Weighted F1 (0.8185) is Lower than Accuracy (83.16%):**  
> The class distribution is heavily skewed toward `ai_engineer` (58.6% of dataset). The model achieves high recall on the majority class (96.55%), but struggles with recall on the `noise` class (47.62%), where 11 out of 21 irrelevant articles are pulled into `ai_engineer`.

---

### Dataset Provenance, Split Strategy & Known Limitations

1. **Label Provenance & Heuristic Alignment:**  
   The initial 471-row training dataset (376 train, 95 validation) was generated by extracting historical titles and descriptions from `news.db` and applying zero-source-bias regex heuristics ([`scripts/build_dataset.py`](file:///Users/abhisheksoni/project-news/scripts/build_dataset.py)). Consequently, fine-tuning teaches the model to approximate and generalize these semantic boundaries. To audit and correct heuristic misclassifications, an interactive labeling interface is provided in [`dataset/audit_review.html`](file:///Users/abhisheksoni/project-news/dataset/audit_review.html).
2. **Data Leakage Considerations:**  
   The current split uses a pseudo-random 80/20 train/validation split. In aggregated news feeds, syndication across multiple RSS feeds can introduce near-duplicate articles into both train and validation splits. Future benchmark revisions should employ **MinHash cluster-based splitting** or **strict temporal holdout** (e.g., train on prior weeks, validate on subsequent week) to eliminate syndication leakage.
3. **Probability Calibration:**  
   The confidence percentages displayed in the dashboard and database are raw **Softmax output distributions** from the sequence classification head. Softmax outputs are uncalibrated and tend toward overconfidence; formal posterior probability calibration (e.g., Platt temperature scaling or isotonic regression) has not been fitted.
4. **System Scope & Scaling Boundaries:**  
   This pipeline is designed as a single-process, local workstation architecture running SQLite and local Apple Silicon MPS inference. Deduplication operates via:
   * **In-Memory MinHash LSH:** Runs within each active batch execution (Jaccard threshold $\ge 0.75$) to cluster syndicated feeds.
   * **Database Uniqueness:** Enforced across separate pipeline executions via SQLite `PRIMARY KEY` on canonical SHA-256 URL hashes.

---

## 📡 Ingestion Sources (22 Feeds)

### 1. Dedicated Hubs & APIs
* **Hugging Face Model Hub:** Trending open-weight checkpoints with plain-text README parsing.
* **Hugging Face Daily Papers:** Daily paper submissions from the HF Hub.
* **GitHub Trending (Python & AI):** Top trending repositories with daily star metrics.
* **AlphaXiv:** Pre-print paper discoveries and summaries.
* **Hacker News:** Top curated stories from `https://news.ycombinator.com/best`.

### 2. Research & Lab Feeds
* **OpenAI Blog:** `https://openai.com/news/rss.xml`
* **Google AI Blog:** `https://blog.google/technology/ai/rss/`
* **Microsoft Research Blog:** `https://www.microsoft.com/en-us/research/blog/feed/`
* **MIT News - AI:** `https://news.mit.edu/rss/topic/artificial-intelligence2`
* **Berkeley AI Research (BAIR):** `https://bair.berkeley.edu/blog/feed.xml`
* **Hugging Face Blog:** `https://huggingface.co/blog/feed.xml`
* **KDnuggets:** `https://www.kdnuggets.com/feed`

### 3. Engineering, Cloud & Developer Blogs
* **Claude & Anthropic Updates:** Newsroom and research tracking feed.
* **NVIDIA Developer Blog:** `https://developer.nvidia.com/blog/feed`
* **AWS Machine Learning Blog:** `https://aws.amazon.com/blogs/machine-learning/feed/`
* **Simon Willison Weblog:** `https://simonwillison.net/atom/entries/`
* **Chip Huyen AI Blog:** `https://huyenchip.com/feed.xml`
* **Latent Space (Substack):** `https://www.latent.space/feed`
* **Ahead of AI (Sebastian Raschka):** `https://magazine.sebastianraschka.com/feed`

### 4. Medium AI / ML Feeds
* **Towards Data Science:** `https://towardsdatascience.com/feed`
* **Medium AI Tag:** `https://medium.com/feed/tag/artificial-intelligence`
* **Medium ML Tag:** `https://medium.com/feed/tag/machine-learning`

### 5. Tech News & DeepTech
* **TechCrunch AI:** `https://techcrunch.com/category/artificial-intelligence/feed/`
* **TechCrunch Startups:** `https://techcrunch.com/category/startups/feed/`
* **VentureBeat AI & Tech:** `https://venturebeat.com/feed/`
* **IIT Innovations & Startups:** Google News topic query for IIT incubation and patents.
* **Top IITs Research (Madras/Bombay/Delhi/Kanpur):** DeepTech research query.

---

## 📊 Database Schema (`news_items` Table)

Located in [`src/storage/database.py`](file:///Users/abhisheksoni/project-news/src/storage/database.py):

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `TEXT PRIMARY KEY` | Canonical URL SHA-256 hash or platform identifier |
| `title` | `TEXT` | Article or repository headline |
| `url` | `TEXT` | Destination URL |
| `source` | `TEXT` | Origin publisher name |
| `source_type` | `TEXT` | Protocol category (`article`, `hf_model`, `github_repo`, `research`, `community`) |
| `published_at` | `TEXT` | ISO publication timestamp |
| `author` | `TEXT` | Author or creator attribution |
| `description` | `TEXT` | Plain-text content excerpt or abstract |
| `category` | `TEXT` | Feed category metadata |
| `image_url` | `TEXT` | Thumbnail, OpenGraph image, or category fallback |
| `is_duplicate` | `INTEGER` | `0` = unique, `1` = duplicate |
| `duplicate_of` | `TEXT` | Parent article ID if duplicate |
| `primary_role` | `TEXT` | Winning role (`ai_researcher`, `ai_engineer`, `startup_innovations`, `noise`) |
| `confidence` | `REAL` | Highest Softmax score ($0.0 \to 1.0$) |
| `researcher_score`| `REAL` | Softmax score for *AI/ML Researcher* |
| `engineer_score`  | `REAL` | Softmax score for *Software & AI Engineer* |
| `startup_score`   | `REAL` | Softmax score for *Startups & Innovation* |
| `irrelevant_score`| `REAL` | Softmax score for *Noise / Irrelevant* |
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
├── test_jev.py                        # Live inference test script
├── models/
│   └── fine_tuned_openjev_4role/      # LoRA adapter weights (4.3 MB) + tokenizer
├── dataset/
│   ├── train.jsonl                    # 376 training samples
│   ├── val.jsonl                      # 95 validation samples
│   └── audit_review.html              # Interactive label editor with category tabs
├── scripts/
│   ├── build_dataset.py               # Dataset builder & audit review HTML generator
│   └── train_openjev.py               # LoRA training script on Apple Silicon MPS
└── src/
    ├── main.py                        # Pipeline orchestrator (Ingest -> Dedup -> Score -> Persist)
    ├── classification/
    │   ├── __init__.py
    │   └── jev_client.py              # In-process local inference client
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
Collects from 22 sources, deduplicates with MinHash LSH, runs local 4-role inference, persists to SQLite, and updates `report.html`:
```bash
PYTHONPATH=src uv run python src/main.py
```

### 3. Inspect Dashboard
```bash
open report.html
```

### 4. Rebuilding Datasets & Fine-Tuning (Optional)
```bash
# 1. Rebuild training splits and visual audit sheet
PYTHONPATH=src uv run python scripts/build_dataset.py

# 2. Inspect/edit labels via visual interface
open dataset/audit_review.html

# 3. Execute LoRA fine-tuning on Apple Silicon MPS (~9 mins)
PYTHONPATH=src uv run python scripts/train_openjev.py

# 4. Run inference test script
PYTHONPATH=src uv run python test_jev.py
```
