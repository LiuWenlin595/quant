# 克隆自聚宽文章：https://www.joinquant.com/post/36805
# 标题：为实盘做的更新: 分钟级别和盘中止损
# 作者：蚂蚁量化

# 克隆自聚宽文章：https://www.joinquant.com/post/36375
# 标题：2021年度文章精选第一篇策略的修订及详解-Python2版
# 作者：蚂蚁量化

#-*- coding: utf-8 -*-
# 如果你的文件包含中文, 请在文件的第一行使用上面的语句指定你的文件编码

# 用到回测API请加入下面的语句
# from kuanke.user_space_api import *
import math

def set_param():
    # 交易设置
    g.stocknum = 4 # 理想持股数量
    g.bearpercent = 0.3 # 熊市仓位
    g.bearposition = True # 熊市是否持仓
    g.sellrank = 10 # 排名多少位之后(不含)卖出
    g.buyrank = 9 # 排名多少位之前(含)可以买入

    # 初始筛选
    g.tradeday = 300 # 上市天数
    g.increase1d = 0.087 # 前一日涨幅
    g.tradevaluemin = 0.01 # 最小流通市值 单位（亿）
    g.tradevaluemax = 1000 # 最大流通市值 单位（亿）
    g.pbmin = 0.5 # 最小市净率
    g.pbmax = 3.5 # 最大市净率

    # 排名条件及权重，正数代表从小到大，负数表示从大到小
    # 各因子权重：总市值，流通市值，最新价格，5日平均成交量，60日涨幅
    g.weights = [5,5,8,4,10]
    
    # 配置择时
    g.MA = ['000001.XSHG', 10] # 均线择时
    g.choose_time_signal = True # 启用择时信号
    g.threshold = 0.003 # 牛熊切换阈值
    g.buyagain = 5 # 再次买入的间隔时间

# 获取股票n日以来涨幅，根据当前价计算
# n 默认20日
def get_growth_rate(code, n=20):
    lc = get_close_price(code, n)
    c = get_close_price(code, 1, '1m')
    
    if not isnan(lc) and not isnan(c) and lc != 0:
        return (c - lc) / lc
    else:
        log.error("数据非法, code: %s, %d日收盘价: %f, 当前价: %f" %(code, n, lc, c))
        return 0

# 获取股票现价和60日以前的价格涨幅    
def get_growth_rate60(code):
    price60d = attribute_history(code, 60, '1d', 'close', False)['close'][0]
    pricenow = get_close_price(code, 1, '1m')
    if not isnan(pricenow) and not isnan(price60d) and price60d != 0:
        return pricenow / price60d
    else:
        return 100

# 过滤涨停的股票
def filter_limitup_stock(context, stock_list):
    last_prices = history(1, unit='1m', field='close', security_list=stock_list, df=False)
    current_data = get_current_data()
    
    # 已存在于持仓的股票即使涨停也不过滤，避免此股票再次可买，但因被过滤而导致选择别的股票
    return [stock for stock in stock_list if stock in context.portfolio.positions.keys() 
        or last_prices[stock][-1] < current_data[stock].high_limit]

# 获取前n个单位时间当时的收盘价
def get_close_price(code, n, unit='1d'):
    return attribute_history(code, n, unit, 'close', df=False)['close'][0]

# 平仓，卖出指定持仓
def close_position(code):
    order = order_target_value(code, 0) # 可能会因停牌或跌停失败
    if order != None and order.status == OrderStatus.held:
        g.sold_stock[code] = 0

# 清空卖出所有持仓
def clear_position(context):
    if context.portfolio.positions:
        log.info("==> 清仓，卖出所有股票")
        for stock in context.portfolio.positions.keys():
            close_position(stock)

# 过滤停牌股票
def filter_paused_stock(stock_list):
    current_data = get_current_data()
    return [stock for stock in stock_list if not current_data[stock].paused]

# 过滤ST及其他具有退市标签的股票
def filter_st_stock(stock_list):
    current_data = get_current_data()
    return [stock for stock in stock_list 
        if not current_data[stock].is_st 
        and 'ST' not in current_data[stock].name 
        and '*' not in current_data[stock].name 
        and '退' not in current_data[stock].name]
        
# 过滤创业版、科创版股票
def filter_gem_stock(context, stock_list):
    return [stock for stock in stock_list if stock[0:3] != '300' and stock[0:3] != "688"]

# 过滤次新股
def filter_new_stock(context, stock_list):
    return [stock for stock in stock_list if (context.previous_date - datetime.timedelta(days=g.tradeday)) > get_security_info(stock).start_date]

# 过滤昨日涨幅过高的股票
def filter_increase1d(stock_list):
    return [stock for stock in stock_list if get_close_price(stock, 1) / get_close_price(stock, 2) < (1 + g.increase1d)]

# 过滤卖出不足buyagain日的股票
def filter_buyagain(stock_list):
    return [stock for stock in stock_list if stock not in g.sold_stock.keys()]

# 取流通市值最小的1000股作为基础的股票池，以备继续筛选
def get_stock_list(context):
    df = get_fundamentals(query(valuation.code).filter(valuation.pb_ratio.between(g.pbmin, g.pbmax)
        ).order_by(valuation.circulating_market_cap.asc()).limit(1000)).dropna()
    stock_list = list(df['code'])
    
    # 过滤创业板、ST、停牌、当日涨停、次新股、昨日涨幅过高、卖出后天数不够
    stock_list = filter_gem_stock(context, stock_list)
    stock_list = filter_st_stock(stock_list)
    stock_list = filter_paused_stock(stock_list)
    stock_list = filter_limitup_stock(context, stock_list)
    stock_list = filter_new_stock(context, stock_list)
    stock_list = filter_increase1d(stock_list)
    stock_list = filter_buyagain(stock_list)
    return stock_list

# 后备股票池进行综合排序筛选
def get_stock_rank_m_m(stock_list):
    rank_stock_list = get_fundamentals(query(
        valuation.code, valuation.market_cap, valuation.circulating_market_cap
        ).filter(valuation.code.in_(stock_list)
        ).order_by(valuation.circulating_market_cap.asc()).limit(100))
        
    # 5日累计成交量
    volume5d = [attribute_history(stock, 1200, '1m', 'volume', df=False)['volume'].sum() for stock in rank_stock_list['code']]
    # 60日涨幅
    increase60d = [get_growth_rate60(stock) for stock in rank_stock_list['code']]
    # 当前价格
    current_price = [get_close_price(stock, 1, '1m') for stock in rank_stock_list['code']]
    
    # 当前价格最低的
    min_price = min(current_price)
    
    # 60日涨幅最小的
    min_increase60d = min(increase60d)
    
    # 流通市值最小的
    min_circulating_market