# 克隆自聚宽文章：https://www.joinquant.com/post/21268
# 标题：期货macd简单择时，atp止损
# 作者：伊玛目的门徒

# 导入函数库
from jqdata import *
import numpy as np
import talib
import time

## 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('AG9999.XSGE')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')

    g.sign=0

    ### 期货相关设定 ###
    # 设定账户为金融账户
    set_subportfolios([SubPortfolioConfig(cash=context.portfolio.starting_cash, type='index_futures')])
    # 期货类每笔交易时的手续费是：买入时万分之0.23,卖出时万分之0.23,平今仓为万分之23
    set_order_cost(OrderCost(open_commission=0.000023, close_commission=0.000023,close_today_commission=0.0023), type='index_futures')
    # 设定保证金比例
    set_option('futures_margin_rate', 0.15)

    # 设置期货交易的滑点
    set_slippage(StepRelatedSlippage(2))
    # 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'IF8888.CCFX'或'IH1602.CCFX'是一样的）
    # 注意：before_open/open/close/after_close等相对时间不可用于有夜盘的交易品种，有夜盘的交易品种请指定绝对时间（如9：30）
    # 开盘前运行
    run_daily( before_market_open, time='09:00', reference_security='AG9999.XSGE')


    # 收盘后运行
    run_daily( after_market_close, time='15:30', reference_security='AG9999.XSGE')
    
    g.stockkind='AG'
    g.stockcode=str(g.stockkind+'9999.XSGE')
    #g.stockkind='AU'
    #g.stockkind='RB'
    

## 开盘前运行函数
def before_market_open(context):
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：'+str(context.current_dt.time()))

    # 给微信发送消息（添加模拟交易，并绑定微信生效）
    # send_message('美好的一天~')

    ## 获取要操作的股票(g.为全局变量)
      # 获取当月沪深300指数期货合约
    g.IF_current_month = get_future_contracts(g.stockkind)[0]
      # 获取下季沪深300指数期货合约
    g.IF_next_quarter = get_future_contracts(g.stockkind)[2]
    
    IF_current_month=g.IF_current_month
    IF_next_quarter=g.IF_next_quarter
    # 合约列表
    # 当月合约价格
    IF_current_month_close = get_bars(IF_current_month, count=1, unit='1d', fields=['close'])["close"]
    # 下季合约价格
    IF_next_quarter_close = get_bars(IF_next_quarter, count=1, unit='1d', fields=['close'])["close"]
    #买入信号
    g.sign=0
    #当日清仓标志
    g.clear=0


## 开盘时运行函数
def handle_data(context,data):
    
    log.info('函数运行时间(market_open):'+str(context.current_dt.time()))
    
    timeArray = context.current_dt.time().strftime('%H:%M:%S')
    #timeArray = time.strptime(context.current_dt.time(), "%H:%M:%S")
    clocktime=int(str(timeArray)[-5:-3])
    
    if clocktime % 5 == 0:  
        deal(context)
    else:
        pass

def deal(context):
    ## 交易

    # 当月合约
    IF_current_month = g.IF_current_month
    # 下季合约
    IF_next_quarter = g.IF_next_quarter

  

    # 获取当月合约交割日期
    end_data = get_CCFX_end_date(IF_current_month)
    
    
    #判断g.sign  做macd交易判断
    df=get_price('AG9999.XSGE' ,count=40, end_date=context.current_dt, frequency='15m',fields='close')
    df2=get_price('AG9999.XSGE' ,count=40, end_date=context.current_dt, frequency='60m',fields='close')

    macd_15min=macd(df['close'])
    macd_60min=macd(df2['close'])
    
    #print (macd_15min)
    #print (macd_60min)
    


    
    
    #止损轻仓判断
    if tralling_stop(context, g.stockcode)==1:
        #止损多头
        order_target(IF_current_month, 0, side='long')
        g.sign=0
        g.clear=1
        
    elif tralling_stop(context, g.stockcode)==-1:
        
        #止损空头
        order_target(IF_current_month, 0, side='short')
        g.sign=0
        g.clear=-1
    
    
    
    #开仓同时保证自己当日没有过当前方向的清仓
    if macd_15min[-1]>0 and macd_15min[-2]<=0 and macd_60min[-1]>0 and g.clear<1:
        g.sign=1
    elif  macd_15min[-1]<0 and macd_15min[-2]>=0 and macd_60min[-1]<0 and g.clear>-1:
        g.sign=-1
    
    
    
    
    '''  
    elif len(context.portfolio.long_positions) > 0:
        if macd_60min[-1]<macd_60min[-2]<=0:
            #小时线平仓止损
            order_target(IF_current_month, 0, side='long')
            g.sign=0
            print ('清仓止损多头')
    
    elif len(context.portfolio.short_positions) > 0:
        if macd_60min[-1]>macd_60min[-2] and macd_60min[-1]>0:
            #小时线平仓止损
            order_target(IF_current_month, 0, side='short')
            g.sign=0
            print ('清仓止损空头')
    '''
    

    # 判断当月合约交割日当天不开仓，多头交易
    if (g.sign==1):
        if (context.current_dt.date() == end_data):
            
            pass
        else:
            #如果空仓>=0，开多仓
            if (len(context.portfolio.short_positions) >= 0 and len(context.portfolio.long_positions) == 0):
                log.info('开多仓---：')
                
                if len(context.portfolio.short_positions) >0 :
                    # 平仓空头
                    order_target(IF_current_month, 0, side='short')
       
                # 做多当季多头合约
                print('开当季多头合约')
           
                order_value(IF_current_month, context.portfolio.available_cash , side='long')
                g.sign=1

                
    #空头交易
    if (g.sign == -1):
        if (context.current_dt.date() == end_data):
            # return
            pass
        else:
            #如果多仓>=0，开空仓
            if (len(context.portfolio.short_positions) >= 0 and len(context.portfolio.long_positions) == 0):
                log.info('开空仓---：')
                
                if len(context.portfolio.long_positions) >0 :
                    # 平仓多头
                    order_target(IF_current_month, 0, side='long')
                # 开当季空头合约
                print('开当季空头合约')
                order_value(IF_current_month, context.portfolio.available_cash , side='short')
                g.sign=-1
    else:
        pass

## 收盘后运行函数
def after_market_close(context):
    log.info(str('函数运行时间(after_market_close):'+str(context.current_dt.time())))
    # 得到当天所有成交记录
    trades = get_trades()
    for _trade in trades.values():
        log.info('成交记录：'+str(_trade))
    log.info('一天结束')
    log.info('##############################################################')
    
    
    

########################## 获取期货合约信息，请保留 #################################
# 获取金融期货合约到期日
def get_CCFX_end_date(future_code):
    # 获取金融期货合约到期日
    return get_security_info(future_code).end_date


########################## 自动移仓换月函数 #################################
def position_auto_switch(context,pindex=0,switch_func=None, callback=None):
    """
    期货自动移仓换月。默认使用市价单进行开平仓