# 克隆自聚宽文章：https://www.joinquant.com/post/32183
# 标题：韶华研究之四-菲阿里四阶在T+1的短线策略应用
# 作者：韶华不负

#菲阿里四阶在优质正趋标的的运用，走T+1
#盘前选股，全A，四去，基本面过滤，前期量价面过滤(过滤暴涨)，按五/十日正趋排序
#卖出，挂限价单,昨高卖出；尾盘检查没卖出，平仓
#买入，挂限价单,昨低买入
# 导入函数库
from jqdata import *
from kuanke.wizard import *
from sklearn.linear_model import LinearRegression
from jqfactor import get_factor_values
from jqlib.technical_analysis import *
from six import BytesIO
import numpy as np
import pandas as pd 
import time

# 初始化函数，设定基准等等
def initialize(context):
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')

    set_params()    #1 设置策略参数
    set_variables() #2 设置中间变量
    set_backtest()  #3 设置回测条件
    
    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
    #run_daily(before_market_open, time='before_open')
      # 开盘时运行
    #run_daily(market_open, time='09:30')
      # 收盘时运行
    #run_daily(market_close, time='14:55')
      # 收盘后运行
    #run_daily(after_market_close, time='after_close')
    
#1 设置策略参数
def set_params():
    #设置全局参数
    #基准及票池
    g.index ='all'      #all-全A,ZZ100,HS300,ZZ800,ZZ500,ZZ1000
    g.trenddays =5      #正趋排序周期，5/10，因为T+1

#2 设置中间变量
def set_variables():
    #暂时未用，测试用全池
    g.stocknum = 2              #持仓数，0-代表全取
    g.poolnum = 1*g.stocknum    #参考池数
    #换仓间隔，也可用weekly或monthly
    g.shiftdays = 1            #换仓周期，1-每日,5-周，20-月，60-季，120-半年
    g.day_count = 0             #换仓日期计数器
    
#3 设置回测条件
def set_backtest():
    ## 设定g.index作为基准
    if g.index == 'all':
        set_benchmark('000300.XSHG')
    else:
        set_benchmark(g.index)
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    #set_option("avoid_future_data", True)
    log.set_level('order', 'error')    # 设置报错等级

## 开盘前运行函数
def before_trading_start(context):
#def before_market_open(context):
    log.info('函数运行时间(before_market_open):'+str(context.current_dt.time()))
    #初始化相关参数
    today_date = context.current_dt.date()
    lastd_date = context.previous_date
    all_data = get_current_data()
    g.poollist =[]
    g.prebuy ={}
    g.presell={}
    
    log.info('='*30)    
    log.info('%s选股,趋势周期为%s,持仓数为%s' % (g.index,g.trenddays,g.stocknum))
    
    #0，判断计数器是否开仓
    if g.day_count % g.shiftdays ==0:
        log.info('今天是换仓日，开仓')
        #2，计数器+1
        g.day_count += 1
    else:
        log.info('今天是旁观日，持仓')
        #2，计数器+1
        g.day_count += 1
        return
    
    #1.圈出原始票池，去ST去退去当日停去新(一年),其他特定过滤条件参考全局参数
    num1,num2,num3,num4=0,0,0,0    #用于过程追踪
    start_time = time.time()
    if g.index =='all':
        stocklist = list(get_all_securities(['stock']).index)   #取all
    else:
        stocklist = get_index_stocks(g.index, date = None)
    
    num1 = len(stocklist)    
    stocklist = [stockcode for stockcode in stocklist if not all_data[stockcode].paused]
    stocklist = [stockcode for stockcode in stocklist if not all_data[stockcode].is_st]
    stocklist = [stockcode for stockcode in stocklist if'退' not in all_data[stockcode].name]
    stocklist = [stockcode for stockcode in stocklist if not stockcode.startswith('688')]
    stocklist = [stockcode for stockcode in stocklist if (today_date-get_security_info(stockcode).start_date).days>365]
    stocklist = [stockcode for stockcode in stocklist if all_data[stockcode].last_price >5]

    #基本面过滤
    stocklist = financial_data_filter_dayu(stocklist, valuation.circulating_market_cap, 50)
    stocklist = financial_data_filter_qujian(stocklist, valuation.pe_ratio, (0,100))
    stocklist = financial_data_filter_qujian(stocklist, valuation.pb_ratio, (0,10))
    
    num2 = len(stocklist)
    #趋势计算并过滤,1-2-3-4为分层测试
    #0-60天负趋
    #stocklist = trend_filter(context,stocklist,60,-0.01)
    #0-60天正趋
    stocklist = trend_filter(context,stocklist,60,0.01)
    num3 = len(stocklist)
    
    #1-5天正趋>2
    g.poollist = trend_filter(context,stocklist,5,2)
    #2-5天正趋0.5-2
    #g.poollist = trend_filter(context,stocklist,5,0.5)
    #3-5天正趋>0
    #g.poollist = trend_filter(context,stocklist,5,0.01)
    #4-5天负趋-0.5--2
    #g.poollist = trend_filter(context,stocklist,5,-0.5)
    #5-5天负趋<-2
    #g.poollist = trend_filter(context,stocklist,5,-2)

    num4 = len(g.poollist)
    end_time = time.time()
    log.info('Step1，选股耗时:%.1f秒，原始票池%s只，基本面滤后%s只，60天趋势滤后%s只, 5天趋势滤后%s只' % (end_time-start_time,num1,num2,num3,num4))
    log.info('='*30)
    
    #定义prebuy和presell的set
    for stockcode in g.poollist:
        df_price = get_price(stockcode,count=1,end_date=lastd_date, frequency='daily', fields=['open','close','high','low'])
        g.prebuy[stockcode] = df_price['low'].values[-1]

    for stockcode in context.portfolio.positions:
        df_price = get_price(stockcode,count=1,end_date=lastd_date, frequency='daily', fields=['open','close','high','low'])
        g.presell[stockcode] = df_price['high'].values[-1]
        
    log.info(g.prebuy,g.