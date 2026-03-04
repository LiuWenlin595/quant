# 克隆自聚宽文章：https://www.joinquant.com/post/17060
# 标题：复现东方证券研报--特质波动率因子研究
# 作者：宸矽


# 导入函数库
from jqdata import *
from jqfactor import *
import datetime as dt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels import regression


# 初始化函数，设定基准等等
def initialize(context):
    # 设定中证全指作为基准
    set_benchmark({'000002.XSHG': 0.5, '399107.XSHE': 0.5})
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    log.set_level('order', 'error')
    
    #第几组
    g.group = 1
    g.method = 'FF5'

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
    run_monthly(before_market_open, monthday = -1, time='before_open', reference_security = '399107.XSHE')
      # 开盘时运行
    run_monthly(market_open, monthday = -1, time='open', reference_security = '399107.XSHE')


## 开盘前运行函数
def before_market_open(context):
    #设置排序方式
    if g.method == 'BP':
        g.asc = False
    else:
        g.asc = True
    #设置滑点、手续费
    set_slip_fee(context)
    #取全A作为股票池
    all_stocks = list(get_all_securities(['stock'], date = context.current_dt).index)
    feasible_stocks = set_feasible_stocks(context, all_stocks)

    if g.method == 'CAPM':
        factor = hetero_factor(feasible_stocks, context.current_dt)
    elif g.method == 'FF3':
        factor = FF3(feasible_stocks, context.current_dt)
    elif g.method == 'CARHART':
        factor = CARHART(feasible_stocks, context.current_dt)
    elif g.method == 'FF5':
        factor = FF5(feasible_stocks, context.current_dt)
    elif g.method == 'circulating_market_cap':
        q = query(valuation.circulating_market_cap, valuation.code).filter(valuation.code.in_(feasible_stocks))
        factor = get_fundamentals(q, context.current_dt)
        factor.index = factor['code'].tolist()
        del factor['code']
        factor.columns = ['score']
    elif g.method == 'BP':
        q = query(1.0 / valuation.pb_ratio, valuation.code).filter(valuation.code.in_(feasible_stocks))
        factor = get_fundamentals(q, context.current_dt)
        factor.index = factor['code'].tolist()
        del factor['code']
        factor.columns = ['score']
        factor = factor.loc[factor['score'] > 0]
          
    
    #排序
    factor = factor.sort('score', ascending = g.asc)

    n = int(len(factor)/10)
    #分组取样
    if g.group == 10:
        g.tobuy_list = factor.index[(g.group - 1) * n :]
    else:
        g.tobuy_list = factor.index[(g.group - 1) * n : g.group * n]
    
    
#1
#设置可行股票池，剔除st、停牌股票，输入日期
def set_feasible_stocks(context, stockList):
    #剔除ST股
    st_data = get_extras('is_st', stockList, count = 1, end_date = context.current_dt)
    stockList = [stock for stock in stockList if not st_data[stock][0]]
    #剔除*st股票
    stockList = [stock for stock in stockList if '*' not in get_security_info(stock).display_name]
    #剔除上市不足3月的新股
    stockList = delete_new(stockList, context.current_dt, n = 91)
    #剔除停牌
    suspended_info_df = get_price(stockList, end_date = context.current_dt, count = 1, frequency = 'daily', fields = 'paused')['paused']
    stockList = [stock for stock in stockList if suspended_info_df[stock][0] == 0]
    
    return stockList   

#剔除新股
def delete_new(stocks, beginDate, n = 365):
    stockList = []
    for stock in stocks:
        start_date = get_security_info(stock).start_date
        if start_date < dt.datetime.date(beginDate - dt.timedelta(days = n)):
            stockList.append(stock)
    return stockList
    

# 根据不同的时间段设置滑点与手续费
def set_slip_fee(context):
    # 将滑点设置为0
    set_slippage(FixedSlippage(0)) 
    # 根据不同的时间段设置手续费
    dt=context.current_dt
    
    if dt>datetime.datetime(2013,1, 1):
        set_commission(PerTrade(buy_cost=0.0003, 
                                sell_cost=0.0013, 
                                min_cost=5)) 
        
    elif dt>datetime.datetime(2011,1, 1):
        set_commission(PerTrade(buy_cost=0.001, 
                                sell_cost=0.002, 
                                min_cost=5))
            
    elif dt>datetime.datetime(2009,1, 1):
        set_commission(PerTrade(buy_cost=0.002, 
                                sell_cost=0.003, 
                                min_cost=5))
                
    else:
        set_commission(PerTrade(buy_cost=0.003, 
                                sell_cost=0.004, 
                                min_cost=5))


## 开盘时运行函数
def market_open(context):
    #调仓，先卖出股票
    for stock in context.portfolio.long_positions:
        if stock not in g.tobuy_list:
            order_target_value(stock, 0)
    #再买入新股票
    total_value = context.portfolio.total_value # 获取总资产
    for i in range(len(g.tobuy_list)):
        value = total_value / len(g.tobuy_list) # 确定每个标的的权重

        order_target_value(g.tobuy_list[i], value) # 调整标的至目标权重
    
    #查看本期持仓股数
    print(len(context.portfolio.long_positions))
    
#计算CAPM特质波动率
def hetero_factor(stocks, end_date, rf = 0.04):
    #设置统计范围
    start_date = list(get_tradeday_list(start = None, end = end_date, frequency = 'month', count = 24).date)[0]
    quote = get_price(stocks, start_date = start_date, end_date = end_date, fields=['close'])['close']
    ret = quote.pct_change()
    ret.dropna(how ='all', inplace = True)
    #构造市场基准收益：流通市值加权
    q = query(valuation.circulating_market_cap, valuation.code).filter(valuation.code.in_(stocks))
    df = get_fundamentals(q, start_date)
    df.index = df['code']
    del df['code']
    df = df/df.sum()
    
    ret_b = pd.DataFrame(np.dot(ret, df), index = ret.index)
    
    #OLS计算hetero_
    hetero = {}
    for stock in ret.columns:
        hetero[stock]  = {'vol': linreg(ret_b - rf/252, ret[stock] - rf/252)}
    
    #规范格式  
    hetero = pd.DataFrame(hetero).T
    hetero.dropna(inplace = True)
    hetero.columns = ['score']

    #返回特质波动率vol
    return hetero

#求Fama-French三因子模型特质波动率
def FF3(stocks, end_date, rf = 0.04):
    LoS=len(stocks)
    #查询三因子/五因子的语句
    q = query(
        valuation.code,
        valuation.circulating_market_cap,
        (balance.total_owner_equities/valuation.circulating_market_cap/100000000.0).label("BP"),
        #indicator.roe,
        #balance.total_assets.label("Inv")
    ).filter(
        valuation.code.in_(stocks)
    )
    
    start_date = list(get_tradeday_list(start = None, end = end_date, frequency = 'month', count = 24).date)[0]
    df = get_fundamentals(q, start_date)
    df.index = df['code']
    del df['code']
    #中性化
    #df = neutralize(df, how = ['sw_l1', 'market_cap'], date = start_date, axis = 0)

    #选出特征股票组合
    S=df.sort('circulating_market_cap').index.tolist()[:LoS/3]
    B=df.sort('circulating_market_cap').index.tolist()[