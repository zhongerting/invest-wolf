#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话助手 - 智能持仓管理和疑问解答
"""

import json
import logging
import re
from datetime import datetime
from llm_client import LLMClient
from biying_client import BiyingClient

logger = logging.getLogger(__name__)


class ChatAssistant:
    """对话助手"""
    
    def __init__(self, position_data=None, eastmoney_client=None):
        self.llm_client = LLMClient()
        self.eastmoney_client = eastmoney_client
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
        
        # 如果规则解析失败，尝试LLM解析
        prompt = f"""你是一个专业的股票交易记录助手。请从以下操作描述中识别买卖操作，严格按照JSON格式输出，不要输出其他任何内容。

用户描述：
{user_input}

请识别以下信息：
1. 股票代码：必须是6位数字（如510210）
2. 股票名称：中文名称（如上证指数ETF）
3. 操作类型：买入或卖出
4. 数量：整数，股数
5. 金额：可选，浮点数

严格按照以下JSON格式输出，只输出JSON：
{{
    "operations": [
        {{
            "stock_code": "股票代码",
            "stock_name": "股票名称",
            "operation_type": "买入",
            "quantity": 1000,
            "amount": 10000.0
        }}
    ],
    "summary": "操作总结描述"
}}

如果无法识别任何操作，operations数组为空。
"""
        
        try:
            result = self.llm_client.chat([{"role": "user", "content": prompt}])
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
                        if all(k in op for k in ['stock_code', 'stock_name', 'operation_type', 'quantity']):
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
                'amount': op.get('amount', 0),
                'recorded_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        self.save_operations()
        logger.info(f"已记录 {len(operations)} 条操作")
        
        # 更新持仓数据
        if self.position_data and self.eastmoney_client:
            for op in operations:
                code = op.get('stock_code', '')
                quantity = op.get('quantity', 0)
                op_type = op.get('operation_type', '')
                stock_name = op.get('stock_name', '')
                
                if not code or quantity <= 0:
                    continue
                
                # 获取当前股票价格
                price_data = self.eastmoney_client.get_stock_price(code)
                price = price_data.get('price', 0) if price_data else 0
                
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
        回答用户疑问
        
        :param question: 用户问题
        :param context: 上下文信息（可选）
        :return: 回答内容
        """
        # 构建上下文
        context_info = ""
        if context:
            context_info = f"\n## 上下文信息\n{context}\n"
        
        prompt = f"""你是一个专业的投资助手，擅长分析市场数据、交易策略和投资建议。

用户问题：
{question}
{context_info}

请提供专业、准确、易懂的回答。如果需要查询实时市场数据，请在回答中明确标注【需要查询：XXX】。

回答要求：
1. 专业准确
2. 条理清晰
3. 实用性强
4. 如涉及风险，请明确提示
"""
        
        try:
            result = self.llm_client.chat([{"role": "user", "content": prompt}])
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
        查询市场数据（通过妙想API）
        
        :param query: 查询内容
        :return: 查询结果
        """
        try:
            result = self.eastmoney_client.query_mx(query)
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
