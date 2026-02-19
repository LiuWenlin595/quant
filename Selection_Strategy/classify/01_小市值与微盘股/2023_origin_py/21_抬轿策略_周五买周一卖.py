# 抬轿策略：博弈「小市值适配因子」周一调仓资金
# 逻辑：与原策略 21.截止到21年12月依然有效的小市值适配因子 使用相同选股规则，
#       在原策略调仓日（周一 9:30）的前一交易日（周五）买入同一批标的，
#       在周一他们买完之后（10:00）卖出，吃其买盘带来的抬轿效应。
# 注意：周五选股用周四数据（previous_date），原策略周一用周五数据，标的池可能略有重叠差异。

from jqdata import *
from jqfactor import get_factor_values
import numpy as np
import pandas as pd


def initialize(context):
    set_benchmark('000905.XSHG')
    set_option('use_real_price', True)
    set_option("avoid_future_data", True)
    set_slippage(FixedSlippage(0))
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, close_today_commission=0, min_commission=5), type='fund')
    log.set_level('order', 'error')
    g.stock_num = 5
    # 周五收盘前（14:50）：先卖上一批，再按「同日选股逻辑」买入本周标的，减少开盘时段其他因素干扰
    run_weekly(friday_buy_after_sell, weekday=5, time='14:55', reference_security='000300.XSHG')
    # 周一 10:00：在他们 9:30 买完之后卖出，吃抬轿
    run_weekly(monday_sell_after_them_buy, weekday=1, time='10:00', reference_security='000300.XSHG')
    run_daily(print_position_info, time='15:10', reference_security='000300.XSHG')


# ---------- 选股（与原策略完全一致，保证标的池一致） ----------
def get_factor_filter_list(context, stock_list, jqfactor, sort, p1, p2):
    yesterday = context.previous_date
    score_list = get_factor_values(stock_list, jqfactor, end_date=yesterday, count=1)[jqfactor].iloc[0].tolist()
    df = pd.DataFrame(columns=['code', 'score'])
    df['code'] = stock_list
    df['score'] = score_list
    df = df.dropna()
    df.sort_values(by='score', ascending=sort, inplace=True)
    filter_list = list(df.code)[int(p1*len(stock_list)):int(p2*len(stock_list))]
    return filter_list


def get_stock_list(context):
    initial_list = get_all_securities().index.tolist()
    initial_list = filter_new_stock(context, initial_list)
    initial_list = filter_kcb_stock(context, initial_list)
    initial_list = filter_st_stock(initial_list)
    x_list = get_factor_filter_list(context, initial_list, 'sales_growth', False, 0, 0.1)
    q = query(valuation.code, valuation.circulating_market_cap, indicator.eps).filter(valuation.code.in_(x_list)).order_by(valuation.circulating_market_cap.asc())
    df = get_fundamentals(q)
    df = df[df['eps'] > 0]
    final_list = list(df.code)
    return final_list


# ---------- 过滤（与原策略一致） ----------
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
    return [stock for stock in stock_list if stock[0:3] != '688']


def filter_new_stock(context, stock_list):
    yesterday = context.previous_date
    return [stock for stock in stock_list if not yesterday - get_security_info(stock).start_date < datetime.timedelta(days=250)]


# ---------- 交易 ----------
def order_target_value_(security, value):
    if value == 0:
        log.debug("Selling out %s" % (security))
    else:
        log.debug("Order %s to value %f" % (security, value))
    return order_target_value(security, value)


def open_position(security, value):
    order = order_target_value_(security, value)
    if order is not None and order.filled > 0:
        return True
    return False


def close_position(position):
    security = position.security
    order = order_target_value_(security, 0)
    if order is not None:
        if order.status == OrderStatus.held and order.filled == order.amount:
            return True
    return False


def friday_buy_after_sell(context):
    """周五 14:50（收盘前）：先清仓（卖上一周持仓），再按同日选股规则买入本周标的。"""
    # 1) 先卖光
    for position in list(context.portfolio.positions.values()):
        close_position(position)
    # 2) 取池子并过滤（与原策略相同规则，当日 previous_date=周四）
    check_out_list = get_stock_list(context)
    check_out_list = filter_limitup_stock(context, check_out_list)
    check_out_list = filter_limitdown_stock(context, check_out_list)
    check_out_list = filter_paused_stock(check_out_list)
    buy_stocks = check_out_list[:g.stock_num]
    if not buy_stocks:
        return
    # 3) 等权买入
    value = context.portfolio.available_cash / len(buy_stocks)
    for stock in buy_stocks:
        if stock not in context.portfolio.positions or context.portfolio.positions[stock].total_amount == 0:
            if open_position(stock, value):
                if len(context.portfolio.positions) >= g.stock_num:
                    break


def monday_sell_after_them_buy(context):
    """周一 10:00：在他们 9:30 买完之后全部卖出。"""
    for position in list(context.portfolio.positions.values()):
        close_position(position)


# ---------- 复盘 ----------
def print_position_info(context):
    trades = get_trades()
    for _trade in trades.values():
        print('成交记录：' + str(_trade))
    for position in list(context.portfolio.positions.values()):
        securities = position.security
        cost = position.avg_cost
        price = position.price
        ret = 100 * (price / cost - 1)
        value = position.value
        amount = position.total_amount
        print('代码:{}'.format(securities))
        print('成本价:{}'.format(format(cost, '.2f')))
        print('现价:{}'.format(price))
        print('收益率:{}%'.format(format(ret, '.2f')))
        print('持仓(股):{}'.format(amount))
        print('市值:{}'.format(format(value, '.2f')))
        print('———————————————————————————————————')
    print('———————————————————————————————————————分割线————————————————————————————————————————')
