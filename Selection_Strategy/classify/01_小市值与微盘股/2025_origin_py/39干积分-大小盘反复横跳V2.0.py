# 克隆自聚宽文章：https://www.joinquant.com/post/47337
# 标题：干积分-大小盘反复横跳V2.0
# 作者：MarioC

from jqdata import *
from jqfactor import *
import numpy as np
import pandas as pd
import pickle
import talib
import warnings
warnings.filterwarnings("ignore")
# 初始化函数
def initialize(context):
    # 设定基准
    set_benchmark('000985.XSHG')
    # 用真实价格交易
    set_option('use_real_price', True)
    # 打开防未来函数
    set_option("avoid_future_data", True)
    # 将滑点设置为0
    set_slippage(FixedSlippage(0))
    # 设置交易成本万分之三，不同滑点影响可在归因分析中查看
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003,
                             close_today_commission=0, min_commission=5), type='stock')
    # 过滤order中低于error级别的日志
    log.set_level('order', 'error')
    # 初始化全局变量
    g.no_trading_today_signal = False
    g.stock_num = 5
    g.hold_list = []  # 当前持仓的全部股票
    g.yesterday_HL_list = []  # 记录持仓中昨日涨停的股票
    # 设置交易运行时间
    run_daily(prepare_stock_list, '9:05')
    # run_weekly(weekly_adjustment, 1, '9:30')
    run_monthly(weekly_adjustment, 1, '9:30')
    # run_monthly(weekly_adjustment, 10, '9:30')
    # run_daily(sell_stocks, '9:30')
    run_daily(check_limit_up, '14:00')  # 检查持仓中的涨停股是否需要卖出
    run_daily(close_account, '14:30')

def sell_stocks(context):
    for stock in context.portfolio.positions.keys():
        # 股票盈利大于等于10%则卖出
        if context.portfolio.positions[stock].price >= context.portfolio.positions[stock].avg_cost * 1.40:
            order_target_value(stock, 0)
            log.debug("Selling out %s" % (stock))
        # 股票亏损大于等于-5%则卖出
        elif context.portfolio.positions[stock].price < context.portfolio.positions[stock].avg_cost * 0.95:
            order_target_value(stock, 0)
            log.debug("Selling out %s" % (stock))

# 1-1 准备股票池
def prepare_stock_list(context):
    # 获取已持有列表
    g.hold_list = []
    for position in list(context.portfolio.positions.values()):
        stock = position.security
        g.hold_list.append(stock)
    # 获取昨日涨停列表
    if g.hold_list != []:
        df = get_price(g.hold_list, end_date=context.previous_date, frequency='daily', fields=['close', 'high_limit'],
                       count=1, panel=False, fill_paused=False)
        df = df[df['close'] == df['high_limit']]
        g.yesterday_HL_list = list(df.code)
    else:
        g.yesterday_HL_list = []


    
#2-4 过滤股价高于10元的股票	
def filter_highprice_stock(context,stock_list):
	last_prices = history(1, unit='1m', field='close', security_list=stock_list)
	return [stock for stock in stock_list if stock in context.portfolio.positions.keys()
			or last_prices[stock][-1] < 10]

# 基本面筛选，并根据小市值排序
def get_peg(context,stocks):
    # 获取基本面数据
    q = query(valuation.code,
                indicator.roe,
                indicator.roa,
                ).filter(
                    indicator.roe > 0.15,
                    indicator.roa > 0.10,
                    valuation.code.in_(stocks))
    df_fundamentals = get_fundamentals(q, date = None)       
    stocks = list(df_fundamentals.code)
    # fuandamental data
    df = get_fundamentals(query(valuation.code).filter(valuation.code.in_(stocks)).order_by(valuation.market_cap.asc()))
    choice = list(df.code)
    return choice

def get_recent_limit_up_stock(context, stock_list, recent_days):
    stat_date = context.previous_date
    new_list = []
    for stock in stock_list:
        df = get_price(stock, end_date=stat_date, frequency='daily', fields=['close','high_limit'], count=recent_days, panel=False, fill_paused=False)
        df = df[df['close'] == df['high_limit']]
        if len(df) > 0:
            new_list.append(stock)
    return new_list
    
def SMALL(context):
    dt_last = context.previous_date
    stocks = get_all_securities('stock', dt_last).index.tolist()
    stocks = filter_kcbj_stock(stocks)
    choice = filter_st_stock(stocks)
    choice = filter_paused_stock(choice)
    choice = filter_new_stock(context, choice)
    choice = filter_limitup_stock(context,choice)
    choice = filter_limitdown_stock(context,choice)
    choice = filter_highprice_stock(context,choice)
    
    choice = get_peg(context,choice)
    recent_limit_up_list = get_recent_limit_up_stock(context, choice, 40)
    black_list = list(set(g.hold_list).intersection(set(recent_limit_up_list)))
    target_list = [stock for stock in choice if stock not in black_list]
    check_out_lists = target_list[:g.stock_num]
    return check_out_lists
    
def BIG(context):
    dt