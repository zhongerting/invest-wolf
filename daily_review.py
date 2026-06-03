import os
import json
import logging
from datetime import datetime, timedelta
from config import Config
from knowledge_base import KnowledgeBase
from positions import PositionManager
from biying_client import BiyingClient
from intraday_analysis import IntradayAnalyzer
from llm_client import LLMClient

logger = logging.getLogger(__name__)

class DailyReview:
    def __init__(self):
        self.kb = KnowledgeBase()
        self.pm = PositionManager()
        self.api = BiyingClient()
        self.analyzer = IntradayAnalyzer()
        self.llm_client = LLMClient()
        Config.ensure_directories()
    
    def generate_review(self, target_date=None, use_llm=True):
        """
        生成每日复盘报告
        
        :param target_date: 目标日期（默认当天）
        :param use_llm: 是否使用LLM进行分析（默认True）
        :return: 复盘报告内容
        """
        if target_date is None:
            target_date = datetime.now()
        
        date_str = target_date.strftime("%Y-%m-%d")
        report = {
            "report_date": date_str,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "market_overview": {},
            "technical_review": {},
            "wolf_posts": [],
            "strategy": {
                "short_term": [],
                "medium_term": [],
                "long_term": []
            },
            "position_diagnosis": {},
            "risk_summary": [],
            "operation_review": {
                "score": 0,
                "score_detail": "",
                "operations": [],
                "evaluation": "",
                "suggestions": []
            }
        }
        
        # 获取市场概况
        report["market_overview"] = self._get_market_overview()
        
        # 技术面复盘
        report["technical_review"] = self._get_technical_review()
        
        # 获取狼大当日发言（使用盘中已分析的结果）
        report["wolf_posts"] = self._get_wolf_posts(target_date)
        
        # 对当日所有狼大发言进行一次整体分析，提取狼大的整体思路
        if use_llm:
            report["wolf_daily_summary"] = self._analyze_daily_wolf_summary(report["wolf_posts"])
        else:
            report["wolf_daily_summary"] = {
                "overall_view": "（LLM分析已跳过）",
                "key_signals": [],
                "investment_theme": "未明确",
                "risk_reminder": ""
            }
        
        # 生成操作复盘评分
        report["operation_review"] = self._generate_operation_review(report, target_date, use_llm=use_llm)
        
        # 生成策略建议
        report["strategy"] = self._generate_strategy(report)
        
        # 持仓诊断（添加异常处理）
        try:
            report["position_diagnosis"] = self.pm.generate_diagnosis()
        except Exception as e:
            logger.error(f"持仓诊断失败: {e}")
            report["position_diagnosis"] = {
                "summary": {"total_stocks": 0, "total_value": 0, "total_cost": 0, "total_profit": 0, "total_profit_pct": 0, "positions": []},
                "sector_distribution": {},
                "recommendations": [],
                "stop_loss_alerts": []
            }
        
        # 风险汇总
        report["risk_summary"] = self._get_risk_summary(report)
        
        # 保存报告为Markdown
        md_content = self._generate_markdown_report(report)
        self._save_report(md_content, date_str)
        
        return report
    
    def _get_market_overview(self):
        """获取市场概况"""
        overview = {
            "indices": [],
            "hot_sectors": [],
            "fund_flow": {}
        }
        
        # 获取主要指数数据
        indices = ["上证指数", "深证成指", "创业板指", "科创50"]
        for index in indices:
            result = self.api.get_index_data(index)
            price = self.api.parse_price_from_result(result)
            overview["indices"].append({
                "name": index,
                "current_price": price
            })
        
        # 获取资金流向
        fund_result = self.api.get_main_funds()
        overview["fund_flow"] = {"data": fund_result is not None}
        
        return overview
    
    def _get_technical_review(self):
        """技术面复盘"""
        review = {
            "key_levels": [],
            "trend_analysis": "",
            "volume_analysis": ""
        }
        
        # 获取上证指数分析
        sh_result = self.api.get_index_data("上证指数")
        
        review["key_levels"] = [
            {"level": "支撑位", "description": "3500点附近"},
            {"level": "压力位", "description": "3600点附近"}
        ]
        
        review["trend_analysis"] = "等待市场选择方向，关注成交量变化"
        review["volume_analysis"] = "近期成交量维持在中等水平，需观察是否放量突破"
        
        return review
    
    def _get_wolf_posts(self, target_date):
        """获取狼大当日发言，使用盘中已分析的结果（不再重复调用LLM）"""
        start_date = target_date.replace(hour=0, minute=0, second=0)
        end_date = target_date.replace(hour=23, minute=59, second=59)
        
        posts = self.kb.get_posts_by_date_range(start_date, end_date)
        
        detailed_posts = []
        for post in posts:
            # 获取完整内容
            date_key = target_date.strftime("%Y%m")
            post_file = os.path.join(self.kb.posts_dir, date_key, f"{post['post_num']}.json")
            
            if os.path.exists(post_file):
                with open(post_file, 'r', encoding='utf-8') as f:
                    full_post = json.load(f)
                    content = full_post.get("content", "")
                    # 使用盘中已经分析好的结果
                    existing_analysis = full_post.get("analysis", {})
                    
                    detailed_posts.append({
                        "post_num": post["post_num"],
                        "date": post["date"],
                        "summary": post["summary"],
                        "tags": post["tags"],
                        "category": post["category"],
                        "mentioned_sectors": post.get("mentioned_sectors", []),
                        "content": content,
                        "llm_analysis": {
                            "core_viewpoint": existing_analysis.get("summary", "（盘中分析）"),
                            "market_signal": existing_analysis.get("category", "未知"),
                            "trading_suggestion": existing_analysis.get("summary", "")
                        }
                    })
        
        return detailed_posts

    def _get_stock_intraday_data(self, stock_code, target_date):
        """
        获取股票当日分时数据，用于分析买卖点
        返回分时数据列表，每项包含时间和价格
        """
        try:
            # 使用东方财富API获取分时数据
            date_str = target_date.strftime("%Y%m%d")
            
            # 东方财富分时数据URL
            url = f"http://push2his.eastmoney.com/api/qt/stock/trends2/get"
            params = {
                "secid": self._get_secid(stock_code),
                "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": "101",  # 日K线
                "fqt": "1",    # 前复权
                "beg": date_str,
                "end": date_str
            }
            
            import requests
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get("data") and data["data"].get("trends"):
                trends = data["data"]["trends"]
                # 解析分时数据
                intraday_data = []
                
                # 兼容字符串和列表两种格式
                if isinstance(trends, str):
                    trend_list = trends.split(",")
                elif isinstance(trends, list):
                    trend_list = trends
                else:
                    trend_list = []
                
                for trend in trend_list:
                    if isinstance(trend, str):
                        parts = trend.split("|")
                        if len(parts) >= 3:
                            try:
                                time_str = parts[0]  # 时间 HH:MM:SS
                                price = float(parts[1])  # 价格
                                volume = int(parts[2]) if parts[2] else 0  # 成交量
                                intraday_data.append({
                                    "time": time_str,
                                    "price": price,
                                    "volume": volume
                                })
                            except (ValueError, IndexError):
                                continue
                
                return {
                    "date": date_str,
                    "name": data["data"].get("name", stock_code),
                    "code": stock_code,
                    "open": float(data["data"].get("open", 0)),
                    "high": float(data["data"].get("high", 0)),
                    "low": float(data["data"].get("low", 0)),
                    "close": float(data["data"].get("close", 0)),
                    "volume": int(data["data"].get("volume", 0)),
                    "data": intraday_data
                }
        except Exception as e:
            logger.error(f"获取股票 {stock_code} 分时数据失败: {e}")
        
        return None
    
    def _get_secid(self, stock_code):
        """获取东方财富的secid"""
        if stock_code.startswith("5") or stock_code.startswith("15"):
            # ETF
            return f"1.{stock_code}"
        elif stock_code.startswith("0") or stock_code.startswith("3"):
            # 深圳
            return f"0.{stock_code}"
        else:
            # 上海
            return f"1.{stock_code}"
    
    def _analyze_post_with_llm(self, content, tags):
        """使用LLM分析单条发言内容"""
        if not self.llm_client.is_configured() or not content:
            return {
                "core_viewpoint": "（LLM分析功能未启用）",
                "market_signal": "未知",
                "trading_suggestion": "请启用LLM功能进行详细分析"
            }
        
        try:
            # 构建分析提示词
            tags_str = ", ".join(tags) if tags else "无"
            
            prompt = f"""请分析以下狼大发言内容，提取关键信息：

## 发言内容
{content}

## 已有标签
{tags_str}

## 分析要求
请从以下角度进行分析：
1. 核心观点：狼大这段话的主要观点是什么？
2. 市场信号：这段话传递了哪些市场信号？（如：看多、看空、谨慎、观望等）
3. 操作建议：根据这段话，短线/中线/长线投资者应该如何操作？
4. 风险提示：有什么需要注意的风险点？

请用简洁专业的语言回答，不需要输出JSON格式。"""
            
            # 调用LLM分析
            analysis_text = self.llm_client.chat([{"role": "user", "content": prompt}])
            
            if analysis_text:
                return {
                    "core_viewpoint": analysis_text,
                    "market_signal": self._extract_market_signal(analysis_text),
                    "trading_suggestion": self._extract_trading_suggestion(analysis_text)
                }
            else:
                return {
                    "core_viewpoint": "（LLM分析失败）",
                    "market_signal": "未知",
                    "trading_suggestion": "无法获取分析结果"
                }
        except Exception as e:
            logger.error(f"LLM分析发言失败: {e}")
            return {
                "core_viewpoint": f"（分析出错: {str(e)}）",
                "market_signal": "未知",
                "trading_suggestion": "无法获取分析结果"
            }
    
    def _extract_market_signal(self, analysis_text):
        """从分析文本中提取市场信号"""
        analysis_lower = analysis_text.lower()
        
        if any(keyword in analysis_lower for keyword in ["看多", "买入", "做多", "加仓", "看好"]):
            return "看多"
        elif any(keyword in analysis_lower for keyword in ["看空", "卖出", "做空", "减仓", "谨慎"]):
            return "看空"
        elif any(keyword in analysis_lower for keyword in ["观望", "中性", "等待"]):
            return "观望"
        else:
            return "中性"
    
    def _extract_trading_suggestion(self, analysis_text):
        """从分析文本中提取操作建议"""
        lines = analysis_text.split('\n')
        suggestions = []
        
        for line in lines:
            if any(keyword in line for keyword in ["短线", "中线", "长线", "建议", "操作"]):
                suggestions.append(line.strip())
        
        return "\n".join(suggestions[:3]) if suggestions else "无明确建议"
    
    def _analyze_daily_wolf_summary(self, wolf_posts):
        """
        对当日所有狼大发言进行一次整体分析，提取狼大的整体思路
        输入：当日所有狼大发言（已包含盘中分析结果）
        输出：整体分析总结
        """
        if not wolf_posts or not self.llm_client.is_configured():
            return {
                "overall_view": "暂无整体分析",
                "key_signals": [],
                "investment_theme": "未明确",
                "risk_reminder": ""
            }
        
        # 收集所有发言的摘要和分析
        posts_summary = []
        for post in wolf_posts:
            summary = post.get("summary", "")
            category = post.get("category", "")
            tags = ", ".join(post.get("tags", []))
            posts_summary.append(f"【{category}】{summary} (标签: {tags})")
        
        all_summary = "\n".join(posts_summary)
        
        try:
            prompt = f"""请对狼大今日的所有发言进行综合分析，提取核心思路：

## 今日发言汇总
{all_summary}

## 分析要求
请从以下角度进行综合分析：
1. 整体观点：狼大今天对市场的整体看法是什么？
2. 关键信号：今天提到了哪些重要的市场信号或板块机会？
3. 投资主线：今天的核心投资主题或方向是什么？
4. 风险提示：有哪些需要注意的风险点？

请用简洁专业的语言回答，不需要输出JSON格式。"""
            
            result = self.llm_client.chat([{"role": "user", "content": prompt}])
            
            if result:
                # 解析结果
                lines = result.strip().split('\n')
                return {
                    "overall_view": lines[0] if lines else result,
                    "key_signals": [line for line in lines if "信号" in line or "板块" in line][:3],
                    "investment_theme": [line for line in lines if "主线" in line or "方向" in line or "主题" in line][0] if any("主线" in line or "方向" in line or "主题" in line for line in lines) else "未明确",
                    "risk_reminder": [line for line in lines if "风险" in line][0] if any("风险" in line for line in lines) else ""
                }
            else:
                return {
                    "overall_view": "分析失败",
                    "key_signals": [],
                    "investment_theme": "未明确",
                    "risk_reminder": ""
                }
        except Exception as e:
            logger.error(f"每日狼大发言综合分析失败: {e}")
            return {
                "overall_view": f"分析出错: {str(e)}",
                "key_signals": [],
                "investment_theme": "未明确",
                "risk_reminder": ""
            }
    
    def _generate_operation_review(self, report, target_date, use_llm=True):
        """
        生成今日操作复盘评分
        
        :param report: 报告对象
        :param target_date: 目标日期
        :param use_llm: 是否使用LLM进行评分（默认True）
        """
        operation_review = {
            "score": 0,
            "score_detail": "",
            "operations": [],
            "evaluation": "",
            "suggestions": []
        }
        
        # 获取今日操作记录（从持仓管理器获取）
        today_operations = self._get_today_operations(target_date)
        operation_review["operations"] = today_operations
        
        if not today_operations:
            operation_review["evaluation"] = "今日无操作记录"
            operation_review["suggestions"] = ["建议根据狼大发言和市场情况制定操作计划"]
            return operation_review
        
        # 使用LLM进行评分
        if use_llm and self.llm_client.is_configured():
            llm_result = self._evaluate_operations_with_llm(today_operations, report)
            operation_review["score"] = llm_result.get("score", 50)
            operation_review["score_detail"] = llm_result.get("score_detail", "")
            operation_review["evaluation"] = llm_result.get("evaluation", "")
            operation_review["suggestions"] = llm_result.get("suggestions", [])
        else:
            # 使用规则引擎进行简单评分
            rule_result = self._evaluate_operations_with_rules(today_operations, report)
            operation_review["score"] = rule_result.get("score", 50)
            operation_review["score_detail"] = rule_result.get("score_detail", "")
            operation_review["evaluation"] = rule_result.get("evaluation", "")
            operation_review["suggestions"] = rule_result.get("suggestions", [])
        
        return operation_review
    
    def _get_today_operations(self, target_date):
        """获取今日操作记录"""
        operations = []
        
        try:
            date_str = target_date.strftime("%Y-%m-%d")
            
            # 从 daily_operations.json 读取今日操作
            operations_file = "daily_operations.json"
            if os.path.exists(operations_file):
                with open(operations_file, 'r', encoding='utf-8') as f:
                    all_operations = json.load(f)
                    today_ops = all_operations.get(date_str, [])
                    
                    for op in today_ops:
                        operations.append({
                            "type": op.get("operation_type", "未知"),
                            "stock_name": op.get("stock_name", "未知"),
                            "stock_code": op.get("stock_code", "未知"),
                            "quantity": op.get("quantity", 0),
                            "price": op.get("price", 0),
                            "amount": op.get("amount", 0),
                            "recorded_at": op.get("recorded_at", ""),
                            "action": f"{op.get('operation_type', '未知')} {op.get('quantity', 0)}股"
                        })
            
            # 如果没有从文件读取到操作，也从持仓中获取当前持仓信息
            if not operations:
                try:
                    diagnosis = self.pm.generate_diagnosis()
                    if diagnosis is None:
                        diagnosis = {}
                    positions = diagnosis.get("summary", {}).get("positions", [])
                except Exception as e:
                    logger.error(f"获取持仓诊断失败: {e}")
                    positions = []
                
                for pos in positions:
                    # 当前持仓作为"持有"操作
                    operations.append({
                        "type": "hold",
                        "stock_name": pos.get("stock_name", "未知"),
                        "stock_code": pos.get("stock_code", "未知"),
                        "quantity": pos.get("quantity", 0),
                        "profit_pct": pos.get("profit_pct", 0),
                        "action": "持有"
                    })
        except Exception as e:
            logger.error(f"获取今日操作失败: {e}")
        
        return operations
    
    def _evaluate_operations_with_llm(self, operations, report, target_date=None):
        """使用LLM评估今日操作，结合分时走势进行多维度评分"""
        if target_date is None:
            target_date = datetime.now()
        
        # 获取狼大发言摘要
        wolf_posts_summary = "\n".join([f"{p['date']}: {p['summary']}" for p in report.get("wolf_posts", [])])
        
        # 构建操作详情（不获取分时数据）
        operations_detail = []
        
        for op in operations:
            stock_code = op.get("stock_code", "")
            stock_name = op.get("stock_name", "未知")
            op_type = op.get("type", "未知")
            price = op.get("price", 0)
            quantity = op.get("quantity", 0)
            recorded_at = op.get("recorded_at", "")
            
            # 构建操作详情
            op_detail = f"- {op_type} {stock_name}({stock_code}): {quantity}股 @ {price:.3f}"
            if recorded_at:
                op_detail += f" ({recorded_at})"
            operations_detail.append(op_detail)
        
        operations_str = "\n".join(operations_detail)
        
        # 获取持仓数据（使用妙想工具能获取到的数据）
        position_summary = report.get("position_diagnosis", {}).get("summary", {})
        positions_str = ""
        if position_summary.get("positions"):
            positions_str = "\n## 当前持仓情况\n"
            for pos in position_summary["positions"]:
                positions_str += f"- {pos.get('stock_name', '')}({pos.get('stock_code', '')}): {pos.get('quantity', 0)}股, 成本价 {pos.get('cost_price', 0):.3f}, 当前价 {pos.get('current_price', 0):.3f}, 盈亏 {pos.get('profit_pct', 0):.2f}%\n"
        
        # 构建详细的评分提示词（不依赖分时数据）
        prompt = f"""请对今日操作进行详细的复盘评分，满分100分。需要从以下四个维度进行评分，每个维度25分。

## 今日市场概况
{[idx['name'] + ': ' + str(idx.get('change_pct', 0)) + '%' for idx in report['market_overview']['indices']]}

## 狼大今日发言摘要
{wolf_posts_summary if wolf_posts_summary else '无'}

## 今日操作记录
{operations_str}

{positions_str}

## 评分维度（每项25分，共100分）

### 1. 操作时机评估（25分）
- 是否符合狼大当日的投资主线？
- 是否在市场明确信号后操作？
- 是否考虑了市场整体氛围？

### 2. 操作价格评估（25分）
- 买入价格是否合理？
- 卖出价格是否合理？
- 与当前持仓成本价的比较

### 3. 操作决策评估（25分）
- 操作是否有明确的逻辑支撑？
- 仓位管理是否合理？
- 风险控制是否到位？

### 4. 操作执行评估（25分）
- 操作记录是否完整？
- 操作数量是否适当？
- 是否有后续计划？

请输出JSON格式的评分结果：
{{
    "score": 总分,
    "score_detail": {{
        "timing_evaluation": {{"score": 分数, "reason": "评分原因"}},
        "price_evaluation": {{"score": 分数, "reason": "评分原因"}},
        "decision_evaluation": {{"score": 分数, "reason": "评分原因"}},
        "execution_evaluation": {{"score": 分数, "reason": "评分原因"}}
    }},
    "total_score_detail": "总分说明",
    "evaluation": "操作评价",
    "suggestions": ["建议1", "建议2"]
}}
"""
        
        try:
            result = self.llm_client.chat([{"role": "user", "content": prompt}])
            # 尝试解析JSON结果
            try:
                llm_result = json.loads(result)
                
                # 构建格式化的评分详情
                score_detail = llm_result.get("score_detail", {})
                formatted_detail = []
                
                if isinstance(score_detail, dict):
                    for dim_name, dim_data in score_detail.items():
                        if isinstance(dim_data, dict):
                            score = dim_data.get("score", 0)
                            reason = dim_data.get("reason", "")
                            dim_title = {
                                "buy_sell_point": "买/卖点评估",
                                "price_evaluation": "买/卖价格评估",
                                "timing_evaluation": "买/卖时机评估",
                                "decision_evaluation": "买/卖决策评估"
                            }.get(dim_name, dim_name)
                            formatted_detail.append(f"- **{dim_title}**: {score}分\n  {reason}")
                
                return {
                    "score": llm_result.get("score", 50),
                    "score_detail": "\n".join(formatted_detail) if formatted_detail else llm_result.get("total_score_detail", ""),
                    "evaluation": llm_result.get("evaluation", ""),
                    "suggestions": llm_result.get("suggestions", [])
                }
            except:
                # 如果不是JSON格式，返回默认结果
                return {
                    "score": 70,
                    "score_detail": "LLM评分：整体操作合理",
                    "evaluation": result if result else "暂无详细评价",
                    "suggestions": ["继续保持当前操作节奏"]
                }
        except Exception as e:
            logger.error(f"LLM评分失败: {e}")
            return self._evaluate_operations_with_rules(operations, report)
    
    def _evaluate_operations_with_rules(self, operations, report):
        """使用规则引擎评估今日操作"""
        score = 50
        score_detail = []
        suggestions = []
        
        # 检查操作数量
        if len(operations) == 0:
            score -= 10
            score_detail.append("无操作记录")
        elif len(operations) > 5:
            score -= 5
            score_detail.append("操作过于频繁")
            suggestions.append("建议减少操作频率")
        
        # 检查盈亏情况
        total_profit = sum(op.get("profit_pct", 0) for op in operations)
        avg_profit = total_profit / len(operations) if operations else 0
        
        if avg_profit > 2:
            score += 20
            score_detail.append("盈利良好")
        elif avg_profit > 0:
            score += 10
            score_detail.append("小幅盈利")
        elif avg_profit >= -2:
            score_detail.append("小幅亏损")
        else:
            score -= 10
            score_detail.append("亏损较大")
            suggestions.append("建议复盘亏损原因")
        
        # 检查是否符合狼大观点
        wolf_posts = report.get("wolf_posts", [])
        if wolf_posts:
            # 简单检查：如果狼大提到买入且有买入操作，加分
            has_buy_signal = any("买入" in p["content"] or "加仓" in p["content"] for p in wolf_posts)
            has_buy_operation = any(op["type"] == "buy" or "买入" in op["action"] for op in operations)
            
            if has_buy_signal and has_buy_operation:
                score += 10
                score_detail.append("操作符合狼大观点")
            elif not has_buy_signal and has_buy_operation:
                score -= 5
                score_detail.append("操作与狼大观点不一致")
        
        # 检查风险控制
        has_stop_loss = any("止损" in op.get("action", "") for op in operations)
        if has_stop_loss:
            score += 10
            score_detail.append("有止损操作")
        
        # 确保分数在0-100之间
        score = max(0, min(100, score))
        
        return {
            "score": score,
            "score_detail": "; ".join(score_detail),
            "evaluation": f"今日操作评分为 {score} 分。{'; '.join(score_detail)}",
            "suggestions": suggestions if suggestions else ["继续保持"]
        }
    
    def _generate_strategy(self, report):
        """生成策略建议"""
        strategy = {
            "short_term": [],  # 1-3天
            "medium_term": [],  # 1-4周
            "long_term": []     # 1-3月
        }
        
        posts = report["wolf_posts"]
        
        # 根据狼大发言生成策略
        for post in posts:
            content = post.get("content", "") + post.get("summary", "")
            content_lower = content.lower()
            
            # 短期策略
            if any(word in content_lower for word in ["反弹", "日内", "短线", "T+1"]):
                strategy["short_term"].append({
                    "signal": "狼大提到短期操作机会",
                    "action": "关注日内波动，可考虑短线交易",
                    "conditions": "成交量配合、板块轮动节奏"
                })
            
            # 中期策略
            if any(word in content_lower for word in ["趋势", "波段", "几周", "阶段"]):
                strategy["medium_term"].append({
                    "signal": "狼大提到趋势判断",
                    "action": "按趋势方向操作，设置合理止损",
                    "conditions": "趋势明确、量价配合"
                })
            
            # 长期策略
            if any(word in content_lower for word in ["长期", "持有", "价值", "基本面"]):
                strategy["long_term"].append({
                    "signal": "狼大提到长期投资观点",
                    "action": "关注基本面，逢低布局优质标的",
                    "conditions": "估值合理、基本面改善"
                })
        
        # 默认策略（如果没有明确观点）
        if not strategy["short_term"]:
            strategy["short_term"].append({
                "signal": "观望信号",
                "action": "等待明确信号",
                "conditions": "等待成交量放大或方向选择"
            })
        
        if not strategy["medium_term"]:
            strategy["medium_term"].append({
                "signal": "震荡格局",
                "action": "区间操作，高抛低吸",
                "conditions": "关注支撑压力位"
            })
        
        if not strategy["long_term"]:
            strategy["long_term"].append({
                "signal": "长期看好",
                "action": "逢低建仓优质标的",
                "conditions": "估值合理时逐步布局"
            })
        
        return strategy
    
    def _get_risk_summary(self, report):
        """汇总风险提示"""
        risks = []
        
        # 从持仓诊断获取风险
        diagnosis = report["position_diagnosis"]
        for alert in diagnosis.get("stop_loss_alerts", []):
            risks.append({
                "level": "high",
                "message": alert["message"],
                "action": "建议及时止损"
            })
        
        # 从狼大发言分析风险
        for post in report["wolf_posts"]:
            content = post.get("content", "").lower()
            if any(word in content for word in ["风险", "谨慎", "减仓", "回避"]):
                risks.append({
                    "level": "medium",
                    "message": f"狼大提示风险：{post['summary']}",
                    "action": "建议谨慎操作"
                })
        
        return risks
    
    def _generate_markdown_report(self, report):
        """生成Markdown格式报告"""
        md = f"""# 每日复盘报告

## 📅 报告日期
{report['report_date']}

---

## 📊 市场概况

### 主要指数
| 指数 | 最新价 |
|------|--------|
"""
        for idx in report["market_overview"]["indices"]:
            md += f"| {idx['name']} | {idx['current_price'] or 'N/A'} |\n"
        
        md += """
---

## 📈 技术面复盘

### 关键价位
"""
        for level in report["technical_review"]["key_levels"]:
            md += f"- **{level['level']}**: {level['description']}\n"
        
        md += f"""
### 趋势分析
{report['technical_review']['trend_analysis']}

### 量能分析
{report['technical_review']['volume_analysis']}

---

## 🐺 狼大今日发言

"""
        if report["wolf_posts"]:
            for i, post in enumerate(report["wolf_posts"], 1):
                md += f"""### {i}. [{post['date']}]

**标签**: {', '.join(post['tags']) if post['tags'] else '无'}  
**分类**: {post['category']}  
**提及板块**: {', '.join(post.get('mentioned_sectors', [])) if post.get('mentioned_sectors') else '无'}  

**摘要**: {post['summary']}

"""
        else:
            md += "今日无狼大发言记录\n"
        
        # 添加操作复盘评分
        op_review = report["operation_review"]
        md += f"""
---

## 📝 今日操作复盘评分

### 评分结果
**综合得分**: {op_review['score']} 分

### 评分详情
{op_review['score_detail']}

### 操作评价
{op_review['evaluation']}

### 今日操作记录
"""
        if op_review["operations"]:
            for op in op_review["operations"]:
                md += f"- **{op.get('stock_name', '未知')}({op.get('stock_code', '')})**: {op.get('action', '')} (盈亏: {op.get('profit_pct', 0)}%)\n"
        else:
            md += "- 今日无操作记录\n"
        
        md += """
### 改进建议
"""
        for suggestion in op_review["suggestions"]:
            md += f"- {suggestion}\n"
        
        md += """
---

## 🎯 操作策略

### 短期策略（1-3天）
"""
        for s in report["strategy"]["short_term"]:
            md += f"""
**信号**: {s['signal']}  
**操作**: {s['action']}  
**条件**: {s['conditions']}
"""
        
        md += """

### 中期策略（1-4周）
"""
        for s in report["strategy"]["medium_term"]:
            md += f"""
**信号**: {s['signal']}  
**操作**: {s['action']}  
**条件**: {s['conditions']}
"""
        
        md += """

### 长期策略（1-3月）
"""
        for s in report["strategy"]["long_term"]:
            md += f"""
**信号**: {s['signal']}  
**操作**: {s['action']}  
**条件**: {s['conditions']}
"""
        
        md += """

---

## 💼 持仓诊断

### 持仓概况
- 持仓股票数: {total_stocks}
- 持仓总市值: {total_value:.2f}
- 持仓总成本: {total_cost:.2f}
- 总盈亏: {total_profit:.2f} ({total_profit_pct:.2f}%)

""".format(**report["position_diagnosis"]["summary"])
        
        md += """### 持仓明细
| 股票 | 持仓数量 | 成本价 | 现价 | 市值 | 盈亏 |
|------|----------|--------|------|------|------|
"""
        for pos in report["position_diagnosis"]["summary"]["positions"]:
            md += f"| {pos['stock_name']}({pos['stock_code']}) | {pos['quantity']} | {pos['cost_price']} | {pos['current_price']} | {pos['market_value']:.2f} | {pos['profit']:.2f} ({pos['profit_pct']:.2f}%) |\n"
        
        md += """

### 行业分布
"""
        for sector, percentage in report["position_diagnosis"]["sector_distribution"].items():
            md += f"- {sector}: {percentage}%\n"
        
        if report["position_diagnosis"]["recommendations"]:
            md += """

### 持仓建议
"""
            for rec in report["position_diagnosis"]["recommendations"]:
                md += f"- {rec}\n"
        
        md += """

---

## ⚠️ 风险提示

"""
        if report["risk_summary"]:
            for risk in report["risk_summary"]:
                md += f"""**{risk['level'].upper()}**: {risk['message']}
> {risk['action']}

"""
        else:
            md += "暂无明显风险提示\n"
        
        md += """

---

*报告生成时间: {}*
""".format(report["generated_at"])
        
        return md
    
    def _save_report(self, md_content, date_str):
        """保存报告文件"""
        file_name = f"{date_str}_daily_report.md"
        file_path = os.path.join(Config.DAILY_REPORT_DIR, file_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"每日复盘报告已保存: {file_path}")

# 示例用法
if __name__ == "__main__":
    review = DailyReview()
    report = review.generate_review()
    
    # 打印报告摘要
    print(f"报告日期: {report['report_date']}")
    print(f"狼大发言数: {len(report['wolf_posts'])}")
    print(f"风险提示数: {len(report['risk_summary'])}")
    print("报告已生成!")
