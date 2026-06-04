#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试综合数据源功能
"""

import os
import sys
import json

# 设置环境变量
os.environ['MX_APIKEY'] = 'mkt_y5OEqO1aoagzi_AmfQmbCBzQsRcVDi2GafW6QCsifjs'

print("="*60)
print("综合数据源功能测试")
print("="*60)

from data_source import DataSource

# 初始化数据源
print("\n1. 初始化综合数据源...")
ds = DataSource()
print("   ✓ 初始化完成")

# 测试必盈API - 股票价格
print("\n2. 测试必盈API - 股票价格查询...")
try:
    price_data = ds.get_stock_price("510210")
    print(f"   510210 数据: {json.dumps(price_data, ensure_ascii=False, indent=4)[:200]}...")
except Exception as e:
    print(f"   ✗ 错误: {e}")

# 测试必盈API - 指数数据
print("\n3. 测试必盈API - 指数数据查询...")
try:
    index_data = ds.get_index_data("上证指数")
    print(f"   上证指数 数据: {json.dumps(index_data, ensure_ascii=False, indent=4)[:200]}...")
except Exception as e:
    print(f"   ✗ 错误: {e}")

# 测试东方财富公开API - 分时数据
print("\n4. 测试东方财富公开API - 分时数据...")
try:
    tick_data = ds.get_tick_data("000001")
    if tick_data:
        print(f"   ✓ 获取到分时数据")
        print(f"     名称: {tick_data.get('name')}")
        print(f"     日期: {tick_data.get('date')}")
        print(f"     分时数据条数: {len(tick_data.get('trends', []))}")
        if tick_data.get('trends'):
            print(f"     前2条分时数据: {tick_data.get('trends')[:2]}")
    else:
        print(f"   ⚠ 未获取到分时数据")
except Exception as e:
    print(f"   ✗ 错误: {e}")

# 测试东方财富妙想API - 主力资金流向
print("\n5. 测试东方财富妙想API - 主力资金流向...")
try:
    funds_data = ds.get_main_funds("510210")
    if funds_data:
        print(f"   ✓ 获取到主力资金数据")
        print(f"     数据预览: {str(funds_data)[:300]}...")
    else:
        print(f"   ⚠ 未获取到主力资金数据")
except Exception as e:
    print(f"   ✗ 错误: {e}")

print("\n" + "="*60)
print("测试完成！")
print("="*60)
