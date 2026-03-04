# 克隆自聚宽文章：https://www.joinquant.com/post/21349
# 标题：宏观指标择时检测
# 作者：大锐锐丶

# 克隆自聚宽文章：https://www.joinquant.com/post/19349
# 标题：择时，还是宏观数据靠谱（宏观择时集合）
# 作者：云帆

# 导入函数库
from jqdata import *
import tushare as ts

import numpy as np
import pandas as pd
import talib as tl
import pickle
import datetime
import tushare as ts
from six import StringIO
import warnings
warnings.filterwarnings('ignore')

# 初始化函数，设定基准等等
def initialize(context):
    cpi_df=ts.get_cpi().set_index("month").sort_index().pct_change()
    ppi_df=ts.get_ppi().set_index("month").sort_index().pct_change()
    g.ppi_cpi_df=pd.concat([cpi_df,ppi_df],axis=1)
    
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')
    set_params()
    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
    if g.run_monthly == True:
        run_monthly(before_market_open, monthday=1, time='09:30')
          # 开盘时运行
        run_monthly(market_open, monthday=1, time='09:30')
    else:
        run_daily(before_market_open, time='open')
        run_daily(market_open, time='open')
        
    
def set_params():
    g.n = 3 #移动平均窗口
    g.bulin_n = 25 #布林带数据长度
    g.position = 0
    g.stocks = '000300.XSHG'
    g.bulin_upper_dev = 1.8 #布林带上限标准差倍数
    g.bulin_lower_dev = 1.8
    g.run_monthly = True
    g.num_date = 90
    g.reserve_ratio_delay = 120 #存款准备金率取之前数据的周期
    g.weight = [1,1,2,1,1]  #'monetary','forex','credit','boom','inflation'
    g.combine_weights = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]  #'PMI','import_idx','primary_yoy','satisfaction_idx','confidence_idx'

## 开盘前运行函数
def before_market_open(context):
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：'+str(context.current_dt.time()))
    current_day = context.current_dt.day
    current_month = context.current_dt.month
    current_year = context.current_dt.year

    month_list = get_last_month(current_year,current_month,24)
    month_list.reverse()
    
    current_date = context.current_dt.date()
    previous_date = context.previous_date
    previous_date = datetime.datetime.strftime(previous_date,'%Y-%m-%d')
    trade_days_one_month = get_trade_days(end_date=current_date,count=g.num_date)
    trade_days_one_month = datetime_to_str(trade_days_one_month)
    trade_days_one_month.pop() #将当天值去除
    ts_data = change_to_tushare_date(trade_days_one_month)
    
    
    m1_m2_position=get_m1_m2_position(month_list)

    

    pmi_position=  get_pmi_position(month_list)
    produce_idx_positon=get_produce_idx_positon(month_list)
    import_idx_positon=get_import_idx_positon(month_list)
    delivery_time_idx_positon= get_delivery_time_idx_positon(month_list)
    finished_produce_idx_positon=get_finished_produce_idx_positon(month_list)
    purchase_quantity_idx_positon=get_purchase_quantity_idx_positon(month_list)
    
    
    expand_yoy_position=get_expand_yoy_position(month_list)
    secondary_yoy_positon=get_secondary_yoy_positon(month_list)
    primary_yoy_positon=get_primary_yoy_positon(month_list)
    
    
    collective_acc_positon=get_collective_acc_positon(month_list)
    foreign_yoy_positon= get_foreign_yoy_positon(month_list)
    growth_yoy_positon=get_growth_yoy_positon(month_list)
    private_yoy_positon=get_private_yoy_positon(month_list)
    joint_stock_yoy_positon=get_joint_stock_yoy_positon(month_list)
        
        
    satisfaction_position=get_satisfaction_position(month_list)
    confidence_position=get_confidence_position(month_list)
    
    ppi_cpi_position=get_ppi_cpi_position(month_list)

    
    combine_position = [
        m1_m2_position
       
        ,ppi_cpi_position
        
        
        ,pmi_position
        ,produce_idx_positon
        # ,import_idx_positon
        ,delivery_time_idx_positon
        # ,finished_produce_idx_positon
        ,purchase_quantity_idx_positon
        
        ,expand_yoy_position
        ,secondary_yoy_positon
        ,primary_yoy_positon
        
        ,collective_acc_positon
        ,foreign_yoy_positon
        ,growth_yoy_positon
        ,private_yoy_positon
        ,joint_stock_yoy_positon
    
    
        ,satisfaction_position
        ,confidence_position]
    
    combine_position = np.array(combine_position).flatten()
    combine_weights = np.array(g.combine_weights)
    position = (combine_position * g.combine_weights).sum()
    position = position/combine_weights.sum()
    print(str(current_year)+"-"+str(current_month ))
    print( combine_position )
    if position > 0.45:
        g.position = 1
    elif position < 0.4:
        g.position = 0
    else:
        g.position = 0.5
    
## 开盘时运行函数
def market_open(context):
    previous_date = context.previous_date
    previous_date = datetime.datetime.strftime(previous_date,'%Y-%m-%d')
    cash = context.portfolio.available_cash
    all_cash = context.portfolio.total_value
    '''
    if g.position == 1:
            log.info('开始下单')
            order_value(g.stocks, cash)
    else:
        order_target(g.stocks, 0)
    '''
    #大盘止损，上月跌幅超5%则卖出
    price = get_price(g.stocks,end_date=previous_date, fields=['close'],count=21)['close']
    pct_change = price.pct_change(20).values[-1]
    print(g.position)
    if g.position == 1:
        log.info('开始下单')
        order_value(g.stocks, cash)
    # 如果上一时间点价格低于五天平均价, 则空仓卖出
    elif g.position == 0.5:
        order_value(g.stocks, all_cash/2)
    else:
        order_target(g.stocks, 0)
    
##################################工具函数###################################################

def get_last_month(year,month,n):
    l = []
    j = 12
    r = 0
    for i in range(n):
        m = month  - i -1
        if m < 1:
            j += 1
            if j==13:
                year -= 1
                j = 1
                r += 1
            ml = month + 12*r - i - 1
            if ml < 10:
                date = str(year) + '-0' + str(ml)  
            else:
                date = str(year) + '-' + str(ml)
            l.append(date)
        else:
            if m < 10:
                date = str(year) + '-0' + str(m)  
            else:
                date = str(year) + '-' + str(m)
            l.append(date)
    return l

def datetime_to_str(date_list):
    l = []
    for date in date_list:
        d = datetime.datetime.strftime(date,'%Y-%m-%d')
        l.append(d)
    return l

def change_to_tushare_date(date_list):
    l = []
    for date in date_list:
        y = date[:4]
        m = date[5:7]
        d = date[8:10]
        nd = y+m+d
        l.append(nd)
    return l


#获取PMI数据
def  get_PMI(month_list):
    a = macro.MAC_MAN