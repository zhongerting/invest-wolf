#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试全量知识库
"""

import os
import json
from datetime import datetime
from config import Config

def count_posts_by_date_range():
    """统计各时间段的帖子数量"""
    
    # 读取 posts_index.json
    posts_index_file = os.path.join(Config.KNOWLEDGE_BASE_DIR, "posts_index.json")
    
    if not os.path.exists(posts_index_file):
        print("❌ posts_index.json 不存在")
        return
    
    with open(posts_index_file, 'r', encoding='utf-8') as f:
        posts_index = json.load(f)
    
    print(f"知识库总帖子数: {len(posts_index)}")
    print()
    
    # 统计各月帖子数
    posts_by_month = {}
    for post in posts_index:
        date_str = post['date']
        try:
            post_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            month_key = post_date.strftime("%Y-%m")
            if month_key not in posts_by_month:
                posts_by_month[month_key] = []
            posts_by_month[month_key].append(post)
        except:
            continue
    
    # 按月份排序
    sorted_months = sorted(posts_by_month.keys())
    
    print("各月帖子分布：")
    for month in sorted_months:
        posts = posts_by_month[month]
        print(f"  {month}: {len(posts)} 条")
    
    print()
    
    # 统计近30天帖子数
    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)
    
    recent_posts = []
    for post in posts_index:
        try:
            post_date = datetime.strptime(post['date'], "%Y-%m-%d %H:%M:%S")
            if post_date >= thirty_days_ago:
                recent_posts.append(post)
        except:
            continue
    
    print(f"近30天帖子数: {len(recent_posts)}")
    print()
    
    # 计算全量数据的大小
    total_size = 0
    for root, dirs, files in os.walk(Config.KNOWLEDGE_BASE_DIR):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)
    
    print(f"知识库总大小: {total_size / 1024 / 1024:.2f} MB")
    print()
    
    # 检查是否需要添加全量数据
    print("=" * 60)
    print("建议：")
    if len(posts_index) < 1000:
        print("  ✅ 当前知识库帖子数量适中")
    else:
        print(f"  ⚠️ 当前知识库有 {len(posts_index)} 条帖子，较多")
    
    if total_size / 1024 / 1024 < 10:
        print("  ✅ 全量数据大小适中 (< 10MB)")
    else:
        print(f"  ⚠️ 全量数据较大 ({total_size / 1024 / 1024:.2f} MB)")
        print("  💡 建议：使用向量数据库或分块检索来优化")

if __name__ == "__main__":
    from datetime import timedelta
    count_posts_by_date_range()
