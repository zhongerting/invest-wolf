#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试NGA爬取功能
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nga_crawler import NGACrawler

print("="*60)
print("测试NGA帖子爬取功能")
print("="*60)

# 创建爬取客户端
crawler = NGACrawler()

print("\n1. ngapost2md工具状态:", "可用" if crawler.is_available() else "不可用")

if crawler.is_available():
    # 测试爬取
    tid = 45974302
    uid = 150058
    
    print("\n2. 开始爬取帖子 TID:%d UID:%d..." % (tid, uid))
    
    try:
        result_dir = crawler.crawl_post(tid, uid)
        
        if result_dir:
            print("   爬取成功！结果目录:", result_dir)
            
            # 检查生成的文件
            post_file = os.path.join(result_dir, 'post.md')
            if os.path.exists(post_file):
                file_size = os.path.getsize(post_file)
                print("   生成帖子文件: post.md (%d bytes)" % file_size)
                
                # 读取内容
                with open(post_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    print("   帖子内容: %d 行" % len(lines))
                    print("   字符数: %d" % len(content))
                    
                    # 显示前几行
                    print("\n   帖子预览 (前10行):")
                    print("   " + "="*50)
                    for i, line in enumerate(lines[:10]):
                        print("   %d: %s" % (i+1, line[:100]))
                    
            else:
                print("   未找到 post.md 文件")
            
            # 获取最新时间
            latest_time = crawler.get_latest_post_time(result_dir)
            if latest_time:
                print("\n   最新发言时间:", latest_time.strftime('%Y-%m-%d %H:%M:%S'))
        
        else:
            print("   爬取失败")
            
    except Exception as e:
        print("   爬取异常:", str(e).encode('utf-8', errors='replace').decode('utf-8'))

else:
    print("   请检查ngapost2md是否正确配置")

print("\n" + "="*60)
print("测试完成！")