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
    QMessageBox, QProgressBar, QFrame, QComboBox, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QTime
from PyQt6.QtGui import QColor, QFont, QIntValidator, QDoubleValidator

# 导入自定义模块
from llm_client import LLMClient
from data_source import DataSource
from knowledge_base import KnowledgeBase
from nga_crawler import NGACrawler
from smart_analysis import SmartAnalysisService
from task_scheduler import TaskScheduler
from daily_review import DailyReview
from chat_assistant import ChatAssistant

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
    """持仓数据管理"""
    def __init__(self, positions_file='positions.json'):
        self.positions_file = positions_file
        self.positions = []
        self.total_assets = 0
        self.last_prices = {}  # 保存上次查询的价格
        self.last_price_update = None  # 上次价格更新时间
        self.load_positions()
    
    def load_positions(self):
        """加载持仓数据"""
        try:
            with open(self.positions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.total_assets = data.get('total_assets', 0)
                self.positions = data.get('positions', [])
                self.last_prices = data.get('last_prices', {})
                self.last_price_update = data.get('last_price_update', None)
            logger.info(f"加载持仓数据成功，共 {len(self.positions)} 只股票")
            if self.last_prices:
                logger.info(f"加载上次价格数据，更新时间: {self.last_price_update}")
        except Exception as e:
            logger.error(f"加载持仓数据失败: {e}")
            self.positions = []
            self.total_assets = 0
            self.last_prices = {}
            self.last_price_update = None
    
    def save_positions(self):
        """保存持仓数据"""
        try:
            data = {
                'total_assets': self.total_assets,
                'positions': self.positions,
                'last_prices': self.last_prices,  # 保存上次价格
                'last_price_update': self.last_price_update,  # 保存价格更新时间
                'last_update': datetime.now().strftime('%Y-%m-%d')
            }
            with open(self.positions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("保存持仓数据成功")
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
            pos['position_percent'] = (market_value / self.total_assets * 100) if self.total_assets > 0 else 0
        
        return {
            'total_market_value': total_market_value,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'total_profit_percent': (total_profit / total_cost * 100) if total_cost > 0 else 0
        }
    
    def buy_stock(self, code, quantity, price, stock_name=None):
        """买入股票"""
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
        
        self.save_positions()
    
    def sell_stock(self, code, quantity, price):
        """卖出股票"""
        for pos in self.positions:
            if pos['code'] == code:
                if quantity > pos.get('available', pos['quantity']):
                    logger.error(f"卖出数量 {quantity} 超过可用数量 {pos.get('available', pos['quantity'])}")
                    return False
                
                pos['quantity'] -= quantity
                pos['available'] = pos.get('available', pos['quantity']) - quantity
                
                # 如果持仓归零，移除该持仓
                if pos['quantity'] <= 0:
                    self.positions.remove(pos)
                    logger.info(f"全部卖出 {pos['name']}({code})")
                else:
                    logger.info(f"卖出 {pos['name']}({code}): -{quantity}股")
                
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
        self.label_total_profit = QLabel("总盈亏: ¥0.00 (0.00%)")
        self.label_market_value = QLabel("市值: ¥0.00")
        
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        self.label_total_assets.setFont(font)
        self.label_total_profit.setFont(font)
        
        overview_layout.addWidget(self.label_total_assets, 0, 0)
        overview_layout.addWidget(self.label_total_profit, 0, 1)
        overview_layout.addWidget(self.label_market_value, 1, 0, 1, 2)
        
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
                self.position_data.buy_stock(code, quantity, current_price, stock_name)
                QMessageBox.information(self, "成功", f"买入 {stock_name}({code}) {quantity}股，均价 ¥{current_price:.2f}")
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
        
        # 更新概览
        self.label_total_assets.setText(f"总资产: ¥{self.position_data.total_assets:,.2f}")
        self.label_market_value.setText(f"市值: ¥{profit_data['total_market_value']:,.2f}")
        
        profit = profit_data['total_profit']
        profit_percent = profit_data['total_profit_percent']
        profit_color = "green" if profit >= 0 else "red"
        self.label_total_profit.setText(
            f"总盈亏: <span style='color:{profit_color}'>¥{profit:,.2f} ({profit_percent:+.2f}%)</span>"
        )
        
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
        
        self.setLayout(layout)
    
    def connect_signals(self):
        """连接信号槽"""
        self.btn_start.clicked.connect(self.start_crawl)
        self.btn_stop.clicked.connect(self.stop_crawl)
        self.btn_manual_crawl.clicked.connect(self.manual_crawl)
    
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
        """开始自动爬取（每10分钟一次）"""
        if not self.nga_crawler.is_available():
            QMessageBox.warning(self, "警告", "NGA爬取器不可用，请检查ngapost2md配置")
            return
        
        self.is_running = True
        self.crawl_error = False
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText("状态: 运行中")
        self.posts_text.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始自动爬取（每10分钟）...")
        
        # 更新指示灯
        self.update_indicator()
        
        # 立即执行一次爬取
        self.manual_crawl()
        
        # 启动定时爬取（10分钟 = 600000毫秒）
        self.timer.start(600000)
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
    
    def update_next_crawl_time(self):
        """更新下次爬取时间显示"""
        next_time = QTime.currentTime().addSecs(600)  # 10分钟后
        self.next_crawl_label.setText(f"下次爬取: {next_time.toString('HH:mm:ss')}")
    
    def scheduled_crawl(self):
        """定时爬取（每10分钟）"""
        if self.is_running:
            self.posts_text.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 定时爬取触发...")
            self.manual_crawl()
            self.update_next_crawl_time()
    
    def manual_crawl(self):
        """手动执行一次爬取和分析"""
        if not self.nga_crawler.is_available():
            QMessageBox.warning(self, "警告", "NGA爬取器不可用")
            return
        
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.posts_text.append(f"[{current_time}] 正在爬取狼大最新发言...")
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
            self._display_analysis(analyses)
            
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
    
    def _display_analysis(self, analyses):
        """显示分析结果"""
        analysis_output = []
        
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


def main():
    # 设置环境变量
    os.environ['LLM_API_URL'] = 'https://gcli.ggchan.dev/v1/chat/completions'
    os.environ['LLM_API_KEY'] = 'gg-gcli-KVOOFwFjeKUrkwfZlyjGZUIleVoIPbaSwdoJ1l1WRe4'
    os.environ['LLM_MODEL'] = 'gemini-3.1-pro-preview'
    os.environ['MX_APIKEY'] = 'mkt_y5OEqO1aoagzi_AmfQmbCBzQsRcVDi2GafW6QCsifjs'
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()