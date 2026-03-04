# 克隆自聚宽文章：https://www.joinquant.com/post/16352
# 标题：基本面单因子测试——以BP因子为例
# 作者：K线放荡不羁

# 单因子选股模型
# 先导入所需要的程序包

import datetime
import numpy as np
import pandas as pd
import time
from jqdata import *
from pandas import Series, DataFrame
import statsmodels.api as sm
from jqfactor import get_factor_values



'''
================================================================================
总体回测前
================================================================================
'''

#总体回测前要做的事情（永远不变的）
def initialize(context):
    set_params()    #1 设置策参数
    set_variables() #2 设置中间变量
    set_backtest()  #3 设置回测条件

#1 设置策略参数
def set_params():
    # 单因子测试时g.factor不应为空
    g.factor = 'BP'        # 当前回测的单因子
    g.shift = 21           # 设置一个观测天数（天数）
    g.precent = 0.10       # 持仓占可选股票池比例
    g.index='000906.XSHG'  # 定义股票池，中证800
    # 多因子合并称DataFrame，单因子测试时可以把无用部分删除提升回测速度
    # 定义因子以及排序方式，默认False方式为降序排列，原值越大sort_rank排序越小
    g.factors = {'BP': False, 'net_profit_increase':True,'inc_net_profit_year_on_year':True,'operating_profit':True,
    'inc_revenue_year_on_year':True
    }
    # 设定选取sort_rank： True 为最大，False 为最小
    g.sort_rank = True
    g.quantile = (0, 10)
'''
000906.XSHG
中证800
'''

#2 设置中间变量
def set_variables():
    g.feasible_stocks = []  # 当前可交易股票池
    g.if_trade = False      # 当天是否交易
    g.num_stocks = 0        # 设置持仓股票数目

    
#3 设置回测条件
def set_backtest():
    set_benchmark('000906.XSHG')       # 设置为基准
    set_option('use_real_price', True) # 用真实价格交易
    log.set_level('order', 'error')    # 设置报错等级

'''
================================================================================
每天开盘前
================================================================================
'''
#每天开盘前要做的事情
def before_trading_start(context):
    # 获得当前日期
    day = context.current_dt.day
    yesterday = context.previous_date
    rebalance_day = shift_trading_day(yesterday, 1)
    if yesterday.month != rebalance_day.month:
        if yesterday.day > rebalance_day.day:
            g.if_trade = True 
            #5 设置可行股票池：获得当前开盘的股票池并剔除当前或者计算样本期间停牌的股票
            g.feasible_stocks = set_feasible_stocks(get_index_stocks(g.index), g.shift,context)
    		#6 设置滑点与手续费
            set_slip_fee(context)
            # 购买股票为可行股票池对应比例股票
            g.num_stocks = int(len(g.feasible_stocks)*g.precent)

#4
# 某一日的前shift个交易日日期 
# 输入：date为datetime.date对象(是一个date，而不是datetime)；shift为int类型
# 输出：datetime.date对象(是一个date，而不是datetime)
def shift_trading_day(date,shift):
    # 获取所有的交易日，返回一个包含所有交易日的 list,元素值为 datetime.date 类型.
    tradingday = get_all_trade_days()
    # 得到date之后shift天那一天在列表中的行标号 返回一个数
    shiftday_index = list(tradingday).index(date)+shift
    # 根据行号返回该日日期 为datetime.date类型
    return tradingday[shiftday_index]

#5    
# 设置可行股票池
# 过滤掉当日停牌的股票,且筛选出前days天未停牌股票
# 输入：stock_list为list类型,样本天数days为int类型，context（见API）
# 输出：list=g.feasible_stocks
def set_feasible_stocks(stock_list,days,context):
    # 得到是否停牌信息的dataframe，停牌的1，未停牌得0
    suspened_info_df = get_price(list(stock_list), 
                       start_date=context.current_dt, 
                       end_date=context.current_dt, 
                       frequency='daily', 
                       fields='paused'
    )['paused'].T
    # 过滤停牌股票 返回dataframe
    unsuspened_index = suspened_info_df.iloc[:,0]<1
    # 得到当日未停牌股票的代码list:
    unsuspened_stocks = suspened_info_df[unsuspened_index].index
    # 进一步，筛选出前days天未曾停牌的股票list:
    feasible_stocks = []
    current_data = get_current_data()
    for stock in unsuspened_stocks:
        if sum(attribute_history(stock, 
                                 days, 
                                 unit = '1d',
                                 fields = ('paused'), 
                                 skip_paused = False
                                )
            )[0] == 0:
            feasible_stocks.append(stock)
    #剔除ST股
    st_data = get_extras('is_st', feasible_stocks, end_date = context.previous_date, count = 1)
    stockList = [stock for stock in feasible_stocks if not st_data[stock][0]]
    return stockList
    
#6 根据不同的时间段设置滑点与手续费(永远不变的函数)
def set_slip_fee(context):
    # 将滑点设置为0
    set_slippage(FixedSlippage(0)) 
    # 根据不同的时间段设置手续费
    dt=context.current_dt
    
    if dt>datetime.datetime(2013,1, 1):
        set_commission(PerTrade(buy_cost=0.0003, 
                                sell_cost=0.0013, 
                                min_cost=5)) 
        
    elif dt>datetime.datetime(2011,1, 1):
        set_commission(PerTrade(buy_cost=0.001, 
                                sell_cost=0.002, 
                                min_cost=5))
            
    elif dt>datetime.datetime(2009,1, 1):
        set_commission(PerTrade(buy_cost=0.002, 
                                sell_cost=0.003, 
                                min_cost=5))
                
    else:
        set_commission(PerTrade(buy_cost=0.003, 
                                sell_cost=0.004, 
                                min_cost=5))
'''
================================================================================
每天交易时
================================================================================
'''
def handle_data(context,data):
	# 如果为交易日
    if g.if_trade == True: 
	    #7 获得买入卖出信号，输入context，输出股票列表list
	    # 字典中对应默认值为false holding_list筛选为true，则选出因子得分最大的
        holding_list = get_stocks(g.feasible_stocks, 
                                context,
                                asc = g.sort_rank)
        # 新加入的部分，计算holding_list长度
        total_number = len(holding_list)
        # print 'feasible_stocks is %d, holding is %d' %(len(g.feasible_stocks), total_number)
        # 提取需要的分位信息
        (start_q, end_q) =  g.quantile
        #8 重新调整仓位，输入context,使用信号结果holding_list
        rebalance(context, holding_list, start_q, end_q, total_number)
	g.if_trade = False

#7 原始数据重提取因子打分排名（核心逻辑）
def get_stocks(stocks_list, context, asc):
    #   构建一个新的字符串，名字叫做 'get_df_'+ 'key'
    tmp='get_df' + '_' + g.factor
    # 声明字符串是个方程
    aa = globals()[tmp](stocks_list, context, g.factors[g.factor])
    #3倍标准差去极值
    #aa = winsorize(aa,g.factor,std = 3,have_negative = True)
    #z标准化
    #aa = standardize(aa,g.factor,ty = 2)
    #获取市值因子
    #cap_data = get_market_cap(context)
    #市值中性化
    #factor_residual_data = neutralization(aa,g.factor,cap_data)
    #删除nan，以备数据中某项没有产生nan
    #aa = aa[pd.notnull(aa['BP'])]
    # 生成排名序数
    #aa['BP_sorted_rank'] = aa['BP'].rank(ascending = asc, method = 'dense')
    score = g.factor + '_' + 'sorted_rank'
    stocks = list(aa.sort(score, ascending = asc).index)
    print stocks
    return stocks

#8
# 依本策略的买入信号，得到应该买的股票列表
# 借用买入信号结果，不需额外输入
# 输入：context（见API）
def rebalance(context, holding_list, start_q, end_q, total