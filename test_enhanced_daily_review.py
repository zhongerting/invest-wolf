#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强版每日复盘功能
"""

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from daily_review import DailyReview
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_enhanced_daily_review():
    """测试增强版每日复盘"""
    print("="*70)
    print("🧪 增强版每日复盘功能测试")
    print("="*70)
    
    review = DailyReview()
    
    # 生成报告
    print("\n📝 正在生成每日复盘报告...")
    report = review.generate_review(use_llm=True)
    
    print(f"\n✅ 报告生成成功！")
    print(f"📅 报告日期: {report['report_date']}")
    print(f"🐺 狼大发言数: {len(report['wolf_posts'])}")
    
    # 测试今日持仓
    print("\n" + "="*70)
    print("💼 今日持仓信息")
    print("="*70)
    positions = report['today_positions']
    print(f"- 持仓股票数: {positions['total_stocks']}")
    print(f"- 持仓总市值: {positions['total_value']:.2f} 元")
    print(f"- 总盈亏: {positions['total_profit']:.2f} 元 ({positions['total_profit_pct']:.2f}%)")
    
    if positions['positions']:
        print("\n持仓明细:")
        for pos in positions['positions']:
            profit_icon = "✅" if pos['profit_pct'] >= 0 else "❌"
            print(f"  {profit_icon} {pos['stock_name']}({pos['stock_code']}): {pos['quantity']}股, 盈亏{pos['profit_pct']:.2f}%")
    
    # 测试狼大交易思路分析
    print("\n" + "="*70)
    print("🧐 狼大交易思路分析")
    print("="*70)
    wolf_summary = report['wolf_daily_summary']
    if wolf_summary:
        print(f"- 整体观点: {wolf_summary.get('overall_view', '无')}")
        print(f"- 投资主线: {wolf_summary.get('investment_theme', '无')}")
        
        if wolf_summary.get('key_signals'):
            print("- 关键信号:")
            for signal in wolf_summary['key_signals']:
                print(f"  • {signal}")
        
        if wolf_summary.get('trading_philosophy'):
            print(f"- 交易哲学: {wolf_summary['trading_philosophy']}")
    
    # 测试操作评分
    print("\n" + "="*70)
    print("📝 今日操作复盘评分")
    print("="*70)
    op_review = report['operation_review']
    print(f"- 综合评分: {op_review['score']} 分")
    print(f"- 评价: {op_review['evaluation']}")
    
    if op_review['suggestions']:
        print("- 改进建议:")
        for sug in op_review['suggestions']:
            print(f"  • {sug}")
    
    # 测试明日操作计划
    print("\n" + "="*70)
    print("🎯 明日操作计划")
    print("="*70)
    tomorrow_plan = report.get('tomorrow_plan', {})
    
    if tomorrow_plan:
        market_cond = tomorrow_plan.get('market_conditions', {})
        if market_cond.get('key_levels'):
            print("- 关键点位:")
            for level in market_cond['key_levels']:
                print(f"  • {level}")
        
        watchlist = tomorrow_plan.get('key_watchlist', [])
        if watchlist:
            print("\n- 重点关注:")
            for item in watchlist:
                print(f"  • {item.get('stock_name', '未知')}({item.get('stock_code', '')}): {item.get('reason', '')}")
        
        if_then = tomorrow_plan.get('if_then_actions', [])
        if if_then:
            print("\n- If-Then策略:")
            for i, action in enumerate(if_then, 1):
                priority_icon = "🔴" if action.get('priority') == 'high' else "🟡" if action.get('priority') == 'medium' else "🟢"
                print(f"  {i}. {priority_icon} {action.get('condition', '')}")
                print(f"     操作: {action.get('action', '')}")
    
    print("\n" + "="*70)
    print("✅ 增强版每日复盘功能测试完成！")
    print("="*70)
    print("\n💡 报告已保存到:")
    report_date = datetime.now().strftime("%Y-%m-%d")
    from config import Config
    report_path = os.path.join(Config.DAILY_REPORT_DIR, f"{report_date}_daily_report.md")
    print(f"   {report_path}")

if __name__ == "__main__":
    test_enhanced_daily_review()
