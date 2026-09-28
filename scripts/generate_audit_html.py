"""Generate updated interactive dataset/audit_review.html from train.jsonl, val.jsonl, and test.jsonl."""

import html
import json
import re
from pathlib import Path


def parse_entry(d: dict, split_name: str) -> dict:
    text = d.get("text", "")
    title_match = re.search(r"Title:\s*(.*?)(?=\.\s*Description:|\.\s*Source:|$)", text)
    desc_match = re.search(r"Description:\s*(.*?)(?=\.\s*Source:|$)", text)
    source_match = re.search(r"Source:\s*(.*?)(?=\.|$)", text)

    title = title_match.group(1).strip() if title_match else d.get("title", text[:80])
    desc = desc_match.group(1).strip() if desc_match else d.get("description", "")
    source = source_match.group(1).strip() if source_match else d.get("source", "Unknown")

    label_name = d.get("label_name", "unknown")
    label_id = d.get("label", 0)

    # Normalize role names
    if label_name in ("startup_innovations", "startup", "startups"):
        # Map startup to noise or preserve based on dataset
        label_key = "startup_innovations"
    elif label_name in ("ai_researcher", "research"):
        label_key = "ai_researcher"
    elif label_name in ("ai_engineer", "engineer"):
        label_key = "ai_engineer"
    else:
        label_key = "noise"

    return {
        "id": d.get("id", ""),
        "split": split_name,
        "title": title,
        "description": desc,
        "source": source,
        "assigned_label": label_key,
        "label_id": label_id,
        "text": text,
    }


def load_dataset_file(filename: str, split_name: str) -> list:
    p = Path("dataset") / filename
    if not p.exists():
        return []
    entries = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(parse_entry(json.loads(line), split_name))
                except Exception:
                    pass
    return entries


def main():
    train_entries = load_dataset_file("train.jsonl", "Train")
    val_entries = load_dataset_file("val.jsonl", "Validation")
    test_entries = load_dataset_file("test.jsonl", "Test")

    all_entries = train_entries + val_entries + test_entries

    print(
        f"Loaded {len(all_entries)} total entries: "
        f"Train={len(train_entries)}, Val={len(val_entries)}, Test={len(test_entries)}"
    )

    data_json = json.dumps(all_entries)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dataset Review & Visual Explorer (Train, Val, Test)</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #090d16;
            --card-bg: #111827;
            --border: #1f2937;
            --border-hover: #374151;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --research-color: #38bdf8;
            --engineer-color: #c084fc;
            --startup-color: #fb923c;
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
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
            transition: transform 0.15s ease, opacity 0.15s ease;
        }}
        .btn-export:hover {{ transform: translateY(-2px); opacity: 0.95; }}

        /* Split Switcher Tabs */
        .split-nav {{ display: flex; gap: 0.75rem; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border); padding-bottom: 0.75rem; flex-wrap: wrap; }}
        .split-btn {{
            padding: 0.65rem 1.25rem;
            border-radius: 8px;
            font-size: 0.95rem;
            font-weight: 700;
            cursor: pointer;
            border: 1px solid transparent;
            background: transparent;
            color: var(--text-muted);
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .split-btn:hover {{ color: #fff; background: rgba(255, 255, 255, 0.05); }}
        .split-btn.active {{ color: #fff; background: #1e293b; border-color: #38bdf8; box-shadow: 0 4px 12px rgba(56, 189, 248, 0.2); }}

        /* Category Filter Selector Tabs */
        .category-nav {{ display: flex; gap: 0.6rem; margin-bottom: 1.5rem; flex-wrap: wrap; }}
        .cat-btn {{
            padding: 0.6rem 1.1rem;
            border-radius: 8px;
            font-size: 0.88rem;
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
        .cat-btn:hover {{ color: var(--text-main); background: #1e293b; border-color: var(--border-hover); }}
        .cat-btn.active {{ color: #fff; background: #1e293b; border-color: #38bdf8; }}
        .cat-btn.active.tab-research {{ border-color: var(--research-color); }}
        .cat-btn.active.tab-engineer {{ border-color: var(--engineer-color); }}
        .cat-btn.active.tab-startup {{ border-color: var(--startup-color); }}
        .cat-btn.active.tab-noise {{ border-color: var(--noise-color); }}
        .cat-count {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.78rem;
            padding: 0.15rem 0.45rem;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.1);
        }}

        /* Search Controls */
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

        /* Table */
        table {{ width: 100%; border-collapse: collapse; background: var(--card-bg); border-radius: 10px; overflow: hidden; border: 1px solid var(--border); }}
        th, td {{ padding: 0.85rem 1rem; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.88rem; vertical-align: middle; }}
        th {{ background: #0f172a; color: var(--text-muted); text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; font-weight: 700; }}
        tr:hover {{ background: rgba(255, 255, 255, 0.02); }}

        .split-tag {{
            font-size: 0.72rem;
            font-weight: 700;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            text-transform: uppercase;
        }}
        .split-tag.Train {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }}
        .split-tag.Validation {{ background: rgba(192, 132, 252, 0.15); color: #c084fc; border: 1px solid rgba(192, 132, 252, 0.3); }}
        .split-tag.Test {{ background: rgba(251, 146, 60, 0.15); color: #fb923c; border: 1px solid rgba(251, 146, 60, 0.3); }}

        /* Interactive Select Dropdown */
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
        }}
        .label-select.ai_researcher {{ border-color: var(--research-color); color: var(--research-color); }}
        .label-select.ai_engineer {{ border-color: var(--engineer-color); color: var(--engineer-color); }}
        .label-select.startup_innovations {{ border-color: var(--startup-color); color: var(--startup-color); }}
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
                <h1>Dataset Review & Visual Explorer</h1>
                <p class="subtitle">Inspecting updated train ({len(train_entries)}), val ({len(val_entries)}), and test ({len(test_entries)}) splits.</p>
            </div>
            <div class="header-actions">
                <button class="btn-export" onclick="exportCurrentSplit()">
                    💾 Export Current Split (.jsonl)
                </button>
            </div>
        </div>

        <!-- Split Tabs -->
        <div class="split-nav">
            <button class="split-btn active" onclick="selectSplit('Train', this)">
                📚 Train Set <span class="cat-count">{len(train_entries)}</span>
            </button>
            <button class="split-btn" onclick="selectSplit('Validation', this)">
                🧪 Validation Set <span class="cat-count">{len(val_entries)}</span>
            </button>
            <button class="split-btn" onclick="selectSplit('Test', this)">
                🎯 Held-Out Test Set <span class="cat-count">{len(test_entries)}</span>
            </button>
            <button class="split-btn" onclick="selectSplit('All', this)">
                🌐 All Combined <span class="cat-count">{len(all_entries)}</span>
            </button>
        </div>

        <!-- Category Selector Buttons -->
        <div class="category-nav">
            <button class="cat-btn active" onclick="selectCategory('all', this)">
                🌐 All Roles <span class="cat-count" id="count-all">0</span>
            </button>
            <button class="cat-btn tab-research" onclick="selectCategory('ai_researcher', this)">
                🔬 AI & ML Research <span class="cat-count" id="count-ai_researcher" style="color:var(--research-color);">0</span>
            </button>
            <button class="cat-btn tab-engineer" onclick="selectCategory('ai_engineer', this)">
                🧑‍💻 AI & Software Engineering <span class="cat-count" id="count-ai_engineer" style="color:var(--engineer-color);">0</span>
            </button>
            <button class="cat-btn tab-startup" onclick="selectCategory('startup_innovations', this)">
                🚀 Startups & Innovation <span class="cat-count" id="count-startup_innovations" style="color:var(--startup-color);">0</span>
            </button>
            <button class="cat-btn tab-noise" onclick="selectCategory('noise', this)">
                🗑️ Noise / Irrelevant <span class="cat-count" id="count-noise" style="color:var(--noise-color);">0</span>
            </button>
        </div>

        <!-- Search Bar -->
        <div class="controls">
            <input type="text" id="searchInput" class="search-box" placeholder="Filter by headline keywords, descriptions, sources..." oninput="filterTable()">
            <div class="visible-count" id="visibleCount">Showing items</div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 45px;">#</th>
                    <th style="width: 90px;">Split</th>
                    <th style="width: 210px;">Assigned Category</th>
                    <th>Headline & Content Snippet</th>
                    <th style="width: 200px;">Source</th>
                </tr>
            </thead>
            <tbody id="tableBody">
"""

    for i, r in enumerate(all_entries, 1):
        t_esc = html.escape(r["title"])
        d_esc = html.escape(r["description"][:170])
        s_esc = html.escape(r["source"])
        cat = r["assigned_label"]
        split = r["split"]
        rid = r["id"]
        search_text = f"{r['title']} {r['description']} {r['source']} {cat} {split}".lower()

        html_content += f"""
            <tr class="audit-row" id="row-{rid}" data-id="{rid}" data-split="{split}" data-cat="{cat}" data-search="{html.escape(search_text)}">
                <td style="color: var(--text-muted); font-family: monospace;">{i}</td>
                <td><span class="split-tag {split}">{split}</span></td>
                <td>
                    <select class="label-select {cat}" onchange="changeLabel('{rid}', this.value, this)">
                        <option value="ai_researcher" {'selected' if cat == 'ai_researcher' else ''}>🔬 AI Research</option>
                        <option value="ai_engineer" {'selected' if cat == 'ai_engineer' else ''}>🧑‍💻 AI Engineering</option>
                        <option value="startup_innovations" {'selected' if cat == 'startup_innovations' else ''}>🚀 Startups</option>
                        <option value="noise" {'selected' if cat == 'noise' else ''}>🗑️ Noise</option>
                    </select>
                    <span class="edited-badge">EDITED</span>
                </td>
                <td>
                    <b style="color: #f8fafc;">{t_esc}</b><br>
                    <span style="color: #9ca3af; font-size: 0.82rem;">{d_esc}...</span>
                </td>
                <td style="color: #38bdf8; font-size: 0.82rem; font-weight: 600;">{s_esc}</td>
            </tr>
        """

    html_content += f"""
            </tbody>
        </table>
    </div>

    <script>
        const AUDIT_DATA = {data_json};
        let currentSplit = 'Train';
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

        function selectSplit(split, btnEl) {{
            currentSplit = split;
            document.querySelectorAll('.split-btn').forEach(b => b.classList.remove('active'));
            btnEl.classList.add('active');
            updateCategoryCounts();
            filterTable();
        }}

        function selectCategory(cat, btnEl) {{
            currentCat = cat;
            document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
            btnEl.classList.add('active');
            filterTable();
        }}

        function updateCategoryCounts() {{
            const filtered = (currentSplit === 'All') ? AUDIT_DATA : AUDIT_DATA.filter(x => x.split === currentSplit);
            
            const counts = {{
                'all': filtered.length,
                'ai_researcher': 0,
                'ai_engineer': 0,
                'startup_innovations': 0,
                'noise': 0
            }};

            filtered.forEach(x => {{
                if (counts[x.assigned_label] !== undefined) {{
                    counts[x.assigned_label]++;
                }}
            }});

            document.getElementById('count-all').textContent = counts['all'];
            document.getElementById('count-ai_researcher').textContent = counts['ai_researcher'];
            document.getElementById('count-ai_engineer').textContent = counts['ai_engineer'];
            document.getElementById('count-startup_innovations').textContent = counts['startup_innovations'];
            document.getElementById('count-noise').textContent = counts['noise'];
        }}

        function filterTable() {{
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            const rows = document.querySelectorAll('.audit-row');
            let visible = 0;

            rows.forEach(row => {{
                const split = row.getAttribute('data-split');
                const cat = row.getAttribute('data-cat');
                const search = row.getAttribute('data-search');

                const matchesSplit = (currentSplit === 'All') || (split === currentSplit);
                const matchesCat = (currentCat === 'all') || (cat === currentCat);
                const matchesSearch = !query || search.includes(query);

                if (matchesSplit && matchesCat && matchesSearch) {{
                    row.style.display = '';
                    visible++;
                }} else {{
                    row.style.display = 'none';
                }}
            }});

            document.getElementById('visibleCount').textContent = `Showing ${{visible}} items (${{currentSplit}} Set)`;
        }}

        function exportCurrentSplit() {{
            const filtered = (currentSplit === 'All') ? AUDIT_DATA : AUDIT_DATA.filter(x => x.split === currentSplit);
            const labelMap = {{
                'ai_researcher': 0,
                'ai_engineer': 1,
                'startup_innovations': 2,
                'noise': 3
            }};

            const formatted = filtered.map(item => ({{
                id: item.id,
                text: item.text,
                label: labelMap[item.assigned_label] !== undefined ? labelMap[item.assigned_label] : 0,
                label_name: item.assigned_label
            }}));

            const jsonlContent = formatted.map(x => JSON.stringify(x)).join('\\n') + '\\n';
            const fileName = currentSplit.toLowerCase() + '.jsonl';
            downloadFile(jsonlContent, fileName, 'application/json');
            alert(`✅ Exported ${{formatted.length}} rows for ${{currentSplit}} split as ${{fileName}}!`);
        }}

        function downloadFile(content, fileName, contentType) {{
            const a = document.createElement('a');
            const file = new Blob([content], {{ type: contentType }});
            a.href = URL.createObjectURL(file);
            a.download = fileName;
            a.click();
            URL.revokeObjectURL(a.href);
        }}

        // Initial render
        updateCategoryCounts();
        filterTable();
    </script>
</body>
</html>
    """

    out_file = Path("dataset/audit_review.html")
    out_file.write_text(html_content, encoding="utf-8")
    print(f"Successfully generated {out_file.resolve()} ({out_file.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
