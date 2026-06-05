#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的持仓显示逻辑
验证：总资产 = 总市值 + 可用资产，买入/卖出操作的影响
"""

import sys
sys.path.insert(0, '.')

from main import PositionData
from database import DatabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_position_data():
    """测试持仓数据管理"""
    print("=" * 60)
    print("测试新的持仓显示逻辑")
    print("=" * 60)
    
    # 创建持仓数据实例
    position_data = PositionData()
    
    print(f"\n初始状态:")
    print(f"  持仓数量: {len(position_data.positions)}")
    print(f"  总资产: ¥{position_data.total_assets:,.2f}")
    print(f"  可用资产: ¥{position_data.available_asset:,.2f}")
    
    # 测试价格
    test_prices = {
        '510210': 1.05,
        '515880': 1.45,
        '513260': 1.10,
        '588870': 1.80
    }
    
    print(f"\n使用测试价格计算盈亏:")
    result = position_data.calculate_profit_loss(test_prices)
    
    print(f"  总市值: ¥{result['total_market_value']:,.2f}")
    print(f"  持仓占比: {result['position_ratio']:.2f}%")
    print(f"  可用资产: ¥{result['available_asset']:,.2f}")
    print(f"  总资产（计算值）: ¥{position_data.total_assets:,.2f}")
    print(f"  总资产（公式验证）: ¥{result['total_market_value'] + result['available_asset']:,.2f}")
    
    # 验证公式
    expected_total = result['total_market_value'] + result['available_asset']
    if abs(position_data.total_assets - expected_total) < 0.01:
        print(f"\n✅ 公式验证通过: 总资产 = 总市值 + 可用资产")
    else:
        print(f"\n❌ 公式验证失败!")
    
    # 显示持仓明细
    print(f"\n持仓明细:")
    for pos in position_data.positions:
        print(f"  {pos['code']} - {pos['name']}:")
        print(f"    数量: {pos['quantity']}股")
        print(f"    成本价: ¥{pos['cost_price']:.3f}")
        print(f"    现价: ¥{pos.get('current_price', 0):.3f}")
        print(f"    市值: ¥{pos.get('market_value', 0):,.2f}")
        print(f"    盈亏: ¥{pos.get('profit', 0):,.2f} ({pos.get('profit_percent', 0):+.2f}%)")
        print(f"    仓位占比: {pos.get('position_percent', 0):.2f}%")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_position_data()