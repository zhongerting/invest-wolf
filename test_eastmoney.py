#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试东方财富妙想API连接
"""

import os
import requests

# 设置API密钥
os.environ['MX_APIKEY'] = 'mkt_y5OEqO1aoagzi_AmfQmbCBzQsRcVDi2GafW6QCsifjs'

api_key = os.environ.get('MX_APIKEY')
base_url = "https://api.dfcfw.com"

headers = {
    'apikey': api_key,
    'Content-Type': 'application/json'
}

def test_api():
    print(f"API Key: {api_key[:10]}...")
    print(f"Base URL: {base_url}")
    print("=" * 50)
    
    # 测试获取股票价格
    stock_code = '510210'
    url = f"{base_url}/stock/realtime"
    
    try:
        print(f"测试获取股票 {stock_code} 价格...")
        response = requests.get(url, headers=headers, params={'code': stock_code}, timeout=10)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                # 使用响应的编码
                response.encoding = response.apparent_encoding
                data = response.json()
                print(f"JSON解析成功")
                print(f"返回码: {data.get('code')}")
                print(f"返回消息: {data.get('msg', '无')}")
                
                if data.get('code') == 0:
                    result = data.get('data', {})
                    price = result.get('price', 0)
                    print(f"价格: {price}")
                    return price
                else:
                    print(f"API返回错误: {data.get('msg')}")
                    return None
                    
            except Exception as e:
                print(f"JSON解析失败: {e}")
                print(f"响应内容(原始字节前100): {response.content[:100]}")
                return None
        
    except Exception as e:
        print(f"请求异常: {e}")
        return None
    
    return None

if __name__ == "__main__":
    price = test_api()
    print(f"\n最终获取的价格: {price}")