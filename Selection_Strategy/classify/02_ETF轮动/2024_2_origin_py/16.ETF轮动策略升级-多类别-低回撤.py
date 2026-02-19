# 克隆自聚宽文章：https://www.joinquant.com/post/35959
# 标题：ETF轮动策略升级-多类别-低回撤
# 作者：宋兵乙

# 调整为每日收盘后运行计算交易信号，第二个交易日进行交易

from jqdata import *
import pandas as pd
import talib as ta
import smtplib
from email.header import Header
from email.mime.text import MIMEText

import prettytable as pt

def initialize(context):
    
    g.purchases = []
    g.sells = []
    # 设置交易参数
    set_params()
    
    set_option("avoid_future_data", True)
    set_option('use_real_price', True)      # 用真实价格交易
    set_benchmark('000300.XSHG')
    log.set_level('order', 'error')
    #
    # 将滑点设置为0
    set_slippage(FixedSlippage(0))
    # 手续费: 采用系统默认设置
    set_order_cost(OrderCost(open_tax=0, close_tax=0, \
        open_commission=0.00005, close_commission=0.00005,\
        close_today_commission=0, min_commission=0), type='stock')
        
    # 开盘前运行
    run_daily(before_market_open, time='21:00', reference_security='000300.XSHG')
 
    # 21:00 计算交易信号
    run_daily(get_signal, time='21:00')
    # 9:35 进行交易
    run_daily(ETF_trade, time='9:32')


# 设置参数
def set_params():

    g.target_market = '000300.XSHG'
    
    g.moment_period = 13                # 计算行情趋势的短期均线
    g.ma_period = 10                    # 计算行情趋势的长期均线
    
    g.type_num = 5                      # 品种数量

    g.ETF_targets =  {
        # # A股指数ETF
        '000300.XSHG':'510300.XSHG',        # 沪深300
        '399006.XSHE':'159915.XSHE',        # 创业板

        # # 国际期货
        '518880.XSHG':'518880.XSHG',        # 黄金ETF
        '501018.XSHG':'501018.XSHG',        # 南方原油
        '161226.XSHE':'161226.XSHE',        # 白银基金
        
        # # 国内期货
        '159985.XSHE':'159985.XSHE',        # 豆粕ETF
        '159981.XSHE':'159981.XSHE',        # 能源化工ETF
        '159980.XSHE':'159980.XSHE',        # 有色期货
        
        # # 全球股指
        '513100.XSHG':'513100.XSHG',        # 纳斯达克ETF
        '513030.XSHG':'513030.XSHG',        # 德国ETF
        '513520.XSHG':'513520.XSHG',        # 日经ETF
        '164824.XSHE':'164824.XSHE',        # 印度基金

        # # REITs
        '180301.XSHE':'180301.XSHE',        # 盐田港REITs
        '180801.XSHE':'180801.XSHE',        # 绿能REITs
        '180101.XSHE':'180101.XSHE',        # 蛇口产业园
        '184801.XSHE':'184801.XSHE',        # 前海REITs
    }
    
    # A股指数
    g.local_stocks  = [
        '510300.XSHG',        # 沪深300
        '159915.XSHE',        # 创业板
        
        ]
    # 全球股指
    g.global_stocks = [
        '513100.XSHG',        # 纳斯达克ETF
        '164824.XSHE',        # 印度基金
        '513030.XSHG',        # 德国ETF
        '513520.XSHG',        # 日经ETF
    ]
    # 国内期货
    g.local_futures = [
        '159980.XSHE',        # 有色期货
        '159981.XSHE',        # 能源化工ETF
        '159985.XSHE',        # 豆粕ETF
        
        ]
    # 全球期货
    g.global_futures = [
        '161226.XSHE',        # 白银基金
        '518880.XSHG',        # 黄金ETF
        '501018.XSHG',        # 南方原油
        
        ]
    # REITs
    g.REITs = [
        '180101.XSHE',        # 蛇口产业园
        '180301.XSHE',        # 盐田港REITs
        '180801.XSHE',        # 绿能REITs
        '180201.XSHE',        # 广州广河REITs
        '184801.XSHE',        # 前海REITs
        ]
    
    # 打印品种上市信息
    stocks_info = "\n股票池:\n"
    for security in g.ETF_targets.values():
        s_info = get_security_info(security)
        stocks_info += "【%s】%s 上市日期:%s\n" % (s_info.code, s_info.display_name, s_info.start_date)
    log.info(stocks_info)

def get_before_after_trade_days(date, count, is_before=True):
    """
    来自： https://www.joinquant.com/view/community/detail/c9827c6126003147912f1b47967052d9?type=1
    date :查询日期
    count : 前后追朔的数量
    is_before : True , 前count个交易日  ; False ,后count个交易日
    返回 : 基于date的日期, 向前或者向后count个交易日的日期 ,一个datetime.date 对象
    """
    all_date = pd.Series(get_all_trade_days())
    if isinstance(date, str):
        date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    if isinstance(date, datetime.datetime):
        date = date.date()