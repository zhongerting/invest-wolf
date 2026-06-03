#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按批次汇总重新构建知识库（带进度显示）
"""

import os
import sys
import shutil
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nga_crawler import NGACrawler
from knowledge_base import KnowledgeBase
from llm_client import LLMClient

def rebuild_knowledge_base():
    """按批次汇总重新构建知识库"""
    print("="*60)
    print("按批次汇总重新构建知识库")
    print("="*60)
    
    BATCH_SIZE = 20
    
    # 1. 清理现有知识库
    print("\n[1/6] 清理现有知识库...")
    kb = KnowledgeBase()
    
    if os.path.exists(kb.base_dir):
        shutil.rmtree(kb.base_dir)
        print(f"      已删除知识库目录\n")
    
    # 2. 初始化新的知识库
    print("[2/6] 初始化新的知识库...")
    kb = KnowledgeBase()
    print(f"      知识库目录: {kb.base_dir}\n")
    
    # 3. 爬取所有发言
    print("[3/6] 爬取所有发言...")
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
    print(f"      共获取 {len(posts)} 条发言\n")
    
    # 4. 按批次分组
    print("[4/6] 按批次分组...")
    batches = [posts[i:i+BATCH_SIZE] for i in range(0, len(posts), BATCH_SIZE)]
    print(f"      每批{BATCH_SIZE}条，共{len(batches)}批\n")
    
    # 5. 按批次分析
    print("[5/6] 按批次分析（预计每批45-50秒）...")
    print("-" * 60)
    
    llm_client = LLMClient()
    total_analyzed = 0
    start_time = time.time()
    
    for batch_idx, batch in enumerate(batches, 1):
        # 汇总本批
        batch_summary = ""
        for i, post in enumerate(batch, 1):
            content = kb._clean_quoted_content(post['content'])[:200]
            if len(content) > 200:
                content = content[:200] + "..."
            batch_summary += f"【{i}】[{post['date'].strftime('%m-%d %H:%M')}]\n{content}\n\n"
        
        # 调用LLM
        print(f"批 {batch_idx:3d}/{len(batches):3d} ({len(batch)}条, {len(batch_summary)}字符)...", end='', flush=True)
        
        result = llm_client.analyze_post_content(batch_summary, batch[0]['date'])
        
        # 添加到知识库
        batch_id = f"BATCH_{batch_idx:03d}_{batch[0]['date'].strftime('%Y%m%d')}"
        kb.add_post(batch_id, batch[0]['date'], batch_summary)
        
        total_analyzed += len(batch)
        tags = result.get('tags', [])[:3]
        print(f" 完成 | 标签:{tags} | 累计:{total_analyzed}/{len(posts)}", flush=True)
        
        # RPM限制
        time.sleep(31)
    
    # 6. 验证
    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"\n[6/6] 验证知识库...")
    kb = KnowledgeBase()
    print(f"      记录数: {len(kb.posts_index)}")
    print(f"      标签数: {len(kb.tags_index)}")
    print(f"      耗时: {elapsed/60:.1f}分钟")
    
    print("\n" + "="*60)
    print("知识库构建完成！")

if __name__ == "__main__":
    rebuild_knowledge_base()