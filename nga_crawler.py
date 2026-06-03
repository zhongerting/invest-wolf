#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NGA帖子爬取客户端

功能：
1. 调用ngapost2md工具爬取指定帖子
2. 按用户ID筛选发言
3. 按半个月时间分割存储
4. 增量更新检测

作者：Trae AI
日期：2026年6月
"""

import os
import subprocess
import logging
import json
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class NGACrawler:
    def __init__(self, ngapost2md_path=None):
        """
        初始化NGA爬取客户端
        
        :param ngapost2md_path: ngapost2md可执行文件路径
        """
        if ngapost2md_path:
            self.ngapost2md_path = ngapost2md_path
        else:
            # 自动查找ngapost2md可执行文件
            self.ngapost2md_path = self._find_ngapost2md()
        
        self.output_base_path = Path('./')
        
        logger.info(f"ngapost2md路径: {self.ngapost2md_path}")
    
    def _find_ngapost2md(self):
        """查找ngapost2md可执行文件"""
        search_paths = [
            './ngapost2md/ngapost2md.exe',
            '../ngapost2md/ngapost2md.exe',
            'ngapost2md.exe'
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                return path
        
        logger.warning("未找到ngapost2md可执行文件")
        return None
    
    def is_available(self):
        """检查ngapost2md是否可用"""
        return self.ngapost2md_path is not None and os.path.exists(self.ngapost2md_path)
    
    def crawl_post(self, tid, uid=None):
        """
        爬取NGA帖子
        
        :param tid: 帖子ID
        :param uid: 用户ID（可选，筛选特定用户发言）
        :return: 爬取结果路径
        """
        if not self.is_available():
            logger.error("ngapost2md不可用")
            return None
        
        try:
            # 构建命令
            cmd = [self.ngapost2md_path, str(tid)]
            
            if uid:
                cmd.extend(['--authorid', str(uid)])
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            
            # 切换到ngapost2md目录执行
            cwd = os.path.dirname(self.ngapost2md_path)
            
            # 执行命令
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info(f"爬取成功: {result.stdout}")
                # 返回生成的文件路径
                output_dir = Path(cwd) / f"{tid}({uid})" if uid else Path(cwd) / str(tid)
                return str(output_dir)
            else:
                logger.error(f"爬取失败: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("爬取超时")
            return None
        except Exception as e:
            logger.error(f"爬取异常: {e}")
            return None
    
    def get_latest_post_time(self, post_dir):
        """
        获取最新帖子的时间
        
        :param post_dir: 帖子目录路径
        :return: 最新时间戳
        """
        post_md = Path(post_dir) / 'post.md'
        if not post_md.exists():
            return None
        
        try:
            with open(post_md, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 查找最新的时间标记
                # NGA帖子格式通常包含时间信息，我们需要解析
                lines = content.split('\n')
                latest_time = None
                
                for line in lines:
                    # 查找时间格式，如 2026-06-02 10:30
                    if '2026-' in line and ':' in line:
                        try:
                            # 提取日期时间
                            date_str = line.split('2026-')[1][:16]
                            dt = datetime.strptime('2026-' + date_str, '%Y-%m-%d %H:%M')
                            if latest_time is None or dt > latest_time:
                                latest_time = dt
                        except:
                            continue
                
                return latest_time
        except Exception as e:
            logger.error(f"解析帖子时间失败: {e}")
            return None
    
    def split_by_half_month(self, source_file, output_base='./'):
        """
        按半个月分割帖子文件
        
        :param source_file: 源帖子文件路径
        :param output_base: 输出目录
        :return: 生成的文件列表
        """
        output_files = []
        
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 按发言分割（简单处理，实际需要更复杂的解析）
            posts = self._parse_posts(content)
            
            # 按时间分组
            groups = self._group_by_half_month(posts)
            
            # 写入文件
            for period, posts_in_period in groups.items():
                filename = f"{period}_nga_master_posts.md"
                filepath = Path(output_base) / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('\n\n'.join(posts_in_period))
                
                output_files.append(str(filepath))
                logger.info(f"生成文件: {filepath}")
            
        except Exception as e:
            logger.error(f"分割文件失败: {e}")
        
        return output_files
    
    def _parse_posts(self, content):
        """解析帖子内容"""
        # 简单按行分割，实际需要更复杂的解析
        lines = content.split('\n')
        posts = []
        current_post = []
        
        for line in lines:
            # 检测新发言开始（通常以日期时间开头）
            if line.startswith('**') or ('2026-' in line and ':' in line):
                if current_post:
                    posts.append('\n'.join(current_post))
                current_post = [line]
            else:
                current_post.append(line)
        
        if current_post:
            posts.append('\n'.join(current_post))
        
        return posts
    
    def _group_by_half_month(self, posts):
        """按半个月分组"""
        groups = {}
        
        for post in posts:
            # 提取日期
            date = self._extract_date(post)
            if date:
                # 确定所属时间段
                period = self._get_half_month_period(date)
                if period not in groups:
                    groups[period] = []
                groups[period].append(post)
        
        return groups
    
    def _extract_date(self, post):
        """从帖子中提取日期"""
        try:
            # 查找日期格式
            if '2026-' in post:
                date_str = post.split('2026-')[1][:10]
                return datetime.strptime('2026-' + date_str, '%Y-%m-%d')
        except:
            pass
        return None
    
    def _get_half_month_period(self, date):
        """获取半个月时间段标识"""
        if date.day <= 15:
            return f"{date.year}{date.month:02d}01-{date.year}{date.month:02d}15"
        else:
            # 获取当月最后一天
            if date.month == 12:
                next_month = datetime(date.year + 1, 1, 1)
            else:
                next_month = datetime(date.year, date.month + 1, 1)
            last_day = (next_month - datetime.timedelta(days=1)).day
            return f"{date.year}{date.month:02d}16-{date.year}{date.month:02d}{last_day:02d}"
    
    def create_daily_backup(self, tid, uid, backup_dir='./'):
        """
        创建当日备份
        
        :param tid: 帖子ID
        :param uid: 用户ID
        :param backup_dir: 备份目录
        :return: 备份文件路径
        """
        today = datetime.now().strftime('%Y%m%d')
        backup_file = Path(backup_dir) / f"{today}_daily_nga_master_posts.md"
        
        # 先爬取最新数据
        post_dir = self.crawl_post(tid, uid)
        if post_dir:
            source_file = Path(post_dir) / 'post.md'
            if source_file.exists():
                # 复制到备份文件
                with open(source_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"创建每日备份: {backup_file}")
                return str(backup_file)
        
        return None


# 示例用法
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 创建爬取客户端
    crawler = NGACrawler()
    
    print(f"ngapost2md可用: {crawler.is_available()}")
    
    if crawler.is_available():
        # 测试爬取
        tid = 45974302
        uid = 150058
        
        print(f"\n开始爬取帖子 {tid} 用户 {uid}...")
        result = crawler.crawl_post(tid, uid)
        
        if result:
            print(f"爬取成功，结果保存在: {result}")
            
            # 获取最新时间
            latest_time = crawler.get_latest_post_time(result)
            if latest_time:
                print(f"最新发言时间: {latest_time}")
        else:
            print("爬取失败")