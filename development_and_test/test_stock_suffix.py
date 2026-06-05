#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试股票API后缀问题
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from config import Config

print("="*60)
print("测试股票API后缀问题")
print("="*60)

test_codes = [
    "510210",
    "510210.SH",
    "510210.SZ",
]

for code in test_codes:
    print(f"\n测试代码: {code}")
    url = f"{Config.BIYING_BASE_URL}/hsstock/real/time/{code}/{Config.BIYING_LICENCE}"
    print(f"  请求URL: {url}")
    
    try:
        resp = requests.get(url, timeout=15)
        print(f"  HTTP状态: {resp.status_code}")
        data = resp.json()
        print(f"  响应数据: {data}")
        
        if isinstance(data, dict) and "error" not in data:
            print(f"  ✅ 成功! 价格: {data.get('p')}")
        else:
            print(f"  ❌ 失败: {data}")
            
    except Exception as e:
        print(f"  ❌ 异常: {e}")

print("\n" + "="*60)
