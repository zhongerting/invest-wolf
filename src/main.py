#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
狼大投资助手 - 主程序

功能：
1. 持仓管理与分析
2. 自动爬取狼大发言
3. 每日/每周复盘
4. 投资策略建议

作者：Trae AI
日期：2026年6月
"""

import sys
import os
import json
import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QTextEdit, QStatusBar, QSplitter, QGroupBox, QGridLayout,
    QMessageBox, QProgressBar, QFrame, QComboBox, QLineEdit,
    QScrollArea, QFormLayout
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QTime
from PyQt6.QtGui import QColor, QFont, QIntValidator, QDoubleValidator

# 导入自定义模块
from .config import Config
from .llm_client import LLMClient
from .data_source import DataSource
from .knowledge_base import KnowledgeBase
from .nga_crawler import NGACrawler
from .smart_analysis import SmartAnalysisService
from .task_scheduler import TaskScheduler
from .daily_review import DailyReview
from .chat_assistant import ChatAssistant

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('investment_assistant.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PositionData:
    """持仓数据管理 - 使用SQLite数据库存储"""
    def __init__(self):
        from database import DatabaseManager
        self.db = DatabaseManager()
        self.positions = []
        self.total_assets = 0  # 总资产 = 总市值 + 可用资产
        self.available_asset = 0  # 可用资产
        self.last_prices = {}  # 保存上次查询的价格
        self.last_price_update = None  # 上次价格更新时间
        self.load_positions()
    
    def load_positions(self):
        """加载持仓数据（从数据库）"""
        try:
            # 尝试从数据库加载
            db_positions = self.db.get_all_positions()
            
            if db_positions:
                self.positions = db_positions
                logger.info(f"从数据库加载持仓数据成功，共 {len(self.positions)} 只股票")
            else:
                # 如果数据库为空，尝试从JSON文件迁移
                self._migrate_from_json()
                db_positions = self.db.get_all_positions()
                self.positions = db_positions
                logger.info(f"数据迁移完成，共 {len(self.positions)} 只股票")
            
            # 加载可用资产设置
            available_asset_str = self.db.get_setting('available_asset')
            if available_asset_str:
                self.available_asset = float(available_asset_str)
            else:
                # 如果没有设置过可用资产，初始化为总资产（首次使用）
                self.available_asset = 100000.00  # 默认初始资金10万
            
            # 加载总资产设置
            total_assets_str = self.db.get_setting('total_assets')
            if total_assets_str:
                self.total_assets = float(total_assets_str)
            
            # 如果总资产为0但有持仓或可用资产，计算总资产
            if self.total_assets == 0 and (len(self.positions) > 0 or self.available_asset > 0):
                # 计算总市值
                total_market_value = sum(pos['cost_price'] * pos['quantity'] for pos in self.positions)
                self.total_assets = total_market_value + self.available_asset
                logger.info(f"根据持仓计算总资产: ¥{self.total_assets:,.2f} (市值 ¥{total_market_value:,.2f} + 可用 ¥{self.available_asset:,.2f})")
            elif self.total_assets == 0:
                # 完全首次使用
                self.available_asset = 100000.00
                self.total_assets = 100000.00
                logger.info("首次使用，初始化总资产和可用资产为 ¥100,000.00")
            
            # 加载上次价格数据
            last_prices_str = self.db.get_setting('last_prices')
            if last_prices_str:
                self.last_prices = json.loads(last_prices_str)
            
            last_update_str = self.db.get_setting('last_price_update')
            if last_update_str:
                self.last_price_update = last_update_str
            
            if self.last_prices:
                logger.info(f"加载上次价格数据，更新时间: {self.last_price_update}")
                
        except Exception as e:
            logger.error(f"加载持仓数据失败: {e}")
            self.positions = []
            self.total_assets = 0
            self.available_asset = 0
            self.last_prices = {}
            self.last_price_update = None
    
    def _migrate_from_json(self):
        """从JSON文件迁移数据到数据库"""
        logger.info("尝试从JSON文件迁移数据...")
        self.db.migrate_from_json()
    
    def save_positions(self):
        """保存持仓数据（到数据库）"""
        try:
            # 保存每个持仓
            for pos in self.positions:
                self.db.save_position(pos)
            
            # 保存总资产和可用资产
            self.db.set_setting('total_assets', str(self.total_assets))
            self.db.set_setting('available_asset', str(self.available_asset))
            
            # 保存价格数据
            self.db.set_setting('last_prices', json.dumps(self.last_prices))
            self.db.set_setting('last_price_update', self.last_price_update or datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            logger.info("保存持仓数据到数据库成功")
        except Exception as e:
            logger.error(f"保存持仓数据失败: {e}")
    
    def calculate_profit_loss(self, current_prices):
        """计算盈亏"""
        total_market_value = 0
        total_cost = 0
        total_profit = 0
        
        for pos in self.positions:
            code = pos['code']
            cost = pos['cost_price']
            quantity = pos['quantity']
            
            current_price = current_prices.get(code, cost)
            market_value = current_price * quantity
            cost_value = cost * quantity
            profit = market_value - cost_value
            
            total_market_value += market_value
            total_cost += cost_value
            total_profit += profit
            
            pos['current_price'] = current_price
            pos['market_value'] = market_value
            pos['cost_value'] = cost_value
            pos['profit'] = profit
            pos['profit_percent'] = (profit / cost_value * 100) if cost_value > 0 else 0
            
            # 使用当前市值计算仓位百分比
            pos['position_percent'] = (market_value / total_market_value * 100) if total_market_value > 0 else 0
        
        # 动态计算总资产 = 市值 + 可用资产
        # 从数据库获取可用资产
        available_asset_str = self.db.get_setting('available_asset')
        if available_asset_str:
            self.available_asset = float(available_asset_str)
        else:
            self.available_asset = 100000.00  # 默认值
        
        self.total_assets = total_market_value + self.available_asset
        
        # 计算持仓占比（总市值 / 总资产）
        position_ratio = (total_market_value / self.total_assets * 100) if self.total_assets > 0 else 0
        
        return {
            'total_market_value': total_market_value,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'total_profit_percent': (total_profit / total_cost * 100) if total_cost > 0 else 0,
            'available_asset': self.available_asset,
            'position_ratio': position_ratio
        }
    
    def buy_stock(self, code, quantity, price, stock_name=None):
        """买入股票：从可用资产中扣除"""
        # 计算买入金额
        buy_amount = quantity * price
        
        # 获取当前可用资产
        available_asset_str = self.db.get_setting('available_asset')
        if available_asset_str:
            self.available_asset = float(available_asset_str)
        else:
            self.available_asset = 100000.00  # 默认初始资金
        
        # 检查可用资产是否足够
        if self.available_asset < buy_amount:
            logger.error(f"可用资产不足，需要 ¥{buy_amount:.2f}，当前可用 ¥{self.available_asset:.2f}")
            raise ValueError(f"可用资产不足，需要 ¥{buy_amount:.2f}，当前可用 ¥{self.available_asset:.2f}")
        
        # 查找现有持仓
        existing_pos = None
        for pos in self.positions:
            if pos['code'] == code:
                existing_pos = pos
                break
        
        if existing_pos:
            # 加仓
            total_quantity = existing_pos['quantity'] + quantity
            total_cost = existing_pos['quantity'] * existing_pos['cost_price'] + quantity * price
            new_cost = total_cost / total_quantity
            
            existing_pos['quantity'] = total_quantity
            existing_pos['cost_price'] = round(new_cost, 3)  # 改为保留3位小数
            existing_pos['available'] = existing_pos.get('available', existing_pos['quantity']) + quantity
            
            logger.info(f"加仓 {existing_pos['name']}({code}): +{quantity}股，成本价: {new_cost:.3f}")
        else:
            # 新建持仓
            new_pos = {
                'code': code,
                'name': stock_name if stock_name else f"股票{code}",
                'cost_price': price,
                'quantity': quantity,
                'available': quantity,
                'buy_date': datetime.now().strftime('%Y-%m-%d')
            }
            self.positions.append(new_pos)
            logger.info(f"新建持仓 {new_pos['name']}({code}): {quantity}股，成本价: {price:.2f}")
        
        # 更新可用资产（从可用资产中扣除买入金额）
        self.available_asset -= buy_amount
        self.db.set_setting('available_asset', str(self.available_asset))
        logger.info(f"买入后可用资产: ¥{self.available_asset:.2f}")
        
        self.save_positions()
    
    def sell_stock(self, code, quantity, price=None):
        """卖出股票：将卖出金额加入可用资产"""
        for pos in self.positions:
            if pos['code'] == code:
                if quantity > pos.get('available', pos['quantity']):
                    logger.error(f"卖出数量 {quantity} 超过可用数量 {pos.get('available', pos['quantity'])}")
                    return False
                
                # 如果没有指定价格，使用当前价格或成本价
                if price is None:
                    price = pos.get('current_price', pos['cost_price'])
                
                # 计算卖出金额
                sell_amount = quantity * price
                
                # 保存当前成本价（部分卖出时保持不变）
                current_cost_price = pos['cost_price']
                
                # 更新持仓数量
                pos['quantity'] -= quantity
                pos['available'] = pos.get('available', pos['quantity']) - quantity
                
                # 如果持仓归零，移除该持仓
                if pos['quantity'] <= 0:
                    logger.info(f"全部卖出 {pos['name']}({code}): -{quantity}股，价格: {price:.2f}")
                    self.positions.remove(pos)
                else:
                    # 部分卖出时，保持成本价不变
                    logger.info(f"卖出 {pos['name']}({code}): -{quantity}股，价格: {price:.2f}，剩余持仓成本价保持为 {current_cost_price:.3f}")
                
                # 更新可用资产（将卖出金额加入可用资产）
                available_asset_str = self.db.get_setting('available_asset')
                if available_asset_str:
                    self.available_asset = float(available_asset_str)
                else:
                    self.available_asset = 100000.00  # 默认初始资金
                
                self.available_asset += sell_amount
                self.db.set_setting('available_asset', str(self.available_asset))
                logger.info(f"卖出后可用资产: ¥{self.available_asset:.2f}")
                
                self.save_positions()
                return True
        
        logger.error(f"未找到持仓: {code}")
        return False


class PositionPanel(QWidget):
    """持仓分析面板"""
    def __init__(self, position_data, data_source):
        super().__init__()
        self.position_data = position_data
        self.data_source = data_source
        self.current_prices = {}
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_and_refresh)
        self.timer.start(60000)  # 每分钟检查一次
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 总资产概览
        self.overview_group = QGroupBox("持仓概览")
        overview_layout = QGridLayout()
        
        self.label_total_assets = QLabel("总资产: ¥0.00")
        self.label_market_value = QLabel("总市值: ¥0.00")
        self.label_position_ratio = QLabel("持仓占比: 0.00%")
        self.label_available_asset = QLabel("可用资产: ¥0.00")
        
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        self.label_total_assets.setFont(font)
        self.label_market_value.setFont(font)
        
        # 第一行：总资产和持仓占比
        overview_layout.addWidget(self.label_total_assets, 0, 0)
        overview_layout.addWidget(self.label_position_ratio, 0, 1)
        
        # 第二行：总市值和可用资产
        overview_layout.addWidget(self.label_market_value, 1, 0)
        overview_layout.addWidget(self.label_available_asset, 1, 1)
        
        self.overview_group.setLayout(overview_layout)
        layout.addWidget(self.overview_group)
        
        # 持仓操作区域
        operation_group = QGroupBox("持仓操作")
        operation_layout = QHBoxLayout()
        
        # 股票代码输入
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("股票代码（如510210）")
        operation_layout.addWidget(QLabel("股票代码:"))
        operation_layout.addWidget(self.code_edit)
        
        # 买卖类型
        self.operation_type = QComboBox()
        self.operation_type.addItem("买入")
        self.operation_type.addItem("卖出")
        operation_layout.addWidget(QLabel("操作:"))
        operation_layout.addWidget(self.operation_type)
        
        # 数量输入
        self.quantity_edit = QLineEdit()
        self.quantity_edit.setPlaceholderText("股数")
        self.quantity_edit.setValidator(QIntValidator())
        operation_layout.addWidget(QLabel("数量:"))
        operation_layout.addWidget(self.quantity_edit)
        
        # 金额输入
        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("金额(可选)")
        self.amount_edit.setValidator(QDoubleValidator())
        operation_layout.addWidget(QLabel("金额:"))
        operation_layout.addWidget(self.amount_edit)
        
        # 执行按钮
        self.execute_btn = QPushButton("执行操作")
        self.execute_btn.clicked.connect(self.execute_operation)
        operation_layout.addWidget(self.execute_btn)
        
        operation_group.setLayout(operation_layout)
        layout.addWidget(operation_group)
        
        # 持仓表格
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            '代码', '名称', '成本价', '现价', '持仓', '可用',
            '仓位', '盈亏', '盈亏%', '市值', '盈亏状态'
        ])
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        
        # 刷新按钮和状态提示
        control_layout = QHBoxLayout()
        refresh_btn = QPushButton("刷新价格")
        refresh_btn.clicked.connect(self.refresh_prices)
        control_layout.addWidget(refresh_btn)
        
        # 数据来源提示
        if self.position_data.last_price_update:
            self.data_source_label = QLabel(f"<font color='blue'>上次价格更新: {self.position_data.last_price_update}</font>")
        else:
            self.data_source_label = QLabel("<font color='gray'>暂无价格数据，请点击刷新</font>")
        control_layout.addWidget(self.data_source_label)
        
        # 下次刷新时间提示
        self.next_refresh_label = QLabel("")
        control_layout.addWidget(self.next_refresh_label)
        
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        self.setLayout(layout)
        
        # 使用上次的价格数据初始化
        if self.position_data.last_prices:
            self.current_prices = self.position_data.last_prices.copy()
            logger.info("使用上次保存的价格数据")
        else:
            # 如果没有上次的价格数据，使用成本价
            for pos in self.position_data.positions:
                self.current_prices[pos['code']] = pos['cost_price']
        
        self.refresh_data()
        self.update_next_refresh_time()
    
    def check_and_refresh(self):
        """定时检查并刷新"""
        now = QTime.currentTime()
        # 11:30 和 15:00 自动刷新
        if (now.hour() == 11 and now.minute() == 30) or (now.hour() == 15 and now.minute() == 0):
            logger.info(f"定时刷新触发: {now.toString()}")
            self.refresh_prices()
        self.update_next_refresh_time()
    
    def update_next_refresh_time(self):
        """更新下次刷新时间提示"""
        now = QTime.currentTime()
        if now.hour() < 11 or (now.hour() == 11 and now.minute() < 30):
            next_time = QTime(11, 30)
        elif now.hour() < 15 or (now.hour() == 15 and now.minute() < 0):
            next_time = QTime(15, 0)
        else:
            # 今天已过15:00，显示明天的时间
            next_time = QTime(11, 30)
            self.next_refresh_label.setText(f"下次自动刷新: 明天 11:30")
            return
        
        self.next_refresh_label.setText(f"下次自动刷新: {next_time.toString('HH:mm')}")
    
    def execute_operation(self):
        """执行买入/卖出操作"""
        try:
            code = self.code_edit.text().strip()
            if not code:
                QMessageBox.warning(self, "警告", "请输入股票代码")
                return
            
            operation = self.operation_type.currentText()
            quantity = int(self.quantity_edit.text()) if self.quantity_edit.text() else 0
            amount = float(self.amount_edit.text()) if self.amount_edit.text() else 0
            
            if quantity <= 0 and amount <= 0:
                QMessageBox.warning(self, "警告", "请输入数量或金额")
                return
            
            # 获取当前价格
            price_data = self.data_source.get_stock_price(code)
            current_price = price_data.get('price', 0) if price_data else 0
            if current_price <= 0:
                QMessageBox.warning(self, "警告", f"无法获取股票{code}的当前价格")
                return
            
            # 获取股票名称
            stock_name = price_data.get('name', f"股票{code}") if price_data else f"股票{code}"
            
            # 如果只输入了金额，计算数量
            if quantity == 0 and amount > 0:
                quantity = int(amount / current_price / 100) * 100
                if quantity == 0:
                    QMessageBox.warning(self, "警告", "金额不足以购买1手")
                    return
            
            # 执行操作
            if operation == "买入":
                try:
                    self.position_data.buy_stock(code, quantity, current_price, stock_name)
                    QMessageBox.information(self, "成功", f"买入 {stock_name}({code}) {quantity}股，均价 ¥{current_price:.2f}")
                except ValueError as ve:
                    QMessageBox.warning(self, "失败", str(ve))
                    return
            else:
                # 查找持仓
                existing_pos = None
                for pos in self.position_data.positions:
                    if pos['code'] == code:
                        existing_pos = pos
                        break
                if not existing_pos:
                    QMessageBox.warning(self, "警告", f"未找到股票{code}的持仓")
                    return
                if quantity > existing_pos.get('available', existing_pos['quantity']):
                    QMessageBox.warning(self, "警告", f"可用数量不足，当前可用: {existing_pos.get('available', existing_pos['quantity'])}股")
                    return
                self.position_data.sell_stock(code, quantity, current_price)
                QMessageBox.information(self, "成功", f"卖出 {existing_pos['name']}({code}) {quantity}股，均价 ¥{current_price:.2f}")
            
            # 刷新持仓
            self.refresh_prices()
            
            # 清空输入
            self.code_edit.clear()
            self.quantity_edit.clear()
            self.amount_edit.clear()
            
        except Exception as e:
            logger.error(f"执行操作失败: {e}")
            QMessageBox.error(self, "错误", f"操作失败: {str(e)}")
    
    def refresh_prices(self):
        """刷新价格"""
        logger.info("开始刷新价格...")
        
        for pos in self.position_data.positions:
            code = pos['code']
            price_data = self.data_source.get_stock_price(code)
            if price_data:
                self.current_prices[code] = price_data.get('price', pos['cost_price'])
                logger.info(f"{code} 价格: {self.current_prices[code]}")
            else:
                self.current_prices[code] = pos['cost_price']
        
        # 保存价格数据到PositionData
        self.position_data.last_prices = self.current_prices.copy()
        self.position_data.last_price_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.position_data.save_positions()
        
        self.refresh_data()
        logger.info("价格刷新完成，已保存价格数据")
    
    def refresh_data(self):
        """刷新数据显示"""
        # 计算盈亏
        profit_data = self.position_data.calculate_profit_loss(self.current_prices)
        
        # 更新概览 - 显示四个关键指标
        self.label_total_assets.setText(f"总资产: ¥{self.position_data.total_assets:,.2f}")
        self.label_market_value.setText(f"总市值: ¥{profit_data['total_market_value']:,.2f}")
        self.label_position_ratio.setText(f"持仓占比: {profit_data['position_ratio']:.2f}%")
        self.label_available_asset.setText(f"可用资产: ¥{profit_data['available_asset']:,.2f}")
        
        # 更新数据来源标签
        if self.position_data.last_price_update:
            self.data_source_label.setText(f"<font color='blue'>上次价格更新: {self.position_data.last_price_update}</font>")
        
        # 更新表格
        self.table.setRowCount(len(self.position_data.positions))
        
        for row, pos in enumerate(self.position_data.positions):
            self.table.setItem(row, 0, QTableWidgetItem(pos['code']))
            self.table.setItem(row, 1, QTableWidgetItem(pos['name']))
            self.table.setItem(row, 2, QTableWidgetItem(f"{pos['cost_price']:.3f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{pos.get('current_price', pos['cost_price']):.3f}"))
            self.table.setItem(row, 4, QTableWidgetItem(str(pos['quantity'])))
            self.table.setItem(row, 5, QTableWidgetItem(str(pos['available'])))
            self.table.setItem(row, 6, QTableWidgetItem(f"{pos.get('position_percent', 0):.2f}%"))
            
            profit = pos.get('profit', 0)
            profit_percent = pos.get('profit_percent', 0)
            
            profit_item = QTableWidgetItem(f"¥{profit:,.2f}")
            profit_item.setForeground(QColor('green' if profit >= 0 else 'red'))
            self.table.setItem(row, 7, profit_item)
            
            profit_percent_item = QTableWidgetItem(f"{profit_percent:+.2f}%")
            profit_percent_item.setForeground(QColor('green' if profit >= 0 else 'red'))
            self.table.setItem(row, 8, profit_percent_item)
            
            self.table.setItem(row, 9, QTableWidgetItem(f"¥{pos.get('market_value', 0):,.2f}"))
            
            status = "盈利" if profit >= 0 else "亏损"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor('green' if profit >= 0 else 'red'))
            self.table.setItem(row, 10, status_item)


class CrawlPanel(QWidget):
    """爬取面板"""
    def __init__(self, llm_client, nga_crawler, smart_analysis):
        super().__init__()
        self.llm_client = llm_client
        self.nga_crawler = nga_crawler
        self.smart_analysis = smart_analysis
        self.is_running = False
        self.last_crawl_time = None
        self.crawl_error = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.scheduled_crawl)
        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 控制区域
        control_group = QGroupBox("自动爬取控制")
        control_layout = QHBoxLayout()
        
        self.btn_start = QPushButton("开始爬取")
        self.btn_stop = QPushButton("停止爬取")
        self.btn_stop.setEnabled(False)
        self.btn_manual_crawl = QPushButton("手动爬取一次")
        self.btn_today_messages = QPushButton("今日消息")
        
        # 状态指示灯
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(20, 20)
        self.status_indicator.setStyleSheet("border-radius: 10px; background-color: #666666;")  # 默认灰色
        
        self.status_label = QLabel("状态: 未启动")
        self.crawler_status = QLabel(f"NGA爬取器: {'可用' if self.nga_crawler.is_available() else '不可用'}")
        self.last_crawl_label = QLabel("上次爬取: -")
        self.next_crawl_label = QLabel("下次爬取: -")
        
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        control_layout.addWidget(self.btn_manual_crawl)
        control_layout.addWidget(self.btn_today_messages)
        control_layout.addWidget(self.status_indicator)
        control_layout.addWidget(self.status_label)
        control_layout.addWidget(self.crawler_status)
        control_layout.addWidget(self.last_crawl_label)
        control_layout.addWidget(self.next_crawl_label)
        control_layout.addStretch()
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # 分割面板：发言内容和分析结果
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 最新发言显示
        posts_group = QGroupBox("最新发言")
        posts_layout = QVBoxLayout()
        
        self.posts_text = QTextEdit()
        self.posts_text.setReadOnly(True)
        self.posts_text.setPlaceholderText("等待爬取...")
        
        posts_layout.addWidget(self.posts_text)
        posts_group.setLayout(posts_layout)
        splitter.addWidget(posts_group)
        
        # 分析结果显示
        analysis_group = QGroupBox("智能分析")
        analysis_layout = QVBoxLayout()
        
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setPlaceholderText("分析结果将显示在这里...")
        
        analysis_layout.addWidget(self.analysis_text)
        analysis_group.setLayout(analysis_layout)
        splitter.addWidget(analysis_group)
        
        layout.addWidget(splitter)
        
        # 今日消息显示区域
        today_group = QGroupBox("今日消息")
        today_layout = QVBoxLayout()
        
        self.today_messages_text = QTextEdit()
        self.today_messages_text.setReadOnly(True)
        self.today_messages_text.setPlaceholderText("点击'今日消息'按钮查看今天提取的所有发言和智能分析...")
        self.today_messages_text.setMaximumHeight(200)
        
        today_layout.addWidget(self.today_messages_text)
        today_group.setLayout(today_layout)
        layout.addWidget(today_group)
        
        self.setLayout(layout)
    
    def connect_signals(self):
        """连接信号槽"""
        self.btn_start.clicked.connect(self.start_crawl)
        self.btn_stop.clicked.connect(self.stop_crawl)
        self.btn_manual_crawl.clicked.connect(self.manual_crawl)
        self.btn_today_messages.clicked.connect(self.show_today_messages)
    
    def update_indicator(self):
        """更新状态指示灯"""
        if self.crawl_error:
            # 故障 - 红灯
            self.status_indicator.setStyleSheet("border-radius: 10px; background-color: #ff0000;")
        elif self.is_running:
            # 运行中 - 绿灯
            self.status_indicator.setStyleSheet("border-radius: 10px; background-color: #00ff00;")
        else:
            # 未运行 - 灰色
            self.status_indicator.setStyleSheet("border-radius: 10px; background-color: #666666;")
    
    def start_crawl(self):
        """开始自动爬取"""
        if not self.nga_crawler.is_available():
            QMessageBox.warning(self, "警告", "NGA爬取器不可用，请检查ngapost2md配置")
            return
        
        self.is_running = True
        self.crawl_error = False
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText("状态: 运行中")
        self.posts_text.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始自动爬取（每{Config.NGA_MONITOR_INTERVAL_MINUTES}分钟）...")
        
        # 更新指示灯
        self.update_indicator()
        
        # 立即执行一次爬取
        self.manual_crawl()
        
        # 启动定时爬取（使用配置文件中的间隔）
        interval_ms = Config.NGA_MONITOR_INTERVAL_MINUTES * 60 * 1000
        self.timer.start(interval_ms)
        self.update_next_crawl_time()
    
    def stop_crawl(self):
        """停止自动爬取"""
        self.is_running = False
        self.crawl_error = False
        self.timer.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("状态: 已停止")
        self.next_crawl_label.setText("下次爬取: -")
        self.posts_text.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 已停止爬取")
        
        # 更新指示灯
        self.update_indicator()
    
    def show_today_messages(self):
        """显示今日消息（今天提取的所有发言和智能分析）"""
        self.today_messages_text.clear()
        
        try:
            # 获取今天的日期范围
            from datetime import timedelta
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            today_str = today_start.strftime('%Y-%m-%d')
            
            # 从知识库获取今天的完整发言（包含内容）
            today_posts = self.smart_analysis.knowledge_base.get_full_posts_by_date_range(today_start, today_end)
            
            if not today_posts:
                self.today_messages_text.append(f"📅 {today_str}")
                self.today_messages_text.append("")
                self.today_messages_text.append("今日暂无狼大发言记录")
                return
            
            # 显示今日消息
            output = []
            output.append(f"📅 {today_str} - 今日消息汇总")
            output.append("=" * 60)
            output.append("")
            
            # 遍历今天的发言
            for i, post in enumerate(today_posts, 1):
                post_time = post.get('date', '')
                # 处理完整帖子和简化帖子两种情况
                if 'analysis' in post:
                    # 完整帖子结构
                    post_content = post.get('content', '')
                    analysis = post.get('analysis', {})
                    post_summary = analysis.get('summary', '')
                    post_tags = analysis.get('tags', [])
                    post_category = analysis.get('category', '')
                else:
                    # 简化帖子结构
                    post_content = post.get('content', '')
                    post_summary = post.get('summary', '')
                    post_tags = post.get('tags', [])
                    post_category = post.get('category', '')
                
                output.append(f"--- 发言 {i} ---")
                output.append(f"时间: {post_time}")
                if post_category:
                    output.append(f"分类: {post_category}")
                if post_tags:
                    output.append(f"标签: {', '.join(post_tags)}")
                output.append(f"摘要: {post_summary}")
                output.append(f"原文:")
                output.append(post_content)
                output.append("")
            
            output.append("=" * 60)
            output.append(f"总计: {len(today_posts)} 条发言")
            
            self.today_messages_text.append('\n'.join(output))
            
        except Exception as e:
            self.today_messages_text.append(f"获取今日消息失败: {str(e)}")
            logger.error(f"获取今日消息失败: {e}")
    
    def update_next_crawl_time(self):
        """更新下次爬取时间显示"""
        next_time = QTime.currentTime().addSecs(Config.NGA_MONITOR_INTERVAL_MINUTES * 60)
        self.next_crawl_label.setText(f"下次爬取: {next_time.toString('HH:mm:ss')}")
    
    def scheduled_crawl(self):
        """定时爬取"""
        if self.is_running:
            self.posts_text.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 定时爬取触发...")
            self.manual_crawl(is_auto=True)
            self.update_next_crawl_time()
    
    def manual_crawl(self, is_auto=False):
        """手动执行一次爬取和分析
        
        Args:
            is_auto: 是否是自动模式，自动模式下保留分析历史内容
        """
        if not self.nga_crawler.is_available():
            QMessageBox.warning(self, "警告", "NGA爬取器不可用")
            return
        
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.posts_text.append(f"[{current_time}] 正在爬取狼大最新发言...")
            # 只有手动模式才清空分析内容，自动模式保留
            if not is_auto:
                self.analysis_text.clear()
            
            # 第一步：获取新发言（快速）
            self.posts_text.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在获取新发言...")
            new_posts = self.smart_analysis.get_new_posts()
            
            # 更新爬取时间（无论是否有新发言）
            self.last_crawl_time = datetime.now()
            self.last_crawl_label.setText(f"上次爬取: {self.last_crawl_time.strftime('%H:%M:%S')}")
            self.smart_analysis._save_last_crawl_time()
            
            if not new_posts:
                self.posts_text.append("暂无新发言")
                # 只有手动模式才显示暂无新发言的提示，自动模式不显示
                if not is_auto:
                    self.analysis_text.append("暂无新发言需要分析")
                self.crawl_error = False
                self.update_indicator()
                return
            
            # 第二步：立即显示新发言内容
            self.posts_text.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 找到 {len(new_posts)} 条新发言，正在显示...")
            for i, post in enumerate(new_posts):
                self.posts_text.append(f"\n=== 新发言 {i+1} ===")
                self.posts_text.append(f"时间: {post['date'].strftime('%Y-%m-%d %H:%M:%S')}")
                self.posts_text.append(f"内容: {post['content']}")
                self.posts_text.append("-" * 60)
            
            # 第三步：进行智能分析（耗时操作）
            self.posts_text.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在进行智能分析...")
            analyses = self.smart_analysis.analyze_new_posts(new_posts)
            
            # 第四步：显示分析结果
            self.posts_text.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 分析完成")
            self._display_analysis(analyses, is_auto)
            
            # 第五步：保存到知识库和文件
            for post in new_posts:
                self.smart_analysis.knowledge_base.add_post(post['post_num'], post['date'], post['content'])
            self.smart_analysis._write_posts_to_date_files(new_posts)
            
            # 重置错误状态
            self.crawl_error = False
            self.update_indicator()
            
        except Exception as e:
            self.posts_text.append(f"爬取异常: {str(e)}")
            # 设置错误状态
            self.crawl_error = True
            self.update_indicator()
            logger.error(f"爬取异常: {e}")
    
    def _display_analysis(self, analyses, is_auto=False):
        """显示分析结果
        
        Args:
            analyses: 分析结果列表
            is_auto: 是否是自动模式，自动模式下添加时间分隔符
        """
        analysis_output = []
        
        # 自动模式下添加时间分隔符，区分不同时间的分析
        if is_auto:
            separator_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            analysis_output.append(f"\n{'='*60}")
            analysis_output.append(f"📅 自动分析 - {separator_time}")
            analysis_output.append(f"{'='*60}\n")
        
        for i, analysis in enumerate(analyses):
            analysis_output.append(f"=== 发言 {i+1} 分析 ===")
            analysis_output.append(f"时间: {analysis['date']}")
            
            # 标签和分类
            tags = analysis['analysis'].get('tags', [])
            category = analysis['analysis'].get('category', '')
            if tags:
                analysis_output.append(f"标签: {', '.join(tags)}")
            if category:
                analysis_output.append(f"分类: {category}")
            
            # 摘要
            summary = analysis['analysis'].get('summary', '')
            if summary:
                analysis_output.append(f"摘要: {summary}")
            
            # 操作指示
            if analysis['action_indications']:
                analysis_output.append("\n📋 操作指示:")
                for idx, indication in enumerate(analysis['action_indications']):
                    analysis_output.append(f"  {idx+1}. {indication}")
            
            # 风险提示
            if analysis['risk_warnings']:
                analysis_output.append("\n⚠️ 风险提示:")
                for idx, warning in enumerate(analysis['risk_warnings']):
                    analysis_output.append(f"  {idx+1}. {warning}")
            
            # 相关历史发言
            if analysis['related_knowledge']:
                analysis_output.append(f"\n📚 相关历史发言: {len(analysis['related_knowledge'])} 条")
                for idx, related in enumerate(analysis['related_knowledge'][:3]):
                    analysis_output.append(f"  - [{related['date']}] {related['summary'][:50]}...")
            
            analysis_output.append("")
        
        self.analysis_text.append('\n'.join(analysis_output))


class ReviewPanel(QWidget):
    """复盘面板"""
    def __init__(self, llm_client):
        super().__init__()
        self.llm_client = llm_client
        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 控制区域
        control_group = QGroupBox("复盘控制")
        control_layout = QHBoxLayout()
        
        self.btn_daily = QPushButton("生成每日复盘")
        self.btn_weekly = QPushButton("生成每周复盘")
        
        # 定时任务状态
        self.schedule_status = QLabel("定时任务: 每日(交易日23:59) | 每周(周日23:59)")
        self.schedule_status.setStyleSheet("color: green;")
        
        control_layout.addWidget(self.btn_daily)
        control_layout.addWidget(self.btn_weekly)
        control_layout.addWidget(self.schedule_status)
        control_layout.addStretch()
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # 复盘报告显示
        report_group = QGroupBox("复盘报告")
        report_layout = QVBoxLayout()
        
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setPlaceholderText("点击生成复盘报告...")
        
        report_layout.addWidget(self.report_text)
        report_group.setLayout(report_layout)
        layout.addWidget(report_group)
        
        self.setLayout(layout)
    
    def connect_signals(self):
        """连接信号"""
        self.btn_daily.clicked.connect(self.generate_daily_report)
        self.btn_weekly.clicked.connect(self.generate_weekly_report)
    
    def generate_daily_report(self):
        """手动生成每日报告"""
        from daily_review import DailyReview
        self.report_text.clear()
        self.report_text.append("正在生成每日复盘报告...")
        
        try:
            daily_review = DailyReview()
            report = daily_review.generate_review()
            self.display_report(report, "daily")
        except Exception as e:
            self.report_text.append(f"生成失败: {str(e)}")
            logger.error(f"生成每日报告失败: {e}")
    
    def generate_weekly_report(self):
        """手动生成每周报告"""
        from daily_review import DailyReview
        self.report_text.clear()
        self.report_text.append("正在生成每周复盘报告...")
        
        try:
            daily_review = DailyReview()
            report = daily_review.generate_review()
            self.display_report(report, "weekly")
        except Exception as e:
            self.report_text.append(f"生成失败: {str(e)}")
            logger.error(f"生成每周报告失败: {e}")
    
    def display_report(self, report, report_type):
        """显示复盘报告"""
        report_type_text = "每日复盘" if report_type == "daily" else "每周复盘"
        
        output = []
        output.append(f"# {report_type_text}报告")
        output.append(f"")
        output.append(f"## 📅 报告日期")
        output.append(f"{report['report_date']}")
        output.append(f"")
        output.append(f"---")
        
        # 操作复盘评分
        op_review = report["operation_review"]
        output.append(f"")
        output.append(f"## 📝 今日操作复盘评分")
        output.append(f"**综合得分**: {op_review['score']} 分")
        output.append(f"")
        output.append(f"### 评分详情")
        output.append(f"{op_review['score_detail']}")
        output.append(f"")
        output.append(f"### 操作评价")
        output.append(f"{op_review['evaluation']}")
        
        # 狼大发言分析
        output.append(f"")
        output.append(f"---")
        output.append(f"## 🐺 狼大今日发言")
        
        # 狼大当日发言整体分析
        wolf_summary = report.get("wolf_daily_summary", {})
        if wolf_summary and wolf_summary.get("overall_view"):
            output.append(f"### 📌 整体观点")
            output.append(f"{wolf_summary['overall_view']}")
            output.append(f"")
            
            if wolf_summary.get("key_signals"):
                output.append(f"### 📡 关键信号")
                for signal in wolf_summary["key_signals"]:
                    output.append(f"- {signal}")
                output.append(f"")
            
            if wolf_summary.get("investment_theme"):
                output.append(f"### 🎯 投资主线")
                output.append(f"{wolf_summary['investment_theme']}")
                output.append(f"")
            
            if wolf_summary.get("risk_reminder"):
                output.append(f"### ⚠️ 风险提示")
                output.append(f"{wolf_summary['risk_reminder']}")
                output.append(f"")
        
        # 发言详情
        if report["wolf_posts"]:
            output.append(f"### 📝 发言详情")
            for i, post in enumerate(report["wolf_posts"], 1):
                output.append(f"")
                output.append(f"#### {i}. [{post['date']}]")
                output.append(f"**标签**: {', '.join(post['tags']) if post['tags'] else '无'}")
                output.append(f"**摘要**: {post['summary']}")
        else:
            output.append("今日无狼大发言记录")
        
        # 市场响应（持仓技术面分析）
        output.append(f"")
        output.append(f"---")
        output.append(f"## 📊 市场响应")
        diagnosis = report["position_diagnosis"]
        summary = diagnosis["summary"]
        output.append(f"### 持仓概况")
        output.append(f"- 持仓股票数: {summary['total_stocks']}")
        output.append(f"- 持仓总市值: {summary['total_value']:.2f}")
        output.append(f"- 持仓总成本: {summary['total_cost']:.2f}")
        output.append(f"- 总盈亏: {summary['total_profit']:.2f} ({summary['total_profit_pct']:.2f}%)")
        
        # 操作计划
        output.append(f"")
        output.append(f"---")
        output.append(f"## 🎯 明日操作计划" if report_type == "daily" else "## 🎯 下周操作计划")
        
        strategy = report["strategy"]
        for term, plans in strategy.items():
            term_name = {"short_term": "短期（1-3天）", "medium_term": "中期（1-4周）", "long_term": "长期（1-3月）"}
            output.append(f"")
            output.append(f"### {term_name.get(term, term)}")
            for plan in plans:
                output.append(f"**如果 {plan['signal'].replace('狼大提到', '').replace('狼大提示', '').strip()}**")
                output.append(f"  那么 **{plan['action']}**")
                output.append(f"  条件: {plan['conditions']}")
        
        # 风险提示
        if report["risk_summary"]:
            output.append(f"")
            output.append(f"---")
            output.append(f"## ⚠️ 风险提示")
            for risk in report["risk_summary"]:
                output.append(f"- **{risk['message']}**")
                output.append(f"  {risk['action']}")
        
        output.append(f"")
        output.append(f"---")
        output.append(f"*报告生成时间: {report['generated_at']}*")
        
        self.report_text.clear()
        self.report_text.append('\n'.join(output))


class ChatPanel(QWidget):
    """对话面板"""
    # 定义信号，用于通知主窗口刷新持仓
    position_updated = pyqtSignal()
    
    def __init__(self, chat_assistant):
        super().__init__()
        self.chat_assistant = chat_assistant
        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 功能选择
        function_group = QGroupBox("功能选择")
        function_layout = QHBoxLayout()
        
        self.btn_operation = QPushButton("智能持仓管理")
        self.btn_question = QPushButton("疑问解答")
        
        function_layout.addWidget(self.btn_operation)
        function_layout.addWidget(self.btn_question)
        function_layout.addStretch()
        
        function_group.setLayout(function_layout)
        layout.addWidget(function_group)
        
        # 操作输入区域（智能持仓管理）
        self.operation_group = QGroupBox("今日操作记录")
        operation_layout = QVBoxLayout()
        
        self.operation_input = QTextEdit()
        self.operation_input.setPlaceholderText("请输入今天的操作，例如：\n\n今天买入了1000股上证指数ETF(510210)，卖出了500股半导体ETF(515880)...")
        self.operation_input.setMaximumHeight(100)
        
        op_btn_layout = QHBoxLayout()
        self.btn_parse = QPushButton("解析操作")
        self.btn_confirm = QPushButton("确认记录")
        self.btn_confirm.setEnabled(False)
        
        op_btn_layout.addWidget(self.btn_parse)
        op_btn_layout.addWidget(self.btn_confirm)
        op_btn_layout.addStretch()
        
        self.operation_result = QTextEdit()
        self.operation_result.setReadOnly(True)
        self.operation_result.setMaximumHeight(150)
        
        operation_layout.addWidget(self.operation_input)
        operation_layout.addLayout(op_btn_layout)
        operation_layout.addWidget(self.operation_result)
        
        self.operation_group.setLayout(operation_layout)
        layout.addWidget(self.operation_group)
        
        # 对话区域（疑问解答）
        self.chat_group = QGroupBox("疑问解答")
        chat_layout = QVBoxLayout()
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setPlaceholderText("对话历史...")
        
        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("输入您的问题...")
        self.btn_send = QPushButton("发送")
        
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.btn_send)
        
        chat_layout.addWidget(self.chat_history)
        chat_layout.addLayout(input_layout)
        
        self.chat_group.setLayout(chat_layout)
        layout.addWidget(self.chat_group)
        
        # 默认显示操作记录
        self.chat_group.setVisible(False)
        
        self.setLayout(layout)
    
    def connect_signals(self):
        """连接信号"""
        self.btn_operation.clicked.connect(self.show_operation_mode)
        self.btn_question.clicked.connect(self.show_question_mode)
        self.btn_parse.clicked.connect(self.parse_operations)
        self.btn_confirm.clicked.connect(self.confirm_operations)
        self.btn_send.clicked.connect(self.send_question)
        self.chat_input.returnPressed.connect(self.send_question)
    
    def show_operation_mode(self):
        """显示操作记录模式"""
        self.operation_group.setVisible(True)
        self.chat_group.setVisible(False)
        self.btn_operation.setEnabled(False)
        self.btn_question.setEnabled(True)
    
    def show_question_mode(self):
        """显示疑问解答模式"""
        self.operation_group.setVisible(False)
        self.chat_group.setVisible(True)
        self.btn_operation.setEnabled(True)
        self.btn_question.setEnabled(False)
    
    def parse_operations(self):
        """解析操作"""
        user_input = self.operation_input.toPlainText().strip()
        if not user_input:
            QMessageBox.warning(self, "警告", "请输入操作描述")
            return
        
        self.operation_result.clear()
        self.operation_result.append("正在解析操作...")
        
        try:
            result = self.chat_assistant.parse_operations(user_input)
            operations = result.get('operations', [])
            summary = result.get('summary', '')
            
            if operations:
                self.parsed_operations = operations
                self.operation_result.clear()
                self.operation_result.append(f"识别到 {len(operations)} 条操作：\n")
                for i, op in enumerate(operations, 1):
                    self.operation_result.append(f"\n{i}. {op['operation_type']} {op['stock_name']}({op['stock_code']})")
                    self.operation_result.append(f"   数量: {op['quantity']}股")
                    if op.get('amount'):
                        self.operation_result.append(f"   金额: {op['amount']}元")
                
                self.operation_result.append(f"\n总结: {summary}")
                self.btn_confirm.setEnabled(True)
            else:
                self.operation_result.clear()
                self.operation_result.append("未识别到有效操作，请重新描述")
                self.btn_confirm.setEnabled(False)
        except Exception as e:
            self.operation_result.clear()
            self.operation_result.append(f"解析失败: {str(e)}")
            self.btn_confirm.setEnabled(False)
    
    def confirm_operations(self):
        """确认并记录操作"""
        if not hasattr(self, 'parsed_operations'):
            return
        
        try:
            operations_data = {
                'operations': self.parsed_operations,
                'summary': self.operation_result.toPlainText()
            }
            
            success = self.chat_assistant.confirm_and_record_operations(operations_data)
            
            if success:
                QMessageBox.information(self, "成功", f"已成功记录 {len(self.parsed_operations)} 条操作，并更新持仓")
                self.operation_input.clear()
                self.operation_result.clear()
                self.btn_confirm.setEnabled(False)
                del self.parsed_operations
                # 发出信号通知主窗口刷新持仓
                self.position_updated.emit()
            else:
                QMessageBox.warning(self, "失败", "记录操作失败")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"记录操作时出错: {str(e)}")
    
    def send_question(self):
        """发送问题"""
        question = self.chat_input.text().strip()
        if not question:
            return
        
        self.chat_input.clear()
        
        # 显示用户问题
        self.chat_history.append(f"👤 您: {question}")
        
        # 获取回答
        try:
            answer = self.chat_assistant.answer_question(question)
            
            # 检查是否需要查询市场数据
            needs = self.chat_assistant.check_need_market_data(answer)
            
            if needs:
                # 查询市场数据
                self.chat_history.append("🤖 助手: 正在查询市场数据...")
                for need in needs:
                    data_result = self.chat_assistant.query_market_data(need)
                    answer += f"\n\n【查询结果】\n{data_result}"
            
            # 显示回答
            self.chat_history.append(f"🤖 助手: {answer}")
            self.chat_history.append("")
        except Exception as e:
            self.chat_history.append(f"🤖 助手: 抱歉，回答问题时出现错误：{str(e)}")
            self.chat_history.append("")


class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.init_clients()
        self.init_ui()
        self.init_scheduler()
        self.test_connections()
    
    def init_clients(self):
        """初始化客户端"""
        self.llm_client = LLMClient()
        self.data_source = DataSource()
        self.knowledge_base = KnowledgeBase()
        self.position_data = PositionData()
        self.nga_crawler = NGACrawler()  # NGA帖子爬取客户端
        self.smart_analysis = SmartAnalysisService()  # 智能分析服务
        self.daily_review = DailyReview()  # 复盘报告生成器
        self.chat_assistant = ChatAssistant(self.position_data, self.data_source, self.knowledge_base)  # 对话助手（传入持仓数据、行情客户端和知识库）
    
    def init_scheduler(self):
        """初始化定时任务调度器"""
        self.scheduler = TaskScheduler()
        # 连接定时任务信号
        self.scheduler.daily_report_triggered.connect(self.on_daily_report_triggered)
        self.scheduler.weekly_report_triggered.connect(self.on_weekly_report_triggered)
        logger.info("定时任务调度器已初始化")
    
    def on_daily_report_triggered(self):
        """处理每日报告触发"""
        logger.info("执行每日复盘报告")
        try:
            report = self.daily_review.generate_review()
            self.review_panel.display_report(report, "daily")
            self.status_bar.showMessage(f"每日复盘报告已生成 - {report['report_date']}", 5000)
        except Exception as e:
            logger.error(f"生成每日报告失败: {e}")
    
    def on_weekly_report_triggered(self):
        """处理每周报告触发"""
        logger.info("执行每周复盘报告")
        try:
            report = self.daily_review.generate_review()
            self.review_panel.display_report(report, "weekly")
            self.status_bar.showMessage(f"每周复盘报告已生成", 5000)
        except Exception as e:
            logger.error(f"生成每周报告失败: {e}")
    
    def init_ui(self):
        self.setWindowTitle("狼大投资助手 v1.0")
        self.setGeometry(100, 100, 1200, 800)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 标签页
        self.tabs = QTabWidget()
        
        # 持仓面板
        self.position_panel = PositionPanel(self.position_data, self.data_source)
        self.tabs.addTab(self.position_panel, "持仓")
        
        # 爬取面板
        self.crawl_panel = CrawlPanel(self.llm_client, self.nga_crawler, self.smart_analysis)
        self.tabs.addTab(self.crawl_panel, "爬取")
        
        # 复盘面板
        self.review_panel = ReviewPanel(self.llm_client)
        self.tabs.addTab(self.review_panel, "复盘")
        
        # 对话面板
        self.chat_panel = ChatPanel(self.chat_assistant)
        self.tabs.addTab(self.chat_panel, "对话")
        
        # 配置面板
        self.config_panel = ConfigPanel(self.llm_client, self.data_source)
        self.tabs.addTab(self.config_panel, "配置")
        
        # 连接对话面板的持仓更新信号到持仓面板的刷新方法
        self.chat_panel.position_updated.connect(self.position_panel.refresh_data)
        
        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)
    
    def test_connections(self):
        """测试连接"""
        status_messages = []
        
        # 测试LLM
        if self.llm_client.is_configured():
            status_messages.append("🟢 LLM已连接")
        else:
            status_messages.append("🔴 LLM未配置")
        
        # 测试必盈API
        if self.data_source.is_configured():
            status_messages.append("🟢 必盈API已连接")
        else:
            status_messages.append("🔴 必盈API未配置")
        
        # 显示状态
        self.status_bar.showMessage(" | ".join(status_messages))
        
        logger.info("连接测试完成")


class ConfigPanel(QWidget):
    """配置和测试面板"""
    def __init__(self, llm_client, data_source):
        super().__init__()
        self.llm_client = llm_client
        self.data_source = data_source
        self.init_ui()
        self.load_config_from_file()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        
        # 大模型配置
        llm_group = QGroupBox("大模型配置")
        llm_layout = QFormLayout()
        
        # 主API配置
        self.main_api_url = QLineEdit()
        self.main_api_key = QLineEdit()
        self.main_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.main_model = QComboBox()
        self.main_model.setEditable(True)
        
        self.main_show_btn = QPushButton("显示/隐藏")
        self.main_show_btn.clicked.connect(lambda: self.toggle_password(self.main_api_key))
        
        main_btn_layout = QHBoxLayout()
        self.main_test_models_btn = QPushButton("测试模型")
        self.main_test_models_btn.clicked.connect(lambda: self.test_llm_models(0))
        self.main_test_conn_btn = QPushButton("测试连接")
        self.main_test_conn_btn.clicked.connect(lambda: self.test_llm_connection(0))
        main_btn_layout.addWidget(self.main_test_models_btn)
        main_btn_layout.addWidget(self.main_test_conn_btn)
        
        llm_layout.addRow("主API地址:", self.main_api_url)
        llm_layout.addRow("主API Key:", self.create_key_input(self.main_api_key, self.main_show_btn))
        llm_layout.addRow("主模型:", self.main_model)
        llm_layout.addRow("", main_btn_layout)
        
        # 备用API配置
        self.backup_api_url = QLineEdit()
        self.backup_api_key = QLineEdit()
        self.backup_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.backup_model = QComboBox()
        self.backup_model.setEditable(True)
        
        self.backup_show_btn = QPushButton("显示/隐藏")
        self.backup_show_btn.clicked.connect(lambda: self.toggle_password(self.backup_api_key))
        
        backup_btn_layout = QHBoxLayout()
        self.backup_test_models_btn = QPushButton("测试模型")
        self.backup_test_models_btn.clicked.connect(lambda: self.test_llm_models(1))
        self.backup_test_conn_btn = QPushButton("测试连接")
        self.backup_test_conn_btn.clicked.connect(lambda: self.test_llm_connection(1))
        backup_btn_layout.addWidget(self.backup_test_models_btn)
        backup_btn_layout.addWidget(self.backup_test_conn_btn)
        
        llm_layout.addRow("备用API地址:", self.backup_api_url)
        llm_layout.addRow("备用API Key:", self.create_key_input(self.backup_api_key, self.backup_show_btn))
        llm_layout.addRow("备用模型:", self.backup_model)
        llm_layout.addRow("", backup_btn_layout)
        
        # 备用说明
        backup_note = QLabel("说明：当主API模型调用失败时，将自动切换到备用API进行调用")
        backup_note.setStyleSheet("color: #666; font-size: 10pt;")
        llm_layout.addRow("", backup_note)
        
        llm_group.setLayout(llm_layout)
        scroll_layout.addWidget(llm_group)
        
        # 任务特定模型
        task_model_group = QGroupBox("任务特定模型配置")
        task_model_layout = QFormLayout()
        
        task_note = QLabel("说明：每个任务会优先使用对应的模型，如果为空则使用主模型")
        task_note.setStyleSheet("color: #666; font-size: 10pt;")
        task_model_layout.addRow("", task_note)
        
        self.daily_review_model = QComboBox()
        self.daily_review_model.setEditable(True)
        self.post_analysis_model = QComboBox()
        self.post_analysis_model.setEditable(True)
        self.chat_model = QComboBox()
        self.chat_model.setEditable(True)
        self.operation_parse_model = QComboBox()
        self.operation_parse_model.setEditable(True)
        
        task_model_layout.addRow("每日复盘模型:", self.daily_review_model)
        task_model_layout.addRow("狼大发言分析模型:", self.post_analysis_model)
        task_model_layout.addRow("智能对话模型:", self.chat_model)
        task_model_layout.addRow("持仓操作解析模型:", self.operation_parse_model)
        task_model_group.setLayout(task_model_layout)
        scroll_layout.addWidget(task_model_group)
        
        # 必盈API配置
        biying_group = QGroupBox("必盈API配置")
        biying_layout = QFormLayout()
        
        self.biying_base_url = QLineEdit()
        self.biying_licence = QLineEdit()
        self.biying_licence.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.biying_show_btn = QPushButton("显示/隐藏")
        self.biying_show_btn.clicked.connect(lambda: self.toggle_password(self.biying_licence))
        
        biying_btn_layout = QHBoxLayout()
        self.biying_test_btn = QPushButton("测试连接")
        self.biying_test_btn.clicked.connect(self.test_biying_connection)
        biying_btn_layout.addWidget(self.biying_test_btn)
        
        biying_layout.addRow("API地址:", self.biying_base_url)
        biying_layout.addRow("Licence:", self.create_key_input(self.biying_licence, self.biying_show_btn))
        biying_layout.addRow("", biying_btn_layout)
        
        biying_group.setLayout(biying_layout)
        scroll_layout.addWidget(biying_group)
        
        # 东方财富API配置
        eastmoney_group = QGroupBox("东方财富API配置")
        eastmoney_layout = QFormLayout()
        
        self.eastmoney_api_url = QLineEdit()
        self.eastmoney_api_key = QLineEdit()
        self.eastmoney_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.eastmoney_show_btn = QPushButton("显示/隐藏")
        self.eastmoney_show_btn.clicked.connect(lambda: self.toggle_password(self.eastmoney_api_key))
        
        eastmoney_btn_layout = QHBoxLayout()
        self.eastmoney_test_btn = QPushButton("测试连接")
        self.eastmoney_test_btn.clicked.connect(self.test_eastmoney_connection)
        eastmoney_btn_layout.addWidget(self.eastmoney_test_btn)
        
        eastmoney_layout.addRow("API地址:", self.eastmoney_api_url)
        eastmoney_layout.addRow("API Key:", self.create_key_input(self.eastmoney_api_key, self.eastmoney_show_btn))
        eastmoney_layout.addRow("", eastmoney_btn_layout)
        
        eastmoney_group.setLayout(eastmoney_layout)
        scroll_layout.addWidget(eastmoney_group)
        
        # 保存按钮
        save_btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存配置")
        self.save_btn.clicked.connect(self.save_config)
        save_btn_layout.addStretch()
        save_btn_layout.addWidget(self.save_btn)
        
        scroll_layout.addLayout(save_btn_layout)
        
        # 测试结果显示区域
        result_group = QGroupBox("测试结果")
        result_layout = QVBoxLayout()
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(200)
        result_layout.addWidget(self.result_text)
        result_group.setLayout(result_layout)
        scroll_layout.addWidget(result_group)
        
        scroll_layout.addStretch()
        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
    
    def create_key_input(self, key_edit, show_btn):
        """创建带显示按钮的key输入框"""
        container = QWidget()
        container_layout = QHBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(key_edit)
        container_layout.addWidget(show_btn)
        container.setLayout(container_layout)
        return container
    
    def toggle_password(self, line_edit):
        """切换密码显示"""
        if line_edit.echoMode() == QLineEdit.EchoMode.Password:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
    
    def load_config_from_file(self):
        """从配置文件加载配置"""
        # 加载到UI
        self.main_api_url.setText(Config.LLM_API_URL)
        self.main_api_key.setText(Config.LLM_API_KEY)
        self.main_model.addItem(Config.LLM_MODEL)
        self.main_model.setCurrentText(Config.LLM_MODEL)
        
        self.backup_api_url.setText(Config.LLM_API_URL_BACKUP)
        self.backup_api_key.setText(Config.LLM_API_KEY_BACKUP)
        self.backup_model.addItem(Config.LLM_MODEL_BACKUP)
        self.backup_model.setCurrentText(Config.LLM_MODEL_BACKUP)
        
        self.daily_review_model.addItem(Config.LLM_MODEL_DAILY_REVIEW)
        self.daily_review_model.setCurrentText(Config.LLM_MODEL_DAILY_REVIEW)
        self.post_analysis_model.addItem(Config.LLM_MODEL_POST_ANALYSIS)
        self.post_analysis_model.setCurrentText(Config.LLM_MODEL_POST_ANALYSIS)
        
        # 加载新增的任务模型
        if hasattr(Config, 'LLM_MODEL_CHAT') and Config.LLM_MODEL_CHAT:
            self.chat_model.addItem(Config.LLM_MODEL_CHAT)
            self.chat_model.setCurrentText(Config.LLM_MODEL_CHAT)
        else:
            self.chat_model.addItem("")
            self.chat_model.setCurrentText("")
        
        if hasattr(Config, 'LLM_MODEL_OPERATION_PARSE') and Config.LLM_MODEL_OPERATION_PARSE:
            self.operation_parse_model.addItem(Config.LLM_MODEL_OPERATION_PARSE)
            self.operation_parse_model.setCurrentText(Config.LLM_MODEL_OPERATION_PARSE)
        else:
            self.operation_parse_model.addItem("")
            self.operation_parse_model.setCurrentText("")
        
        self.biying_base_url.setText(Config.BIYING_BASE_URL)
        self.biying_licence.setText(Config.BIYING_LICENCE)
        
        self.eastmoney_api_url.setText(Config.MX_API_URL)
        self.eastmoney_api_key.setText(Config.MX_API_KEY)
    
    def save_config(self):
        """保存配置"""
        try:
            # 更新Config类属性
            Config.LLM_API_URL = self.main_api_url.text()
            Config.LLM_API_KEY = self.main_api_key.text()
            Config.LLM_MODEL = self.main_model.currentText()
            
            Config.LLM_API_URL_BACKUP = self.backup_api_url.text()
            Config.LLM_API_KEY_BACKUP = self.backup_api_key.text()
            Config.LLM_MODEL_BACKUP = self.backup_model.currentText()
            
            Config.LLM_MODEL_DAILY_REVIEW = self.daily_review_model.currentText()
            Config.LLM_MODEL_POST_ANALYSIS = self.post_analysis_model.currentText()
            
            # 保存新增的任务模型
            Config.LLM_MODEL_CHAT = self.chat_model.currentText()
            Config.LLM_MODEL_OPERATION_PARSE = self.operation_parse_model.currentText()
            
            Config.BIYING_BASE_URL = self.biying_base_url.text()
            Config.BIYING_LICENCE = self.biying_licence.text()
            
            Config.MX_API_URL = self.eastmoney_api_url.text()
            Config.MX_API_KEY = self.eastmoney_api_key.text()
            
            # 保存到文件
            Config.save_config()
            self.result_text.append("✅ 配置保存成功！")
            QMessageBox.information(self, "成功", "配置保存成功！请重启程序以使配置生效。")
        except Exception as e:
            self.result_text.append(f"❌ 配置保存失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"配置保存失败: {str(e)}")
    
    def test_llm_models(self, api_index):
        """测试获取可用模型列表"""
        self.result_text.append(f"=== 测试获取模型列表 (API {api_index + 1}) ===")
        
        try:
            if api_index == 0:
                api_url = self.main_api_url.text()
                api_key = self.main_api_key.text()
                combo_box = self.main_model
            else:  # api_index == 1 (备用API)
                api_url = self.backup_api_url.text()
                api_key = self.backup_api_key.text()
                combo_box = self.backup_model
            
            # 创建临时LLM客户端测试
            client = LLMClient(api_url=api_url, api_key=api_key)
            models = client.list_available_models()
            
            if models:
                self.result_text.append(f"✅ 成功获取 {len(models)} 个模型:")
                for model in models:
                    self.result_text.append(f"  - {model}")
                
                # 更新下拉框
                current_text = combo_box.currentText()
                combo_box.clear()
                for model in models:
                    combo_box.addItem(model)
                if current_text:
                    index = combo_box.findText(current_text)
                    if index >= 0:
                        combo_box.setCurrentIndex(index)
            else:
                self.result_text.append("⚠️ 未获取到模型列表")
        except Exception as e:
            self.result_text.append(f"❌ 测试失败: {str(e)}")
    
    def test_llm_connection(self, api_index):
        """测试LLM连接"""
        self.result_text.append(f"=== 测试LLM连接 (API {api_index + 1}) ===")
        
        try:
            if api_index == 0:
                api_url = self.main_api_url.text()
                api_key = self.main_api_key.text()
                model = self.main_model.currentText()
            else:  # api_index == 1 (备用API)
                api_url = self.backup_api_url.text()
                api_key = self.backup_api_key.text()
                model = self.backup_model.currentText()
            
            # 创建临时LLM客户端测试
            client = LLMClient(api_url=api_url, api_key=api_key, model=model)
            response, used_backup = client.chat([{"role": "user", "content": "返回一段富有人生哲理的话"}])
            
            self.result_text.append("✅ 连接成功！")
            if used_backup:
                self.result_text.append("⚠️ 注意：使用了备用API进行响应")
            self.result_text.append(f"返回内容: {response}")
        except Exception as e:
            self.result_text.append(f"❌ 连接失败: {str(e)}")
    
    def test_biying_connection(self):
        """测试必盈API连接"""
        self.result_text.append("=== 测试必盈API连接 ===")
        
        try:
            base_url = self.biying_base_url.text()
            licence = self.biying_licence.text()
            
            # 创建临时数据源测试
            from biying_client import BiyingClient
            client = BiyingClient(licence=licence)
            data = client.get_index_data("000001")
            
            if data:
                self.result_text.append("✅ 连接成功！")
                self.result_text.append(f"上证指数信息: 开盘={data.get('open', 'N/A')}, 收盘={data.get('close', 'N/A')}")
            else:
                self.result_text.append("⚠️ 连接成功，但未获取到数据")
        except Exception as e:
            self.result_text.append(f"❌ 连接失败: {str(e)}")
    
    def test_eastmoney_connection(self):
        """测试东方财富API连接"""
        self.result_text.append("=== 测试东方财富API连接 ===")
        
        try:
            api_url = self.eastmoney_api_url.text()
            api_key = self.eastmoney_api_key.text()
            
            # 创建临时数据源测试
            from data_source import DataSource
            ds = DataSource()
            
            # 直接使用东方财富公开接口测试
            from eastmoney_client import EastMoneyClient
            client = EastMoneyClient()
            data = client.get_intraday_data("000001")
            
            if data:
                self.result_text.append("✅ 连接成功！")
                if len(data) > 0:
                    last_data = data[-1]
                    self.result_text.append(f"上证指数分时数据: 最后价格={last_data.get('price', 'N/A')}")
            else:
                self.result_text.append("⚠️ 连接成功，但未获取到数据")
        except Exception as e:
            self.result_text.append(f"❌ 连接失败: {str(e)}")


def main():
    # 加载配置文件
    Config.load_config()
    
    # 设置环境变量（从配置中读取）
    os.environ['LLM_API_URL'] = Config.LLM_API_URL
    os.environ['LLM_API_KEY'] = Config.LLM_API_KEY
    os.environ['LLM_MODEL'] = Config.LLM_MODEL
    os.environ['MX_APIKEY'] = Config.MX_API_KEY
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()