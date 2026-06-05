#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量发送：15条一批，使用主API (gemini-2.5-pro-maxthinking)
RPM=2，每批间隔31秒
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

def rebuild_knowledge_base_15batch():
    """5条一批的批量发送（无RPM限制）"""
    print("="*60)
    print("批量发送知识库构建（5条一批，主API，无RPM限制）")
    print("="*60)
    
    batch_size = 5
    max_retries = 2
    rpm_limit = 1000  # 无限制
    interval = 0  # 无需等待
    
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
    
    # 4. 按批次分组
    print("[4/6] 按批次分组...")
    batches = [posts[i:i+batch_size] for i in range(0, len(posts), batch_size)]
    print(f"      每批{batch_size}条，共{len(batches)}批")
    print(f"      无RPM限制\n")
    
    # 5. 使用主API
    print("[5/6] 按批次发送LLM分析...")
    print("-" * 60)
    
    # 创建LLM客户端（设置高RPM限制以实现无限制）
    llm_client = LLMClient(rpm_limit=1000)
    print(f"      API: {llm_client.api_url}")
    print(f"      Model: {llm_client.model}\n")
    
    total_analyzed = 0
    failed_count = 0
    start_time = time.time()
    
    for batch_idx, batch in enumerate(batches, 1):
        batch_posts = []
        batch_input = ""
        
        for i, post in enumerate(batch, 1):
            cleaned = kb._clean_quoted_content(post['content'])
            if len(cleaned) > 200:
                cleaned = cleaned[:200] + "..."
            
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
            {"role": "system", "content": "你是一个专业的股票投资分析师。"},
            {"role": "user", "content": prompt}
        ]
        
        success = False
        response = None
        
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
                            last_request_time = time.time()
                            break
                        else:
                            print(f" 结果数不匹配({len(results)}!={len(batch)})", end='')
                    
                    except json.JSONDecodeError:
                        print(f" JSON解析失败", end='')
                        if retry < max_retries - 1:
                            print(f" 重试...", flush=True)
                            time.sleep(3)
                            continue
                else:
                    print(f" 无响应", end='')
                    if retry < max_retries - 1:
                        print(f" 重试...", flush=True)
                        time.sleep(3)
                        continue
            
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
        
        if not success and response is None:
            failed_count += len(batch)
        
        if batch_idx % 10 == 0:
            elapsed = time.time() - start_time
            eta = (elapsed / total_analyzed) * (len(posts) - total_analyzed) if total_analyzed > 0 else 0
            print(f"    进度: {total_analyzed}/{len(posts)} | 失败: {failed_count} | 耗时: {elapsed/60:.1f}分钟 | 预计剩余: {eta/60:.1f}分钟")
    
    print("-" * 60)
    print(f"\n[6/6] 验证知识库...")
    kb = KnowledgeBase()
    print(f"      记录数: {len(kb.posts_index)}")
    print(f"      标签数: {len(kb.tags_index)}")
    print(f"      失败数: {failed_count}")
    
    elapsed = time.time() - start_time
    print(f"      耗时: {elapsed/60:.1f}分钟")
    
    print("\n" + "="*60)
    print("知识库构建完成！")
    
    return total_analyzed, failed_count

if __name__ == "__main__":
    total, failed = rebuild_knowledge_base_15batch()
    
    # 如果失败太多，提示用更小的批次
    if failed > len([total, failed][0]) * 0.1:
        print(f"\n警告: 失败率较高，建议尝试10条一批")