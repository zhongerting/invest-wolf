#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试东方财富API功能：主力资金流向和分时数据
"""

import os
import sys
import json
import requests
from datetime import datetime
from eastmoney_api import EastMoneyAPI
from eastmoney_client import EastMoneyClient

def test_main_funds_api():
    """测试主力资金流向获取"""
    print("\n" + "=" * 60)
    print("测试1：主力资金流向获取")
    print("=" * 60)
    
    # 设置API Key
    os.environ['MX_APIKEY'] = 'mkt_y5OEqO1aoagzi_AmfQmbCBzQsRcVDi2GafW6QCsifjs'
    
    # 测试API
    api = EastMoneyAPI()
    
    # 测试获取510210主力资金流向
    print("\n1.1 测试510210主力资金流向")
    result = api.get_main_funds("510210")
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("获取失败，返回None")
    
    # 测试获取大盘主力资金流向
    print("\n1.2 测试大盘主力资金流向")
    result = api.get_main_funds()
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("获取失败，返回None")
    
    return result

def test_tick_data_direct():
    """直接测试东方财富分时数据接口"""
    print("\n" + "=" * 60)
    print("测试2：东方财富分时数据接口")
    print("=" * 60)
    
    # 直接调用东方财富公开API获取分时数据
    test_codes = [
        ("1.510210", "510210"),
        ("1.000001", "000001")
    ]
    
    for secid, code in test_codes:
        print(f"\n2.1 测试 {code} 分时数据")
        try:
            url = "http://push2his.eastmoney.com/api/qt/stock/trends2/get"
            params = {
                "secid": secid,
                "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": "101",
                "fqt": "1",
                "beg": datetime.now().strftime("%Y%m%d"),
                "end": datetime.now().strftime("%Y%m%d")
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get("data") and data["data"].get("trends"):
                print(f"✅ 成功获取 {code} 分时数据")
                print(f"   名称: {data['data'].get('name')}")
                print(f"   最新价: {data['data'].get('prePrice')}")
                print(f"   分时数据条数: {len(data['data']['trends'])}")
                print(f"   样本数据 (前3条): {data['data']['trends'][:3]}")
            else:
                print(f"⚠️  未获取到 {code} 分时数据")
                print(f"完整响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
        except Exception as e:
            print(f"❌ 获取 {code} 分时数据异常: {e}")

def test_integrated_data_source():
    """测试综合数据源方案"""
    print("\n" + "=" * 60)
    print("测试3：综合数据源方案测试")
    print("=" * 60)
    
    print("\n3.1 必盈API - 实时价格和指数数据")
    from biying_client import BiyingClient
    by_client = BiyingClient()
    
    # 测试必盈API
    try:
        price_result = by_client.get_stock_price("510210")
        print(f"   510210价格: {price_result}")
    except Exception as e:
        print(f"   必盈API测试异常: {e}")
    
    print("\n3.2 东方财富API - 分时数据（直接调用公开接口）")

if __name__ == "__main__":
    print("开始测试东方财富API功能...")
    
    # 测试主力资金流向
    test_main_funds_api()
    
    # 测试分时数据
    test_tick_data_direct()
    
    # 测试综合数据源方案
    test_integrated_data_source()
    
    print("\n" + "=" * 60)
    print("测试完成")
