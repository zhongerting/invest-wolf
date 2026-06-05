#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试必盈API客户端功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from biying_client import BiyingClient

print("=" * 60)
print("必盈API客户端功能测试")
print("=" * 60)

client = BiyingClient()

print(f"\nis_configured(): {client.is_configured()}")

print("\n" + "-" * 60)
print("测试1: 普通股票 (600519 贵州茅台):")
data = client.get_stock_price("600519")
print(f"  代码: {data.get('code')}")
print(f"  名称: {data.get('name')}")
print(f"  价格: {data.get('price')}")
print(f"  涨跌: {data.get('change')}")
print(f"  涨跌幅: {data.get('change_percent')}")
print(f"  是否模拟: {data.get('is_mock')}")
if not data.get('is_mock'):
    print("  ✅ 使用真实API数据")

print("\n" + "-" * 60)
print("测试2: 上证指数 (000001):")
data = client.get_index_data("000001")
print(f"  代码: {data.get('code')}")
print(f"  名称: {data.get('name')}")
print(f"  价格: {data.get('price')}")
print(f"  涨跌: {data.get('change')}")
print(f"  涨跌幅: {data.get('change_percent')}")
print(f"  是否模拟: {data.get('is_mock')}")
if not data.get('is_mock'):
    print("  ✅ 使用真实API数据")

print("\n" + "-" * 60)
print("测试3: ETF (510210):")
data = client.get_stock_price("510210")
print(f"  代码: {data.get('code')}")
print(f"  名称: {data.get('name')}")
print(f"  价格: {data.get('price')}")
print(f"  涨跌: {data.get('change')}")
print(f"  涨跌幅: {data.get('change_percent')}")
print(f"  是否模拟: {data.get('is_mock')}")
if data.get('is_mock'):
    print("  ⚠️ 使用模拟数据（必盈API不支持此ETF）")
else:
    print("  ✅ 使用真实API数据")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
