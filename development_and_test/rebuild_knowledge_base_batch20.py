#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按批次汇总重新构建知识库（20条一批，故障转移支持）
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

def rebuild_knowledge_base_batch20():
    """按批次汇总重新构建知识库（20条一批）"""
    print("="*60)
    print("按批次汇总重新构建知识库（20条一批）")
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
    
    # 5. 按批次分析（每条单独调用LLM）
    print("[5/6] 按批次分析（每条单独结果，预计每批8-10分钟）...")
    print("-" * 60)
    
    llm_client = LLMClient()
    total_analyzed = 0
    failed_count = 0
    start_time = time.time()
    
    for batch_idx, batch in enumerate(batches, 1):
        print(f"\n>>> 批次 {batch_idx}/{len(batches)} 开始")
        
        for post in batch:
            print(f"批 {batch_idx:3d}/{len(batches):3d} | 发言 {total_analyzed+1}/{len(posts)}...", end='', flush=True)
            
            try:
                # 使用知识库的add_post方法（会自动调用LLM分析）
                kb.add_post(
                    post_num=post['post_num'],
                    post_date=post['date'],
                    post_content=post['content']
                )
                
                total_analyzed += 1
                print(" 完成", flush=True)
                
                # RPM限制（每31秒一次）
                time.sleep(31)
                
            except Exception as e:
                print(f" 失败: {str(e)[:30]}", flush=True)
                failed_count += 1
        
        # 批次完成后显示进度
        elapsed = time.time() - start_time
        avg_time_per_post = elapsed / max(total_analyzed, 1)
        remaining_posts = len(posts) - total_analyzed
        estimated_remaining = remaining_posts * avg_time_per_post / 60
        
        print(f"<<< 批次 {batch_idx}/{len(batches)} 完成 | 累计: {total_analyzed}/{len(posts)} | 剩余: {estimated_remaining:.1f}分钟")
    
    # 6. 验证
    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"\n[6/6] 验证知识库...")
    kb = KnowledgeBase()
    print(f"      记录数: {len(kb.posts_index)}")
    print(f"      标签数: {len(kb.tags_index)}")
    print(f"      失败数: {failed_count}")
    print(f"      耗时: {elapsed/60:.1f}分钟")
    
    print("\n" + "="*60)
    print("知识库构建完成！")

if __name__ == "__main__":
    rebuild_knowledge_base_batch20()