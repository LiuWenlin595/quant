# 克隆自聚宽文章：https://www.joinquant.com/post/39897
# 标题：韶华研究之十六，指数增强
# 作者：韶华不负

##策略介绍
##
# 导入函数库
from jqdata import *
from kuanke.wizard import * #不能和technical_analysis共存
from six import BytesIO
from jqlib.technical_analysis  import *
from sklearn.linear_model import LinearRegression
from scipy.stats import linregress
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
      # 开盘时运行
    run_daily(market_open, time='09:30')    
      # 收盘时运行
    #run_daily(market_close, time='14:55')
      # 收盘后运行
    #run_daily(after_market_close, time='20:00')
          # 收盘后运行
    #run_daily(after_market_analysis, time='21:00')

#1 设置策略参数
def set_params():
    ##0-设置全局参数，以及票池基准
    g.index ='000905.XSHG'  #all-zz(8&10的合集)-300-500-1000
    
    ##1-票池的辅助过滤
    g.pool_filter = 'R'    #R-过滤周期内上涨过大的
    g.indus_level = 'None' #对应I，sw_l1--申万一级；sw_l2--申万二级
    g.drop_line = 0      #针对过滤D，回调线0.75-0.8
    g.drop_days = 0       #针对过滤D，回调周期10-20
    g.rise_uplimit = 1.5    #针对过滤R，2-1.5-1.2
    
    ##2-票池的主要筛选策略
    g.strategy = 'T'       #T-Trend，采用斜线拟合斜率，
    g.fields_name = 'close'     #源数据取close/avg或其他
    g.short_duration = 20   #趋势和涨幅过滤周期
    
    #趋势策略的斜率上下限
    g.trend_up = 999
    g.trend_down = 0
    
    ##3-个股的损失控制部分
    g.lostcontrol = 2      #对持仓标的是否做卖出判断，0-不做，1-净损，2-回调，3-趋势止损，4-均线止损，5-RSI；6-MACD死叉止损；7-BOLL中轨止损；10-系统止损
    g.drop_line = 0.75      #针对损控1-止损，0.9/0.85、0.8;损控2-回调，0.8/0.75/0.7
    g.drop_ma_days = 20     #针对损控2/4/5/7/8，10-20-30
    g.drop_trend_dura = 0  #针对损控3-趋势止损，10-20
    g.drop_rsi_value = 50    #针对损控5的RSI阈值，35-40-45-50-55
    
#2 设置中间变量
def set_variables():
    #暂时未用，测试用全池
    g.stocknum = 5             #持仓数，0-代表全取
    g.poolnum = 0.3    #参考池数,小于1代表着取总池的百分比
    #换仓间隔，也可用weekly或monthly，暂时没启用
    g.shiftdays = 1            #换仓周期，5-周，20-月，60-季，120-半年
    g.day_count = 0             #换仓日期计数器
    
#3 设置回测条件
def set_backtest():
    ## 设定g.index作为基准
    if g.index == 'all':
        set_benchmark('000001.XSHG')
    else:
        set_benchmark(g.index)
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    set_option("avoid_future_data", True)
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
    all_data = get_current_data()
    induslist =[]
    g.poollist=[]
    g.buylist =[]
    g.selllist=[]
    
    #止损控制
    if g.lostcontrol !=0:
        holdlist = list(context.portfolio.positions)
        g.selllist = lost_control(context, holdlist, today_date)
        log.info('%s损控-%s卖出:' % (today_date,g.lostcontrol))
        log.info(g.selllist)
        
        #此处用于每日筛选时，满仓无损跳过
        """
        if (len(holdlist)-len(g.selllist))>=g.stocknum:
            log.info('满仓无损，不用选后备')
            return
        """
    
    #0，判断计数器是否开仓
    if (g.day_count % g.shiftdays ==0):
        log.info('今天是换仓日，开仓')
        g.adjustpositions = True
        g.day_count += 1
    else:
        log.info('今天是旁观日，持仓')
        g.day_count += 1
        g.adjustpositions = False
        return
    
    num1,num2,num3,num4=0,0,0,0    #用于过程追踪

    
    #1，构建基准指数票池，三去+去新
    start_time = time.time()
    if g.index =='all':
        stocklist = list(get_all_securities(['stock']).index)   #取all
    elif g.index == 'zz':
        stocklist = get_index_stocks('000300.XSHG', date = None) + get_index_stocks('000905.XSHG', date = None) + get_index_stocks('000852.XSHG', date = None)
    else:
        stocklist = get_index_stocks(g.index, date = None)
    
    num1 = len(stocklist)    
    stocklist = [stockcode for stockcode in stocklist if not all_data[stockcode].paused]
    stocklist = [stockcode for stockcode in stocklist if not all_data[stockcode].is_st]
    stocklist = [stockcode for stockcode in stocklist if'退' not in all_data[stockcode].name]
    stocklist = [stockcode for stockcode in stocklist if (today_date-get_security_info(stockcode).start_date).days>365]
    num2 = len(stocklist)

    end_time = time.time()
    print('Step1,基准%s,原始%d只,四去后共%d只,构建耗时:%.1f 秒' % (g.index,num1,num2,end_time-start_time))
    
    #2，筛选出主策略周期内符合要求的候选标的
    start_time = time.time()
    if g.strategy == 'T':
        stocklist = get_trend_filter(context,stocklist,lastd_date,g.short_duration,'1d',g.trend_up,g.trend_down)
        
    num3 = len(stocklist)
    end_time = time