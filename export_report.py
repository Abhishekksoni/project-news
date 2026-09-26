"""Generate an interactive HTML report to inspect all fetched news items."""

import html
from pathlib import Path
from storage.database import get_news_items, get_total_count, init_db


def generate_html_report(output_path: str = "report.html") -> str:
    init_db()
    items = get_news_items(limit=500, only_unique=False)
    stats = get_total_count()

    categories = sorted(list({item.category for item in items if item.category}))
    sources = sorted(list({item.source for item in items if item.source}))

    # HTML template with modern styling, instant search, and category filtering
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project News Quality & Relevance Inspector</title>
    <style>
        :root {{
            --bg: #0f172a;
            --card-bg: #1e293b;
            --card-border: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --accent-green: #4ade80;
            --accent-purple: #c084fc;
            --accent-orange: #fb923c;
            --badge-bg: #334155;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        body {{
            background-color: var(--bg);
            color: var(--text-main);
            padding: 2rem;
            line-height: 1.5;
        }}
        .header {{
            max-width: 1200px;
            margin: 0 auto 2rem auto;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 1.5rem;
        }}
        .header h1 {{
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(to right, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        .stats-bar {{
            display: flex;
            gap: 1.5rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }}
        .stat-badge {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-size: 0.9rem;
        }}
        .stat-value {{
            font-weight: bold;
            color: var(--accent);
        }}
        .controls {{
            max-width: 1200px;
            margin: 0 auto 2rem auto;
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            align-items: center;
        }}
        .search-box {{
            flex: 1;
            min-width: 250px;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            color: var(--text-main);
            font-size: 1rem;
            outline: none;
        }}
        .search-box:focus {{
            border-color: var(--accent);
        }}
        .filter-select {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            color: var(--text-main);
            font-size: 0.9rem;
            outline: none;
            cursor: pointer;
        }}
        .grid {{
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
            gap: 1.5rem;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}
        .card:hover {{
            transform: translateY(-2px);
            border-color: #475569;
        }}
        .card-img {{
            width: 100%;
            height: 180px;
            object-fit: cover;
            background-color: #0b1120;
            border-bottom: 1px solid var(--card-border);
        }}
        .card-body {{
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            flex-grow: 1;
        }}
        .badges {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-bottom: 0.75rem;
        }}
        .badge {{
            font-size: 0.75rem;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            background: var(--badge-bg);
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge-source {{
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent);
            border: 1px solid rgba(56, 189, 248, 0.3);
        }}
        .badge-dup {{
            background: rgba(239, 68, 68, 0.2);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.4);
        }}
        .card-title {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
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
            font-size: 0.88rem;
            color: var(--text-muted);
            margin-bottom: 1rem;
            flex-grow: 1;
            display: -webkit-box;
            -webkit-line-clamp: 4;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .card-footer {{
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 0.75rem;
            font-size: 0.75rem;
            color: var(--text-muted);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .author {{
            max-width: 180px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Project News Inspector</h1>
        <p style="color: var(--text-muted);">Inspection and quality verification tool for all collected feeds and articles.</p>
        <div class="stats-bar">
            <div class="stat-badge">Total Articles: <span class="stat-value">{stats['total']}</span></div>
            <div class="stat-badge">Unique Items: <span class="stat-value" style="color: var(--accent-green);">{stats['unique']}</span></div>
            <div class="stat-badge">Duplicates Flagged: <span class="stat-value" style="color: #f87171;">{stats['duplicates']}</span></div>
            <div class="stat-badge">Sources Active: <span class="stat-value">{len(sources)}</span></div>
        </div>
    </div>

    <div class="controls">
        <input type="text" id="searchInput" class="search-box" placeholder="Search titles, abstracts, authors, keywords..." oninput="filterCards()">
        
        <select id="sourceFilter" class="filter-select" onchange="filterCards()">
            <option value="">All Sources ({len(sources)})</option>
            {"".join(f'<option value="{html.escape(s)}">{html.escape(s)}</option>' for s in sources)}
        </select>

        <select id="categoryFilter" class="filter-select" onchange="filterCards()">
            <option value="">All Categories ({len(categories)})</option>
            {"".join(f'<option value="{html.escape(c)}">{html.escape(c)}</option>' for c in categories)}
        </select>

        <select id="duplicateFilter" class="filter-select" onchange="filterCards()">
            <option value="all">All Items</option>
            <option value="unique" selected>Only Unique Items</option>
            <option value="duplicates">Only Duplicates</option>
        </select>
    </div>

    <div class="grid" id="cardsGrid">
"""

    for item in items:
        title_esc = html.escape(item.title)
        url_esc = html.escape(item.url)
        source_esc = html.escape(item.source)
        cat_esc = html.escape(item.category or "General")
        desc_esc = html.escape(item.description or "No description provided.")
        author_esc = html.escape(item.author or "Unknown")
        date_str = item.published_at.strftime("%b %d, %Y %H:%M") if item.published_at else "No Date"
        is_dup = "true" if item.is_duplicate else "false"

        img_tag = f'<img src="{html.escape(item.image_url)}" class="card-img" alt="Thumbnail" onerror="this.style.display=\'none\'">' if item.image_url else ''

        dup_badge = '<span class="badge badge-dup">Duplicate</span>' if item.is_duplicate else ''

        html_content += f"""
        <div class="card" data-source="{source_esc.lower()}" data-category="{cat_esc.lower()}" data-duplicate="{is_dup}" data-text="{title_esc.lower()} {desc_esc.lower()} {author_esc.lower()}">
            {img_tag}
            <div class="card-body">
                <div class="badges">
                    <span class="badge badge-source">{source_esc}</span>
                    <span class="badge">{cat_esc}</span>
                    {dup_badge}
                </div>
                <a href="{url_esc}" target="_blank" class="card-title" title="{title_esc}">{title_esc}</a>
                <p class="card-desc">{desc_esc}</p>
                <div class="card-footer">
                    <span class="author">👤 {author_esc}</span>
                    <span>📅 {date_str}</span>
                </div>
            </div>
        </div>
        """

    html_content += """
    </div>

    <script>
        function filterCards() {
            const search = document.getElementById('searchInput').value.toLowerCase();
            const source = document.getElementById('sourceFilter').value.toLowerCase();
            const category = document.getElementById('categoryFilter').value.toLowerCase();
            const duplicate = document.getElementById('duplicateFilter').value;

            const cards = document.querySelectorAll('.card');
            let visibleCount = 0;

            cards.forEach(card => {
                const cardSource = card.getAttribute('data-source');
                const cardCat = card.getAttribute('data-category');
                const isDup = card.getAttribute('data-duplicate');
                const cardText = card.getAttribute('data-text');

                const matchesSearch = !search || cardText.includes(search);
                const matchesSource = !source || cardSource === source;
                const matchesCat = !category || cardCat === category;
                
                let matchesDup = true;
                if (duplicate === 'unique') matchesDup = (isDup === 'false');
                if (duplicate === 'duplicates') matchesDup = (isDup === 'true');

                if (matchesSearch && matchesSource && matchesCat && matchesDup) {
                    card.style.display = 'flex';
                    visibleCount++;
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
