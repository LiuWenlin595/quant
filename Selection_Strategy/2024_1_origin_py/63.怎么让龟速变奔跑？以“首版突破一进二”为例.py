# 克隆自聚宽文章：https://www.joinquant.com/post/45733
# 标题：怎么让龟速变奔跑？以“首版突破一进二”为例
# 作者：jqz1226

# 克隆自聚宽文章：https://www.joinquant.com/post/45724
# 标题：首版突破、一进二
# 作者：klaus5

from datetime import timedelta

from jqdata import *


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_option("match_by_signal", True)  # # 强制撮合

    # 过滤掉order系列API产生的比error级别低的log
    log.set_level('order', 'error')

    g.help_stock = {}  # dict：{股票代码：今日涨停价}
    g.max_stock_num = 20  # 持仓20只

    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    run_daily(market_run, time='every_bar', reference_security='000300.XSHG')


def market_run(context):
    # type: (Context) -> None
    time_now = context.current_dt.strftime('%H:%M:%S')
    if time_now <= '09:31:00':
        return

    # 1. 买入
    cash = context.portfolio.available_cash
    # 时间必须是9:32及以后，确保有2分钟的数据
    if cash > 5000 and len(context.portfolio.positions) < g.max_stock_num:
        bars = get_bars(list(g.help_stock.keys()), count=2, unit='1m', fields=['close'],
                        include_now=True, end_dt=context.current_dt)  # 过去2分钟的收盘价
        for stock in g.help_stock:
            if stock in context.portfolio.positions:
                continue
            close2m = bars[stock]['close']
            # 上一分钟没有涨停，本分钟涨停了
            if close2m[-2] < close2m[-1] == g.help_stock[stock]:
                function_buy(context, stock)

    # 2.卖出
    holdings = [s for s in context.portfolio.positions if context.portfolio.positions[s].closeable_amount > 0]
    if not holdings:
        return

    # 昨日数据
    df_pre = get_price(holdings, count=1, end_date=context.previous_date, frequency='daily',
                       fields=['close', 'high_limit'], panel=False).set_index('code')

    # 今天数据
    today_start = context.current_dt.replace(hour=9, minute=31, second=0)
    df_all_day = get_price(holdings, start_date=today_start, end_date=context.current_dt,
                           frequency='1m', fields=['high', 'close', 'high_limit'], panel=False)
    # 今日目前最高价
    s_high_today = df_all_day.groupby('code')['high'].max()
    # 今日目前涨停的分钟数
    s_count_limit_all_day = df_all_day.groupby('code').apply(lambda x: (x.close == x.high_limit).sum())
    # 今天前10分钟涨停的分钟数
    s_count_limit_first_10m = df_all_day.groupby('code').apply(lambda x: (x.close == x.high_limit)[:10].sum())

    curr_data = get_current_data()
    for stock in holdings:
        current_price = curr_data[stock].last_price
        day_open_price = curr_data[stock].day_open
        day_high_limit = curr_data[stock].high_limit
        day_low_limit = curr_data[stock].low_limit
        if current_price <= day_low_limit:  # 已经跌停，卖不掉了
            continue

        # 昨日收盘价，昨日涨停价
        pre_close = df_pre['close'][stock]
        pre_high_limit = df_pre['high_limit'][stock]

        # 今日数据
        high_all_day = s_high_today[stock]  # 今天最高价
        count_limit_all_day = s_count_limit_all_day[stock]
        count_limit_before10 = s_count_limit_first_10m[stock]
        # 成本数据
        cost = context.portfolio.positions[stock].avg_cost
        if current_price >= cost * 2:
            order_target(stock, 0)
        elif current_price < cost * 0.92 and current_price < day_open_price and pre_close == pre_high_limit:
            order_target(stock, 0)
        elif (current_price < cost * 0.97 and current_price < day_open_price and time_now >= '09:35:00' and
              pre_close < pre_high_limit):
            order_target(stock, 0)
        elif day_high_limit *