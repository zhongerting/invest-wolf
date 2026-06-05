import os
import re
import subprocess
import shutil
from datetime import datetime, timedelta
from collections import defaultdict
import schedule
import time
import logging
import argparse

# 导入新模块
from .config import Config
from .knowledge_base import KnowledgeBase
from .positions import PositionManager
from .intraday_analysis import IntradayAnalyzer
from .daily_review import DailyReview

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 初始化模块
kb = KnowledgeBase()
pm = PositionManager()
analyzer = IntradayAnalyzer()
review = DailyReview()


def get_half_month_period(date):
    """根据日期返回半个月时间段"""
    year = date.year
    month = date.month
    day = date.day
    
    if day <= 15:
        start = datetime(year, month, 1)
        end = datetime(year, month, 15)
    else:
        start = datetime(year, month, 16)
        next_month = start.replace(day=28) + timedelta(days=4)
        end = next_month.replace(day=1) - timedelta(days=1)
    
    return start, end


def get_period_filename(start_date, end_date):
    """生成时间段文件名"""
    return f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}_nga_master_posts.md"


def get_daily_filename(date):
    """生成每日备份文件名"""
    return f"{date.strftime('%Y%m%d')}_daily_nga_master_posts.md"


def parse_posts_from_file(file_path):
    """解析md文件中的帖子，返回帖子列表"""
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    post_pattern = re.compile(
        r'^##### <span id="pid\d+">(\d+)\.\[\d+\] \\<pid:\d+\\> (\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2} by .+?</span>',
        re.MULTILINE
    )
    
    matches = list(post_pattern.finditer(content))
    posts = []
    
    for i, match in enumerate(matches):
        start = match.start()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(content)
        
        post_content = content[start:end]
        post_num = int(match.group(1))
        post_date_str = match.group(2)
        post_date = datetime.strptime(post_date_str, "%Y-%m-%d")
        
        posts.append({
            'num': post_num,
            'date': post_date,
            'date_str': post_date_str,
            'content': post_content,
            'start': start,
            'end': end
        })
    
    return posts


def get_existing_max_post_num():
    """获取现有分割文件中最大的帖子编号"""
    max_num = 0
    pattern = re.compile(r'^(\d{8})-(\d{8})_nga_master_posts\.md$')
    
    for filename in os.listdir(Config.BASE_DIR):
        if pattern.match(filename):
            file_path = os.path.join(Config.BASE_DIR, filename)
            posts = parse_posts_from_file(file_path)
            for post in posts:
                if post['num'] > max_num:
                    max_num = post['num']
    
    return max_num


def run_ngapost2md():
    """运行ngapost2md工具爬取最新内容"""
    logger.info("开始运行 ngapost2md 爬取...")
    
    env = os.environ.copy()
    env['PATH'] = Config.TOOL_DIR + ';' + env.get('PATH', '')
    
    try:
        result = subprocess.run(
            [Config.TOOL_EXE, str(Config.TID), "--authorid", str(Config.AUTHOR_ID)],
            cwd=Config.TOOL_DIR,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=300,
            env=env
        )
        
        if result.returncode != 0:
            logger.error(f"ngapost2md 执行失败: {result.stderr}")
            return False
        
        logger.info("ngapost2md 执行成功")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("ngapost2md 执行超时")
        return False
    except Exception as e:
        logger.error(f"执行 ngapost2md 异常: {e}")
        return False


def find_latest_posts_file():
    """找到ngapost2md生成的最新输出文件"""
    tid_folder = os.path.join(Config.TOOL_DIR, str(Config.TID))
    if os.path.isdir(tid_folder):
        for filename in os.listdir(tid_folder):
            if filename.endswith('.md'):
                return os.path.join(tid_folder, filename)
    
    tid_author_folder = os.path.join(Config.TOOL_DIR, f"{Config.TID}({Config.AUTHOR_ID})")
    if os.path.isdir(tid_author_folder):
        for filename in os.listdir(tid_author_folder):
            if filename.endswith('.md'):
                return os.path.join(tid_author_folder, filename)
    
    output_pattern = re.compile(r'^' + str(Config.TID) + r'(_.*)?\.md$')
    for filename in os.listdir(Config.TOOL_DIR):
        if output_pattern.match(filename):
            return os.path.join(Config.TOOL_DIR, filename)
    
    output_file = os.path.join(Config.TOOL_DIR, f"{Config.TID}.md")
    if os.path.exists(output_file):
        return output_file
    
    for filename in os.listdir(Config.TOOL_DIR):
        if filename.endswith('.md') and filename != 'README.md':
            file_path = os.path.join(Config.TOOL_DIR, filename)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(500)
                if f'pid:' in content or 'UID:150058' in content:
                    return file_path
    
    return None


def merge_new_posts(mode='normal'):
    """
    合并新增帖子到分割文件，并进行分析
    
    mode: 
      - 'normal': 按半个月分割存储
      - 'daily': 存储到当日daily文件
    """
    latest_file = find_latest_posts_file()
    
    if not latest_file or not os.path.exists(latest_file):
        logger.warning("未找到 ngapost2md 输出文件")
        return
    
    existing_max = get_existing_max_post_num()
    new_posts = parse_posts_from_file(latest_file)
    
    truly_new = [p for p in new_posts if p['num'] > existing_max]
    
    if not truly_new:
        logger.info("没有新增帖子需要处理")
        return
    
    logger.info(f"发现 {len(truly_new)} 条新增帖子")
    
    # 盘中分析每条新帖子
    for post in truly_new:
        analyzer.analyze_new_post(post['num'], post['date'], post['content'])
    
    if mode == 'daily':
        today = datetime.now()
        daily_file = os.path.join(Config.BASE_DIR, get_daily_filename(today))
        
        header = get_file_header()
        
        if not os.path.exists(daily_file):
            with open(daily_file, 'w', encoding='utf-8') as f:
                f.write(header + "\n")
        
        with open(daily_file, 'a', encoding='utf-8') as f:
            for post in truly_new:
                f.write(post['content'])
        
        logger.info(f"已写入当日备份文件: {daily_file}")
    
    else:
        posts_by_period = defaultdict(list)
        for post in truly_new:
            period = get_half_month_period(post['date'])
            posts_by_period[period].append(post)
        
        header = get_file_header()
        
        for period, posts in posts_by_period.items():
            start_date, end_date = period
            filename = get_period_filename(start_date, end_date)
            file_path = os.path.join(Config.BASE_DIR, filename)
            
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(header + "\n")
            
            with open(file_path, 'a', encoding='utf-8') as f:
                for post in posts:
                    f.write(post['content'])
            
            logger.info(f"已写入分割文件: {filename} ({len(posts)} 条)")
    
    update_master_posts(truly_new)


def get_file_header():
    """获取文件头部内容"""
    return """### 自立自强，科学技术打头阵-只看 150058

Made by ngapost2md (c) ludoux [GitHub Repo](https://github.com/ludoux/ngapost2md)

----
"""


def update_master_posts(new_posts):
    """更新主文件 nga_master_posts.md"""
    if not os.path.exists(Config.MASTER_POSTS_FILE):
        with open(Config.MASTER_POSTS_FILE, 'w', encoding='utf-8') as f:
            f.write(get_file_header() + "\n")
    
    with open(Config.MASTER_POSTS_FILE, 'a', encoding='utf-8') as f:
        for post in new_posts:
            f.write(post['content'])
    
    logger.info(f"已更新主文件: {Config.MASTER_POSTS_FILE}")


def job盘中爬取():
    """盘中定时爬取任务（9:30-11:30, 13:00-15:00）"""
    now = datetime.now()
    current_time = now.strftime('%H:%M')
    
    trading_hours_1 = (Config.MORNING_START, Config.MORNING_END)
    trading_hours_2 = (Config.AFTERNOON_START, Config.AFTERNOON_END)
    
    is_trading = (current_time >= trading_hours_1[0] and current_time <= trading_hours_1[1]) or \
                 (current_time >= trading_hours_2[0] and current_time <= trading_hours_2[1])
    
    if not is_trading:
        logger.info(f"当前时间 {current_time} 不在交易时段，跳过")
        return
    
    logger.info(f"=== 盘中爬取开始 ({current_time}) ===")
    
    if run_ngapost2md():
        merge_new_posts(mode='normal')
    
    logger.info("=== 盘中爬取完成 ===")


def job晚间爬取():
    """晚间爬取任务（23:00）"""
    logger.info("=== 晚间爬取开始 (23:00) ===")
    
    if run_ngapost2md():
        merge_new_posts(mode='normal')
    
    logger.info("=== 晚间爬取完成 ===")


def job每日备份():
    """每日0:00备份任务"""
    logger.info("=== 每日备份开始 (00:00) ===")
    
    if run_ngapost2md():
        merge_new_posts(mode='daily')
    
    logger.info("=== 每日备份完成 ===")


def job每日复盘():
    """每日复盘任务（23:30）"""
    logger.info("=== 每日复盘开始 (23:30) ===")
    
    try:
        review.generate_review()
        logger.info("=== 每日复盘完成 ===")
    except Exception as e:
        logger.error(f"每日复盘执行异常: {e}")


def setup_schedule():
    """配置定时任务"""
    schedule.every(Config.NGA_MONITOR_INTERVAL_MINUTES).minutes.do(job盘中爬取)
    
    schedule.every().day.at(Config.EVENING_ANALYSIS_TIME).do(job晚间爬取)
    
    schedule.every().day.at(Config.DAILY_REPORT_TIME).do(job每日备份)
    
    schedule.every().day.at("23:30").do(job每日复盘)
    
    logger.info("定时任务已配置:")
    logger.info(f"  - 盘中爬取: 每{Config.NGA_MONITOR_INTERVAL_MINUTES}分钟检查（{Config.MORNING_START}-{Config.MORNING_END}, {Config.AFTERNOON_START}-{Config.AFTERNOON_END}执行）")
    logger.info(f"  - 晚间爬取: 每日{Config.EVENING_ANALYSIS_TIME}")
    logger.info(f"  - 每日备份: 每日{Config.DAILY_REPORT_TIME}")
    logger.info("  - 每日复盘: 每日23:30")


def run_once(mode='normal'):
    """单次运行（不启动定时任务）"""
    logger.info("=== 单次运行开始 ===")
    
    if run_ngapost2md():
        merge_new_posts(mode=mode)
    
    logger.info("=== 单次运行完成 ===")


def run_review():
    """单独运行每日复盘"""
    logger.info("=== 单独运行每日复盘 ===")
    review.generate_review()
    logger.info("=== 每日复盘完成 ===")


def show_positions():
    """显示当前持仓"""
    summary = pm.get_portfolio_summary()
    logger.info("=== 当前持仓 ===")
    logger.info(f"持仓股票数: {summary['total_stocks']}")
    logger.info(f"持仓总市值: {summary['total_value']:.2f}")
    logger.info(f"持仓总成本: {summary['total_cost']:.2f}")
    logger.info(f"总盈亏: {summary['total_profit']:.2f} ({summary['total_profit_pct']:.2f}%)")
    
    for pos in summary['positions']:
        logger.info(f"- {pos['stock_name']}({pos['stock_code']}): {pos['quantity']}股 @ {pos['cost_price']}, 当前价: {pos['current_price']}, 盈亏: {pos['profit']:.2f} ({pos['profit_pct']:.2f}%)")


def add_position_cli(args):
    """添加持仓"""
    pm.add_position(
        stock_code=args.code,
        stock_name=args.name,
        quantity=int(args.quantity),
        cost_price=float(args.price),
        reason=args.reason
    )
    logger.info(f"已添加持仓: {args.name}({args.code}) {args.quantity}股 @ {args.price}")


def sell_position_cli(args):
    """卖出持仓"""
    success = pm.sell_position(
        stock_code=args.code,
        quantity=int(args.quantity)
    )
    if success:
        logger.info(f"已卖出 {args.code} {args.quantity}股")
    else:
        logger.error(f"卖出失败")


def main():
    parser = argparse.ArgumentParser(description='NGA狼大发言智能分析系统')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 爬取相关命令
    crawl_parser = subparsers.add_parser('crawl', help='爬取相关操作')
    crawl_parser.add_argument('--once', action='store_true', help='单次运行')
    crawl_parser.add_argument('--daily', action='store_true', help='单次运行并存储到daily文件')
    crawl_parser.add_argument('--schedule', action='store_true', help='启动定时任务模式')
    
    # 复盘命令
    review_parser = subparsers.add_parser('review', help='生成每日复盘')
    
    # 持仓管理命令
    position_parser = subparsers.add_parser('position', help='持仓管理')
    position_subparsers = position_parser.add_subparsers(dest='position_cmd')
    
    # 查看持仓
    position_subparsers.add_parser('list', help='查看持仓')
    
    # 添加持仓
    add_parser = position_subparsers.add_parser('add', help='添加持仓')
    add_parser.add_argument('--code', required=True, help='股票代码')
    add_parser.add_argument('--name', required=True, help='股票名称')
    add_parser.add_argument('--quantity', required=True, help='持仓数量')
    add_parser.add_argument('--price', required=True, help='成本价')
    add_parser.add_argument('--reason', default='', help='买入理由')
    
    # 卖出持仓
    sell_parser = position_subparsers.add_parser('sell', help='卖出持仓')
    sell_parser.add_argument('--code', required=True, help='股票代码')
    sell_parser.add_argument('--quantity', required=True, help='卖出数量')
    
    args = parser.parse_args()
    
    if args.command == 'crawl':
        if args.once:
            mode = 'daily' if args.daily else 'normal'
            run_once(mode=mode)
        elif args.schedule:
            setup_schedule()
            logger.info("定时任务已启动，按 Ctrl+C 停止...")
            try:
                while True:
                    schedule.run_pending()
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("定时任务已停止")
        else:
            crawl_parser.print_help()
    
    elif args.command == 'review':
        run_review()
    
    elif args.command == 'position':
        if args.position_cmd == 'list':
            show_positions()
        elif args.position_cmd == 'add':
            add_position_cli(args)
        elif args.position_cmd == 'sell':
            sell_position_cli(args)
        else:
            position_parser.print_help()
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
