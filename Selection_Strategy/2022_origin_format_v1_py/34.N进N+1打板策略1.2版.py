# 克隆自聚宽文章：https://www.joinquant.com/post/20946
# 标题：N进N+1打板策略1.2版
# 作者：修行者

# 导入函数库
from jqdata import *
from jqlib.technical_analysis import *
from jqdata import finance 
import pandas as pd
import warnings
import numpy as np
import datetime
import time
import tushare as ts

# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 为全部交易品种设定固定值滑点
    set_slippage(FixedSlippage(0.01))
    #开启盘口撮合
    set_option('match_with_order_book', True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')

    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
      # 收盘后运行
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')
    enable_profile()
    g.rest = 0  #吃大面后强制休息2天

## 开盘前运行函数
def before_market_open(context):
    print('--------------------------------新的一天：%s' % str(context.current_dt))
    data = pd.DataFrame([])
    if g.rest > 0:
        g.rest -= 1
        print('<<<<<<<<打板休息日>>>>>>>')
    else:
        data=countBoard(context)
    g.pre_close = {}
    g.dragonLeader = []
    if data.empty:
        g.security = []
    else:
        g.security = prepareStocks(data, context)
        if 'max' in g.security:
            g.security.remove('max')
        if 'code' in g.security:
            g.security.remove('code')
        for stock in g.security:
            price = attribute_history(stock, 1, unit='1d',fields=['close'],skip_paused=True, df=True, fq='pre')
            g.pre_close[stock] = price.iloc[0]['close']
    for stock in context.portfolio.positions:
        if stock not in g.security:
            g.security.append(stock)
            price = attribute_history(stock, 1, unit='1d',fields=['close'],skip_paused=True, df=True, fq='pre')
            g.pre_close[stock] = price.iloc[0]['close']
        #如果持仓股为市场最高板，那么卖点单独处理
        print(g.continuousBoard)
        if stock in g.continuousBoard.iloc[-1]['code']:
            g.dragonLeader.append(stock)
    if g.rest == 0 and (len(g.security)>0):
        subscribe(g.security, 'tick')
    if len(g.dragonLeader)>0:
        print('拿着龙头：%s' %str(g.dragonLeader))
    
## 收盘后运行函数
def after_market_close(context):
    # 取消今天订阅的标的
    unsubscribe_all()
    #得到当天所有成交记录
    trades = get_trades()
    for _trade in trades.values():
        log.info('成交记录：'+str(_trade))
    log.info('一天结束')
    log.info('##############################################################')


# 有tick事件时运行函数
'''
一个 tick 所包含的信息。 tick 中的信息是在 tick 事件发生时， 盘面的一个快照。

code: 标的的代码
datetime: tick 发生的时间
current: 最新价
high: 截至到当前时刻的最高价
low: 截至到当前时刻的最低价
volume: 截至到当前时刻的成交量
amount: 截至到当前时刻的成交额
position: 截至到当前时刻的持仓量，只适用于期货 tick 对象
a1_v ~ a5_v: 卖一量到卖五量，对于期货，只有卖一量
a1_p ~ a5_p: 卖一价到卖五价，对于期货，只有卖一价
b1_v ~ b5_v: 买一量到买五量，对于期货，只有买一量
b1_p ~ b5_p: 买一价到买五价，对于期货，只有买一价
'''
def handle_tick(context, tick):
    if len(g.security) and g.rest==0:
        hitBoard(context, tick)
    nuke(context,tick)


#暂时使用翻绿或者尾盘不涨停卖点
def nuke(context, tick):
    hour = context.current_dt.hour
    minute = context.current_dt.minute
    stock = tick.code
    if hour==9 and minute<30:
        return
    curPositions = context.portfolio.positions
    if len(curPositions) == 0 or tick.code not in curPositions\
     or curPositions[stock].closeable_amount<=0:
        return

    current_data = get_current_data()
    high_limit = current_data[stock].high_limit
    limit_low = current_data[stock].low_limit
    dayOpen =  current_data[stock].day_open
    #跌停没法卖
    if tick.current == limit_low:
        return
     #统计当天最高价
    barCnt = (hour-9)*4+int(minute/15)
    barsOf15Min = get_bars(tick.code, barCnt, unit='15m',fields=['high'],include_now=True)
    dayHigh = max(barsOf15Min['high'])
    
    isDragonLeader =len(g.dragonLeader)>0 and str(tick.code) in g.dragonLeader
    if isDragonLeader:
        dragonPrice = attribute_history(stock, 5, unit='1d',fields=[ 'close'],skip_paused=True, df=True, fq='pre')
        #6板及以上才这么卖，否则使用下面的卖法
        if dayHigh/dragonPrice.iloc[0]['close']>1.77:
            sellIfGreen(tick)
            sellIfNotBoard(tick, hour, minute, high_limit)
            return #独立卖法要return，不然就执行下面的卖法去了

    if dayOpen<curPositions[tick.code].avg_cost*0.9:
        g.rest = 2
        bigNoodlePrice = attribute_history(stock, 1, unit='1d',fields=[ 'low'],skip_paused=True, df=True, fq='pre')
        priceToSell = bigNoodlePrice.iloc[0]['low']*0.98
        if tick.current >= priceToSell or hour>14:
            print('吃大面，强制休息2天'+str(stock))
            order_target(stock, 0)
            if stock not in curPositions:
                log.info('卖出股票:' + str(stock))
        #独立卖法要return，不然就执行下面的卖法去了
        return
     #绿盘卖
    sellIfGreen(tick, curPositions)
    #最高价回撤超过4%卖
    if tick.current<=dayHigh*0.96 :
        print('最高价回撤超过4%卖'+str(stock))
        order_target(stock, 0)
        if stock not in curPositions:
            log.info('卖出股票:' + str(stock))
    #亏损超过5%止损
    if curPositions[tick.code].price<curPositions[tick.code].avg_cost*0.95:
        print('止损卖'+str(stock))
        order_target(stock, 0)
        if stock not in curPositions:
            log.info('卖出股票:' + str(stock))
    
    #收盘不涨停卖
    sellIfNotBoard(tick, hour, minute, high_limit)
    #半分钟跌幅超过3%卖，一个Tick是3秒
    tickPrice = get_ticks(stock,end_dt=tick.datetime, count=20, fields=[ 'current'])
    minMax = max(tickPrice['current'])
    if tick.current<minMax*0.97 and tick.current<dayOpen:
        print('半分钟跌幅超过3%卖'+str(stock))
        order_target(stock, 0)
        if stock not in curPositions:
            log.info('卖出股票:' + str(stock))

def sellIfGreen(tick, curPositions):
    if tick.current<g.pre_close[tick.code]:
        print('绿盘卖'+str(tick.code))
        order_target(tick.code, 0)
        if tick.code not in cur