# 克隆自聚宽文章：https://www.joinquant.com/post/49434
# 标题：首板低开策略-终极版  最大回撤15%，年化50%
# 作者：蓝猫量化

# 导入函数库
from jqlib.technical_analysis import *
from jqfactor import *
from jqdata import *
import datetime as dt
import pandas as pd


# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    
    run_daily(sell_if_limit_down_yesterday, '09:30')
    run_daily(buy, '09:30')
    run_daily(sell, '11:25')
    run_daily(sell, '14:30')


def buy(context):
    # 基础信息
    date = get_previous_trade_day(context, 0)
    stock_list_with_ST = prepare_stock_list(context)
    stock_list_not_ST = prepare_stock_list2(context)

    stock_list = stock_list_with_ST+stock_list_not_ST

    if len(stock_list) > 0:
        print(f"今日待选池为：{stock_list}")
        # 获取当前账户的现金余额
        cash = context.portfolio.cash
        # 买入
        if cash > 0:
            for s in stock_list:
                order_target_value(s, cash / len(stock_list))
                print('买入', [get_security_info(s, date).display_name, s])
                print('———————————————————————————————————')
        else:
            print("当前账户没有现金,无法买入")


def sell(context):
    # 基础信息
    date = get_previous_trade_day(context, 0)
    current_data = get_current_data()

    # 根据时间执行不同的卖出策略
    if str(context.current_dt)[-8:] == '11:25:00':
        for s in list(context.portfolio.positions):
            if ((context.portfolio.positions[s].closeable_amount != 0) and
                    (current_data[s].last_price < current_data[s].high_limit) and
                    (current_data[s].last_price > context.portfolio.positions[s].avg_cost)):
                order_target_value(s, 0)
                print('止盈卖出', [get_security_info(s, date).display_name, s])
                print('———————————————————————————————————')

    if str(context.current_dt)[-8:] == '14:30:00':
        for s in list(context.portfolio.positions):
            if ((context.portfolio.positions[s].closeable_amount != 0) and
                    (current_data[s].last_price < current_data[s].high_limit)):
                order_target_value(s, 0)
                if current_data[s].last_price > context.portfolio.positions[s].avg_cost:
                    print('止盈卖出', [get_security_info(s, date).display_name, s])
                    print('———————————————————————————————————')
                else:
                    print('止损卖出', [get_security_info(s, date).display_name, s])
                    print('———————————————————————————————————')

def sell_if_limit_down_yesterday(context):
    # 获取持仓股票列表
    positions = context.portfolio.positions
    
    # 获取昨天的日期
    yesterday = get_previous_trade_day(context, 1)
    
    # 遍历持仓股票
    for stock in positions:
        # 获取持仓股票的成本价和当前可卖出数量
        avg_cost = positions[stock].avg_cost
        closeable_amount = positions[stock].closeable_amount
        
        # 获取昨天的价格数据
        stock_data = get_price(stock, end_date=yesterday, count=1, fields=['close', 'low', 'low_limit'])
        
        if not stock_data.empty:
            close_price = stock_data['close'].iloc[0]
            low_price = stock_data['low'].iloc[0]
            low_limit = stock_data['low_limit'].iloc[0]
            
            # 判断是否跌停
            if close_price == low_limit and low_price == low_limit:
                order_target_value(stock, 0)
                log.info(f'股票 {stock} 昨日跌停，触发风控止损卖出')
                continue
            
            # 判断亏损是否超过 4%
            loss_ratio = (close_price - avg_cost) / avg_cost * 100
            if loss_ratio <= -4:
                order_target_value(stock, 0)
                log.info(f'股票 {stock} 亏损超过阈值，触发风控止损卖出')
        else:
            log.warning(f'无法获取 {stock} 的价格数据')
            
# 每日初始股票池
def prepare_stock_list(context):
    # 获取交易日
    date = get_previous_trade_day(context, 0)
    last_date = get_previous_trade_day(context, 1)
    last_last_date = get_previous_trade_day(context, 2)

    # 获取所有股票
    stock_list = get_all_securities('stock', last_date).index.tolist()
    # 筛选涨停股票
    stock_list = get_limit_up_stock(stock_list, last_date)
    # 过滤次新股
    stock_list = filter_new_stock(stock_list, last_date)
    # 过滤非ST股
    stock_list = filter_st_stock(stock_list, last_date)
    # 今日低开
    stock_list = filter_stocks_by_opening_range(date, stock_list)
    # 计算N日无涨停
    stock_list = get_no_limit_up_stocks(last_last_date, 1, stock_list)
    # 计算相对位置
    stock_list = get_relative_position_stocks(last_date, 15, stock_list)

    return stock_list

def prepare_stock_list2(context):
    # 获取交易日
    date = get_previous_trade_day(context, 0)
    last_date = get_previous_trade_day(context, 1)
    last_last_date = get_previous_trade_day(context, 2)

    # 获取所有股票
    stock_list = get_all_securities('stock', last_date).index.tolist()
    # 筛选涨停股票
    stock_list = get_limit_up_stock2(stock_list, last_date)
    # 过滤次新股
    stock_list = filter_new_stock2(stock_list, last_date)
    # 过滤ST股
    stock_list = filter_st_stock2(stock_list