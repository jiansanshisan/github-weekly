"""HackerNews 上热议的 GitHub 项目采集"""

import re
import requests
from datetime import datetime, timedelta


HN_ALGOLIA_API = "https://hn.algolia.com/api/v1/search"


def fetch_hackernews(config, github_token=""):
    """从 HackerNews 搜索包含 github.com 链接的热门文章"""
    repos = []
    max_results = config.get("max_results", 15)
    min_points = config.get("min_points", 50)
    days_range = config.get("days_range", 7)

    since_timestamp = int(
        (datetime.utcnow() - timedelta(days=days_range)).timestamp()
    )

    queries = [
        "github.com",
        "open source",
        "new framework",
        "new library",
    ]

    seen_urls = set()

    for query in queries:
        params = {
            "query": query,
            "tags": "story",
            "numericFilters": f"created_at_i>{since_timestamp},points>{min_points}",
            "hitsPerPage": 30,
        }

        try:
            resp = requests.get(HN_ALGOLIA_API, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[HN] 搜索失败: {e}")
            continue

        for hit in resp.json().get("hits", []):
            url = hit.get("url", "")
            if not url:
                continue

            # 提取 github.com 链接
            github_match = re.search(
                r"github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)", url
            )
            if not github_match:
                continue

            owner = github_match.group(1)
            repo_name = github_match.group(2)

            # 跳过非仓库页面
            skip_paths = ["issues", "pull", "blob", "tree", "wiki", "blog", "features"]
            if repo_name.lower() in skip_paths:
                continue

            repo_url = f"https://github.com/{owner}/{repo_name}"
            if repo_url in seen_urls:
                continue
            seen_urls.add(repo_url)

            hn_points = hit.get("points", 0)
            hn_title = hit.get("title", "")
            hn_id = hit.get("objectID", "")

            repos.append({
                "name": f"{owner}/{repo_name}",
                "url": repo_url,
                "description": hn_title,
                "language": "",
                "stars": 0,
                "gained_stars": 0,
                "source": "hackernews",
                "source_detail": f"HackerNews ({hn_points} pts)",
                "hn_link": f"https://news.ycombinator.com/item?id={hn_id}",
                "hn_points": hn_points,
            })

            if len(repos) >= max_results:
                break

        if len(repos) >= max_results:
            break

    print(f"[HN] 共抓取 {len(repos)} 个项目")
    return repos
