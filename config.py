import os

class Config:
    # 项目基础配置
    BASE_DIR = r"e:\杂项\NGA狼"
    LOG_FILE = os.path.join(BASE_DIR, "investment_analysis.log")
    
    # NGA帖子配置
    TID = 45974302
    AUTHOR_ID = 150058
    TOOL_DIR = os.path.join(BASE_DIR, "ngapost2md")
    TOOL_EXE = os.path.join(TOOL_DIR, "ngapost2md.exe")
    
    # 文件路径配置
    KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")
    POSITIONS_FILE = os.path.join(BASE_DIR, "positions.json")
    DAILY_REPORT_DIR = os.path.join(BASE_DIR, "daily_reports")
    INTRADAY_ALERTS_DIR = os.path.join(BASE_DIR, "intraday_alerts")
    
    # 东方财富妙想API配置
    MX_API_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/query"
    MX_API_KEY = os.environ.get("MX_APIKEY", "")  # 从环境变量获取
    
    # LLM API配置
    LLM_API_URL = "https://gcli.ggchan.dev/v1/chat/completions"
    LLM_API_KEY = "gg-gcli-KVOOFwFjeKUrkwfZlyjGZUIleVoIPbaSwdoJ1l1WRe4"
    LLM_MODEL = "gemini-3-flash-preview"
    
    # LLM API配置（备用API - Anthropic）
    LLM_API_URL_BACKUP = "https://anthropic.qnaigc.com/v1/messages"
    LLM_API_KEY_BACKUP = "sk-cb63ac5a226656822a4862ce68c39d8045f16bb5482053ce77aad0ba714dcb9b"
    LLM_MODEL_BACKUP = "claude-sonnet-4-20250514"
    
    # LLM API配置（NVIDIA API）
    LLM_API_URL_NVIDIA = "https://integrate.api.nvidia.com/v1/chat/completions"
    LLM_API_KEY_NVIDIA = "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"
    LLM_MODEL_NVIDIA = "deepseek-ai/deepseek-v4-flash"
    
    # 定时任务配置
    INTRADAY_INTERVAL_MINUTES = 5
    MORNING_START = "09:30"
    MORNING_END = "11:30"
    AFTERNOON_START = "13:00"
    AFTERNOON_END = "15:00"
    EVENING_ANALYSIS_TIME = "23:00"
    DAILY_REPORT_TIME = "00:00"
    
    # 分析配置
    MAX_HISTORY_DAYS_FOR_ANALYSIS = 30
    
    @staticmethod
    def ensure_directories():
        os.makedirs(Config.KNOWLEDGE_BASE_DIR, exist_ok=True)
        os.makedirs(Config.DAILY_REPORT_DIR, exist_ok=True)
        os.makedirs(Config.INTRADAY_ALERTS_DIR, exist_ok=True)
