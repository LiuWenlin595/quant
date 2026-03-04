# 克隆自聚宽文章：https://www.joinquant.com/post/24103
# 标题：再次抛砖
# 作者：那時花開海布裡

# 导入函数库
from jqdata import *
import numpy as np
from jqlib.technical_analysis import *
from datetime import datetime

## 初始化函数，设定基准等等
def initialize(context):
    set_params() 
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    
    ### 期货相关设定 ###
    # 设定账户为金融账户
    set_subportfolios([SubPortfolioConfig(cash=context.portfolio.starting_cash, type='index_futures')])
    # 期货类每笔交易时的手续费是：买入时万分之0.23,卖出时万分之0.23,平今仓为万分之23 注意这里平今还用的是万4.6而不是现在的万3.45
    set_order_cost(OrderCost(open_commission=0.000023, close_commission=0.000023,close_today_commission=0.0046), type='index_futures')
    # 设定保证金比例
    set_option('futures_margin_rate', 0.15)

    # 设置期货交易的滑点
    set_slippage(StepRelatedSlippage(2))
    # 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'IF8888.CCFX'或'IH1602.CCFX'是一样的）
    # 注意：before_open/open/close/after_close等相对时间不可用于有夜盘的交易品种，有夜盘的交易品种请指定绝对时间（如9：30）
    # 开盘前运行
    run_daily( before_market_open, time='09:00', reference_security='IF8888.CCFX')
    # 开盘时运行
    # run_daily( market_open, time='09:30', reference_security='IF8888.CCFX')
    # 收盘后运行
    run_daily( after_market_close, time='15:30', reference_security='IF8888.CCFX')

def set_params():
    g.nMa = 17
    g.nMaSlope =5
    g.SlopeLong = 100.2
    g.SlopeShort = 98.6
    
## 开盘前运行函数
def before_market_open(context):
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：'+str(context.current_dt.time()))

    # 给微信发送消息（添加模拟交易，并绑定微信生效）
    # send_message('美好的一天~')

    ## 获取要操作的股票(g.为全局变量)
    # 获取当月沪深300指数期货合约
    g.IF_current_month = get_future_contracts('IF')[1]
    # 获取下季沪深300指数期货合约
    g.IF_next_quarter = get_future_contracts('IF')[3]

## 开盘时运行函数
def handle_data(context, data):
    ## 交易
    hour = context.current_dt.hour
    minute = context.current_dt.minute
    # 当月合约
    IF_current_month = g.IF_current_month
    # 下季合约
    IF_next_quarter = g.IF_next_quarter
    
    if hour == 9 and minute == 31:
        signal = get_signal(context)
        log.info('signal =',signal)
        if signal == 1 and len(context.portfolio.long_positions) == 0:
            order_target_value(IF_next_quarter,context.portfolio.cash*0.25, side='long')
            log.info('多单开仓')
        elif signal == 1 and len(context.portfolio.long_positions) != 0:
            log.info('继续持有多单')
        elif signal ==-1 and len(context.portfolio.short_positions) == 0:
            order_target_value(IF_next_quarter,context.portfolio.cash*0.2, side='short')
            log.info('空单开仓')
        elif signal ==-1 and len(context.portfolio.short_positions) != 0:
            log.info('继续空单')
        elif signal == 0 and len(context.portfolio.positions) == 0:
            log.info('暂时空仓')
        elif signal == 0 and len(context.portfolio.positions) != 0:
            sell_all_long(context)
            sell_all_short(context)
            log.info('平所有仓位')
        return
    if hour == 10 and minute == 31:
        signal = get_signal(context)
        log.info('signal =',signal)
        if signal == 1 and len(context.portfolio.long_positions) == 0:
            order_target_value(IF_next_quarter,context.portfolio.cash*0.25, side='long')
            log.info('多单开仓')
        elif signal == 1 and len(context.portfolio.long_positions) != 0:
            log.info('继续持有多单')
        elif signal ==-1 and len(context.portfolio.short_positions) == 0:
            order_target_value(IF_next_quarter,context.portfolio.cash*0.2, side='short')
            log.info('空单开仓')
        elif signal ==-1 and len(context.portfolio.short_positions) != 0:
            log.info('继续空单')
        elif signal == 0 and len(context.portfolio.positions) == 0:
            log.info('暂时空仓')
        elif signal == 0 and len(context.portfolio.positions) != 0:
            sell_long_pos(context)
            sell_short_pos(context)
            log.info('平所有仓位')
        log.info('10点31分')
        return
    if hour == 11 and minute == 1:
        signal = get_signal(context)
        log.info('signal =',signal)
        if signal == 1 and len(context.portfolio.long_positions) == 0:
            order_target_value(IF_next_quarter,context.portfolio.cash*0.25, side='long')
            log.info('多单开仓')
        elif signal == 1 and len(context.portfolio.long_positions) != 0:
            log.info('继续持有多单')
        elif signal ==-1 and len(context.portfolio.short_positions) == 0:
            order_target_value(IF_next_quarter,context.portfolio.cash*0.2, side='short')
            log.info('空单开仓')
        elif signal ==-1 and len(context.portfolio.short_positions) != 0:
            log.info('继续空单')
        elif signal == 0 and len(context.portfolio.positions) == 0:
            log.info('暂时空仓')
        elif signal == 0 and len(context.portfolio.positions) != 0:
            sell_long_pos(context)
            sell_short_pos(context)
            log.info('平所有仓位')
        log.info('11点1分')
        return
    if hour == 13 and minute == 5:
        signal = get_signal(context)
        log.info('signal =',signal)
        if signal == 1 and len(context.portfolio.long_positions) == 0:
            order_target_value(IF_next_quarter,context.portfolio.cash*0.25, side='long')
            log.info('多单开仓')
        elif signal == 1 and len(context.portfolio.long_positions) != 0:
            log.info('继续持有多单')
        elif signal ==-1 and len(context.portfolio.short_positions) == 0:
            order_target_value(IF_next_quarter,context.portfolio.cash*0.2, side='short')
            log.info('空单开仓')
        elif signal ==-1 and len(context.portfolio.short_positions) != 0:
            log.info('继续空单')
        elif signal == 0 and len(context.portfolio.positions) == 0:
            log.info('暂时空仓')
        elif signal == 0 and len(context.portfolio.positions) != 0:
            sell_long_pos(context)
            sell_short_pos(context)
            log.info('平所有仓位')
        log.info('13点5分')
        return
    if hour == 13 and minute == 35:
        signal = get_signal(context)
        log.info('signal =',signal)
        if signal == 1 and len(context.portfolio.long_positions) == 0:
            order_target_value(IF_next_quarter,context.portfolio.cash*0.25, side='long')
            log.info('多单开仓')
        elif signal == 1 and len(context.portfolio.long_positions) != 0:
            log.info('继续持有多单')
        elif signal ==-1 and len(context.portfolio.short_positions) == 0:
            order_target_value(IF_next_quarter,context.portfolio.cash*0.2, side='short')
            log.info('空单开仓')
        elif signal ==-1 and len(context.portfolio.short_positions) != 0:
            log.info('继续空单')
        elif signal