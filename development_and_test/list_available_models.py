#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
列出所有可用的大模型
"""

import requests
import json
from config import Config


def list_openai_compatible_models(api_url, api_key):
    """
    列出OpenAI兼容API的可用模型
    
    :param api_url: API地址（通常是 /v1/chat/completions）
    :param api_key: API密钥
    :return: 模型列表
    """
    # 从聊天URL推断模型列表URL
    base_url = api_url.replace("/chat/completions", "")
    models_url = f"{base_url}/models"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.get(models_url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            return sorted([m.get("id", "unknown") for m in models])
        else:
            return f"请求失败，状态码: {response.status_code}"
    except Exception as e:
        return f"请求异常: {str(e)}"


def list_anthropic_models():
    """
    列出Anthropic API支持的模型（Anthropic没有/models端点，返回已知模型）
    """
    return [
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-haiku-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307"
    ]


def main():
    print("=" * 70)
    print("大模型API可用模型列表")
    print("=" * 70)
    
    # 主API
    print("\n【1】主API (gcli.ggchan.dev)")
    print(f"  当前模型: {Config.LLM_MODEL}")
    print(f"  API地址: {Config.LLM_API_URL}")
    print("  正在查询可用模型...")
    models1 = list_openai_compatible_models(Config.LLM_API_URL, Config.LLM_API_KEY)
    if isinstance(models1, list):
        print(f"  可用模型 ({len(models1)}个):")
        for m in models1:
            print(f"    - {m}")
    else:
        print(f"  {models1}")
    
    # 备用API (Anthropic)
    print("\n【2】备用API (anthropic.qnaigc.com - Anthropic)")
    print(f"  当前模型: {Config.LLM_MODEL_BACKUP}")
    print(f"  API地址: {Config.LLM_API_URL_BACKUP}")
    print(f"  已知支持的模型:")
    for m in list_anthropic_models():
        print(f"    - {m}")
    
    # NVIDIA API
    print("\n【3】NVIDIA API")
    print(f"  当前模型: {Config.LLM_MODEL_NVIDIA}")
    print(f"  API地址: {Config.LLM_API_URL_NVIDIA}")
    print("  正在查询可用模型...")
    models3 = list_openai_compatible_models(Config.LLM_API_URL_NVIDIA, Config.LLM_API_KEY_NVIDIA)
    if isinstance(models3, list):
        print(f"  可用模型 ({len(models3)}个):")
        for m in models3:
            print(f"    - {m}")
    else:
        print(f"  {models3}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()

