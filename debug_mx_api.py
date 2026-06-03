#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试妙想API返回数据
"""

import requests
import json
import os

os.environ['MX_APIKEY'] = 'mkt_y5OEqO1aoagzi_AmfQmbCBzQsRcVDi2GafW6QCsifjs'

api_key = os.environ.get('MX_APIKEY')
base_url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/query"

headers = {
    "Content-Type": "application/json",
    "apikey": api_key
}

# 测试查询
queries = [
    "510210最新价",
    "000001最新点位",
    "上证指数最新点位"
]

for query in queries:
    print(f"\n{'='*50}")
    print(f"查询: {query}")
    print(f"{'='*50}")
    
    data = {"toolQuery": query}
    
    try:
        response = requests.post(base_url, headers=headers, json=data, timeout=30, proxies={})
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"状态: {result.get('status')}")
            print(f"消息: {result.get('message')}")
            
            data = result.get("data", {})
            inner_data = data.get("data", {})
            search_result = inner_data.get("searchDataResultDTO", {})
            dto_list = search_result.get("dataTableDTOList", [])
            
            print(f"\n数据表数量: {len(dto_list)}")
            
            for i, dto in enumerate(dto_list):
                print(f"\n--- 表 {i+1} ---")
                print(f"标题: {dto.get('title')}")
                print(f"实体名称: {dto.get('entityName')}")
                table = dto.get("table", {})
                print(f"表数据: {json.dumps(table, ensure_ascii=False, indent=2)[:1000]}...")
                
    except Exception as e:
        print(f"错误: {e}")