#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话助手 - 智能持仓管理和疑问解答
"""

import os
import logging
import re
import json
from datetime import datetime, timedelta
from llm_client import LLMClient
from data_source import DataSource
from knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


class ChatAssistant:
    """对话助手"""
    
    def __init__(self, position_data=None, data_source=None, knowledge_base=None):
        self.llm_client = LLMClient()
        self.data_source = data_source if data_source else DataSource()
        self.knowledge_base = knowledge_base if knowledge_base else KnowledgeBase()
        self.position_data = position_data
        self.operations_file = 'daily_operations.json'
        self.load_operations()
    
    def load_operations(self):
        """加载每日操作记录"""
        try:
            with open(self.operations_file, 'r', encoding='utf-8') as f:
                self.operations = json.load(f)
        except:
            self.operations = {}
    
    def save_operations(self):
        """保存每日操作记录"""
        with open(self.operations_file, 'w', encoding='utf-8') as f:
            json.dump(self.operations, f, ensure_ascii=False, indent=2)
    
    def should_use_knowledge_base(self, question):
        """
        智能判断是否需要使用知识库
        
        判断逻辑：
        1. 提到"狼大"、"发言"、"观点"、"看法"等关键词
        2. 询问特定板块或股票的看法
        3. 询问市场走势、操作建议
        4. 涉及投资策略、交易理念
        
        :param question: 用户问题
        :return: 是否需要知识库
        """
        keywords = [
            # 直接关键词
            "狼大", "发言", "观点", "看法", "说过", "提过", 
            "最近说", "今天说", "之前说",
            # 市场相关
            "怎么看", "看法", "走势", "行情", "后市", "机会", "风险",
            # 操作相关
            "怎么做", "怎么操作", "建议", "策略", "买入", "卖出",
            # 板块股票
            "半导体", "新能源", "券商", "创业板", "上证指数", "大盘"
        ]
        
        question_lower = question.lower()
        
        # 检查是否包含关键词
        for keyword in keywords:
            if keyword in question_lower:
                return True
        
        return False
    
    def get_recent_knowledge_base(self, days=30):
        """
        获取最近N天的知识库内容（狼大发言）
        
        :param days: 天数（默认30天）
        :return: 格式化的知识库内容字符串
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 获取时间段内的帖子
            posts = self.knowledge_base.get_posts_by_date_range(start_date, end_date)
            
            if not posts:
                return f"【知识库提示】暂无最近{days}天的狼大发言记录"
            
            # 格式化输出
            kb_content = f"【狼大最近{days}天发言记录 - 背景世界书】\n"
            kb_content += "=" * 60 + "\n\n"
            
            for i, post in enumerate(posts, 1):
                post_date = post.get("date", "")
                post_summary = post.get("summary", "")
                post_tags = ", ".join(post.get("tags", []))
                post_category = post.get("category", "")
                post_sectors = ", ".join(post.get("mentioned_sectors", []))
                
                kb_content += f"【发言 {i} - {post_date}】\n"
                kb_content += f"分类: {post_category}\n"
                if post_tags:
                    kb_content += f"标签: {post_tags}\n"
                if post_sectors:
                    kb_content += f"提到板块: {post_sectors}\n"
                kb_content += f"内容摘要: {post_summary}\n\n"
            
            kb_content += "=" * 60 + "\n"
            kb_content += f"总计: {len(posts)} 条发言\n"
            kb_content += "请基于以上狼大的发言记录来回答用户的问题。\n"
            
            return kb_content
            
        except Exception as e:
            logger.error(f"获取知识库内容失败: {e}")
            return f"【知识库提示】获取知识失败: {str(e)}"
    
    def get_full_knowledge_base(self):
        """
        获取全量知识库内容（所有狼大发言）
        
        :return: 格式化的知识库内容字符串
        """
        try:
            # 获取所有帖子
            posts = self.knowledge_base.get_all_posts()
            
            if not posts:
                return "【知识库提示】暂无狼大发言记录"
            
            # 格式化输出
            kb_content = "【狼大全量发言记录 - 背景世界书】\n"
            kb_content += "=" * 60 + "\n"
            kb_content += f"总计 {len(posts)} 条发言\n"
            kb_content += "=" * 60 + "\n\n"
            
            for i, post in enumerate(posts, 1):
                post_date = post.get("date", "")
                post_summary = post.get("summary", "")
                post_tags = ", ".join(post.get("tags", []))
                post_category = post.get("category", "")
                post_sectors = ", ".join(post.get("mentioned_sectors", []))
                
                kb_content += f"【发言 {i} - {post_date}】\n"
                kb_content += f"分类: {post_category}\n"
                if post_tags:
                    kb_content += f"标签: {post_tags}\n"
                if post_sectors:
                    kb_content += f"提到板块: {post_sectors}\n"
                kb_content += f"内容摘要: {post_summary}\n\n"
            
            kb_content += "=" * 60 + "\n"
            kb_content += "请基于以上狼大的全量发言记录来回答用户的问题。\n"
            
            return kb_content
            
        except Exception as e:
            logger.error(f"获取全量知识库内容失败: {e}")
            return f"【知识库提示】获取知识失败: {str(e)}"
    
    def parse_operations(self, user_input):
        """
        解析用户操作
        
        :param user_input: 用户输入的操作描述
        :return: 解析后的操作列表
        """
        # 首先尝试规则解析（更可靠）
        rule_result = self._parse_operations_with_rules(user_input)
        
        # 如果规则解析成功，直接返回
        if rule_result['operations']:
            return rule_result
        
        # 使用LLM解析（优先使用大模型）
        prompt = f"""你是一个专业的股票交易记录助手。请从以下操作描述中识别买卖操作，严格按照JSON格式输出，不要输出其他任何内容。

用户描述：
{user_input}

请识别以下信息：
1. 股票代码（stock_code）：必须是6位数字（如510210）
2. 股票名称（stock_name）：中文名称（如上证指数ETF）
3. 操作类型（operation_type）：买入或卖出
4. 数量（quantity）：整数，股数
5. 价格（price）：买入或卖出的价格，浮点数
6. 操作时间（operation_time）：操作发生的时间，如果没有明确说明则为空字符串

严格按照以下JSON格式输出，只输出JSON：
{{
    "operations": [
        {{
            "stock_code": "6位数字股票代码",
            "stock_name": "股票中文名称",
            "operation_type": "买入",
            "quantity": 1000,
            "price": 10.50,
            "operation_time": "2024-01-15 10:30:00"
        }}
    ],
    "summary": "操作总结描述"
}}

注意事项：
- 如果用户描述中没有提到某个字段（如价格、操作时间），请将该字段设置为空字符串或0
- 股票代码必须是6位数字，其他格式请忽略
- 数量单位默认为"股"，如果是"手"请转换为股数（1手=100股）
- 操作时间格式：YYYY-MM-DD HH:MM:SS，如果没有时间则留空

如果无法识别任何操作，operations数组为空。
"""
        
        try:
            result, used_backup = self.llm_client.chat([{"role": "user", "content": prompt}])
            if used_backup:
                logger.info("持仓操作解析使用备用API")
            logger.debug(f"LLM返回结果: {result}")
            
            # 清理结果，移除可能的markdown标记
            result = result.strip()
            if result.startswith('```json'):
                result = result[7:]
            if result.endswith('```'):
                result = result[:-3]
            result = result.strip()
            
            # 尝试解析JSON
            try:
                parsed = json.loads(result)
                # 验证结构
                if 'operations' in parsed and isinstance(parsed['operations'], list):
                    # 验证每条操作的必要字段
                    valid_ops = []
                    for op in parsed['operations']:
                        # 确保必要字段存在
                        op.setdefault('stock_code', '')
                        op.setdefault('stock_name', '')
                        op.setdefault('operation_type', '')
                        op.setdefault('quantity', 0)
                        op.setdefault('price', 0.0)
                        op.setdefault('operation_time', '')
                        
                        # 验证股票代码是6位数字
                        if op['stock_code'] and len(op['stock_code']) != 6:
                            continue
                            
                        valid_ops.append(op)
                    parsed['operations'] = valid_ops
                    return parsed
                else:
                    return {"operations": [], "summary": "返回格式不正确"}
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}, 原始响应: {result}")
                return rule_result
            except Exception as e:
                logger.error(f"解析失败: {e}")
                return rule_result
        except Exception as e:
            logger.error(f"调用LLM失败: {e}")
            return rule_result
    
    def _parse_operations_with_rules(self, user_input):
        """
        使用规则解析操作（备选方案）
        
        :param user_input: 用户输入的操作描述
        :return: 解析后的操作列表
        """
        operations = []
        summary = ""
        
        # 股票代码模式
        stock_pattern = r'(\d{6})'
        # 数量模式（支持手和股）
        quantity_pattern = r'(\d+(?:\.\d+)?)\s*(?:股|手|份)'
        # 金额模式
        amount_pattern = r'(\d+(?:\.\d+)?)\s*(?:元|块|人民币|金额|元整)'
        
        # 常见ETF映射
        etf_mapping = {
            '510210': '上证指数ETF',
            '515880': '半导体ETF',
            '513260': '新能源车ETF',
            '588870': '科创板ETF',
            '510300': '沪深300ETF',
            '510500': '中证500ETF',
            '159995': '芯片ETF',
            '512760': '半导体50ETF',
            '512480': '半导体ETF易方达',
            '512000': '券商ETF',
            '512880': '证券ETF',
            '159915': '创业板ETF',
            '510050': '上证50ETF',
            '513500': '中概互联ETF',
            '513100': '纳指ETF',
            '512980': '证券ETF',
            '510880': '红利ETF',
            '159928': '消费ETF',
            '159902': '中小板ETF',
            '510180': '上证180ETF'
        }
        
        # 按句子分割
        sentences = re.split(r'[,，。！!？?；;\n]', user_input)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # 查找买入/卖出关键词
            if '买入' in sentence:
                op_type = '买入'
            elif '卖出' in sentence:
                op_type = '卖出'
            elif '加仓' in sentence:
                op_type = '买入'
            elif '减仓' in sentence:
                op_type = '卖出'
            else:
                continue
            
            # 查找股票代码
            code_match = re.search(stock_pattern, sentence)
            if not code_match:
                # 尝试在整个输入中查找代码
                code_match = re.search(stock_pattern, user_input)
                if not code_match:
                    continue
            
            stock_code = code_match.group(1)
            stock_name = etf_mapping.get(stock_code, f"股票{stock_code}")
            
            # 查找数量
            quantity_match = re.search(quantity_pattern, sentence)
            if not quantity_match:
                quantity_match = re.search(quantity_pattern, user_input)
            
            quantity = 0
            if quantity_match:
                quantity = int(float(quantity_match.group(1)))
            
            # 如果数量是0但找到了操作，尝试默认值
            if quantity == 0:
                # 检查是否有"一手"等表述
                if '一手' in sentence or '1手' in sentence:
                    quantity = 100
                elif '两手' in sentence or '2手' in sentence:
                    quantity = 200
            
            # 查找金额
            amount_match = re.search(amount_pattern, sentence)
            if not amount_match:
                amount_match = re.search(amount_pattern, user_input)
            
            amount = 0
            if amount_match:
                amount = float(amount_match.group(1))
            
            operations.append({
                'stock_code': stock_code,
                'stock_name': stock_name,
                'operation_type': op_type,
                'quantity': quantity,
                'amount': amount
            })
        
        if operations:
            summary = f"已识别{len(operations)}条操作"
        else:
            summary = "未识别到有效操作，请按照格式输入：买入/卖出 + 股票代码(6位数字) + 数量"
        
        return {
            'operations': operations,
            'summary': summary
        }
    
    def confirm_and_record_operations(self, operations_data, date=None):
        """
        确认并记录操作（同时更新持仓）
        
        :param operations_data: 操作数据
        :param date: 操作日期（默认今天）
        :return: 是否成功
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        operations = operations_data.get('operations', [])
        if not operations:
            return False
        
        # 记录操作到日志
        if date not in self.operations:
            self.operations[date] = []
        
        for op in operations:
            self.operations[date].append({
                'stock_code': op.get('stock_code', ''),
                'stock_name': op.get('stock_name', ''),
                'operation_type': op.get('operation_type', ''),
                'quantity': op.get('quantity', 0),
                'price': op.get('price', 0.0),
                'amount': op.get('amount', 0),
                'operation_time': op.get('operation_time', ''),
                'recorded_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        self.save_operations()
        logger.info(f"已记录 {len(operations)} 条操作")
        
        # 更新持仓数据
        if self.position_data and self.data_source:
            for op in operations:
                code = op.get('stock_code', '')
                quantity = op.get('quantity', 0)
                op_type = op.get('operation_type', '')
                stock_name = op.get('stock_name', '')
                # 优先使用解析到的价格，如果没有则从数据源获取
                parsed_price = op.get('price', 0.0)
                
                if not code or quantity <= 0:
                    continue
                
                # 获取股票价格（优先使用解析到的价格）
                if parsed_price > 0:
                    price = parsed_price
                    logger.info(f"使用解析到的价格: {price}")
                else:
                    price_data = self.data_source.get_stock_price(code)
                    price = price_data.get('price', 0) if price_data else 0
                    logger.info(f"从数据源获取价格: {price}")
                
                if op_type == '买入':
                    self.position_data.buy_stock(code, quantity, price, stock_name)
                    logger.info(f"持仓更新: 买入 {stock_name}({code}) {quantity}股 @ {price}")
                elif op_type == '卖出':
                    self.position_data.sell_stock(code, quantity, price)
                    logger.info(f"持仓更新: 卖出 {stock_name}({code}) {quantity}股 @ {price}")
        
        return True
    
    def get_today_operations(self, date=None):
        """获取今日操作"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        return self.operations.get(date, [])
    
    def answer_question(self, question, context=None):
        """
        回答用户疑问（支持知识库增强）
        
        :param question: 用户问题
        :param context: 上下文信息（可选）
        :return: 回答内容
        """
        # 构建上下文
        context_info = ""
        if context:
            context_info = f"\n## 上下文信息\n{context}\n"
        
        # 判断是否需要使用知识库
        use_kb = self.should_use_knowledge_base(question)
        kb_content = ""
        
        if use_kb:
            # 优先使用全量知识库（包含所有2919条发言）
            logger.info(f"用户问题涉及知识库，正在检索狼大全量发言记录（{len(self.knowledge_base.get_all_posts())}条）...")
            kb_content = self.get_full_knowledge_base()
            logger.info(f"全量知识库内容已准备")
        
        # 构建系统提示词
        system_prompt = """你是一个专业的投资助手，擅长分析市场数据、交易策略和投资建议。

回答要求：
1. 专业准确
2. 条理清晰
3. 实用性强
4. 如涉及风险，请明确提示
5. 如果知识库中有相关内容，请优先基于狼大的发言来回答问题
6. 如果知识库中没有相关内容，可以基于你的专业知识回答，但要说明这是你自己的看法而非狼大的观点
"""
        
        # 构建用户问题
        user_content = question + "\n" + context_info
        
        if use_kb:
            user_content = kb_content + "\n\n## 用户问题\n" + user_content
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            result, used_backup = self.llm_client.chat(messages)
            if used_backup:
                logger.info("智能对话使用备用API")
            return result
        except Exception as e:
            logger.error(f"回答问题失败: {e}")
            return f"抱歉，回答问题时出现错误：{str(e)}"
    
    def check_need_market_data(self, answer):
        """
        检查是否需要查询市场数据
        
        :param answer: 回答内容
        :return: 需要查询的数据列表
        """
        needs = []
        if '【需要查询：' in answer:
            # 提取需要查询的内容
            matches = re.findall(r'【需要查询：(.*?)】', answer)
            needs = matches
        
        return needs
    
    def query_market_data(self, query):
        """
        查询市场数据（通过综合数据源）
        
        :param query: 查询内容
        :return: 查询结果
        """
        try:
            result = self.data_source.query_mx(query)
            return result
        except Exception as e:
            logger.error(f"查询市场数据失败: {e}")
            return f"查询失败：{str(e)}"
    
    def get_operations_summary(self, date=None):
        """获取操作总结"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        operations = self.get_today_operations(date)
        if not operations:
            return "今日无操作记录"
        
        summary = []
        for op in operations:
            summary.append(f"{op['operation_type']} {op['stock_name']}({op['stock_code']}) {op['quantity']}股")
        
        return "、".join(summary)
