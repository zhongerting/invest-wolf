#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理模块 - 使用SQLite存储持仓和操作数据
"""

import os
import sqlite3
import json
import logging
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        # 使用程序运行目录作为数据库位置
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'investment.db')
        # 确保目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建持仓表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS positions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        code TEXT NOT NULL,
                        name TEXT NOT NULL,
                        cost_price REAL NOT NULL,
                        quantity INTEGER NOT NULL,
                        available INTEGER NOT NULL,
                        buy_date TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(code)
                    )
                ''')
                
                # 创建操作记录表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS operations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        stock_code TEXT NOT NULL,
                        stock_name TEXT NOT NULL,
                        operation_type TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        price REAL NOT NULL,
                        amount REAL NOT NULL,
                        record_date TEXT NOT NULL,
                        recorded_at TEXT NOT NULL
                    )
                ''')
                
                # 创建总资产配置表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                ''')
                
                # 创建每日复盘报告表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS daily_reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        report_date TEXT NOT NULL UNIQUE,
                        report_content TEXT NOT NULL,
                        generated_at TEXT NOT NULL
                    )
                ''')
                
                conn.commit()
            logger.info("数据库初始化完成")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
    
    def _get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    # ============ 持仓操作 ============
    
    def save_position(self, position):
        """保存持仓（插入或更新）"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查是否已存在
                cursor.execute('SELECT id FROM positions WHERE code = ?', (position['code'],))
                exists = cursor.fetchone()
                
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                if exists:
                    # 更新现有持仓
                    cursor.execute('''
                        UPDATE positions 
                        SET name=?, cost_price=?, quantity=?, available=?, updated_at=?
                        WHERE code=?
                    ''', (
                        position['name'],
                        position['cost_price'],
                        position['quantity'],
                        position['available'],
                        now,
                        position['code']
                    ))
                else:
                    # 插入新持仓
                    cursor.execute('''
                        INSERT INTO positions 
                        (code, name, cost_price, quantity, available, buy_date, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        position['code'],
                        position['name'],
                        position['cost_price'],
                        position['quantity'],
                        position['available'],
                        position['buy_date'],
                        now,
                        now
                    ))
                
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"保存持仓失败: {e}")
            return False
    
    def get_all_positions(self):
        """获取所有持仓"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM positions ORDER BY code')
                
                positions = []
                for row in cursor.fetchall():
                    positions.append({
                        'id': row[0],
                        'code': row[1],
                        'name': row[2],
                        'cost_price': row[3],
                        'quantity': row[4],
                        'available': row[5],
                        'buy_date': row[6],
                        'created_at': row[7],
                        'updated_at': row[8]
                    })
                
            return positions
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return []
    
    def get_position_by_code(self, code):
        """根据代码获取持仓"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM positions WHERE code = ?', (code,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'code': row[1],
                        'name': row[2],
                        'cost_price': row[3],
                        'quantity': row[4],
                        'available': row[5],
                        'buy_date': row[6],
                        'created_at': row[7],
                        'updated_at': row[8]
                    }
                return None
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return None
    
    def delete_position(self, code):
        """删除持仓"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM positions WHERE code = ?', (code,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"删除持仓失败: {e}")
            return False
    
    # ============ 操作记录 ============
    
    def add_operation(self, operation):
        """添加操作记录"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO operations 
                    (stock_code, stock_name, operation_type, quantity, price, amount, record_date, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    operation['stock_code'],
                    operation['stock_name'],
                    operation['operation_type'],
                    operation['quantity'],
                    operation['price'],
                    operation['amount'],
                    operation['record_date'],
                    operation['recorded_at']
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"添加操作记录失败: {e}")
            return False
    
    def get_operations_by_date(self, date):
        """获取指定日期的操作记录"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM operations WHERE record_date = ? ORDER BY recorded_at', (date,))
                
                operations = []
                for row in cursor.fetchall():
                    operations.append({
                        'id': row[0],
                        'stock_code': row[1],
                        'stock_name': row[2],
                        'operation_type': row[3],
                        'quantity': row[4],
                        'price': row[5],
                        'amount': row[6],
                        'record_date': row[7],
                        'recorded_at': row[8]
                    })
                
            return operations
        except Exception as e:
            logger.error(f"获取操作记录失败: {e}")
            return []
    
    def get_all_operations(self):
        """获取所有操作记录"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM operations ORDER BY record_date DESC, recorded_at DESC')
                
                operations = []
                for row in cursor.fetchall():
                    operations.append({
                        'id': row[0],
                        'stock_code': row[1],
                        'stock_name': row[2],
                        'operation_type': row[3],
                        'quantity': row[4],
                        'price': row[5],
                        'amount': row[6],
                        'record_date': row[7],
                        'recorded_at': row[8]
                    })
                
            return operations
        except Exception as e:
            logger.error(f"获取操作记录失败: {e}")
            return []
    
    # ============ 设置操作 ============
    
    def get_setting(self, key):
        """获取设置值"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
                row = cursor.fetchone()
                if row:
                    return row[0]
                return None
        except Exception as e:
            logger.error(f"获取设置失败: {e}")
            return None
    
    def set_setting(self, key, value):
        """设置配置值"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 检查是否已存在
                cursor.execute('SELECT key FROM settings WHERE key = ?', (key,))
                exists = cursor.fetchone()
                
                if exists:
                    cursor.execute('UPDATE settings SET value=?, updated_at=? WHERE key=?', (value, now, key))
                else:
                    cursor.execute('INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)', (key, value, now))
                
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"设置配置失败: {e}")
            return False
    
    # ============ 复盘报告 ============
    
    def save_daily_report(self, report_date, report_content):
        """保存每日复盘报告"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_reports 
                    (report_date, report_content, generated_at)
                    VALUES (?, ?, ?)
                ''', (report_date, report_content, now))
                
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"保存复盘报告失败: {e}")
            return False
    
    def get_daily_report(self, report_date):
        """获取指定日期的复盘报告"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT report_content, generated_at FROM daily_reports WHERE report_date = ?', (report_date,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'report_content': row[0],
                        'generated_at': row[1]
                    }
                return None
        except Exception as e:
            logger.error(f"获取复盘报告失败: {e}")
            return None
    
    # ============ 数据迁移 ============
    
    def migrate_from_json(self, positions_file='positions.json', operations_file='daily_operations.json'):
        """从JSON文件迁移数据到数据库"""
        logger.info("开始从JSON文件迁移数据...")
        
        # 迁移持仓数据
        if os.path.exists(positions_file):
            try:
                with open(positions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    positions = data.get('positions', [])
                    
                    for pos in positions:
                        position = {
                            'code': pos['code'],
                            'name': pos.get('name', f"股票{pos['code']}"),
                            'cost_price': pos['cost_price'],
                            'quantity': pos['quantity'],
                            'available': pos.get('available', pos['quantity']),
                            'buy_date': pos.get('buy_date', datetime.now().strftime('%Y-%m-%d'))
                        }
                        self.save_position(position)
                    
                    logger.info(f"已迁移 {len(positions)} 条持仓数据")
            except Exception as e:
                logger.error(f"迁移持仓数据失败: {e}")
        
        # 迁移操作记录
        if os.path.exists(operations_file):
            try:
                with open(operations_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    for date, ops in data.items():
                        for op in ops:
                            operation = {
                                'stock_code': op['stock_code'],
                                'stock_name': op.get('stock_name', f"股票{op['stock_code']}"),
                                'operation_type': op['operation_type'],
                                'quantity': op['quantity'],
                                'price': op.get('amount', 0) / op['quantity'] if op['quantity'] > 0 else 0,
                                'amount': op.get('amount', 0),
                                'record_date': date,
                                'recorded_at': op.get('recorded_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                            }
                            self.add_operation(operation)
                    
                    logger.info(f"已迁移操作记录")
            except Exception as e:
                logger.error(f"迁移操作记录失败: {e}")
        
        logger.info("数据迁移完成")
