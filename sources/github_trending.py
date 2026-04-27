"""GitHub Trending 仓库采集"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime


TRENDING_URL = "https://github.com/trending"


def fetch_trending(config, github_token=""):
    """抓取 GitHub Trending 页面，返回项目列表"""
    repos = []
    headers = {"Accept": "text/html"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    languages = config.get("languages", [""])
    since = config.get("since", "weekly")
    max_per_lang = config.get("max_per_language", 5)

    for lang in languages:
        params = {"since": since}
        if lang:
            params["l"] = lang

        try:
            resp = requests.get(TRENDING_URL, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[Trending] 抓取失败 (lang={lang or 'overall'}): {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.select("article.Box-row")

        count = 0
        for article in articles:
            if count >= max_per_lang:
                break

            name_el = article.select_one("h2 a")
            if not name_el:
                continue

            href = name_el.get("href", "").strip("/")
            owner, repo_name = href.split("/", 1) if "/" in href else ("", href)

            desc_el = article.select_one("p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            lang_el = article.select_one("[itemprop='programmingLanguage']")
            language = lang_el.get_text(strip=True) if lang_el else ""

            stars_el = article.select_one("a.Link--muted")
            total_stars = 0
            if stars_el:
                stars_text = stars_el.get_text(strip=True).replace(",", "")
                try:
                    total_stars = int(stars_text)
                except ValueError:
                    pass

            # 本周/本期新增 star
            gained_stars = 0
            gained_el = article.select_one(".float-sm-right")
            if gained_el:
                gained_text = gained_el.get_text(strip=True)
                gained_text = gained_text.replace(",", "").replace("stars today", "").replace("stars this week", "").replace("stars this month", "").strip()
                try:
                    gained_stars = int(gained_text)
                except ValueError:
                    pass

            repos.append({
                "name": f"{owner}/{repo_name}" if owner else repo_name,
                "url": f"https://github.com/{href}",
                "description": description,
                "language": language,
                "stars": total_stars,
                "gained_stars": gained_stars,
                "source": "trending",
                "source_detail": f"Trending ({lang or 'overall'})",
            })
            count += 1

    print(f"[Trending] 共抓取 {len(repos)} 个项目")
    return repos
