#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试API响应
"""

import requests

url = "https://push2.eastmoney.com/api/qt/stock/get"
params = {
    'secid': '1.510210',
    'fields': 'f57,f58,f116,f117,f118,f119,f120,f121,f122,f123,f124,f125'
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

response = requests.get(url, params=params, headers=headers, timeout=10)
print(f"状态码: {response.status_code}")
print(f"响应内容: {response.text}")