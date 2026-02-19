# 克隆自聚宽文章：https://www.joinquant.com/post/46977
# 标题：发一个学习策略5年70倍，思路可以学习
# 作者：xxzlw

#有赚就好
import talib
import numpy as np
import pandas as pd
import math
import datetime

def initialize(context):
    log.set_level('order', 'warning')
    set_benchmark('000001.XSHG')
    g.choice = 500
    g.amount = 5
    g.muster = []
    g.bucket = []
    g.summit = {}
    set_benchmark('000905.XSHG')
    # 用真实价格交易
    set_option('use_real_price', True)
    # 设置滑点为理想情况，不同滑点影响可以在归因分析中查看
    set_slippage(PriceRelatedSlippage(0.000))
    run_daily(prepare, time='9:15')
    run_daily(buy, time='9:26')
    run_daily(sell, time='13:06')
    
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001,