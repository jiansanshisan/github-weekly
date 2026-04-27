"""GitHub Releases 追踪 - 监控热门项目的新版本发布"""

import requests
from datetime import datetime, timedelta


GITHUB_API = "https://api.github.com"


def fetch_releases(config, github_token=""):
    """检查配置中列出的项目是否有新的 Release"""
    repos = []
    watch_repos = config.get("repos", [])
    days_range = config.get("days_range", 7)

    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    since_date = datetime.utcnow() - timedelta(days=days_range)

    for repo_full_name in watch_repos:
        try:
            # 获取仓库基本信息
            repo_resp = requests.get(
                f"{GITHUB_API}/repos/{repo_full_name}",
                headers=headers,
                timeout=15,
            )
            repo_resp.raise_for_status()
            repo_data = repo_resp.json()

            # 获取最近的 Release
            releases_resp = requests.get(
                f"{GITHUB_API}/repos/{repo_full_name}/releases",
                headers=headers,
                params={"per_page": 3},
                timeout=15,
            )
            releases_resp.raise_for_status()
            releases = releases_resp.json()

            if not releases:
                continue

            latest = releases[0]
            published_at = latest.get("published_at", "")

            # 检查是否在时间范围内
            if published_at:
                pub_date = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
                if pub_date < since_date:
                    continue
            else:
                continue

            tag_name = latest.get("tag_name", "")
            release_body = latest.get("body", "") or ""
            # 截取前 500 字符避免过长
            release_body = release_body[:500]

            repos.append({
                "name": repo_full_name,
                "url": repo_data.get("html_url", f"https://github.com/{repo_full_name}"),
                "description": repo_data.get("description", "") or "",
                "language": repo_data.get("language", "") or "",
                "stars": repo_data.get("stargazers_count", 0),
                "gained_stars": 0,
                "source": "releases",
                "source_detail": f"新版本发布: {tag_name}",
                "release_tag": tag_name,
                "release_url": latest.get("html_url", ""),
                "release_body": release_body,
                "release_date": published_at[:10] if published_at else "",
            })

        except requests.RequestException as e:
            print(f"[Releases] {repo_full_name} 获取失败: {e}")
            continue

    print(f"[Releases] 共发现 {len(repos)} 个新版本发布")
    return repos
