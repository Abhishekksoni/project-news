import html
from pathlib import Path
import re
from storage.database import get_news_items, get_total_count, init_db


def clean_display_text(text: str) -> str:
    """Strip raw markdown formatting artifacts, asterisks, escaped characters, and stray symbols."""
    if not text:
        return ""
    text = re.sub(r"\\([~*_\-\[\]\(\)])", r"\1", text)
    text = text.replace("\\", "")
    text = re.sub(r"\*{1,3}", "", text)
    text = re.sub(r"_{1,3}", "", text)
    text = re.sub(r"(^|\s)>\s*", r"\1 ", text)
    text = re.sub(r"[#~`>]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_role_3(role_raw: str | None) -> tuple[str, str]:
    """Normalize role string to (role_key, role_label) across 3 roles."""
    r = (role_raw or "ai_engineer").lower().strip()
    if r in ("ai_researcher", "research", "researcher"):
        return "ai_researcher", "🔬 AI & ML Research"
    elif r in ("ai_engineer", "engineer", "engineering", "ai_ml", "startup_innovations", "startup"):
        return "ai_engineer", "🧑‍💻 AI & Software Engineering"
    else:
        return "noise", "🗑️ Noise / Irrelevant"


def generate_html_report(output_path: str = "report.html") -> str:
    init_db()
    items = get_news_items(limit=None, only_unique=False)
    stats = get_total_count()

    # Separate items into 3 dedicated streams
    github_items = [
        item for item in items 
        if item.source_type == "github_repo" or "github trending" in (item.source or "").lower()
    ]
    hf_model_items = [
        item for item in items 
        if item.source_type == "hf_model" or "model hub" in (item.source or "").lower()
    ]
    article_items = [
        item for item in items 
        if item not in github_items and item not in hf_model_items
    ]

    # Calculate 3-role distribution for unique articles
    researcher_count = 0
    engineer_count = 0
    noise_count = 0
    unique_articles_count = 0

    sources_set = set()
    for item in article_items:
        if item.source:
            sources_set.add(item.source)
        if not item.is_duplicate:
            unique_articles_count += 1
            role_key, _ = normalize_role_3(item.primary_role)
            if role_key == "ai_researcher":
                researcher_count += 1
            elif role_key == "ai_engineer":
                engineer_count += 1
            else:
                noise_count += 1

    sources = sorted(sources_set)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project News | 4-Role Intelligence & Quality Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #090d16;
            --card-bg: #111827;
            --card-border: #1f2937;
            --card-hover-border: #374151;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --text-dim: #6b7280;
            --accent: #38bdf8;
            --research-color: #38bdf8;
            --research-bg: rgba(56, 189, 248, 0.12);
            --research-border: rgba(56, 189, 248, 0.3);
            --engineer-color: #c084fc;
            --engineer-bg: rgba(192, 132, 252, 0.12);
            --engineer-border: rgba(192, 132, 252, 0.3);
            --startup-color: #fb923c;
            --startup-bg: rgba(251, 146, 60, 0.12);
            --startup-border: rgba(251, 146, 60, 0.3);
            --noise-color: #94a3b8;
            --noise-bg: rgba(148, 163, 184, 0.12);
            --noise-border: rgba(148, 163, 184, 0.3);
            --github-color: #58a6ff;
            --hf-color: #fbbf24;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        body {{
            background-color: var(--bg);
            color: var(--text-main);
            padding: 2.5rem 1.5rem;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{
            max-width: 1320px;
            margin: 0 auto;
        }}
        .header {{
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 1.75rem;
        }}
        .title-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 0.5rem;
        }}
        .header h1 {{
            font-size: 2.2rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #60a5fa 0%, #c084fc 50%, #f472b6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header p {{
            color: var(--text-muted);
            font-size: 0.95rem;
        }}
        .stats-bar {{
            display: flex;
            gap: 0.75rem;
            margin-top: 1.25rem;
            flex-wrap: wrap;
        }}
        .stat-badge {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 0.4rem 0.85rem;
            border-radius: 8px;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .stat-value {{
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
        }}

        /* Top View Section Nav (News vs GitHub vs HF Models) */
        .section-nav {{
            display: flex;
            gap: 0.75rem;
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 0.75rem;
            flex-wrap: wrap;
        }}
        .nav-btn {{
            padding: 0.75rem 1.35rem;
            border-radius: 10px;
            font-size: 0.96rem;
            font-weight: 700;
            cursor: pointer;
            border: 1px solid var(--card-border);
            background: var(--card-bg);
            color: var(--text-muted);
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }}
        .nav-btn:hover {{
            color: var(--text-main);
            border-color: var(--card-hover-border);
            background: #1e293b;
        }}
        .nav-btn.active {{
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.15) 0%, rgba(192, 132, 252, 0.15) 100%);
            color: #fff;
            border-color: #38bdf8;
            box-shadow: 0 4px 15px rgba(56, 189, 248, 0.2);
        }}
        .nav-badge {{
            font-size: 0.78rem;
            padding: 0.15rem 0.55rem;
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.1);
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
        }}

        /* Section Containers */
        .view-section {{
            display: none;
        }}
        .view-section.active {{
            display: block;
        }}

        /* 4-Role Category Tabs */
        .role-tabs {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
            background: rgba(17, 24, 39, 0.7);
            padding: 0.35rem;
            border-radius: 12px;
            border: 1px solid var(--card-border);
            width: fit-content;
        }}
        .role-tab {{
            padding: 0.6rem 1.1rem;
            border-radius: 8px;
            font-size: 0.88rem;
            font-weight: 600;
            cursor: pointer;
            border: 1px solid transparent;
            background: transparent;
            color: var(--text-muted);
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .role-tab:hover {{
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.04);
        }}
        .role-tab.active {{
            background: #1e293b;
            color: #fff;
            border-color: #38bdf8;
            box-shadow: 0 4px 12px rgba(56, 189, 248, 0.25);
        }}
        .role-tab.active.tab-research {{
            border-color: var(--research-color);
            box-shadow: 0 4px 12px rgba(56, 189, 248, 0.25);
        }}
        .role-tab.active.tab-engineer {{
            border-color: var(--engineer-color);
            box-shadow: 0 4px 12px rgba(192, 132, 252, 0.25);
        }}
        .role-tab.active.tab-startup {{
            border-color: var(--startup-color);
            box-shadow: 0 4px 12px rgba(251, 146, 60, 0.25);
        }}
        .role-tab.active.tab-noise {{
            border-color: var(--noise-color);
            box-shadow: 0 4px 12px rgba(148, 163, 184, 0.25);
        }}
        .role-count {{
            font-size: 0.75rem;
            padding: 0.1rem 0.45rem;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.1);
            font-family: 'JetBrains Mono', monospace;
        }}

        /* Filter Controls */
        .controls {{
            display: flex;
            gap: 0.75rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
            align-items: center;
        }}
        .search-box {{
            flex: 1;
            min-width: 260px;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 0.7rem 1rem;
            border-radius: 10px;
            color: var(--text-main);
            font-size: 0.92rem;
            outline: none;
            transition: border-color 0.2s ease;
        }}
        .search-box:focus {{
            border-color: var(--accent);
        }}
        .filter-select {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 0.7rem 1rem;
            border-radius: 10px;
            color: var(--text-main);
            font-size: 0.88rem;
            outline: none;
            cursor: pointer;
        }}

        /* Grid & Cards Layout */
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
            gap: 1.5rem;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
            position: relative;
        }}
        .card:hover {{
            transform: translateY(-3px);
            border-color: var(--card-hover-border);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        }}
        .card-img-wrap {{
            width: 100%;
            height: 180px;
            background-color: #0c121e;
            position: relative;
            overflow: hidden;
            border-bottom: 1px solid var(--card-border);
        }}
        .card-img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s ease;
        }}
        .card:hover .card-img {{
            transform: scale(1.03);
        }}
        .card-body {{
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            flex-grow: 1;
        }}
        .card-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
            gap: 0.5rem;
        }}
        .role-pill {{
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.2rem 0.55rem;
            border-radius: 6px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
        }}
        .role-pill.ai_researcher {{
            background: var(--research-bg);
            color: var(--research-color);
            border: 1px solid var(--research-border);
        }}
        .role-pill.ai_engineer {{
            background: var(--engineer-bg);
            color: var(--engineer-color);
            border: 1px solid var(--engineer-border);
        }}
        .role-pill.startup_innovations {{
            background: var(--startup-bg);
            color: var(--startup-color);
            border: 1px solid var(--startup-border);
        }}
        .role-pill.noise {{
            background: var(--noise-bg);
            color: var(--noise-color);
            border: 1px solid var(--noise-border);
        }}
        .source-tag {{
            font-size: 0.72rem;
            font-weight: 600;
            color: var(--text-dim);
            background: rgba(255, 255, 255, 0.05);
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 140px;
        }}
        .card-title {{
            font-size: 1.05rem;
            font-weight: 700;
            line-height: 1.35;
            margin-bottom: 0.6rem;
            color: var(--text-main);
            text-decoration: none;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .card-title:hover {{
            color: var(--accent);
        }}
        .card-desc {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 1rem;
            flex-grow: 1;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
            line-height: 1.45;
        }}

        /* 4-Role Score Breakdown Box */
        .scores-panel {{
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 8px;
            padding: 0.65rem 0.8rem;
            margin-bottom: 0.85rem;
        }}
        .scores-title {{
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-dim);
            margin-bottom: 0.45rem;
            display: flex;
            justify-content: space-between;
        }}
        .score-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.76rem;
            margin-bottom: 0.3rem;
        }}
        .score-row:last-child {{
            margin-bottom: 0;
        }}
        .score-label {{
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 0.3rem;
            width: 160px;
        }}
        .score-bar-wrap {{
            flex: 1;
            height: 5px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 3px;
            overflow: hidden;
            margin: 0 0.6rem;
        }}
        .score-bar-fill {{
            height: 100%;
            border-radius: 3px;
            transition: width 0.3s ease;
        }}
        .score-num {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            font-size: 0.72rem;
            width: 34px;
            text-align: right;
        }}
        .card-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.75rem;
            color: var(--text-dim);
            border-top: 1px solid var(--card-border);
            padding-top: 0.75rem;
            margin-top: auto;
        }}

        /* Tool Cards (GitHub Repos & HF Models) */
        .tool-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}
        .tool-card:hover {{
            transform: translateY(-2px);
            border-color: var(--card-hover-border);
        }}
        .tool-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }}
        .tool-badge {{
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
        }}
        .tool-badge.gh {{
            background: rgba(88, 166, 255, 0.12);
            color: var(--github-color);
            border: 1px solid rgba(88, 166, 255, 0.3);
        }}
        .tool-badge.hf {{
            background: rgba(251, 191, 36, 0.12);
            color: var(--hf-color);
            border: 1px solid rgba(251, 191, 36, 0.3);
        }}
        .tool-title {{
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-main);
            text-decoration: none;
            word-break: break-all;
        }}
        .tool-title:hover {{
            color: var(--accent);
        }}
        .tool-desc {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin: 0.6rem 0 1rem 0;
            line-height: 1.45;
        }}
        .tool-meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.78rem;
            color: var(--text-dim);
            border-top: 1px solid var(--card-border);
            padding-top: 0.75rem;
        }}
        .tool-btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.4rem 0.85rem;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            color: #fff;
            background: #1e293b;
            text-decoration: none;
            transition: background 0.2s ease;
            border: 1px solid var(--card-border);
        }}
        .tool-btn:hover {{
            background: #334155;
            color: var(--accent);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title-row">
                <h1>Project News</h1>
                <div class="stats-bar">
                    <div class="stat-badge">Articles: <span class="stat-value" style="color:#60a5fa;">{unique_articles_count}</span></div>
                    <div class="stat-badge">GitHub Repos: <span class="stat-value" style="color:#58a6ff;">{len(github_items)}</span></div>
                    <div class="stat-badge">HF Models: <span class="stat-value" style="color:#fbbf24;">{len(hf_model_items)}</span></div>
                    <div class="stat-badge">Duplicates: <span class="stat-value" style="color:#f87171;">{stats['duplicates']}</span></div>
                </div>
            </div>
            <p>Intelligence platform powered by local OpenJev neural cross-encoder across 4 specialized roles.</p>
        </div>

        <!-- Section Navigation Switcher -->
        <div class="section-nav">
            <button class="nav-btn active" onclick="switchSection('newsSection', this)">
                📰 Curated News & Papers <span class="nav-badge">{unique_articles_count}</span>
            </button>
            <button class="nav-btn" onclick="switchSection('githubSection', this)">
                🔥 Trending GitHub Repos <span class="nav-badge">{len(github_items)}</span>
            </button>
            <button class="nav-btn" onclick="switchSection('hfSection', this)">
                🤗 Trending Hugging Face Models <span class="nav-badge">{len(hf_model_items)}</span>
            </button>
        </div>

        <!-- SECTION 1: CURATED NEWS & PAPERS -->
        <div id="newsSection" class="view-section active">
            <!-- 3 Role Category Tabs -->
            <div class="role-tabs">
                <button class="role-tab active" data-filter="all" onclick="selectRoleTab('all', this)">
                    🌐 All Stories <span class="role-count">{unique_articles_count}</span>
                </button>
                <button class="role-tab tab-research" data-filter="ai_researcher" onclick="selectRoleTab('ai_researcher', this)">
                    🔬 AI & ML Research <span class="role-count">{researcher_count}</span>
                </button>
                <button class="role-tab tab-engineer" data-filter="ai_engineer" onclick="selectRoleTab('ai_engineer', this)">
                    🧑‍💻 AI & Software Engineering <span class="role-count">{engineer_count}</span>
                </button>
                <button class="role-tab tab-noise" data-filter="noise" onclick="selectRoleTab('noise', this)">
                    🗑️ Noise <span class="role-count">{noise_count}</span>
                </button>
            </div>

            <!-- Search and Refinement -->
            <div class="controls">
                <input type="text" id="searchInput" class="search-box" placeholder="Filter by title, keywords, authors, libraries..." oninput="filterCards()">
                
                <select id="sourceFilter" class="filter-select" onchange="filterCards()">
                    <option value="">All News Sources ({len(sources)})</option>
                    {"".join(f'<option value="{html.escape(s)}">{html.escape(s)}</option>' for s in sources)}
                </select>

                <select id="duplicateFilter" class="filter-select" onchange="filterCards()">
                    <option value="unique" selected>Unique Only</option>
                    <option value="all">All Items (incl. Dups)</option>
                    <option value="duplicates">Duplicates Only</option>
                </select>
            </div>

            <div class="grid" id="cardsGrid">
"""

    for item in article_items:
        title_esc = html.escape(item.title)
        url_esc = html.escape(item.url)
        source_esc = html.escape(item.source)
        desc_esc = html.escape(clean_display_text(item.description or "No summary available."))
        author_esc = html.escape(item.author or "Editorial")
        date_str = item.published_at.strftime("%b %d, %Y") if item.published_at else "Recent"
        is_dup = "true" if item.is_duplicate else "false"

        role_key, role_label = normalize_role_3(item.primary_role)

        res_score = getattr(item, 'researcher_score', 0.0) or 0.0
        eng_score = getattr(item, 'engineer_score', 0.0) or 0.0
        noise_score = getattr(item, 'noise_score', 0.0) or 0.0
        if noise_score == 0.0 and getattr(item, 'irrelevant_score', 0.0):
            noise_score = getattr(item, 'irrelevant_score', 0.0)

        r_pct = int(res_score * 100)
        e_pct = int(eng_score * 100)
        n_pct = int(noise_score * 100)
        conf_pct = int(item.confidence * 100) if item.confidence else max(r_pct, e_pct, n_pct)

        img_tag = f'<img src="{html.escape(item.image_url)}" class="card-img" alt="Banner" onerror="this.style.display=\'none\'">' if item.image_url else ''

        html_content += f"""
            <div class="card" data-role="{role_key}" data-source="{source_esc.lower()}" data-duplicate="{is_dup}" data-text="{title_esc.lower()} {desc_esc.lower()} {source_esc.lower()} {author_esc.lower()}">
                <div class="card-img-wrap">
                    {img_tag}
                </div>
                <div class="card-body">
                    <div class="card-top">
                        <span class="role-pill {role_key}">{role_label}</span>
                        <span class="source-tag" title="{source_esc}">{source_esc}</span>
                    </div>

                    <a href="{url_esc}" target="_blank" class="card-title" title="{title_esc}">{title_esc}</a>
                    <p class="card-desc">{desc_esc}</p>

                    <!-- 3-Role Decision Scores -->
                    <div class="scores-panel">
                        <div class="scores-title">
                            <span>Role Probabilities</span>
                            <span>Conf: {conf_pct}%</span>
                        </div>
                        <div class="score-row">
                            <span class="score-label">🔬 AI Research</span>
                            <div class="score-bar-wrap">
                                <div class="score-bar-fill" style="width: {r_pct}%; background: var(--research-color);"></div>
                            </div>
                            <span class="score-num" style="color: var(--research-color);">{r_pct}%</span>
                        </div>
                        <div class="score-row">
                            <span class="score-label">🧑‍💻 AI Engineering</span>
                            <div class="score-bar-wrap">
                                <div class="score-bar-fill" style="width: {e_pct}%; background: var(--engineer-color);"></div>
                            </div>
                            <span class="score-num" style="color: var(--engineer-color);">{e_pct}%</span>
                        </div>
                        <div class="score-row">
                            <span class="score-label">🗑️ Noise</span>
                            <div class="score-bar-wrap">
                                <div class="score-bar-fill" style="width: {n_pct}%; background: var(--noise-color);"></div>
                            </div>
                            <span class="score-num" style="color: var(--noise-color);">{n_pct}%</span>
                        </div>
                    </div>

                    <div class="card-footer">
                        <span>👤 {author_esc}</span>
                        <span>📅 {date_str}</span>
                    </div>
                </div>
            </div>
        """


    html_content += """
            </div>
        </div>

        <!-- SECTION 2: TRENDING GITHUB REPOSITORIES -->
        <div id="githubSection" class="view-section">
            <div style="margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
                <div>
                    <h2 style="font-size: 1.4rem; font-weight: 800; color: #58a6ff;">🔥 Trending GitHub Repositories (Python & AI)</h2>
                    <p style="color: var(--text-muted); font-size: 0.88rem;">Open-source AI libraries, autonomous frameworks, agent memory, and developer tooling.</p>
                </div>
            </div>
            <div class="grid">
    """

    for gh in github_items:
        title_esc = html.escape(gh.title)
        url_esc = html.escape(gh.url)
        desc_esc = html.escape(clean_display_text(gh.description or "Trending GitHub repository."))
        author_esc = html.escape(gh.author or "Open Source")
        
        html_content += f"""
            <div class="tool-card">
                <div>
                    <div class="tool-header">
                        <span class="tool-badge gh">⭐ GitHub Trending</span>
                        <span style="font-size: 0.75rem; color: var(--text-dim); font-family: 'JetBrains Mono', monospace;">🐍 Python / AI</span>
                    </div>
                    <a href="{url_esc}" target="_blank" class="tool-title">{title_esc}</a>
                    <p class="tool-desc" style="margin-top: 0.6rem;">{desc_esc}</p>
                </div>
                <div class="tool-meta">
                    <span>👤 {author_esc}</span>
                    <a href="{url_esc}" target="_blank" class="tool-btn">View Code ↗</a>
                </div>
            </div>
        """

    html_content += """
            </div>
        </div>

        <!-- SECTION 3: TRENDING HUGGING FACE MODELS -->
        <div id="hfSection" class="view-section">
            <div style="margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
                <div>
                    <h2 style="font-size: 1.4rem; font-weight: 800; color: #fbbf24;">🤗 Trending Hugging Face Models & Checkpoints</h2>
                    <p style="color: var(--text-muted); font-size: 0.88rem;">Latest trending open-weights models, vision systems, and text generation checkpoints.</p>
                </div>
            </div>
            <div class="grid">
    """

    for hf in hf_model_items:
        title_esc = html.escape(hf.title)
        url_esc = html.escape(hf.url)
        desc_esc = html.escape(clean_display_text(hf.description or "Trending open weights model."))
        author_esc = html.escape(hf.author or "Hugging Face")
        
        html_content += f"""
            <div class="tool-card">
                <div>
                    <div class="tool-header">
                        <span class="tool-badge hf">🤗 Hugging Face</span>
                        <span style="font-size: 0.75rem; color: var(--text-dim); font-family: 'JetBrains Mono', monospace;">⚡ Open Weights</span>
                    </div>
                    <a href="{url_esc}" target="_blank" class="tool-title">{title_esc}</a>
                    <p class="tool-desc" style="margin-top: 0.6rem;">{desc_esc}</p>
                </div>
                <div class="tool-meta">
                    <span>👤 {author_esc}</span>
                    <a href="{url_esc}" target="_blank" class="tool-btn">Model Card ↗</a>
                </div>
            </div>
        """

    html_content += """
            </div>
        </div>
    </div>

    <script>
        let currentRole = 'all';

        function switchSection(sectionId, btnEl) {
            document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            
            const targetSection = document.getElementById(sectionId);
            if (targetSection) {
                targetSection.classList.add('active');
            }
            if (btnEl) {
                btnEl.classList.add('active');
            }
        }

        function selectRoleTab(role, tabEl) {
            currentRole = role;
            document.querySelectorAll('.role-tab').forEach(t => t.classList.remove('active'));
            tabEl.classList.add('active');
            filterCards();
        }

        function filterCards() {
            const search = document.getElementById('searchInput').value.toLowerCase();
            const source = document.getElementById('sourceFilter').value.toLowerCase();
            const duplicate = document.getElementById('duplicateFilter').value;

            const cards = document.querySelectorAll('#cardsGrid .card');

            cards.forEach(card => {
                const cardRole = card.getAttribute('data-role');
                const cardSource = card.getAttribute('data-source');
                const isDup = card.getAttribute('data-duplicate');
                const cardText = card.getAttribute('data-text');

                const matchesRole = (currentRole === 'all') || (cardRole === currentRole);
                const matchesSearch = !search || cardText.includes(search);
                const matchesSource = !source || cardSource === source;
                
                let matchesDup = true;
                if (duplicate === 'unique') matchesDup = (isDup === 'false');
                if (duplicate === 'duplicates') matchesDup = (isDup === 'true');

                if (matchesRole && matchesSearch && matchesSource && matchesDup) {
                    card.style.display = 'flex';
                } else {
                    card.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""

    out_file = Path(output_path)
    out_file.write_text(html_content, encoding="utf-8")
    return str(out_file.resolve())


if __name__ == "__main__":
    path = generate_html_report("report.html")
    print(f"Report successfully generated at: {path}")
