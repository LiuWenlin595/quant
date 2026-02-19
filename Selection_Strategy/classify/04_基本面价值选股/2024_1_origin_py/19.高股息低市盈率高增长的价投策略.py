# 克隆自聚宽文章：https://www.joinquant.com/post/45552
# 标题：高股息低市盈率高增长的价投策略
# 作者：芹菜1303

# 0、股票筛选所有股票，去科创板和北交所，去ST，去上市未满300天；
# 1、股票筛选和排序：最近3年平均分红股息率最大10%的股票，按分红/股价 从大到小排序；（股价上涨，会导致排名下跌）
# 2、股票筛选：PEG在0.08-2之间，市盈率：0~20之间，净资产收益率>3%,营业收入同比增长率>5%,净资产同比增长>11%;（股价上涨到PE超过25就会跌出股票池）
# 3、选取的股票：去停牌，去昨天涨停的，取前10个股票做为买入股票池（股价）
# 4、执行频率每月执行一次；
# 5、每天执行的是：如果昨天是涨停的，今天没有涨停，则卖出；

import pandas as pd
from jqdata import *

def initialize(context):
    set_benchmark('000300.XSHG') #000905.XSHG
    log.set_level('order', 'error')
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)# 设置是否开启避免未来数据模式
    set_slippage(FixedSlippage(0.02))# 设置滑点    
    g.stock_num = 10
    g.month=context.current_dt.month-1

# 开盘前运行，做为未来拓展的空间预留
def before_trading_start(context):
    # log.info(str(context.current_dt))
    prepare_stock_list(context)
    print(context.run_params.type) #模拟交易

# 开盘时运行函数
def handle_data(context,data):
    hour=context.current_dt.hour#读取当前时间-小时
    minute=context.current_dt.minute#读取当前时间-分钟
    #选股程序每月执行一次
    if context.current_dt.month !=g.month and hour==9 and minute==30:
        my_Trader(context)
        g.month=context.current_dt.month

    #-----------------------执行频率的设置和股票筛选程序----------------------
    if hour==14 and minute==0:  
        check_limit_up(context)#昨天涨停今天开板的卖出
    #显示可动用现金/总资产
    record(cash=context.portfolio.available_cash/context.portfolio.total_value*100)

def my_Trader(context):
    dt_last = context.previous_date
    stocks = get_all_securities('stock', dt_last).index.tolist()#读取所有股票
    stocks = filter_kcbj_stock(stocks)  #去科创和北交所
    stocks = filter_st_stock(stocks)#去ST
    stocks = filter_new_stock(context, stocks)#去除上市未满300天
    stocks = choice_try_A(context,stocks)#基本面选股
    stocks = filter_paused_stock(stocks)#去停牌
    stocks = filter_limit_stock(context,stocks)[:g.stock_num]#去除涨停的
    cdata = get_current_data()
    slist(context,stocks)
    # Sell
    for s in context.portfolio.positions:
        if (s  not in stocks) and (cdata[s].last_price <  cdata[s].high_limit):
            log.info('Sell', s, cdata[s].name)
            order_target(s, 0)
    # buy
    position_count = len(context.portfolio.positions)
    if g.stock_num > position_count:
        psize = context.portfolio.available_cash/(g.stock_num - position_count)
        for s in stocks:
            if s not in context.portfolio.positions:
                log.info('buy', s, cdata[s].name)
                order_value(s, psize)
                if len(context.portfolio.positions) == g.stock_num:
                    break
    
#显示筛查出股票的：名称，代码，市值
def slist(context,stock_list):    
    current_data = get_current_data()
    for stock in stock_list:
        df = get_fundamentals(query(valuation).filter(valuation.code == stock))
        print('股票代码：{0},  名称：{1},  总市值:{2:.2f},  流通市值:{3:.2f},  PE:{4:.2f},股价：{5:.2f}'.format(stock,get_security_info(stock).display_name,df['market_cap'][0],df['circulating_market_cap'][0],df['pe_ratio'][0],current_data[stock].last_price))

#1-1 准备股票池
# 如果持有股票昨天处于涨停的，则放入涨停列表，只要今天打开涨停就卖出，这个每天执行
def prepare_stock_list(context):
    #获取已持有列表
    g.hold_list= []
    g.high_limit_list=[]
    for position in list(context.portfolio.positions.values()):
        stock = position.security
        g.hold_list.append(stock)
    #获取昨日涨停列表
    if g.hold_list != []:
        for stock in g.hold_list:
            df = get_price(stock, end_date=context.previous_date, frequency='daily', fields=['close','high_limit'], count=1)
            if df['close'][0] >= df['high_limit'][0]*0.98:#如果昨天有股票涨停，则放入列表
                g.high_limit_list.append(stock)
    
#1-5 调整昨日涨停股票
def check_limit_up(context):
    now_time = context.current_dt
    if g.high_limit_list != []:
        #对昨日涨停股票观察到尾盘如不涨停则提前卖出，如果涨停即使不在应买入列表仍暂时持有
        for stock in g.high_limit_list:
            current_data = get_current_data()
            if current_data[stock].last_price <   current_data[stock].high_limit:
                log.info("[%s]涨停打开，卖出" % (stock))
                order_target(stock, 0)
            else:
                log.info("[%s]涨停，继续持有" % (stock))            
 
# 过滤科创北交股票
def filter_kcbj_stock(stock_list):
    for stock in stock_list[:]:
        if stock[0] == '4' or stock[0] == '8' or stock[:2] == '68':
            stock_list.remove(stock)
    return stock_list

# 过滤停牌股票
def filter_paused_stock(stock_list):
	current_data = get_current_data()
	return [stock for stock in stock_list if not current_data[stock].paused]


# 过滤ST及其他具有退市标签的股票
def filter_st_stock(stock_list):
	current_data = get_current_data()
	return [stock for stock