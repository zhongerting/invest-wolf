#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试不同类型的股票
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from config import Config

print("="*60)
print("测试不同类型的股票")
print("="*60)

test_codes = [
    "600519",  # 贵州茅台 (主板)
    "000001",  # 平安银行 (主板)
    "000002",  # 万科A
    "510300",  # 沪深300ETF
    "510500",  # 中证500ETF
]

for code in test_codes:
    print(f"\n测试代码: {code}")
    url = f"{Config.BIYING_BASE_URL}/hsstock/real/time/{code}/{Config.BIYING_LICENCE}"
    print(f"  请求URL: {url}")
    
    try:
        resp = requests.get(url, timeout=15)
        print(f"  HTTP状态: {resp.status_code}")
        data = resp.json()
        
        if isinstance(data, dict) and "error" not in data:
            print(f"  ✅ 成功!")
            print(f"     价格: {data.get('p')}")
            print(f"     涨跌: {data.get('ud')}")
            print(f"     涨跌幅: {data.get('pc')}")
        else:
            print(f"  ❌ 失败: {data}")
            
    except Exception as e:
        print(f"  ❌ 异常: {e}")

print("\n" + "="*60)
