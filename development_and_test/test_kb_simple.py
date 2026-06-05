#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试知识库加载
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from knowledge_base import KnowledgeBase

print("="*60)
print("简单测试知识库加载")
print("="*60)

# 创建知识库
kb = KnowledgeBase()

print("\n1. 知识库状态")
print("   帖子索引数量:", len(kb.posts_index))
print("   标签索引数量:", len(kb.tags_index))

# 检查是否有数据
if kb.posts_index:
    print("\n2. 最新10条发言")
    print("-" * 60)
    
    # 获取最新的10条
    latest_posts = sorted(kb.posts_index, key=lambda x: x['date'], reverse=True)[:10]
    
    for i, post in enumerate(latest_posts, 1):
        print(f"\n发言 #{post['post_num']}")
        print(f"日期: {post['date']}")
        print(f"标签: {post.get('tags', [])}")
        summary = post.get('summary', '')[:80] + "..." if len(post.get('summary', '')) > 80 else post.get('summary', '')
        print(f"摘要: {summary}")

print("\n" + "="*60)
print("测试完成！")