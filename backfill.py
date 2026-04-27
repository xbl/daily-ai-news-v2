#!/usr/bin/env python3
"""
历史资讯回溯脚本
抓取过去多日的 AI 资讯（不带 GitHub push，只保存本地）
"""
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 加载主脚本的函数
sys.path.insert(0, str(Path(__file__).parent))
from fetch_news import fetch_hackernews, fetch_rss, generate_markdown, REPO_PATH

CHINA_TZ = timezone(timedelta(hours=8))

def backfill(start_date: str, end_date: str):
    """回填指定日期范围（只写本地，不 push）"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    current = end
    while current >= start:
        date_str = current.strftime("%Y-%m-%d")
        out_file = REPO_PATH / "daily" / f"{date_str}.md"

        if out_file.exists():
            print(f"  [跳过] {date_str} 已存在")
            current -= timedelta(days=1)
            continue

        print(f"  [抓取] {date_str} ...")
        all_entries = {}

        hn = fetch_hackernews()
        all_entries["Hacker News"] = hn
        print(f"    HN: {len(hn)} 条")

        tc = fetch_rss("https://techcrunch.com/category/artificial-intelligence/feed/", "TechCrunch AI")
        all_entries["TechCrunch AI"] = tc
        print(f"    TC: {len(tc)} 条")

        tv = fetch_rss("https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "The Verge AI")
        all_entries["The Verge AI"] = tv
        print(f"    TV: {len(tv)} 条")

        content = generate_markdown(all_entries)
        out_file.parent.mkdir(exist_ok=True)
        out_file.write_text(content, encoding="utf-8")
        print(f"    -> 已保存 {out_file}")

        current -= timedelta(days=1)

if __name__ == "__main__":
    # 订阅从 2026-04-13 开始，回填到昨天
    today = datetime.now(CHINA_TZ)
    yesterday = today - timedelta(days=1)
    backfill("2026-04-13", yesterday.strftime("%Y-%m-%d"))
    print("\n✅ 回填完成")
