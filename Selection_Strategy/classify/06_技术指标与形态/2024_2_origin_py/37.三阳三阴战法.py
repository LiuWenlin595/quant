# 克隆自聚宽文章：https://www.joinquant.com/post/37593
# 标题：三阳三阴战法
# 作者：游资小码哥

# 导入函数库
from jqdata import *
from jqlib.technical_analysis import *
help_stock = []
# 初始化函数，设定基准等等
#需要注意的点，1.最高点前不能连续涨停 2.最高点要高过前面一年
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
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
      # 开盘时运行
    run_daily(market_open, time='every_bar', reference_security='000300.XSHG')
      # 收盘后运行
    #run_daily(before_market_open, time='after_close', reference_security='000300.XSHG')

## 开盘时运行函数
def market_open(context):
    date_now =  (context.current_dt + timedelta(days = -1)).strftime("%Y-%m-%d")#'2021-01-15'#datetime.datetime.now()
    cash = context.portfolio.available_cash
    if len(help_stock) > 0:
        for stock in help_stock:
            if cash > 5000 :
                day_open_price = get_current_data()[stock].day_open
                current_price = get_current_data()[stock].last_price
                day_high_limit = get_current_data()[stock].high_limit 
                close_data = attribute_history(stock, 10, '1d', ['close'])
                pre_date_yes =  (context.current_dt + timedelta(days = -1)).strftime("%Y-%m-%d")
                df_panel_yes = get_price(stock, count = 1,end_date=pre_date_yes, frequency='daily', fields=['open', 'close','high_limit','money','low','high'])
                pre_low_price_yes =df_panel_yes['low'].values
                pre_close_price_yes =df_panel_yes['close'].values
                pre_high_price_yes =df_panel_yes['high'].values
                # 取得过去五天的平均价格
                if current_price > pre_close_price_yes * 1.01 and current_price < day_high_limit:
                    print("1."+stock+"买入金额"+str(cash))
                    order_value(stock, cash)
                    help_stock.remove(stock)
                    
    time_sell = context.current_dt.strftime('%H:%M:%S')
    cday = datetime.datetime.strptime('14:40:00', '%H:%M:%S').strftime('%H:%M:%S')
    now = context.current_dt
    zeroToday = now - datetime.timedelta(hours=now.hour, minutes=now.minute, seconds=now.second,microseconds=now.microsecond)
    lastToday = zeroToday + datetime.timedelta(hours=9, minutes=31, seconds=00)
    if time_sell > cday:
        stock_owner = context.portfolio.positions
        if len(stock_owner) > 0:
            for stock_two in stock_owner:
                if context.portfolio.positions[stock_two].closeable_amount > 0:
                    current_price_list = get_ticks(stock_two,start_dt=None, end_dt=context.current_dt, count=1, fields=['time', 'current', 'high', 'low', 'volume', 'money'])
                    current_price = current_price_list['current'][0]
                    day_open_price = get_current_data()[stock_two].day_open
                    day_high_limit = get_current_data()[stock_two].high_limit 
                    
                    #查询当天的最高价
                    df = get_price(stock_two, start_date=lastToday,end_date=context.current_dt, frequency='minute', fields=['high','low'],skip_paused=True)
                    df_max_high = df["high"].max()
                    df_min_high = df["low"].min()
                    ##获取前一天的收盘价
                    pre_date =  (context.current_dt + timedelta(days = -1)).strftime("%Y-%m-%d")
                    df_panel = get_price(stock_two, count = 1,end_date=pre_date, frequency='daily', fields=['open', 'close','high_limit','money','low',])
                    pre_low_price =df_panel['low'].values
                    pre_close_price =df_panel['close'].values
                    close_data = attribute_history(stock_two, 10, '1d', ['close'])
                    MA10 = close_data['close'].mean()
                    
                    #short_macd_dif, short_macd_dea, short_macd_macd = MACD(security,check_date=context.previous_date, SHORT = 2, LONG = 5, MID = 9)
                    short_pre_macd_dif, short_pre_macd_dea, short_pre_macd_macd = MACD(stock_two,check_date=context.current_dt, SHORT = 2, LONG = 5, MID = 9)
                    if stock_two == '601608.XSHG':
                        print("macd来了-------------")
                        print(short_pre_macd_macd[stock_two])
                        print(short_pre_macd_macd < 0)
                    
                    df_panel_3 = get_price(stock_two, count = 3,end_date=pre_date, frequency='daily', fields=['open', 'close','high_limit','money'])
                    sum_plus_num_3 = (df_panel_3.loc[:,'close'] == df_panel_3.loc[:,'high_limit']).sum()  
                        
                    
                    #平均持仓成本
                    cost = context.portfolio.positions[stock_two].avg_cost
                    if current_price < MA10 * 0.98 and pre_close_price < MA10 * 0.98:
                        print("1.卖出股票：小于最高价0.869倍"+str(stock_two))
                        order_target(stock_two, 0)
                    elif current_price > cost * 2.1:
                        print("2.卖出股票：挣了超过60%"+str(stock_two))
                        order_target(stock_two, 0)
                    elif current_price < cost * 0.90:
                        print("3.卖出股票：亏了5%"+str(stock_two))
                        order_target(stock_two, 0)
                    elif current_price < day_open_price * 0.90 and current_price < pre_close_price * 0.95 and current_price > cost * 1.1:
                        print("#3.卖出股票：亏了5%"+str(stock_two))
                        order_target(stock_two, 0)
                    elif current_price < cost * 1.15 and short_pre_macd_macd[stock_two] < 0.00 and sum_plus_num_3 == 0:
                        print("#4.MACD不强势卖了"+str(stock_two))
                        order_target(stock_two, 0)
    else:
        stock_owner = context.portfolio.positions
        if len(stock_owner) > 0:
            for stock_two in stock_owner:
                current_price_list = get_ticks(stock_two,start_dt=None, end_dt=context.current_dt, count=1, fields=['time', 'current', 'high', 'low', 'volume', 'money'])
                current_price = current_price_list['current'][0]
                day_open_price = get_current_data()[stock_two].day_open
                day_high_limit = get_current_data()[stock_two].high_limit 
                #查询当天的最高价
                df = get_price(stock_two, start_date=context.portfolio.positions[stock_two].init_time,end_date=context.current_dt, frequency='minute', fields=['high'],skip_paused=True)
                df_max_high = df["high"].max()
                ##获取前一天的收盘价
                pre_date =  (context.current_dt + timedelta(days = -1)).strftime("%Y-%m-%d")
                df_panel = get_price(stock_two, count = 1,end_date=pre_date, frequency='daily', fields=['open', 'close','high_limit','money','low',])
                pre_low_price =df_panel['low'].values
                pre_close_price =df_panel['close'].values
                
                df_panel_5 = get_price(stock_two, count = 5,end_date=pre_date, frequency='daily', fields=['open', 'close','high_limit','money'])
                df_close_mean_5 = df_panel_5['close'].mean()
                
                df_panel_10 = get_price(stock_two, count = 10,end_date=pre_date, frequency='daily', fields=['open', 'close','high_limit','money'])
                df_close_mean_10 = df_panel_10['close'].mean()
                #查看是否连续涨停超过5次，只有后面低于前一交易日就卖
                now = context.current_dt
                zeroToday = now - datetime.timedelta(hours=now.hour, minutes=now.minute, seconds=now.second,microseconds=now.microsecond)
                lastToday = zeroToday + datetime.timedelta(hours=9, minutes=31, seconds=00)
                df_panel_allday = get_price(stock_two, start_date=lastToday, end_date=context.current_dt, frequency='minute', fields=['high','low','close','high_limit','money'])
                low_allday = df_panel_allday.loc[:,"low"].min()
                high_allday = df_panel_allday.loc[:,"high"].max()
                current_price = context.portfolio.positions[stock_two].price #持仓股票的当前价 
                cost = context.portfolio.positions[stock_two].avg_cost
                
                df_panel_3 = get_price(stock_two, count = 3,end_date=pre_date, frequency='daily', fields=['open', 'close','high_limit','money'])
                sum_plus_num_3= (df_panel_3.loc[:,'close'] == df_panel_3.loc[:,'high_limit']).sum()  
                
                if current_price < df_close_mean_5 * 0.98 and day_open_price > df_close_mean_5 and current_price < day_open_price * 0.95 and df_close_mean_5 > df_close_mean_10 * 1.08:
                    print("6.卖出股票：12个板以上"+str(stock_two))
                    order_target(stock_two, 0)
                elif day_open_price < pre_close_price * 0.93 and current_price > pre_close_price * 1.07:
                    print("7.开盘超跌"+str(stock_two))
                    order_target(stock_two, 0)
                elif day_open_price == day_high_limit and current_price < pre_close_price:
                    print("8.高位放量，请走！"+str(stock_two))
                    order_target(stock_two, 0)
                elif sum_plus_num_3 == 3 and current_price < day_open_price * 0.93:
                    print("9.高位放量，请走！"+str(stock_two))
                    order_target(stock_two, 0)
                elif sum_plus_num_3 == 3 and current_price < pre_close_price * 0.93:
                    print("9.高位放量，请走！"+str(stock_two))
                    order_target(stock_two, 0)
                elif current_price > cost * 2 and day_high_limit == high_allday and current_price < day_high_limit * 0.95:
                    print("10.高位放量，请走！"+str(stock_two))
                    order_target(stock_two, 0)

    if time_sell > cday and len(help_stock) > 0:
        instead_stock = help_stock
        for stock_remove in instead_stock:
            help_stock.remove(stock_remove)

## 开盘前运行函数
def before_market_open(context):
    date_now =  (context.current_dt + timedelta(days = -1)).strftime("%Y-%m-%d")#'2021-01-15'#datetime.datetime.now()
    yesterday = (context.current_dt + timedelta(days = -91)).strftime("%Y-%m-%d")
    trade_date = get_trade_days(start_date=yesterday, end_date=date_now, count=None)
    yes_date_one = trade_date[trade_date.size-1]
    yes_date_two = trade_date[trade_date.size-4]
    yes_date_10 = trade_date[trade_date.size-15]
    yes_date_30 = trade_date[trade_date.size-30]
    stocks = list(get_all_securities(['stock']).index)
    pick_high_list = pick_high_limit(stocks,trade_date,yes_date_one,yes_date_two,yes_date_10,yes_date_30)
    codelist = filter_st(pick_high_list)
    filter_paused_list =filter_paused_stock(codelist)
    templist = filter_stock_by_days(context, filter_paused_list, 1080)
    for stock in templist:
        # result_true = high_continous(stock,trade_date,date_now,context)
        # if result_true == True:
        help_stock.append(stock)
    print("------今天要扫描的股票------")
    print(help_stock)
    
##选出打板的股票
def pick_high_limit(stocks,trade_date,end_date,yes_date_two,yes_date_10,yes_date_30):
    df_panel = get_price(stocks, count = 1,end_date=end_date, frequency='daily', fields=['open', 'close','high_limit','money','low','pre_close'])
    df_close = df_panel['close']
    df_open = df_panel['open']
    df_high_limit = df_panel['high_limit']
    df_low = df_panel['low']
    df_pre_close = df_panel['pre_close']
    high_limit_stock = []
    for stock in (stocks):
        if(stock[0:3] == '300' or stock[0:3] == '688'):
            continue
        _high_limit = (df_high_limit[stock].values)
        _close = (df_close[stock].values)
        _open =  (df_open[stock].values)
        _low = (df_low[stock].values)
        _pre_close = (df_pre_close[stock].values)
        if _close > _open:
            df_panel_1 = get_price(stock, count = 1,end_date=end_date, frequency='daily', fields=['open', 'close','high_limit','money'])
            close_price_yes =df_panel_1['close'].values

            df_panel_3 = get_price(stock, count = 3,end_date=end_date, frequency='daily', fields=['open', 'close','high_limit','money'])
            sum_plus_num_3= (df_panel_3.loc[:,'close'] >= df_panel_3.loc[:,'open']).sum()       

            df_panel_6 = get_price(stock, count = 6,end_date=end_date, frequency='daily', fields=['open', 'close','high_limit','money'])
            sum_plus_num_6= (df_panel_6.loc[:,'close'] > df_panel_6.loc[:,'open']).sum()
            sum_open_num_6= (df_panel_6.loc[:,'open'] == df_panel_6.loc