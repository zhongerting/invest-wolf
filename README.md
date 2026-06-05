# 狼大投资助手

一个基于PyQt6的智能投资辅助工具，集成了持仓管理、NGA论坛爬取、AI智能分析和定时任务功能。

## 版权声明

### 本项目

Copyright (c) 2026. All rights reserved.

### 第三方组件

本项目使用了以下开源组件：

#### ngapost2md

- **来源**: [https://github.com/ludoux/ngapost2md](https://github.com/ludoux/ngapost2md)
- **许可证**: MIT License
- **版权声明**: Copyright (c) 2020-2026 Lu Chang
- **使用说明**: 本项目使用ngapost2md作为NGA帖子爬取工具，遵循MIT许可证条款。ngapost2md是一个用Go语言编写的NGA帖子转Markdown工具。

MIT许可证允许：
- 商业使用
- 复制和分发
- 修改和改进
- 私有使用

要求：
- 包含原始版权声明
- 在再分发时包含许可证副本

---

## 功能介绍

### 1. 持仓管理

- 实时显示持仓信息（市值、成本、盈亏）
- 支持买入/卖出操作
- 自动计算总资产、总市值、持仓占比
- 现金余额管理

### 2. NGA帖子爬取

- 自动爬取指定NGA帖子
- 按用户ID筛选发言（狼大发言）
- 定时爬取（支持自定义间隔）
- 支持增量更新

### 3. AI智能分析

- 对狼大发言进行智能分析
- 自动生成操作指示和风险提示
- 关联历史发言进行参考
- 智能对话功能（基于知识库）

### 4. 每日复盘

- 自动生成每日投资复盘报告
- 结合市场数据和发言分析
- 定时执行（晚间23:00）

### 5. 盘中分析

- 实时监控持仓ETF价格
- 定时刷新（交易时段）
- 桌面通知提醒

---

## 安装说明

### 环境要求

- Python 3.9+
- Windows操作系统

### 第一步：安装Python依赖

```bash
pip install -r requirements.txt
```

`requirements.txt`包含以下依赖：
- PyQt6 >= 6.4.0 (GUI框架)
- requests >= 2.28.0 (HTTP请求)
- schedule >= 1.1.0 (定时任务)

### 第二步：配置ngapost2md

ngapost2md已包含在`tools/ngapost2md/`目录中。

#### 方式一：使用预编译版本

`tools/ngapost2md/`目录中已包含`ngapost2md.exe`可执行文件。

#### 方式二：从源码编译

如果需要重新编译：

```bash
cd tools/ngapost2md
go build -o ngapost2md.exe main.go
```

需要Go 1.25+环境。

#### 配置ngapost2md

在`tools/ngapost2md/`目录下创建`config.ini`文件：

```ini
[config]
ua = 你的User-Agent
ngaPassportUid = 你的UID
ngaPassportCid = 你的Cid
```

获取方法：
1. 登录NGA论坛
2. 按F12打开开发者工具
3. 在Network中找到任意请求，复制Cookie中的`ngaPassportUid`和`ngaPassportCid`
4. UA可以使用浏览器默认UA

### 第三步：配置API

首次运行程序后，会自动生成`app_config.json`配置文件。编辑该文件配置API：

```json
{
  "llm_main": {
    "api_url": "https://your-llm-api.com/v1/chat/completions",
    "api_key": "your-api-key",
    "model": "your-model-name"
  },
  "biying": {
    "base_url": "https://api.biyingapi.com",
    "licence": "your-biying-licence"
  }
}
```

#### LLM API配置

程序使用大语言模型进行智能分析。推荐使用兼容OpenAI格式的API：

| 配置项 | 说明 |
|--------|------|
| api_url | API地址，如 `https://gcli.ggchan.dev/v1/chat/completions` |
| api_key | API密钥 |
| model | 模型名称，如 `gemini-3-flash-preview` |

#### 必盈API配置（可选）

用于获取实时行情数据：

| 配置项 | 说明 |
|--------|------|
| base_url | 必盈API地址（默认已配置） |
| licence | 必盈API许可证密钥 |

---

## 使用说明

### 启动主程序

```bash
python main.py
```

### 自动爬取模式

使用命令行定时爬取（不含GUI）：

```bash
# 单次爬取
python nga_auto_crawler.py --once

# 启动定时任务
python nga_auto_crawler.py --schedule
```

### 定时任务配置

程序支持以下定时任务：

| 任务 | 默认时间 | 说明 |
|------|----------|------|
| 盘中爬取 | 每5分钟 | 交易时段(9:30-11:30, 13:00-15:00) |
| 晚间爬取 | 23:00 | 收盘后爬取最新发言 |
| 每日备份 | 00:00 | 备份当日数据 |
| 每日复盘 | 23:30 | 生成复盘报告 |

可通过`config.py`修改定时任务的执行时间和间隔。

---

## 项目结构

```
狼大投资助手/
├── main.py                    # PyQt6主程序
├── config.py                  # 配置文件
├── requirements.txt            # Python依赖
├── database.py                 # 数据库管理
├── positions.py                # 持仓管理
├── biying_client.py            # 必盈API客户端
├── eastmoney_client.py         # 东方财富API客户端
├── knowledge_base.py           # 知识库管理
├── smart_analysis.py           # 智能分析服务
├── chat_assistant.py           # 智能对话
├── nga_crawler.py              # NGA爬取客户端
├── nga_auto_crawler.py         # 自动爬取定时任务
├── daily_review.py             # 每日复盘
├── intraday_analysis.py        # 盘中分析
├── task_scheduler.py           # 任务调度器
├── llm_client.py               # LLM API客户端
├── data_source.py              # 数据源整合
├── build_knowledge_base.py     # 知识库构建
├── tools/
│   └── ngapost2md/            # NGA爬取工具
│       ├── ngapost2md.exe      # 可执行文件
│       └── ...
└── knowledge_base/             # 知识库数据（运行时生成）
```

---

## 注意事项

1. **数据安全**: `app_config.json`包含敏感信息，请勿上传至公开仓库
2. **网络请求**: NGA爬取有一定频率限制，请勿设置过短的爬取间隔
3. **市场风险**: 程序仅供参考，投资决策请自行判断

---

## 许可证

本项目仅供学习和研究使用。
