#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按批次汇总重新构建知识库（小批次版本）
"""

import os
import sys
import shutil
import time
import traceback
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nga_crawler import NGACrawler
from knowledge_base import KnowledgeBase
from llm_client import LLMClient

def rebuild_knowledge_base_by_small_batch():
    """按小批次汇总重新构建知识库"""
    print("="*60)
    print("按小批次汇总重新构建知识库")
    print("="*60)
    
    # 每批最多处理的发言数（较小的批次）
    BATCH_SIZE = 20
    
    # 1. 清理现有知识库
    print("\n1. 清理现有知识库...")
    kb = KnowledgeBase()
    
    if os.path.exists(kb.base_dir):
        shutil.rmtree(kb.base_dir)
        print(f"已删除知识库目录: {kb.base_dir}")
    
    # 2. 初始化新的知识库
    print("\n2. 初始化新的知识库...")
    kb = KnowledgeBase()
    print(f"知识库已初始化，目录: {kb.base_dir}")
    
    # 3. 爬取所有发言
    print("\n3. 爬取所有发言...")
    crawler = NGACrawler()
    
    if not crawler.is_available():
        print("错误：NGA爬取器不可用")
        return
    
    result_dir = crawler.crawl_post(45974302, 150058)
    if not result_dir:
        print("错误：爬取失败")
        return
    
    post_file = os.path.join(result_dir, 'post.md')
    if not os.path.exists(post_file):
        print("错误：未找到帖子文件")
        return
    
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
                if date_match:
                    date_str = date_match.group(1)
                    post_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
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
    
    if current_post:
        current_post['content'] = '\n'.join(current_content).strip()
        posts.append(current_post)
    
    posts.sort(key=lambda x: x['date'], reverse=False)
    print(f"共获取 {len(posts)} 条发言")
    
    # 4. 按批次分组
    print(f"\n4. 按批次分组（每批{BATCH_SIZE}条）...")
    batches = []
    
    for i in range(0, len(posts), BATCH_SIZE):
        batches.append(posts[i:i+BATCH_SIZE])
    
    print(f"共分为 {len(batches)} 批")
    
    # 5. 初始化LLM客户端
    llm_client = LLMClient()
    if not llm_client.is_configured():
        print("错误：LLM未配置")
        return
    
    # 6. 按批次汇总分析
    print("\n5. 按批次汇总分析...")
    total_analyzed = 0
    failed_batches = 0
    
    for batch_idx, batch in enumerate(batches, 1):
        print(f"\n处理批次 {batch_idx}/{len(batches)}（{len(batch)} 条）...")
        
        # 汇总本批所有发言
        batch_summary = ""
        for i, post in enumerate(batch, 1):
            # 清理引用内容
            content = kb._clean_quoted_content(post['content'])
            # 只取前200字符
            if len(content) > 200:
                content = content[:200] + "..."
            batch_summary += f"【{i}】[{post['date'].strftime('%m-%d %H:%M')}]\n{content}\n\n"
        
        content_length = len(batch_summary)
        print(f"  内容长度: {content_length} 字符")
        
        # 调用LLM分析
        print("  调用LLM分析...", end='', flush=True)
        
        try:
            # 调用LLM分析
            result = llm_client.analyze_post_content(batch_summary, batch[0]['date'])
            
            print(" 完成")
            
            # 添加到知识库
            batch_id = f"BATCH_{batch_idx:03d}_{batch[0]['date'].strftime('%Y%m%d')}"
            kb.add_post(
                post_num=batch_id,
                post_date=batch[0]['date'],
                post_content=batch_summary
            )
            
            total_analyzed += len(batch)
            tags = result.get('tags', [])[:3]  # 只显示前3个标签
            print(f"  结果: 标签={tags}, 关键点={len(result.get('key_points', []))}个")
            
            # RPM限制（每分钟最多2次请求）
            time.sleep(31)
            
        except Exception as e:
            print(f" 失败: {e}")
            traceback.print_exc()
            failed_batches += 1
        
        print(f" 累计: {total_analyzed}/{len(posts)} 条")
    
    # 7. 验证知识库
    print("\n6. 验证知识库...")
    kb = KnowledgeBase()
    print(f"知识库中批次记录数量: {len(kb.posts_index)}")
    print(f"标签数量: {len(kb.tags_index)}")
    print(f"失败批次: {failed_batches}")
    
    if kb.posts_index:
        print("\n前3条批次记录摘要:")
        for i, post in enumerate(kb.posts_index[:3]):
            print(f"\n{i+1}. 批次: {post['post_num']}")
            print(f"   日期: {post['date']}")
            print(f"   标签: {post['tags']}")
            print(f"   摘要: {post['summary'][:80]}...")
    
    print("\n" + "="*60)
    print("知识库按批次汇总构建完成！")

if __name__ == "__main__":
    rebuild_knowledge_base_by_small_batch()