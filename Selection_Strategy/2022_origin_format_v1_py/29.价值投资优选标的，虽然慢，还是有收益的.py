# 克隆自聚宽文章：https://www.joinquant.com/post/20963
# 标题：价值投资优选标的，虽然慢，还是有收益的
# 作者：Dr. 梨花博士

from kuanke.wizard import *
from jqdata import *
import numpy as np
import pandas as pd
import talib
import datetime

'''
================================================================================
总体回测前
================================================================================
'''
def initialize(context):


    set_backtest()
    

def process_initialize(context):
       
    # 设置参数
    set_params()
    # 设置全局变量
    set_variables()
    # 设置回测

    # 股票筛选排序初始化函数
    # 股票筛选初始化函数
    #check_stocks_initialize()
    # 股票筛选排序初始化函数
    check_stocks_sort_initialize()


# 设置参数
def set_params():
    # 设置股票池
    g.security = get_index_stocks('000300.XSHG')
    g.security_zz500 = get_index_stocks('000905.XSHG')
    g.security_gqgg = get_index_stocks('399974.XSHE')

    # 测试多头趋势的均线长度
    #g.ma_lengths = [5,10,20,60]
    g.ma_lengths = [5,10,20,60,120]
    # 测试买入回踩的均线长度
    g.test_ma_length = 10
    # 买入时回踩但必须站住的均线
    g.stand_ma_length = 20
    # 同时最多持有几支股票
    g.num_stocks = 5
    # 多头趋势天数
    g.in_trend_days = 10

    #回测及实盘交易的不同值，回测设为0，实盘为1
    #g.huice_shipan = 0
    g.huice_shipan = 1

    #不可重复买入
    g.filter_holded = False

# 2
# 设置全局变量
def set_variables():
    # 可行股票池
    g.available_stocks = []

# 3
# 设置回测
def set_backtest():
    # 一律使用真实价格
    set_option('use_real_price', True)
    # 过滤log
    log.set_level('order', 'error')
    # 设置基准
    set_benchmark('000300.XSHG')

def check_stocks_sort_initialize():
    # 总排序准则： desc-降序、asc-升序
    g.check_out_lists_ascending = 'desc'


'''
================================================================================
每日回测前
================================================================================
'''
def before_trading_start(context):
    # 设置滑点、手续费和指数成分股

    print("==========================================================================")
    print("新的一天开始了，祝君好运")
    print("优先采用多头回踩策略")
    set_slip_fee(context)



# 4
# 根据不同的时间段设置滑点与手续费并且更新指数成分股
def set_slip_fee(context):
    # 更新指数成分股
    g.security = get_index_stocks('000300.XSHG')
    g.security_zz500 = get_index_stocks('000905.XSHG')
    g.security_gqgg = get_index_stocks('399974.XSHE')

    # 将滑点设置为0
    set_slippage(PriceRelatedSlippage(0.002)) 
    # 根据不同的时间段设置手续费
    dt=context.current_dt
    
    if dt>datetime.datetime(2013,1, 1):
        set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5)) 

        
    elif dt>datetime.datetime(2011,1, 1):
        set_commission(PerTrade(buy_cost=0.001, sell_cost=0.002, min_cost=5))
            
    elif dt>datetime.datetime(2009,1, 1):
        set_commission(PerTrade(buy_cost=0.002, sell_cost=0.003, min_cost=5))
                
    else:
        set_commission(PerTrade(buy_cost=0.003, sell_cost=0.004, min_cost=5))


'''
================================================================================
每天交易时
================================================================================
'''
# 每个回测单位
def handle_data(context, data):
    
    # 选取有效股票
    g.available_stocks = get_available_stocks(context)
    # 产生卖出信号
    to_sell = sell_signal(context)
    # 卖出股票
    sell_stocks(to_sell)
    # 产生买入信号
    to_buy = buy_signal(g.available_stocks, context)
    # 买入该买的股票
    buy_stocks(to_buy,context)
    log.info("15.已执行完当日操作")
# 6
# 获取卖出信号
# 返回一list，是所有达到止盈或者止损线的股票
def sell_signal(context):

    to_sell = []
    #previous_dapan = attribute_history('000300.XSHG', 1, '1d', ['close','low'])
    #current_dapan_price = previous_dapan['close'].iloc[0]

    ##############################################################
    ##根据大盘的情况来设置不同程度的止盈止损点，当指数过高意味着投机成分加大则适当减小止盈点
    ##############################################################
    
    cut_gain_percentage=0.1
    cut_loss_percentage=0.1



    # 建立需要卖出的股票list 
    
    if len(context.portfolio.positions) == 0:
        log.info("7. 今日空仓")
    #sell_lists = []
    # 对于仓内所有股票
    for security in context.portfolio.positions:
        # 取现价
        current_price = history(1, '1m', 'close', security).iloc[0].iloc[0]
        # 获取买入平均价格
        avg_cost = context.portfolio.positions[security].avg_cost
        # 计算止盈线
        high = avg_cost * (1+ cut_gain_percentage)
        # 计算止损线
        low = avg_cost*(1-cut_loss_percentage)

        ################################################################
        #以持仓日期内的最高价计算止损线，可以尽最大可能保留已经赚取的利润
        #keep_day_range = len(get_trade_days(start_date = context.portfolio.positions[security].transact_time, end_date = context.current_dt))  
        #close_data_keepday = attribute_history(security, keep_day_range, '1d', ['close'])
        #获取持仓期间的最高价
        #max_keepday_security_close = close_data_keepday['close'].max()
        
        #log.info(security,"持有天数",keep_day_range,max_keepday_security_close)

        ##############################################################

        # 如果价格突破了止损或止盈线

        ##############################################################
        ##############################################################

        log.info("7. ",security, "现价", current_price, "成本价",avg_cost, "止盈线",high,"止损线", low)

        ##形态止损条件依次为：两只乌鸦，三只乌鸦，乌云盖顶，流星线
        if CDL2CROWS_judge(security) or CDL3BLACKCROWS_judge(security) or CDLDARKCLOUDCOVER_judge(security) :

            to_sell.append(security)
            log.info(security, "形态止损，卖出股票")
        #止损点
        elif current_price <= low :
            # 全部卖出
            to_sell.append(security)
            log.info(security,"止损平仓，卖出股票")
        #止盈点
        elif current_price >= high :
            to_sell.append(security)
            log.info(security, "止盈平仓，卖出股票")
    log.info("8. 已执行完sell signal操作")
    return(to_sell)

# 7
# 卖出函数
# 输入一list股票
# 执行卖出
def sell_stocks(to_sell):
    for security in to_sell:
        order_target(security, 0)
        log.info("已经执行卖出如下股票",security)

# 8
# 计算买入信号
# 输入所有多头趋势股票
# 返回一list，包含所有在趋势内但是踩到测量均线的股票
def buy_signal(available_stocks, context):
    
    
    signal = []
    security_list = []


    ##############################################################
    ## 两种考虑，当行情好时自然KDJ等各指数都是高位，利用多头回踩可抓住大牛
    ##############################################################


    security_list = get_in_trends(available_stocks, context)
    log.info("12.buy sinal中get in trends的股票列表security_list，应当与available_stocks一致",security_list)

    if len(security_list) == 0:
        log.info("13.未能选出可用的股票" )

    for security in security_list:
        # 获取历史收盘价
        past_prices = attribute_history(security,g.test_ma_length, '1d', 'close', skip_paused = True)
        # 计算均线
        test_ma = sum(past_prices).iloc[0] / g.test_ma_length
        # 获取