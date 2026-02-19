# 克隆自聚宽文章：https://www.joinquant.com/post/44880
# 标题：5年12倍-小市值
# 作者：道尘

#导入函数库
from jqdata import *
from jqfactor import get_factor_values
from jqlib.technical_analysis import *
import numpy as np
import pandas as pd
import statsmodels.api as sm
import datetime as dt

#初始化函数 
def initialize(context):
    # 设定基准
    set_benchmark('000905.XSHG')
    # 用真实价格交易
    set_option('use_real_price', True)
    # 打开防未来函数
    set_option("avoid_future_data", True)
    # 交易量限制
    set_option('order_volume_ratio', 1)
    # 将滑点设置为0，不同滑点影响可在归因分析中查看
    set_slippage(PriceRelatedSlippage(0.002),type='stock')
    # 设置交易成本万一免五
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0001, close_commission=0.0001, close_today_commission=0, min_commission=0.1),type='fund')
    # 过滤order中低于error级别的日志
    log.set_level('order', 'error')
    #初始化全局变量
    g.stock_num = 9
    g.limit_up_list = [] #记录持仓中涨停的股票
    g.hold_list = [] #当前持仓的全部股票
    g.history_hold_list = [] #过去一段时间内持仓过的股票
    g.not_buy_again_list = [] #最近买过且涨停过的股票一段时间内不再买入
    g.limit_days = 10 #不再买入的时间段天数
    g.target_list = [] #开盘前预操作股票池
    # 设置交易运行时间
    run_daily(prepare_stock_list, time='9:05', reference_security='000300.XSHG')
    run_weekly(weekly_adjustment, weekday=1, time='9:30', reference_security='000300.XSHG')
    run_daily(check_limit_up, time='14:00', reference_security='000300.XSHG') #检查持仓中的涨停股是否需要卖出
    run_daily(print_position_info, time='15:10', reference_security='000300.XSHG')

def after_code_changed(context):
    unschedule_all()
    run_daily(prepare_stock_list, time='9:05', reference_security='000300.XSHG')
    run_weekly(weekly_adjustment, weekday=1, time='9:30', reference_security='000300.XSHG')
    run_daily(check_limit_up, time='14:00', reference_security='000300.XSHG') #检查持仓中的涨停股是否需要卖出
    run_daily(print_position_info, time='15:10', reference_security='000300.XSHG')

#1-1 选股模块
def get_factor_filter_list(context,stock_list,jqfactor,sort,p1,p2):
    yesterday = context.previous_date
    score_list = get_factor_values(stock_list, jqfactor, end_date=yesterday, count=1)[jqfactor].iloc[0].tolist()
    df = pd.DataFrame(columns=['code','score'])
    df['code'] = stock_list
    df['score']