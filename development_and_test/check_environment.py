#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行条件检查脚本
"""
import sys
import os

print("=== NGA狼投资助手 - 运行条件检查 ===")
print("")

# 1. 检查Python版本
print(f"1. Python版本: {sys.version}")
print(f"   Python主版本: {sys.version_info.major}.{sys.version_info.minor}")
print("")

# 2. 检查当前目录
current_dir = os.getcwd()
print(f"2. 当前工作目录: {current_dir}")
print("")

# 3. 检查关键文件
files_to_check = [
    "main.py",
    "config.py",
    "requirements.txt",
    "investment.db",
    "knowledge_base.json",
    "app_config.json"
]

print("3. 关键文件检查:")
for file in files_to_check:
    exists = os.path.exists(file)
    status = "✓ 存在" if exists else "✗ 缺失"
    print(f"   {file:<30} {status}")
print("")

# 4. 检查ngapost2md工具
print("4. ngapost2md工具检查:")
try:
    from config import Config
    print(f"   TOOL_DIR: {Config.TOOL_DIR}")
    print(f"   TOOL_EXE: {Config.TOOL_EXE}")
    exe_exists = os.path.exists(Config.TOOL_EXE)
    print(f"   EXE文件: {'✓ 存在' if exe_exists else '✗ 缺失'}")
except Exception as e:
    print(f"   检查配置失败: {e}")
print("")

# 5. 检查Python依赖
print("5. Python依赖检查:")
dependencies = [
    ("PyQt6.QtWidgets", "PyQt6 (GUI框架)"),
    ("requests", "requests (HTTP请求)"),
    ("schedule", "schedule (定时任务)")
]

for module_name, desc in dependencies:
    try:
        __import__(module_name)
        print(f"   ✓ {desc}")
    except ImportError:
        print(f"   ✗ {desc} - 未安装")
print("")

# 6. 检查目录结构
print("6. 目录结构检查:")
dirs_to_check = [
    "tools/ngapost2md",
    "knowledge_base",
    "daily_reports",
    "intraday_alerts"
]

for dir_path in dirs_to_check:
    exists = os.path.exists(dir_path)
    status = "✓ 存在" if exists else "✗ 缺失"
    print(f"   {dir_path:<30} {status}")
print("")

# 7. 检查是否能启动程序（简单测试）
print("7. 程序启动测试:")
try:
    from config import Config
    from database import DatabaseManager
    db = DatabaseManager()
    print("   ✓ 数据库模块加载成功")
    db.close()
except Exception as e:
    print(f"   ✗ 数据库模块问题: {e}")
print("")

print("=== 检查完成 ===")
print("")
print("如需安装依赖，请运行:")
print("   pip install -r requirements.txt")
