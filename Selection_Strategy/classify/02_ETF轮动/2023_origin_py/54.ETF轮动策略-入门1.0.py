# 克隆自聚宽文章：https://www.joinquant.com/post/35136
# 标题：ETF轮动策略-入门1.0
# 作者：vzhb1998

'''
优化说明:
    1.使用修正标准分
        rsrs_score的算法有：
            仅斜率slope，效果一般；
            仅标准分zscore，效果不错；
            修正标准分 = zscore * r2，效果最佳;
            右偏标准分 = zscore * slope，效果不错。
    2.将原策略的每次持有两只etf改成只买最优的一个，收益显著提高
    3.将每周调仓换成每日调仓，收益显著提高
    4.因为交易etf，所以手续费设为万分之三，印花税设为零，未设置滑点
    5.修改股票池中候选etf，删除银行，红利等收益较弱品种，增加纳指etf以增加不同国家市场间轮动的可能性
    6.根据研报，默认参数介已设定为最优
    7.加入防未来函数
    8.增加择时与选股模块的打印日志，方便观察每笔操作依据
    9.本版本为1.0，后续确定不存在过拟合后会更新2.0
    10.作者vx:iamzhangb，有好的建议可加
'''

#导入函数库
from jqdata import *
import numpy as np

#初始化函数 
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 用真实价格交易
    set_option('use_real_price', True)
    # 打开防未来函数
    set_option("avoid_future_data", True)
    # 将滑点设置为0.001
    set_slippage(FixedSlippage(0.001))
    # 设置交易成本万分之一
    set_order_cost(OrderCost(open_tax=0, close_tax=0, open_commission=0.0001, close_commission=0.0001, close_today_commission=0, min_commission=5),
                   type='fund')
    # 股票类每笔交易时的手续费是：买入时佣金万分之二，卖出时佣金万分之二，无印花税, 每笔交易佣金最低扣5块钱
    # set_order_cost(OrderCost(close_tax=0.000, open_commission=0.0002, close_commission=0.0002, min_commission=5), type='fund')
    # 过滤order中低于error级别的日志
    log.set_level('order', 'error')
    # 初始化各类全局变量
    #股票池
    g.stock_pool = [
        '159915.XSHE', # 易方达创业板ETF
        '510300.XSHG', # 华泰柏瑞沪深300ETF
        #'513100.XSHG', #纳指ETF
        '510500.XSHG', # 南方中证500ETF
    ]
    #动量轮动参数
    g.stock_num = 1 #买入评分最高的前stock_num只股票
    g.momentum_day = 29 #最新动量参考最近momentum_day的
    #rsrs择时参数
    g.ref_stock = '000300.XSHG' #用ref_stock做择时计算的基础数据
    g.N = 18 # 计算最新斜率slope，拟合度r2参考最近N天
    g.M = 600 # 计算最新标准分zscore，rsrs_score参考最近M天
    g.score_threshold = 0.7 # rsrs标准分指标阈值
    #ma择时参数
    g.mean_day = 20 #计算结束ma收盘价，参考最近mean_day
    g.mean_diff_day = 3 #计算初始ma收盘价，参考(mean_day + mean_diff_day)天前，窗口为mean_diff_day的一段时间
    g.slope_series = initial_slope_series()[:-1] # 除去回测第一天的slope，避免运行时重复加入
    # 设置交易时间，每天运行
    run_daily(my_trade, time='9:30', reference_security='000300.XSHG')
    run_daily(check_lose, time='open', reference_security='000300.XSHG')
    run_daily(print_trade_info, time='15:30', reference_security='000300.XSHG')


#1-1 选股模块-动量因子轮动