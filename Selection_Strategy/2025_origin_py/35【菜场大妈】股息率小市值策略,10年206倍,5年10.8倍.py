# 克隆自聚宽文章：https://www.joinquant.com/post/45261
# 标题：【菜场大妈】股息率小市值策略,10年206倍,5年10.8倍
# 作者：120022

# 克隆自聚宽文章：https://www.joinquant.com/post/45126
# 标题：实盘策略5年收益1083.18%，回撤只有16.82%
# 作者：@安易

import pandas as pd 
from jqdata import *
import redis
import json


def initialize(context):
    # setting
    log.set_level('order', 'error')
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    set_benchmark('000905.XSHG')
    # 设置滑点为理想情况，纯为了跑分好看，实际使用注释掉为好
    # set_slippage(PriceRelatedSlippage(0.000))
    # 设置交易成本
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, close_today_commission=0, min_commission=5),type='fund')
    # strategy
    #初始化全局变量
    g.no_trading_today_signal = False
    g.stock_num = 5
    g.choice = []
    g.just_sold = []
    run_daily(prepare_stock_list, time='9:05', reference_security='000300.XSHG') 
    run_daily(check_limit_up, time='14:00') 
    run_monthly(my_Trader, 1 ,time='9:30', force=True) 
    run_monthly(go_Trader, 1 ,time='14:55', force=True) 
    run_daily(close_account, '14:30')
          # 收盘后运行
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')
    
def my_Trader(context):

    #1 all stocks
    dt_last = context