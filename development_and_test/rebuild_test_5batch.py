#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真正的批量发送：5条一批测试主API
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

def rebuild_knowledge_base_test():
    """测试批次发送"""
    print("="*60)
    print("测试批次发送（5条一批）")
    print("="*60)
    
    batch_size = 5
    max_retries = 2
    
    # 1. 清理现有知识库
    print("\n[1/6] 清理现有知识库...")
    kb = KnowledgeBase()
    
    if os.path.exists(kb.base_dir):
        shutil.rmtree(kb.base_dir)
        print(f"      已删除知识库目录\n")
    
    # 2. 初始化知识库
    print("[2/6] 初始化知识库...")
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
    
    # 4. 只取前50条测试
    test_posts = posts[:50]
    print(f"[4/6] 测试前 {len(test_posts)} 条发言\n")
    
    # 5. 按批次分析
    print("[5/6] 按批次发送LLM分析...")
    print("-" * 60)
    
    llm_client = LLMClient()
    print(f"      使用API: {llm_client.api_url}")
    print(f"      使用模型: {llm_client.model}\n")
    
    total_analyzed = 0
    failed_count = 0
    start_time = time.time()
    
    # 分批处理
    batches = [test_posts[i:i+batch_size] for i in range(0, len(test_posts), batch_size)]
    
    for batch_idx, batch in enumerate(batches, 1):
        batch_posts = []
        batch_input = ""
        
        for i, post in enumerate(batch, 1):
            cleaned = kb._clean_quoted_content(post['content'])
            if len(cleaned) > 150:
                cleaned = cleaned[:150] + "..."
            
            batch_posts.append({
                'post_num': post['post_num'],
                'date': post['date'],
                'content': cleaned
            })
            
            batch_input += f"[{i}] {post['date'].strftime('%Y-%m-%d %H:%M')}\n{cleaned}\n\n"
        
        print(f"批 {batch_idx:3d}/{len(batches):3d} ({len(batch)}条, {len(batch_input)}字符)...", end='', flush=True)
        
        prompt = f"""分析以下{len(batch)}条帖子，为每条生成单独的分析结果。

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
        
        success = False
        for retry in range(max_retries):
            try:
                response = llm_client.chat(messages, temperature=0.3)
                
                if response and response.strip():
                    try:
                        json_str = llm_client._extract_json(response)
                        results = json.loads(json_str)
                        
                        if len(results) == len(batch):
                            for result in results:
                                idx = result.get('index', 0) - 1
                                if 0 <= idx < len(batch_posts):
                                    post = batch_posts[idx]
                                    kb.add_post(
                                        post_num=post['post_num'],
                                        post_date=post['date'],
                                        post_content=post['content']
                                    )
                                    total_analyzed += 1
                            
                            print(f" 完成({len(results)}条)", flush=True)
                            success = True
                            break
                        else:
                            print(f" 结果数不匹配({len(results)}!={len(batch)})", end='')
                    
                    except json.JSONDecodeError:
                        print(f" JSON解析失败", end='')
                
                if not success:
                    if retry < max_retries - 1:
                        print(f" 重试...", flush=True)
                        time.sleep(3)
                        continue
                    else:
                        print(f" 放弃本批", flush=True)
                        failed_count += len(batch)
            
            except Exception as e:
                print(f" 错误: {str(e)[:30]}", end='')
                if retry < max_retries - 1:
                    print(f" 重试...", flush=True)
                    time.sleep(3)
                    continue
                else:
                    print(f" 放弃本批", flush=True)
                    failed_count += len(batch)
                break
        
        time.sleep(31)
        
        if batch_idx % 3 == 0:
            elapsed = time.time() - start_time
            print(f"    进度: {total_analyzed}/{len(test_posts)} | 失败: {failed_count} | {elapsed/60:.1f}分钟")
    
    print("-" * 60)
    print(f"\n[6/6] 验证知识库...")
    kb = KnowledgeBase()
    print(f"      记录数: {len(kb.posts_index)}")
    print(f"      标签数: {len(kb.tags_index)}")
    print(f"      失败数: {failed_count}")
    
    elapsed = time.time() - start_time
    print(f"      耗时: {elapsed/60:.1f}分钟")
    
    print("\n" + "="*60)
    print(f"测试完成！成功率: {total_analyzed}/{len(test_posts)}")
    
    return total_analyzed, failed_count

if __name__ == "__main__":
    rebuild_knowledge_base_test()