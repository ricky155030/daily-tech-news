#!/usr/bin/env python3
"""
daily-tech-news - RSS News Fetcher & Generator
從多個國外可靠 RSS 來源抓取新聞，精選後輸出 Markdown
"""

import os
import sys
import json
import re
import requests
import feedparser
from datetime import datetime
from bs4 import BeautifulSoup

# RSS Sources Configuration
RSS_SOURCES = [
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "max_items": 5,
        "type": "rss"
    },
    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "max_items": 5,
        "type": "rss"
    },
    {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/index.xml",
        "max_items": 5,
        "type": "atom"
    },
    {
        "name": "Hacker News",
        "url": "https://news.ycombinator.com/rss",
        "max_items": 5,
        "type": "rss"
    },
    {
        "name": "Wired",
        "url": "https://www.wired.com/feed/rss",
        "max_items": 5,
        "type": "rss"
    },
    {
        "name": "BBC Tech",
        "url": "http://feeds.bbci.co.uk/news/technology/rss.xml",
        "max_items": 5,
        "type": "rss"
    },
]

# Output directory
OUTPUT_DIR = "_posts"
DATA_DIR = "data"

def clean_html(text):
    """移除 HTML 標籤"""
    if not text:
        return ""
    # 移除 HTML 標籤
    soup = BeautifulSoup(text, "html.parser")
    clean_text = soup.get_text()
    # 移除多餘空白
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    # 截斷長度
    if len(clean_text) > 300:
        clean_text = clean_text[:300] + "..."
    return clean_text

def parse_date(date_str):
    """嘗試解析日期"""
    from email.utils import parsedate_to_datetime
    try:
        dt = parsedate_to_datetime(date_str)
        return dt
    except:
        return None

def fetch_feed(source):
    """抓取單一 RSS 來源"""
    name = source["name"]
    url = source["url"]
    max_items = source.get("max_items", 5)
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; daily-tech-news/1.0)"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        
        items = []
        for entry in feed.entries[:max_items]:
            # 嘗試取得發布時間
            pub_date = None
            if hasattr(entry, 'published'):
                pub_date = parse_date(entry.published)
            elif hasattr(entry, 'updated'):
                pub_date = parse_date(entry.updated)
            
            # 取得標題和連結
            title = entry.get('title', '').strip()
            link = entry.get('link', '')
            
            # 取得摘要
            if hasattr(entry, 'summary'):
                summary = clean_html(entry.summary)
            elif hasattr(entry, 'description'):
                summary = clean_html(entry.description)
            else:
                summary = ""
            
            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "pub_date": pub_date,
                    "source": name
                })
        
        print(f"✓ {name}: 抓到 {len(items)} 條")
        return items
        
    except Exception as e:
        print(f"✗ {name}: 錯誤 - {e}")
        return []

def is_recent(item, hours=24):
    """檢查是否為近 N 小時的新聞"""
    if not item.get("pub_date"):
        return True  # 無法判斷時預設為 True
    now = datetime.now(item["pub_date"].tzinfo)
    diff = now - item["pub_date"]
    return diff.total_seconds() < hours * 3600

def calculate_importance(item):
    """計算新聞重要性分數 (簡單關鍵字權重)"""
    score = 0
    title = item.get("title", "").lower()
    summary = item.get("summary", "").lower()
    text = title + " " + summary
    
    # AI 相關關鍵字
    ai_keywords = ["ai", "openai", "gpt", "gemini", "claude", "llm", "model", "anthropic", "microsoft", "google", "nvidia"]
    for kw in ai_keywords:
        if kw in text:
            score += 3
    
    # 資安關鍵字
    security_keywords = ["security", "hack", "attack", "vulnerability", "malware", "breach", "cyber"]
    for kw in security_keywords:
        if kw in text:
            score += 3
    
    # 大公司
    big_tech = ["apple", "amazon", "meta", "facebook", "tesla", "musk", "xai"]
    for kw in big_tech:
        if kw in text:
            score += 2
    
    # 新創 funding
    if "funding" in text or "raises" in text or "series" in text:
        score += 2
    
    return score

def select_top_news(all_items, top_n=10):
    """精選最重要的新聞"""
    # 過濾近 24 小時的新聞
    recent_items = [item for item in all_items if is_recent(item, hours=24)]
    
    # 如果沒有夠多的近新聞，放寬到 48 小時
    if len(recent_items) < top_n:
        recent_items = [item for item in all_items if is_recent(item, hours=48)]
    
    # 計算重要性分數並排序
    for item in recent_items:
        item["importance"] = calculate_importance(item)
    
    sorted_items = sorted(recent_items, key=lambda x: x["importance"], reverse=True)
    
    return sorted_items[:top_n]

def generate_markdown(news_items, date_str):
    """生成 Markdown 格式"""
    md_lines = []
    md_lines.append("---")
    md_lines.append(f'title: "{date_str} 科技新聞精選"')
    md_lines.append(f'date: {date_str}')
    md_lines.append('tags: [科技, AI, 資安, 新創]')
    md_lines.append("---")
    md_lines.append("")
    md_lines.append(f"# 🔥 {date_str} 科技新聞精選")
    md_lines.append("")
    md_lines.append(f"*精選自 TechCrunch, Ars Technica, The Verge, Wired 等來源*")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    for i, item in enumerate(news_items, 1):
        md_lines.append(f"### {i}. {item['title']}")
        md_lines.append("")
        md_lines.append(f"**摘要：** {item['summary']}")
        md_lines.append("")
        md_lines.append(f"**出處：** {item['source']}")
        md_lines.append("")
        md_lines.append(f"**連結：** [閱讀原文]({item['link']})")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
    
    md_lines.append("*由 🤖 AI 自動彙整 | 資料來源：RSS Feeds*")
    
    return "\n".join(md_lines)

def main():
    print("=" * 50)
    print("📰 daily-tech-news 開始抓取...")
    print("=" * 50)
    
    # 建立輸出目錄
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # 抓取所有來源
    all_items = []
    for source in RSS_SOURCES:
        items = fetch_feed(source)
        all_items.extend(items)
    
    print(f"\n📊 總共抓到 {len(all_items)} 條新聞")
    
    # 精選 Top 10
    top_news = select_top_news(all_items, top_n=10)
    print(f"✅ 精選 {len(top_news)} 條重要新聞")
    
    # 生成日期
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 產生 Markdown
    markdown_content = generate_markdown(top_news, today)
    
    # 儲存檔案
    filename = f"{today}-daily-news.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    print(f"\n💾 已儲存: {filepath}")
    
    # 同時儲存一份 JSON 備份
    json_path = os.path.join(DATA_DIR, f"{today}.json")
    # 轉換 datetime 為字串
    for item in top_news:
        if item.get("pub_date"):
            item["pub_date"] = item["pub_date"].isoformat()
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": today,
            "news": top_news
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 JSON 備份: {json_path}")
    
    # 印出預覽
    print("\n" + "=" * 50)
    print("📝 預覽 (前 3 條):")
    print("=" * 50)
    for i, item in enumerate(top_news[:3], 1):
        print(f"\n{i}. {item['title']}")
        print(f"   📌 {item['source']}")
        print(f"   🔗 {item['link']}")

if __name__ == "__main__":
    main()
