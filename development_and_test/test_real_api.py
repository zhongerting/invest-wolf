#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试真实API获取所有持仓股票价格
"""

import os
import sys

# 设置环境变量
os.environ['MX_APIKEY'] = 'mkt_y5OEqO1aoagzi_AmfQmbCBzQsRcVDi2GafW6QCsifjs'

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from eastmoney_client import EastMoneyClient

# 用户持仓
positions = [
    {'code': '510210', 'name': '上证指数ETF', 'quantity': 27000, 'cost_price': 1.031},
    {'code': '515880', 'name': '半导体ETF', 'quantity': 10000, 'cost_price': 1.541},
    {'code': '513260', 'name': '新能源车ETF', 'quantity': 1700, 'cost_price': 1.232}
]

print("="*60)
print("测试东方财富妙想API获取股票价格")
print("="*60)

client = EastMoneyClient(use_real_api=True)

total_market_value = 0
total_cost = 0
total_profit = 0

print(f"\n{'代码':<10} {'名称':<15} {'持仓':<8} {'成本价':<8} {'现价':<8} {'市值':<12} {'盈亏':<10} {'盈亏%':<8}")
print("-"*80)

for pos in positions:
    code = pos['code']
    name = pos['name']
    quantity = pos['quantity']
    cost_price = pos['cost_price']
    
    # 获取实时价格
    price_data = client.get_stock_price(code)
    current_price = price_data['price']
    
    market_value = current_price * quantity
    cost_value = cost_price * quantity
    profit = market_value - cost_value
    profit_percent = (profit / cost_value) * 100
    
    total_market_value += market_value
    total_cost += cost_value
    total_profit += profit
    
    # 颜色标记
    color = 'green' if profit >= 0 else 'red'
    
    print(f"{code:<10} {name:<15} {quantity:<8} {cost_price:<8.3f} {current_price:<8.3f} "
          f"{market_value:<12.2f} {profit:<10.2f} {profit_percent:<8.2f}%")

print("-"*80)
print(f"{'合计':<10} {'':<15} {'':<8} {'':<8} {'':<8} {total_market_value:<12.2f} "
      f"{total_profit:<10.2f} {(total_profit/total_cost*100):<8.2f}%")

print(f"\n总资产: {total_market_value:.2f} 元")
print(f"总成本: {total_cost:.2f} 元")
print(f"总盈亏: {total_profit:.2f} 元 ({(total_profit/total_cost*100):.2f}%)")

print("\n✅ API测试成功！")