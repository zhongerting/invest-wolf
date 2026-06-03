#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试主API并查询可用模型
"""

import os
import sys
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config

def test_primary_api_models():
    print("="*60)
    print("测试主API")
    print("="*60)
    
    api_url = Config.LLM_API_URL
    api_key = Config.LLM_API_KEY
    
    print(f"\nAPI: {api_url}")
    print(f"Key: {api_key[:20]}...")
    
    # 1. 测试根路径
    print("\n[1] 测试根路径...")
    try:
        resp = requests.get("https://gcli.ggchan.dev/", timeout=10)
        print(f"    状态: {resp.status_code}")
        print(f"    响应: {resp.text[:200]}")
    except Exception as e:
        print(f"    错误: {e}")
    
    # 2. 测试models端点
    print("\n[2] 测试/models端点...")
    try:
        resp = requests.get(
            "https://gcli.ggchan.dev/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        print(f"    状态: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"    可用模型:")
            if "data" in data:
                for model in data.get("data", []):
                    print(f"      - {model.get('id', 'unknown')}")
            else:
                print(f"    响应: {resp.text[:500]}")
        else:
            print(f"    响应: {resp.text[:200]}")
    except Exception as e:
        print(f"    错误: {e}")
    
    # 3. 测试chat completions端点
    print("\n[3] 测试/chat/completions端点...")
    try:
        resp = requests.post(
            "https://gcli.ggchan.dev/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gemini-3.1-pro-preview",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10
            },
            timeout=30
        )
        print(f"    状态: {resp.status_code}")
        print(f"    响应: {resp.text[:300]}")
    except Exception as e:
        print(f"    错误: {e}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    test_primary_api_models()