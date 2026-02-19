# 克隆自聚宽文章：https://www.joinquant.com/post/33126
# 标题：最新解密--追涨龙头打板策略-适合近期实盘行情
# 作者：GoodThinker

# 克隆自聚宽文章：https://www.joinquant.com/post/25562
# 标题：涨停板策略，只买涨停板
# 作者：小微微

# 导入函数库
from jqdata import *
from jqlib.technical_analysis import *
import datetime as dt
#欢迎一起交流学习，探索出打板策略
#作者：山背小微 2020-02-17

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
    g.count=30
    g.buy_stock_list=[] #记录每天筛选出来的股票
    g.max_number_stock=3
    g.stop_loss_per = 0.96 #允许跌4%
    g.stop_win = 0.6 #卖出止赢
    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
      # 开盘时运行
    run_daily(market_open, time='09:33', reference_security='000300.XSHG')
      # 收盘后运行
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')
    
    run_daily(stop_win, time='14:50', reference_security='000300.XSHG')
    
    run_daily(stop_down_loss, time='9:40', reference_security='000300.XSHG')

def stop_down_loss(context):
    #判断盘中是不是高开低走，是就清仓
    if(len(context.portfolio.positions.keys())>0):
        for stock in context.portfolio.positions.keys():
             last_price_dict = get_current_data()
             current_price=last_price_dict[stock].last_price 
             closeable_amount = context.portfolio.positions[stock].closeable_amount
             if(closeable_amount>0):
                 df = get_price(stock, end_date=context.current_dt, frequency='daily', fields=['open'], skip_paused=True, fq='pre', count=1)
                 if df.empty:
                    continue
                 today_open_price = df['open'][0]
                 if(current_price<0.97*today_open_price):
                       sell_stock(stock,0)
                       log.info(str(get_security_info(stock).display_name)+"  盘中高开低走,卖出止损")
                 else:
                       log.info(str(get_security_info(stock).display_name)+"   盘中高开低走,不用止损")
                 
    
def print_stock_info(stock_list):
    if(stock_list is None):
        return
    if(len(stock_list)<0):
        return 
    for stock in stock_list:
        stock_name = get_security_info(stock).display_name
        log.info(str(stock)+ "   "+ str(stock_name))


def search_can_buy_stock(context):
    #寻找类似模塑科技那样的股票
    stock_list = Get_all_security_list(context)
    #寻找昨天涨停板股票
    up_limted_stock_list = find_predata_up_limted(context,stock_list)
    #筛选出昨天涨停板，并且昨日收盘价>5日移动平均线>10日移动平均线>20日移动平均线>60日移动平均线
    if(up_limted_stock_list is None):
        return None
    stock_list=[]
    for stock in up_limted_stock_list:
        ma_5 = MA(stock,context.previous_date,5,'1d')
        ma_10 = MA(stock,context.previous_date,10,'1d')
        ma_20 = MA(stock,context.previous_date,20,'1d')
        ma_60 = MA(stock,context.previous_date,60,'1d')
        df = get_price(stock, end_date=context.previous_date, frequency='daily', fields=['close'], skip_paused=True, fq='pre', count=1)
        if df.empty:
            continue
        pre_close_price = df['close'][0]
        if(pre_close_price>ma_5[stock] and ma_5[stock]>ma_10[stock] and ma_10[stock]>ma_20[stock] and ma_20[stock]>ma_60[stock]):
            stock_list.append(stock)
    
    return stock_list
    
    
    
## 开盘前运行函数
def before_market_open(context):
    g.buy_stock_list  = search_can_buy_stock(context)
    
def stop_loss(context):
    #开盘判断是否要止损,如果当前价格相对持仓成本跌了4% 或者当前价格相对昨日收盘价跌了4% 就止损
    if(len(context.portfolio.positions.keys())>0):
        for stock in context.portfolio.positions.keys():
             last_price_dict = get_current_data()
             current_price=last_price_dict[stock].last_price 
             closeable_amount = context.portfolio.positions[stock].closeable_amount