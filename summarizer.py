"""DeepSeek 摘要生成模块"""

import requests


def fetch_readme(repo_name, github_token=""):
    """获取项目 README 内容（前 2000 字）"""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    url = f"https://api.github.com/repos/{repo_name}/readme"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            import base64
            content = resp.json().get("content", "")
            decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
            return decoded[:2000]
    except Exception:
        pass
    return ""


def generate_summaries(projects, config):
    """批量生成项目摘要"""
    api_key = config["deepseek"]["api_key"]
    base_url = config["deepseek"]["base_url"]
    model = config["deepseek"]["model"]
    prompt_template = config["summary"]["prompt_template"]
    language = config["summary"]["language"]
    github_token = config.get("github_token", "")

    if api_key == "YOUR_DEEPSEEK_API_KEY":
        print("[Summarizer] 警告：未配置 DeepSeek API Key，跳过摘要生成")
        for p in projects:
            p["summary"] = p.get("description", "暂无摘要")
        return projects

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for i, project in enumerate(projects):
        print(f"[Summarizer] 生成摘要 ({i+1}/{len(projects)}): {project['name']}")

        # 获取 README
        readme = fetch_readme(project["name"], github_token)

        # 如果有 release_body（来自 releases 源），也加入
        extra_info = ""
        if project.get("release_body"):
            extra_info = f"\n最新 Release 说明：{project['release_body']}"

        prompt = prompt_template.format(
            name=project["name"],
            url=project["url"],
            language=project.get("language", "未知"),
            stars=project.get("stars", 0),
            description=project.get("description", "无描述"),
            readme=readme + extra_info,
        )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": f"你是一位资深技术编辑，擅长深入分析开源项目。请用{language}撰写详细、有深度的技术摘要。"},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 600,
            "temperature": 0.3,
        }

        try:
            resp = requests.post(
                f"{base_url}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            summary = resp.json()["choices"][0]["message"]["content"].strip()
            project["summary"] = summary
        except Exception as e:
            print(f"[Summarizer] 摘要生成失败 ({project['name']}): {e}")
            project["summary"] = project.get("description", "暂无摘要")

    return projects


def generate_overview(projects, config):
    """生成周报总览：趋势综述 + 精选推荐"""
    api_key = config["deepseek"]["api_key"]
    base_url = config["deepseek"]["base_url"]
    model = config["deepseek"]["model"]

    if api_key == "YOUR_DEEPSEEK_API_KEY":
        return None

    # 构建项目清单供模型分析
    project_list = ""
    for i, p in enumerate(projects, 1):
        summary_text = p.get("summary", p.get("description", ""))
        # 截取摘要前150字避免过长
        if len(summary_text) > 150:
            summary_text = summary_text[:150] + "..."
        project_list += f"\n{i}. {p['name']} ({p.get('language', '?')}, {p.get('stars', 0)} stars) - {summary_text}"

    prompt = f"""你是一位资深技术编辑。以下是我本周收集的 {len(projects)} 个 GitHub 热门项目，请分析后输出两部分内容。

严格按以下格式输出，不要用markdown：

===趋势综述===
提炼 3-5 个本周最显著的技术趋势方向，每个趋势用一段话说明：
- 这个趋势是什么
- 代表了什么信号
- 涉及哪些项目（提到项目名即可）

===精选推荐===
从中选出 5-8 个最值得深入了解的项目，对每个项目用一两句话说明推荐理由。

项目清单：{project_list}"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一位资深技术编辑，擅长从大量开源项目中提炼趋势和发现亮点。请用中文撰写。"},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1500,
        "temperature": 0.4,
    }

    try:
        resp = requests.post(
            f"{base_url}/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()["choices"][0]["message"]["content"].strip()
        print("[Overview] 周报总览生成完成")
        return result
    except Exception as e:
        print(f"[Overview] 总览生成失败: {e}")
        return None
