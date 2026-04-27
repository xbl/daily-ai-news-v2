# Daily AI News

每日 AI 资讯精选，自动抓取以下来源：

- **Hacker News**（AI 关键词过滤）
- **TechCrunch AI**
- **The Verge AI**

## 运行方式

```bash
pip install feedparser
python fetch_news.py
```

## 定时任务

每日 09:00（北京时间）自动抓取并推送到 GitHub。

可通过以下命令查看/管理定时任务：

```bash
crontab -l
```

## 输出

每日生成 `daily/YYYY-MM-DD.md`，格式为：

- 当日资讯列表
- 每条包含标题、链接、摘要
- 按来源分组
