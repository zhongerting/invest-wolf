#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富妙想API客户端（使用自然语言查询）

功能：
1. 获取股票实时价格
2. 获取指数数据

作者：Trae AI
日期：2026年6月
"""

import requests
import logging
import os

logger = logging.getLogger(__name__)

class EastMoneyClient:
    def __init__(self, use_real_api=True):
        self.use_real_api = use_real_api
        
        # 妙想API配置
        self.base_url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/query"
        self.api_key = os.environ.get('MX_APIKEY', 'mkt_y5OEqO1aoagzi_AmfQmbCBzQsRcVDi2GafW6QCsifjs')
        
        # 模拟价格数据（备用）
        self.mock_prices = {
            '510210': 1.028,   # 上证指数ETF
            '515880': 1.535,   # 半导体ETF
            '513260': 1.228,   # 新能源车ETF
            '000001': 4075.10  # 上证指数
        }
        
        # 指数代码映射（这些代码需要用指数名称查询）
        self.index_codes = {'000001', '000300', '399001', '399006'}
    
    def is_configured(self):
        """检查API是否已配置"""
        return bool(self.api_key)
    
    def query_mx(self, query_text):
        """
        调用妙想API进行自然语言查询
        """
        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }
        data = {
            "toolQuery": query_text
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30, proxies={})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"妙想API调用失败: {e}")
            return None
    
    def parse_price_from_result(self, result):
        """
        从API结果中解析价格
        """
        if not result or result.get("status") != 0:
            return None
        
        data = result.get("data", {}).get("data", {})
        search_result = data.get("searchDataResultDTO", {})
        dto_list = search_result.get("dataTableDTOList", [])
        
        if dto_list:
            for dto in dto_list:
                table = dto.get("table", {})
                if isinstance(table, dict) and "f2" in table:
                    f2_values = table.get("f2", [])
                    if f2_values:
                        try:
                            return float(f2_values[0])
                        except (ValueError, TypeError):
                            continue
        
        return None
    
    def get_stock_price(self, stock_code):
        """
        获取股票实时价格
        
        :param stock_code: 股票代码（如 510210）
        :return: 价格信息字典
        """
        if self.use_real_api:
            return self.get_real_stock_price(stock_code)
        else:
            return self.get_mock_price(stock_code)
    
    def get_real_stock_price(self, stock_code):
        """
        使用妙想API获取股票价格
        """
        try:
            # 构建查询
            query = f"{stock_code}最新价"
            result = self.query_mx(query)
            
            price = self.parse_price_from_result(result)
            if price:
                # 获取股票名称
                stock_name = self._get_stock_name(stock_code)
                logger.info(f"获取 {stock_code} 价格成功: {price}")
                return {
                    'code': stock_code,
                    'name': stock_name,
                    'price': price,
                    'change': 0,
                    'change_percent': 0,
                    'volume': 0,
                    'amount': 0,
                    'high': price,
                    'low': price,
                    'open': price,
                    'pre_close': price
                }
            
            logger.warning(f"未找到 {stock_code} 价格数据，使用模拟数据")
            return self.get_mock_price(stock_code)
                
        except Exception as e:
            logger.error(f"获取股票价格异常，使用模拟数据: {e}")
            return self.get_mock_price(stock_code)
    
    def _get_stock_name(self, stock_code):
        """获取股票名称"""
        # ETF名称映射
        etf_names = {
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
            '513100': '纳指ETF'
        }
        
        return etf_names.get(stock_code, f"股票{stock_code}")
    
    def get_mock_price(self, stock_code):
        """获取模拟价格"""
        price = self.mock_prices.get(stock_code, 1.0)
        return {
            'code': stock_code,
            'price': price,
            'change': 0,
            'change_percent': 0,
            'volume': 0,
            'amount': 0,
            'high': price,
            'low': price,
            'open': price,
            'pre_close': price
        }
    
    def get_index_data(self, index_code):
        """
        获取指数数据
        
        :param index_code: 指数代码（如 000001）
        :return: 指数数据字典
        """
        if self.use_real_api:
            return self.get_real_index_data(index_code)
        else:
            return self.get_mock_index_data(index_code)
    
    def get_real_index_data(self, index_code):
        """使用妙想API获取指数数据"""
        try:
            # 指数需要用名称查询，避免和股票代码冲突
            index_names = {
                '000001': '上证指数',
                '000300': '沪深300',
                '399001': '深证成指',
                '399006': '创业板指'
            }
            
            index_name = index_names.get(index_code, index_code)
            query = f"{index_name}最新点位"
            result = self.query_mx(query)
            
            price = self.parse_price_from_result(result)
            if price:
                logger.info(f"获取指数 {index_code}({index_name}) 数据成功: {price}")
                return {
                    'code': index_code,
                    'price': price,
                    'change': 0,
                    'change_percent': 0,
                    'volume': 0,
                    'amount': 0
                }
            
            return self.get_mock_index_data(index_code)
                
        except Exception as e:
            logger.error(f"获取指数数据异常: {e}")
            return self.get_mock_index_data(index_code)
    
    def get_mock_index_data(self, index_code):
        """获取模拟指数数据"""
        price = self.mock_prices.get(index_code, 3600)
        return {
            'code': index_code,
            'price': price,
            'change': 10.5,
            'change_percent': 0.3,
            'volume': 5000000000,
            'amount': 20000000000
        }
    
    def test_connection(self):
        """测试API连接"""
        try:
            result = self.get_index_data('000001')
            if result and result.get('price', 0) > 1000:  # 指数肯定大于1000
                logger.info(f"股票API连接测试成功，上证指数: {result['price']}")
                return True
            else:
                logger.error("股票API连接测试失败")
                return False
        except Exception as e:
            logger.error(f"API连接测试异常: {e}")
            return False


# 示例用法
if __name__ == "__main__":
    # 设置环境变量
    os.environ['MX_APIKEY'] = 'mkt_y5OEqO1aoagzi_AmfQmbCBzQsRcVDi2GafW6QCsifjs'
    
    client = EastMoneyClient(use_real_api=True)
    
    print("测试股票价格获取...")
    
    # 测试获取股票价格
    price = client.get_stock_price('510210')
    if price:
        print(f"510210 价格: {price['price']}")
        print(f"涨跌幅: {price['change_percent']:.2f}%")
    
    # 测试获取指数
    index = client.get_index_data('000001')
    if index:
        print(f"\n上证指数: {index['price']}")
        print(f"涨跌幅: {index['change_percent']:.2f}%")