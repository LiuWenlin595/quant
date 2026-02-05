# 克隆自聚宽文章：https://www.joinquant.com/post/45425
# 标题：分享一种K线小碎步后突破的分钟级打法
# 作者：画家

from jqlib.technical_analysis import *
from jqfactor import *
from jqdata import *
import datetime as dt
import pandas as pd



def initialize(context):
    # 系统设置
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)   
    log.set_level('system', 'error')

    # 最大持股数
    g.max_hold_num = 5
    g.prepare_stocks = []
    # 每天选出的待买股票
    g.chosen_stocks = []
    g.holdable_days = 6  # 可持股天数
    # 持股天数
    g.hold_days = {}
    # 待卖股
    g.need_sell = set()


    run_daily(change_hold_info, time='8:30')
    run_daily(prepare_stocks, '9:05')
    run_daily(market_open, time='every_bar')
    run_daily(do_sell, time='14:40')
    run_daily(do_sell2, time='9:30')
    # run_daily(sell, '11:28')

# 早盘卖出昨天没有卖出的满足条件的股票
def do_sell2(context):
    if len(context.portfolio.positions) < 1:
        log.info("空仓没什么可卖的")
        return

    pos = context.portfolio.positions
    for stock in g.need_sell.copy():
        if close_position(pos[stock]):
            g.need_sell.remove(stock)


# 判断是否涨停
def is_limitup(stock):
    current_data = get_current_data()
    return current_data[stock].last_price >= current_data[stock].high_limit

def check_hold_days(position):
    stock = position.security
    cost = position.avg_cost
    price = position.price
    ret = 100 * (price / cost - 1)
    return ret < 5 and g.hold_days[stock] > g.holdable_days

def check_earn(position, rate):
    cost = position.avg_cost
    price = position.price
    ret = 100 * (price / cost - 1)
    return ret > rate

def check_lose(position):
    cost = position.avg_cost
    price = position.price
    ret = 100 * (price / cost - 1)
    return ret <= -6

# 拉尖峰回落卖出
def scream_sell(stock, date_time, current_price, down_range=3):
    cnt = 15  # 每天210min的交易时间按15min进行划分
    df = get_price(stock, count=cnt, end_date=date_time, frequency='15m',
                   fields=['open', 'close', 'high', 'low'])
    pre_close_price = df['close'][0]
    high_price = df['high'][1:].max()
    flag = False
    for i in range(1, 15):
        if df['high'][i] / df['high'][i-1] - 1 > 0.05:
            flag = True
            break

    high2low_length = (high_price - current_price) / pre_close_price * 100

    return high2low_length > down_range and flag

def check_hold_days(position):
    stock = position.security
    cost = position.avg_cost
    price = position.price
    ret = 100 * (price / cost - 1)
    return ret < 5 and g.hold_days[stock] > g.holdable_days

# 卖出
def do_sell(context):

    if len(context.portfolio.positions) < 1:
        log.info("空仓没什么可卖的")
        return

    pre_date = context.previous_date
    date_time = context.current_dt + datetime.timedelta(minutes=-10)

    pos = context.portfolio.positions
    for stock in pos:
        # 没有可卖的，比如当天买的当天不能卖
        if pos[stock].closeable_amount <= 0:
            continue
        # 涨停不卖
        if is_limitup(stock):
            log.info("%s 涨停的不卖" % stock)
            continue

        # 还在选股范围内的不卖, 因为卖在选股后
        if stock in g.chosen_stocks:
            log.info("%s 还在选股范围内的不卖" % stock)
            continue

        if check_earn(pos[stock], 12) and scream_sell(stock, date_time, pos[stock].price):
            log.info("卖出{}, scream_sell".format(stock))
            g.need_sell.add(stock)

        # 超过持股天数且一直不盈利卖出
        if check_hold_days(pos[stock]):
            log.info("卖出{}, check_hold_days".format(stock))
            g.need_sell.add(stock)

        if stock in pos and big_volume_sell(stock, pos[stock].price, context):
            log.info("卖出{}, big_volume_sell".format(stock))
            g.need_sell.add(stock)

        # if check_lose(pos[stock]):
        #     log.info("卖出{}, check_lose".format(stock))
        #     g.need_sell.add(stock)

        if check_earn(pos[stock], 15):
            log.info("卖出{}, check_earn".format(stock))
            g.need_sell.add(stock)

    for stock in g.need_sell.copy():
        if close_position(pos[stock]):
            g.need_sell.remove(stock)


def prepare_stocks(context):
    # 优化回测速度, 满仓状态不选股
    if len(context.portfolio.positions) >= g.max_hold_num:
        g.prepare_stocks = []
        log.info("满仓中")
        return

    # 文本日期
    date = context.previous_date
    date = transform_date(date, 'str')
    # 初始列表
    initial_list = prepare_stock_list(date)
    q = query(valuation.code,valuation.circulating_market_cap,indicator.eps).filter(valuation.code.in_(initial_list), valuation.circulating_market_cap < 25)
    df = get_fundamentals(q)
    lst = list(df['code'])
    lst = get_hl_stock(lst, date, 300)
    
    lst = get_no_hl_stock(lst, date, 30)

    lst = filter_amp(lst, date, 15)

    df = upward(lst, date, 15)
    lst = list(df.index)

    lst = approaching_max(lst, date, 60)

    g.prepare_stocks = lst

def market_open(context):
    # 优化回测速度, 满仓状态不选股
    if len(context.portfolio.positions) >= g.max_hold_num:
        g.chosen_stocks = []
        log.info("满仓中")
        return

    lst = g.prepare_stocks
    current_data = get_current_data()
    for s in lst:
        if s in list(context.portfolio.positions):
            continue
        if current_data[s].high_limit * 0.945 < current_data[s].last_price < current_data[s].high_limit * 0.975:
            # print(s)
            # print(context.current_dt)
            # print(current_data[s].last_price)
            g.chosen_stocks.append(s)

    do_buy(context)



def sell(context):
    # 基础信息
    date = transform_date(context.previous_date, 'str')
    current_data = get_current_data()
    
    # 根据时间执行不同的卖出策略
    if str(context.current_dt)[-8:] == '11:28:00':
        for s in list(context.portfolio.positions):
            if ((context.portfolio.positions[s].closeable_amount != 0) and (current_data[s].last_price < current_data[s].high_limit) and (current_data[s].last_price > 1.1* context.portfolio.positions[s].avg_cost)):
                order_target_value(s, 0)
                print( '止盈卖出', [get_security_info(s, date).display_name, s])
                print('———————————————————————————————————')
                del_holds(s)


def del_holds(s):
    for k in list(g.holds.keys()):
        if s in g.holds[k]:
            g.holds[k].remove(s)
    for k in list(g.holds.keys()):
        if len(g.holds[k]) == 0:
            del g.holds[k]



def daily_adjustment(context):
    current_data = get_current_data()
    date = transform_date(context.previous_date, 'str')

    #调仓卖出
    if len(g.holds.keys()) > 0:
        for key in list(g.holds.keys()):
            if key not in g.industry_stocks:
                for s in g.holds[key]:
                    if ((context.portfolio.positions[s].closeable_amount != 0) and (current_data[s].last_price < current_data[s].high_limit)):
                        order_target_value(s, 0)
                        print( '调仓卖出', [get_security_info(s, date).display_name, s])
                        print('———————————————————————————————————')
                        del_holds(s)

    # 调仓买入
    # 基础信息
    if g.industry_stocks=={} or len(g.industry_stocks)<1:
        return 
    position_count = len(context.portfolio.positions)

    if  g.num > position_count:
        target_num = g.num - position_count
        value = context.portfolio.available_cash / target_num


        for key in g.industry_stocks:
            stock_list = g.industry_stocks[key]
            df =  get_price(stock_list, end_date=date, frequency='daily', fields=['close'], count=1, panel=False, fill_paused=False, skip_paused=True).set_index('code') if len(stock_list) != 0 else pd.DataFrame()
            df['open_pct'] = [current_data[s].day_open/df.loc[s, 'close'] for s in stock_list]
            df = df[(0.97 <= df['open_pct']) & (df['open_pct'] <= 1.02)] 
            stock_list = list(df.index)
            for s in stock_list:
                if context.portfolio.positions[s].total_amount == 0:
                    order_target_value(s, value)
                    print( '买入', [get_security_info(s, date).display_name, s])
                    print('———————————————————————————————————')
                    if key in g.holds:
                        g.holds[key].append(s)
                    else:
                        g.holds[key] = [s]
                    target_num = target_num - 1
                    if target_num < 1:
                        break;
            if target_num < 1:
                break;

# # 调整昨日涨停股票
# def check_limit_up(context):
#     now_time = context.current_dt
#     if g.yesterday_HL_list != []:
#         #对昨日涨停股票观察到尾盘如不涨停则提前卖出，如果涨停即使不在应买入列表仍暂时持有
#         for stock in g.yesterday_HL_list:
#             current_data = get_price(stock, end_date=now_time, frequency='1m', fields=['close','high_limit'], skip_paused=False, fq='pre', count=1, panel=False, fill_paused=True)
#             if current_data.iloc[0,0] <    current_data.iloc[0,1]:
#                 log.info("[%s]涨停打开，卖出" % (stock))
#                 position = context.portfolio.positions[stock]
#                 close_position(position)
#             else:
#                 log.info("[%s]涨停，继续持有" % (stock))



############################################################################################################################################################################

# 买入
def do_buy(context):
    hold_num = len(context.portfolio.positions)

    if hold_num >= g.max_hold_num:
        log.info("满仓中")
        return

    holdable_num = g.max_hold_num - hold_num
    cash = context.portfolio.available_cash / holdable_num

    current_data = get_current_data()

    chosen_stocks = g.chosen_stocks

    for stock in chosen_stocks:
        # 不再买已经持有的股票
        if stock in context.portfolio.positions:
            log.info("不买已经持有的股票%s" % stock)
            continue

        if stock in g.need_sell:
            log.info("不买满足卖出条件没有卖出的股票%s" % stock)
            continue

        if ((context.portfolio.positions[stock].closeable_amount != 0) and (current_data[s].last_price < current_data[stock].high_limit)):
            log.info("已经涨停无法买入%s" % stock)
            continue

        if open_position(stock, cash):
            if len(context.portfolio.positions) >= g.max_hold_num:
                break

# 交易模块-开仓
def open_position(s, value):

    order = order_target_value_(s, value)
    if order != None and order.filled > 0:
        add_hold_info(s)
        return True
    return False

# 交易模块-自定义下单
def order_target_value_(security, value):
    if value == 0:
        log.debug("Selling out %s" % (security))
    else:
        log.debug("Order %s to value %f" % (security, value))
    return order_target_value(security, value)


# 处理日期相关函数
def transform_date(date, date_type):
    if type(date) == str:
        str_date = date
        dt_date = dt.datetime.strptime(date, '%Y-%m-%d')
        d_date = dt_date.date()
    elif type(date) == dt.datetime:
        str_date = date.strftime('%Y-%m-%d')
        dt_date = date
        d_date = dt_date.date()
    elif type(date) == dt.date:
        str_date = date.strftime('%Y-%m-%d')
        dt_date = dt.datetime.strptime(str_date, '%Y-%m-%d')
        d_date = date
    dct = {'str':str_date, 'dt':dt_date, 'd':d_date}
    return dct[date_type]


# 筛选出一段时间有涨停的股票
def get_hl_stock(initial_list, date, watch_days=1):
    df = get_price(initial_list, end_date=date, frequency='daily', fields=['close','high_limit'], count=watch_days, panel=False, fill_paused=False, skip_paused=False)
    df = df.dropna() #去除停牌
    df = df[df['close'] == df['high_limit']]
    hl_list = list(set(df.code))
    return hl_list

# 筛选出一段时间没有涨停的股票
def get_no_hl_stock(initial_list, date, watch_days=1):
    df = get_price(initial_list, end_date=date, frequency='daily', fields=['close','high_limit'], count=watch_days, panel=False, fill_paused=False, skip_paused=False)
    df = df.dropna() #去除停牌
#     df = df[df['close'] == df['high_limit']]
    df = df[df['close'] > 0.95*df['high_limit']]
    hl_list = list(set(df.code))
    lst = [s for s in initial_list if s not in hl_list]
    return lst

# 每日初始股票池
def prepare_stock_list(date): 
    initial_list = get_all_securities('stock', date).index.tolist()
    initial_list = filter_kcbj_stock(initial_list)
    initial_list = filter_new_stock(initial_list, date)
    initial_list = filter_st_stock(initial_list, date)
    initial_list = filter_paused_stock(initial_list, date)
    return initial_list

# 过滤函数
def filter_new_stock(initial_list, date, days=100):
    d_date = transform_date(date, 'd')
    return [stock for stock in initial_list if d_date - get_security_info(stock).start_date > dt.timedelta(days=days)]

def filter_st_stock(initial_list, date):
    str_date = transform_date(date, 'str')
    if get_shifted_date(str_date, 0, 'N') != get_shifted_date(str_date, 0, 'T'):
        str_date = get_shifted_date(str_date,