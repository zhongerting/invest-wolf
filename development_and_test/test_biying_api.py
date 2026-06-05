#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断必盈API问题
"""
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from config import Config

def test_biying_api():
    """测试必盈API连接"""
    print("=" * 60)
    print("必盈API诊断测试")
    print("=" * 60)
    
    # 检查配置
    print(f"\n配置检查：")
    print(f"  BIYING_BASE_URL: {Config.BIYING_BASE_URL}")
    print(f"  BIYING_LICENCE: {Config.BIYING_LICENCE[:10]}...")
    
    # 测试1：测试股票API
    print(f"\n[测试1] 获取上证指数ETF (510210) 实时价格：")
    url = f"{Config.BIYING_BASE_URL}/hsstock/real/time/510210/{Config.BIYING_LICENCE}"
    print(f"  请求URL: {url}")
    
    try:
        resp = requests.get(url, timeout=15)
        print(f"  HTTP状态码: {resp.status_code}")
        print(f"  响应内容: {resp.text[:500]}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"  数据类型: {type(data)}")
            if isinstance(data, list):
                print(f"  列表长度: {len(data)}")
                if len(data) > 0:
                    item = data[0]
                    print(f"  价格 p: {item.get('p')}")
                    print(f"  涨跌额 ud: {item.get('ud')}")
                    print(f"  涨跌幅 pc: {item.get('pc')}")
                    print(f"  ✅ 测试1通过，API正常返回数据")
            else:
                print(f"  ⚠️ 数据格式不是列表")
        else:
            print(f"  ❌ 测试1失败，HTTP错误: {resp.status_code}")
    except Exception as e:
        print(f"  ❌ 测试1异常: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试2：测试指数API
    print(f"\n[测试2] 获取上证指数 (000001) 实时数据：")
    url = f"{Config.BIYING_BASE_URL}/hsindex/real/time/000001/{Config.BIYING_LICENCE}"
    print(f"  请求URL: {url}")
    
    try:
        resp = requests.get(url, timeout=15)
        print(f"  HTTP状态码: {resp.status_code}")
        print(f"  响应内容: {resp.text[:500]}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"  数据类型: {type(data)}")
            if isinstance(data, list):
                print(f"  列表长度: {len(data)}")
                if len(data) > 0:
                    item = data[0]
                    print(f"  价格 p: {item.get('p')}")
                    print(f"  涨跌额 ud: {item.get('ud')}")
                    print(f"  涨跌幅 pc: {item.get('pc')}")
                    print(f"  ✅ 测试2通过，指数API正常")
            else:
                print(f"  ⚠️数据格式不是列表")
        else:
            print(f"  ❌ 测试2失败，HTTP错误: {resp.status_code}")
    except Exception as e:
        print(f"  ❌ 测试2异常: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试3：测试BiyingClient类
    print(f"\n[测试3] 测试BiyingClient类：")
    try:
        from biying_client import BiyingClient
        client = BiyingClient()
        
        print(f"  is_configured(): {client.is_configured()}")
        
        # 测试获取股票价格
        stock_data = client.get_stock_price("510210")
        print(f"\n  get_stock_price(\"510210\"):")
        if stock_data:
            print(f"    代码: {stock_data.get('code')}")
            print(f"    名称: {stock_data.get('name')}")
            print(f"    价格: {stock_data.get('price')}")
            print(f"    是否模拟: {stock_data.get('is_mock')}")
            if stock_data.get('is_mock'):
                print(f"    ⚠️ 使用的是模拟数据")
            else:
                print(f"    ✅ 使用的是真实API数据")
        
        # 测试获取指数
        index_data = client.get_index_data("000001")
        print(f"\n  get_index_data(\"000001\"):")
        if index_data:
            print(f"    代码: {index_data.get('code')}")
            print(f"    价格: {index_data.get('price')}")
            print(f"    是否模拟: {index_data.get('is_mock')}")
            if index_data.get('is_mock'):
                print(f"    ⚠️ 使用的是模拟数据")
            else:
                print(f"    ✅ 使用的是真实API数据")
                
    except Exception as e:
        print(f"  ❌ 测试3异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    test_biying_api()
