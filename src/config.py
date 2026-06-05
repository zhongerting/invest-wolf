import os
import json
import logging

logger = logging.getLogger(__name__)

class Config:
    # 项目基础配置
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOG_FILE = os.path.join(BASE_DIR, "investment_analysis.log")
    CONFIG_FILE = os.path.join(BASE_DIR, "app_config.json")
    
    # 配置字典（运行时配置
    _config = {}
    
    @staticmethod
    def load_config():
        """从文件加载配置"""
        try:
            if os.path.exists(Config.CONFIG_FILE):
                with open(Config.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    Config._config = json.load(f)
                logger.info("配置文件加载成功")
                # 应用配置到类属性
                Config._apply_config()
            else:
                logger.info("配置文件不存在，使用默认配置")
                # 保存默认配置
                Config.save_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            Config._config = {}
    
    @staticmethod
    def save_config():
        """保存配置到文件"""
        try:
            os.makedirs(os.path.dirname(Config.CONFIG_FILE), exist_ok=True)
            # 从类属性构建配置字典
            Config._build_config_dict()
            with open(Config.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(Config._config, f, ensure_ascii=False, indent=2)
            logger.info("配置文件保存成功")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    @staticmethod
    def _apply_config():
        """将配置字典应用到类属性"""
        # LLM主配置
        if 'llm_main' in Config._config:
            llm_main = Config._config['llm_main']
            Config.LLM_API_URL = llm_main.get('api_url', Config.LLM_API_URL)
            Config.LLM_API_KEY = llm_main.get('api_key', Config.LLM_API_KEY)
            Config.LLM_MODEL = llm_main.get('model', Config.LLM_MODEL)
        
        # LLM备用配置
        if 'llm_backup' in Config._config:
            llm_backup = Config._config['llm_backup']
            Config.LLM_API_URL_BACKUP = llm_backup.get('api_url', Config.LLM_API_URL_BACKUP)
            Config.LLM_API_KEY_BACKUP = llm_backup.get('api_key', Config.LLM_API_KEY_BACKUP)
            Config.LLM_MODEL_BACKUP = llm_backup.get('model', Config.LLM_MODEL_BACKUP)
        
        # 任务特定模型
        if 'llm_task' in Config._config:
            llm_task = Config._config['llm_task']
            Config.LLM_MODEL_DAILY_REVIEW = llm_task.get('daily_review', Config.LLM_MODEL_DAILY_REVIEW)
            Config.LLM_MODEL_POST_ANALYSIS = llm_task.get('post_analysis', Config.LLM_MODEL_POST_ANALYSIS)
            Config.LLM_MODEL_CHAT = llm_task.get('chat', Config.LLM_MODEL_CHAT)
            Config.LLM_MODEL_OPERATION_PARSE = llm_task.get('operation_parse', Config.LLM_MODEL_OPERATION_PARSE)
        
        # 必盈API配置
        if 'biying' in Config._config:
            biying = Config._config['biying']
            Config.BIYING_BASE_URL = biying.get('base_url', Config.BIYING_BASE_URL)
            Config.BIYING_LICENCE = biying.get('licence', Config.BIYING_LICENCE)
        
        # 东方财富API配置
        if 'eastmoney' in Config._config:
            eastmoney = Config._config['eastmoney']
            Config.MX_API_URL = eastmoney.get('api_url', Config.MX_API_URL)
            Config.MX_API_KEY = eastmoney.get('api_key', Config.MX_API_KEY)
    
    @staticmethod
    def _build_config_dict():
        """从类属性构建配置字典"""
        Config._config = {
            'llm_main': {
                'api_url': Config.LLM_API_URL,
                'api_key': Config.LLM_API_KEY,
                'model': Config.LLM_MODEL
            },
            'llm_backup': {
                'api_url': Config.LLM_API_URL_BACKUP,
                'api_key': Config.LLM_API_KEY_BACKUP,
                'model': Config.LLM_MODEL_BACKUP
            },
            'llm_task': {
                'daily_review': Config.LLM_MODEL_DAILY_REVIEW,
                'post_analysis': Config.LLM_MODEL_POST_ANALYSIS,
                'chat': Config.LLM_MODEL_CHAT,
                'operation_parse': Config.LLM_MODEL_OPERATION_PARSE
            },
            'biying': {
                'base_url': Config.BIYING_BASE_URL,
                'licence': Config.BIYING_LICENCE
            },
            'eastmoney': {
                'api_url': Config.MX_API_URL,
                'api_key': Config.MX_API_KEY
            }
        }
    
    # NGA帖子配置
    TID = 45974302
    AUTHOR_ID = 150058
    TOOL_DIR = os.path.join(BASE_DIR, "tools", "ngapost2md")  # 相对路径，相对于项目根目录
    TOOL_EXE = os.path.join(TOOL_DIR, "ngapost2md.exe")
    
    # 文件路径配置
    KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")
    POSITIONS_FILE = os.path.join(BASE_DIR, "positions.json")
    DAILY_REPORT_DIR = os.path.join(BASE_DIR, "daily_reports")
    INTRADAY_ALERTS_DIR = os.path.join(BASE_DIR, "intraday_alerts")
    
    # 东方财富妙想API配置（已弃用，保留兼容）
    MX_API_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/query"
    MX_API_KEY = os.environ.get("MX_APIKEY", "")
    
    # 必盈API配置（主行情数据源）
    BIYING_BASE_URL = "https://api.biyingapi.com"
    BIYING_LICENCE = "D98DACC0-428F-43A4-82AE-3C04C0EE4DA3"
    
    # 指数代码映射（名称→必盈API代码）
    INDEX_CODE_MAP = {
        "上证指数": "000001",
        "深证成指": "399001",
        "创业板指": "399006",
        "科创50": "000688",
        "沪深300": "000300",
        "中证500": "000905",
    }
    
    # ETF名称映射（代码→中文名）
    ETF_NAME_MAP = {
        "510210": "上证指数ETF",
        "515880": "半导体ETF",
        "513260": "新能源车ETF",
        "588870": "科创板ETF",
        "510300": "沪深300ETF",
        "510500": "中证500ETF",
        "159995": "芯片ETF",
        "512760": "半导体50ETF",
        "512480": "半导体ETF易方达",
        "512000": "券商ETF",
        "512880": "证券ETF",
        "159915": "创业板ETF",
        "510050": "上证50ETF",
        "513500": "中概互联ETF",
        "513100": "纳指ETF",
        "512980": "证券ETF",
        "510880": "红利ETF",
        "159928": "消费ETF",
        "159902": "中小板ETF",
        "510180": "上证180ETF",
    }
    
    # LLM API配置
    LLM_API_URL = "https://gcli.ggchan.dev/v1/chat/completions"
    LLM_API_KEY = "gg-gcli-KVOOFwFjeKUrkwfZlyjGZUIleVoIPbaSwdoJ1l1WRe4"
    LLM_MODEL = "gemini-3-flash-preview"
    
    # 任务特定模型配置
    LLM_MODEL_DAILY_REVIEW = "gemini-3.1-pro-preview-cache"    # 每日复盘使用
    LLM_MODEL_POST_ANALYSIS = "gemini-2.5-pro-search"          # 狼大发言分析使用
    LLM_MODEL_CHAT = "gemini-3.1-pro-preview-cache"            # 智能对话使用（假流式版本）
    LLM_MODEL_OPERATION_PARSE = "gemini-3-flash-preview"       # 持仓操作解析使用（默认使用主模型）
    
    # LLM API配置（备用API - NVIDIA）
    LLM_API_URL_BACKUP = "https://integrate.api.nvidia.com/v1/chat/completions"
    LLM_API_KEY_BACKUP = "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"
    LLM_MODEL_BACKUP = "deepseek-ai/deepseek-v4-flash"
    
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
    
    # 狼大发帖监控配置（快速响应模式）
    NGA_MONITOR_INTERVAL_MINUTES = 5  # 监控频率：5分钟一次（交易时段）
    NGA_MONITOR_COOLDOWN_MINUTES = 5  # 发现新帖后冷却时间：5分钟
    NGA_MONITOR_ENABLED = True  # 是否启用监控
    NGA_MONITOR_DESKTOP_NOTIFICATION = True  # 桌面通知
    NGA_MONITOR_SOUND_ALERT = True  # 声音提醒
    
    # 分析配置
    MAX_HISTORY_DAYS_FOR_ANALYSIS = 30
    
    @staticmethod
    def ensure_directories():
        os.makedirs(Config.KNOWLEDGE_BASE_DIR, exist_ok=True)
        os.makedirs(Config.DAILY_REPORT_DIR, exist_ok=True)
        os.makedirs(Config.INTRADAY_ALERTS_DIR, exist_ok=True)
