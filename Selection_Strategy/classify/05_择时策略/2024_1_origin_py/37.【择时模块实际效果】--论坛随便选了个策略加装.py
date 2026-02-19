# 克隆自聚宽文章：https://www.joinquant.com/post/40237
# 标题：【择时模块实际效果】--论坛随便选了个策略加装
# 作者：一只皮卡丘

# 克隆自聚宽文章：https://www.joinquant.com/post/39961
# 标题：科技与狠活
# 作者：wywy1995

#导入函数库
from jqdata import *
from jqfactor import get_factor_values
import numpy as np
import pandas as pd
import talib

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
    g.stock_num = 10
    g.limit_days = 20
    g.limit_up_list = []
    g.hold_list = []
    g.history_hold_list = []
    g.not_buy_again_list = []
    # 设置交易时间，每天运行
    run_daily(prepare_stock_list, time='9:05', reference_security='000300.XSHG')
    run_daily(daily_adjustment, time='9:40', reference_security='000300.XSHG')
    run_daily(check_limit_up, time='14:00', reference_security='000300.XSHG')
    run_daily(print_position_info, time='15:10', reference_security='000300.XSHG')



#1-1 选股模块
def get_factor_filter_list(context,stock_list,jqfactor,sort,p1,p2):
    yesterday = context.previous_date
    score_list = get_factor_values(stock_list, jqfactor, end_date=yesterday, count=1)[jqfactor].iloc[0].tolist()
    df = pd.DataFrame(columns=['code','score'])
    df['code'] = stock_list
    df['score'] = score_list
    df = df.dropna()
    df.sort_values(by='score', ascending=sort, inplace=True)
    filter_list = list(df.code)[int(p1*len(df)):int(p2*len(df))]
    return filter_list

#1-2 选股模块
def get_stock_list(context):
    yesterday = context.previous_date
    initial_list = get_all_securities().index.tolist()
    initial_list = filter_kcbj_stock(initial_list)
    initial_list = filter_st_stock(initial_list)
    initial_list_1 = filter_new_stock(context, initial_list, 250)    
    #长期资产回报率小
    test_list = get_factor_filter_list(context, initial_list_1, 'roa_ttm_8y', True, 0, 0.1)
    q = query(valuation.code,valuation.circulating_market_cap,indicator.eps).filter(valuation.code.in_(test_list)).order_by(valuation.circulating_market_cap.asc())
    df = get_fundamentals(q, date=yesterday)
    df = df[df['eps']>0]
    roa_list = list(df.code)[:5]
    #每股留存收益小
    test_list = get_factor_filter_list(context, initial_list_1, 'retained_earnings_per_share', True, 0, 0.1)
    q = query(valuation.code,valuation.circulating_market_cap,indicator.eps).filter(valuation.code.in_(test_list)).order_by(valuation.circulating_market_cap.asc())
    df = get_fundamentals(q, date=yesterday)
    df = df[df['eps']>0]
    reps_list = list(df.code)[:5]
    #非线性市值小
    initial_list_2 = filter_new_stock(context, initial_list, 125)
    test_list = get_factor_filter_list(context, initial_list_2, 'non_linear_size', True, 0, 0.1)
    q = query(valuation.code,valuation.circulating_market_cap,indicator.eps).filter(valuation.code.in_(test_list)).order_by(valuation.circulating_market_cap.asc())
    df = get_fundamentals(q, date=yesterday)
    df = df[df['eps']>0]
    nls_list = list(df.code)[:5]
    #并集去重
    union_list = list(set(roa_list).union(set(reps_list)).union(set(nls_list)))
    q = query(valuation.code,valuation.circulating_market_cap).filter(valuation.code.in_(union_list)).order_by(valuation.circulating_market_cap.asc())
    df = get_fundamentals(q, date=yesterday)
    final_list = list(df.code)
    return final_list

#1-3 准备股票池
def prepare_stock_list(context):
    #获取已持有列表
    g.hold_list=