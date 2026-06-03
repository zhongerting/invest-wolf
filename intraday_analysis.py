import os
import json
import logging
from datetime import datetime
from config import Config
from knowledge_base import KnowledgeBase
from positions import PositionManager
from eastmoney_api import EastMoneyAPI

logger = logging.getLogger(__name__)

class IntradayAnalyzer:
    def __init__(self):
        self.kb = KnowledgeBase()
        self.pm = PositionManager()
        self.api = EastMoneyAPI()
        Config.ensure_directories()
    
    def is_market_related(self, post_content):
        """
        判断帖子是否涉及市场相关内容
        
        :param post_content: 帖子内容
        :return: True/False 和相关标签
        """
        content_lower = post_content.lower()
        
        # 市场相关关键词
        market_keywords = [
            "市场", "大盘", "指数", "走势", "行情", "板块", "股票", "买入", "卖出",
            "均线", "macd", "kdj", "支撑", "压力", "突破", "回调", "趋势",
            "半导体", "人工智能", "新能源", "消费", "医药", "金融", "军工",
            "看好", "看空", "风险", "机会", "策略", "操作", "建议"
        ]
        
        found_keywords = []
        for keyword in market_keywords:
            if keyword in content_lower:
                found_keywords.append(keyword)
        
        return len(found_keywords) > 0, found_keywords
    
    def analyze_new_post(self, post_num, post_date, post_content):
        """
        分析新帖子并生成操作指示
        
        :param post_num: 帖子编号
        :param post_date: 帖子日期
        :param post_content: 帖子内容
        :return: 分析结果
        """
        result = {
            "post_num": post_num,
            "post_date": post_date.strftime("%Y-%m-%d %H:%M:%S"),
            "is_market_related": False,
            "analysis": {},
            "operations": [],
            "position_impacts": [],
            "risk_alerts": []
        }
        
        # 判断是否市场相关
        is_market, keywords = self.is_market_related(post_content)
        result["is_market_related"] = is_market
        
        if not is_market:
            logger.info(f"帖子 {post_num} 不涉及市场内容，跳过分析")
            return result
        
        # 添加到知识库
        self.kb.add_post(post_num, post_date, post_content)
        
        # 分析内容
        analysis = self._analyze_market_content(post_content, keywords)
        result["analysis"] = analysis
        
        # 生成操作建议
        operations = self._generate_operations(analysis)
        result["operations"] = operations
        
        # 分析对持仓的影响
        position_impacts = self._analyze_position_impacts(analysis)
        result["position_impacts"] = position_impacts
        
        # 检查风险提示
        risk_alerts = self._check_risk_alerts(analysis)
        result["risk_alerts"] = risk_alerts
        
        # 保存分析结果到文件
        self._save_analysis_result(result)
        
        logger.info(f"帖子 {post_num} 分析完成，生成 {len(operations)} 条操作建议")
        return result
    
    def _analyze_market_content(self, content, keywords):
        """分析市场内容，提取关键信息"""
        analysis = {
            "keywords": keywords,
            "sentiment": "neutral",
            "mentioned_sectors": [],
            "technical_signals": [],
            "price_levels": [],
            "summary": ""
        }
        
        # 判断情绪
        content_lower = content.lower()
        if any(word in content_lower for word in ["看好", "机会", "上涨", "强势", "加仓"]):
            analysis["sentiment"] = "bullish"
        elif any(word in content_lower for word in ["看空", "风险", "下跌", "弱势", "减仓"]):
            analysis["sentiment"] = "bearish"
        
        # 识别提到的板块
        sectors = ["半导体", "人工智能", "新能源", "消费", "医药", "金融", "地产", "军工", "科技"]
        for sector in sectors:
            if sector in content:
                analysis["mentioned_sectors"].append(sector)
        
        # 识别技术信号
        if any(word in content_lower for word in ["金叉", "突破", "多头"]):
            analysis["technical_signals"].append("bullish_signal")
        if any(word in content_lower for word in ["死叉", "跌破", "空头"]):
            analysis["technical_signals"].append("bearish_signal")
        if any(word in content_lower for word in ["支撑", "压力", "阻力"]):
            analysis["technical_signals"].append("support_resistance")
        
        # 生成摘要
        lines = content.strip().split('\n')
        if lines:
            analysis["summary"] = lines[0][:150] + "..." if len(lines[0]) > 150 else lines[0]
        
        return analysis
    
    def _generate_operations(self, analysis):
        """根据分析结果生成操作建议"""
        operations = []
        
        # 根据情绪生成建议
        if analysis["sentiment"] == "bullish":
            if analysis["mentioned_sectors"]:
                operations.append({
                    "type": "watch",
                    "target": ", ".join(analysis["mentioned_sectors"]),
                    "action": "关注",
                    "reason": f"狼大对{', '.join(analysis['mentioned_sectors'])}板块表达看好观点",
                    "confidence": "medium"
                })
        elif analysis["sentiment"] == "bearish":
            if analysis["mentioned_sectors"]:
                operations.append({
                    "type": "caution",
                    "target": ", ".join(analysis["mentioned_sectors"]),
                    "action": "谨慎",
                    "reason": f"狼大对{', '.join(analysis['mentioned_sectors'])}板块表达看空观点",
                    "confidence": "medium"
                })
        
        # 根据技术信号生成建议
        if "bullish_signal" in analysis["technical_signals"]:
            operations.append({
                "type": "technical",
                "target": "技术面",
                "action": "技术面偏多",
                "reason": "狼大提到技术面出现多头信号（如金叉、突破等）",
                "confidence": "medium"
            })
        
        if "bearish_signal" in analysis["technical_signals"]:
            operations.append({
                "type": "technical",
                "target": "技术面",
                "action": "技术面偏空",
                "reason": "狼大提到技术面出现空头信号（如死叉、跌破等）",
                "confidence": "medium"
            })
        
        if "support_resistance" in analysis["technical_signals"]:
            operations.append({
                "type": "level",
                "target": "关键价位",
                "action": "关注支撑/压力位",
                "reason": "狼大提到支撑位或压力位，建议关注关键价位表现",
                "confidence": "high"
            })
        
        return operations
    
    def _analyze_position_impacts(self, analysis):
        """分析对当前持仓的影响"""
        impacts = []
        positions = self.pm.get_all_positions()
        
        for pos in positions:
            # 检查持仓股票是否与提到的板块相关
            for sector in analysis["mentioned_sectors"]:
                if sector in pos["stock_name"]:
                    impact_type = "positive" if analysis["sentiment"] == "bullish" else "negative"
                    impacts.append({
                        "stock_code": pos["stock_code"],
                        "stock_name": pos["stock_name"],
                        "sector": sector,
                        "impact": impact_type,
                        "message": f"{pos['stock_name']}属于{sector}板块，受狼大观点影响"
                    })
        
        return impacts
    
    def _check_risk_alerts(self, analysis):
        """检查风险提示"""
        alerts = []
        
        # 如果情绪看空且持仓较多相关股票
        if analysis["sentiment"] == "bearish" and analysis["mentioned_sectors"]:
            positions = self.pm.get_all_positions()
            affected_positions = []
            
            for pos in positions:
                for sector in analysis["mentioned_sectors"]:
                    if sector in pos["stock_name"]:
                        affected_positions.append(pos["stock_name"])
            
            if affected_positions:
                alerts.append({
                    "level": "warning",
                    "message": f"狼大对{', '.join(analysis['mentioned_sectors'])}板块表达谨慎观点",
                    "affected_stocks": affected_positions,
                    "suggestion": "建议关注相关持仓表现，必要时考虑减仓或止损"
                })
        
        return alerts
    
    def _save_analysis_result(self, result):
        """保存分析结果到文件"""
        date_str = datetime.now().strftime("%Y%m%d")
        time_str = datetime.now().strftime("%H%M%S")
        file_name = f"{date_str}_{time_str}_analysis.json"
        file_path = os.path.join(Config.INTRADAY_ALERTS_DIR, file_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"盘中分析结果已保存: {file_path}")
    
    def generate_intraday_report(self):
        """生成当日盘中分析报告"""
        today = datetime.now().strftime("%Y%m%d")
        report = {
            "report_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_analyzed": 0,
            "market_related_count": 0,
            "operations": [],
            "risk_alerts": []
        }
        
        # 读取今日所有分析结果
        for filename in os.listdir(Config.INTRADAY_ALERTS_DIR):
            if filename.startswith(today):
                file_path = os.path.join(Config.INTRADAY_ALERTS_DIR, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    analysis = json.load(f)
                    report["total_analyzed"] += 1
                    if analysis["is_market_related"]:
                        report["market_related_count"] += 1
                        report["operations"].extend(analysis["operations"])
                        report["risk_alerts"].extend(analysis["risk_alerts"])
        
        # 保存报告
        report_file = os.path.join(Config.INTRADAY_ALERTS_DIR, f"{today}_intraday_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report

# 示例用法
if __name__ == "__main__":
    analyzer = IntradayAnalyzer()
    
    # 测试分析
    test_post = """半导体板块今天表现不错，但我认为只是反弹，之后还要找新低。建议反弹减仓，不要追高。"""
    result = analyzer.analyze_new_post(1002, datetime.now(), test_post)
    
    print("分析结果:", json.dumps(result, indent=2, ensure_ascii=False))
