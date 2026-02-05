# 克隆自聚宽文章：https://www.joinquant.com/post/35521
# 标题：龙头战法之单阳不破
# 作者：游资小码哥

from jqdata import *
from jqlib.technical_analysis import *
# 初始化函数，设定基准等等
# 卖点设计
#1.早上开盘9点25的挂单成交量要是很少就直接卖
#2.早上10点之前要是大于8%然后回到5%以下就卖

#卖点设计
#1.成交量是前一分钟的6倍  2.成交量是前一分钟的10倍 并且当前一分钟大于1000万
#3.昨天的换手率要低于15%
def initialize(context):
   # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    set_slippage(PriceRelatedSlippage(0.0002),type='stock')

    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')
    # g 内置全局变量
    g.my_security = '510300.XSHG'
    set_universe([g.my_security])
    
    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    g.help_stock = []
    g.cash = context.portfolio.available_cash
    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
# 开盘时运行函数
def handle_tick(context, tick):
    #log.info('【market_run】')
    time_buy = context.current_dt.strftime('%H:%M:%S')
    current_data = get_current_data()
    end_date = (context.current_dt + timedelta(days = -1)).strftime("%Y-%m-%d")
    now = context.current_dt
    zeroToday = now - datetime.timedelta(hours=now.hour, minutes=now.minute, seconds=now.second,microseconds=now.microsecond)
    lastToday = zeroToday + datetime.timedelta(hours=9, minutes=31, seconds=00)
    if time_buy>='09:30:00':
        if len(context.portfolio.positions) > 0:
            for stock in context.portfolio.positions:
                if context.portfolio.positions[stock].closeable_amount > 0:
                    current_price = current_data[stock].last_price
                    day_open_price = current_data[stock].day_open
                    low_limit_price = current_data[stock].low_limit
                    high_limit_price = current_data[stock].high_limit
                    df_panel = get_price(stock, count = 1,end_date=end_date, frequency='daily', fields=['open', 'close','pre_close','high_limit','money','low'],skip_paused=True)
                    df_close = df_panel['close'].values
                    df_pre_close = df_panel['pre_close'].values
                    df_open = df_panel['open'].values
                    df_high_limit = df_panel['high_limit'].values
                    df_money = df_panel['money'].values
                    df_low = df_panel['low'].values
                    cost = context.portfolio.positions[stock].avg_cost
                    
                    df_panel_all = get_price(
                    stock, 
                    start_date=lastToday, 
                    end_date=context.current_dt, 
                    frequency='minute', 
                    fields=['high','low','close','high_limit','money','volume']
                )
                    df_min_low_all = df_panel_all.loc[:,"close"].min()
                    df_max_high_all = df_panel_all.loc[:,"close"].max()
                    money_all = df_panel_all.loc[:,"money"].sum()
                    volume_all = df_panel_all.loc[:,"volume"].sum()
                    
                    #分时均价线
                    minute_price = money_all / (volume_all+0.0001)
                    
                    if day_open_price < cost * 0.93:
                        order_target(stock, 0)
                        log.info('1.亏5个点卖出:' + str(stock))
                    elif day_open_price < cost * 0.97 and current_price > cost * 0.99:
                        order_target(stock, 0)
                        log.info('2.昨天的板是烂板:' + str(stock))
                    elif current_price < df_low and time_buy>='10:50:00' and current_price > low_limit_price and current_price > cost * 1.05 and df_close < df_high_limit * 0.98:
                        order_target(stock, 0)
                        log.info('3.小于昨天的最低点卖出:' + str(stock))
                    elif day_open_price > df_close * 1.06 and time_buy>='10:00:00' and current_price < day_open_price * 0.96 and current_price > low_limit_price:
                        order_target(stock, 0)
                        log.info('4.开盘价过高，低于开盘价四个点:' + str(stock))
                    elif current_price > cost * 1.20 and time_buy>='13:30:00' and df_max_high_all > df_close * 1.07 and current_price < df_max_high_all * 0.96 and df_max_high_all < high_limit_price:
                        order_target(stock, 0)
                        log.info('4.开盘价过高，低于开盘价四个点:' + str(stock))
                    elif df_close > cost * 1.20 and time_buy>='10:00:00' and day_open_price < df_close and current_price > df_close and current_price < df_close * 1.05:
                        order_target(stock, 0)
                        log.info('4.开盘价过高，低于开盘价四个点:' + str(stock))
                    elif df_close > cost * 1.20 and time_buy>='9:50:00' and current_price < minute_price and current_price < df_close * 1.05:
                        order_target(stock, 0)
                        log.info('4.开盘价过高，低于开盘价四个点:' + str(stock))

        
        stock = tick['code']
        limit_high = current_data[stock].high_limit
        now_peice = current_data[stock].last_price
        # if stock == '600096.XSHG' and time_buy>='13:05:00':
        #     log.info('【600096.XSHG】'+str(now_peice))
        if now_peice != limit_high and time_buy <= '13:30:00':
        
            sell_5 = tick['a5_p']
            sell_4 = tick['a4_p']
            sell_3 = tick['a3_p']
            sell_2 = tick['a2_p']
            sell_1 = tick['a1_p']
            if stock == '000966.XSHG' and time_buy<='09:35:00':
                log.info('【600096.XSHG】'+str(now_peice))
                log.info('【limit_high】'+str(limit_high))
                log.info('【sell_3】'+str(sell_3))
                log.info('【sell_2】'+str(sell_2))
                log.info('【sell_1】'+str(sell_1))
            if limit_high == sell_3 or limit_high == sell_2 or limit_high == sell_1:
                if stock not in context.portfolio.positions:
                    new_peice = current_data[stock].last_price
                    if context.portfolio.available_cash > 5000: 
                        if g.cash > new_peice*100:
                            # cash_buy = 0
                            # if len(context.portfolio.positions) == 0:
                            #     cash_buy = g.cash / 2
                            # elif len(context.portfolio.positions) == 1:
                            #     cash_buy = g.cash
                            order_count = (int(g.cash // (new_peice*100))) * 100
                            log.info('---------买入股票:' + str(stock) +', 金额:'+ str(int(new_peice*order_count)))
                            order_target(stock, order_count)
                            #order_target(stock, 100)

# 开盘前运行函数 选择二板放量股 并且横盘震荡
def before_trading_start(context):
    
    date_now = (context.current_dt + timedelta(days = -1)).strftime("%Y-%m-%d")#'2021-01-15'#datetime.datetime.now()
    yesterday = (context.current_dt + timedelta(days = -60)).strftime("%Y-%m-%d")
    trade_date = get_trade_days(start_date=yesterday, end_date=date_now, count=None)
    
    ##查询所有股票的当天的涨停板
    stocks = list(get_all_securities(['stock']).index)
    end_date=trade_date[trade_date.size-1]
    ##去除st的连板股票
    tmpList = filter_st(stocks)
    #tmpList = filter_stock_by_days(context, tmpList_st, 1080)
    ##查询所有股票的当天的涨停板
    pre_date=trade_date[trade_date.size-2]
    pre_date_20=trade_date[trade_date.size-20]
    ##查看股票前期是否平整，并且股票第一个板要高过一年的最高收盘价
    for stock_flat in tmpList:
        if stock_flat == '002900.XSHE':
            print("----002900.XSHE-----")
        if stock_flat[0:3] != '300' and stock_flat[0:3] != '688':
            bool_result = filter_flat_stock(stock_flat,end_date,pre_date,pre_date_20)
            if bool_result == True:
                g.help_stock.append(stock_flat)
    subscribe(g.help_stock,'tick')
    print("----------------最后被选出的股票-----------")
    print(g.help_stock)
    # log.info('g.yest_df_panel')
    # log.info(g.yest_df_panel['high'])

#去除st的股票
def filter_st(codelist):
    current_data = get_current_data()
    codelist = [code for code in codelist if not current_data[code].is_st]
    return codelist

# 查看股票前期是否平整 且两板的最高点是否超过其他的最高点
def filter_flat_stock(stock,end_date,pre_date,pre_date_20):
    #查询昨天的涨停价格
    df_panel = get_price(stock, count = 1,end_date=end_date, frequency='daily', fields=['open', 'close','high_limit','money'],skip_paused=True)
    df_close = df_panel['close'].values
    df_open = df_panel['open'].values
    df_high_limit