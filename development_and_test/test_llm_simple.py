#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试LLM调用
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_client import LLMClient

print("测试LLM连接...")

llm_client = LLMClient()

print(f"API URL: {llm_client.api_url}")
print(f"模型: {llm_client.model}")
print(f"已配置: {llm_client.is_configured()}")

# 测试简单对话
messages = [
    {"role": "system", "content": "你是一个助手。"},
    {"role": "user", "content": "你好！"}
]

print("\n发送测试请求...")
try:
    response = llm_client.chat(messages, temperature=0.3)
    print(f"响应: {response}")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

print("\n测试完成")