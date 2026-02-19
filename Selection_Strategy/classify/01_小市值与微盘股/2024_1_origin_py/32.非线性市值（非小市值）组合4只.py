# 克隆自聚宽文章：https://www.joinquant.com/post/42211
# 标题：非线性市值（非小市值）组合4只
# 作者：璐璐202006

import math
from jqdata import *
from pandas.core.frame import DataFrame
def initialize(context):
    # 设置系统参数
    set_option('use_real_price', True)
    set_slippage(PriceRelatedSlippage(0.00))
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),type='stock')
    # 初始化全局变量
    g.chosen_stock_list = []  # 选出的股票列表
    g.sold_stock = {}         # 已卖出股票列表
    g.buy_stock_count = 4    # 购买股票数量
#    g.increase1d = 0.06       # 1日涨幅限制
#    g.tradeday = 12          # 上市天数限制
#    g.buyagain = 31            # 再次购买间隔天数
    g.score = 7               # 股票评分
    g.buyrank = g.buy_stock_count * 2 #输出可买入列表的个数
    g.sellrank = g.buy_stock_count * 2# 筛选时保留的股票个数
    g.stock_selection_percent = 0.7  # 设置选取市值最大股票的百分比，1为全部。
    g.volume_days = 5         # 成交量天数
    g.increase_days = 60      # 涨幅天数
#    g.score_weights = [10,9,1,10,10]# [当前价格，成交量，涨幅天数，流通市值，总市值]
    g.score_weights = [2,1,1,4,4]# [当前价格，成交量，涨幅天数，流通市值，总市值]
    # 设置定时任务
    run_monthly(before_trading,1,'09:29')
    run_daily(mysell,'09:30')
    run_daily(mybuy,'09:31')
    # 设置日志级别
    log.set_level('order', 'error')
    log.set_level('system', 'error')
    log.set_level('history', 'error')
def select_top_percent_stocks(df, percent):
    """
    选择前N%的股票
    :param df: DataFrame，包含股票数据的数据帧
    :param percent: float，要选择的股票百分比，范围为0到1
    :return: DataFrame，包含所选股票的数据帧
    """
    top_percent = int(len(df) * percent)  # 计算前N%的股票数量
    return df.head(top_percent)  # 返回前N%的股票
# 每月运行，筛选股票
def before_trading(context):
#    temp = g.sold_stock  # 临时存储已卖出股票
#    g.sold_stock = {}  # 清空已卖出股票列表
#    for stock in temp.keys():# 判断已经卖出的股票是否达到了再次购买的条件
#        if temp[stock] >= g.buyagain - 1:
#            pass
#        else:
#            g.sold_stock[stock] = temp[stock] + 1
    g.chosen_stock_list = get_stock_list(context)  # 获取筛选后的股票列表
# 获取股票列表
def get_stock_list(context):
    # 从valuation表获取股票代码，并添加过滤条件
    q = query(
        valuation.code,
        valuation.pe_ratio,
        valuation.pb_ratio,
        indicator.inc_return,
        indicator.inc_total_revenue_year_on_year,
        indicator.inc_net_profit_year_on_year,
        valuation.market_cap   # 添加市值字段
    ).filter(
        valuation.pe_ratio > 0,
        valuation.pb_ratio > 0,
        indicator.inc_return > 0,
        indicator.inc_total_revenue_year_on_year > 0,
        indicator.inc_net_profit_year_on_year > 0
    )
    df = get_fundamentals(q)
    df = pd.DataFrame(df)
    df = df.dropna()
    df = df.sort_values(by='market_cap', ascending=False)  # 按市值从大到小排序
    print('本月股票总数: %s' % len(df))  # 输出符合条件的股票总数
    df = select_top_percent_stocks(df, g.stock_selection_percent)  # 调用全局函数，选取前N%的股票
    print('本月选中股票总数: {}% ({})'.format(g.stock_selection_percent * 100, len(df)))  # 输出选取的股票总数
    stock_list = list(df['code'])
    # 过滤股票
    stock_list = filter_st_stock(stock_list)
    stock_list = filter_paused_stock(stock_list)
    # stock_list = filter_new_stock(context, stock_list)
    stock_list = filter_limitup_stock(context, stock_list)
    stock_list = filter_limitdown_stock(context, stock_list)
    # stock_list = filter_increase1d(stock_list)
    # stock_list = filter_buyagain(stock_list)
    stock_list = filter_kcbj_stock(stock_list)
    stock_list = ffscore_stock(context, g.score, stock_list, context.current_dt.date())
    print('本月股票池 %s 个' % len(stock_list))
#    log.info("——————————————————————————————————")
#    for i, stock in enumerate(stock_list):
#        rank=i+1
#        name = get_security_info(stock).display_name
#        print("本月股票池第 {}：{} {}".format(rank, stock, name))
#    log.info("——————————————————————————————————")
    return stock_list

#   定义调仓策略：控制在设置的仓位比例附近，如果过多或过少则调整
def my_adjust_position(context, hold_stocks):
    free_value = context.portfolio.total_value
    maxpercent = 1.3 / g.buy_stock_count
    buycash = free_value / g.buy_stock_count
    for stock in context.portfolio.positions.keys():
        current_data = get_current_data()
        price1d = get_close_price(stock, 1)
        nosell_1 = context.portfolio.positions[stock].price >= current_data[stock].high_limit
        sell_2 = stock not in hold_stocks
        if sell_2 and not nosell_1:
            close_position(stock)
        else:
            current_percent = context.portfolio.positions[stock].value / context.portfolio.total_value
            if current_percent > maxpercent:order_target_value(stock, buycash)
#   卖出函数
def mysell(context):
    g.chosen_stock_list = get_stock_rank_m_m(g.chosen_stock_list)
    my_adjust_position(context, g.chosen_stock_list)
#   买入函数
def mybuy(context):
     # 获取已筛选股票列表
    hold_stocks = (g.chosen_stock_list)    
    # 检查持有股票的数量是否小于预期购买数量
    if len(hold_stocks) < g.buy_stock_count:
        g.buy_stock_count = len(hold_stocks)
        log.info("Adjusted buy_stock_count to {} as there are fewer stocks in hold_stocks.".format(g.buy_stock_count))
    # 获取可用资金和最小持仓比例
    free_value, minpercent = context.portfolio.total_value, 0.7 / g.buy_stock_count
    # 计算每只股票应购买金额
    buycash = free_value / g.buy_stock_count
    # 计算当前可用资金
    free_cash = free_value - context.portfolio.positions_value
    # 计算最小购买金额
    min_buy = context.portfolio.total_value / (g.buy_stock_count * 10)
    # 遍历持仓股票，尝试调整其持仓比例
    for i in range(g.buy_stock_count):
        # 如果已经持有了目标数量的股票，则退出循环
        if len(context.portfolio.positions) >= g.buy_stock_count:
            break
        # 获取当前循环股票
        stock = hold_stocks[i]
        # 如果当前可用资金小于最小购买金额，则退出循环
        if free_cash <= min_buy:
            break
        # 获取当前股票的持仓信息
        position = context.portfolio.positions.get(stock)
        # 如果已经持有该股票且其持仓比例已达到最小持仓比例，则继续循环
        current_percent = position.value / context.portfolio.total_value if position else 0
        if current_percent >= minpercent:
            continue
        # 计算应购买该股票的金额
        tobuy = min(free_cash, buycash - position.value) if position else min(buycash, free_cash)
        # 下单购买该股票
        order_value(stock, tobuy)
        # 更新可用资金
        free_cash -= tobuy
# 根据自定义评分排名筛选股票
def get_stock_rank_m_m(stock_list):
    rank_stock_list = DataFrame(stock_list)  # 将股票列表转换为DataFrame格式
    rank_stock_list.rename(columns={0: 'code'}, inplace=True)  # 重命名列名
    # 获取流通市值和总市值
    rank_stock_list['circulating_market_cap'] = [get_fundamentals(query(valuation).filter(valuation.code == stock)).iloc[0]['circulating_market_cap'] for stock in rank_stock_list['code']]
    rank_stock_list['market_cap'] = [get_fundamentals(query(valuation).filter(valuation.code == stock)).iloc[0]['market_cap'] for stock in rank_stock_list['code']]
    # 计算各项指标
    volume_days_sum = [attribute_history(stock, g.volume_days, '1d', 'volume', df=False)['volume'].sum() for stock in rank_stock_list['code']]
    increase_period = [get_growth_rate(g.increase_days, stock) for stock in rank_stock_list['code']]
    current_price = [get_close_price(stock, 1, '1m') for stock in rank_stock_list['code']]
    # 计算最小值
    min_price = min(current_price)
    min_increase_period = min(increase_period)
    min_volume = min(volume_days_sum)
    min_circulating_market_cap = min(rank_stock_list['circulating_market_cap'])
    min_market_cap = min(rank_stock_list['market_cap'])
    # 计算评分
    totalcount = [[i,
                   math.log(min_price / current_price[i]) * g.score_weights[0] +
                   math.log(min_volume / volume_days_sum[i]) * g.score_weights[1] +
                   math.log(min_increase_period / increase_period[i]) * g.score_weights[2] +
                   math.log(min_circulating_market_cap / rank_stock_list['circulating_market_cap'][i]) * g.score_weights[3] +
                   math.log(min_market_cap / rank_stock_list['market_cap'][i]) * g.score_weights[4]
                   ] for i in rank_stock_list.index]
    # 根据评分排序
    totalcount.sort(key=lambda x: x[1])
    # 选取排名靠前的股票
    # 保留最多g.sellrank设置的个数股票代码返回
    final_list = [rank_stock_list['code'][totalcount[-1 - i][0]] for i in range(min(g.sellrank, len(rank_stock_list)))]
    stock_list = final_list
#    log.info("——————————————————————————————————")
#    for i, stock in enumerate(stock_list[:g.buyrank]):
#        rank=i+1
#        name = get_security_info(stock).display_name
#        print("今日股票池第 {}：{} {}".format(rank, stock, name))
#    log.info("——————————————————————————————————")
    return stock_list
# 获取收盘价
def get_close_price(code, n, unit='1d'):
    return attribute_history(code, n, unit, 'close')['close'][0]
# 获取增长率
def get_growth_rate(days, code):
    try:
        price_period = attribute_history(code, days, '1d', 'close', False)['close'][0]
        pricenow = get_close_price(code, 1, '1m')
        if not math.isnan(pricenow) and not math.isnan(price_period) and price_period != 0:
            return pricenow / price_period
        else:
            return 100
    except Exception as e:
        print(f"Error calculating growth rate for stock {code}: {e}")
        return 100
# 定义平仓，卖出指定持仓
def close_position(code):
    order = order_target_value(code, 0)
    if order != None and order.status == OrderStatus.held:
        g.sold_stock[code] = 0
# 定义过滤停牌股票
def filter_paused_stock(stock_list):
	current_data = get_current_data()
	return [stock for stock in stock_list if not current_data[stock].paused]
# 定义过滤ST及其他具有退市标签的股票        
def filter_st_stock(stock_list):
    current_data = get_current_data()
    return [stock for stock in stock_list if not current_data[stock].is_st and 'ST' not in current_data[stock].name and '*' not in current_data[stock].name and '退' not in current_data[stock].name]
# 定义过滤涨停的股票
def filter_limitup_stock(context, stock_list):
    last_prices = history(1, unit='1m', field='close', security_list=stock_list)
    current_data = get_current_data()
    return [stock for stock in stock_list if stock in context.portfolio.positions.keys() 
        or last_prices[stock][-1] < current_data[stock].high_limit]
# 定义过滤跌停的股票
def filter_limitdown_stock(context, stock_list):
    last_prices = history(1, unit='1m', field='close', security_list=stock_list)
    current_data = get_current_data()
    return [stock for stock in stock_list if stock in context.portfolio.positions.keys()
			or last_prices[stock][-1] > current_data[stock].low_limit]
# 定义过滤次新股
def filter_new_stock(context, stock_list):
    return [stock for stock in stock_list if (context.previous_date - datetime.timedelta(days=g.tradeday)) > get_security_info(stock).start_date]
# 定义过滤昨日涨幅过高的股票    
def filter_increase1d(stock_list):
    return [stock for stock in stock_list if get_close_price(stock, 1) / get_close_price(stock, 2) < (1 + g.increase1d)]
# 定义过滤买过的股票
def filter_buyagain(stock_list):
    return [stock for stock in stock_list if stock not in g.sold_stock.keys()]
# 定义过滤科创北交股票
def filter_kcbj_stock(stock_list):
    for stock in stock_list[:]:
        if stock[0] == '4' or stock[0] == '8' or stock[:2] == '68':
            stock_list.remove(stock)
    return stock_list
# 定义过滤基本面股票    
def ffscore_stock(context,score,security_list,date):
    my_watch_date = date
    one_year_ago = my_watch_date - datetime.timedelta(days=365)
    h = get_history_fundamentals(security_list,
                             [indicator.adjusted_profit,
                              balance.total_current_assets,
                              balance.total_assets,
                              balance.total_current_liability,
                              balance.total_non_current_liability,
                              cash_flow.net_operate_cash_flow,
                              income.operating_revenue,
                              income.operating_cost,
                              ],
                             watch_date=my_watch_date, count=5).dropna()  # 连续的5个季度
    def ttm_sum(x):
        return x.iloc[1:].sum()
    def ttm_avg(x):
        return x.iloc[1:].mean()
    def pre_ttm_sum(x):
        return x.iloc[:-1].sum()
    def pre_ttm_avg(x):
        return x.iloc[:-1].mean()
    def val_1(x):
        return x.iloc[-1]
    def val_