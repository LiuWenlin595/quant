# 克隆自聚宽文章：https://www.joinquant.com/post/44907
# 标题：韶华研究之十八，201系列
# 作者：韶华不负

##策略介绍
##思路，采取N天M涨停，结合人气前排，和2N天涨幅限制，再观察低开高开的收益区分
##2.10，信号收集分析后，采取201，5-2/3两种类型的优化过滤，按20日涨幅升序排序，取竞价低开的
##竞价符合条件后买入，次日开盘如果收益大于1.05卖出，否则等尾盘非停即出
##2.11 对比尾卖/五刻卖/分钟卖，尾卖最好，因为图的是再板的超额利益

##2.12，信号收集分析后，采取201，低开低涨类型，半仓轮动
##2.12，采用201低位首板低开上，次日尾盘不板卖的策略，并发布
##23/3/18,加入放量倍量过滤，回测显示20天5倍量胜率相对高效果更好，发布
##23/7/22，卖出加入量能控制，回测显示120D0.9V效果最好，发布
# 导入函数库
from jqdata import *
from kuanke.wizard import * #不能和technical_analysis共存
from six import BytesIO
from jqlib.technical_analysis  import *
from jqfactor import get_factor_values
from sklearn.linear_model import LinearRegression
import numpy as np
import pandas as pd 
import time

# 初始化函数，设定基准等等
def after_code_changed(context):
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    unschedule_all()
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
    run_daily(before_market_open, time='7:00')
      # 竞价时运行
    run_daily(call_auction, time='09:26')
      # 开盘时运行
    #run_daily(market_run, time='09:30')
    #run_daily(market_run, time='10:30')
    #run_daily(market_run, time='13:30')
    run_daily(market_run, time='14:55')
      # 收盘后运行
    #run_daily(after_market_close, time='20:00')
          # 收盘后运行
    #run_daily(after_market_analysis, time='21:00')

#1 设置策略参数
def set_params():
    #设置全局参数
    g.index ='all'          #all-zz-300-500-1000
    g.auction_open_highlimit = 0.985  #竞价开盘上限
    g.auction_open_lowlimit = 0.945 #竞价开盘下限
    g.profit_line = 1.05    #盘中的止盈门槛
    
    #买前量能过滤参数
    g.volume_control = 2    #0-默认不控制，1-周期放量控制,2-周期倍量控制,3,倍量控制(相对昨日),4-放量(240-0.9)加倍量(20-5)的最佳回测叠加
    g.volume_period = 20   #放量控制周期，240-120-90-60
    g.volume_ratio = 5    #放量控制和周期最高量的比值，0.9/0.8
    
    #持仓量能过滤参数
    g.sell_mode = 0     #0-默认尾盘非板卖，11-T日天量(240),12-T日倍量(相对周期)，13-T日倍量(相对D日)
    g.sell_vol_period = 120   #放量控制周期，240-120-90-60
    g.sell_vol_ratio = 0.9    #放量控制和周期最高量的比值，0.9/0.8
#2 设置中间变量
def set_variables():
    #暂时未用，测试用全池
    g.stocknum = 0              #持仓数，0-代表全取
    g.poolnum = 1*g.stocknum    #参考池数

    
#3 设置回测条件
def set_backtest():
    ## 设定g.index作为基准
    if g.index == 'all':
        set_benchmark('000001.XSHG')
    else:
        set_benchmark(g.index)
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    #set_option("avoid_future_data", True)
    #显示所有列
    pd.set_option('display.max_columns', None)
    #显示所有行
    pd.set_option('display.max_rows', None)
    log.set_level('order', 'error')    # 设置报错等级
    
## 开盘前运行函数
def before_market_open(context):
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：'+str(context.current_dt.time()))
    #0，预置全局参数
    today_date = context.current_dt.date()
    lastd_date = context.previous_date
    befor_date = get_trade_days(end_date=today_date, count=3)[0]
    all_data = get_current_data()
    g.poolist = []
    g.sell_list =[]
    
    num1,num2,num3,num4,num5,num6=0,0,0,0,0,0    #用于过程追踪
    
    #1，构建基准指数票池，三去+去新
    start_time = time.time()
    if g.index =='all':
        stocklist = list(get_all_securities(['stock']).index)   #取