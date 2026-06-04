#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能分析服务 - 分析新发言并结合知识库

功能：
1. 增量爬取NGA帖子（只获取新发言）
2. 分析新发言与知识库的关联
3. 生成操作指示和风险提示

作者：Trae AI
日期：2026年6月
"""

import os
import json
import logging
import re
from datetime import datetime, timedelta
from config import Config
from nga_crawler import NGACrawler
from knowledge_base import KnowledgeBase
from llm_client import LLMClient

logger = logging.getLogger(__name__)

class SmartAnalysisService:
    def __init__(self):
        self.nga_crawler = NGACrawler()
        self.knowledge_base = KnowledgeBase()
        self.llm_client = LLMClient(model=Config.LLM_MODEL_POST_ANALYSIS)
        
        # 记录上次爬取时间
        self.last_crawl_time_file = 'last_crawl_time.json'
        self.last_crawl_time = self._load_last_crawl_time()
    
    def _load_last_crawl_time(self):
        """加载上次爬取时间"""
        if os.path.exists(self.last_crawl_time_file):
            try:
                with open(self.last_crawl_time_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return datetime.fromisoformat(data.get('last_crawl_time', '2026-01-01 00:00:00'))
            except:
                pass
        return datetime(2026, 1, 1)
    
    def _save_last_crawl_time(self):
        """保存当前爬取时间"""
        current_time = datetime.now()
        # 更新内存中的时间
        self.last_crawl_time = current_time
        # 保存到文件
        with open(self.last_crawl_time_file, 'w', encoding='utf-8') as f:
            json.dump({
                'last_crawl_time': current_time.isoformat()
            }, f)
    
    def get_new_posts(self, tid=45974302, uid=150058):
        """
        获取新发言（增量爬取）
        
        :param tid: 帖子ID
        :param uid: 用户ID
        :return: 新发言列表
        """
        if not self.nga_crawler.is_available():
            logger.error("NGA爬取器不可用")
            return []
        
        try:
            # 爬取帖子
            result_dir = self.nga_crawler.crawl_post(tid, uid)
            if not result_dir:
                return []
            
            # 读取帖子文件
            post_file = os.path.join(result_dir, 'post.md')
            if not os.path.exists(post_file):
                return []
            
            with open(post_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析新发言
            new_posts = self._parse_new_posts(content)
            logger.info(f"找到 {len(new_posts)} 条新发言")
            
            return new_posts
            
        except Exception as e:
            logger.error(f"获取新发言失败: {e}")
            return []
    
    def _parse_new_posts(self, content):
        """解析帖子内容，提取新发言"""
        posts = []
        lines = content.split('\n')
        current_post = None
        current_content = []
        
        for line in lines:
            # 检测新发言开始（格式：##### <span id="pidXXX">XXX.[XXX] \<pid:XXX\> YYYY-MM-DD HH:MM:SS by ...</span>）
            # 注意：用户名可能显示为乱码（如 -闃跨嫾- 是 -阿狼- 的乱码形式）
            if line.startswith('##### <span id="pid') and '(150058)' in line:
                if current_post:
                    # 检查是否是新发言
                    if self._is_new_post(current_post['date']):
                        current_post['content'] = '\n'.join(current_content).strip()
                        posts.append(current_post)
                
                # 解析新发言头
                try:
                    # 提取日期时间（格式：##### <span id="pidXXX">XXX.[XXX] \<pid:XXX\> YYYY-MM-DD HH:MM:SS by ...</span>）
                    # 直接从整行提取日期和编号
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
                    if date_match:
                        date_str = date_match.group(1)
                        post_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    else:
                        post_date = None
                    
                    # 提取帖子编号（格式：0.[477]）
                    num_match = re.search(r'(\d+)\.\[\d+\]', line)
                    if num_match:
                        post_num = int(num_match.group(1))
                    else:
                        post_num = 0
                    
                    current_post = {
                        'post_num': post_num,
                        'date': post_date,
                        'content': ''
                    }
                    current_content = []
                except:
                    current_post = None
                    current_content = []
            elif current_post:
                # 跳过引用线
                if line.strip() != '----':
                    current_content.append(line)
        
        # 添加最后一条
        if current_post and self._is_new_post(current_post['date']):
            current_post['content'] = '\n'.join(current_content).strip()
            posts.append(current_post)
        
        # 按时间排序（最新的在前）
        posts.sort(key=lambda x: x['date'], reverse=True)
        
        return posts
    
    def _is_new_post(self, post_date):
        """判断是否是新发言（比上次爬取时间晚）"""
        if post_date is None:
            return False
        return post_date > self.last_crawl_time
    
    def analyze_new_posts(self, new_posts):
        """
        分析新发言并结合知识库
        
        :param new_posts: 新发言列表
        :return: 分析结果列表
        """
        results = []
        
        for post in new_posts:
            analysis = self._analyze_single_post(post)
            results.append(analysis)
        
        return results
    
    def _analyze_single_post(self, post):
        """分析单条发言"""
        result = {
            'post_num': post['post_num'],
            'date': post['date'].strftime('%Y-%m-%d %H:%M:%S'),
            'content': post['content'],
            'analysis': {},
            'related_knowledge': [],
            'action_indications': [],
            'risk_warnings': []
        }
        
        # 1. AI分析帖子内容
        if self.llm_client.is_configured():
            ai_result = self.llm_client.analyze_post_content(post['content'], post['date'])
            result['analysis'] = ai_result
        else:
            # 使用知识库的规则分析
            kb_analysis = self.knowledge_base.analyze_post_with_ai(post['content'], post['date'])
            result['analysis'] = kb_analysis
        
        # 2. 查找相关知识库内容
        related = self._find_related_knowledge(post)
        result['related_knowledge'] = related
        
        # 3. 生成操作指示
        action_indications = self._generate_action_indications(post, related)
        result['action_indications'] = action_indications
        
        # 4. 生成风险提示
        risk_warnings = self._generate_risk_warnings(post, related)
        result['risk_warnings'] = risk_warnings
        
        return result
    
    def _find_related_knowledge(self, post):
        """查找相关知识库内容"""
        related = []
        
        # 根据标签查找相关帖子
        content_lower = post['content'].lower()
        sector_names = ["半导体", "人工智能", "新能源", "消费", "医药", "金融", "地产", "军工", "科技", "周期", "券商", "银行"]
        
        # 查找提到的板块
        mentioned_sectors = []
        for sector in sector_names:
            if sector in post['content']:
                mentioned_sectors.append(sector)
        
        # 从知识库查找相关内容
        for post_info in self.knowledge_base.posts_index:
            # 检查标签匹配
            post_tags = post_info.get('tags', [])
            post_sectors = post_info.get('mentioned_sectors', [])
            
            # 如果有共同的板块或标签
            has_common_sector = any(s in mentioned_sectors for s in post_sectors)
            has_common_tag = False
            
            if has_common_sector or has_common_tag:
                related.append({
                    'post_num': post_info['post_num'],
                    'date': post_info['date'],
                    'summary': post_info.get('summary', ''),
                    'tags': post_tags,
                    'mentioned_sectors': post_sectors
                })
        
        # 最多返回5条相关内容
        return related[:5]
    
    def _generate_action_indications(self, post, related_knowledge):
        """生成操作指示"""
        indications = []
        
        content = post['content']
        content_lower = content.lower()
        
        # 基于关键词生成操作指示
        if '买入' in content or '加仓' in content or '布局' in content:
            indications.append("建议关注买入机会")
        
        if '卖出' in content or '减仓' in content or '止盈' in content:
            indications.append("建议关注卖出机会")
        
        if '持有' in content or '观望' in content:
            indications.append("建议保持当前仓位")
        
        if '支撑' in content or '压力' in content:
            indications.append("建议关注关键价位")
        
        if '风险' in content or '谨慎' in content:
            indications.append("建议谨慎操作")
        
        # 如果有相关知识库内容，提示参考
        if related_knowledge:
            indications.append(f"已找到 {len(related_knowledge)} 条相关历史发言，建议参考")
        
        return indications
    
    def _generate_risk_warnings(self, post, related_knowledge):
        """生成风险提示"""
        warnings = []
        
        content = post['content']
        content_lower = content.lower()
        
        # 基于关键词生成风险提示
        if '风险' in content or '警惕' in content or '注意' in content:
            warnings.append("发言中提到风险，请谨慎操作")
        
        if '回调' in content or '下跌' in content or '调整' in content:
            warnings.append("可能存在回调风险")
        
        if '追高' in content or '追涨' in content:
            warnings.append("注意追高风险")
        
        return warnings
    
    def process_new_posts(self, tid=45974302, uid=150058):
        """
        处理新发言的完整流程
        
        :param tid: 帖子ID
        :param uid: 用户ID
        :return: 分析结果
        """
        logger.info("开始处理新发言...")
        logger.info(f"上次爬取时间: {self.last_crawl_time}")
        
        # 获取新发言
        new_posts = self.get_new_posts(tid, uid)
        
        # 无论是否有新发言，都更新爬取时间（关键修复！）
        self._save_last_crawl_time()
        
        if not new_posts:
            logger.info("没有新发言")
            return {
                'success': True,
                'new_post_count': 0,
                'analyses': [],
                'message': '暂无新发言'
            }
        
        # 分析新发言
        analyses = self.analyze_new_posts(new_posts)
        
        # 添加到知识库
        for post in new_posts:
            self.knowledge_base.add_post(post['post_num'], post['date'], post['content'])
        
        # 自动将新发言写入对应的日期范围文件
        self._write_posts_to_date_files(new_posts)
        
        logger.info(f"处理完成，共 {len(new_posts)} 条新发言")
        
        return {
            'success': True,
            'new_post_count': len(new_posts),
            'analyses': analyses,
            'message': f'成功分析 {len(new_posts)} 条新发言'
        }
    
    def _write_posts_to_date_files(self, posts):
        """
        将新发言写入对应的日期范围文件
        文件命名格式：[起始时间]-[终止时间]_nga_master_posts.md
        例如：20260601-20260615_nga_master_posts.md（每月上半月）
              20260616-20260630_nga_master_posts.md（每月下半月）
        """
        for post in posts:
            post_date = post['date']
            file_name = self._get_date_range_file_name(post_date)
            
            # 构建发言内容
            content = self._format_post_content(post)
            
            # 追加写入文件
            self._append_to_file(file_name, content)
        
        logger.info(f"已将 {len(posts)} 条发言写入对应日期范围文件")
    
    def _get_date_range_file_name(self, post_date):
        """获取日期范围文件名"""
        year = post_date.year
        month = post_date.month
        
        # 判断是上半月还是下半月
        if post_date.day <= 15:
            start_date = f"{year}{month:02d}01"
            end_date = f"{year}{month:02d}15"
        else:
            # 获取当月最后一天
            if month == 12:
                next_month_first = datetime(year + 1, 1, 1)
            else:
                next_month_first = datetime(year, month + 1, 1)
            last_day = (next_month_first - timedelta(days=1)).day
            start_date = f"{year}{month:02d}16"
            end_date = f"{year}{month:02d}{last_day}"
        
        return f"{start_date}-{end_date}_nga_master_posts.md"
    
    def _format_post_content(self, post):
        """格式化发言内容为Markdown格式"""
        date_str = post['date'].strftime('%Y-%m-%d %H:%M:%S')
        content = post['content'].strip()
        
        # 处理内容中的特殊字符
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # 构建Markdown格式
        md_content = f"""
## [{date_str}] 发言 #{post['post_num']}

{content}

---
"""
        return md_content
    
    def _append_to_file(self, file_name, content):
        """追加内容到文件"""
        try:
            with open(file_name, 'a', encoding='utf-8') as f:
                f.write(content)
            logger.debug(f"已追加内容到 {file_name}")
        except Exception as e:
            logger.error(f"写入文件失败 {file_name}: {e}")


# 示例用法
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 创建分析服务
    service = SmartAnalysisService()
    
    print("="*60)
    print("智能分析服务测试")
    print("="*60)
    
    print(f"\n上次爬取时间: {service.last_crawl_time}")
    
    # 处理新发言
    result = service.process_new_posts()
    
    print(f"\n结果: {result['message']}")
    print(f"新发言数量: {result['new_post_count']}")
    
    if result['analyses']:
        for i, analysis in enumerate(result['analyses']):
            print(f"\n--- 发言 {i+1} ---")
            print(f"时间: {analysis['date']}")
            print(f"内容预览: {analysis['content'][:100]}...")
            print(f"标签: {analysis['analysis'].get('tags', [])}")
            print(f"分类: {analysis['analysis'].get('category', '')}")
            print(f"操作指示: {analysis['action_indications']}")
            print(f"风险提示: {analysis['risk_warnings']}")
            print(f"相关历史发言: {len(analysis['related_knowledge'])} 条")