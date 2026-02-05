# 克隆自聚宽文章：https://www.joinquant.com/post/48996
# 标题：动态保形回归小市值策略改进
# 作者：yanzigao

# 克隆自聚宽文章：https://www.joinquant.com/post/43738
# 标题：分享适合研究多因子和随机森林的框架
# 作者：TheFun

#时间间隔方面5日与20日间隔有较好表现和回撤
#价格训练的判断标准return小于0表现更好
#导入函数库
from jqlib.technical_analysis import *
from jqdata import *
from jqfactor import *
import pandas as pd
import numpy as np
import math
from sklearn.svm import SVR  
from sklearn.model_selection import GridSearchCV  
from sklearn.model_selection import learning_curve
from sklearn.linear_model import LinearRegression
import jqdata
import datetime
from datetime import time
from sklearn.tree import DecisionTreeRegressor
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler 
from sklearn.model_selection import train_test_split 
from sklearn.preprocessing import StandardScaler 
import sklearn.base
from sklearn.mixture import GaussianMixture  
import xgboost
from xgboost import Booster, XGBRegressor

def initialize(context):
    set_params()# #设置策略参数
    set_backtest()#设置回测条件
    set_variables()  
    set_option('avoid_future_data', True)#防止未来函数
    # run_daily(trade, 'every_bar')# 开盘时运行
    run_daily(close_account, '14:50')
    g.pass_april = True# 是否一、四月空仓
    g.no_trading_today_signal = False
    g.filter_bons = True #国九条：红利条件
    g.stock_pro =0.1   # 股票池内股票占删选后总股票比例
    g.stoploss_market = 0.1 # 止损线
    g.stopprofit_market = 0.35 #止盈线
    g.list_to_buy=[] #买入列表初始化
    
def set_params():
    # g.refresh_rate = 10
    g.tc=20 # 调仓频率，这里为5天一次
    g.tc_stoploss = 1 #止损检测，每天一次
    g.stocknum_1 = 5#突破行情持股数量
    g.stocknum_2 = 3#反转行情持股数量
    g.ret=-0.05
    
def set_backtest():
    set_benchmark('000300.XSHG')#设置对比基本，这里为沪深300
    set_option('use_real_price', True)#使用真实价格成交
    log.set_level('order', 'error')
    
def set_variables():
    g.days = 0 # 记录回测运行的天数
    g.if_trade = False 
    g.if_trade_stoploss = False

# 开盘之前需要做的事：
def before_trading_start(context):
    g.no_trading_today_signal = today_is_between(context)
    #print(g.no_trading_today_signal)
    
    
    
    final_list = []
   # MKT_index = '399101.XSHE'#沪深300:'000300.XSHG'
   # stock_list = get_index_stocks(MKT_index)

    yesterday = context.previous_date
    today = context.current_dt
    stock_list = get_all_securities('stock',yesterday).index.tolist()
    # 设置可行股票池
    stock_list = stock_list
    #国九条：财务造假退市指标：==> 【C罗：按审计无保留意见过滤】
    stock_list = filter_stocks_by_auditor_opinion_jqz(context, stock_list)
    #国九条：利润总额、净利润、扣非净利润三者孰低为负值，且营业收入低于 3 亿元 退市
    stock_list = filter_stocks_by_revenue_and_profit(context, stock_list)
    #国九条：最近三个会计年度累计现金分红总额低于年均净利润的30%，且累计分红金额低于5000万元的，将被实施ST
    stock_list = filter_st_stock(stock_list)
    stock_list = filter_kcb_stock(context, stock_list)
    stock_list = filter_new_stock(context, stock_list)
    stock_list = filter_paused_stock(stock_list)
    
    g.feasible_stocks = list(stock_list)
    
    set_slip_fee(context) 
    if g.days%g.tc==0:
        g.if_trade=True                          # 每g.tc天，调仓一次
    if g.days%g.tc_stoploss == 0:
        g.if_trade_stoploss = True
        
        set_slip_fee(context)                    # 设置手续费与手续费
    if g.no_trading_today_signal == True :         #在空仓月份重置天数计数
        g.days = -1
        
    g.days+=1
    #print(g.days)
#过滤函数
def filter_paused_stock(stock_list):
    current_data = get_current_data()
    return [stock for stock in stock_list if not current_data[stock].paused]
    
def filter_st_stock(stock_list):
    current_data = get_current_data()
    return [stock for stock in stock_list
            if not current_data[stock].is_st
            and 'ST' not in current_data[stock].name
            and '*' not in current_data[stock].name
            and '退' not in current_data[stock].name]

def filter_limitup_stock(context, stock_list):
    last_prices = history(1, unit='1m', field='close', security_list=stock_list)
    current_data = get_current_data()
    return [stock for stock in stock_list if stock in context.portfolio.positions.keys()
            or last_prices[stock][-1] < current_data[stock].high_limit]

def filter_limitdown_stock(context, stock_list):
    last_prices = history(1, unit='1m', field='close', security_list=stock_list)
    current_data = get_current_data()
    return [stock for stock in stock_list if stock in context.portfolio.positions.keys()
            or last_prices[stock][-1] > current_data[stock].low_limit]

def filter_kcb_stock(context, stock_list):
    return [stock for stock in stock_list  if stock[0:3] != '688']

def filter_new_stock(context,stock_list):
    yesterday = context.previous_date
    return [stock for stock in stock_list if not yesterday - get_security_info(stock).start_date < datetime.timedelta(days=250)]

# 2.1 筛选审计意见：蒋老师提供
def filter_stocks_by_auditor_opinion_jqz(context, stock_list):
    #print(f'按审计无保留意见筛选前：{len(stock_list)}')
    # type:(context,list)-> list
    #剔除近三年内有不合格(opinion_type_id >2 且不是 6)审计意见的股票
    start_date = datetime.date(context.current_dt.year - 3, 1,1).strftime('%Y-%m-%d')
    end_date = context.previous_date.strftime('%Y-%m-%d')
    q = query(finance.STK_AUDIT_OPINION).filter(finance.STK_AUDIT_OPINION.code.in_(stock_list), 
        finance.STK_AUDIT_OPINION.report_type == 0, #0:财务报表审计报告
        finance.STK_AUDIT_OPINION.opinion_type_id > 2,  #1:无保留,2:无保留带解释性说明
        finance.STK_AUDIT_OPINION.opinion_type_id != 6,   #6:未经审计，季报
        finance.STK_AUDIT_OPINION.end_date >= start_date,
        finance.STK_AUDIT_OPINION.pub_date <= end_date)
    df = finance.run_query(q)
    bad_companies = df['code'].unique().tolist()
    #print (f'剔除：审计有保留意见的公司：{bad_companies}')
    keep_list = [s for s in stock_list if s not in bad_companies ]
    #print(f'按审计无保留意意见筛选后：{len(keep_list)}')
    return keep_list

#国九条：财务造假退市指标：==> 【C罗：按审计无保留意见过滤】
def filter_stocks_by_revenue_and_profit(context, stock_list):

    #计算分红的三年起止时间
    time1 = context.previous_date
    time0 = time1 - datetime.timedelta(days=365*3) #三年
    #计算年报的去年
    if time1.month>=5:#5月后取去年
        last_year=str(time1.year-1)
    else:   #5月前取前年
        last_year=str(time1.year-2)

    #print(f'按收入和盈利筛选前：{len(stock_list)}')
    #2：主板亏损公司营业收入退市标准，组合指标修改为利润总额、净利润、扣非净利润三者孰低为负值，且营业收入低于 3 亿元。
    #get_history_fundamentals(security, fields, watch_date=None, stat_date=None, count=1, interval='1q', stat_by_year=False)
    list_len = len(stock_list)
    interval = 1000 
    multiple_n = list_len // interval + 1
    start_i = 0
    stk_df = pd.DataFrame()
    for mul in range(multiple_n):
        start_i = mul * interval
        end_i = start_i + interval
        #print(f'{start_i} - {end_i}')
        df = get_history_fundamentals( stock_list[start_i:end_i], fields=[income.operating_revenue, income.total_profit, income.net_profit ], 
            watch_date=context.current_dt, count=1, interval='1y', stat_by_year=True )
        #扣非净利润找不到
        if len(stk_df) == 0:
            stk_df = df
        else:
            stk_df = pd.concat([stk_df,df])
    df = stk_df[ (stk_df["operating_revenue"] < 3e8) & ((stk_df["total_profit"] < 0) | (stk_df["net_profit"] < 0))]
    bad_companies = list(df["code"]) 
    #print (f'剔除：营收太小 且 净利润为负的公司：{bad_companies}')
    
    selected_columns = ['code', 'operating_revenue', 'total_profit','net_profit']
    #print (df[selected_columns])

    # 同时满足才剔除
    keep_list = [s for s in stock_list if s not in bad_companies ]

    #print(f'按利润总额、净利润最低为负值，且 营业收入低于3亿元 筛选后：{len(keep_list)}')
    return keep_list
    
#红利筛选
def bons_filter(context, stock_list):
    time1 = context.previous_date
    time2= time1 - datetime.timedelta(days=365)
    time3 = time1 - datetime.timedelta(days=365*3)
    #去年未分配利润大于0
    q = query(
        finance.STK_BALANCE_SHEET.code, 
        finance