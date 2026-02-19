#导入函数库
from jqdata import *
from jqlib.technical_analysis import *
from jqfactor import get_factor_values
import numpy as np
import pandas as pd
import statsmodels.api as sm
import datetime as dt

#初始化函数 
def initialize(context):

    # 设定基准
    set_benchmark('000905.XSHG')
    # 用真实价格交易
    set_option('use_real_price', True)
    # 打开防未来函数
    set_option("avoid_future_data", True)
    # 将滑点设置为0
    set_slippage(FixedSlippage(0))
    # 设置交易成本万分之三，不同滑点影响可在归因分析中查看
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, close_today_commission=0, min_commission=5),type='fund')
    # 过滤order中低于error级别的日志
    log.set_level('order', 'error')
    
    #初始化全局变量
    g.stock_num = 10 #最大持仓数
    g.limit_up_list = [] #记录持仓中涨停的股票
    g.hold_list = [] #当前持仓的全部股票
    g.history_hold_list = [] #过去一段时间内持仓过的股票
    g.not_buy_again_list = [] #最近买过且涨停过的股票一段时间内不再买入
    g.limit_days = 20 #不再买入的时间段天数
    g.target_list = [] #开盘前预操作股票池
    g.industry_control = True #过滤掉不看好的行业
    g.industry_filter_list = ['钢铁I','煤炭I','石油石化I','采掘I', #重资产
    '银行I','非银金融I','金融服务I', #高负债
    '交运设备I','交通运输I','传媒I','环保I'] #盈利差
    #列表中的行业选择为主观判断结果，如果g.industry_control为False，则上述列表不影响选股
    
    # 设置交易运行时间
    run_daily(prepare_stock_list, time='9:05', reference_security='000300.XSHG') #准备预操作股票池
    run_weekly(weekly_adjustment, weekday=1, time='9:30', reference_security='000300.XSHG') #默认周一开盘调仓，收益最高
    run_daily(check_limit_up, time='14:00', reference_security='000300.XSHG') #检查持仓中的涨停股是否需要卖出
    run_daily(print_position_info, time='15:10', reference_security='000300.XSHG') #打印复盘信息



#1-1 选股模块
def get_stock_list(context):
    yesterday = str(context.previous_date)
    initial_list = get_all_securities().index.tolist()
    initial_list = filter_new_stock(context,initial_list)
    initial_list = filter_kcb_stock(context, initial_list)
    initial_list = filter_st_stock(initial_list)
    #PB过滤
    q = query(valuation.code, valuation.pb_ratio, indicator.eps).filter(valuation.code.in_(initial_list)).order_by(valuation.pb_ratio.asc())
    df = get_fundamentals(q)
    df = df[df['eps']>0]
    df = df[df['pb_ratio']>0]
    pb_list = list(df.code)[:int(0.5*len(df.code))]
    #ROEC过滤
    #因为get_history_fundamentals有返回数据限制最多5000行，需要把pb_list拆分后查询再组合
    interval = 1000 #count=5时，一组最多1000个，组数向下取整
    pb_len = len(pb_list)
    if pb_len <= interval:
        df = get_history_fundamentals(pb_list, fields=[indicator.code, indicator.roe], watch_date=yesterday, count=5, interval='1q')
    else:
        df_num = pb_len // interval
        df = get_history_fundamentals(pb_list[:interval], fields=[indicator.code, indicator.roe], watch_date=yesterday, count=5, interval='1q')
        for i in range(df_num):
            dfi = get_history_fundamentals(pb_list[interval*(i+1):min(pb_len,interval*(i+2))], fields=[indicator.code, indicator.roe], watch_date=yesterday, count=5, interval='1q')
            df = df.append(dfi)
    df = df.groupby('code').apply(lambda x:x.reset_index()).roe.unstack()
    df['increase'] = 4*df.iloc[:,4] - df.iloc[:,0] - df.iloc[:,1] - df.iloc[:,2] - df.iloc[:,3]
    df.dropna(inplace=True)
    df.sort_values(by='increase',ascending=False, inplace=True)
    temp_list = list(df.index)
    temp_len = len(temp_list)
    roe_list = temp_list[:int(0.1*temp_len)]
    #行业过滤
    if g.industry_control == True:
        industry_df = get_stock_industry(roe_list, yesterday)
        ROE_list = filter_industry(industry_df, g.industry_filter_list)
    else:
        ROE_list = roe_list
    #市值排序
    q = query(valuation.code,valuation.circulating_market_cap).filter(valuation.code.in_(ROE_list)).order_by(valuation.circulating_market_cap.asc())
    df = get_fundamentals(q)
    ROEC_list = list(df.code)

    return ROEC_list


#1-2 行业过滤函数
def get_stock_industry(securities, watch_date, level='sw_l1', method='industry_name'): 
    industry_dict = get_industry(securities, watch_date)
    industry_ser = pd.Series({k: v.get(level, {method: np.nan