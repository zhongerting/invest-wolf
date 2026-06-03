# LLM API 配置指南

本文档介绍如何配置 LLM API 以增强智能分析功能。

## 支持的 LLM 服务商

系统支持多种 LLM API，你可以选择其中一个进行配置：

### 1. OpenAI GPT（推荐）
- **API 地址**: `https://api.openai.com/v1/chat/completions`
- **支持模型**: gpt-4o, gpt-4, gpt-3.5-turbo
- **优点**: 分析能力强，准确性高
- **缺点**: 需要国际网络，费用较高

### 2. 通义千问（阿里云）
- **API 地址**: `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`
- **支持模型**: qwen-max, qwen-plus, qwen-turbo
- **优点**: 国内访问快，中文理解好
- **缺点**: 需要阿里云账号

### 3. 文心一言（百度）
- **API 地址**: `https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions`
- **支持模型**: ernie-bot-4, ernie-bot-3.5
- **优点**: 中文能力强
- **缺点**: 接口格式略有不同

### 4. 智谱 AI
- **API 地址**: `https://open.bigmodel.cn/api/paas/v4/chat/completions`
- **支持模型**: glm-4, glm-3-turbo
- **优点**: 性价比高，国内访问快
- **缺点**: 知名度相对较低

### 5. 其他兼容 OpenAI 格式的 API
- 包括：DeepSeek、Moonshot（月之暗面）、MiniMax 等
- 只要接口格式兼容 OpenAI，都可以使用

## 配置方法

### 方法一：设置环境变量（推荐）

#### Windows PowerShell（临时设置，当前会话有效）
```powershell
$env:LLM_API_URL="https://api.openai.com/v1/chat/completions"
$env:LLM_API_KEY="你的 API 密钥"
$env:LLM_MODEL="gpt-4o"
```

#### Windows 永久设置（推荐）
1. 右键"此电脑" → "属性" → "高级系统设置"
2. 点击"环境变量"
3. 在"用户变量"或"系统变量"中添加：
   - 变量名：`LLM_API_URL`
   - 变量值：`https://api.openai.com/v1/chat/completions`
4. 同样添加 `LLM_API_KEY` 和 `LLM_MODEL`
5. 重启终端或电脑使设置生效

### 方法二：修改 config.py 文件

编辑 `config.py` 文件，直接写入配置：

```python
# LLM API 配置
LLM_API_URL = "https://api.openai.com/v1/chat/completions"
LLM_API_KEY = "你的 API 密钥"
LLM_MODEL = "gpt-4o"
```

**注意**: 不要将包含密钥的 config.py 提交到版本控制系统！

## 获取 API 密钥

### OpenAI
1. 访问 https://platform.openai.com/
2. 注册/登录账号
3. 进入 API Keys 页面
4. 创建新的 API Key

### 通义千问
1. 访问 https://dashscope.console.aliyun.com/
2. 登录阿里云账号
3. 开通 DashScope 服务
4. 创建 API Key

### 智谱 AI
1. 访问 https://open.bigmodel.cn/
2. 注册/登录账号
3. 进入控制台 → API 密钥管理
4. 创建 API Key

## 测试配置

配置完成后，运行以下命令测试：

```bash
python llm_client.py
```

如果配置正确，会看到类似输出：
```
使用 LLM 分析帖子内容
LLM API 调用成功，返回长度：256
分析结果：{
  "tags": ["market", "technical", "sector"],
  "category": "market_analysis",
  "summary": "半导体板块今天表现不错...",
  ...
}
```

如果显示"LLM API 未配置"，请检查环境变量是否正确设置。

## 费用说明

不同服务商的收费标准（仅供参考，具体以官方为准）：

| 服务商 | 模型 | 价格（每 1000 tokens） |
|--------|------|---------------------|
| OpenAI | gpt-4o | $0.005 (输入) / $0.015 (输出) |
| OpenAI | gpt-3.5-turbo | $0.0005 / $0.0015 |
| 通义千问 | qwen-turbo | ¥0.002 / ¥0.006 |
| 智谱 AI | glm-3-turbo | ¥0.001 / ¥0.001 |

**建议**: 
- 初期测试使用便宜的模型（如 gpt-3.5-turbo 或 qwen-turbo）
- 正式使用再考虑升级到更强的模型

## 使用示例

配置完成后，系统会自动使用 LLM 进行以下分析：

1. **帖子内容分析**: 自动识别市场观点、技术分析、情绪倾向
2. **策略生成**: 根据狼大发言和市场数据生成操作建议
3. **持仓诊断**: 分析持仓结构，给出调仓建议

## 常见问题

### Q: 配置后仍然显示"LLM 未配置"？
A: 检查环境变量是否生效，可以重启终端或电脑。

### Q: 调用失败怎么办？
A: 检查网络连接、API Key 是否正确、账户是否有余额。

### Q: 可以同时配置多个服务商吗？
A: 当前版本只支持一个服务商，如需切换请修改环境变量。

### Q: LLM 分析失败会影响系统运行吗？
A: 不会，系统会自动回退到规则分析模式。

## 下一步

配置完成后，运行以下命令体验完整功能：

```bash
# 单次爬取并分析
python nga_auto_crawler.py crawl --once

# 查看知识库
python -c "from knowledge_base import KnowledgeBase; kb = KnowledgeBase(); print(kb.get_tag_summary())"

# 生成每日复盘
python nga_auto_crawler.py review
```
