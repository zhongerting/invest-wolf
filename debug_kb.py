#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本：找出卡住的原因
"""

import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nga_crawler import NGACrawler
from knowledge_base import KnowledgeBase
from llm_client import LLMClient

print("调试开始...")

# 1. 爬取帖子
print("\n1. 爬取帖子...")
crawler = NGACrawler()
result_dir = crawler.crawl_post(45974302, 150058)
post_file = os.path.join(result_dir, 'post.md')

with open(post_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 解析前几条帖子
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
            if len(posts) >= 3:  # 只取前3条
                break
            
        try:
            date_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
            if date_match:
                post_date = datetime.strptime(date_match.group(1), '%Y-%m-%d %H:%M:%S')
            else:
                post_date = None
            
            num_match = re.search(r'(\d+)\.\[\d+\]', line)
            if num_match:
                post_num = int(num_match.group(1))
            else:
                post_num = 0
            
            current_post = {
                'post_num': post_num,
                'date': post_date,
                'content': ''
            }
            current_content = []
        except:
            current_post = None
            current_content = []
    elif current_post:
        if line.strip() != '----':
            current_content.append(line)

print(f"获取到 {len(posts)} 条测试帖子")

# 2. 测试清理引用内容
print("\n2. 测试清理引用内容...")
kb = KnowledgeBase()

for i, post in enumerate(posts):
    print(f"\n帖子{i+1}:")
    print(f"  原始内容长度: {len(post['content'])}")
    
    start_time = time.time()
    cleaned = kb._clean_quoted_content(post['content'])
    elapsed = time.time() - start_time
    
    print(f"  清理耗时: {elapsed:.2f}秒")
    print(f"  清理后长度: {len(cleaned)}")
    print(f"  预览: {cleaned[:100]}...")

# 3. 测试LLM分析
print("\n3. 测试LLM分析...")
llm_client = LLMClient()

test_content = "\n\n".join([f"【{i+1}】{kb._clean_quoted_content(p['content'])[:100]}" for i, p in enumerate(posts)])
print(f"汇总内容长度: {len(test_content)}")

start_time = time.time()
result = llm_client.analyze_post_content(test_content, posts[0]['date'])
elapsed = time.time() - start_time

print(f"LLM分析耗时: {elapsed:.2f}秒")
print(f"结果: {result}")

print("\n调试完成！")