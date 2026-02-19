# 克隆自聚宽文章：https://www.joinquant.com/post/47033
# 标题：基于趋势、拥挤、景气的行业轮动，及行业强势个股的选择
# 作者：hayy

# 导入函数库
from jqdata import *
from jqfactor import *
from jqlib.technical_analysis import *
import datetime as dt
import pandas as pd
# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    set_option("avoid_future_data", True)
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.0005, open_commission=0.0001, close_commission=0.0001, min_commission=1), type='stock')
    set_slippage(FixedSlippage(0.02))# 设置滑点  
    
    g.buyList = []
      # 开盘时运行
    # run_weekly(market_open, 1, time='open')
    run_monthly(market_open, 20, time='open')
    # run_daily(market_open, '9:30')

## 运行函数
def market_open(context):
    industry_codes = ["801010", "801030", "801040", "801050", "801080", "801110", "801120", "801130", "801140", 
                  "801150", "801160", "801170", "801180", "801200", "801210", "801230", "801710", 
                  "801720", "801730", "801740", "801750", "801760", "801770", "801780", "801790", 
                  "801880", "801890"]
    codes = get_factor(context, industry_codes)[0:2]
   # g.buyList = get_stocks_from_industry(context, codes)
    g.buyList = get_buyStock_from_industry(context, codes)
    rebalance_position(context, g.buyList)

# 该行业所有股票
def get_stocks_from_industry(context, codes):
    stock_list = []
    prepare_list = prepare_stock_list(context.previous_date)
    for code in codes:
        i_dt = (get_factor_values(prepare_list, code, context.previous_date, count=1))
        i_dt = i_dt[code].T.iloc[:,0]
        stock_list = stock_list+i_dt[i_dt == 1].index.tolist()
    return stock_list
    
# 为每个行业选择市值最大的20支股票代表整个行业情况（改成动态选择）
def get_star_stocks_from_industry(context, codes):
    stock_dict = dict()
    prepare_list = prepare_stock_list(context.previous_date)
    for code in codes:
        i_dt = (get_factor_values(prepare_list, code, context.previous_date, count=1))
        i_dt = i_dt[code].T.iloc[:,0]
        stock_dict[code] = sorted_by_circulating_market_cap(i_dt[i_dt == 1].index.tolist(), n_limit_top=int(round(len(prepare_list)/130)))
    return stock_dict

# 为每个行业选择强势个股
def get_buyStock_from_industry(context, industry_codes):
    stocks = []
    for code in industry_codes:
        stock_list = get_stocks_from_industry(context, [code])
                # 股票所属行业过去20日数据
        industry_data = finance.run_query(query(finance.SW1_DAILY_PRICE).filter(finance.SW1_DAILY_PRICE.code==code)
                          .filter(finance.SW1_DAILY_PRICE.date<=context.previous_date)
                          .order_by(finance.SW1_DAILY_PRICE.date.desc()).limit(20))
        industry_data.index = pd.to_datetime(industry_data.date)
        factor_values = pd.Series()
        for stock in stock_list:
            # 股票过去20日数据
            stock_data = attribute_history(stock, 20, unit='1d', fields=['close', 'pre_close', 'volume'], skip_paused=False, df=True, fq='pre')
            stock_data.insert(0, 'sy',stock_data.close/stock_data.pre_close-1)
            stock_data.insert(0, 'sy_volume',stock_data.sy*stock_data.volume)
            #股票收益×成交量最大的五天
            stock_sy_max5days = stock_data.sort_values(by = 'sy_volume', ascending = False).iloc[0:5,:]
            # 相对应的行业那5天
            industry_5days_from_stock = industry_data.loc[industry_data.index.isin(stock_sy_max5days.index)]
            factor_value = 0
            for i in range(0,5):
                change_pct = industry_5days_from_stock.loc[stock_sy_max5days.index[i]].change_pct
                weight = pow(2, -(i/(5-1)))
                factor_value = factor_value+weight*change_pct
            factor_values[stock] = factor_value
        stocks = stocks+factor_values.sort_values(ascending = False).index.tolist()[0:10]
    return stocks
    


# 获取因子
def get_factor(context, industry_codes):
    industry_dict = get_star_stocks_from_industry(context, industry_codes)
    
    # 动量因子 60天夏普比率
    factor_mom = pd.Series()
    for key in industry_dict.keys():
        stock_list = industry_dict[key]
        factor_mom_values = get_factor_values(stock_list, 'sharpe_ratio_60', end_date=context.previous