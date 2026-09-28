"""Extract historical news data from news.db and build auditable 3-role training, validation, and test datasets.

Roles:
0: ai_researcher (🔬 AI & ML Research)
1: ai_engineer   (🧑‍💻 AI & Software Engineering)
2: noise         (🗑️ Noise / Irrelevant)

100% Semantic Content Classification based STRICTLY on Title + Description text.
Zero source/category metadata bias.
"""

import html
import json
import random
import re
import sqlite3
import sys
from pathlib import Path

# Add src to path so taxonomy is imported
src_path = str(Path(__file__).resolve().parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from classification.taxonomy import ID2LABEL, LABEL2ID, ROLES, ROLE_DISPLAY_NAMES


def classify_text_content(title: str, description: str) -> tuple[str, float, str]:
    """
    Pure semantic text analyzer based strictly on the Title and Description text.
    Evaluates term frequency, multi-word phrases, and semantic domain weights.
    Returns: (role_name, confidence, justification)
    """
    title_clean = title.strip()
    desc_clean = description.strip()
    full_text = f"{title_clean}. {desc_clean}".lower()

    # --- 1. NOISE FILTER (Non-technical, Pure Retail, Gossip, Sports, General VC/Deals) ---
    noise_keywords = [
        "celebrity", "movie", "actor", "actress", "cricket", "football", "sports",
        "horoscope", "recipe", "diet", "weight loss", "fashion", "sneakers", "clothing",
        "sunglasses", "cosmetics", "daily soap", "box office", "suicide", "crime", "murder",
        "upsc", "ips officer", "ias officer", "citizenship", "supreme court", "midterm elections",
        "campus surveillance", "anti-human", "pelican riding bicycles",
        "luxury retail", "real estate", "food delivery", "travel guide",
    ]
    noise_hits = [w for w in noise_keywords if re.search(r"\b" + re.escape(w) + r"\b", full_text)]
    if len(noise_hits) >= 1 and not any(k in full_text for k in ["llm", "ai model", "neural", "gpu", "compiler", "dataset", "deep learning"]):
        return "noise", 0.95, f"Non-technical topic detected ({', '.join(noise_hits[:2])})."

    # Non-technical funding / business deals without AI or tech substance -> noise
    funding_only_terms = ["seed round", "series a", "series b", "angel investment", "first close", "valuation", "fundraise"]
    has_funding = any(f in full_text for f in funding_only_terms)
    has_tech = any(t in full_text for t in ["ai", "model", "llm", "algorithm", "software", "api", "code", "neural", "gpu", "data"])
    if has_funding and not has_tech:
        return "noise", 0.90, "General financial/funding deal without technical AI/engineering depth."

    # --- 2. AI & ML RESEARCH SIGNALS ---
    research_keywords = [
        "arxiv", "paper", "papers", "theorem", "proof", "mathematical", "loss function",
        "ablation study", "empirical evaluation", "scaling law", "scaling laws",
        "gradient descent", "latent reasoning", "diffusion model", "diffusion process",
        "pre-training", "post-training recipe", "rlhf", "dpo", "preference optimization",
        "chain-of-thought", "cot traces", "synthetic reasoning", "benchmark", "benchmarks",
        "generalization", "attention mechanism", "transformer architecture", "neural collapse",
        "loss curve", "inductive bias", "we propose", "we introduce", "state-of-the-art results",
        "cross-encoder", "supervised fine-tuning", "sft", "vision-language", "reasoning model",
    ]
    research_score = 0
    research_hits = []
    for kw in research_keywords:
        if re.search(r"\b" + re.escape(kw) + r"\b", full_text):
            research_score += 2
            research_hits.append(kw)

    # --- 3. SOFTWARE & AI ENGINEERING SIGNALS ---
    eng_keywords = [
        "github", "library", "sdk", "api", "apis", "server", "docker", "cuda", "kernel",
        "vllm", "llama.cpp", "ollama", "gguf", "fp8", "bf16", "awq", "quantization",
        "langchain", "llamaindex", "fastapi", "sqlite", "postgres", "mcp server",
        "agent", "agents", "tool calling", "agent memory", "serving engine", "developer tool",
        "open source", "open-source", "open weights", "runtime", "latency", "throughput",
        "pagedattention", "cloud", "infrastructure", "python", "rust", "typescript",
        "code", "coding", "compiler", "tutorial", "how to build", "architecture for deploying",
        "rag", "retrieval", "vector search", "embedding", "database", "pull request", "release",
    ]
    eng_score = 0
    eng_hits = []
    for kw in eng_keywords:
        if re.search(r"\b" + re.escape(kw) + r"\b", full_text):
            eng_score += 2
            eng_hits.append(kw)

    # Strong title priority overrides
    title_lower = title_clean.lower()
    if any(term in title_lower for term in ["arxiv:", "scaling law", "rethinking deep search", "post-training recipe", "chain-of-thought in", "bounds for"]):
        return "ai_researcher", 0.95, f"Title indicates academic/theoretical research paper ({', '.join(research_hits[:2])})."

    # Compare weighted scores
    if research_score > eng_score and research_score >= 2:
        return "ai_researcher", 0.90, f"Text focuses on ML research, benchmarks, or paper concepts: {', '.join(research_hits[:3])}"
    elif eng_score >= 2:
        return "ai_engineer", 0.90, f"Text focuses on software engineering, SDKs, tools, or deployment: {', '.join(eng_hits[:3])}"

    # Default technical fallback
    if any(w in full_text for w in ["ai", "model", "llm", "software", "data", "robot", "tech", "computer"]):
        return "ai_engineer", 0.70, "General technical discussion categorized as Software & AI Engineering."

    return "noise", 0.80, "General non-technical content without specific engineering or research keywords."


def build_dataset_from_db(
    db_path: str = "news.db",
    output_dir: str = "dataset",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM news_items WHERE is_duplicate = 0")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    print(f"Loaded {len(rows)} unique historical items from {db_path}.")

    labeled_dataset = []
    audit_records = []
    stats = {role: 0 for role in ROLES}

    for item in rows:
        title = (item.get("title") or "").strip()
        desc = (item.get("description") or "").strip()
        source = (item.get("source") or "").strip()

        if not title:
            continue

        label_key, conf, justification = classify_text_content(title, desc)
        label_id = LABEL2ID[label_key]

        stats[label_key] += 1

        text_prompt = f"Based on this technical news summary: Title: {title}. Description: {desc}. Source: {source}."

        entry = {
            "id": item["id"],
            "text": text_prompt,
            "label": label_id,
            "label_name": label_key,
        }
        labeled_dataset.append(entry)

        audit_records.append({
            "id": item["id"],
            "title": title,
            "source": source,
            "description": desc,
            "assigned_label": label_key,
            "confidence": conf,
            "justification": justification,
        })

    # Shuffle deterministically with seed
    random.seed(42)
    random.shuffle(labeled_dataset)

    n_total = len(labeled_dataset)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)

    train_data = labeled_dataset[:n_train]
    val_data = labeled_dataset[n_train : n_train + n_val]
    test_data = labeled_dataset[n_train + n_val :]

    # Write JSONL files
    train_file = out_path / "train.jsonl"
    val_file = out_path / "val.jsonl"
    test_file = out_path / "test.jsonl"

    with open(train_file, "w", encoding="utf-8") as f:
        for ex in train_data:
            f.write(json.dumps(ex) + "\n")

    with open(val_file, "w", encoding="utf-8") as f:
        for ex in val_data:
            f.write(json.dumps(ex) + "\n")

    with open(test_file, "w", encoding="utf-8") as f:
        for ex in test_data:
            f.write(json.dumps(ex) + "\n")

    # Generate Audit HTML
    generate_audit_html(audit_records, out_path / "audit_review.html", stats)

    print(f"\n================ 3-ROLE DATASET CREATION SUMMARY ================")
    print(f" Total Unique Historical Records: {len(labeled_dataset)}")
    print(f" Training Set (70%):             {len(train_data)} examples -> {train_file}")
    print(f" Validation Set (15%):           {len(val_data)} examples -> {val_file}")
    print(f" Held-Out Test Set (15%):        {len(test_data)} examples -> {test_file}")
    print(f" Class Breakdown:")
    for role in ROLES:
        print(f"   {ROLE_DISPLAY_NAMES[role]} ({LABEL2ID[role]}): {stats[role]}")
    print(f" Visual Audit Sheet:             {out_path / 'audit_review.html'}")
    print(f"=================================================================\n")


def generate_audit_html(records: list, output_file: Path, stats: dict):
    """Generate an interactive HTML audit file for 3 roles with category selector tabs, live editing dropdowns, and dataset export."""
    records_json = json.dumps(records)
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>3-Role Training Dataset Label Review & Editor (news.db)</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #090d16;
            --card-bg: #111827;
            --border: #1f2937;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --research-color: #38bdf8;
            --engineer-color: #c084fc;
            --noise-color: #94a3b8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }}
        body {{ background: var(--bg); color: var(--text-main); padding: 2.5rem; line-height: 1.5; }}
        .container {{ max-width: 1440px; margin: 0 auto; }}
        
        .header-row {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.5rem; }}
        h1 {{ font-size: 2rem; font-weight: 800; color: #38bdf8; }}
        p.subtitle {{ color: var(--text-muted); font-size: 0.95rem; margin-top: 0.2rem; }}
        
        .header-actions {{ display: flex; gap: 0.75rem; align-items: center; }}
        .btn-export {{
            padding: 0.75rem 1.4rem;
            background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%);
            color: #fff;
            border: none;
            border-radius: 8px;
            font-weight: 700;
            font-size: 0.92rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
            transition: transform 0.15s ease, opacity 0.15s ease;
        }}
        .btn-export:hover {{ transform: translateY(-2px); opacity: 0.95; }}

        .category-nav {{ display: flex; gap: 0.6rem; margin-bottom: 1.5rem; flex-wrap: wrap; }}
        .cat-btn {{
            padding: 0.65rem 1.25rem;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 700;
            cursor: pointer;
            border: 1px solid var(--border);
            background: var(--card-bg);
            color: var(--text-muted);
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .cat-btn:hover {{ color: var(--text-main); background: #1e293b; border-color: #374151; }}
        .cat-btn.active {{ color: #fff; background: #1e293b; border-color: #38bdf8; box-shadow: 0 4px 12px rgba(56, 189, 248, 0.2); }}
        .cat-btn.active.tab-research {{ border-color: var(--research-color); }}
        .cat-btn.active.tab-engineer {{ border-color: var(--engineer-color); }}
        .cat-btn.active.tab-noise {{ border-color: var(--noise-color); }}
        .cat-count {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.78rem;
            padding: 0.15rem 0.45rem;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.1);
        }}

        .controls {{ display: flex; gap: 1rem; margin-bottom: 1.5rem; align-items: center; }}
        .search-box {{
            flex: 1;
            background: var(--card-bg);
            border: 1px solid var(--border);
            padding: 0.75rem 1.1rem;
            border-radius: 8px;
            color: var(--text-main);
            font-size: 0.92rem;
            outline: none;
        }}
        .search-box:focus {{ border-color: #38bdf8; }}
        .visible-count {{ font-size: 0.88rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; }}

        table {{ width: 100%; border-collapse: collapse; background: var(--card-bg); border-radius: 10px; overflow: hidden; border: 1px solid var(--border); }}
        th, td {{ padding: 0.85rem 1rem; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.88rem; vertical-align: middle; }}
        th {{ background: #0f172a; color: var(--text-muted); text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; font-weight: 700; }}
        tr:hover {{ background: rgba(255, 255, 255, 0.02); }}

        .label-select {{
            background: #0f172a;
            color: var(--text-main);
            border: 1px solid var(--border);
            padding: 0.45rem 0.65rem;
            border-radius: 6px;
            font-size: 0.82rem;
            font-weight: 600;
            outline: none;
            cursor: pointer;
            transition: border-color 0.2s ease;
        }}
        .label-select.ai_researcher {{ border-color: var(--research-color); color: var(--research-color); }}
        .label-select.ai_engineer {{ border-color: var(--engineer-color); color: var(--engineer-color); }}
        .label-select.noise {{ border-color: var(--noise-color); color: var(--noise-color); }}
        
        .edited-badge {{
            display: none;
            font-size: 0.68rem;
            background: #eab308;
            color: #000;
            font-weight: 800;
            padding: 0.1rem 0.35rem;
            border-radius: 4px;
            margin-left: 0.4rem;
        }}
        .row-edited .edited-badge {{ display: inline-block; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-row">
            <div>
                <h1>3-Role Dataset Label Review & Editor</h1>
                <p class="subtitle">Inspect records by category, edit misclassified labels via the dropdown, and export updated splits.</p>
            </div>
            <div class="header-actions">
                <button class="btn-export" onclick="exportUpdatedDatasets()">
                    💾 Export Updated Datasets (.jsonl)
                </button>
            </div>
        </div>

        <!-- Category Selector Buttons -->
        <div class="category-nav">
            <button class="cat-btn active" onclick="selectCategory('all', this)">
                🌐 All Records <span class="cat-count" id="count-all">{len(records)}</span>
            </button>
            <button class="cat-btn tab-research" onclick="selectCategory('ai_researcher', this)">
                🔬 AI & ML Research <span class="cat-count" id="count-ai_researcher" style="color:var(--research-color);">{stats['ai_researcher']}</span>
            </button>
            <button class="cat-btn tab-engineer" onclick="selectCategory('ai_engineer', this)">
                🧑‍💻 AI & Software Engineering <span class="cat-count" id="count-ai_engineer" style="color:var(--engineer-color);">{stats['ai_engineer']}</span>
            </button>
            <button class="cat-btn tab-noise" onclick="selectCategory('noise', this)">
                🗑️ Noise / Irrelevant <span class="cat-count" id="count-noise" style="color:var(--noise-color);">{stats['noise']}</span>
            </button>
        </div>

        <!-- Search Bar -->
        <div class="controls">
            <input type="text" id="searchInput" class="search-box" placeholder="Filter by title, keywords, or reasoning..." oninput="filterTable()">
            <div class="visible-count" id="visibleCount">Showing {len(records)} items</div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 45px;">#</th>
                    <th style="width: 210px;">Assigned Category (Click to Change)</th>
                    <th>Title & Snippet</th>
                    <th style="width: 170px;">Source</th>
                    <th style="width: 260px;">Reasoning Justification</th>
                </tr>
            </thead>
            <tbody id="tableBody">
    """
    for i, r in enumerate(records, 1):
        t_esc = html.escape(r["title"])
        d_esc = html.escape(r["description"][:160])
        s_esc = html.escape(r["source"])
        j_esc = html.escape(r["justification"])
        cat = r["assigned_label"]
        rid = r["id"]
        search_text = f"{r['title']} {r['description']} {r['source']} {r['justification']}".lower()

        html_content += f"""
                <tr class="audit-row" id="row-{rid}" data-id="{rid}" data-cat="{cat}" data-search="{html.escape(search_text)}">
                    <td style="color: var(--text-muted);">{i}</td>
                    <td>
                        <select class="label-select {cat}" onchange="changeLabel('{rid}', this.value, this)">
                            <option value="ai_researcher" {'selected' if cat == 'ai_researcher' else ''}>🔬 AI Research</option>
                            <option value="ai_engineer" {'selected' if cat == 'ai_engineer' else ''}>🧑‍💻 AI Engineering</option>
                            <option value="noise" {'selected' if cat == 'noise' else ''}>🗑️ Noise</option>
                        </select>
                        <span class="edited-badge">EDITED</span>
                    </td>
                    <td>
                        <b style="color: #f8fafc;">{t_esc}</b><br>
                        <span style="color: #9ca3af; font-size: 0.82rem;">{d_esc}...</span>
                    </td>
                    <td style="color: #cbd5e1; font-size: 0.82rem;">{s_esc}</td>
                    <td style="color: #38bdf8; font-size: 0.82rem;">{j_esc}</td>
                </tr>
        """
    html_content += f"""
            </tbody>
        </table>
    </div>

    <script>
        const AUDIT_DATA = {records_json};
        const LABEL_MAP = {{
            'ai_researcher': 0,
            'ai_engineer': 1,
            'noise': 2
        }};
        let currentCat = 'all';

        function changeLabel(id, newLabel, selectEl) {{
            const item = AUDIT_DATA.find(x => x.id === id);
            if (item) {{
                item.assigned_label = newLabel;
                item.edited = true;
            }}

            const row = document.getElementById(`row-${{id}}`);
            if (row) {{
                row.setAttribute('data-cat', newLabel);
                row.classList.add('row-edited');
                selectEl.className = `label-select ${{newLabel}}`;
            }}

            updateCategoryCounts();
            filterTable();
        }}

        function updateCategoryCounts() {{
            const counts = {{
                'all': AUDIT_DATA.length,
                'ai_researcher': 0,
                'ai_engineer': 0,
                'noise': 0
            }};

            AUDIT_DATA.forEach(x => {{
                if (counts[x.assigned_label] !== undefined) {{
                    counts[x.assigned_label]++;
                }}
            }});

            document.getElementById('count-all').textContent = counts['all'];
            document.getElementById('count-ai_researcher').textContent = counts['ai_researcher'];
            document.getElementById('count-ai_engineer').textContent = counts['ai_engineer'];
            document.getElementById('count-noise').textContent = counts['noise'];
        }}

        function selectCategory(cat, btnEl) {{
            currentCat = cat;
            document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
            btnEl.classList.add('active');
            filterTable();
        }}

        function filterTable() {{
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            const rows = document.querySelectorAll('.audit-row');
            let visible = 0;

            rows.forEach(row => {{
                const cat = row.getAttribute('data-cat');
                const search = row.getAttribute('data-search');

                const matchesCat = (currentCat === 'all') || (cat === currentCat);
                const matchesSearch = !query || search.includes(query);

                if (matchesCat && matchesSearch) {{
                    row.style.display = '';
                    visible++;
                }} else {{
                    row.style.display = 'none';
                }}
            }});

            document.getElementById('visibleCount').textContent = `Showing ${{visible}} items`;
        }}

        function exportUpdatedDatasets() {{
            const formatted = AUDIT_DATA.map(item => ({{
                id: item.id,
                text: `Based on this technical news summary: Title: ${{item.title}}. Description: ${{item.description}}. Source: ${{item.source}}.`,
                label: LABEL_MAP[item.assigned_label],
                label_name: item.assigned_label
            }}));

            // Split 70 / 15 / 15
            const shuffled = [...formatted].sort(() => Math.random() - 0.5);
            const nTrain = Math.floor(shuffled.length * 0.70);
            const nVal = Math.floor(shuffled.length * 0.15);

            const train = shuffled.slice(0, nTrain);
            const val = shuffled.slice(nTrain, nTrain + nVal);
            const test = shuffled.slice(nTrain + nVal);

            const trainJsonl = train.map(x => JSON.stringify(x)).join('\\n') + '\\n';
            const valJsonl = val.map(x => JSON.stringify(x)).join('\\n') + '\\n';
            const testJsonl = test.map(x => JSON.stringify(x)).join('\\n') + '\\n';

            downloadFile(trainJsonl, 'train.jsonl', 'application/json');
            setTimeout(() => downloadFile(valJsonl, 'val.jsonl', 'application/json'), 200);
            setTimeout(() => downloadFile(testJsonl, 'test.jsonl', 'application/json'), 400);

            alert(`✅ Successfully exported updated datasets!\\n\\nTrain: ${{train.length}} | Val: ${{val.length}} | Test: ${{test.length}}\\n\\nSaved directly to your Downloads folder.`);
        }}

        function downloadFile(content, fileName, contentType) {{
            const a = document.createElement('a');
            const file = new Blob([content], {{ type: contentType }});
            a.href = URL.createObjectURL(file);
            a.download = fileName;
            a.click();
            URL.revokeObjectURL(a.href);
        }}
    </script>
</body>
</html>
    """
    output_file.write_text(html_content, encoding="utf-8")


if __name__ == "__main__":
    build_dataset_from_db()
