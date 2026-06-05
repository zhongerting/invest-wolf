#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库构建脚本

功能：
1. 从压缩精选目录读取所有MD文件
2. 解析发言内容
3. 使用LLM为每条发言打标签
4. 生成结构化的JSON知识库

作者：Trae AI
日期：2026年6月
"""

import os
import re
import json
import logging
from datetime import datetime
from .llm_client import LLMClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('knowledge_base_build.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class KnowledgeBaseBuilder:
    def __init__(self):
        self.llm_client = LLMClient()
        self.source_dir = r"e:\杂项\NGA狼\压缩精选"
        self.output_file = r"e:\杂项\NGA狼\knowledge_base.json"
        self.posts = []
        self.tags_index = {}
        self.post_num = 0
    
    def read_file_with_encoding(self, file_path):
        """尝试多种编码读取文件"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    # 验证是否为有效文本（不含大量乱码）
                    if not self.has_many_invalid_chars(content):
                        return content, encoding
            except (UnicodeDecodeError, LookupError):
                continue
        
        # 如果都失败，尝试二进制读取
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                # 尝试多种编码解码
                for encoding in encodings:
                    try:
                        decoded = content.decode(encoding)
                        if not self.has_many_invalid_chars(decoded):
                            return decoded, encoding
                    except UnicodeDecodeError:
                        continue
        except Exception as e:
            logger.error(f"读取文件 {file_path} 失败: {e}")
        
        return None, None
    
    def has_many_invalid_chars(self, text):
        """检测文本是否包含大量无效字符"""
        invalid_pattern = r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\xFF]'
        matches = re.findall(invalid_pattern, text)
        # 如果无效字符超过10个，认为是编码错误
        return len(matches) > 10
    
    def parse_md_file(self, file_path):
        """解析单个MD文件，提取发言内容"""
        try:
            content, encoding = self.read_file_with_encoding(file_path)
            if content is None:
                logger.error(f"无法读取文件: {file_path}")
                return None
            
            logger.debug(f"文件 {file_path} 使用编码: {encoding}")
            
            # 从文件名提取时间范围
            filename = os.path.basename(file_path)
            match = re.match(r'(\d{8})-(\d{8})', filename)
            if match:
                start_date = match.group(1)
                end_date = match.group(2)
            else:
                start_date = end_date = "20260101"
            
            # 提取日期和内容
            extracted_content = []
            
            # 匹配引用格式 > 内容
            quote_pattern = r'>\s*([^\n]+)'
            matches = re.findall(quote_pattern, content)
            for match in matches:
                text = match.strip()
                if text and len(text) > 10:
                    extracted_content.append(text)
            
            # 匹配标题下的段落
            section_pattern = r'##?\s*[^#\n]+\n\n([\s\S]*?)(?=\n\n##|\n\n###|\Z)'
            section_matches = re.findall(section_pattern, content)
            for match in section_matches:
                paragraphs = re.split(r'\n\n', match.strip())
                for para in paragraphs:
                    para = para.strip()
                    # 跳过列表项和短内容
                    if para and len(para) > 20 and not para.startswith(('-', '*', '1.', '2.', '3.')):
                        # 去除多余空格
                        para = re.sub(r'\s+', ' ', para)
                        extracted_content.append(para)
            
            # 提取带日期的内容
            date_pattern = r'(\d{1,2}月\d{1,2}日)\s*[：:]?\s*([^\n]+)'
            date_matches = re.findall(date_pattern, content)
            for date_str, text in date_matches:
                text = text.strip()
                if text and len(text) > 10:
                    extracted_content.append(f"{date_str}：{text}")
            
            return {
                'file': filename,
                'start_date': start_date,
                'end_date': end_date,
                'content': extracted_content
            }
            
        except Exception as e:
            logger.error(f"解析文件 {file_path} 失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def process_all_files(self):
        """处理所有MD文件"""
        logger.info("开始处理所有MD文件...")
        
        md_files = [f for f in os.listdir(self.source_dir) if f.endswith('.md')]
        md_files.sort()
        
        for md_file in md_files:
            file_path = os.path.join(self.source_dir, md_file)
            logger.info(f"处理文件: {md_file}")
            
            parsed = self.parse_md_file(file_path)
            if parsed:
                # 为每条内容创建一条记录
                for content in parsed['content']:
                    self.post_num += 1
                    
                    # 使用LLM分析
                    analysis = self.analyze_with_llm(content, parsed['start_date'])
                    
                    post = {
                        'post_num': self.post_num,
                        'file_source': parsed['file'],
                        'date_range': f"{parsed['start_date']} - {parsed['end_date']}",
                        'content': content,
                        **analysis
                    }
                    
                    self.posts.append(post)
                    logger.info(f"已处理第 {self.post_num} 条发言，类别: {analysis.get('category', 'unknown')}")
        
        logger.info(f"处理完成，共解析 {self.post_num} 条发言")
    
    def analyze_with_llm(self, content, date_str):
        """使用LLM分析发言内容"""
        if not self.llm_client.is_configured():
            logger.debug("LLM未配置，使用规则分析")
            return self.rule_based_analysis(content)
        
        try:
            result = self.llm_client.analyze_post_content(content, date_str)
            return result
        except Exception as e:
            logger.error(f"LLM分析失败，回退到规则分析: {e}")
            return self.rule_based_analysis(content)
    
    def rule_based_analysis(self, content):
        """基于规则的分析（作为LLM的回退）"""
        tags = []
        mentioned_sectors = []
        content_lower = content.lower()
        
        # 标签关键词映射
        keywords_map = {
            "market": ["市场", "大盘", "指数", "走势", "行情", "阶段", "主升", "调整", "趋势"],
            "technical": ["均线", "macd", "kdj", "支撑", "压力", "量能", "K线", "日线", "周线", "金叉", "死叉"],
            "sector": ["半导体", "新能源", "消费", "医药", "AI", "航天", "卫星", "电池", "券商", "军工"],
            "stock": ["股票", "个股", "买入", "卖出", "持仓", "仓位", "减仓", "加仓"],
            "sentiment": ["看好", "看空", "风险", "机会", "谨慎", "乐观", "悲观"],
            "strategy": ["策略", "操作", "建议", "满仓", "轻仓", "观望", "布局"]
        }
        
        # 板块关键词
        sector_keywords = ["半导体", "新能源", "消费", "医药", "AI", "人工智能", "航天", "卫星", 
                          "电池", "券商", "军工", "科技", "金融", "周期", "光伏", "锂电"]
        
        # 情绪关键词
        bullish_words = ["看好", "上涨", "机会", "加仓", "买入", "主升", "加速", "突破", "走强"]
        bearish_words = ["看空", "下跌", "风险", "减仓", "卖出", "调整", "谨慎", "回落", "破位"]
        
        # 分析标签
        for tag_type, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in content_lower:
                    tags.append(tag_type)
                    break
        
        # 分析板块
        for sector in sector_keywords:
            if sector in content_lower:
                mentioned_sectors.append(sector)
        
        # 分析情绪
        sentiment = "neutral"
        bull_count = sum(1 for w in bullish_words if w in content_lower)
        bear_count = sum(1 for w in bearish_words if w in content_lower)
        if bull_count > bear_count:
            sentiment = "bullish"
        elif bear_count > bull_count:
            sentiment = "bearish"
        
        # 确定类别
        if "technical" in tags:
            category = "technical_analysis"
        elif "market" in tags:
            category = "market_analysis"
        elif "strategy" in tags or "stock" in tags:
            category = "trading_signal"
        elif "sector" in tags:
            category = "market_analysis"
        else:
            category = "other"
        
        return {
            "tags": list(set(tags)),
            "category": category,
            "summary": content[:100] + "..." if len(content) > 100 else content,
            "mentioned_sectors": mentioned_sectors,
            "sentiment": sentiment,
            "confidence": "low",
            "key_points": [],
            "analysis_method": "rule_based"
        }
    
    def build_tags_index(self):
        """构建标签索引"""
        logger.info("构建标签索引...")
        
        for post in self.posts:
            tags = post.get('tags', [])
            post_num = post['post_num']
            
            for tag in tags:
                if tag not in self.tags_index:
                    self.tags_index[tag] = []
                self.tags_index[tag].append(post_num)
        
        logger.info(f"标签索引构建完成，共 {len(self.tags_index)} 个标签")
    
    def save_knowledge_base(self):
        """保存知识库到JSON文件"""
        logger.info("保存知识库...")
        
        knowledge_base = {
            "posts": self.posts,
            "tags_index": self.tags_index,
            "metadata": {
                "total_posts": len(self.posts),
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0",
                "source_files": [f for f in os.listdir(self.source_dir) if f.endswith('.md')]
            }
        }
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(knowledge_base, f, ensure_ascii=False, indent=2)
        
        logger.info(f"知识库已保存到: {self.output_file}")
    
    def run(self):
        """执行完整构建流程"""
        logger.info("=" * 60)
        logger.info("开始构建知识库...")
        logger.info("=" * 60)
        
        # 1. 处理所有文件
        self.process_all_files()
        
        # 2. 构建标签索引
        self.build_tags_index()
        
        # 3. 保存知识库
        self.save_knowledge_base()
        
        # 4. 输出统计信息
        self.print_stats()
        
        logger.info("=" * 60)
        logger.info("知识库构建完成！")
        logger.info("=" * 60)
    
    def print_stats(self):
        """打印统计信息"""
        logger.info("\n--- 知识库统计 ---")
        logger.info(f"总发言数: {len(self.posts)}")
        logger.info(f"标签数量: {len(self.tags_index)}")
        
        # 按类别统计
        category_counts = {}
        sentiment_counts = {}
        
        for post in self.posts:
            category = post.get('category', 'other')
            sentiment = post.get('sentiment', 'neutral')
            
            category_counts[category] = category_counts.get(category, 0) + 1
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        
        logger.info("\n类别分布:")
        for cat, count in category_counts.items():
            logger.info(f"  {cat}: {count}")
        
        logger.info("\n情绪分布:")
        for sent, count in sentiment_counts.items():
            logger.info(f"  {sent}: {count}")
        
        logger.info("\n标签分布:")
        for tag, posts in self.tags_index.items():
            logger.info(f"  {tag}: {len(posts)} 条")


if __name__ == "__main__":
    # 设置环境变量（测试用）
    import os
    os.environ['LLM_API_URL'] = 'https://gcli.ggchan.dev/v1/chat/completions'
    os.environ['LLM_API_KEY'] = 'gg-gcli-KVOOFwFjeKUrkwfZlyjGZUIleVoIPbaSwdoJ1l1WRe4'
    os.environ['LLM_MODEL'] = 'gemini-3.1-pro-preview'
    
    builder = KnowledgeBaseBuilder()
    builder.run()
    
    print(f"\n知识库构建完成！")
    print(f"总发言数: {len(builder.posts)}")
    print(f"输出文件: {builder.output_file}")