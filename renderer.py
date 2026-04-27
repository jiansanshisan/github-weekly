"""卡片式静态 HTML 周报渲染器"""

import os
import re
from datetime import datetime


# 语言对应的颜色
LANG_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Java": "#b07219",
    "C++": "#f34b7d",
    "C": "#555555",
    "C#": "#178600",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Dart": "#00B4AB",
    "Shell": "#89e051",
    "Lua": "#000080",
    "Zig": "#ec915c",
    "Vue": "#41b883",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "": "#999999",
}


def _lang_color(lang):
    return LANG_COLORS.get(lang, "#999999")


def _escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _parse_summary_sections(summary):
    """将摘要文本按【小标题】解析为结构化段落"""
    # 匹配 【xxx】 开头的段落
    pattern = r'【([^】]+)】\s*(.+?)(?=【|$)'
    matches = re.findall(pattern, summary, re.DOTALL)

    # 小标题对应的图标和颜色
    section_config = {
        "定位": ("icon-target", "#6e40c9"),
        "亮点": ("icon-bolt", "#cf222e"),
        "场景": ("icon-globe", "#0969da"),
        "热度": ("icon-fire", "#bc4c00"),
    }

    if not matches:
        # 没有匹配到格式，返回整段文本
        return f'<p>{_escape_html(summary)}</p>'

    sections_html = ""
    for title, content in matches:
        title = title.strip()
        content = content.strip()
        if not content:
            continue
        icon_class, color = section_config.get(title, ("icon-info", "#656d76"))
        sections_html += f'''
            <div class="summary-section">
                <span class="section-label" style="color:{color};border-color:{color}">{title}</span>
                <span class="section-content">{_escape_html(content)}</span>
            </div>'''

    return sections_html


def _split_overview_line(text):
    """Split a short generated overview line into a heading and body."""
    text = text.strip()
    for separator in ("：", ":", " - ", " — "):
        if separator in text:
            title, body = text.split(separator, 1)
            title = title.strip(" -•*0123456789.、)")
            body = body.strip()
            if title and body and len(title) <= 36:
                return title, body
    return "", text


def _render_card(project):
    """渲染单个项目卡片"""
    name = _escape_html(project.get("name", ""))
    url = project.get("url", "#")
    summary = project.get("summary", project.get("description", ""))
    language = _escape_html(project.get("language", ""))
    stars = project.get("stars", 0)
    gained = project.get("gained_stars", 0)
    source_detail = _escape_html(project.get("source_detail", ""))
    source = project.get("source", "")

    lang_color = _lang_color(language)

    # 解析摘要为分段
    summary_html = _parse_summary_sections(summary)

    stars_html = ""
    if stars > 0:
        stars_html = f'<span class="stars">&#9733; {stars:,}</span>'
    if gained > 0:
        stars_html += f'<span class="gained">+{gained:,} this week</span>'

    # Release 信息
    release_html = ""
    if project.get("release_tag"):
        tag = _escape_html(project["release_tag"])
        release_url = project.get("release_url", url)
        release_date = project.get("release_date", "")
        release_html = f'''
        <div class="release-info">
            <span class="release-tag">{tag}</span>
            <span class="release-date">{release_date}</span>
            <a href="{release_url}" target="_blank" class="release-link">Release Notes</a>
        </div>'''

    # 社区链接
    community_html = ""
    if project.get("hn_link"):
        community_html += f'<a href="{project["hn_link"]}" target="_blank" class="community-link">HN 讨论 ({project.get("hn_points", 0)} pts)</a>'
    if project.get("reddit_link"):
        community_html += f'<a href="{project["reddit_link"]}" target="_blank" class="community-link">Reddit 讨论 ({project.get("reddit_score", 0)} upvotes)</a>'

    # 来源标签颜色
    source_colors = {
        "trending": "#0e7a3f",
        "star_growth": "#c9820a",
        "hackernews": "#ff6600",
        "reddit": "#ff4500",
        "releases": "#6e40c9",
    }
    source_color = source_colors.get(source, "#666")

    return f'''
    <div class="card" data-source="{source}">
        <div class="card-header">
            <div class="card-title-row">
                <a href="{url}" target="_blank" class="card-title">{name}</a>
                <span class="source-badge" style="background-color:{source_color}">{source_detail}</span>
            </div>
            <div class="card-meta">
                <span class="lang-dot" style="background-color:{lang_color}"></span>
                <span class="lang-name">{language or 'N/A'}</span>
                {stars_html}
            </div>
        </div>
        <div class="card-body">
            {summary_html}
        </div>
        <div class="card-footer">
            <a href="{url}" target="_blank" class="repo-link">&#128279; 查看项目</a>
            {community_html}
        </div>
        {release_html}
    </div>'''


def _render_overview(overview_text):
    """将总览文本渲染为 HTML 模块"""
    if not overview_text:
        return ""

    # 解析两部分
    trends_html = ""
    picks_html = ""

    # 匹配 ===趋势综述=== 和 ===精选推荐=== 之间的内容
    trends_match = re.search(r'===趋势综述===\s*(.+?)(?====精选推荐===|$)', overview_text, re.DOTALL)
    picks_match = re.search(r'===精选推荐===\s*(.+?)$', overview_text, re.DOTALL)

    if trends_match:
        trends_content = trends_match.group(1).strip()
        # 按段落拆分（空行分隔）
        paragraphs = [p.strip() for p in trends_content.split("\n\n") if p.strip()]
        for idx, p in enumerate(paragraphs, 1):
            # 清理开头的 - 或数字前缀
            p = re.sub(r'^[-•]\s*', '', p)
            p = re.sub(r'^\d+[.、]\s*', '', p)
            title, body = _split_overview_line(p)
            if title:
                trends_html += f'''
                <article class="trend-item">
                    <span class="overview-number">{idx:02d}</span>
                    <div>
                        <h4>{_escape_html(title)}</h4>
                        <p>{_escape_html(body)}</p>
                    </div>
                </article>'''
            else:
                trends_html += f'''
                <article class="trend-item">
                    <span class="overview-number">{idx:02d}</span>
                    <p>{_escape_html(body)}</p>
                </article>'''

    if picks_match:
        picks_content = picks_match.group(1).strip()
        # 按行拆分精选推荐
        lines = [l.strip() for l in picks_content.split("\n") if l.strip()]
        for idx, line in enumerate(lines, 1):
            # 清理前缀
            line = re.sub(r'^[-•*\d.、)\s]+', '', line)
            if not line:
                continue
            title, body = _split_overview_line(line)
            if title:
                picks_html += f'''
                <article class="pick-item">
                    <span class="pick-rank">{idx}</span>
                    <div>
                        <h4>{_escape_html(title)}</h4>
                        <p>{_escape_html(body)}</p>
                    </div>
                </article>'''
            else:
                picks_html += f'''
                <article class="pick-item">
                    <span class="pick-rank">{idx}</span>
                    <p>{_escape_html(body)}</p>
                </article>'''

    # 如果解析失败，回退为纯文本
    if not trends_html and not picks_html:
        trends_html = f'''
        <article class="trend-item">
            <span class="overview-number">01</span>
            <p>{_escape_html(overview_text)}</p>
        </article>'''

    trends_section = ""
    if trends_html:
        trends_section = f'''
        <div class="overview-part overview-trends">
            <div class="overview-part-heading">
                <span class="overview-kicker">Trends</span>
                <h3 class="overview-part-title">趋势综述</h3>
            </div>
            <div class="trends-list">{trends_html}</div>
        </div>'''

    picks_section = ""
    if picks_html:
        picks_section = f'''
        <div class="overview-part overview-picks">
            <div class="overview-part-heading">
                <span class="overview-kicker">Picks</span>
                <h3 class="overview-part-title">精选推荐</h3>
            </div>
            <div class="picks-list">{picks_html}</div>
        </div>'''

    return f'''
    <section class="overview-section" id="section-overview">
        <div class="overview-header">
            <div>
                <span class="overview-eyebrow">Weekly Brief</span>
                <h2>本周概览</h2>
            </div>
            <span class="overview-date">{datetime.now().strftime("%m.%d")}</span>
        </div>
        <div class="overview-content">
            {trends_section}
            {picks_section}
        </div>
    </section>'''


def render_html(projects_by_source, output_path, date_str, overview=None):
    """生成完整的 HTML 周报（按来源分组，组内按 star 排序）"""

    source_titles = {
        "trending": "🔥 GitHub Trending",
        "star_growth": "🚀 Star 飙升",
        "hackernews": "🔶 HackerNews 热议",
        "reddit": "🔴 Reddit 讨论",
        "releases": "📦 新版本发布",
    }

    sections_html = ""
    total_count = 0
    nav_items = ""

    # 渲染总览模块
    overview_html = _render_overview(overview)
    if overview_html:
        sections_html += overview_html
        total_count += 0  # 总览不计入项目数
        nav_items += '<a href="#section-overview" class="nav-link">本周概览</a>'

    for source, title in source_titles.items():
        projects = projects_by_source.get(source, [])
        if not projects:
            continue

        total_count += len(projects)
        cards_html = "\n".join(_render_card(p) for p in projects)

        sections_html += f'''
        <section class="section" id="section-{source}">
            <h2 class="section-title">{title} <span class="count">({len(projects)})</span></h2>
            <div class="card-grid">
                {cards_html}
            </div>
        </section>'''

        nav_items += f'<a href="#section-{source}" class="nav-link">{title.split(" ", 1)[1]} ({len(projects)})</a>'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub 热点周报 - {date_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f6f8fa;
            color: #24292f;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        header {{
            text-align: center;
            padding: 40px 20px 30px;
            background: linear-gradient(135deg, #24292f 0%, #2d333b 100%);
            color: white;
            margin-bottom: 30px;
            border-radius: 12px;
        }}
        header h1 {{
            font-size: 28px;
            margin-bottom: 8px;
        }}
        header .subtitle {{
            color: #8b949e;
            font-size: 15px;
        }}
        header .stats {{
            margin-top: 12px;
            font-size: 14px;
            color: #58a6ff;
            display: flex;
            justify-content: center;
            gap: 16px;
            flex-wrap: wrap;
        }}
        .stat-item {{
            background: rgba(255,255,255,0.1);
            padding: 3px 12px;
            border-radius: 12px;
        }}
        nav {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: center;
            margin-bottom: 30px;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }}
        .nav-link {{
            padding: 6px 14px;
            background: #f6f8fa;
            border-radius: 20px;
            text-decoration: none;
            color: #24292f;
            font-size: 13px;
            border: 1px solid #d0d7de;
            transition: all 0.2s;
        }}
        .nav-link:hover {{
            background: #24292f;
            color: white;
            border-color: #24292f;
        }}
        .overview-section {{
            position: relative;
            overflow: hidden;
            background: #ffffff;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 40px;
            border: 1px solid #d0d7de;
            box-shadow: 0 10px 30px rgba(27, 31, 36, 0.06);
        }}
        .overview-section::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 5px;
            background: linear-gradient(90deg, #0969da, #1a7f37, #bc4c00);
        }}
        .overview-header {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 18px;
            margin-bottom: 24px;
        }}
        .overview-eyebrow,
        .overview-kicker {{
            display: inline-block;
            color: #0969da;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .overview-header h2 {{
            margin-top: 3px;
            font-size: 26px;
            line-height: 1.25;
            color: #24292f;
        }}
        .overview-date {{
            min-width: 58px;
            padding: 8px 10px;
            border: 1px solid #d0d7de;
            border-radius: 8px;
            color: #57606a;
            background: #f6f8fa;
            font-size: 13px;
            font-weight: 700;
            text-align: center;
        }}
        .overview-content {{
            display: grid;
            grid-template-columns: minmax(0, 1.15fr) minmax(300px, 0.85fr);
            gap: 18px;
        }}
        .overview-part {{
            min-width: 0;
            border: 1px solid #d8dee4;
            border-radius: 10px;
            background: #fbfbfc;
            padding: 18px;
        }}
        .overview-part-heading {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 14px;
        }}
        .overview-part-title {{
            font-size: 16px;
            font-weight: 600;
            color: #24292f;
            margin: 0;
        }}
        .trends-list {{
            display: grid;
            gap: 12px;
        }}
        .trend-item {{
            display: grid;
            grid-template-columns: 42px minmax(0, 1fr);
            gap: 12px;
            font-size: 14px;
            color: #424a53;
            line-height: 1.7;
            padding: 14px;
            border: 1px solid #d8dee4;
            border-radius: 8px;
            background: white;
        }}
        .trend-item h4,
        .pick-item h4 {{
            margin: 0 0 4px;
            color: #24292f;
            font-size: 14px;
            line-height: 1.35;
        }}
        .trend-item p,
        .pick-item p {{
            margin: 0;
        }}
        .overview-number {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 34px;
            height: 34px;
            border-radius: 50%;
            background: #ddf4ff;
            color: #0969da;
            font-size: 12px;
            font-weight: 700;
        }}
        .picks-list {{
            display: grid;
            gap: 10px;
        }}
        .pick-item {{
            display: grid;
            grid-template-columns: 28px minmax(0, 1fr);
            gap: 10px;
            font-size: 14px;
            color: #424a53;
            line-height: 1.6;
            padding: 12px;
            background: white;
            border: 1px solid #d8dee4;
            border-radius: 8px;
        }}
        .pick-rank {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 24px;
            height: 24px;
            border-radius: 6px;
            background: #dafbe1;
            color: #1a7f37;
            font-size: 12px;
            font-weight: 700;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section-title {{
            font-size: 22px;
            padding-bottom: 10px;
            border-bottom: 2px solid #d0d7de;
            margin-bottom: 20px;
        }}
        .section-title .count {{
            font-size: 14px;
            color: #8b949e;
            font-weight: normal;
        }}
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
        }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #d0d7de;
            transition: box-shadow 0.2s, transform 0.15s;
            display: flex;
            flex-direction: column;
        }}
        .card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }}
        .card-header {{
            margin-bottom: 12px;
        }}
        .card-title-row {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 8px;
            margin-bottom: 6px;
        }}
        .card-title {{
            font-size: 16px;
            font-weight: 600;
            color: #0969da;
            text-decoration: none;
            word-break: break-all;
        }}
        .card-title:hover {{
            text-decoration: underline;
        }}
        .source-badge {{
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 12px;
            color: white;
            white-space: nowrap;
            flex-shrink: 0;
        }}
        .card-meta {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: #656d76;
        }}
        .lang-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }}
        .lang-name {{ font-weight: 500; }}
        .stars {{ color: #e3b341; font-weight: 500; }}
        .gained {{ color: #1a7f37; font-size: 12px; }}
        .card-body {{
            flex: 1;
            font-size: 14px;
            color: #424a53;
            line-height: 1.7;
        }}
        .card-body p {{
            margin-bottom: 0;
        }}
        .summary-section {{
            display: flex;
            align-items: baseline;
            gap: 8px;
            margin-bottom: 8px;
            line-height: 1.6;
        }}
        .summary-section:last-child {{
            margin-bottom: 0;
        }}
        .section-label {{
            font-size: 12px;
            font-weight: 600;
            padding: 1px 7px;
            border-radius: 4px;
            border: 1px solid;
            white-space: nowrap;
            flex-shrink: 0;
            background: rgba(0,0,0,0.02);
        }}
        .section-content {{
            font-size: 13.5px;
            color: #424a53;
        }}
        .card-footer {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-top: 14px;
            padding-top: 12px;
            border-top: 1px solid #f0f0f0;
        }}
        .repo-link {{
            font-size: 13px;
            color: #0969da;
            text-decoration: none;
        }}
        .repo-link:hover {{ text-decoration: underline; }}
        .community-link {{
            font-size: 12px;
            color: #656d76;
            text-decoration: none;
            background: #f6f8fa;
            padding: 2px 8px;
            border-radius: 10px;
            border: 1px solid #d0d7de;
        }}
        .community-link:hover {{
            background: #eaeef2;
        }}
        .release-info {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px dashed #d0d7de;
            font-size: 13px;
        }}
        .release-tag {{
            background: #ddf4ff;
            color: #0969da;
            padding: 2px 8px;
            border-radius: 10px;
            font-weight: 600;
        }}
        .release-date {{ color: #8b949e; }}
        .release-link {{
            color: #0969da;
            text-decoration: none;
            margin-left: auto;
        }}
        .release-link:hover {{ text-decoration: underline; }}
        footer {{
            text-align: center;
            padding: 30px;
            color: #8b949e;
            font-size: 13px;
        }}
        @media (max-width: 768px) {{
            .container {{
                padding: 12px;
            }}
            .card-grid {{
                grid-template-columns: 1fr;
            }}
            .overview-section {{
                padding: 22px 16px;
                border-radius: 10px;
            }}
            .overview-header {{
                margin-bottom: 18px;
            }}
            .overview-header h2 {{
                font-size: 22px;
            }}
            .overview-content {{
                grid-template-columns: 1fr;
                gap: 14px;
            }}
            .overview-part {{
                padding: 14px;
            }}
            .trend-item {{
                grid-template-columns: 34px minmax(0, 1fr);
                padding: 12px;
            }}
            .overview-number {{
                width: 30px;
                height: 30px;
            }}
            .pick-item {{
                padding: 11px;
            }}
            header h1 {{ font-size: 22px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>GitHub 热点周报</h1>
            <div class="subtitle">{date_str}</div>
            <div class="stats">共收录 {total_count} 个热点项目</div>
        </header>

        <nav>{nav_items}</nav>

        {sections_html}

        <footer>
            <p>由 GitHub Weekly Report 系统自动生成 | 数据来源于 GitHub / HackerNews / Reddit</p>
        </footer>
    </div>
</body>
</html>'''

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[Renderer] 周报已生成: {output_path}")
    return output_path
