import requests
import json
import logging
from config import Config

logger = logging.getLogger(__name__)

class EastMoneyAPI:
    def __init__(self):
        self.api_url = Config.MX_API_URL
        self.api_key = Config.MX_API_KEY
    
    def query(self, query_text):
        """
        调用东方财富妙想API查询金融数据
        
        :param query_text: 自然语言查询语句
        :return: API返回的JSON数据
        """
        if not self.api_key:
            logger.warning("东方财富API Key未配置，无法查询数据")
            return None
        
        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }
        
        data = {
            "toolQuery": query_text
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"东方财富API查询成功: {query_text}")
                return result
            else:
                logger.error(f"东方财富API查询失败，状态码: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"东方财富API请求异常: {e}")
            return None
    
    def get_stock_price(self, stock_code):
        """获取股票最新价"""
        return self.query(f"{stock_code} 最新价")
    
    def get_stock_quote(self, stock_code):
        """获取股票完整行情"""
        return self.query(f"{stock_code} 实时行情")
    
    def get_index_data(self, index_code):
        """获取指数数据"""
        return self.query(f"{index_code} 实时行情")
    
    def get_sector_data(self, sector_name):
        """获取板块数据"""
        return self.query(f"{sector_name} 板块行情")
    
    def get_main_funds(self, stock_code=None):
        """获取主力资金流向"""
        if stock_code:
            return self.query(f"{stock_code} 主力资金流向")
        else:
            return self.query("主力资金流向")
    
    def parse_price_from_result(self, result):
        """
        从API返回结果中解析价格数据
        
        :param result: API返回的JSON数据
        :return: 价格数值或None
        """
        if not result or "data" not in result:
            return None
        
        data = result.get("data", {})
        if data is None:
            return None
        
        table_list = data.get("dataTableDTOList", [])
        
        if not table_list:
            return None
        
        first_table = table_list[0]
        table_data = first_table.get("table", {})
        
        # 尝试从表格数据中提取价格
        for key, value in table_data.items():
            if isinstance(value, list) and len(value) > 0:
                try:
                    return float(value[0])
                except ValueError:
                    continue
        
        return None
    
    def parse_multi_price_from_result(self, result):
        """
        从API返回结果中解析多个价格数据
        
        :param result: API返回的JSON数据
        :return: 字典 {股票代码: 价格}
        """
        if not result or "data" not in result:
            return {}
        
        data = result.get("data", {})
        table_list = data.get("dataTableDTOList", [])
        prices = {}
        
        for table in table_list:
            code = table.get("code", "")
            entity_name = table.get("entityName", "")
            table_data = table.get("table", {})
            
            for key, value in table_data.items():
                if isinstance(value, list) and len(value) > 0:
                    try:
                        price = float(value[0])
                        prices[code] = {
                            "name": entity_name,
                            "price": price
                        }
                        break
                    except ValueError:
                        continue
        
        return prices

# 示例用法
if __name__ == "__main__":
    api = EastMoneyAPI()
    
    # 设置环境变量测试
    import os
    os.environ["MX_APIKEY"] = "mkt_y5OEqO1aoagzi_AmfQmbCBzQsRcVDi2GafW6QCsifj"
    
    api.api_key = os.environ["MX_APIKEY"]
    
    # 测试查询
    result = api.get_stock_price("东方财富")
    print("东方财富价格查询结果:", json.dumps(result, indent=2, ensure_ascii=False))
    
    price = api.parse_price_from_result(result)
    print("解析出的价格:", price)
