# 克隆自聚宽文章：https://www.joinquant.com/post/35141
# 标题：多策略融合-80倍-无未来函数
# 作者：游资小码哥

# 导入函数库
from jqdata import *
from jqlib.technical_analysis import *

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
    # g 内置全局变量
    g.my_security = '510300.XSHG'
    set_universe([g.my_security])
    
    g.help_stock_four = []
    g.help_stock_four_sell = []
    
    g.help_stock_five = []
    g.help_stock_five_sell = []
    
    g.help_stock_seven = []
    g.help_stock_seven_sell = []
    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
    run_daily(before_market_open_all, time='before_open', reference_security='000300.XSHG')
      # 开盘时运行
    run_daily(market_open, time='every_bar', reference_security='000300.XSHG')
    #run_daily(market_run_sell, time='every_bar', reference_security='000300.XSHG')
    
    #收盘后运行before_open
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')
    

def before_market_open_all(context):
    before_market_open_four(context)
    before_market_open_five(context)
    before_market_open_seven(context)
    
    help_stock_msg = "今日选出股票："
    help_stock_msg_four = "--连扳分歧战法："
    help_stock_msg_five = "--龙头底分型战法："
    help_stock_msg_seven = "--缩量分歧反包战法："

    if len(g.help_stock_four) > 0:
        for stock in g.help_stock_four:
            help_stock_msg_four = help_stock_msg_four + stock + "; "
        help_stock_msg = help_stock_msg + help_stock_msg_four

    if len(g.help_stock_five) > 0:
        for stock in g.help_stock_five:
            help_stock_msg_five = help_stock_msg_five + stock + "; "
        help_stock_msg = help_stock_msg + help_stock_msg_five
        
    if len(g.help_stock_seven) > 0:
        for stock in g.help_stock_seven:
            help_stock_msg_seven = help_stock_msg_seven + stock + "; "
        help_stock_msg = help_stock_msg + help_stock_msg_seven
            
    # sell类型     
    help_stock_msg_sell = "#今日持仓的股票："
    help_stock_msg_four_sell = "--连扳分歧战法："
    help_stock_msg_five_sell = "--龙头底分型战法："
    help_stock_msg_seven_sell = "--三阳三阴战法："

    if len(g.help_stock_four_sell) > 0:
        for stock in g.help_stock_four_sell:
            help_stock_msg_four_sell = help_stock_msg_four_sell + stock + "; "
        help_stock_msg_sell = help_stock_msg_sell + help_stock_msg_four_sell

    if len(g.help_stock_five_sell) > 0:
        for stock in g.help_stock_five_sell:
            help_stock_msg_five_sell = help_stock_msg_five_sell + stock + "; "
        help_stock_msg_sell = help_stock_msg_sell + help_stock_msg_five_sell
        
    
    if len(g.help_stock_seven_sell) > 0:
        for stock in g.help_stock_seven_sell:
            help_stock_msg_seven_sell = help_stock_msg_seven_sell + stock + "; "
        help_stock_msg_sell = help_stock_msg_sell + help_stock_msg_seven_sell
        
    ##每日买卖持仓
    print(help_stock_msg)
    print(help_stock_msg_sell)


## 开盘时运行函数
def market_open(context):
    
    #三虎 三板确定性买入法
    market_open_four(context)
    
    #四虎 龙头底分型
    market_open_five(context)
    
    #七龙珠 缩量分歧反包战法
    market_open_seven(context)


##三虎 三板确定性买入法
## 开盘时运行函数
def market_open_four(context):
    time_buy = context.current_dt.strftime('%H:%M:%S')
    aday = datetime.datetime.strptime('13:00:00', '%H:%M:%S').strftime('%H:%M:%S')
    if len(g.help_stock_four) > 0 :
        for stock in g.help_stock_four:
            #log.info("当前时间 %s" % (context.current_dt))
            #log.info("股票 %s 的最新价: %f" % (stock, get_current_data()[stock].last_price))
            cash = context.portfolio.available_cash
            #print(cash)
            day_open_price = get_current_data()[stock].day_open
            current_price = get_current_data()[stock].last_price
            high_limit_price = get_current_data()[stock].high_limit
            pre_date =  (context.current_dt + timedelta(days = -1)).strftime("%Y-%m-%d")
            df_panel = get_price(stock, count = 1,end_date=pre_date, frequency='daily', fields=['open', 'high', 'close','low', 'high_limit','money','pre_close'])
            pre_high_limit = df_panel['high_limit'].values
            pre_close = df_panel['close'].values
            pre_open = df_panel['open'].values
            pre_high = df_panel['high'].values
            pre_low = df_panel['low'].values
            pre_pre_close = df_panel['pre_close'].values
            
            now = context.current_dt
            zeroToday = now - datetime.timedelta(hours=now.hour, minutes=now.minute, seconds=now.second,microseconds=now.microsecond)
            lastToday = zeroToday + datetime.timedelta(hours=9, minutes=31, seconds=00)
            df_panel_allday = get_price(stock, start_date=lastToday, end_date=context.current_dt, frequency='minute', fields=['close','high_limit'])
            low_allday = df_panel_allday.loc[:,"close"].min()
            high_allday = df_panel_allday.loc[:,"close"].max()
            sum_plus_num_two = (df_panel_allday.loc[:,'close'] == df_panel_allday.loc[:,'high_limit']).sum()
            
            pre_date_two =  (context.current_dt + timedelta(days = -10)).strftime("%Y-%m-%d")
            df_panel_150 = get_price(stock, count = 150,end_date=pre_date_two, frequency='daily', fields=['open', 'close','high_limit','money','low','high','pre_close'])
            df_max_high_150 = df_panel_150["close"].max()
            ##当前持仓有哪些股票
            if cash > 20000 :

                if sum_plus_num_two > 10 and current_price < high_limit_price and current_price > pre_close * 1.08:
                    print("1."+stock+"买入金额"+str(cash))
                    orders = order_value(stock, cash)
                    if str(orders.status) == 'held':
                        g.help_stock_four.remove(stock)
                        g.help_stock_four_sell.append(stock)
                elif day_open_price > pre_close * 1.05 and current_price > day_open_price * 1.02 and current_price > df_max_high_150 and current_price < high_limit_price:
                    print("2."+stock+"买入金额"+str(cash))
                    orders = order_value(stock, cash)
                    if str(orders.status) == 'held':
                        g.help_stock_four.remove(stock)
                        g.help_stock_four_sell.append(stock)

    time_sell = context.current_dt.strftime('%H:%M:%S')
    cday = datetime.datetime.strptime('14:40:00', '%H:%M:%S').strftime('%H:%M:%S')
    sell_day = datetime.datetime.strptime('11:10:00', '%H:%M:%S').strftime('%H:%M:%S')
    sell_day_10 = datetime.datetime.strptime('13:30:00', '%H:%M:%S').strftime('%H:%M:%S')
    
    if time_sell > cday:
        stock_owner = context.portfolio.positions
        if len(stock_owner) > 0 and len(g.help_stock_four_sell) > 0:
            for stock_two in stock_owner:
                if context.portfolio.positions[stock_two].closeable_amount > 0:
                    current_price = get_current_data()[stock_two].last_price
                    day_open_price = get_current_data()[stock_two].day_open
                    day_high_limit = get_current_data()[stock_two].high_limit 
                    
                    now = context.current_dt
                    zeroToday = now - datetime.timedelta(hours=now.hour, minutes=now.minute, seconds=now.second,microseconds=now.microsecond)
                    lastToday = zeroToday + datetime.timedelta(hours=9, minutes=31, seconds=00)
                    df_panel_allday = get_price(stock_two, start_date=lastToday, end_date=context.current_dt, frequency='minute', fields=['close','high_limit'])
                    low_allday = df_panel_allday.loc[:,"close"].min()
                    high_allday = df_panel_allday.loc[:,"close"].max()
                    sum_plus_num_two = (df_panel_allday.loc[:,'close'] == df_panel_allday.loc[:,'high_limit']).sum()
                    
                    ##获取前一天的收盘价
                    pre_date =  (context.current_dt + timedelta(days = -1)).strftime("%Y-%m-%d")
                    df_panel = get_price(stock_two, count = 1,end_date=pre_date, frequency='daily', fields=['open', 'close','high_limit','money','low',])
                    pre_low_price =df_panel['low'].values
                    pre_close_price =df_panel['close'].values
                    
                    #平均持仓成本
                    cost = context.portfolio.positions[stock_two].avg_cost
                    if current_price < high_allday * 0.92 and day_open_price > pre_close_price:
                        print("1.卖出股票：小于最高价0.869倍"+str(stock_two))
                        orders =order_target(stock_two, 0)
                        if str(orders.status) == 'held':
                            g.help_stock_four_sell.remove(stock_two)
                    elif current_price > cost * 1.3 and sum_plus_num_two < 80:
                        print("2.卖出股票：亏8个点"+str(stock_two))
                        orders =order_target(stock_two, 0)
                        if str(orders.status) == 'held':
                            g.help_stock_four_sell.remove(stock_two)
                    elif day_open_price < pre_close_price * 0.98 and current_price < pre_close_price * 0.93:
                        print("3.卖出股票：1.3以下"+str(stock_two))
                        orders =order_target(stock_two, 0)
                        if str(orders.status) == 'held':
                            g.help_stock_four_sell.remove(stock_two)
    else:
        stock_owner = context.portfolio.positions
        if len(stock_owner) > 0 and len(g.help_stock_four_sell) > 0:
            for stock_two in stock_owner:
                if context.portfolio.positions[stock_two].closeable_amount > 0:
                    current_price = get_current_data()[stock_two].last_price
                    day_open_price = get_current_data()[stock_two].day_open
                    day_high_limit = get_current_data()[stock_two].high_limit 
                    
                    ##获取前一天的收盘价
                    pre_date =  (context.current_dt + timedelta(days = -1)).strftime("%Y-%m-%d")
                    df_panel = get_price(stock_two, count = 1,end_date=pre_date, frequency='daily', fields=['open', 'close','high_limit','money','low',])
                    pre_low_price =df_panel['low'].values
                    pre_close_price =df_panel['close'].values
                    pre_high_limit =df_panel['high_limit'].values
                    now = context.current_dt
                    zeroToday = now - datetime.timedelta(hours=now.hour, minutes=now.minute, seconds=now.second,microseconds=now.microsecond)
                    lastToday = zeroToday + datetime.timedelta(hours=9, minutes=31, seconds=00)
                    df_panel_allday = get_price(stock_two, start_date=lastToday, end_date=context.current_dt, frequency='minute', fields=['close','high_limit'])
                    low_allday = df_panel_allday.loc[:,"close"].min()
                    high_allday = df_panel_allday.loc[:,"close"].max()
                    sum_plus_num_two = (df_panel_allday.loc[:,'close'] == df_panel_allday.loc[:,'high_limit']).sum()
                    
                    current_price = context.portfolio.positions[stock_two].price #持仓股票的当前价 
                    cost = context.portfolio.positions[stock_two].avg_cost
                    
                    if current_price < cost * 0.91:
                        print("6.卖出股票：亏5个点"+str(stock_two))
                        orders =order_target(stock_two, 0)
                        if str(orders.status) == 'held':
                            g.help_stock_four_sell.remove(stock_two)
                    elif current_price < pre_close_price and time_sell > sell_day and current_price > cost:
                        print("7.高位放量，请走！"+str(day_open_price))
                        orders =order_target(stock_two, 0)
                        if str(orders.status) == 'held':
                            g.help_stock_four_sell.remove(stock_two)
                    elif day_open_price < pre_close_price * 0.95 and current_price > pre_close_price * 0.97:
                        print("add.高位放量，请走！"+str(day_open_price))
                        orders =order_target(stock_two, 0)
                        if str(orders.status) == 'held':
                            g.help_stock_four_sell.remove(stock_two)
                    elif high_allday > pre_close_price * 1.09 and current_price < day_open_price and day_open_price < day_high_limit * 0.95 and current_price < cost * 1.2:
                        print("8.高位放量，请走！"+str(day_open_price))
                        orders =order_target(stock_two, 0)
                        if str(orders.status) == 'held':
                            g.help_stock_four_sell.remove(stock_two)
                    elif current_price > cost * 1.25 and current_price < day_high_limit * 0.95 and time_sell > sell_day:
                        print("9.挣够25%，高位放量，请走！"+str(day_open_price))
                        orders =order_target(stock_two, 0)
                        if str(orders.status) == 'held':
                            g.help_stock_four_sell.remove(stock_two)
                    elif day_open_price < pre_close_price * 0.98 and current_price < high_allday * 0.95 and high_allday > pre_close_price * 1.05:
                        print("10.挣够25%，高位放量，请走！"+str(day_open_price))
                        orders =order_target(stock_two, 0)
                        if str(orders.status) == 'held':
                            g.help_stock_four_sell.remove(stock_two)
                    elif current_price < high_allday * 0.93 and high_allday > pre_close_price * 1.06 and time_sell > sell_day_10:
                        print("11.挣够25%，高位放量，请走！"+str(day_open_price))
                        orders =order_target(stock_two, 0)
                        if str(orders.status) == 'held':
                            g.help_stock_four_sell.remove(stock_two)
                    elif day_open_price < pre_close_price * 0.97 and current_price > pre_close_price:
                        print("10.挣够25%，高位放量，请走！"+str(day_open_price))
                        orders =order_target(stock_two, 0)
                        if str(orders.status) == 'held':
                            g.help_stock_four_sell.remove(stock_two)

## 选出连续涨停超过3天的，最近一天是阴板的
def before_market_open_four(context):
    date_now =  (context.current_dt + timedelta(days = -1)).strftime("%Y-%m-%d")#'2021-01-15'#datetime.datetime.now()
    yesterday = (context.current_dt + timedelta(days = -90)).strftime("%Y-%m-%d")
    trade_date = get_trade_days(start_date=yesterday, end_date=date_now, count=None)
    stocks = list(get_all_securities(['stock']).index)
    end_date = trade_date[trade_date.size-1]
    pre_date = trade_date[trade_date.size-3]
    #选出昨天是涨停板的个股
    continuous_price_limit = pick_high_limit_four(stocks,end_date,pre_date)

    filter_st_stock = filter_st(continuous_price_limit)
    templist = filter_stock_by_days(context,filter_st_stock,150)
    for stock in templist:
        ##查询昨天的股票是否阴板
        stock_date=trade_date[trade_date.size-2]
        df_panel = get_price(stock, count = 1,end_date=stock_date, frequency='daily', fields=['open', 'close','high_limit','money','low','high','pre_close'])
        df_close = df_panel['close'].values
        df_high = df_panel['high'].values
        df_low = df_panel['low'].values
        df_open = df_panel['open'].values
        df_pre_close = df_panel['pre_close'].values
        df_high_limit = df_panel['high_limit'].values
        #查询昨天的close价格
        df_panel_yes = get_price(stock, count = 1,end_date=end_date, frequency='daily', fields=['open', 'close','high_limit','money','low','high','pre_close'])
        df_close_yes = df_panel_yes['close'].values
        count_limit = count_limit_num_all_four(stock,context)
        # if stock == '002400.XSHE':
        #     print(df_open)
        #     print(df_close)
        #     print(df_high)
        #     print(count_limit)
        pre_date_two = trade_date[trade_date.size