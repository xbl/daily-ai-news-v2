#!/usr/bin/env python3
"""
每日 AI 资讯抓取脚本（零外部依赖，纯标准库）
抓取 Hacker News (Algolia API)、TechCrunch AI、The Verge AI
按日期生成 Markdown 文件，commit 到 GitHub
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ========== 配置 ==========
REPO_PATH = Path(__file__).parent
CHINA_TZ = timezone(timedelta(hours=8))
import os
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = "xbl/daily-ai-news-v2"
REMOTE_URL = f"https://xbl:{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"

HN_KEYWORDS = ["AI", "artificial intelligence", "machine learning", "LLM", "GPT", "Claude", "OpenAI", "deep learning", "neural", "langchain", "RAG", "agent", "generative"]


# ========== RSS 抓取 ==========
def fetch_rss(url: str, source_name: str, keyword_filter: list = None) -> list:
    """用标准库抓取 RSS/Atom"""
    entries = []
    try:
        req = urllib.request.urlopen(url, timeout=15)
        raw = req.read().decode("utf-8", errors="ignore")

        root = ET.fromstring(raw)

        # 处理 Atom（namespace in tag）
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        is_atom = "feed" in root.tag or bool(root.find("atom:entry", ns) or root.find(".//{http://www.w3.org/2005/Atom}entry"))

        if is_atom:
            items = root.findall("atom:entry", ns) or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for item in items:
                title_el = item.find("atom:title", ns) or item.find("{http://www.w3.org/2005/Atom}title")
                title = title_el.text if title_el is not None else ""

                link_el = item.find("atom:link[@href]", ns) or item.find("{http://www.w3.org/2005/Atom}link[@href]")
                link = link_el.attrib.get("href", "") if link_el is not None else ""

                if not link:
                    for l in item.findall("atom:link", ns) or []:
                        if l.attrib.get("rel") == "alternate" or "href" in l.attrib:
                            link = l.attrib.get("href", l.attrib.get("href", ""))
                            break

                summary_el = item.find("atom:summary", ns) or item.find("{http://www.w3.org/2005/Atom}summary") \
                              or item.find("atom:content", ns) or item.find("{http://www.w3.org/2005/Atom}content")
                summary = ""
                if summary_el is not None and summary_el.text:
                    summary = re.sub(r"<[^>]+>", "", summary_el.text).strip()
                    summary = summary[:300] + ("..." if len(summary) > 300 else "")

                pub_el = item.find("atom:published", ns) or item.find("{http://www.w3.org/2005/Atom}published") \
                        or item.find("atom:updated", ns) or item.find("{http://www.w3.org/2005/Atom}updated")
                time_str = pub_el.text[:16] if pub_el is not None and pub_el.text else ""

                if keyword_filter:
                    if not any(kw.lower() in title.lower() for kw in keyword_filter):
                        continue

                entries.append({
                    "title": title.strip(),
                    "link": link.strip(),
                    "summary": summary,
                    "time": time_str,
                    "source": source_name,
                })
            return entries

        # RSS 格式
        items = root.findall(".//item")
        for item in items:
            title_el = item.find("title")
            link_el = item.find("link")
            title = title_el.text if title_el is not None else ""
            link = link_el.text if link_el is not None else ""

            if keyword_filter:
                if not any(kw.lower() in title.lower() for kw in keyword_filter):
                    continue

            summary_el = item.find("description") or item.find("summary") or item.find("content")
            summary = ""
            if summary_el is not None and summary_el.text:
                summary = re.sub(r"<[^>]+>", "", summary_el.text).strip()
                summary = summary[:300] + ("..." if len(summary) > 300 else "")

            pub_el = item.find("pubDate")
            time_str = pub_el.text[:16] if pub_el is not None and pub_el.text else ""

            entries.append({
                "title": title.strip(),
                "link": link.strip(),
                "summary": summary,
                "time": time_str,
                "source": source_name,
            })
    except Exception as e:
        print(f"  [WARN] {source_name} 抓取失败: {e}")
    return entries


def fetch_hackernews() -> list:
    """通过 Algolia API 抓取 HN"""
    entries = []
    try:
        query = " OR ".join(HN_KEYWORDS[:5])
        url = f"https://hn.algolia.com/api/v1/search?tags=front_page&query={urllib.parse.quote(query)}&hitsPerPage=15"
        req = urllib.request.Request(url, headers={"User-Agent": "Daily-AI-News/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        for hit in data.get("hits", []):
            title = hit.get("title", "")
            link = hit.get("url", f"https://news.ycombinator.com/item?id={hit.get('objectID','')}")
            points = hit.get("points", 0)
            entries.append({
                "title": title,
                "link": link,
                "summary": f"HN · {points} points",
                "time": hit.get("created_at", "")[:16],
                "source": "Hacker News",
            })
    except Exception as e:
        print(f"  [WARN] Hacker News 抓取失败: {e}")
    return entries


# ========== Markdown 生成 ==========
def generate_markdown(entries_by_source: dict) -> str:
    today = datetime.now(CHINA_TZ)
    date_str = today.strftime("%Y-%m-%d")
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][today.weekday()]

    lines = [
        f"# AI 资讯日报 · {date_str} {weekday}",
        "",
        f"> 自动抓取 · 生成时间：{today.strftime('%H:%M:%S')}",
        "",
    ]

    total = 0
    for src_name, entries in entries_by_source.items():
        if not entries:
            continue
        total += len(entries)
        lines.append(f"## {entries[0]['source']}")
        lines.append("")
        for e in entries:
            summary_line = f"  \\ {e['summary']}" if e['summary'] else ""
            lines.append(f"- [{e['title']}]({e['link']}){summary_line}  \\ {e['time']}")
        lines.append("")

    lines.append(f"---\n共收录 **{total}** 条资讯")
    return "\n".join(lines)


# ========== GitHub 操作 ==========
def git_push(content: str, date_str: str):
    """初始化（若需要）并推送当日内容"""
    repo = REPO_PATH

    # 设置 git 用户
    subprocess_run(["git", "config", "--global", "user.email", "bot@daily-ai-news"])
    subprocess_run(["git", "config", "--global", "user.name", "Daily AI News Bot"])

    # 尝试 init（已有则忽略）
    subprocess_run(["git", "init"], cwd=repo, check=False)
    subprocess_run(["git", "remote", "add", "origin", REMOTE_URL], cwd=repo, check=False)

    # 拉取已有内容
    result = subprocess_run(
        ["git", "fetch", "origin", "main"],
        cwd=repo, check=False,
    )
    if result.returncode == 0:
        # 切换到 main 分支
        subprocess_run(["git", "checkout", "-B", "main", "origin/main"], cwd=repo, check=False)
    else:
        # 新仓库，没有任何 remote 分支，直接在 main 上工作
        subprocess_run(["git", "checkout", "-B", "main"], cwd=repo, check=False)
        subprocess_run(["git", "branch", "--set-upstream-to", "origin/main"], cwd=repo, check=False)

    # 写入当日文件
    daily_dir = repo / "daily"
    daily_dir.mkdir(exist_ok=True)
    output_file = daily_dir / f"{date_str}.md"
    output_file.write_text(content, encoding="utf-8")

    subprocess_run(["git", "add", "."], cwd=repo)

    # 有变更才提交
    diff_result = subprocess_run(
        ["git", "diff", "--cached", "--stat"],
        cwd=repo, capture=True
    )
    if not diff_result.stdout.strip():
        print("今日无新内容，跳过推送")
        return

    commit_msg = f"📰 Daily AI News {date_str}"
    subprocess_run(["git", "commit", "-m", commit_msg], cwd=repo)
    push_result = subprocess_run(["git", "push", "origin", "main"], cwd=repo)
    if push_result.returncode == 0:
        print("✅ 已推送至 GitHub")
    else:
        print(f"⚠️ 推送失败: {push_result.stderr}")


def subprocess_run(cmd, cwd=None, check=True, capture=False):
    import subprocess
    kwargs = {"cwd": cwd, "text": True}
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    r = subprocess.run(cmd, **kwargs)
    if check and r.returncode != 0:
        print(f"[ERR] {' '.join(cmd)}: {(r.stderr or '').strip()[:200]}")
    return r


# ========== 主流程 ==========
def main():
    if not GITHUB_TOKEN:
        print("[ERR] 未设置 GITHUB_TOKEN 环境变量")
        print("用法: GITHUB_TOKEN=xxx python3 fetch_news.py")
        sys.exit(1)
    print("📡 开始抓取 AI 资讯...\n")

    all_entries = {}

    # Hacker News
    print("  [Hacker News] 通过 Algolia API 抓取...")
    hn_entries = fetch_hackernews()
    all_entries["Hacker News"] = hn_entries
    print(f"    -> 获取 {len(hn_entries)} 条")

    # TechCrunch
    print("  [TechCrunch AI] 抓取 RSS...")
    tc_entries = fetch_rss(
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "TechCrunch AI"
    )
    all_entries["TechCrunch AI"] = tc_entries
    print(f"    -> 获取 {len(tc_entries)} 条")

    # The Verge
    print("  [The Verge AI] 抓取 RSS...")
    tv_entries = fetch_rss(
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "The Verge AI"
    )
    all_entries["The Verge AI"] = tv_entries
    print(f"    -> 获取 {len(tv_entries)} 条")

    # 生成 Markdown
    today_str = datetime.now(CHINA_TZ).strftime("%Y-%m-%d")
    content = generate_markdown(all_entries)

    print(f"\n📝 生成日报: {today_str}")
    git_push(content, today_str)
    print("\n🎉 完成！")


if __name__ == "__main__":
    main()
