# 克隆自聚宽文章：https://www.joinquant.com/post/46874
# 标题：首版+2版龙虎榜挖掘V2.0，年化1400
# 作者：xxzlw

# 导入函数库
from jqdata import *
from collections import OrderedDict
# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 输出内容到日志 log.info()
      # 开盘前运行
    g.muster = [] #目标
    g.amount = 1 #最大持股
    g.isbull = False # 是否牛市
      
    set_slippage(PriceRelatedSlippage(0.000))
    run_daily(prepare, time='9:15')
    run_daily(buy, time='9:26')
    
    # run_daily(sell, time='9:35')
    # run_daily(sell, time='10:00')
    # run_daily(sell, time='10:30')
    run_daily(sell, time='11:00')
    run_daily(sell, time='11:29')
    run_daily(sell, time='13:00')
    run_daily(sell, time='13:30')
    run_daily(sell, time='14:00')
    run_daily(sell, time='14:30')
    run_daily(sell, time='14:45')
    run_daily(sell, time='14:55')


def sell(context):
        current_data = get_current_data()     
        for position in list(context.portfolio.positions.values()):
            code=position.security
            name = get_security_info(code).display_name
            cost=position.avg_cost
            nowprice = current_data[code].last_price
            closeable_amount = position.closeable_amount
            high_limit = current_data[code].high_limit
            #小于成本
            target_price = high_limit*0.99
            # if code[:2] == '30':
            #   target_price = high_limit*0.83
            if nowprice !=high_limit and closeable_amount>0:
                order_target_value(code, 0)
                print('______________成本价卖出_______________')
                print("卖出[%s]" % (name))
        

def buy_prepare(context):
    result_stocks = []
    if g.muster is not None and len(g.muster)>0: 
        
    	current_data = get_current_data()
    	for stock in g.muster:
    	    price_data =  get_price(stock, count=1, panel=False,end_date=context.previous_date, frequency='daily', fields=['open', 'close', 'high_limit', 'low_limit', 'volume'])
    	    day_open = current_data[stock].day_open
    	    yesterday_high_limit = price_data['high_limit'][-1]
    	    high_limit = current_data[stock].high_limit
    	   # 大于昨日涨停且开盘不是涨停
    	    if yesterday_high_limit*1.04<= day_open and day_open<high_limit:
    	   # if day_open<price_data['close'][-1]*0.98:
    	        result_stocks.append(stock)
    # 	if len(result_stocks)>0:
    # 	    result_stocks = sorted(result_stocks, key=lambda x: get_price(x, count=1, panel=False, end_date=context.previous_date, frequency='daily', fields=['volume'])['volume'][-1], reverse=False)
    
    return result_stocks
    


# def buy(context):
    
    
#     #开盘再次判断
#     g.muster = buy_prepare(context)
    
#     if g.muster is not None and len(g.muster)>0:
#         for s in g.muster:
            
#             order_target_value(s, context.portfolio.total_value/len(g.muster)) # 调整标的至目标权重

def buy(context):
    available_slots = g.amount - len(context.portfolio.positions)
    if available_slots <= 0: 
        print("满仓无需开仓")
        return
    allocation = context.portfolio.cash / available_slots
    
    #开盘