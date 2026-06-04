#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合数据源模块
整合必盈API（实时行情、指数）和东方财富API（分时数据、主力资金流向
"""

import requests
import logging
import os
import re
from datetime import datetime
from config import Config
from biying_client import BiyingClient

logger = logging.getLogger(__name__)


class DataSource:
    """综合数据源"""
    
    def __init__(self):
        """初始化数据源客户端"""
        # 必盈API - 用于实时行情、指数数据
        self.biying_client = BiyingClient()
        
        # 东方财富API Key
        self.mx_api_key = os.environ.get('MX_APIKEY', 'mkt_y5OEqO1aoagzi_AmfQmbCBzQsRcVDi2GafW6QCsifjs')
        self.mx_api_url = Config.MX_API_URL if hasattr(Config, 'MX_API_URL') else 'https://mkapi2.dfcfs.com/finskillshub/api/claw/query'
        
    def is_configured(self):
        """检查数据源是否已配置"""
        return self.biying_client.is_configured()
    
    # ============ 实时行情数据（必盈API）============
    
    def get_stock_price(self, stock_code):
        """
        获取股票实时价格
        """
        return self.biying_client.get_stock_price(stock_code)
    
    def get_index_data(self, index_query):
        """
        获取指数实时数据
        """
        return self.biying_client.get_index_data(index_query)
    
    def get_stock_quote(self, stock_code):
        return self.get_stock_price(stock_code)
    
    def parse_price_from_result(self, result):
        return self.biying_client.parse_price_from_result(result)
    
    # ============ 分时数据（东方财富公开接口）============
    
    def get_tick_data(self, stock_code, target_date=None):
        """
        获取股票分时数据
        
        :param stock_code: 股票代码
        :param target_date: 日期，默认为今天
        """
        if target_date is None:
            target_date = datetime.now()
        
        date_str = target_date.strftime("%Y%m%d")
        
        # 判断是股票代码类型
        if stock_code.startswith('15') or stock_code.startswith('5'):
            # ETF
            secid = f"1.{stock_code}"
        elif stock_code.startswith('0') or stock_code.startswith('3'):
            # 深市
            secid = f"0.{stock_code}"
        else:
            # 沪市
            secid = f"1.{stock_code}"
        
        try:
            url = "http://push2his.eastmoney.com/api/qt/stock/trends2/get"
            params = {
                "secid": secid,
                "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": "101",
                "fqt": "1",
                "beg": date_str,
                "end": date_str
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get("data") and data["data"].get("trends"):
                return {
                    "date": date_str,
                    "name": data["data"].get("name"),
                    "code": stock_code,
                    "open": float(data["data"].get("open", 0)),
                    "high": float(data["data"].get("high", 0)),
                    "low": float(data["data"].get("low", 0)),
                    "close": float(data["data"].get("preClose", 0)),
                    "trends": self._parse_trends(data["data"]["trends"])
                }
            return None
        except Exception as e:
            logger.error(f"获取 {stock_code} 分时数据失败: {e}")
            return None
    
    def _parse_trends(self, trends_data):
        """
        解析东方财富分时数据
        
        数据格式:
        "时间,最新价,均价,成交量(手),成交额(元),...
        """
        result = []
        
        # 兼容字符串和列表两种格式
        trend_list = trends_data if isinstance(trends_data, list) else str(trends_data).split(",")
        
        for trend in trend_list:
            if isinstance(trend, str):
                parts = trend.split(",")
                if len(parts) >= 3:
                    try:
                        result.append({
                            "time": parts[0],
                            "price": float(parts[1]) if parts[1] else 0,
                            "avg_price": float(parts[2]) if parts[2] else 0,
                            "volume": int(float(parts[3])) if len(parts) > 3 and parts[3] else 0,
                            "amount": float(parts[4]) if len(parts) > 4 and parts[4] else 0
                        })
                    except (ValueError, IndexError):
                        continue
        return result
    
    # ============ 主力资金流向（东方财富妙想API）============
    
    def get_main_funds(self, stock_code=None):
        """
        获取主力资金流向
        """
        if not self.mx_api_key:
            logger.warning("东方财富API Key未配置，无法获取主力资金流向")
            return None
        
        try:
            query_text = f"{stock_code} 主力资金流向" if stock_code else "主力资金流向"
            
            headers = {
                "Content-Type": "application/json",
                "apikey": self.mx_api_key
            }
            
            data = {
                "toolQuery": query_text
            }
            
            response = requests.post(
                self.mx_api_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"获取主力资金流向成功")
                return result
            else:
                logger.error(f"获取主力资金流向失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"获取主力资金流向异常: {e}")
            return None
    
    def get_sector_data(self, sector_name):
        """获取板块数据（返回None，必盈API不支持"""
        return None
    
    def query(self, query_text):
        """
        自然语言查询（兼容接口）
        优先尝试从文本提取股票代码并查询价格
        """
        code_match = re.search(r'(\d{6})', query_text)
        if code_match:
            stock_code = code_match.group(1)
            price_data = self.get_stock_price(stock_code)
            return {
                "status": 0,
                "data": {
                    "data": {
                        "searchDataResultDTO": {
                            "dataTableDTOList": [{
                                "table": {
                                    "f2": [price_data.get("price", 0) if price_data else 0]
                                }
                            }]
                        }
                    }
                }
            }
        return {"status": -1, "data": None}
    
    def query_mx(self, query_text):
        """妙想API兼容接口"""
        return self.query(query_text)
