# 克隆自聚宽文章：https://www.joinquant.com/post/38120
# 标题：ETF轮动策略-入门2.0
# 作者：vzhb1998

# -*- coding: utf-8 -*-
# @author: zhangb
# @qq：1337569005

# 优化说明:
#     1.使用修正标准分
#         rsrs_score的算法有：
#             仅斜率slope，效果一般；
#             仅标准分zscore，效果不错；
#             修正标准分 = zscore * r2，效果最佳;
#             右偏标准分 = 修正标准分 * slope，效果不错。
#     2.将原策略的每次持有两只etf改成只买最优的一个，收益显著提高
#     3.将每周调仓换成每日调仓，收益显著提高
#     4.因为交易etf，所以手续费设为万分之1，印花税设为零，未设置滑点
#     5.修改股票池中候选etf，删除银行，红利等收益较弱品种，增加纳指etf以增加不同国家市场间轮动的可能性
#     6.根据研报，默认参数介已设定为最优
#     7.针对盈利分析发现沪深300etf不适用此策略，做优化调整
#     8.添加北向策略对沪深300etf复合优化
#     9.加入防未来函数
#     10.增加择时与选股模块的打印日志，方便观察每笔操作依据

#导入函数库
from jqdata import *
import numpy as np
import numpy
import datetime
import statistics

#初始化函数 
def initialize(context):
    # 设定300作为基准
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
        #'159945.XSHE', # 易方达创业板50
        '510300.XSHG', # 华泰柏瑞沪深300ETF
        '510500.XSHG', # 南方中证500ETF
        #'513100.XSHG', #纳指ETF
        #'159928.XSHE', #消费ETF
    ]

	#北向净流入数据
    g.Northbound=[]
	#针对300etf优化选值,初始为15
    g.Northbound_val=15
    g.north_money=0
    
    #动量轮动参数
    g.stock_num = 1 #买入评分最高的前stock_num只股票
    g.momentum_day = 27 #最新动量参考最近momentum_day的
    #rsrs择时参数
    g.ref_stock = '000300.XSHG' #用ref_stock做择时计算的基础数据
    g.N = 18 # 计算最新斜率slope，拟合度r2参考最近N(18)天
    g.M = 600 # 计算最新标准分zscore，rsrs_score参考最近M(600)天
    g.score_threshold = 0.7 # rsrs标准分指标阈值
    #ma择时参数
    g.mean_day = 20 #计算结束ma收盘价，参考最近mean_day
    g.mean_diff_day = 5 #计算初始ma收盘价，参考(mean_day + mean_diff_day)天前，窗口为mean_diff_day的一段时间
    g.slope_series = initial_slope_series()[:-1] # 除去回测第一天的slope，避免运行时重复加入
    # 设置交易时间，每天运行
    run_daily(my_trade, time='8:50', reference_security='000300.XSHG')
    run_daily(check_lose, time='open', reference_security='000300.XSHG')
    run_daily(print_trade_info, time='15:30', reference_security='000300.XSHG')

#1-1 选股模块-动量因子轮动 
#基于股票年化收益和判定系数打分,并按照分数从大到小排名
def get_rank(stock_pool):
    score_list = []
    for stock in g.stock_pool:
        data = attribute_history(stock, g.momentum_day, '1d', ['close'])
        y = data['log'] = np.log(data.close)
        x = data['num'] = np.arange(data.log.size)
        slope, intercept = np.polyfit(x, y, 1)
        annualized_returns = math.pow(math.exp(slope), 250) - 1
        r_squared = 1 - (sum((y - (slope * x + intercept))**2) / ((len(y) - 1) * np.var(y, ddof=1)))
        score = annualized_returns * r_squared
        score_list.append(score)
    stock_dict=dict(zip(g.stock_pool, score_list))
    sort_list=sorted(stock_dict.items(), key=lambda item:item[1], reverse=True) #True为降序
    code_list=[]
    for i in range((len(g.stock_pool))):
        code_list.append(sort_list[i][0])
    rank_stock = code_list[0:g.stock_num]
    print(code_list[0:5])
    return rank_stock



#2-1 择时模块-计算线性回归统计值
#对输入的自变量每日最低价x(series)和因变量每日最高价y(series)建立OLS回归模型,返回元组(截距,斜率,拟合度)
def get_ols(x, y):
    slope, intercept = np.polyfit(x, y, 1)
    r2 = 1 - (sum((y - (slope * x + intercept))**2) / ((len(y) - 1) * np.var(y, ddof=1)))
    return (intercept, slope, r2)

#2-2 择时模块-设定初始斜率序列
#通过前M日最高最低价的线性回归计算初始的斜率,返回斜率的列表
def initial_slope_series():
    data = attribute_history(g.ref_stock, g.N + g.M, '1d', ['high', 'low'])
    return [get_ols(data.low[i:i+g.N], data.high[i:i+g.N])[1] for i in range(g.M)]

#2-3 择时模块-计算标准分
#通过斜率列表计算并返回截至回测结束日的最新标准分
def get_zscore(slope_series):
    mean = np.mean(slope_series)
    std = np.std(slope_series)
    return (slope_series[-1] - mean) / std

#2-4 择时模块-计算综合信号
#1.获得rsrs与MA信号,rsrs信号算法参考优化说明，MA信号为一段时间两个端点的MA数值比较大小
#2.信号同时为True时返回买入信号，同为False时返回卖出信号，其余情况返回持仓不变信号
def get_timing_signal(stock):
    #计算MA信号
    close_data = attribute_history(g.ref_stock, g.mean_day + g.mean_diff_day, '1d', ['close'])
    today_MA = close_data.close[g.mean_diff_day:].mean() 
    before_MA = close_data.close[:-g.mean_diff_day].mean()
    #计算rsrs信号
    high_low_data = attribute_history(g.ref_stock, g.N, '1d', ['high', 'low'])
    intercept, slope, r2 = get_ols(high_low_data.low, high_low_data.high)
    g.slope_series.append(slope)
    rsrs_score = get_zscore(g.slope