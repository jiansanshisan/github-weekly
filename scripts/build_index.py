from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"


def extract_date(path):
    match = re.search(r"weekly_(\d{4}-\d{2}-\d{2})\.html$", path.name)
    return match.group(1) if match else path.stem


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    reports = sorted(OUTPUT_DIR.glob("weekly_*.html"), key=extract_date, reverse=True)

    items = "\n".join(
        f'                <li><a href="{report.name}">{extract_date(report)} 周报</a></li>'
        for report in reports
    )
    latest_link = reports[0].name if reports else "#"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub 热点周报</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f6f8fa;
            color: #24292f;
            line-height: 1.6;
        }}
        main {{
            max-width: 760px;
            margin: 0 auto;
            padding: 32px 20px;
        }}
        header {{
            margin-bottom: 24px;
        }}
        h1 {{
            margin: 0 0 8px;
            font-size: 28px;
        }}
        .latest {{
            display: inline-block;
            margin: 12px 0 20px;
            padding: 9px 14px;
            border-radius: 6px;
            background: #0969da;
            color: white;
            text-decoration: none;
            font-weight: 600;
        }}
        ul {{
            list-style: none;
            padding: 0;
            margin: 0;
            background: white;
            border: 1px solid #d0d7de;
            border-radius: 8px;
            overflow: hidden;
        }}
        li + li {{
            border-top: 1px solid #d0d7de;
        }}
        li a {{
            display: block;
            padding: 14px 16px;
            color: #0969da;
            text-decoration: none;
            font-weight: 500;
        }}
        li a:hover {{
            background: #f6f8fa;
        }}
        .empty {{
            padding: 16px;
            background: white;
            border: 1px solid #d0d7de;
            border-radius: 8px;
            color: #656d76;
        }}
    </style>
</head>
<body>
    <main>
        <header>
            <h1>GitHub 热点周报</h1>
            <p>自动生成的技术项目周报，适合在电脑和手机浏览器阅读。</p>
            <a class="latest" href="{latest_link}">查看最新周报</a>
        </header>
        <section>
            {f"<ul>{items}</ul>" if reports else '<div class="empty">还没有生成周报。</div>'}
        </section>
    </main>
</body>
</html>
"""
    (OUTPUT_DIR / "index.html").write_text(html, encoding="utf-8")
    (OUTPUT_DIR / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Generated {OUTPUT_DIR / 'index.html'} with {len(reports)} reports")


if __name__ == "__main__":
    main()
