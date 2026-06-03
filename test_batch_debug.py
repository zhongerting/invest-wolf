#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试：发送20条一批，看模型实际返回什么
"""

import os
import sys
import shutil
import time
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nga_crawler import NGACrawler
from knowledge_base import KnowledgeBase
from llm_client import LLMClient
from config import Config

def test_batch_analysis():
    print("="*60)
    print("测试批次分析")
    print("="*60)
    
    batch_size = 5
    
    # 1. 爬取发言
    print("\n[1] 爬取发言...")
    crawler = NGACrawler()
    result_dir = crawler.crawl_post(45974302, 150058)
    post_file = os.path.join(result_dir, 'post.md')
    
    with open(post_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 解析帖子
    import re
    posts = []
    lines = content.split('\n')
    current_post = None
    current_content = []
    
    for line in lines:
        if line.startswith('##### <span id="pid') and '(150058)' in line:
            if current_post:
                current_post['content'] = '\n'.join(current_content).strip()
                posts.append(current_post)
            
            try:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
                post_date = datetime.strptime(date_match.group(1), '%Y-%m-%d %H:%M:%S') if date_match else None
                num_match = re.search(r'(\d+)\.\[\d+\]', line)
                post_num = int(num_match.group(1)) if num_match else 0
                
                current_post = {'post_num': post_num, 'date': post_date, 'content': ''}
                current_content = []
            except:
                current_post = None
                current_content = []
        elif current_post and line.strip() != '----':
            current_content.append(line)
    
    if current_post:
        current_post['content'] = '\n'.join(current_content).strip()
        posts.append(current_post)
    
    posts.sort(key=lambda x: x['date'], reverse=False)
    print(f"      共获取 {len(posts)} 条发言")
    
    # 2. 取前20条测试
    test_posts = posts[:batch_size]
    print(f"\n[2] 测试前 {len(test_posts)} 条发言\n")
    
    kb = KnowledgeBase()
    llm_client = LLMClient()
    
    print(f"      API: {llm_client.api_url}")
    print(f"      Model: {llm_client.model}\n")
    
    # 准备批次
    batch_posts = []
    batch_input = ""
    
    for i, post in enumerate(test_posts, 1):
        cleaned = kb._clean_quoted_content(post['content'])
        if len(cleaned) > 200:
            cleaned = cleaned[:200] + "..."
        
        batch_posts.append({
            'post_num': post['post_num'],
            'date': post['date'],
            'content': cleaned
        })
        
        batch_input += f"[{i}] {post['date'].strftime('%Y-%m-%d %H:%M')}\n{cleaned}\n\n"
    
    print(f"[3] 发送请求（{len(test_posts)}条, {len(batch_input)}字符）...")
    
    prompt = f"""分析以下{len(test_posts)}条帖子，为每条生成单独的分析结果。

{batch_input}

返回JSON数组格式：
[
    {{"index":1,"tags":["tag1"],"category":"类型","summary":"摘要","sentiment":"情绪"}},
    {{"index":2,"tags":["tag1"],"category":"类型","summary":"摘要","sentiment":"情绪"}}
]

只返回JSON，不要其他内容。"""

    messages = [
        {"role": "system", "content": "你是专业的股票投资分析师。"},
        {"role": "user", "content": prompt}
    ]
    
    start_time = time.time()
    response = llm_client.chat(messages, temperature=0.3)
    elapsed = time.time() - start_time
    
    print(f"      耗时: {elapsed:.1f}秒")
    print(f"\n[4] 原始响应:")
    print("-" * 60)
    print(response if response else "无响应")
    print("-" * 60)
    
    # 尝试解析
    if response:
        print(f"\n[5] 尝试解析JSON...")
        try:
            json_str = llm_client._extract_json(response)
            print(f"      提取的JSON: {json_str[:500]}...")
            results = json.loads(json_str)
            print(f"      解析成功！共 {len(results)} 条结果")
            for r in results:
                print(f"        index={r.get('index')}, tags={r.get('tags')}, summary={r.get('summary', '')[:30]}...")
        except Exception as e:
            print(f"      解析失败: {e}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    test_batch_analysis()