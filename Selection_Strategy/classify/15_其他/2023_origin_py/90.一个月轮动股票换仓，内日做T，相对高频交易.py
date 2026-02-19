# 克隆自聚宽文章：https://www.joinquant.com/post/34847
# 标题：一个月轮动股票换仓，内日做T，相对高频交易
# 作者：Pengpengpeng

# 克隆自聚宽文章：https://www.joinquant.com/post/34748
# 标题：【复现】FFScore财务模型
# 作者：Hugo2046

from typing import (List,Tuple,Dict,Callable,Union)

import datetime as dt
import numpy as np
import pandas as pd

from jqdata import *
from jqfactor import (calc_factors,Factor,winsorize_med,neutralize,standardlize)

# enable_profile()  # 开启性能分析
# 初始化函数，设定基准等等

def initialize(context):

    set_backtest()
    set_params()
    set_variables()
    before_trading_start(context)
    run_monthly(trade,1, 'open', reference_security='000300.XSHG')
    
    run_daily(get_T, time='every_bar', reference_security='000300.XSHG')

def set_params():
    
    # 用于打分的因子
    g.sel_fields = ['DELTA_ROE', 'ROA2', 'DELTA_MARGIN', 'DELTA_CATURN', 'DELTA_ROA2','DLTA_LIQUID']
    g.orderid = []

def set_variables():
    
    pass

def set_backtest():
    '''回测所需设置'''

    set_option("avoid_future_data", True)  # 避免数据
    set_option("use_real_price", True)  # 真实价格交易
    set_option('order_volume_ratio', 1)  # 根据实际行情限制每个订单的成交量
    set_benchmark('000905.XSHG')  # 设置基准
    #log.set_level("order", "debuge")
    log.set_level('order', 'error')


# 每日盘前运行 设置不同区间手续费
def before_trading_start(context):

    # 手续费设置
    # 将滑点设置为0.002
    set_slippage(FixedSlippage(0.002))

    # 根据不同的时间段设置手续费
    c_dt = context.current_dt

    if c_dt > dt.datetime(2013, 1, 1):
        set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5))

    elif c_dt > dt.datetime(2011, 1, 1):
        set_commission(PerTrade(buy_cost=0.001, sell_cost=0.002, min_cost=5))

    elif c_dt > dt.datetime(2009, 1, 1):
        set_commission(PerTrade(buy_cost=0.002, sell_cost=0.003, min_cost=5))

    else:
        set_commission(PerTrade(buy_cost=0.003, sell_cost=0.004, min_cost=5))
        
# 股票池过滤

# 筛选股票池
class Filter_Stocks(object):
    '''
    获取某日的成分股股票
    1. 过滤st
    2. 过滤上市不足N个月
    3. 过滤当月交易不超过N日的股票
    ---------------
    输入参数：
        index_symbol:指数代码,A等于全市场,
        watch_date:日期
    '''
    
    def __init__(self,symbol:str,watch_date:str)->None:
        
        if isinstance(watch_date,str):
            
            self.watch_date = pd.to_datetime(watch_date).date()
            
        else:
            
            self.watch_date = watch_date
            
        self.symbol = symbol
        self.get_index_component_stocks()
        
    def get_index_component_stocks(self)->list:
        
        '''获取指数成分股'''
        
        if self.symbol == 'A':
            
            wd:pd.DataFrame = get_all_securities(types=['stock'],date=self.watch_date)
            self.securities:List = wd.query('end_date != "2200-01-01"').index.tolist()
        else:
            
            self.securities:List = get_index_stocks(self.symbol,self.watch_date)
    
    def filter_paused(self,paused_N:int=1,threshold:int=None)->list:
        
        '''过滤停牌股
        -----
        输入:
            paused_N:默认为1即查询当日不停牌
            threshold:在过paused_N日内停牌数量小于threshold
        '''
        
        if (threshold is not None) and (threshold > paused_N):
            raise ValueError(f'参数threshold天数不能大于paused_N天数')
            
        
        paused = get_price(self.securities,end_date=self.watch_date,count=paused_N,fields='paused',panel=False)
        paused = paused.pivot(index='time',columns='code')['paused']
        
        # 如果threhold不为None 获取过去paused_N内停牌数少于threshodl天数的股票
        if threshold:
            
            sum_paused_day = paused.sum()
            self.securities = sum_paused_day[sum_paused_day < threshold].index.tolist()
        
        else:
            
            paused_ser = paused.iloc[-1]
            self.securities = paused_ser[paused_ser ==