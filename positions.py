import os
import json
import logging
from datetime import datetime
from collections import defaultdict
from config import Config
from biying_client import BiyingClient

logger = logging.getLogger(__name__)

class PositionManager:
    def __init__(self):
        self.positions_file = Config.POSITIONS_FILE
        self.api = BiyingClient()
        self._load_positions()
    
    def _load_positions(self):
        """加载持仓数据"""
        if os.path.exists(self.positions_file):
            with open(self.positions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.positions = data.get("positions", [])
                self.transaction_history = data.get("transaction_history", [])
        else:
            self.positions = []
            self.transaction_history = []
    
    def _save_positions(self):
        """保存持仓数据"""
        data = {
            "positions": self.positions,
            "transaction_history": self.transaction_history,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(self.positions_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_position(self, stock_code, stock_name, quantity, cost_price, buy_date=None, reason="", target_price=None, stop_loss=None):
        """
        添加新持仓
        
        :param stock_code: 股票代码
        :param stock_name: 股票名称
        :param quantity: 持仓数量
        :param cost_price: 成本价
        :param buy_date: 买入日期（默认当前日期）
        :param reason: 买入理由
        :param target_price: 目标价
        :param stop_loss: 止损价
        """
        if buy_date is None:
            buy_date = datetime.now().strftime("%Y-%m-%d")
        
        # 检查是否已持有该股票
        existing_pos = None
        for pos in self.positions:
            pos_code = pos.get("stock_code") or pos.get("code", "")
            if pos_code == stock_code:
                existing_pos = pos
                break
        
        if existing_pos:
            # 更新现有持仓（加仓）
            total_quantity = existing_pos["quantity"] + quantity
            total_cost = existing_pos["quantity"] * existing_pos["cost_price"] + quantity * cost_price
            new_cost = total_cost / total_quantity
            
            existing_pos["quantity"] = total_quantity
            existing_pos["cost_price"] = round(new_cost, 2)
            if target_price:
                existing_pos["target_price"] = target_price
            if stop_loss:
                existing_pos["stop_loss"] = stop_loss
            if reason:
                existing_pos["reason"] = reason
            
            logger.info(f"已加仓 {stock_name}({stock_code}): +{quantity}股，总成本价: {new_cost:.2f}")
        else:
            # 新建持仓
            position = {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "quantity": quantity,
                "cost_price": cost_price,
                "buy_date": buy_date,
                "reason": reason,
                "target_price": target_price,
                "stop_loss": stop_loss,
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.positions.append(position)
            
            logger.info(f"已添加新持仓: {stock_name}({stock_code}) {quantity}股，成本价: {cost_price}")
        
        # 记录交易历史
        self._record_transaction(stock_code, stock_name, quantity, cost_price, "buy")
        
        self._save_positions()
    
    def sell_position(self, stock_code, quantity, sell_price=None):
        """
        卖出持仓
        
        :param stock_code: 股票代码
        :param quantity: 卖出数量
        :param sell_price: 卖出价格（默认使用最新价）
        :return: 是否成功
        """
        for pos in self.positions:
            pos_code = pos.get("stock_code") or pos.get("code", "")
            if pos_code == stock_code:
                if pos["quantity"] < quantity:
                    logger.error(f"卖出数量 {quantity} 超过持仓数量 {pos['quantity']}")
                    return False
                
                # 如果没有指定卖出价格，尝试从API获取
                if sell_price is None:
                    result = self.api.get_stock_price(stock_code)
                    sell_price = self.api.parse_price_from_result(result)
                
                # 更新持仓
                pos["quantity"] -= quantity
                
                # 如果持仓归零，移除该持仓
                if pos["quantity"] <= 0:
                    self.positions.remove(pos)
                    logger.info(f"已全部卖出 {pos['stock_name']}({stock_code})")
                else:
                    logger.info(f"已卖出 {pos['stock_name']}({stock_code}): -{quantity}股")
                
                # 记录交易历史
                self._record_transaction(stock_code, pos["stock_name"], quantity, sell_price, "sell")
                
                self._save_positions()
                return True
        
        logger.error(f"未找到持仓: {stock_code}")
        return False
    
    def _record_transaction(self, stock_code, stock_name, quantity, price, transaction_type):
        """记录交易历史"""
        transaction = {
            "transaction_id": f"{transaction_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "stock_code": stock_code,
            "stock_name": stock_name,
            "quantity": quantity,
            "price": price,
            "transaction_type": transaction_type,
            "transaction_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.transaction_history.append(transaction)
    
    def get_position_by_code(self, stock_code):
        """根据代码获取持仓"""
        for pos in self.positions:
            pos_code = pos.get("stock_code") or pos.get("code", "")
            if pos_code == stock_code:
                return pos
        return None
    
    def get_all_positions(self):
        """获取所有持仓"""
        return self.positions
    
    def get_portfolio_summary(self):
        """获取持仓组合摘要（包含实时盈亏）"""
        summary = {
            "total_stocks": len(self.positions),
            "total_value": 0,
            "total_cost": 0,
            "total_profit": 0,
            "total_profit_pct": 0,
            "positions": []
        }
        
        for pos in self.positions:
            # 兼容处理字段名：支持 stock_code 或 code
            stock_code = pos.get("stock_code") or pos.get("code", "")
            stock_name = pos.get("stock_name") or pos.get("name", "未知")
            
            # 获取实时价格
            result = self.api.get_stock_price(stock_code)
            if result is None:
                current_price = pos.get("cost_price", 0)
            else:
                current_price = self.api.parse_price_from_result(result)
            
            if current_price is None:
                current_price = pos.get("cost_price", 0)
            
            market_value = pos.get("quantity", 0) * current_price
            cost_value = pos.get("quantity", 0) * pos.get("cost_price", 0)
            profit = market_value - cost_value
            profit_pct = (profit / cost_value) * 100 if cost_value > 0 else 0
            
            summary["total_value"] += market_value
            summary["total_cost"] += cost_value
            summary["total_profit"] += profit
            
            summary["positions"].append({
                "stock_code": stock_code,
                "stock_name": stock_name,
                "quantity": pos.get("quantity", 0),
                "cost_price": pos.get("cost_price", 0),
                "current_price": current_price,
                "market_value": market_value,
                "cost_value": cost_value,
                "profit": profit,
                "profit_pct": profit_pct,
                "target_price": pos.get("target_price"),
                "stop_loss": pos.get("stop_loss")
            })
        
        summary["total_profit_pct"] = (summary["total_profit"] / summary["total_cost"]) * 100 if summary["total_cost"] > 0 else 0
        
        return summary
    
    def get_sector_distribution(self):
        """获取持仓行业分布"""
        sector_map = {
            "半导体": ["半导体", "芯片", "光刻机"],
            "人工智能": ["AI", "人工智能", "大模型"],
            "新能源": ["新能源", "光伏", "锂电", "储能"],
            "消费": ["消费", "白酒", "食品", "家电"],
            "医药": ["医药", "创新药", "医疗"],
            "金融": ["金融", "银行", "券商", "保险"],
            "地产": ["地产", "物业"],
            "军工": ["军工", "国防"],
            "科技": ["科技", "软件", "通信"]
        }
        
        distribution = defaultdict(float)
        total_value = 0
        
        for pos in self.positions:
            pos_code = pos.get("stock_code") or pos.get("code", "")
            pos_name = pos.get("stock_name") or pos.get("name", "")
            pos_quantity = pos.get("quantity", 0)
            pos_cost = pos.get("cost_price", 0)
            
            result = self.api.get_stock_price(pos_code)
            current_price = self.api.parse_price_from_result(result) or pos_cost
            market_value = pos_quantity * current_price
            total_value += market_value
            
            # 根据股票名称判断行业
            matched = False
            for sector, keywords in sector_map.items():
                for keyword in keywords:
                    if keyword in pos_name:
                        distribution[sector] += market_value
                        matched = True
                        break
                if matched:
                    break
            
            if not matched:
                distribution["其他"] += market_value
        
        # 转换为百分比
        if total_value > 0:
            for sector in distribution:
                distribution[sector] = round((distribution[sector] / total_value) * 100, 2)
        
        return dict(sorted(distribution.items(), key=lambda x: x[1], reverse=True))
    
    def check_stop_loss(self):
        """检查止损条件"""
        alerts = []
        
        for pos in self.positions:
            pos_code = pos.get("stock_code") or pos.get("code", "")
            pos_name = pos.get("stock_name") or pos.get("name", "")
            
            result = self.api.get_stock_price(pos_code)
            if result is None:
                continue
            
            current_price = self.api.parse_price_from_result(result)
            
            if current_price is None:
                continue
            
            stop_loss = pos.get("stop_loss")
            if stop_loss and current_price <= stop_loss:
                alerts.append({
                    "stock_code": pos_code,
                    "stock_name": pos_name,
                    "current_price": current_price,
                    "stop_loss_price": stop_loss,
                    "message": f"{pos_name}({pos_code}) 触发止损，当前价 {current_price} <= 止损价 {stop_loss}"
                })
        
        return alerts
    
    def generate_diagnosis(self):
        """生成持仓诊断报告"""
        summary = self.get_portfolio_summary()
        sector_dist = self.get_sector_distribution()
        stop_loss_alerts = self.check_stop_loss()
        
        diagnosis = {
            "summary": summary,
            "sector_distribution": sector_dist,
            "stop_loss_alerts": stop_loss_alerts,
            "recommendations": []
        }
        
        # 生成简单的建议
        if len(summary["positions"]) > 10:
            diagnosis["recommendations"].append("持仓股票数量较多，建议适当精简，集中优质标的")
        
        if summary["total_profit_pct"] < -10:
            diagnosis["recommendations"].append("整体亏损超过10%，建议检查持仓结构，考虑止损或调仓")
        
        # 检查单一行业集中度
        for sector, percentage in sector_dist.items():
            if percentage > 40:
                diagnosis["recommendations"].append(f"{sector}行业持仓占比超过40%，建议分散风险")
        
        return diagnosis

# 示例用法
if __name__ == "__main__":
    pm = PositionManager()
    
    # 添加初始持仓
    pm.add_position("600519", "贵州茅台", 100, 1850.00, reason="长期价值投资")
    pm.add_position("300059", "东方财富", 500, 15.80, reason="看好金融科技")
    
    # 获取持仓摘要
    summary = pm.get_portfolio_summary()
    print("持仓摘要:", json.dumps(summary, indent=2, ensure_ascii=False))
    
    # 获取行业分布
    distribution = pm.get_sector_distribution()
    print("行业分布:", distribution)
    
    # 生成诊断报告
    diagnosis = pm.generate_diagnosis()
    print("持仓诊断:", json.dumps(diagnosis, indent=2, ensure_ascii=False))
