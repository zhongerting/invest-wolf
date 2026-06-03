#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试备用API (Anthropic)
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_client import LLMClient

def test_backup_api():
    print("="*60)
    print("测试备用API (Anthropic)")
    print("="*60)
    
    llm_client = LLMClient()
    
    # 强制切换到备用API
    llm_client._switch_to_backup()
    print(f"API URL: {llm_client.api_url}")
    print(f"API Key: {llm_client.api_key[:20]}...")
    print(f"Model: {llm_client.model}")
    print()
    
    # 发送测试请求
    messages = [
        {"role": "system", "content": "你是一个专业的股票投资分析师。"},
        {"role": "user", "content": "你好，请简单介绍一下自己。"}
    ]
    
    print("发送测试请求...")
    start_time = time.time()
    
    try:
        response = llm_client.chat(messages, temperature=0.3, max_tokens=500)
        elapsed = time.time() - start_time
        
        print(f"耗时: {elapsed:.1f}秒")
        print(f"响应: {response[:200] if response else '无响应'}...")
        
    except Exception as e:
        print(f"错误: {e}")
    
    print("="*60)

if __name__ == "__main__":
    test_backup_api()