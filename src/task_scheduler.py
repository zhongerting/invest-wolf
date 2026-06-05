#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务调度器 - 处理每日/每周复盘报告
"""

import logging
from datetime import datetime, timedelta
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

logger = logging.getLogger(__name__)


class TaskScheduler(QObject):
    """定时任务调度器"""
    
    daily_report_triggered = pyqtSignal()
    weekly_report_triggered = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_tasks)
        self.timer.start(60000)  # 每分钟检查一次
        
        # 记录上次执行时间，避免重复执行
        self.last_daily_report_date = None
        self.last_weekly_report_date = None
        
        logger.info("定时任务调度器已启动")
    
    def _check_tasks(self):
        """检查是否需要执行定时任务"""
        now = datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()  # 0=周一, 6=周日
        
        # 检查每日复盘任务 (交易日 23:59)
        # 交易日：周一到周五 (0-4)
        if current_weekday <= 4:  # 周一到周五
            if self._is_time_match(current_time, 23, 59):
                if self.last_daily_report_date != now.date():
                    self._execute_daily_report(now)
        
        # 检查每周复盘任务 (每周日 23:59)
        if current_weekday == 6:  # 周日
            if self._is_time_match(current_time, 23, 59):
                if self.last_weekly_report_date != now.date():
                    self._execute_weekly_report(now)
    
    def _is_time_match(self, current_time, target_hour, target_minute):
        """检查当前时间是否匹配目标时间（允许1分钟误差）"""
        return (current_time.hour == target_hour and 
                abs(current_time.minute - target_minute) <= 1)
    
    def _execute_daily_report(self, now):
        """执行每日复盘报告"""
        logger.info(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 触发每日复盘报告任务")
        self.last_daily_report_date = now.date()
        self.daily_report_triggered.emit()
    
    def _execute_weekly_report(self, now):
        """执行每周复盘报告"""
        logger.info(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 触发每周复盘报告任务")
        self.last_weekly_report_date = now.date()
        self.weekly_report_triggered.emit()
    
    def is_trading_day(self, date=None):
        """判断是否为交易日（周一到周五）"""
        if date is None:
            date = datetime.now()
        return date.weekday() <= 4  # 0-4 是周一到周五
    
    def get_next_daily_report_time(self):
        """获取下次每日报告执行时间"""
        now = datetime.now()
        next_time = now.replace(hour=23, minute=59, second=0, microsecond=0)
        
        # 如果今天已经过了23:59，且明天是交易日
        if now > next_time:
            next_day = now + timedelta(days=1)
            # 找到下一个交易日
            while not self.is_trading_day(next_day):
                next_day += timedelta(days=1)
            next_time = next_day.replace(hour=23, minute=59, second=0, microsecond=0)
        
        return next_time
    
    def get_next_weekly_report_time(self):
        """获取下次每周报告执行时间（下周日23:59）"""
        now = datetime.now()
        # 计算下周日
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7  # 如果今天是周日，下周周日
        next_sunday = now + timedelta(days=days_until_sunday)
        return next_sunday.replace(hour=23, minute=59, second=0, microsecond=0)
    
    def get_scheduled_tasks(self):
        """获取所有定时任务的状态"""
        return {
            'daily_report': {
                'next_execution': self.get_next_daily_report_time(),
                'is_enabled': True,
                'description': '每日复盘报告（交易日23:59）'
            },
            'weekly_report': {
                'next_execution': self.get_next_weekly_report_time(),
                'is_enabled': True,
                'description': '每周复盘报告（周日23:59）'
            }
        }
    
    def trigger_daily_report_now(self):
        """立即触发每日报告（用于测试）"""
        now = datetime.now()
        logger.info(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 手动触发每日复盘报告")
        self.last_daily_report_date = now.date()
        self.daily_report_triggered.emit()
    
    def trigger_weekly_report_now(self):
        """立即触发每周报告（用于测试）"""
        now = datetime.now()
        logger.info(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 手动触发每周复盘报告")
        self.last_weekly_report_date = now.date()
        self.weekly_report_triggered.emit()
