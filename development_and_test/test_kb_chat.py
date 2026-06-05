#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试知识库聊天功能
"""

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chat_assistant import ChatAssistant
from knowledge_base import KnowledgeBase

def test_knowledge_base_retrieval():
    """测试知识库检索"""
    print("=" * 70)
    print("测试知识库功能")
    print("=" * 70)
    
    kb = KnowledgeBase()
    
    # 获取最近30天的发言
    print("\n1. 测试知识库检索...")
    assistant = ChatAssistant(knowledge_base=kb)
    
    # 测试获取知识库
    kb_content = assistant.get_recent_knowledge_base(days=30)
    print(f"\n知识库内容长度: {len(kb_content)} 字符")
    print(f"\n知识库内容预览:\n{kb_content[:500]}...")
    
    # 测试判断逻辑
    print("\n" + "=" * 70)
    print("2. 测试知识库使用判断逻辑")
    print("=" * 70)
    
    test_questions = [
        "狼大最近怎么看半导体？",
        "今天上证指数怎么样？",
        "帮我算个数学题",
        "新能源板块有机会吗？",
        "狼大之前说过什么关于券商的看法？",
        "明天天气怎么样？",
        "现在应该买入还是卖出？"
    ]
    
    for question in test_questions:
        should_use = assistant.should_use_knowledge_base(question)
        status = "✅ 使用知识库" if should_use else "❌ 不使用知识库"
        print(f"问题: '{question}' -> {status}")
    
    # 测试完整对话
    print("\n" + "=" * 70)
    print("3. 测试完整对话功能")
    print("=" * 70)
    
    test_conversations = [
        "狼大最近对半导体板块怎么看？",
        "现在市场走势怎么样？"
    ]
    
    for question in test_conversations:
        print(f"\n用户问题: {question}")
        print("-" * 50)
        answer = assistant.answer_question(question)
        print(f"助手回答:\n{answer}")
        print("-" * 50)
    
    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)

if __name__ == "__main__":
    test_knowledge_base_retrieval()

