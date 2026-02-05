# 克隆自聚宽文章：https://www.joinquant.com/post/49499
# 标题：首板高开-低开-弱转强混合策略（今年收益1138.61%）
# 作者：天山灵兔

# 克隆自聚宽文章：https://www.joinquant.com/post/48680
# 标题：追首板涨停 过去两年年化304%
# 作者：子匀


from jqdata import *
from jqfactor import *
import pandas as pd
from datetime import datetime,timedelta,date


################################### 初始化设置 #############################################
def initialize(context):
    set_option('use_real_price', True)
    log.set_level('system', 'error')
    set_option('avoid_future_data', True)
    
def after_code_changed(context):
    g.n_days_limit_up_list = []   #重新初始化列表
    unschedule_all() # 取消所有定时运行    
    # run_daily(get_stock_list, '9:05')
    run_daily(buy, '09:26')
    run_daily(sell, time='11:25', reference_security='000300.XSHG')
    run_daily(sell, time='14:50', reference_security='000300.XSHG')


def after_trading_end(context):
    print('———————————————————————————————————')
    
## 定义股票池     
def set_stockpool(context):
    yesterday = context.previous_date 
    initial_list = get_all_securities('stock', yesterday).index.tolist()
    return initial_list

##################################  交易函数群 ##################################
def buy(context):
    current_data = get_current_data()
    qualified_stocks =  get_stock_list(context)
    if qualified_stocks:
        value = context.portfolio.available_cash / len(qualified_stocks)
        for s in qualified_stocks:
            # 下单   #至少够买1手
            if context.portfolio.available_cash/current_data[s].last_price>100: 
                order_value(s, value, MarketOrderStyle(current_data[s].day_open))
                print('买入' + s)
                
def sell(context):
    stime = context.current_dt.strftime("%H%M")
    current_data = get_current_data()
    
    for s in list(context.portfolio.positions):
        close_data = attribute_history(s, 4, '1d', ['close'])
        M4=close_data['close'].mean()
        MA5=(M4*4+current_data[s].last_price)/5
        position=context.portfolio.positions[s]
        
        if ((position.closeable_amount !=