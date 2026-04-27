"""
GitHub 热点周报系统 - 主入口
用法: python main.py
"""

import os
import yaml
from datetime import datetime
from pathlib import Path

from sources.github_trending import fetch_trending
from sources.star_growth import fetch_star_growth
from sources.hackernews import fetch_hackernews
from sources.reddit import fetch_reddit
from sources.github_releases import fetch_releases
from summarizer import generate_summaries, generate_overview
from renderer import render_html


def load_config():
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    github_token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")

    if deepseek_api_key:
        config.setdefault("deepseek", {})["api_key"] = deepseek_api_key
    if github_token:
        config["github_token"] = github_token

    return config


def collect_all(config):
    """从所有数据源采集项目"""
    github_token = config.get("github_token", "")
    sources_config = config.get("sources", {})
    all_projects = []

    # 1. GitHub Trending
    if sources_config.get("trending", {}).get("enabled", True):
        print("\n" + "=" * 50)
        print("📊 正在抓取 GitHub Trending...")
        projects = fetch_trending(sources_config["trending"], github_token)
        all_projects.extend(projects)

    # 2. Star 增长
    if sources_config.get("star_growth", {}).get("enabled", True):
        print("\n" + "=" * 50)
        print("⭐ 正在搜索 Star 飙升项目...")
        projects = fetch_star_growth(sources_config["star_growth"], github_token)
        all_projects.extend(projects)

    # 3. HackerNews
    if sources_config.get("hackernews", {}).get("enabled", True):
        print("\n" + "=" * 50)
        print("🔶 正在抓取 HackerNews...")
        projects = fetch_hackernews(sources_config["hackernews"], github_token)
        all_projects.extend(projects)

    # 4. Reddit
    if sources_config.get("reddit", {}).get("enabled", True):
        print("\n" + "=" * 50)
        print("🔴 正在抓取 Reddit...")
        projects = fetch_reddit(sources_config["reddit"], github_token)
        all_projects.extend(projects)

    # 5. GitHub Releases
    if sources_config.get("releases", {}).get("enabled", True):
        print("\n" + "=" * 50)
        print("📦 正在检查新版本发布...")
        projects = fetch_releases(sources_config["releases"], github_token)
        all_projects.extend(projects)

    return all_projects


def deduplicate(projects):
    """按项目名去重，保留优先级更高的来源版本"""
    seen = {}
    source_priority = {
        "trending": 1,
        "releases": 2,
        "hackernews": 3,
        "reddit": 4,
        "star_growth": 5,
    }

    for p in projects:
        name = p["name"].lower()
        if name not in seen:
            seen[name] = p
        else:
            existing = seen[name]
            existing_priority = source_priority.get(existing["source"], 99)
            current_priority = source_priority.get(p["source"], 99)
            if current_priority < existing_priority:
                seen[name] = p

    deduped = list(seen.values())
    print(f"\n[去重] {len(projects)} → {len(deduped)} 个项目")
    return deduped


def group_by_source(projects):
    """按来源分组"""
    groups = {}
    for p in projects:
        source = p.get("source", "other")
        if source not in groups:
            groups[source] = []
        groups[source].append(p)
    return groups


def main():
    print("🚀 GitHub 热点周报系统")
    print("=" * 50)

    config = load_config()

    # 1. 采集数据
    all_projects = collect_all(config)

    if not all_projects:
        print("\n❌ 未抓取到任何项目，请检查网络连接和配置")
        return

    # 2. 去重
    projects = deduplicate(all_projects)

    # 3. 按 star 增长量排序（有增长量的排前面，其次按总 star 数）
    projects.sort(key=lambda p: (p.get("gained_stars", 0), p.get("stars", 0)), reverse=True)
    print(f"\n[排序] 按 star 增长量排序完成")

    # 4. 生成摘要
    print("\n" + "=" * 50)
    print("🤖 正在生成 AI 摘要...")
    max_projects = config.get("summary", {}).get("max_projects", 50)
    projects = projects[:max_projects]
    projects = generate_summaries(projects, config)

    # 5. 生成周报总览
    print("\n" + "=" * 50)
    print("📝 正在生成周报总览...")
    overview = generate_overview(projects, config)

    # 6. 按来源分组（组内保持 star 排序）
    grouped = group_by_source(projects)

    # 7. 渲染 HTML
    print("\n" + "=" * 50)
    print("🎨 正在生成周报网页...")

    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = config.get("output", {}).get("dir", "output")
    filename_template = config.get("output", {}).get("filename_template", "weekly_{date}.html")
    filename = filename_template.replace("{date}", date_str)

    output_path = Path(__file__).parent / output_dir / filename
    render_html(grouped, str(output_path), date_str, overview)

    print("\n" + "=" * 50)
    print(f"✅ 周报生成完成！")
    print(f"📄 文件位置: {output_path}")
    print(f"📊 共收录 {len(projects)} 个项目")
    print("=" * 50)


if __name__ == "__main__":
    main()
