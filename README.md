# Project News: Multi-Source Aggregator & Decision Pipeline

A lightweight, single-node news aggregation, deduplication, and classification pipeline built with Python 3.12, `uv`, and SQLite. It ingests technical news, preprints, repositories, and models across 20 multi-platform sources, applies batch-level MinHash LSH deduplication, and routes articles into 3 target audience roles using a locally fine-tuned LoRA model on Apple Silicon (`mps`).

---

## 🏗️ Architecture & Pipeline Flow

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        20 Multi-Platform Feeds                         │
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
│              3-Role Decision Engine (OpenJev Qwen-0.8B LoRA)           │
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
* **Classification Head:** Linear sequence classification layer ($1024 \to 3$ logits) replacing the original 3-class NLI head.
* **Weights Footprint:** 4.3 MB (`adapter_model.safetensors`), saved in [`models/fine_tuned_openjev_3role/`](file:///Users/abhisheksoni/project-news/models/fine_tuned_openjev_3role).

### Target Roles
1. **`ai_researcher` (🔬 AI & ML Research):** Theoretical ML, loss functions, scaling laws, new architectures, benchmark evaluations, and preprint papers.
2. **`ai_engineer` (🧑‍💻 AI & Software Engineering):** Production tooling, SDKs, inference runtimes (`vLLM`, `llama.cpp`, `Ollama`), APIs, quantization, and implementation guides.
3. **`noise` (🗑️ Noise / Irrelevant):** Non-technical content, general lifestyle, sports, gaming, and consumer retail products.

---

### Empirical Baseline Comparison

Evaluated on the held-out test set ($N = 60$, untouched during training and checkpoint selection):

| Model / Approach | Accuracy | Weighted F1 | Macro F1 | Notes / Failure Mode |
| :--- | :--- | :--- | :--- | :--- |
| **Random Guessing Baseline** | 33.33% | 0.3333 | 0.3333 | Expected uniform chance across 3 balanced classes. |
| **TF-IDF + Logistic Regression** | **100.00%** | **1.0000** | **1.0000** | 5k n-gram linear baseline on balanced text data. |
| **Fine-Tuned OpenJev LoRA (Epoch 1 Best)** | **100.00%** | **1.0000** | **1.0000** | Transformer semantic representation ($L=0.0019$). |

---

### Per-Class Performance Breakdown & Confusion Matrix

#### Per-Class Metrics on Held-Out Test Set ($N=60$):
| Class | Support | Precision | Recall | F1-Score | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ai_researcher`** | 20 | **1.0000** | **1.0000** | **1.0000** | Clean identification of preprints and theoretical math. |
| **`ai_engineer`** | 20 | **1.0000** | **1.0000** | **1.0000** | High precision on tooling, SDKs, kernels, and runtimes. |
| **`noise`** | 20 | **1.0000** | **1.0000** | **1.0000** | Complete filtering of non-technical consumer/lifestyle items. |
| **Overall / Average** | **60** | **1.0000** | **1.0000** | **1.0000** | Macro avg: 1.0000; Accuracy: 100.00%. |

#### Confusion Matrix ($N=60$):
```text
                     Predicted Labels
                   Research   Engineer    Noise
Actual Research  │    20          0         0    │ (N=20)
Actual Engineer  │     0         20         0    │ (N=20)
Actual Noise     │     0          0        20    │ (N=20)
```

---

### Dataset Provenance, Split Strategy & System Scope

1. **Dataset Structure & Provenance:**  
   The dataset comprises **520 total items** partitioned into three balanced splits with a fixed seed (`seed=42`):
   * **Train Set:** [`dataset/train.jsonl`](file:///Users/abhisheksoni/project-news/dataset/train.jsonl) (400 examples: 134 Research, 133 Engineering, 133 Noise)
   * **Validation Set:** [`dataset/val.jsonl`](file:///Users/abhisheksoni/project-news/dataset/val.jsonl) (60 examples: 20 Research, 20 Engineering, 20 Noise)
   * **Held-Out Test Set:** [`dataset/test.jsonl`](file:///Users/abhisheksoni/project-news/dataset/test.jsonl) (60 examples: 20 Research, 20 Engineering, 20 Noise)
   * **Visual Audit Sheet:** Interactive dataset explorer available in [`dataset/audit_review.html`](file:///Users/abhisheksoni/project-news/dataset/audit_review.html).
2. **Probability Calibration:**  
   The confidence percentages displayed in the dashboard and database are raw **Softmax output distributions** from the sequence classification head.
3. **System Scope & Scaling Boundaries:**  
   This pipeline is designed as a single-process, local workstation architecture running SQLite and local Apple Silicon MPS inference. Deduplication operates via:
   * **In-Memory MinHash LSH:** Runs within each active batch execution (Jaccard threshold $\ge 0.75$) to cluster syndicated feeds.
   * **Database Uniqueness:** Enforced across separate pipeline executions via SQLite `PRIMARY KEY` on canonical SHA-256 URL hashes.

---

## 📡 Ingestion Sources (20 Feeds)

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
* **VentureBeat AI & Tech:** `https://venturebeat.com/feed/`
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
| `primary_role` | `TEXT` | Winning role (`ai_researcher`, `ai_engineer`, `noise`) |
| `confidence` | `REAL` | Highest Softmax score ($0.0 \to 1.0$) |
| `researcher_score`| `REAL` | Softmax score for *AI/ML Researcher* |
| `engineer_score`  | `REAL` | Softmax score for *Software & AI Engineer* |
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
│   └── fine_tuned_openjev_3role/      # LoRA adapter weights (4.3 MB) + tokenizer
├── dataset/
│   ├── train.jsonl                    # 400 balanced training samples
│   ├── val.jsonl                      # 60 balanced validation samples
│   ├── test.jsonl                     # 60 balanced held-out test samples
│   └── audit_review.html              # Interactive visual dataset explorer
├── scripts/
│   ├── build_dataset.py               # Dataset extractor & split generator
│   ├── generate_audit_html.py         # Visual audit review HTML compiler
│   └── train_openjev.py               # LoRA training script on Apple Silicon MPS
└── src/
    ├── main.py                        # Pipeline orchestrator (Ingest -> Dedup -> Score -> Persist)
    ├── classification/
    │   ├── __init__.py
    │   ├── taxonomy.py                # Centralized 3-role label definitions
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
Collects from 20 sources, deduplicates with MinHash LSH, runs local 3-role inference, persists to SQLite, and updates `report.html`:
```bash
PYTHONPATH=src uv run python src/main.py
```

### 3. Inspect Dashboard
```bash
open report.html
```

### 4. Rebuilding Datasets & Fine-Tuning (Optional)
```bash
# 1. Compile visual audit sheet from train/val/test splits
PYTHONPATH=src uv run python scripts/generate_audit_html.py

# 2. Inspect/edit labels via visual interface
open dataset/audit_review.html

# 3. Execute LoRA fine-tuning on Apple Silicon MPS
PYTHONPATH=src uv run python scripts/train_openjev.py

# 4. Run live inference test script
PYTHONPATH=src uv run python test_jev.py
```
