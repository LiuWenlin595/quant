# 克隆自聚宽文章：https://www.joinquant.com/post/22140
# 标题：一个简单策略，看起来还行。
# 作者：davidwan75

from kuanke.wizard import *
from jqdata import *
import numpy as np
import pandas as pd
import talib
import datetime

## 初始化函数，设定要操作的股票、基准等等
def initialize(context):
    # 设定基准
    set_benchmark('000001.XSHG')
    # 设定滑点
    set_slippage(FixedSlippage(0.02))
    # True为开启动态复权模式，使用真实价格交易
    set_option('use_real_price', True)
    # 设定成交量比例
    set_option('order_volume_ratio', 1)
    # 股票类交易手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    # 个股最大持仓比重
    g.security_max_proportion = 1
    # 选股频率
    g.check_stocks_refresh_rate = 1
    # 买入频率
    g.buy_refresh_rate = 1
    # 卖出频率
    g.sell_refresh_rate = 1
    # 最大建仓数量
    g.max_hold_stocknum = 2

    # 选股频率计数器
    g.check_stocks_days = 0
    # 买卖交易频率计数器
    g.buy_trade_days=0
    g.sell_trade_days=0
    # 获取未卖出的股票
    g.open_sell_securities = []
    # 卖出股票的dict
    g.selled_security_list={}

    # 股票筛选初始化函数
    check_stocks_initialize()
    # 股票筛选排序初始化函数
    check_stocks_sort_initialize()
    # 出场初始化函数
    sell_initialize()
    # 入场初始化函数
    buy_initialize()
    # 风控初始化函数
    risk_management_initialize()

    # 关闭提示
    log.set_level('order', 'info')

    # 运行函数
    run_daily(sell_every_day,'open') #卖出未卖出成功的股票
    run_daily(risk_management, 'every_bar') #风险控制
    run_daily(check_stocks, 'open') #选股
    run_daily(trade, 'open') #交易
    run_daily(selled_security_list_count, 'after_close') #卖出股票日期计数


## 股票筛选初始化函数
def check_stocks_initialize():
    # 是否过滤停盘
    g.filter_paused = True
    # 是否过滤退市
    g.filter_delisted = True
    # 是否只有ST
    g.only_st = False
    # 是否过滤ST
    g.filter_st = True
    # 股票池
    g.security_universe_index = ["000300.XSHG"]
    g.security_universe_user_securities = []
    # 行业列表
    g.industry_list = ["801010","801020","801030","801040","801050","801080","801110","801120","801130","801140","801150","801160","801170","801180","801200","801210","801230","801710","801720","801730","801740","801750","801760","801770","801780","801790","801880","801890"]
    # 概念列表
    g.concept_list = []

## 股票筛选排序初始化函数
def check_stocks_sort_initialize():
    # 总排序准则： desc-降序、asc-升序
    g.check_out_lists_ascending = 'desc'

## 出场初始化函数
def sell_initialize():
    # 设定是否卖出buy_lists中的股票
    g.sell_will_buy = False

    # 固定出仓的数量或者百分比
    g.sell_by_amount = None
    g.sell_by_percent = None

## 入场初始化函数
def buy_initialize():
    # 是否可重复买入
    g.filter_holded = True

    # 委托类型
    g.order_style_str = 'by_cap_mean'
    g.order_style_value = 100

## 风控初始化函数
def risk_management_initialize():
    # 策略风控信号
    g.risk_management_signal = True

    # 策略当日触发风控清仓信号
    g.daily_risk_management = True

    # 单只最大买入股数或金额
    g.max_buy_value = None
    g.max_buy_amount = None


## 卖出未卖出成功的股票
def sell_every_day(context):
    g.open_sell_securities = list(set(g.open_sell_securities))
    open_sell_securities = [s for s in context.portfolio.positions.keys() if s in g.open_sell_securities]
    if len(open_sell_securities)>0:
        for stock in open_sell_securities:
            order_target_value(stock, 0)
    g.open_sell_securities = [s for s in g.open_sell_securities if s in context.portfolio.positions.keys()]
    return

## 风控
def risk_management(context):
    ### _风控函数筛选-开始 ###
    security_stoploss(context,0.05,g.open_sell_securities)
    portfolio_stoploss(context,0.08,g.open_sell_securities)
    index_stoploss_diefu(context,2,2,g.open_sell_securities, '000300.XSHG')
    ### _风控函数筛选-结束 ###
    return

## 股票筛选
def check_stocks(context):
    if g.check_stocks_days%g.check_stocks_refresh_rate != 0:
        # 计数器加一
        g.check_stocks_days += 1
        return
    # 股票池赋值
    g.check_out_lists = get_security_universe(context, g.security_universe_index, g.security_universe_user_securities)
    # 行业过滤
    g.check_out_lists = industry_filter(context, g.check_out_lists, g.industry_list)
    # 概念过滤
    g.check_out_lists = concept_filter(context, g.check_out_lists, g.concept_list)
    # 过滤ST股票
    g.check_out_lists = st_filter(context, g.check_out_lists)
    # 过滤退市股票
    g.check_out_lists = delisted_filter(context, g.check_out_lists)
    # 财务筛选
    g.check_out_lists = financial_statements_filter(context, g.check_out_lists)
    # 行情筛选
    g.check_out_lists = situation_filter(context, g.check_out_lists)
    # 技术指标筛选
    g.check_out_lists = technical_indicators_filter(context, g.check_out_lists)
    # 形态指标筛选函数
    g.check_out_lists = pattern_recognition_filter(context, g.check_out_lists)
    # 其他筛选函数
    g.check_out_lists = other_func_filter(context, g.check_out_lists)

    # 排序
    input_dict = get_check_stocks_sort_input_dict()
    g.check_out_lists = check_stocks_sort(context,g.check_out_lists,input_dict,g.check_out_lists_ascending)

    # 计数器归一
    g.check_stocks_days = 1
    return

## 交易函数
def trade(context):
   # 初始化买入列表
    buy_lists = []

    # 买入股票筛选
    if g.buy_trade_days%g.buy_refresh_rate == 0:
        # 获取 buy_lists 列表
        buy_lists = g.check_out_lists
        # 过滤ST股票
        buy_lists = st_filter(context, buy_lists)
        # 过滤停牌股票
        buy_lists = paused_filter(context, buy_lists)
        # 过滤退市股票
        buy_lists = delisted_filter(context, buy_lists)
        # 过滤涨停股票
        buy_lists = high_limit_filter(context, buy_lists)

        ### _入场函数筛选-开始 ###
        buy_lists = [security for security in buy_lists if MACD_judge_duotou(security, 12, 26, 26)]
        ### _入场函数筛选-结束 ###

    # 卖出操作
    if g.sell_trade_days%g.sell_refresh_rate != 0:
        # 计数器加一
        g.sell_trade_days += 1
    else:
        # 卖出股票
        sell(context, buy_lists)
        # 计数器归一
        g.sell_trade_days = 1


    # 买入操作
    if g.buy_trade_days%g.buy_refresh_rate !=