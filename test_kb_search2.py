#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试知识库功能
"""

from knowledge_base import KnowledgeBase

print("="*60)
print("测试知识库功能")
print("="*60)

kb = KnowledgeBase()

# 统计标签分布
tag_counts = {}
for post in kb.posts_index:
    tags = post.get('tags', [])
    for tag in tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

print("\n1. 标签分布统计")
print("-" * 40)
for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"   {tag}: {count} 条")

# 查找包含特定关键词的发言
print("\n2. 搜索包含'半导体'的发言")
print("-" * 40)
semiconductor_posts = [p for p in kb.posts_index if '半导体' in p.get('summary', '') or '半导体' in p.get('content', '')]
print(f"   找到 {len(semiconductor_posts)} 条相关发言")
for p in semiconductor_posts[:3]:
    print(f"\n   日期: {p['date']}")
    print(f"   摘要: {p['summary'][:60]}...")

# 查找最近的发言
print("\n3. 最近5条发言")
print("-" * 40)
latest = sorted(kb.posts_index, key=lambda x: x['date'], reverse=True)[:5]
for p in latest:
    print(f"\n   日期: {p['date']}")
    print(f"   标签: {p.get('tags', [])}")
    print(f"   分类: {p.get('category', '')}")

print("\n" + "="*60)
print("测试完成！")