# 克隆自聚宽文章：https://www.joinquant.com/post/35394
# 标题：ETF动量轮动RSRS择时-魔改3-北向资金择时-再优化
# 作者：nixun

# 克隆自聚宽文章：https://www.joinquant.com/post/35376
# 标题：年化108%最大回撤10%的ETF动量轮动RSRS择时（续）
# 作者：秋天来了

# 克隆自聚宽文章：https://www.joinquant.com/post/35279
# 标题：ETF动量轮动RSRS择时-魔改3小优化
# 作者：莫急莫急

from jqdata import *
import numpy as np

#初始化函数 
def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_option("avoid_future_data", True)
    #set_slippage(PriceRelatedSlippage(0.003))
    set_slippage(FixedSlippage(0.001))
    set_order_cost(OrderCost(open_tax=0, close_tax=0, open_commission=0.0003, close_commission=0.0003, close_today_commission=0, min_commission=5),
                   type='fund')
    log.set_level('order', 'error')
    g.stock_pool = [
        '510050.XSHG', # 上证50ETF
        '159928.XSHE', # 中证消费ETF
        '510300.XSHG', # 沪深300ETF
        '159949.XSHE', # 创业板50ETF
    ]
    # 备选池：用流动性和市值更大的50ETF分别代替宽指ETF，500与300ETF保留一个

    g.north_money = 0
    g.stock_num = 1 #买入评分最高的前stock_num只股票
    g.momentum_day = 20 #最新动量参考最近momentum_day的
    g.momentum_day_t = 0
    g.ref_stock = '000300.XSHG' #用ref_stock做择时计算的基础数据
    g.N = 18 # 计算最新斜率slope，拟合度r2参考最近N天
    g.M = 600 # 计算最新标准分zscore，rsrs_score参考最近M天
    g.score_threshold = 0.7 # rsrs标准分指标阈值
    g.mean_day = 30 #计算结束ma收盘价，参考最近mean_day
    g.mean_diff_day = 2 #计算初始ma收盘价，参考(mean_day + mean_diff_day)天前，窗口为mean_diff_day的一段时间
    g.slope_series = initial_slope_series()[:-1] # 除去回测第一天的slope，避免运行时重复加入
    run_daily(my_trade, time='9:30', reference_security='000300.XSHG')
    run_daily(check_lose, time='open', reference_security='000300.XSHG')
    run_daily(print_trade_info, time='15:30', reference_security='000300.XSHG')

# 20日收益率动量拟合取斜率最大的
def get_rank(context,stock_pool):
    rank = []
    for stock in g.stock_pool:
        data = attribute_history(stock, g.momentum_day, '1d', ['close'])
        
        # 下面这句是为了测试get_price的未来函数功能，在当前日期的基础上减去一天，与attribute_history的数据一样
        # data = get_price(stock, end_date=context.