#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试智能分析服务 - 增量爬取和分析
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smart_analysis import SmartAnalysisService

print("="*60)
print("测试智能分析服务")
print("="*60)

# 创建分析服务
service = SmartAnalysisService()

print("\n1. 检查服务状态")
print("   NGA爬取器:", "可用" if service.nga_crawler.is_available() else "不可用")
print("   LLM客户端:", "已配置" if service.llm_client.is_configured() else "未配置")
print("   上次爬取时间:", service.last_crawl_time)

print("\n2. 开始增量爬取和分析...")

try:
    result = service.process_new_posts()
    
    print("\n3. 处理结果")
    print("   成功:", result['success'])
    print("   新发言数量:", result['new_post_count'])
    print("   消息:", result['message'])
    
    if result['analyses']:
        print("\n4. 分析结果详情")
        print("-" * 60)
        
        for i, analysis in enumerate(result['analyses']):
            print("\n发言", i+1)
            print("时间:", analysis['date'])
            print("内容预览:", analysis['content'][:100], "...")
            print("\n分析结果:")
            print("  标签:", analysis['analysis'].get('tags', []))
            print("  分类:", analysis['analysis'].get('category', ''))
            print("  摘要:", analysis['analysis'].get('summary', '')[:50], "...")
            
            if analysis['action_indications']:
                print("\n  操作指示:")
                for idx, indication in enumerate(analysis['action_indications']):
                    print("    %d - %s" % (idx+1, indication))
            
            if analysis['risk_warnings']:
                print("\n  风险提示:")
                for idx, warning in enumerate(analysis['risk_warnings']):
                    print("    %d - %s" % (idx+1, warning))
            
            if analysis['related_knowledge']:
                print(f"\n  📚 相关历史发言: {len(analysis['related_knowledge'])} 条")
        
        print("\n" + "-" * 60)
        print("分析完成！")
    
    else:
        print("\n   暂无新发言")
        
except Exception as e:
    print("\n   错误:", str(e))

print("\n" + "="*60)
print("测试完成！")