#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试知识库检索功能
"""

from knowledge_base import KnowledgeBase

print("="*60)
print("测试知识库检索功能")
print("="*60)

kb = KnowledgeBase()

# 测试标签检索
print("\n1. 按标签检索 - technical")
results = kb.search_by_tag('technical')
print(f"   找到 {len(results)} 条技术分析相关发言")
print("   最近5条:")
for r in results[:5]:
    print(f"     - {r['date'][:16]}: {r['summary'][:50]}...")

# 测试标签检索 - strategy
print("\n2. 按标签检索 - strategy")
results = kb.search_by_tag('strategy')
print(f"   找到 {len(results)} 条策略相关发言")

# 测试标签检索 - market
print("\n3. 按标签检索 - market")
results = kb.search_by_tag('market')
print(f"   找到 {len(results)} 条市场分析相关发言")

# 测试日期范围检索
print("\n4. 按日期范围检索（今天）")
from datetime import datetime
today = datetime.now().date()
results = kb.search_by_date(today, today)
print(f"   今天的发言数: {len(results)}")

print("\n" + "="*60)
print("检索测试完成！")