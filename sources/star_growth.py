"""Star 增长追踪 - 搜索近期高 star 项目"""

import requests
from datetime import datetime, timedelta


GITHUB_API = "https://api.github.com"


def fetch_star_growth(config, github_token=""):
    """通过 GitHub Search API 查找近期 star 数飙升的项目"""
    repos = []
    max_results = config.get("max_results", 15)
    days_range = config.get("days_range", 7)

    since_date = (datetime.utcnow() - timedelta(days=days_range)).strftime("%Y-%m-%d")

    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    # 搜索策略：最近创建且 star 数高的项目
    queries = [
        f"created:>{since_date} stars:>100",
        f"pushed:>{since_date} stars:>5000",
    ]

    seen = set()

    for query in queries:
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": min(30, max_results),
        }

        try:
            resp = requests.get(
                f"{GITHUB_API}/search/repositories",
                params=params,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[StarGrowth] 搜索失败: {e}")
            continue

        data = resp.json()
        for item in data.get("items", []):
            full_name = item["full_name"]
            if full_name in seen:
                continue
            seen.add(full_name)

            repos.append({
                "name": full_name,
                "url": item["html_url"],
                "description": item.get("description", "") or "",
                "language": item.get("language", "") or "",
                "stars": item.get("stargazers_count", 0),
                "gained_stars": 0,  # Search API 不提供增量，需要额外 API 调用
                "source": "star_growth",
                "source_detail": "Star 飙升",
            })

            if len(repos) >= max_results:
                break

        if len(repos) >= max_results:
            break

    print(f"[StarGrowth] 共抓取 {len(repos)} 个项目")
    return repos
