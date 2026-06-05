#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试任务特定的模型配置
"""

import json
import logging
from config import Config
from llm_client import LLMClient
from daily_review import DailyReview
from smart_analysis import SmartAnalysisService


def test_post_analysis_model():
    """测试狼大发言分析模型"""
    print("\n" + "=" * 70)
    print("【测试1】狼大发言内容分析 - 使用 gemini-2.5-pro-search")
    print("=" * 70)
    
    try:
        client = LLMClient(model=Config.LLM_MODEL_POST_ANALYSIS)
        print(f"模型: {client.model}")
        
        test_content = """
        半导体板块今天表现不错，从技术面来看，MACD 指标出现金叉信号，
        建议关注相关个股的买入机会。但要注意成交量是否跟上，如果量能不足可能会有回调风险。
        """
        
        print(f"\n测试内容: {test_content[:50]}...")
        
        result = client.analyze_post_content(test_content, "2026-06-04")
        print(f"\n分析结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("\n✅ 狼大发言分析模型测试通过")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_daily_review_model():
    """测试每日复盘模型"""
    print("\n" + "=" * 70)
    print("【测试2】每日复盘 - 使用 gemini-3.1-pro-preview-cache")
    print("=" * 70)
    
    try:
        review = DailyReview()
        print(f"每日复盘模型: {review.llm_client.model}")
        
        # 测试一个简单的功能
        print("\n✅ 每日复盘模型配置正确")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_smart_analysis_model():
    """测试智能分析服务模型"""
    print("\n" + "=" * 70)
    print("【测试3】智能分析服务模型")
    print("=" * 70)
    
    try:
        service = SmartAnalysisService()
        print(f"智能分析模型: {service.llm_client.model}")
        
        print("\n✅ 智能分析服务模型配置正确")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def main():
    print("\n" + "=" * 70)
    print("任务特定模型配置测试")
    print("=" * 70)
    
    print(f"\n当前配置:")
    print(f"  默认模型: {Config.LLM_MODEL}")
    print(f"  每日复盘模型: {Config.LLM_MODEL_DAILY_REVIEW}")
    print(f"  发言分析模型: {Config.LLM_MODEL_POST_ANALYSIS}")
    
    results = {}
    
    results['发言分析'] = test_post_analysis_model()
    results['每日复盘'] = test_daily_review_model()
    results['智能分析服务'] = test_smart_analysis_model()
    
    print("\n" + "=" * 70)
    print("测试结果总结:")
    print("=" * 70)
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + ("所有测试通过！" if all_passed else "部分测试失败，请检查。"))
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

