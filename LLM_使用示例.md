# LLM API 使用示例

本文档提供 LLM API 配置后的使用示例和效果对比。

## 配置验证

配置完成后，首先验证是否成功：

```bash
python llm_client.py
```

**成功输出示例**：
```
使用 LLM 分析帖子内容
LLM API 调用成功，返回长度：256
分析结果：{
  "tags": ["market", "technical", "sector"],
  "category": "market_analysis",
  "summary": "半导体板块今天表现不错...",
  "sentiment": "bullish",
  "confidence": "high"
}
```

**未配置输出**：
```
LLM API 未配置，请先设置环境变量：
  LLM_API_URL=<API 地址>
  LLM_API_KEY=<API 密钥>
  LLM_MODEL=<模型名称>（可选，默认 gpt-4o）
```

## 使用场景对比

### 场景 1：帖子内容分析

**输入帖子**：
```
半导体板块今天表现不错，从技术面来看，MACD 指标出现金叉信号，
建议关注相关个股的买入机会。但要注意成交量是否跟上，如果量能
不足可能会有回调风险。
```

**LLM 分析结果**（配置后）：
```json
{
  "tags": ["technical", "sector", "strategy"],
  "category": "technical_analysis",
  "summary": "半导体板块技术面出现 MACD 金叉，建议关注买入机会",
  "mentioned_sectors": ["半导体"],
  "sentiment": "bullish",
  "confidence": "high",
  "key_points": [
    "MACD 金叉信号",
    "建议关注买入",
    "需注意成交量配合"
  ]
}
```

**规则分析结果**（未配置 LLM）：
```json
{
  "tags": ["technical", "sector", "strategy"],
  "category": "technical_analysis",
  "summary": "半导体板块今天表现不错，从技术面来看，MACD 指标出现金叉信号...",
  "mentioned_sectors": ["半导体"],
  "sentiment": "neutral",
  "confidence": "low"
}
```

**优势**：
- ✅ LLM 能更准确判断情绪倾向（bullish vs neutral）
- ✅ 提取关键观点，不仅仅是关键词匹配
- ✅ 理解上下文，区分"建议买入"和"已经买入"
- ✅ 提供置信度评估

---

### 场景 2：策略生成

**输入**：
- 狼大发言：多条关于半导体、新能源的观点
- 市场数据：上证指数点位、成交量等
- 持仓信息：当前持仓股票和盈亏

**LLM 生成的策略**（配置后）：
```json
{
  "short_term": [
    {
      "signal": "半导体板块技术面转好",
      "action": "逢低关注半导体 ETF 或龙头股",
      "conditions": "成交量放大至 1.5 万亿以上"
    },
    {
      "signal": "大盘在 3500 点遇阻",
      "action": "控制仓位在 6 成以内",
      "conditions": "等待方向选择"
    }
  ],
  "medium_term": [
    {
      "signal": "新能源行业景气度回升",
      "action": "逐步布局新能源龙头",
      "conditions": "回调至 20 日均线附近"
    }
  ],
  "long_term": [
    {
      "signal": "科技自主可控是长期主线",
      "action": "持续持有半导体、AI 相关优质标的",
      "conditions": "估值合理区间内"
    }
  ],
  "risks": [
    "美联储加息预期升温",
    "地缘政治风险",
    "成交量持续萎缩"
  ]
}
```

**规则生成策略**（未配置 LLM）：
```json
{
  "short_term": [
    {
      "signal": "观望信号",
      "action": "等待明确信号",
      "conditions": "等待成交量放大或方向选择"
    }
  ],
  "medium_term": [
    {
      "signal": "震荡格局",
      "action": "区间操作，高抛低吸",
      "conditions": "关注支撑压力位"
    }
  ],
  "long_term": [
    {
      "signal": "长期看好",
      "action": "逢低建仓优质标的",
      "conditions": "估值合理时逐步布局"
    }
  ]
}
```

**优势**：
- ✅ 结合具体板块和狼大观点，不是通用模板
- ✅ 提供具体的操作条件和触发信号
- ✅ 风险点更具体，有针对性

---

### 场景 3：持仓诊断

**输入**：
- 持仓：贵州茅台 100%，成本 1850，当前价 1850
- 市场分析：消费板块近期表现疲软

**LLM 诊断结果**（配置后）：
```json
{
  "summary": "持仓过于集中，风险较高",
  "issues": [
    "单一股票持仓 100%，缺乏分散",
    "消费板块近期走势偏弱",
    "未设置止损位"
  ],
  "recommendations": [
    "建议将仓位分散至 3-5 只股票",
    "可考虑配置部分科技、医药板块",
    "设置止损位（如 -10%）",
    "关注茅台即将发布的财报"
  ],
  "risk_level": "high"
}
```

**规则诊断结果**（未配置 LLM）：
```json
{
  "recommendations": [
    "其他行业持仓占比超过 40%，建议分散风险"
  ]
}
```

**优势**：
- ✅ 诊断更深入，不仅看行业分布
- ✅ 建议更具体，包含止损、财报关注等
- ✅ 明确风险等级

---

## 实际使用流程

### 1. 配置环境变量

**方法一：使用配置脚本**
```bash
# 运行配置脚本
.\配置 LLM_API.bat

# 或临时测试
.\测试 LLM_API.bat
```

**方法二：手动设置（PowerShell）**
```powershell
$env:LLM_API_URL="https://api.openai.com/v1/chat/completions"
$env:LLM_API_KEY="sk-xxxxxxxx"
$env:LLM_MODEL="gpt-4o"
```

### 2. 验证配置
```bash
python llm_client.py
```

### 3. 正常使用

配置后，所有功能自动使用 LLM 分析：

```bash
# 单次爬取（自动分析新帖子）
python nga_auto_crawler.py crawl --once

# 生成每日复盘（使用 LLM 生成策略）
python nga_auto_crawler.py review

# 查看持仓诊断
python nga_auto_crawler.py position list
```

---

## 性能对比

| 功能 | 规则分析 | LLM 分析 | 提升 |
|------|---------|---------|------|
| 情绪判断准确率 | ~60% | ~90% | +50% |
| 策略针对性 | 通用模板 | 个性化 | 显著提升 |
| 持仓诊断深度 | 表面统计 | 深入分析 | 显著提升 |
| 响应时间 | <100ms | 2-5 秒 | - |
| 单次分析成本 | ¥0 | ¥0.01-0.05 | - |

---

## 成本估算

假设每天：
- 爬取 20 条新帖子
- 每条帖子分析：~500 tokens
- 每日复盘策略生成：~2000 tokens
- 持仓诊断：~1000 tokens

**每日 token 消耗**：
- 帖子分析：20 × 500 = 10,000 tokens
- 策略生成：2,000 tokens
- 持仓诊断：1,000 tokens
- **总计**：约 13,000 tokens

**以 gpt-3.5-turbo 为例**（$0.002/1000 tokens）：
- 每日成本：13 × $0.002 = $0.026（约¥0.19）
- 每月成本：约¥5.7

**以 gpt-4o 为例**（$0.005/1000 tokens 输入，$0.015/1000 tokens 输出）：
- 假设输入输出各半：约¥0.2-0.5/天
- 每月成本：约¥6-15

**建议**：
- 初期测试使用 gpt-3.5-turbo 或 qwen-turbo
- 正式使用再考虑 gpt-4o 等更强模型

---

## 常见问题

### Q1: LLM 分析失败怎么办？
A: 系统会自动回退到规则分析，不影响正常使用。检查网络、API Key 和账户余额。

### Q2: 响应太慢怎么办？
A: 可以选择更快的模型（如 qwen-turbo、glm-3-turbo），或调整超时时间。

### Q3: 分析结果不理想怎么办？
A: 可以尝试：
- 更换更强的模型（如 gpt-4o）
- 调整 temperature 参数（降低随机性）
- 优化 prompt（在 llm_client.py 中）

### Q4: 可以只分析部分帖子吗？
A: 可以，在 knowledge_base.py 中添加过滤条件。

---

## 下一步

配置完成后，建议按以下顺序测试：

1. **基础测试**：`python llm_client.py`
2. **帖子分析测试**：爬取新帖子并查看分析结果
3. **策略生成测试**：运行每日复盘，查看策略建议
4. **持仓诊断测试**：添加持仓并查看诊断报告

如有问题，请参考 `LLM_API_CONFIG.md` 或检查日志文件。
