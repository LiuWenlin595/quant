# 克隆自聚宽文章：https://www.joinquant.com/post/36975
# 标题：短线策略-2022年两个半月收益45%-无未来函数
# 作者：zk001

# 克隆自聚宽文章：https://www.joinquant.com/post/36906
# 标题：2022年三个月收益51%，超短线实盘交易策略！无未来函数
# 作者：御风起浪

# 克隆自聚宽文章：https://www.joinquant.com/post/36786
# 标题：14个月200%，超短线实盘交易策略！无未来函数
# 作者：随波逐浪9

# 导入函数库
from jqdata import *
from jqlib.technical_analysis import *
import numpy as np
from datetime import datetime
# 初始化函数，设定基准等等
def initialize(context):
    enable_profile()
    # log.set_level('order', 'error')
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 关闭未来函数
    # set_option("avoid_future_data", True)
    
    # 将滑点设置为0
    set_slippage(FixedSlippage(0))
    # 设置交易成本万分之三
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, close_today_commission=0, min_commission=5),type='fund')
    # 股票购买限制
    g.buy_stock_limit = 1

def initHandleParam():
    g.buy_list = []

## 开盘前运行函数
def before_trading_start(context):
    # 初始化参数
    initHandleParam()
    
    start = datetime.now()
    
    # 获取股票池
    prev_date = context.previous_date
    stock_pool=get_stock_pool(prev_date)
    
    # 通过不同的条件筛选股票
    dx1 = stock_filter1(stock_pool,prev_date)
    print('dx1:{}'.format(len(dx1)))
    
    dx2 = stock_filter2(dx1,prev_date)
    print('dx2:{}'.format(len(dx2)))
    
    dx3 = stock_filter3(dx2,prev_date)
    print('dx3:{}'.format(len(dx3)))
    
    dx4 = stock_filter4(dx3,prev_date)
    print('dx4:{}'.format(len(dx4)))
    
    end = datetime.now()
    print('选股{}'.format(end-start))
    
    g.buy_list = dx4
    g.buy_list.sort()
    print('%s:共找到%d只股票可以购买.%s'%(context.current_dt,len(g.buy_list),g.buy_list))


## 开盘时运行函数
def handle_data(context,data):
    
    start = datetime.now()
    
    current_data = get_current_data()
    # 卖出
    for stock in context.portfolio.positions.keys():
        # 如果在买入列表中，则跳过
        if stock in g.buy_list:
            continue
        
        # 如果可卖出仓位为0，或者跌停、涨停，则跳过
        price = data[stock].close
        if context.portfolio.positions[stock].closeable_amount == 0  \
        or current_data[stock].low_limit == price \
        or current_data[stock].high_limit == price \
        :
            continue
        
        # 否则，清空该股票
        print('%s卖出(自动):自动卖出:成本价:%s,当前价:%s'%(stock,context.portfolio.positions[stock].avg_cost,price))
        sell_stock(stock,0)

    # 判断是否买满
    if g.buy_stock_limit <= len(context.portfolio.positions.keys()):
        return 
    
    # 买入
    for stock in g.buy_list:
        price = data[stock].close
        if context.portfolio.available_cash < (price * 100) \
        or current_data[stock].low_limit == price \
        or current_data[stock].high_limit == price \
        or stock in context.portfolio.positions.keys() \
        :
            continue
        print('%s买入(自动):自动买入:当前价:%s'%(stock,price))
        buy_stock(context,stock)
    
    end = datetime.now()
    print('交易{}'.format(end-start))