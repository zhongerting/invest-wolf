#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试买入和卖出操作对总资产的影响
验证：
1. 买入：从可用资产扣除，市值增加
2. 卖出：从市值扣除，可用资产增加
3. 总资产保持不变（不考虑盈亏）
"""

import sys
sys.path.insert(0, '.')

from main import PositionData
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_buy_operation():
    """测试买入操作"""
    print("\n" + "=" * 60)
    print("测试买入操作")
    print("=" * 60)
    
    position_data = PositionData()
    
    # 记录初始状态
    initial_available = position_data.available_asset
    print(f"\n初始可用资产: ¥{initial_available:,.2f}")
    print(f"初始总资产: ¥{position_data.total_assets:,.2f}")
    
    # 模拟买入操作
    test_prices = {'510210': 1.05}
    position_data.calculate_profit_loss(test_prices)
    initial_market_value = position_data.total_assets - initial_available
    print(f"初始总市值: ¥{initial_market_value:,.2f}")
    
    # 执行买入
    buy_amount = 1000 * 1.05  # 买入1000股，价格1.05
    print(f"\n执行买入: 1000股 @ ¥1.05 = ¥{buy_amount:,.2f}")
    
    try:
        position_data.buy_stock('510210', 1000, 1.05, '上证指数ETF')
        
        print(f"\n买入后:")
        print(f"  可用资产: ¥{position_data.available_asset:,.2f} (减少 ¥{initial_available - position_data.available_asset:,.2f})")
        print(f"  总资产: ¥{position_data.total_assets:,.2f}")
        
        # 验证
        expected_available = initial_available - buy_amount
        print(f"\n验证:")
        print(f"  预期可用资产: ¥{expected_available:,.2f}")
        print(f"  实际可用资产: ¥{position_data.available_asset:,.2f}")
        
        if abs(position_data.available_asset - expected_available) < 0.01:
            print("  ✅ 买入操作验证通过!")
        else:
            print("  ❌ 买入操作验证失败!")
            
    except ValueError as e:
        print(f"\n买入失败: {e}")

def test_sell_operation():
    """测试卖出操作"""
    print("\n" + "=" * 60)
    print("测试卖出操作")
    print("=" * 60)
    
    position_data = PositionData()
    
    # 记录初始状态
    test_prices = {
        '510210': 1.05,
        '515880': 1.45,
        '513260': 1.10,
        '588870': 1.80
    }
    position_data.calculate_profit_loss(test_prices)
    
    initial_available = position_data.available_asset
    initial_market_value = position_data.total_assets - initial_available
    initial_total = position_data.total_assets
    
    print(f"\n初始状态:")
    print(f"  可用资产: ¥{initial_available:,.2f}")
    print(f"  总市值: ¥{initial_market_value:,.2f}")
    print(f"  总资产: ¥{initial_total:,.2f}")
    
    # 执行卖出
    sell_amount = 100 * 1.05  # 卖出100股，价格1.05
    print(f"\n执行卖出: 100股 @ ¥1.05 = ¥{sell_amount:,.2f}")
    
    success = position_data.sell_stock('510210', 100, 1.05)
    
    if success:
        # 重新计算盈亏以更新市值
        position_data.calculate_profit_loss(test_prices)
        
        print(f"\n卖出后:")
        print(f"  可用资产: ¥{position_data.available_asset:,.2f} (增加 ¥{position_data.available_asset - initial_available:,.2f})")
        print(f"  总资产: ¥{position_data.total_assets:,.2f}")
        
        # 验证（卖出后总资产应该增加卖出金额，因为资金从市值转到了可用资产）
        expected_available = initial_available + sell_amount
        print(f"\n验证:")
        print(f"  预期可用资产: ¥{expected_available:,.2f}")
        print(f"  实际可用资产: ¥{position_data.available_asset:,.2f}")
        
        if abs(position_data.available_asset - expected_available) < 0.01:
            print("  ✅ 卖出操作验证通过!")
        else:
            print("  ❌ 卖出操作验证失败!")
    else:
        print("\n卖出失败!")

def main():
    print("\n" + "=" * 60)
    print("完整测试：买入和卖出操作的影响")
    print("=" * 60)
    
    test_buy_operation()
    test_sell_operation()
    
    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()