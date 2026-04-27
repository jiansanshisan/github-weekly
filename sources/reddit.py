"""Reddit 上提到的 GitHub 项目采集"""

import re
import requests
from datetime import datetime, timedelta


REDDIT_BASE = "https://www.reddit.com"


def fetch_reddit(config, github_token=""):
    """从 Reddit 技术板块抓取包含 GitHub 链接的热门帖子"""
    repos = []
    max_results = config.get("max_results", 15)
    subreddits = config.get("subreddits", ["programming"])
    min_score = config.get("min_score", 50)
    days_range = config.get("days_range", 7)

    headers = {"User-Agent": "github-weekly-report/1.0"}
    seen_urls = set()

    since_timestamp = (datetime.utcnow() - timedelta(days=days_range)).timestamp()

    for subreddit in subreddits:
        url = f"{REDDIT_BASE}/r/{subreddit}/hot.json"
        params = {"limit": 30}

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[Reddit] r/{subreddit} 抓取失败: {e}")
            continue

        for child in resp.json().get("data", {}).get("children", []):
            post = child.get("data", {})

            if post.get("score", 0) < min_score:
                continue

            # 检查帖子创建时间
            created = post.get("created_utc", 0)
            if created < since_timestamp:
                continue

            # 在 URL 和正文中搜索 github.com 链接
            texts_to_check = [
                post.get("url", ""),
                post.get("selftext", ""),
                post.get("title", ""),
            ]

            for text in texts_to_check:
                github_matches = re.findall(
                    r"github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)", text
                )
                for owner, repo_name in github_matches:
                    skip_paths = ["issues", "pull", "blob", "tree", "wiki", "blog", "features"]
                    if repo_name.lower() in skip_paths:
                        continue

                    repo_url = f"https://github.com/{owner}/{repo_name}"
                    if repo_url in seen_urls:
                        continue
                    seen_urls.add(repo_url)

                    reddit_permalink = f"{REDDIT_BASE}{post.get('permalink', '')}"

                    repos.append({
                        "name": f"{owner}/{repo_name}",
                        "url": repo_url,
                        "description": post.get("title", ""),
                        "language": "",
                        "stars": 0,
                        "gained_stars": 0,
                        "source": "reddit",
                        "source_detail": f"Reddit r/{subreddit} ({post.get('score', 0)} upvotes)",
                        "reddit_link": reddit_permalink,
                        "reddit_score": post.get("score", 0),
                    })

                    if len(repos) >= max_results:
                        break
                if len(repos) >= max_results:
                    break
            if len(repos) >= max_results:
                break
        if len(repos) >= max_results:
            break

    print(f"[Reddit] 共抓取 {len(repos)} 个项目")
    return repos
