#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按批次汇总重新构建知识库（每条单独结果）
30条一批发送给LLM，LLM为每条发言生成单独的分析结果
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

def rebuild_knowledge_base_with_individual_results():
    """按批次汇总重新构建知识库（每条单独结果）"""
    print("="*60)
    print("按批次汇总重新构建知识库（每条单独结果）")
    print("="*60)
    
    BATCH_SIZE = 30
    
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
    
    # 5. 按批次分析（每条单独结果）
    print("[5/6] 按批次分析（每条单独结果，预计每批50-60秒）...")
    print("-" * 60)
    
    llm_client = LLMClient()
    total_analyzed = 0
    failed_count = 0
    start_time = time.time()
    
    for batch_idx, batch in enumerate(batches, 1):
        # 构建批次输入（每条发言标记序号）
        batch_input = ""
        cleaned_posts = []  # 保存清理后的内容用于匹配
        
        for i, post in enumerate(batch, 1):
            cleaned_content = kb._clean_quoted_content(post['content'])
            # 限制长度
            if len(cleaned_content) > 300:
                cleaned_content = cleaned_content[:300] + "..."
            
            cleaned_posts.append({
                'post_num': post['post_num'],
                'date': post['date'],
                'content': cleaned_content
            })
            
            batch_input += f"【发言{i}】\n日期: {post['date'].strftime('%Y-%m-%d %H:%M')}\n内容:\n{cleaned_content}\n\n"
        
        print(f"批 {batch_idx:3d}/{len(batches):3d} ({len(batch)}条, {len(batch_input)}字符)...", end='', flush=True)
        
        # 调用LLM分析（要求为每条发言单独生成结果）
        try:
            # 构建prompt要求单独分析每条
            prompt = f"""请分析以下股票投资相关的帖子内容，为每条发言单独生成分析结果：

帖子内容：
{batch_input}

请按照以下JSON格式返回，为每条发言生成单独的分析结果：
[
    {{
        "index": 1,  // 对应【发言1】
        "tags": ["标签1", "标签2"],
        "category": "market_analysis|technical_analysis|trading_signal|other",
        "summary": "简短摘要（50字以内）",
        "mentioned_sectors": ["半导体"],
        "sentiment": "bullish|bearish|neutral",
        "confidence": "high|medium|low",
        "key_points": ["关键点"]
    }},
    {{
        "index": 2,  // 对应【发言2】
        ...
    }}
]

注意：
1. 只返回JSON数组，不要其他内容
2. tags从以下类别选择：market(市场分析), technical(技术分析), stock(个股), sector(板块), sentiment(情绪), strategy(策略)
3. 如果内容不涉及股市，category设为"other"
4. 必须为每条发言生成一个结果对象"""
            
            messages = [
                {"role": "system", "content": "你是专业股票投资分析师，擅长分析帖子并提取关键信息。"},
                {"role": "user", "content": prompt}
            ]
            
            response = llm_client.chat(messages, temperature=0.3)
            
            if not response:
                print(f" LLM无响应", flush=True)
                failed_count += len(batch)
                time.sleep(31)
                continue
            
            # 解析返回的JSON数组
            try:
                json_str = llm_client._extract_json(response)
                results = json.loads(json_str)
            except Exception as e:
                print(f" 解析失败: {str(e)[:30]}", flush=True)
                failed_count += len(batch)
                time.sleep(31)
                continue
            
            # 将每条结果添加到知识库
            for result in results:
                idx = result.get('index', 0) - 1  # 转换为0-based索引
                
                if idx >= 0 and idx < len(cleaned_posts):
                    post = cleaned_posts[idx]
                    
                    # 添加到知识库
                    kb.add_post(
                        post_num=post['post_num'],
                        post_date=post['date'],
                        post_content=post['content']
                    )
                    
                    total_analyzed += 1
            
            tags = results[0].get('tags', [])[:2] if results else []
            print(f" 完成 | 第1条标签:{tags} | 累计:{total_analyzed}/{len(posts)}", flush=True)
            
        except Exception as e:
            print(f" 错误: {str(e)[:30]}", flush=True)
            failed_count += len(batch)
        
        # RPM限制
        time.sleep(31)
    
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
    rebuild_knowledge_base_with_individual_results()