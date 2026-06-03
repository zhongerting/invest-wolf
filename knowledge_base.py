import os
import json
import re
import logging
from datetime import datetime
from collections import defaultdict
from config import Config
from llm_client import LLMClient

logger = logging.getLogger(__name__)

class KnowledgeBase:
    def __init__(self):
        Config.ensure_directories()
        self.base_dir = Config.KNOWLEDGE_BASE_DIR
        self.posts_index_file = os.path.join(self.base_dir, "posts_index.json")
        self.tags_index_file = os.path.join(self.base_dir, "tags_index.json")
        self.posts_dir = os.path.join(self.base_dir, "posts")
        
        self.llm = LLMClient()
        
        os.makedirs(self.posts_dir, exist_ok=True)
        self._load_indices()
    
    def _load_indices(self):
        """加载索引文件"""
        if os.path.exists(self.posts_index_file):
            with open(self.posts_index_file, 'r', encoding='utf-8') as f:
                self.posts_index = json.load(f)
        else:
            self.posts_index = []
        
        if os.path.exists(self.tags_index_file):
            with open(self.tags_index_file, 'r', encoding='utf-8') as f:
                self.tags_index = json.load(f)
        else:
            self.tags_index = defaultdict(list)
    
    def _save_indices(self):
        """保存索引文件"""
        with open(self.posts_index_file, 'w', encoding='utf-8') as f:
            json.dump(self.posts_index, f, ensure_ascii=False, indent=2)
        
        with open(self.tags_index_file, 'w', encoding='utf-8') as f:
            json.dump(dict(self.tags_index), f, ensure_ascii=False, indent=2)
    
    def analyze_post_with_ai(self, post_content, post_date):
        """
        使用 AI 分析帖子内容，提取标签
        
        :param post_content: 帖子内容
        :param post_date: 帖子日期
        :return: 分析结果（包含标签、分类、摘要等）
        """
        # 优先使用 LLM 分析
        if self.llm.is_configured():
            logger.info("使用 LLM 分析帖子内容")
            
            # 清理引用内容，只分析狼大原创内容
            cleaned_content = self._clean_quoted_content(post_content)
            
            # 分段分析，防止上下文过长
            llm_result = self._analyze_with_segments(cleaned_content, post_date)
            
            # 提取提到的板块
            sector_names = ["半导体", "人工智能", "新能源", "消费", "医药", "金融", "地产", "军工", "科技", "周期", "券商", "银行"]
            mentioned_sectors = []
            for sector in sector_names:
                if sector in cleaned_content:
                    mentioned_sectors.append(sector)
            
            # 生成摘要（优先使用LLM结果，否则使用清理后的内容）
            if llm_result.get("summary"):
                summary = llm_result["summary"]
            else:
                content_lines = cleaned_content.strip().split('\n')
                if content_lines:
                    summary_text = '\n'.join(content_lines[:3])
                    summary = summary_text[:150] + "..." if len(summary_text) > 150 else summary_text
                else:
                    summary = ""
            
            return {
                "tags": llm_result.get("tags", []),
                "category": llm_result.get("category", "other"),
                "summary": summary,
                "mentioned_sectors": mentioned_sectors,
                "sentiment": llm_result.get("sentiment", "neutral"),
                "confidence": llm_result.get("confidence", "medium"),
                "key_points": llm_result.get("key_points", []),
                "analysis_method": "llm"
            }
        else:
            logger.info("LLM 未配置，使用规则分析帖子内容")
            cleaned_content = self._clean_quoted_content(post_content)
            return self._fallback_analysis(cleaned_content)
    
    def _analyze_with_segments(self, content, post_date):
        """
        分段分析帖子内容，防止上下文过长
        
        :param content: 清理后的帖子内容
        :param post_date: 帖子日期
        :return: 分析结果
        """
        # 每段最大字符数（控制上下文长度）
        MAX_SEGMENT_LENGTH = 2000
        
        # 如果内容较短，直接分析
        if len(content) <= MAX_SEGMENT_LENGTH:
            return self.llm.analyze_post_content(content, post_date)
        
        # 分段处理
        segments = []
        lines = content.split('\n')
        current_segment = []
        current_length = 0
        
        for line in lines:
            line_length = len(line)
            
            # 如果单行过长，也需要分割
            if line_length > MAX_SEGMENT_LENGTH:
                # 先保存当前段
                if current_segment:
                    segments.append('\n'.join(current_segment))
                    current_segment = []
                    current_length = 0
                
                # 分割长行
                for i in range(0, line_length, MAX_SEGMENT_LENGTH):
                    segments.append(line[i:i+MAX_SEGMENT_LENGTH])
            else:
                # 检查是否超过段长度限制
                if current_length + line_length > MAX_SEGMENT_LENGTH:
                    segments.append('\n'.join(current_segment))
                    current_segment = []
                    current_length = 0
                
                current_segment.append(line)
                current_length += line_length + 1  # +1 for newline
        
        # 保存最后一段
        if current_segment:
            segments.append('\n'.join(current_segment))
        
        logger.info(f"内容过长（{len(content)}字符），分为 {len(segments)} 段进行分析")
        
        # 串行分析每一段（不并发）
        all_results = []
        for i, segment in enumerate(segments, 1):
            logger.info(f"分析第 {i}/{len(segments)} 段...")
            result = self.llm.analyze_post_content(segment, post_date)
            if result:
                all_results.append(result)
        
        # 合并结果
        if not all_results:
            return self._fallback_analysis(content)
        
        # 合并标签（去重）
        merged_tags = []
        for result in all_results:
            tags = result.get("tags", [])
            for tag in tags:
                if tag not in merged_tags:
                    merged_tags.append(tag)
        
        # 合并关键点
        merged_key_points = []
        for result in all_results:
            key_points = result.get("key_points", [])
            for point in key_points:
                if point not in merged_key_points:
                    merged_key_points.append(point)
        
        # 合并提到的板块（去重）
        merged_sectors = []
        for result in all_results:
            sectors = result.get("mentioned_sectors", [])
            for sector in sectors:
                if sector not in merged_sectors:
                    merged_sectors.append(sector)
        
        # 使用第一段的主要分类和摘要
        first_result = all_results[0]
        
        return {
            "tags": merged_tags,
            "category": first_result.get("category", "other"),
            "summary": first_result.get("summary", ""),
            "mentioned_sectors": merged_sectors,
            "sentiment": first_result.get("sentiment", "neutral"),
            "confidence": first_result.get("confidence", "medium"),
            "key_points": merged_key_points,
            "analysis_method": "llm_segmented"
        }
    
    def _fallback_analysis(self, content):
        """
        LLM 分析失败时的后备方案（使用规则）
        
        :param content: 帖子内容
        :return: 分析结果
        """
        logger.info("使用规则引擎作为后备方案")
        
        tags = []
        category = "other"
        
        content_lower = content.lower()
        
        # 关键词分析
        keywords_map = {
            "market": ["市场", "大盘", "指数", "沪指", "创业板", "走势", "行情", "开盘", "收盘", "涨跌", "板块"],
            "technical": ["均线", "macd", "kdj", "布林", "支撑", "压力", "突破", "回调", "趋势", "量能", "成交量"],
            "stock": ["股票", "个股", "代码", "买入", "卖出", "持仓", "成本", "仓位", "止损", "止盈"],
            "sector": ["半导体", "人工智能", "新能源", "消费", "医药", "金融", "地产", "军工", "科技", "周期"],
            "sentiment": ["看好", "看空", "谨慎", "乐观", "悲观", "风险", "机会", "安全", "危机"],
            "strategy": ["策略", "操作", "建议", "布局", "配置", "减仓", "加仓", "持有", "观望"]
        }
        
        for tag_type, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in content_lower:
                    tags.append(tag_type)
                    break
        
        # 确定主要分类
        if "market" in tags or "sector" in tags:
            category = "market_analysis"
        elif "technical" in tags:
            category = "technical_analysis"
        elif "stock" in tags or "strategy" in tags:
            category = "trading_signal"
        else:
            category = "other"
        
        # 提取提到的板块
        sector_names = ["半导体", "人工智能", "新能源", "消费", "医药", "金融", "地产", "军工", "科技", "周期", "券商", "银行"]
        mentioned_sectors = []
        for sector in sector_names:
            if sector in content:
                mentioned_sectors.append(sector)
        
        # 生成摘要
        content_lines = content.strip().split('\n')
        if content_lines:
            summary_text = '\n'.join(content_lines[:3])
            summary = summary_text[:150] + "..." if len(summary_text) > 150 else summary_text
        else:
            summary = ""
        
        return {
            "tags": list(set(tags)),
            "category": category,
            "summary": summary,
            "mentioned_sectors": mentioned_sectors,
            "analysis_method": "rule_based"
        }
    
    def _clean_quoted_content(self, content):
        """
        清理引用的内容（回复别人的发言），只保留狼大的原创内容
        
        NGA帖子中引用内容通常有以下格式：
        1. >开头的行（markdown引用）
        2. [jump](#pidXXX) 链接
        3. 引用线 ---
        """
        lines = content.strip().split('\n')
        cleaned_lines = []
        
        in_quote = False
        
        for line in lines:
            # 跳过空行
            if not line.strip():
                continue
            
            # 跳过引用标记
            if line.startswith('>'):
                continue
            
            # 跳过jump链接
            if '[jump' in line.lower():
                continue
            
            # 跳过引用线
            if line.strip() == '---':
                continue
            
            # 跳过用户信息行（格式类似：username(uid)(YYYY-MM-DD HH:MM) 说:）
            if re.match(r'.*\(\d+\)\(\d{4}-\d{2}-\d{2} \d{2}:\d{2}\).*说:', line):
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def add_post(self, post_num, post_date, post_content):
        """
        添加新帖子到知识库
        
        :param post_num: 帖子编号
        :param post_date: 帖子日期（datetime对象）
        :param post_content: 帖子内容
        """
        # 检查是否已存在
        for existing in self.posts_index:
            if existing["post_num"] == post_num:
                logger.info(f"帖子 {post_num} 已存在于知识库中")
                return False
        
        # AI分析帖子
        analysis = self.analyze_post_with_ai(post_content, post_date)
        
        # 创建帖子记录
        post_record = {
            "post_num": post_num,
            "date": post_date.strftime("%Y-%m-%d %H:%M:%S"),
            "tags": analysis["tags"],
            "category": analysis["category"],
            "summary": analysis["summary"],
            "mentioned_sectors": analysis["mentioned_sectors"],
            "content_hash": hash(post_content)
        }
        
        # 添加到索引
        self.posts_index.append(post_record)
        
        # 更新标签索引
        for tag in analysis["tags"]:
            if post_num not in self.tags_index[tag]:
                self.tags_index[tag].append(post_num)
        
        # 按日期分组存储
        date_key = post_date.strftime("%Y%m")
        month_dir = os.path.join(self.posts_dir, date_key)
        os.makedirs(month_dir, exist_ok=True)
        
        # 保存完整内容到文件
        post_file = os.path.join(month_dir, f"{post_num}.json")
        with open(post_file, 'w', encoding='utf-8') as f:
            json.dump({
                "post_num": post_num,
                "date": post_date.strftime("%Y-%m-%d %H:%M:%S"),
                "content": post_content,
                "analysis": analysis
            }, f, ensure_ascii=False, indent=2)
        
        # 保存索引
        self._save_indices()
        
        logger.info(f"帖子 {post_num} 已成功添加到知识库，标签: {analysis['tags']}")
        return True
    
    def get_posts_by_date_range(self, start_date, end_date):
        """
        获取指定日期范围内的帖子
        
        :param start_date: 开始日期（datetime对象）
        :param end_date: 结束日期（datetime对象）
        :return: 帖子列表
        """
        result = []
        start_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_date.strftime("%Y-%m-%d %H:%M:%S")
        
        for post in self.posts_index:
            if start_str <= post["date"] <= end_str:
                result.append(post)
        
        return sorted(result, key=lambda x: x["date"])
    
    def get_posts_by_tag(self, tag):
        """
        获取指定标签的帖子
        
        :param tag: 标签名称
        :return: 帖子列表
        """
        post_nums = self.tags_index.get(tag, [])
        result = []
        for post in self.posts_index:
            if post["post_num"] in post_nums:
                result.append(post)
        
        return sorted(result, key=lambda x: x["date"])
    
    def get_recent_posts(self, days=7):
        """
        获取最近N天的帖子
        
        :param days: 天数
        :return: 帖子列表
        """
        end_date = datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        
        return self.get_posts_by_date_range(start_date, end_date)
    
    def get_tag_summary(self):
        """获取标签统计摘要"""
        tag_stats = {}
        for tag, post_nums in self.tags_index.items():
            tag_stats[tag] = len(post_nums)
        
        return sorted(tag_stats.items(), key=lambda x: x[1], reverse=True)
    
    def get_category_stats(self):
        """获取分类统计"""
        category_counts = defaultdict(int)
        for post in self.posts_index:
            category_counts[post["category"]] += 1
        
        return dict(category_counts)

# 示例用法
if __name__ == "__main__":
    kb = KnowledgeBase()
    
    # 测试添加帖子
    test_content = """今天半导体板块表现不错，从技术面来看，MACD指标出现金叉信号，建议关注相关个股的买入机会。但要注意成交量是否跟上，如果量能不足可能会有回调风险。"""
    kb.add_post(1001, datetime.now(), test_content)
    
    # 获取标签统计
    print("标签统计:", kb.get_tag_summary())
    
    # 获取分类统计
    print("分类统计:", kb.get_category_stats())
    
    # 获取最近帖子
    print("最近帖子:", kb.get_recent_posts())
