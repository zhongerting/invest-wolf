#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真正的批量发送：20条一批发送给LLM，LLM为每条发言单独分析
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

def rebuild_knowledge_base_true_batch(batch_size=20, max_retries=3):
    """真正的批量发送：每批batch_size条发送给LLM"""
    print("="*60)
    print(f"真正的批量发送知识库构建（每批{batch_size}条）")
    print("="*60)
    
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
    batches = [posts[i:i+batch_size] for i in range(0, len(posts), batch_size)]
    print(f"      每批{batch_size}条，共{len(batches)}批\n")
    
    # 5. 按批次分析
    print("[5/6] 按批次发送LLM分析...")
    print("-" * 60)
    
    llm_client = LLMClient()
    total_analyzed = 0
    failed_count = 0
    start_time = time.time()
    
    for batch_idx, batch in enumerate(batches, 1):
        # 准备批次输入
        batch_posts = []
        batch_input = ""
        
        for i, post in enumerate(batch, 1):
            cleaned = kb._clean_quoted_content(post['content'])
            # 限制每条长度
            if len(cleaned) > 250:
                cleaned = cleaned[:250] + "..."
            
            batch_posts.append({
                'post_num': post['post_num'],
                'date': post['date'],
                'content': cleaned
            })
            
            batch_input += f"[{i}] {post['date'].strftime('%Y-%m-%d %H:%M')}\n{cleaned}\n\n"
        
        print(f"批 {batch_idx:3d}/{len(batches):3d} ({len(batch)}条, {len(batch_input)}字符)...", end='', flush=True)
        
        # 构建prompt
        prompt = f"""你是一个专业的股票投资分析师。请分析以下{len(batch)}条帖子，为每条生成单独的分析结果。

帖子内容：
{batch_input}

请严格按照以下JSON格式返回，每条帖子对应一个分析结果，不要遗漏任何一条：
[
    {{"index":1,"tags":["tag1","tag2"],"category":"类型","summary":"摘要","sentiment":"情绪","confidence":"置信度","key_points":["要点"]}},
    {{"index":2,"tags":["tag1"],"category":"类型","summary":"摘要","sentiment":"情绪","confidence":"置信度","key_points":["要点"]}}
]

要求：
1. 只返回JSON数组，不要任何其他文字
2. tags可选：market(市场), technical(技术), stock(个股), sector(板块), strategy(策略), sentiment(情绪)
3. category可选：market_analysis, technical_analysis, trading_signal, sector_rotation, risk_warning, other
4. sentiment可选：bullish(看多), bearish(看空), neutral(中性)
5. confidence可选：high, medium, low
6. summary不超过50字
7. 必须为每一条生成分析结果"""

        messages = [
            {"role": "system", "content": "你是一个专业的股票投资分析师。"},
            {"role": "user", "content": prompt}
        ]
        
        # 调用LLM，带重试
        success = False
        for retry in range(max_retries):
            try:
                response = llm_client.chat(messages, temperature=0.3)
                
                if response:
                    # 解析JSON
                    try:
                        json_str = llm_client._extract_json(response)
                        results = json.loads(json_str)
                        
                        # 验证结果数量
                        if len(results) == len(batch):
                            # 添加到知识库
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
                            print(f" 结果数不匹配({len(results)}!={len(batch)})", end='', flush=True)
                    
                    except json.JSONDecodeError as e:
                        print(f" JSON解析失败", end='', flush=True)
                        if retry < max_retries - 1:
                            print(f" 重试...", flush=True)
                            time.sleep(5)
                            continue
                        else:
                            print(f" 放弃本批", flush=True)
                            failed_count += len(batch)
                else:
                    print(f" LLM无响应", end='', flush=True)
                    if retry < max_retries - 1:
                        print(f" 重试...", flush=True)
                        time.sleep(5)
                        continue
                    else:
                        print(f" 放弃本批", flush=True)
                        failed_count += len(batch)
            
            except Exception as e:
                print(f" 错误: {str(e)[:30]}", end='', flush=True)
                if retry < max_retries - 1:
                    print(f" 重试...", flush=True)
                    time.sleep(5)
                    continue
                else:
                    print(f" 放弃本批", flush=True)
                    failed_count += len(batch)
                break
        
        # RPM限制
        time.sleep(31)
        
        # 显示进度
        if batch_idx % 10 == 0 or success:
            elapsed = time.time() - start_time
            print(f"    进度: {total_analyzed}/{len(posts)} | 失败: {failed_count} | 耗时: {elapsed/60:.1f}分钟")
    
    # 6. 验证
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
    batch_size = 20
    max_retries = 2
    
    total, failed = rebuild_knowledge_base_true_batch(batch_size=batch_size, max_retries=max_retries)
    
    # 如果失败太多，尝试更小的批次
    if failed > 0:
        print(f"\n失败{failed}条，尝试15条一批...")
        total2, failed2 = rebuild_knowledge_base_true_batch(batch_size=15, max_retries=max_retries)
        
        if failed2 > 0:
            print(f"\n失败{failed2}条，尝试10条一批...")
            total3, failed3 = rebuild_knowledge_base_true_batch(batch_size=10, max_retries=max_retries)