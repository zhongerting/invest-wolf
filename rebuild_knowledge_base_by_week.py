#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按周汇总重新构建知识库
每周的所有发言汇总成一个请求发送给大模型进行分析
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

def rebuild_knowledge_base_by_week_summary():
    """按周汇总重新构建知识库"""
    print("="*60)
    print("按周汇总重新构建知识库")
    print("="*60)
    
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
    
    posts.sort(key=lambda x: x['date'], reverse=False)  # 按时间升序排列
    print(f"共获取 {len(posts)} 条发言")
    
    # 4. 按周分组
    print("\n4. 按周分组...")
    posts_by_week = {}
    
    for post in posts:
        post_date = post['date']
        monday = post_date - timedelta(days=post_date.weekday())
        week_key = monday.strftime("%Y-%m-%d")
        
        if week_key not in posts_by_week:
            posts_by_week[week_key] = []
        posts_by_week[week_key].append(post)
    
    print(f"共分为 {len(posts_by_week)} 周")
    for week, posts_in_week in posts_by_week.items():
        print(f"  {week}: {len(posts_in_week)} 条")
    
    # 5. 初始化LLM客户端
    llm_client = LLMClient()
    if not llm_client.is_configured():
        print("错误：LLM未配置")
        return
    
    # 6. 按周汇总分析
    print("\n5. 按周汇总分析...")
    total_analyzed = 0
    
    for week, posts_in_week in sorted(posts_by_week.items()):
        print(f"\n处理周 {week} ({len(posts_in_week)} 条)...")
        
        # 汇总本周所有发言
        weekly_summary = ""
        for i, post in enumerate(posts_in_week, 1):
            content = kb._clean_quoted_content(post['content'])  # 清理引用内容
            weekly_summary += f"【发言{i}】[{post['date'].strftime('%Y-%m-%d %H:%M')}]\n{content}\n\n"
        
        print(f"  汇总内容长度: {len(weekly_summary)} 字符")
        
        # 调用LLM进行周总结
        print("  调用LLM分析...", end='', flush=True)
        
        try:
            # 清理内容
            cleaned_content = kb._clean_quoted_content(weekly_summary)
            
            # 如果内容过长，分段处理
            if len(cleaned_content) > 4000:
                # 分段分析
                segments = []
                chunk_size = 3500
                for i in range(0, len(cleaned_content), chunk_size):
                    segments.append(cleaned_content[i:i+chunk_size])
                
                print(f"（内容过长，分为{len(segments)}段）", end='', flush=True)
                
                all_tags = []
                all_key_points = []
                all_sectors = []
                
                for seg_idx, segment in enumerate(segments, 1):
                    result = llm_client.analyze_post_content(segment, posts_in_week[0]['date'])
                    if result:
                        all_tags.extend(result.get("tags", []))
                        all_key_points.extend(result.get("key_points", []))
                        all_sectors.extend(result.get("mentioned_sectors", []))
                    
                    if seg_idx < len(segments):
                        time.sleep(31)  # RPM限制
                
                # 合并结果
                week_result = {
                    "tags": list(set(all_tags)),
                    "category": "market_analysis",
                    "summary": f"周 {week} 共 {len(posts_in_week)} 条发言",
                    "mentioned_sectors": list(set(all_sectors)),
                    "sentiment": "neutral",
                    "confidence": "medium",
                    "key_points": list(set(all_key_points)),
                    "analysis_method": "llm_segmented"
                }
            else:
                week_result = llm_client.analyze_post_content(cleaned_content, posts_in_week[0]['date'])
            
            print(" 完成")
            
            # 将周分析结果作为一条记录添加到知识库
            week_post = {
                'post_num': f"WEEK_{week}",
                'date': posts_in_week[0]['date'],
                'content': weekly_summary,
                'analysis': week_result
            }
            
            # 添加到知识库
            kb.add_post(
                post_num=f"WEEK_{week}",
                post_date=posts_in_week[0]['date'],
                post_content=weekly_summary
            )
            
            total_analyzed += len(posts_in_week)
            print(f"  分析结果: 标签={week_result.get('tags', [])}, 关键点={len(week_result.get('key_points', []))}个")
            
            # RPM限制
            time.sleep(31)
            
        except Exception as e:
            print(f" 失败: {e}")
        
        print(f" 本周完成，累计处理 {total_analyzed} 条")
    
    # 7. 验证知识库
    print("\n6. 验证知识库...")
    kb = KnowledgeBase()
    print(f"知识库中周记录数量: {len(kb.posts_index)}")
    print(f"标签数量: {len(kb.tags_index)}")
    
    if kb.posts_index:
        print("\n前3条周记录摘要:")
        for i, post in enumerate(kb.posts_index[:3]):
            print(f"\n{i+1}. 周: {post['post_num']}")
            print(f"   日期: {post['date']}")
            print(f"   标签: {post['tags']}")
            print(f"   摘要: {post['summary'][:80]}...")
            print(f"   分析方法: {post.get('analysis_method', 'unknown')}")
    
    print("\n" + "="*60)
    print("知识库按周汇总构建完成！")

if __name__ == "__main__":
    rebuild_knowledge_base_by_week_summary()