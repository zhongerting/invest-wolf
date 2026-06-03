import requests
import json
import logging
import re
import time
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class LLMClient:
    """
    LLM API 客户端封装
    
    支持多种 LLM API 接口，包括：
    - OpenAI GPT
    - 通义千问
    - 文心一言
    - 智谱 AI
    - Google Gemini（通过兼容接口）
    - 其他兼容 OpenAI 格式的 API
    
    特性：
    - 速率限制（RPM 控制）
    - 指数退避重试机制
    - 支持 429 限流处理
    """
    
    def __init__(self, api_url=None, api_key=None, model=None, rpm_limit=1000):
        # 主API配置（支持自定义）
        self.api_url = api_url if api_url else Config.LLM_API_URL
        self.api_key = api_key if api_key else Config.LLM_API_KEY
        self.model = model if model else Config.LLM_MODEL
        
        # 备用API配置
        self.api_url_backup = Config.LLM_API_URL_BACKUP
        self.api_key_backup = Config.LLM_API_KEY_BACKUP
        self.model_backup = Config.LLM_MODEL_BACKUP
        
        # 当前是否使用备用API
        self.using_backup = False
        
        # 速率限制相关
        self.rpm_limit = rpm_limit  # 每分钟最多请求数（防止被封号）
        self.request_timestamps = []  # 记录请求时间戳
        self.last_request_time = 0
        self.min_request_interval = 60.0 / self.rpm_limit  # 最小请求间隔（秒）
        
        # 重试相关
        self.max_retries = 3
        self.base_delay = 2  # 基础重试延迟（秒）
    
    def _switch_to_backup(self):
        """切换到备用API"""
        if not self.using_backup:
            self.api_url = self.api_url_backup
            self.api_key = self.api_key_backup
            self.model = self.model_backup
            self.using_backup = True
            logger.info("已切换到备用API")
    
    def _switch_to_primary(self):
        """切换回主API"""
        if self.using_backup:
            self.api_url = Config.LLM_API_URL
            self.api_key = Config.LLM_API_KEY
            self.model = Config.LLM_MODEL
            self.using_backup = False
            logger.info("已切换回主API")
    
    def is_configured(self):
        """检查 LLM API 是否已配置"""
        return bool(self.api_url and self.api_key)
    
    def _rate_limit_check(self):
        """
        检查是否超过速率限制
        
        :return: True 表示可以请求，False 表示需要等待
        """
        now = time.time()
        
        # 清理过期的时间戳（只保留最近1分钟内的）
        self.request_timestamps = [t for t in self.request_timestamps if now - t < 60]
        
        # 检查是否超过 RPM 限制
        if len(self.request_timestamps) >= self.rpm_limit:
            # 计算需要等待的时间
            oldest_time = self.request_timestamps[0]
            wait_time = 60 - (now - oldest_time)
            logger.warning(f"速率限制：已达到每分钟 {self.rpm_limit} 次请求，需要等待 {wait_time:.1f} 秒")
            return False, wait_time
        
        # 检查最小请求间隔
        if now - self.last_request_time < self.min_request_interval:
            wait_time = self.min_request_interval - (now - self.last_request_time)
            logger.debug(f"速率限制：需要等待 {wait_time:.2f} 秒")
            return False, wait_time
        
        return True, 0
    
    def _wait_for_rate_limit(self):
        """等待直到可以发送请求"""
        can_proceed, wait_time = self._rate_limit_check()
        while not can_proceed:
            time.sleep(min(wait_time, 5))  # 最多等待5秒，然后重新检查
            can_proceed, wait_time = self._rate_limit_check()
        
        # 记录请求时间
        now = time.time()
        self.request_timestamps.append(now)
        self.last_request_time = now
    
    def chat(self, messages, temperature=0.7, max_tokens=2000):
        """
        发送聊天请求到 LLM API（带速率限制和重试）
        
        :param messages: 消息列表，格式为 [{"role": "user/system/assistant", "content": "内容"}]
        :param temperature: 温度参数，控制随机性
        :param max_tokens: 最大生成长度
        :return: LLM 返回的文本或 None
        """
        if not self.is_configured():
            logger.warning("LLM API 未配置，无法调用")
            return None
        
        # 根据是否使用备用API选择不同的请求格式
        if self.using_backup and "anthropic" in self.api_url:
            # Anthropic API格式
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            # 将OpenAI格式的messages转换为Anthropic格式
            anthropic_messages = []
            for msg in messages:
                if msg.get("role") == "system":
                    anthropic_messages.append({
                        "role": "user",
                        "content": f"【系统提示】{msg.get('content', '')}"
                    })
                else:
                    anthropic_messages.append({
                        "role": "user" if msg.get("role") == "user" else "assistant",
                        "content": msg.get("content", "")
                    })
            
            data = {
                "model": self.model,
                "messages": anthropic_messages,
                "max_tokens": max_tokens
            }
        else:
            # OpenAI兼容格式
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        
        # 重试循环（支持故障转移到备用API）
        for attempt in range(self.max_retries + 1):
            # 速率限制检查
            self._wait_for_rate_limit()
            
            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 根据API类型选择不同的响应解析方式
                    if self.using_backup and "anthropic" in self.api_url:
                        # Anthropic API响应格式
                        content_blocks = result.get("content", [])
                        if content_blocks and len(content_blocks) > 0:
                            content = content_blocks[0].get("text", "")
                        else:
                            content = ""
                    else:
                        # OpenAI兼容格式响应
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    logger.info(f"LLM API 调用成功（第{attempt+1}次尝试），返回长度：{len(content)}")
                    # 如果之前切换到了备用API，成功后切回主API
                    if self.using_backup:
                        self._switch_to_primary()
                    return content
                
                elif response.status_code == 429:
                    # 服务器限流，需要等待
                    retry_after = int(response.headers.get('Retry-After', 10))
                    logger.error(f"LLM API 限流（429），需要等待 {retry_after} 秒，第{attempt+1}次尝试")
                    
                    # 如果是主API限流，尝试切换到备用API
                    if not self.using_backup and attempt < self.max_retries:
                        self._switch_to_backup()
                        headers["Authorization"] = f"Bearer {self.api_key}"
                        continue
                    
                    if attempt < self.max_retries:
                        delay = min(self.base_delay * (2 ** attempt) + (retry_after * 0.5), 60)
                        logger.info(f"等待 {delay:.1f} 秒后重试...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"LLM API 限流，已达最大重试次数 ({self.max_retries})")
                        return None
                
                else:
                    logger.error(f"LLM API 调用失败，状态码：{response.status_code}, 响应：{response.text}")
                    
                    # 如果是主API失败，尝试切换到备用API
                    if not self.using_backup and attempt < self.max_retries:
                        self._switch_to_backup()
                        headers["Authorization"] = f"Bearer {self.api_key}"
                        continue
                    
                    if attempt < self.max_retries:
                        delay = self.base_delay * (2 ** attempt)
                        logger.info(f"等待 {delay:.1f} 秒后重试...")
                        time.sleep(delay)
                        continue
                    else:
                        return None
                        
            except requests.exceptions.RequestException as e:
                logger.error(f"LLM API 请求异常（第{attempt+1}次尝试）：{e}")
                
                # 如果是主API异常，尝试切换到备用API
                if not self.using_backup and attempt < self.max_retries:
                    self._switch_to_backup()
                    headers["Authorization"] = f"Bearer {self.api_key}"
                    continue
                
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    logger.info(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                    continue
                else:
                    return None
        
        return None
    
    def _extract_json(self, text):
        """
        从文本中提取 JSON 内容，处理可能的 markdown 代码块
        
        :param text: 原始文本
        :return: 提取的 JSON 字符串或 None
        """
        if not text:
            return None
            
        # 尝试提取 markdown 代码块中的 JSON
        # 匹配 ```json ... ``` 或 ``` ... ```
        code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        match = re.search(code_block_pattern, text, re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        # 如果没有代码块，直接返回原文本（可能本身就是 JSON）
        return text.strip()
    
    def analyze_post_content(self, post_content, post_date):
        """
        使用 LLM 分析帖子内容，提取标签和关键信息
        
        :param post_content: 帖子内容
        :param post_date: 帖子日期
        :return: 分析结果字典
        """
        prompt = f"""请分析以下股票投资相关的帖子内容，提取关键信息：

帖子内容：
{post_content}

请按照以下 JSON 格式返回分析结果：
{{
    "tags": ["标签 1", "标签 2"],  // 从以下类别选择：market(市场分析), technical(技术分析), stock(个股), sector(板块), sentiment(情绪), strategy(策略)
    "category": "market_analysis|technical_analysis|trading_signal|other",
    "summary": "简短摘要（100 字以内）",
    "mentioned_sectors": ["半导体", "新能源"],  // 提到的板块
    "sentiment": "bullish|bearish|neutral",  // 情绪倾向
    "confidence": "high|medium|low",  // 分析置信度
    "key_points": ["关键点 1", "关键点 2"]  // 关键观点
}}

注意：
1. 只返回 JSON 格式，不要其他内容
2. 如果内容不涉及股市，category 设为"other"
3. sentiment 根据作者对市场的态度判断"""
        
        messages = [
            {"role": "system", "content": "你是一个专业的股票投资分析师，擅长从文本中提取关键信息和市场观点。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.chat(messages, temperature=0.3)
        
        if response:
            try:
                # 尝试提取 JSON（处理可能的 markdown 代码块）
                json_str = self._extract_json(response)
                result = json.loads(json_str)
                logger.info(f"帖子分析成功，类别：{result.get('category')}")
                return result
            except json.JSONDecodeError:
                logger.error(f"LLM 返回格式不是有效的 JSON: {response[:200]}")
                return self._fallback_analysis(post_content)
        else:
            return self._fallback_analysis(post_content)
    
    def generate_trading_strategy(self, wolf_posts, market_data, position_info):
        """
        根据狼大发言、市场数据和持仓生成操作策略
        
        :param wolf_posts: 狼大发言列表
        :param market_data: 市场数据
        :param position_info: 持仓信息
        :return: 策略建议
        """
        prompt = f"""请根据以下信息生成股票操作策略：

## 狼大今日发言摘要：
"""
        
        for i, post in enumerate(wolf_posts, 1):
            prompt += f"{i}. [{post.get('date', '')}] {post.get('summary', '')}\n"
        
        prompt += f"""
## 当前市场概况：
{json.dumps(market_data, ensure_ascii=False, indent=2)}

## 当前持仓：
{json.dumps(position_info, ensure_ascii=False, indent=2)}

请生成操作策略，包括：
1. 短期策略（1-3 天）：具体的买入/卖出/观望建议
2. 中期策略（1-4 周）：趋势判断和波段操作建议
3. 长期策略（1-3 月）：基于基本面的布局建议
4. 风险提示：需要关注的风险点

请按照以下 JSON 格式返回：
{{
    "short_term": [
        {{"signal": "信号", "action": "操作", "conditions": "条件"}}
    ],
    "medium_term": [
        {{"signal": "信号", "action": "操作", "conditions": "条件"}}
    ],
    "long_term": [
        {{"signal": "信号", "action": "操作", "conditions": "条件"}}
    ],
    "risks": ["风险 1", "风险 2"]
}}"""
        
        messages = [
            {"role": "system", "content": "你是一个专业的投资策略顾问，擅长根据市场信息和专家观点生成可操作的投资策略。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.chat(messages, temperature=0.5)
        
        if response:
            try:
                json_str = self._extract_json(response)
                result = json.loads(json_str)
                logger.info("策略生成成功")
                return result
            except json.JSONDecodeError:
                logger.error(f"策略生成返回格式不是有效的 JSON")
                return None
        else:
            return None
    
    def diagnose_position(self, position_data, market_analysis):
        """
        诊断持仓并给出建议
        
        :param position_data: 持仓数据
        :param market_analysis: 市场分析
        :return: 诊断结果
        """
        prompt = f"""请诊断以下股票持仓并给出建议：

## 持仓信息：
{json.dumps(position_data, ensure_ascii=False, indent=2)}

## 市场分析：
{json.dumps(market_analysis, ensure_ascii=False, indent=2)}

请分析：
1. 持仓结构是否合理（行业分布、集中度）
2. 盈亏状况评估
3. 风险提示（止损、回撤等）
4. 调仓建议

请按照以下 JSON 格式返回：
{{
    "summary": "整体评估",
    "issues": ["问题 1", "问题 2"],
    "recommendations": ["建议 1", "建议 2"],
    "risk_level": "high|medium|low"
}}"""
        
        messages = [
            {"role": "system", "content": "你是一个专业的投资顾问，擅长持仓诊断和风险评估。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.chat(messages, temperature=0.4)
        
        if response:
            try:
                json_str = self._extract_json(response)
                result = json.loads(json_str)
                logger.info("持仓诊断完成")
                return result
            except json.JSONDecodeError:
                logger.error(f"持仓诊断返回格式不是有效的 JSON")
                return None
        else:
            return None
    
    def _fallback_analysis(self, post_content):
        """LLM 分析失败时的回退方案（使用规则分析）"""
        tags = []
        content_lower = post_content.lower()
        
        # 关键词分析
        keywords_map = {
            "market": ["市场", "大盘", "指数", "走势", "行情"],
            "technical": ["均线", "macd", "kdj", "支撑", "压力"],
            "stock": ["股票", "个股", "买入", "卖出", "持仓"],
            "sector": ["半导体", "新能源", "消费", "医药"],
            "sentiment": ["看好", "看空", "风险", "机会"],
            "strategy": ["策略", "操作", "建议"]
        }
        
        for tag_type, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in content_lower:
                    tags.append(tag_type)
                    break
        
        return {
            "tags": list(set(tags)),
            "category": "market_analysis" if "market" in tags else "other",
            "summary": post_content[:100] + "..." if len(post_content) > 100 else post_content,
            "mentioned_sectors": [],
            "sentiment": "neutral",
            "confidence": "low",
            "key_points": [],
            "analysis_method": "rule_based_fallback"
        }


# 示例用法
if __name__ == "__main__":
    # 测试 LLM 客户端
    client = LLMClient()
    
    # 检查是否已配置
    if not client.is_configured():
        print("LLM API 未配置，请先设置环境变量：")
        print("  LLM_API_URL=<API 地址>")
        print("  LLM_API_KEY=<API 密钥>")
        print("  LLM_MODEL=<模型名称>（可选，默认 gpt-4o）")
    else:
        print(f"当前模型: {client.model}")
        print(f"速率限制: {client.rpm_limit} RPM")
        
        # 测试分析功能
        test_post = """半导体板块今天表现不错，从技术面来看，MACD 指标出现金叉信号，建议关注相关个股的买入机会。但要注意成交量是否跟上，如果量能不足可能会有回调风险。"""
        
        result = client.analyze_post_content(test_post, "2026-06-02")
        print("分析结果:", json.dumps(result, indent=2, ensure_ascii=False))