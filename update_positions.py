#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新现有持仓数据
"""
import json
import logging
from datetime import datetime
from eastmoney_client import EastMoneyClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_positions():
    """更新现有持仓数据"""
    try:
        # 读取当前持仓
        with open('positions.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        positions = data.get('positions', [])
        total_assets = data.get('total_assets', 0)
        
        logger.info(f"当前持仓共 {len(positions)} 只股票")
        
        # 初始化客户端
        client = EastMoneyClient()
        
        # 更新每只持仓
        updated_positions = []
        for pos in positions:
            code = pos.get('code')
            if not code:
                continue
                
            logger.info(f"正在更新 {pos.get('name', code)}({code})...")
            
            # 获取最新股票信息
            price_data = client.get_stock_price(code)
            if price_data:
                # 更新股票名称
                stock_name = price_data.get('name', pos.get('name', f"股票{code}"))
                
                updated_pos = {
                    'code': code,
                    'name': stock_name,
                    'quantity': pos.get('quantity', 0),
                    'cost_price': pos.get('cost_price', 0),
                    'available': pos.get('available', pos.get('quantity', 0)),
                    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                updated_positions.append(updated_pos)
                logger.info(f"  已更新: {stock_name}")
            else:
                # 保持原样
                updated_positions.append(pos)
                logger.warning(f"  获取失败，保持原样")
        
        # 保存更新后的持仓
        data['positions'] = updated_positions
        data['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open('positions.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info("持仓数据更新完成！")
        
        # 显示更新后的持仓
        print("\n更新后的持仓：")
        print("="*60)
        for pos in updated_positions:
            print(f"{pos['name']}({pos['code']}): {pos['quantity']}股，成本价{pos['cost_price']}")
        print("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"更新持仓失败: {e}")
        return False

if __name__ == "__main__":
    update_positions()
