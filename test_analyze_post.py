#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 analyze_post_content 方法
"""

import os
import sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_client import LLMClient

print("测试 analyze_post_content...")

llm_client = LLMClient()

# 测试简短内容
test_content = """今天大盘走势不错，半导体板块表现强势。
从技术面看，MACD金叉，成交量放大。
注意风险控制。"""

print(f"输入内容长度: {len(test_content)}")
print("\n发送请求...")

try:
    response = llm_client.analyze_post_content(test_content, datetime.now())
    print(f"响应类型: {type(response)}")
    print(f"响应: {response}")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

print("\n测试完成")