#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
必盈API客户端 - 沪深实时行情数据获取

支持的接口：
- 实时股票行情: hsstock/real/time/{code}/{licence}
- 实时指数行情: hsindex/real/time/{code}/{licence}
- 股票基础信息: hsstock/instrument/{code}.S[ZH]/{licence}
- 实时交易公开数据: hsrl/ssjy/{code}/{licence}

Licence: 免费申请于 https://www.biyingapi.com/licencelt.html
"""

import requests
import logging
import re
from datetime import datetime, timedelta
from config import Config

logger = logging.getLogger(__name__)


class BiyingClient:
    """必盈API客户端 - 同时兼容EastMoneyClient和EastMoneyAPI的接口"""

    def __init__(self, licence=None):
        self.base_url = Config.BIYING_BASE_URL
        self.licence = licence if licence else Config.BIYING_LICENCE
        self.stock_name_cache = {}
        self.last_request_time = None
        self.request_count = 0

    def is_configured(self):
        return bool(self.licence)

    def _get_url(self, path, stock_code):
        return f"{self.base_url}/{path}/{stock_code}/{self.licence}"

    def _get_full_code(self, stock_code):
        """根据股票代码推断完整的secid格式（.SZ或.SH）"""
        if stock_code.startswith("6"):
            return f"{stock_code}.SH"
        return f"{stock_code}.SZ"

    def get_stock_price(self, stock_code):
        """
        获取股票实时价格
        同时兼容 EastMoneyClient 和 EastMoneyAPI 的返回格式
        """
        try:
            url = self._get_url("hsstock/real/time", stock_code)
            logger.debug(f"请求必盈API: {url}")
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list) and len(data) > 0:
                item = data[0]
                price = float(item.get("p", 0))
                stock_name = self._resolve_name(stock_code)

                return {
                    "code": stock_code,
                    "name": stock_name,
                    "price": price,
                    "change": float(item.get("ud", 0)),
                    "change_percent": float(item.get("pc", 0)),
                    "volume": int(float(item.get("v", 0))),
                    "amount": float(item.get("cje", 0)),
                    "high": float(item.get("h", 0)),
                    "low": float(item.get("l", 0)),
                    "open": float(item.get("o", 0)),
                    "pre_close": float(item.get("yc", 0)),
                }
            logger.warning(f"必盈API get_stock_price 返回空数据: {stock_code}")
            return self._mock_price(stock_code)
        except Exception as e:
            logger.error(f"必盈API获取 {stock_code} 价格失败: {e}")
            return self._mock_price(stock_code)

    def get_index_data(self, index_query):
        """
        获取指数实时数据
        支持：指数名称（"上证指数"）或代码（"000001"）
        兼容 EastMoneyAPI.get_index_data()
        """
        index_code = Config.INDEX_CODE_MAP.get(index_query, index_query)
        try:
            url = self._get_url("hsindex/real/time", index_code)
            logger.debug(f"请求指数必盈API: {url}")
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list) and len(data) > 0:
                item = data[0]
                price = float(item.get("p", 0))
                return {
                    "code": index_code,
                    "name": index_query,
                    "price": price,
                    "change": float(item.get("ud", 0)),
                    "change_percent": float(item.get("pc", 0)),
                    "volume": int(float(item.get("v", 0))),
                    "amount": float(item.get("cje", 0)),
                    "high": float(item.get("h", 0)),
                    "low": float(item.get("l", 0)),
                    "open": float(item.get("o", 0)),
                    "pre_close": float(item.get("yc", 0)),
                }
            return self._mock_index_data(index_code)
        except Exception as e:
            logger.error(f"必盈API获取指数{index_query}失败: {e}")
            return self._mock_index_data(index_code)

    def get_stock_quote(self, stock_code):
        return self.get_stock_price(stock_code)

    def parse_price_from_result(self, result):
        """
        从API返回中提取价格（兼容EastMoneyAPI接口）
        """
        if not result:
            return None
        if isinstance(result, dict):
            return float(result.get("price", 0)) or None
        if isinstance(result, (int, float)):
            return float(result)
        return None

    def get_main_funds(self, stock_code=None):
        """
        获取主力资金流向
        必盈API无直接对应接口，返回None表示无数据
        """
        return None

    def get_sector_data(self, sector_name):
        return None

    def query(self, query_text):
        """
        自然语言查询（兼容EastMoneyAPI接口）
        尝试从文本中提取股票代码并查询价格
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
        """妙想API兼容接口 - 用于 ChatAssistant"""
        return self.query(query_text)

    def _resolve_name(self, stock_code):
        """获取股票名称，带缓存"""
        if stock_code in self.stock_name_cache:
            return self.stock_name_cache[stock_code]

        name = Config.ETF_NAME_MAP.get(stock_code)
        if name:
            self.stock_name_cache[stock_code] = name
            return name

        full_code = self._get_full_code(stock_code)
        try:
            url = self._get_url("hsstock/instrument", full_code)
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                name = data[0].get("name", f"股票{stock_code}")
                self.stock_name_cache[stock_code] = name
                return name
        except Exception:
            try:
                alt_code = f"{stock_code}.SH" if full_code.endswith(".SZ") else f"{stock_code}.SZ"
                url = self._get_url("hsstock/instrument", alt_code)
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    name = data[0].get("name", f"股票{stock_code}")
                    self.stock_name_cache[stock_code] = name
                    return name
            except Exception:
                pass

        name = f"股票{stock_code}"
        self.stock_name_cache[stock_code] = name
        return name

    def _mock_price(self, stock_code):
        """模拟价格（API不可用时的降级方案）"""
        mock_prices = {
            "510210": 1.028,
            "515880": 1.535,
            "513260": 1.228,
        }
        price = mock_prices.get(stock_code, 1.0)
        name = Config.ETF_NAME_MAP.get(stock_code, f"股票{stock_code}")
        logger.warning(f"使用模拟价格: {stock_code} = {price}")
        return {
            "code": stock_code,
            "name": name,
            "price": price,
            "change": 0,
            "change_percent": 0,
            "volume": 0,
            "amount": 0,
            "high": price,
            "low": price,
            "open": price,
            "pre_close": price,
        }

    def _mock_index_data(self, index_code):
        """模拟指数数据"""
        mock = {
            "000001": 3600, "399001": 12000, "399006": 2400,
            "000688": 1050, "000300": 4200, "000905": 6000,
        }
        price = mock.get(index_code, 3600)
        logger.warning(f"使用模拟指数数据: {index_code} = {price}")
        return {
            "code": index_code,
            "name": "",
            "price": price,
            "change": 0,
            "change_percent": 0,
            "volume": 0,
            "amount": 0,
            "high": price,
            "low": price,
            "open": price,
            "pre_close": price,
        }
