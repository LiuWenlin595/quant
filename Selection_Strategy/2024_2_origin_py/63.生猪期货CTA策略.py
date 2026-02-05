# 克隆自聚宽文章：https://www.joinquant.com/post/35604
# 标题：生猪期货CTA策略
# 作者：PokerTrader

# 导入函数库
from jqdata import *
import talib
import numpy as np
import pandas as pd

## 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('LH8888.XDCE')
    # set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')

    ### 期货相关设定 ###
    # 设定账户为金融账户
    set_subportfolios([SubPortfolioConfig(cash=context.portfolio.starting_cash, type='futures')])
    # 期货类每笔交易时的手续费是：买入时万分之0.23,卖出时万分之0.23,平今仓为万分之23
    set_order_cost(OrderCost(open_commission=0.000023, close_commission=0.000023,close_today_commission=0.0023), type='futures')
    # 设定保证金比例
    set_option('futures_margin_rate', 0.14)

    # 设置期货交易的滑点
    set_slippage(StepRelatedSlippage(0))
    # 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'IF8888.CCFX'或'IH1602.CCFX'是一样的）
    # 注意：before_open/open/close/after_close等相对时间不可用于有夜盘的交易品种，有夜盘的交易品种请指定绝对时间（如9：30）

    g.loss_ratio = 0.03
    g.win_ratio = 0.03
    g.loss_limit =0 
    g.std=0
    g.security = 'LH9999.XDCE'
    g.relative_security = '002714.XSHE' #相关品种选取的是牧原股份
    g.main_symbol = get_dominant_future('LH')
    g.buy_ration = 0.7
    g.sell_ration = 0.7
    g.long_order = None
    g.short_order = None
    g.long_threshold = g.short_threshold = 0
    g.ma_up_count = 0
    g.ma_down_count = 0
    g.open_order_lock = False 
    g.is_settlement_date = False
    g.firstTimeCalculateThreshold = True
    g.today_canBuy = True
    g.iskd_deadCross = False
    g.relative_is_close_down = False
    g.relative_is_close_up = False
    dt = context.current_dt # 当前日期
    dt_yestoday = dt-datetime.timedelta(days=1)
    cacluate_ma(dt_yestoday)
    run_daily( before_market_open, time = '8:50', reference_security = g.security)
    
      # 开盘时运行,支持分钟级别
    #run_daily( market_open, time = 'every_bar', reference_security = g.security)
      # 收盘后运行
     
    run_daily( after_market_close, time = '15:30', reference_security = g.security)

def handle_tick(context, tick):
    # 获取最新的 tick 数据 2018-01-02 09:00:59.
    tick_data = get_current_tick(g.main_symbol)
    # 判断是不是敏感时间
    
    deal(context, tick_data.current, 'tick')
    # print(tick_data)
# 2018-01-02 09:00:59.500000 - INFO  - Tick(code: RB1805.XSGE, datetime: 2018-01-02 09:00:59.500000, open: 3801.0, current: 3800.0, high: 3809.0, low: 3798.0, volume: 79234, money: 3013083440.0, position: 2527764.0, a1_p: 3800.0, a1_v: 116, b1_p: 3799.0, b1_v: 141)
## 开盘前运行函数
def before_market_open(context):
    # log.info('函数运行时间(before_market_open)：'+str(context.current_dt.time()))
    dt = context.current_dt # 当前日期
    g.main_symbol = get_dominant_future('LH')  #获取主力合约
    if g.long_order is not None : g.main_symbol = g.long_order['security']
    if g.short_order is not None : g.main_symbol = g.short_order['security']
    subscribe(g.main_symbol, 'tick')
    
    #计算截止到上一个交易日的MACD指标
    dt_yestoday = dt-datetime.timedelta(days=1)
    yestoday = dt_yestoday.strftime('%Y-%m-%d')
    cacluate_ma(dt_yestoday)
    set_ration()
    g.firstTimeCalculateThreshold = True
    g.today_canBuy = True
    '''
    kdlist = myself_kdj(g.main_symbol,yestoday)
    g.k = kdlist[0]
    g.d = kdlist[1]
    g.iskd_deadCross = is_kd_deadCross(kdlist)
    g.std = calculate_std(g.main_symbol,20,yestoday)
    '''
    g.macd,g.diff,g.dea= calculateMACD_oneday(g.main_symbol,yestoday)
    print(g.macd,g.diff,g.dea)
    #判断相关品种的趋势一致性
    g.relative_is_close_down=is_close_down(g.relative_security,yestoday,5)
    g.relative_is_close_up = not g.relative_is_close_down
    print(g.relative_is_close_down)



def market_open(context):
    deal(context, get_current_data()[g.main_symbol].last_price)

def deal(context, last_price, frequency = 'tick'):
    dt = context.current_dt# 当前日期
    dt_yestoday = dt-datetime.timedelta(days=1)
    if frequency == 'bar' and dt.hour ==9 and dt.minute ==0:return
    
    #log.info('函数运行时间(deal)：'+str(dt.time()))
    if g.long_order and can_close_long(g.long_order, last_price, context.current_dt):
        log.info('close long in ', frequency)
        close_orders(g.long_order,list(context.portfolio.long_positions.keys())[0])
        g.main_symbol = get_dominant_future('LH')
    if g.short_order and can_close_short(g.short_order, last_price, context.current_dt):
        log.info('close short in ', frequency)
        close_orders(g.short_order, list(context.portfolio.short_positions.keys())[0])
        g.main_symbol = get_dominant_future('LH')
    if dt.hour == 21 or dt.hour == 9 :
        calculate_threshold(dt_yestoday)

    if g.long_order or g.short_order or g.is_settlement_date or (dt.hour == 14 and dt.minute == 59) or dt.hour == 15: return

    # 开仓逻辑 当macd大于0，且最新价格突破开仓阈值，且相关品种趋势向上时开多仓
    if  g.macd>0 and last_price > g.long_threshold and g.long_threshold!=0  and g.today_canBuy and g.relative_is_close_up:
        log.info('open long in ', frequency, last_price, g.long_threshold)
        open_order(context.portfolio.total_value, last_price, 'long')
    
    if  last_price < g.short_threshold and g.short_threshold!=0 and g.macd<0 and g.today_canBuy and g.relative_is_close_down:
        log.info('open short in ', frequency, last_price, g.long_threshold)
        open_order(context.portfolio.total_value, last_price,'short')

    
## 收盘后运行函数
def after_market_close(context):
    g.long_threshold = g.short_threshold = 0
    unsubscribe_all()
    log.info('##############################################################')

def cacluate_ma(dt):
    g.ten_ma_up = is_ma_up(g.main_symbol, 10, 4, dt.date())
    g.ten_ma_down = is_ma_down(g.main_symbol, 10, 4, dt.date())
    g.long_ma_down = is_ma_down(g.main_symbol, 60, 4, dt.date())
    g.long_ma_up = is_ma_up(g.main_symbol, 60, 4, dt.date())
    g.five_ma_up = is_ma_up(g.main_symbol, 5, 4, dt.date())
    g.five_ma_down = is_ma_down(g.main_symbol, 5, 4, dt.date())
    if(g.ten_ma_up): 
        g.ma_up_count = g.ma_up_count + 1
        log.info("均线上升趋势打开第" + str(g.ma_up_count) + "次")
    if(g.ten_ma_down): 
        g.ma_down_count = g.ma_down_count + 1
        log.info("均线下降趋势打开" + str(g.ma_down_count) + "次")
#计算标准差 
def calculate_std(stock,timePeriod,end_date):
    df = get_price(stock, count = timePeriod, end_date=end_date, frequency='daily', fields=['close'])
    close = df['close'].values
    std=close.std(ddof = 1)
    return std    


def open_order(total_value, last_price, side):
    # log.info("try open order =>",g.open_order_lock)
    if g.open_order_lock: return
    g.open_order_lock = True
    setLimit(last_price)
    lots = set_lots(total_value, g.loss_limit)
    new_order = order(g.main_symbol, lots, side=side)
    if new_order is None:
        g.open_order_lock = False
        log.warn("开仓失败!!!!!")
    else:
        # 还没有执行到这里另一个tick就进来了.. 所以这里需要做些什么
        if (new_