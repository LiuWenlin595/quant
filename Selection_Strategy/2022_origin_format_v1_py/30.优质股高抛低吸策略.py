# 克隆自聚宽文章：https://www.joinquant.com/post/23312
# 标题：优质股高抛低吸策略
# 作者：chencongqun

from jqdata import *
import pandas as pd
from jqfactor import *
import numpy as np
import datetime

# 初始化函数，设定基准等等
def initialize(context):
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
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),
                   type='stock')

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
    # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    # 开盘时运行
    # run_daily(market_open, time='open', reference_security='000300.XSHG')
    # 收盘后运行
    run_daily(buy_or_sell, time='every_bar', reference_security='000300.XSHG')

    g.stock_list = []


def get_income_profit():
    q = query(
        indicator
    ).filter(
    )
    df = get_fundamentals(q)
    inc_total_revenue_year_on_year = {}
    inc_operation_profit_year_on_year = {}
    for index, row in df.iterrows():
        code = row['code']
        inc_total_revenue_year_on_year[code] = row['inc_total_revenue_year_on_year']
        inc_operation_profit_year_on_year[code] = row['inc_operation_profit_year_on_year']
    return inc_total_revenue_year_on_year, inc_operation_profit_year_on_year


def set_feasible_stocks(context, stock_list):
    set_universe(stock_list)
    current_data = get_current_data()
    stock_list_after_filter = []
    inc_total_revenue_year_on_year, inc_operation_profit_year_on_year = get_income_profit()
    st_dict = get_extras('is_st', stock_list, start_date=context.previous_date, end_date=context.previous_date,
                         df=True)

    # filter  paused / st / hight limit / low limit / bad profit
    for stock in stock_list:
        if st_dict[stock][0]:
            #log.info('stock %s st', stock)
            continue

        if inc_total_revenue_year_on_year.get(stock, -1) < 0:
            # log.info('inc_total_revenue_year_on_year not good')
            continue
        if inc_operation_profit_year_on_year.get(stock, -1) < 0:
            # log.info('inc_operation_profit_year_on_year not good')
            continue

        stock_list_after_filter.append(stock)
    # filter bad profit

    return stock_list_after_filter


def get_index_percent(context):
    end_date = context.previous_date
    start_date = end_date - datetime.timedelta(days=366)
    # 获取最近60天的指数数据
    sh_index = {}
    sz_index = {}
    price_list = get_price('000001.XSHG', start_date=start_date, end_date=end_date)
    last_value = 0
    for index, row in price_list.iterrows():
        if last_value == 0:
            last_value = row['close']
            continue
        sh_index[index] = round(((row['close'] - last_value) / last_value) * 100, 3)
        last_value = row['close']

    price_list = get_price('399001.XSHE', start_date=start_date, end_date=end_date)
    last_value = 0
    for index, row in price_list.iterrows():
        if last_value == 0:
            last_value = row['close']
            continue
        sz_index[index] = round(((row['close'] - last_value) / last_value) * 100, 3)
        last_value = row['close']
    return sh_index, sz_index


def get_stock_percent(context, stock_list):
    stock_percent = {}
    stock_last_prict = {}
    end_date = context.previous_date
    start_date = end_date - datetime.timedelta(days=366)
    price_list = get_price(stock_list, start_date=start_date, end_date=end_date, frequency='daily')
    close_price_list = price_list['close']
    for index, row in close_price_list.iterrows():
        for code in close_price_list.columns:
            if not (code in stock_percent.keys()):
                stock_percent[code] = {}
            last_price = stock_last_prict.get(code, 0)
            stock_last_prict[code] = row[code]
            if last_price == 0:
                continue
            stock_percent[code][index] = round(((row[code] - last_price) / last_price) * 100, 3)
    #log.info(stock_percent[stock_list[0]])
    return stock_percent


def calculate_strong_factor(context, stock_list):
    stock_factor_list = {}
    #end_date = context.previous_date
    #start_date = end_date - datetime.timedelta(days=61)

    previous_date_timestamp = pd.Timestamp(context.previous_date)
    # 获取最近60天的指数数据和股票行情数据
    log.info('start get data')
    sh_index, sz_index = get_index_percent(context)
    log.info('finish get index')
    stock_percent_dict = get_stock_percent(context, stock_list)
    log.info('finish get stock')
    for stock in stock_list:
        current_stock_data = stock_percent_dict.get(stock, None)
        if not current_stock_data:
            #log.info('stock %s has not data', stock)
            continue
        # 过滤涨跌盘
        if (current_stock_data[previous_date_timestamp] > 9) or (current_stock_data[previous_date_timestamp] < -9):
            #log.info('The previous date change too much %s', stock)
            continue
        #过滤过去10天涨跌幅度过大的股票
        previe_ten_percent = 0
        for i in range(10):
            current_dt = context.previous_date - datetime.timedelta(days=i)
            current_timestamp = pd.Timestamp(current_dt)
            current_percent = current_stock_data.get(current_timestamp, 0)
            if current_percent < 0:
                current_percent = -current_percent
            if ( stock == '603189.XSHG'):
                log.info(current_stock_data.get(current_timestamp, 0))
            previe_ten_percent += current_percent
        if (stock == '603189.XSHG'):
            log.info('previe_ten_percent %s' % previe_ten_percent)
        if (previe_ten_percent >= 30):
            log.info('The previous date change too much %s', stock)
            continue

        tmp_index = sh_index
        if stock.endswith('.XSHE'):
            tmp_index = sz_index
        count_good = 0
        count_bad = 0
        # 计算factor
        for key, value in current_stock_data.items():
            if value > tmp_index.get(key, 0):
                count_good += 1
            else:
                count_bad += 1
        stock_factor_list[stock] = count_good / (count_bad + count_good)
    #log.info(stock_factor_list)
    stock_after_sorted = sorted(stock_factor_list.items(), key=lambda d: d[1], reverse=True)
    stock_after_sorted_100 = stock_after_sorted[0:100]
    #log.info(stock_after_sorted_100)
    #return stock_after_sorted[0:100]
    stock_factor_list_100 = {}
    ts_21 = pd.Timestamp(context.previous_date - datetime.timedelta(days=21))
    #按最近20天再重新排序
    for stock, value in stock_after_sorted_100:
        current_stock_data = stock_percent_dict.get(stock, None)
        tmp_index = sh_index
        if stock.endswith('.XSHE'):
            tmp_index = sz_index
        count_good = 0
        count_bad = 0
        # 计算factor
        for key, value in current_stock_data.items():
            if key < ts_21:
                continue
            if value > tmp_index.get(key, 0):
                count_good += 1
            else:
                count_bad += 1
        stock_factor_list_100[stock] = count_good / (count_bad + count_good)
    stock_100_after_sorted = sorted(stock_factor_list_100.items(), key=lambda d: d[1], reverse=True)
    #log.info(stock_100_after_sorted)