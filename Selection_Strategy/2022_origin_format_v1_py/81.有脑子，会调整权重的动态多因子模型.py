# 克隆自聚宽文章：https://www.joinquant.com/post/21275
# 标题：有脑子，会调整权重的动态多因子模型
# 作者：fireflytxy

# 导入函数库

import jqdata
from jqdata import *

from jqfactor import Factor, calc_factors
import math
import statsmodels.api as sm

import datetime
import time



import pandas as pd
import numpy as np

#import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, make_scorer
from sklearn.preprocessing import StandardScaler
from sklearn.grid_search import GridSearchCV
from scipy.sparse import csr_matrix, hstack
from sklearn.cross_validation import KFold, train_test_split



import scipy.stats as stats
import scipy.optimize as opt




# 初始化函数，设定基准等等
def initialize(context):
    
    
    context.limit = 100
    
    
    #scheduler.run_daily(machine_learning(context.now-datetime.timedelta(7), a = 6))
    context.OBSERVATION=20
    context.stocks= []
    
    context.count_day = 0
    g.stocknum = 15
    # 设定沪深300作为基准
    
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
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
      # 开盘时运行
    run_daily(market_open, time='open', reference_security='000300.XSHG')
      # 收盘后运行
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')

    
## 开盘前运行函数     
def before_market_open(context):
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：'+str(context.current_dt.time()))

    if context.count_day%10 ==0: 
        
        stock_list1 = get_index_stocks('000905.XSHG') + get_index_stocks('000300.XSHG')
        #10个交易日训练一次新的模型
        #获取交易日
        today = context.current_dt
        StartDate = today-datetime.timedelta(130)  #改了
        EndDate = today - datetime.timedelta(1)  #改了
        trading_dates = jqdata.get_trade_days(start_date=StartDate, end_date=EndDate) #, count=None
        
        
        
        IC,stock_data = get_data(context,stock_list1,trading_dates[-1],trading_dates[-11],trading_dates[-31])
        

        #data_matrix = data.values
        for i in range(1,6):
            
            date1 = trading_dates[-(10 * i + 1 )]
            date2 = trading_dates[-(10 * i + 11 )]
            #date3 = trading_dates[-(10 * i + 16 )]
            date3 = trading_dates[-(10 * i + 31 )]
            temp_IC,temp_data = get_data(context,stock_list1,date1,date2,date3)   
            IC = IC.append(temp_IC)
            #data_matrix = np.row_stack((data_matrix,temp_data.values))
            #print temp_IC
        IC.columns =  ['cap','pe','bp','roe','turnover_ratio','increase','price_change_20days']
        print(IC)
        #print IC
        #选取负向因子和正向因子
        negative_factor = []
        positive_factor = []
        #负向因子
        PE = IC.pe[0:5]
        if len(PE[PE != 0]) >=3:
            IC_pe = PE.mean()
            if IC_pe >0:
                positive_factor.append('pe')
            else:
                negative_factor.append('pe')
        else:
            IC_pe = 0
        
                
        #正向因子
        BP = IC.bp[0:5]
        if len(BP[BP != 0]) >=3:
            IC_bp = BP.mean()
            if IC_bp >0:
                positive_factor.append('bp')
            else:
                negative_factor.append('bp')
        else:
            IC_bp = 0
                
        #正向？
        Turn_Over_Rate = IC.turnover_ratio[0:5]
        if len(Turn_Over_Rate[Turn_Over_Rate != 0 ] )>3:
            IC_turn_over = Turn_Over_Rate.mean()
            if IC_turn_over >0:
                positive_factor.append('turnover_ratio')
            else:
                negative_factor.append('turnover_ratio')
        else:
            IC_turn_over = 0
         
        #负向
        Cap = IC.cap[0:5]
        if len(Cap[Cap != 0]) >=3:
            IC_cap = Cap.mean()
            if IC_cap >0:
                positive_factor.append('cap')
            else:
                negative_factor.append('cap')
        else:
            IC_cap = 0
        
        #正向
        Increase = IC.increase[0:5]
        if len(Increase[Increase != 0]) >=3:
            IC_increase = Increase.mean()
            if IC_increase >0:
                positive_factor.append('increase')
            else:
                negative_factor.append('increase')
        else:
            IC_increase = 0
        
        #正向
        Roe = IC.roe[0:5]
        if len(Roe[Roe != 0]) >=3:
            IC_roe = Roe.mean()  
            if IC_roe >0:
                
                positive_factor.append('roe')
            else:
                negative_factor.append('roe')
        else:
            IC_roe = 0
                
        '''
        #动量 负向
        Momentum5 = IC.price_change_5days[0:5]
        if len(Momentum5[Momentum5 != 0]) >=3:
            IC_momentum5 = Momentum5.mean()
            if IC_momentum5 >0:    
                positive_factor.append('price_change_5days')
            else:
                negative_factor.append('price_change_5days')
            
        else:
            IC_momentum5 = 0
            
        '''    
        Momentum10 = IC.price_change_20days[0:5]
        if len(Momentum10[Momentum10 != 0]) >=3:
            IC_momentum10 = Momentum10.mean()
            if IC_momentum10 >0:
                positive_factor.append('price_change_20days')
            else:
                negative_factor.append('price_change_20days')
         
        else:
            IC_momentum10 = 0  
        
        
            
        weight = {'pe':IC_pe,'bp':IC_bp,'turnover_ratio':IC_turn_over,'cap':IC_cap,'increase':IC_increase,'roe':IC_roe,'price_change_20days':IC_momentum10 }
        
        #stock_list = 
        
        #获取当前的交易数据
        current_factor = get_factor(stock_list1,trading_dates[-1],trading_dates[-21])
        
        df_positive = current_factor[positive_factor]
        df_negative = current_factor[negative_factor]
        factors = positive_factor + negative_factor
        
        sum_weight = 0
        for factor in factors:
            sum_weight = sum_weight + abs(weight[factor])
        
           
        for factor in df_positive.columns.tolist():#越高越好
            df_positive.sort_values(factor,inplace=True)
            df_positive[factor]=abs(weight[factor])/sum_weight * np.linspace(1,len(df_positive),len(df_positive))
            
        
        for factor in df_negative.columns.tolist():#越高越好
            df_negative.sort_values(factor,inplace=True)
            df_negative[factor]=abs(weight[factor])/sum_weight * np.linspace(len(df_negative),1,len(df_negative))
            
        df_positive.sort_index(inplace=True)
        df_negative.sort_index(inplace=True)
        
        fundamental_df_rank=df_negative.join(df_positive)
        
        ranking = fundamental_df_rank.apply(sum,axis = 1)
        if len(ranking)>10:
            ranking = ranking.sort_values()[-15:]
            context.stocks = ranking.index.tolist()
            
        else:
            context.stocks = []
            
        print(context.stocks)

    # 要操作的股票：平安银行（g.为全局变量）
    #g.security = '000001.XSHE'

'''
def get_industry_exposure(order_book_ids):
    SHENWAN_INDUSTRY_MAP = {