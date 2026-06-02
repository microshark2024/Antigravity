#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
特朗普推文与 Truth Social 动态下载及检索脚本
支持下载特朗普的历史 Twitter 推文以及最新的 Truth Social 帖子，并提供本地过滤和双格式保存。
"""

import os
import csv
import json
import sys
import argparse
import time
import urllib.parse
import requests

# 确保在 Windows 控制台下支持 UTF-8 输出以避免 GBK 编码错误
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 常量定义
TRUTH_SOCIAL_URL = "https://ix.cnn.io/data/truth-social/truth_archive.json"
TWITTER_IN_OFFICE_URL = "https://raw.githubusercontent.com/MarkHershey/CompleteTrumpTweetsArchive/master/data/realDonaldTrump_in_office.csv"
TWITTER_BEFORE_OFFICE_URL = "https://raw.githubusercontent.com/MarkHershey/CompleteTrumpTweetsArchive/master/data/realDonaldTrump_bf_office.csv"

DEFAULT_OUTPUT_DIR = "trump_tweets"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def print_banner():
    """打印漂亮的终端 Banner"""
    # 避免在不支持 UTF-8 的 Windows 控制台 (GBK) 打印 Emoji 导致 UnicodeEncodeError
    banner = """
============================================================
     Donald Trump Tweet & Truth Social Downloader
       —— 特朗普推文与 Truth Social 动态下载与检索工具 ——
============================================================
    """
    try:
        print(banner)
    except Exception:
        print("Donald Trump Tweet & Truth Social Downloader")

def show_progress(current, total, prefix=""):
    """简易的终端进度条"""
    if total <= 0:
        return
    percent = (current / total) * 100
    bar_length = 30
    filled_length = int(bar_length * current // total)
    bar = "█" * filled_length + "-" * (bar_length - filled_length)
    sys.stdout.write(f"\r{prefix} |{bar}| {percent:.1f}% ({current}/{total})")
    sys.stdout.flush()

def download_truth_social_posts(limit=None, query=None):
    """
    从 CNN 实时存档接口下载 Truth Social 帖子
    """
    print(f"正在从 Truth Social 实时存档下载最新数据...")
    print(f"链接: {TRUTH_SOCIAL_URL}")
    
    try:
        response = requests.get(TRUTH_SOCIAL_URL, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            print(f"❌ 下载失败，服务器返回 HTTP {response.status_code}")
            return []
        
        posts = response.json()
        print(f"✅ 成功获取到共 {len(posts)} 条 Truth Social 原始帖子。")
        
        parsed_posts = []
        for post in posts:
            content = post.get("content", "")
            
            # 关键字过滤
            if query and query.lower() not in content.lower():
                continue
                
            # 清理 HTML 标签（Truth Social 帖子内容常含 <p> 或 <a> 标签）
            clean_content = content
            if "<" in clean_content and ">" in clean_content:
                import re
                clean_content = re.sub(r'<[^>]+>', '', clean_content)
            
            # 解析媒体文件
            media_list = []
            media_attachments = post.get("media_attachments", [])
            if isinstance(media_attachments, list):
                for media in media_attachments:
                    url = media.get("url") or media.get("preview_url")
                    if url:
                        media_list.append(url)
            
            media_str = ";".join(media_list)
            
            parsed_posts.append({
                "id": str(post.get("id", "")),
                "source": "Truth Social",
                "created_at": post.get("created_at", ""),
                "content": clean_content.strip(),
                "url": post.get("url", ""),
                "media": media_str,
                "replies_count": post.get("replies_count", 0),
                "reblogs_count": post.get("reblogs_count", 0),
                "favourites_count": post.get("favourites_count", 0)
            })
            
            if limit and len(parsed_posts) >= limit:
                break
                
        print(f"🔍 经过过滤和清理后，共保留了 {len(parsed_posts)} 条 Truth Social 记录。")
        return parsed_posts
        
    except Exception as e:
        print(f"❌ 下载/解析 Truth Social 数据时出错: {e}")
        return []

def download_twitter_tweets(limit=None, query=None, include_before_office=False):
    """
    下载 Twitter 历史推文（CSV 格式）
    """
    urls_to_download = [("在任期间 (2017-2021)", TWITTER_IN_OFFICE_URL)]
    if include_before_office:
        urls_to_download.append(("执政前 (2009-2017)", TWITTER_BEFORE_OFFICE_URL))
        
    all_tweets = []
    
    for label, url in urls_to_download:
        print(f"\n正在从 Twitter 历史存档下载 {label} 数据...")
        print(f"链接: {url}")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=40)
            if response.status_code != 200:
                print(f"❌ 下载失败，服务器返回 HTTP {response.status_code}")
                continue
                
            # 解析 CSV 内容
            csv_data = response.text.splitlines()
            reader = csv.reader(csv_data)
            
            # 读取表头
            try:
                header = next(reader)
            except StopIteration:
                print("❌ 存档 CSV 文件为空。")
                continue
                
            # 建立列名映射
            header_map = {col.lower().strip(): idx for idx, col in enumerate(header)}
            
            # 兼容不同的列名结构
            id_idx = header_map.get("id") or header_map.get("tweet_id") or 0
            text_idx = header_map.get("content") or header_map.get("tweet") or header_map.get("text") or 1
            date_idx = header_map.get("date") or header_map.get("date_time") or header_map.get("created_at") or 2
            retweets_idx = header_map.get("retweets") or header_map.get("retweet_count") or 3
            favorites_idx = header_map.get("favorites") or header_map.get("favorite_count") or 4
            
            source_idx = header_map.get("source")
            is_retweet_idx = header_map.get("is_retweet")
            
            tweets_list = list(reader)
            print(f"✅ 成功获取到共 {len(tweets_list)} 条 Twitter 历史推文。")
            
            count = 0
            for row in tweets_list:
                if not row or len(row) <= max(id_idx, text_idx):
                    continue
                    
                content = row[text_idx]
                
                # 关键字过滤
                if query and query.lower() not in content.lower():
                    continue
                
                # 提取数据并格式化
                tweet_id = row[id_idx]
                created_at = row[date_idx]
                retweets = int(row[retweets_idx]) if retweets_idx < len(row) and row[retweets_idx].isdigit() else 0
                favorites = int(row[favorites_idx]) if favorites_idx < len(row) and row[favorites_idx].isdigit() else 0
                
                # 拼接直接访问的 Twitter 网址
                url_str = f"https://twitter.com/realDonaldTrump/status/{tweet_id}"
                
                all_tweets.append({
                    "id": str(tweet_id),
                    "source": "Twitter",
                    "created_at": created_at,
                    "content": content.strip(),
                    "url": url_str,
                    "media": "",  # 历史 CSV 一般不带直链
                    "replies_count": 0,  # 历史归档一般没有回复数
                    "reblogs_count": retweets,
                    "favourites_count": favorites
                })
                
                count += 1
                if limit and len(all_tweets) >= limit:
                    break
            
            print(f"🔍 当前 Twitter 存档经过过滤保留了 {count} 条记录。")
            if limit and len(all_tweets) >= limit:
                break
                
        except Exception as e:
            print(f"❌ 下载/解析 Twitter 数据时出错: {e}")
            
    return all_tweets

def translate_text(text, src='en', dest='zh-CN'):
    """
    使用 Google Translate 免费接口将英文内容翻译为中文。
    支持多句段拼接，遇到错误自动降级。
    """
    if not text or not text.strip():
        return ""
        
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        'client': 'gtx',
        'sl': src,
        'tl': dest,
        'dt': 't',
        'q': text
    }
    
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0 and data[0]:
                translated_segments = []
                for segment in data[0]:
                    if segment and len(segment) > 0 and segment[0]:
                        translated_segments.append(segment[0])
                return "".join(translated_segments).strip()
    except Exception:
        pass
    
    return "[翻译失败] " + text

def translate_results(results):
    """
    顺序翻译所有抓取到的帖子内容为中文
    """
    total = len(results)
    if total == 0:
        return results
        
    print(f"\n🌐 正在将 {total} 条帖子内容翻译为中文 (免费 Google 翻译接口)...")
    
    for idx, item in enumerate(results):
        english_content = item.get("content", "")
        # 如果本身就是中文（极少情况下）或为空，则跳过
        if not english_content:
            item["content_zh"] = ""
            continue
            
        chinese_content = translate_text(english_content)
        item["content_zh"] = chinese_content
        
        # 显示进度
        show_progress(idx + 1, total, prefix="翻译进度")
        
        # 礼貌延迟，避免被 Google API 频繁限制
        time.sleep(0.1)
        
    print("\n✅ 中文翻译完成！")
    return results

def save_data(data, output_dir, translated=True):
    """
    保存数据为中文和英文的 JSON & CSV 双版本（总共 4 个文件）
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # 原版（含中英双语列）
    json_path = os.path.join(output_dir, "trump_posts.json")
    csv_path = os.path.join(output_dir, "trump_posts.csv")
    
    # 纯中文版
    json_zh_path = os.path.join(output_dir, "trump_posts_zh.json")
    csv_zh_path = os.path.join(output_dir, "trump_posts_zh.csv")
    
    # 1. 保存完整原始版本 (如果已翻译则包含 content_zh 字段)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    fields = ["id", "source", "created_at", "content"]
    if translated:
        fields.append("content_zh")
    fields.extend(["url", "media", "replies_count", "reblogs_count", "favourites_count"])
    
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in data:
            writer.writerow({k: item.get(k, "") for k in fields})
            
    # 2. 如果存在翻译，保存纯中文翻译版本
    if translated:
        zh_data = []
        for item in data:
            zh_item = item.copy()
            zh_item["content"] = item.get("content_zh", item.get("content", ""))
            if "content_zh" in zh_item:
                del zh_item["content_zh"]
            zh_data.append(zh_item)
            
        with open(json_zh_path, 'w', encoding='utf-8') as f:
            json.dump(zh_data, f, ensure_ascii=False, indent=2)
            
        zh_fields = ["id", "source", "created_at", "content", "url", "media", "replies_count", "reblogs_count", "favourites_count"]
        with open(csv_zh_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=zh_fields)
            writer.writeheader()
            for item in zh_data:
                writer.writerow({k: item.get(k, "") for k in zh_fields})
                
    print(f"\n💾 数据已成功保存到以下文件：")
    print(f"   📂 目录: {os.path.abspath(output_dir)}")
    print(f"   📝 原文完整版 JSON: [trump_posts.json](file:///{os.path.abspath(json_path).replace(os.sep, '/')}) ({len(data)} 条记录)")
    print(f"   📊 原文完整版 CSV : [trump_posts.csv](file:///{os.path.abspath(csv_path).replace(os.sep, '/')})")
    if translated:
        print(f"   📝 纯中文译本 JSON: [trump_posts_zh.json](file:///{os.path.abspath(json_zh_path).replace(os.sep, '/')}) ({len(data)} 条记录)")
        print(f"   📊 纯中文译本 CSV : [trump_posts_zh.csv](file:///{os.path.abspath(csv_zh_path).replace(os.sep, '/')})")

def main():
    parser = argparse.ArgumentParser(description="下载并检索特朗普的推文与 Truth Social 帖子")
    parser.add_argument("--source", choices=["twitter", "truth", "both"], default="both",
                        help="数据来源: twitter (Twitter 历史推文), truth (Truth Social 动态), both (全部，默认)")
    parser.add_argument("--limit", type=int, default=100,
                        help="每个数据源最大下载/保留记录条数 (默认 100)")
    parser.add_argument("--query", type=str, default=None,
                        help="根据关键字检索过滤推文 (不区分大小写)")
    parser.add_argument("--all-twitter", action="store_true",
                        help="是否包含特朗普 2009-2017 年（执政前）的超早期推文，注意这可能会增加下载时间")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_DIR,
                        help=f"数据保存输出目录，默认 '{DEFAULT_OUTPUT_DIR}'")
    parser.add_argument("--no-translate", action="store_true",
                        help="关闭自动中文翻译功能")
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.query:
        print(f"🔍 检索关键字: '{args.query}'")
    print(f"🔢 数量上限: 每个源最多 {args.limit} 条")
    print(f"📂 输出目录: {args.output}\n")
    
    results = []
    
    # 1. 尝试在线爬取
    try:
        # 爬取 Truth Social
        if args.source in ["truth", "both"]:
            truth_posts = download_truth_social_posts(limit=args.limit, query=args.query)
            results.extend(truth_posts)
            
        # 爬取 Twitter
        if args.source in ["twitter", "both"]:
            twitter_tweets = download_twitter_tweets(
                limit=args.limit, 
                query=args.query, 
                include_before_office=args.all_twitter
            )
            results.extend(twitter_tweets)
    except Exception as e:
        print(f"⚠️ 在线爬取时发生异常: {e}")
        
    # 2. 如果在线抓取失败（例如网络受限/SSL异常），尝试读取本地已有的历史数据作为缓存备份
    if not results:
        backup_path = os.path.join(args.output, "trump_posts.json")
        if os.path.exists(backup_path):
            print(f"📡 检测到网络访问受阻，正在从本地历史备份 [{backup_path}] 中加载数据进行二次筛选与翻译...")
            try:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    local_data = json.load(f)
                    
                # 重新应用过滤条件
                truth_count = 0
                twitter_count = 0
                for item in local_data:
                    source = item.get("source", "").lower()
                    
                    # 来源筛选
                    if args.source == "truth" and "truth" not in source:
                        continue
                    if args.source == "twitter" and "twitter" not in source:
                        continue
                        
                    # 关键字过滤
                    content = item.get("content", "")
                    if args.query and args.query.lower() not in content.lower():
                        continue
                        
                    # 限制各个源的数量
                    if "truth" in source:
                        if truth_count >= args.limit:
                            continue
                        truth_count += 1
                    else:
                        if twitter_count >= args.limit:
                            continue
                        twitter_count += 1
                        
                    results.append(item)
                    
                print(f"✅ 成功从本地恢复并筛选出 {len(results)} 条记录。")
            except Exception as ex:
                print(f"❌ 读取本地备份文件失败: {ex}")
                
    if not results:
        print("\n⚠️ 未匹配到任何数据，请检查网络或更换检索关键字。")
        return
        
    # 翻译结果
    do_translate = not args.no_translate
    if do_translate:
        results = translate_results(results)
        
    # 保存结果
    save_data(results, args.output, translated=do_translate)
    
    print("\n🎉 任务已圆满完成！使用愉快！")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 进程被用户强行终止。")
        sys.exit(0)
