# 克隆自聚宽文章：https://www.joinquant.com/post/16343
# 标题：基于机器学习的多因子选股策略
# 作者：quant.show

# 标题：基于机器学习的多因子选股的量化投资策略
# 作者：ChenXuan

import pandas as pd
import numpy as np
import math
import json
import jqdata
from jqfactor import standardlize
from jqfactor import winsorize_med
from jqdata import *
from sklearn.model_selection import KFold


def initialize(context):
    set_params()
    set_backtest()

#
def set_params():
    # 记录回测运行的天数
    g.days = 0
    # 当天是否交易
    g.if_trade = False                       

    ## 可变参数
    # 股票池
    g.secCode = '000985.XSHG'  #中证全指
    #g.secCode = '000300.XSHG'
    #g.secCode = '000905.XSHG' #中证500
    # 调仓天数
    g.refresh_rate = 30 
    ## 机器学习算法
    # 线性回归：lr
    # 岭回归：ridge
    # 线性向量机：svr
    # 随机森林：rf
    g.method = 'svr'
    
    ## 分组测试之用 ####
    # True:开启分组测试（g.stocknum失效,g.group有效，g.quantile有效）
    # False:关闭分组测试（g.stocknum有效，g.group有效，g.quantile失效）
    g.invest_by_group = False
    # 每组（占所有股票中的）百分比
    # g.group（MAX）* g.quantile = 1， 即包含全部分组
    g.quantile = 0.1
    # 分组
    # 第1组：1
    # 第2组：2
    # ... ...
    # 第n组：n
    g.group = 1
    # 持仓数（分组时失效）
    g.stocknum = 5

#
def set_backtest():
    set_benchmark('000985.XSHG')   #中证全指
    set_option('use_real_price', True)
    log.set_level('order', 'error')
    
# 保存不能被序列化的对象, 进程每次重启都初始化,
def process_initialize(context):
    
    # 交易次数记录
    g.__tradeCount = 0
    # 删除建仓日或者重新建仓日停牌的股票后剩余的可选股
    g.__feasible_stocks = [] 
    # 网格搜索是否开启
    g.__gridserach = False

    ## 机器学习验证集及测试集评分记录之用（实际交易策略中不需要，请设定为False）#####
    # True：开启（写了到研究模块，文件名：score.json）
    # False：关闭
    g.__scoreWrite = False
    g.__valscoreSum = 0
    g.__testscoreSum = 0
    ## 机器学习验证集及测试集评分记录之用（实际交易策略中不需要，请设定为False）#####

    # 训练集长度
    g.__trainlength = 4
    # 训练集合成间隔周期（交易日）
    g.__intervals = 21
    
    # 离散值处理列表
    g.__winsorizeList = ['log_NC', 'LEV', 'NI_p', 'NI_n', 'g', 'RD',
                            'EP','BP','G_p','PEG','DP',
                               'ROE','ROA','OPTP','GPM','FACR']
    
    # 标准化处理列表
    g.__standardizeList = ['log_mcap',
                        'log_NC', 
                        'LEV', 
                        'NI_p', 'NI_n', 
                        'g', 
                        'RD',
                        'EP',
                        'BP',
                        'G_p',
                        'PEG',
                        'DP',
                        'CMV',
                        'ROE',
                        'ROA',
                        'OPTP',
                        'GPM',
                        'FACR',
                        'CFP',
                        'PS']
                        
    # 聚宽一级行业
    g.__industry_set = ['HY001', 'HY002', 'HY003', 'HY004', 'HY005', 'HY006', 'HY007', 'HY008', 'HY009', 
          'HY010', 'HY011']
    
    '''
    # 因子列表（因子组合1）
    g.__factorList = [#估值
                    'EP',
                    #'BP',
                    #'PS',
                    #'DP',
                    'RD',
                    #'CFP',
                    #资本结构
                    'log_NC', 
                    'LEV', 
                    #'CMV',
                    #'FACR',
                    #盈利
                    'NI_p', 
                    'NI_n', 
                    #'GPM',
                    #'ROE',
                    #'ROA',
                    #'OPTP',
                    #成长
                    'PEG',
                    #'g', 
                    #'G_p',
                    #行业哑变量
                    'HY001', 'HY002', 'HY003', 'HY004', 'HY005', 'HY006', 'HY007', 'HY008', 'HY009', 'HY010', 'HY011']
    '''
    '''
    # 因子列表(因子组合2)
    g.__factorList = [#估值
                    'EP',
                    'BP',
                    #'PS',
                    #'DP',
                    'RD',
                    #'CFP',
                    #资本结构
                    'log_NC', 
                    'LEV', 
                    'CMV',
                    #'FACR',
                    #盈利
                    'NI_p', 
                    'NI_n', 
                    'GPM',
                    'ROE',
                    #'ROA',
                    #'OPTP',
                    #成长
                    'PEG',
                    #'g', 
                    #'G_p',
                    #行业哑变量
                    'HY001', 'HY002', 'HY003', 'HY004', 'HY005', 'HY006', 'HY007', 'HY008', 'HY009', 'HY010', 'HY011']
    '''
    #'''
    # 因子列表(因子组合3)
    g.__factorList = [#估值
                    'EP',
                    'BP',
                    'PS',
                    'DP',
                    'RD',
                    'CFP',
                    #资本结构
                    'log_NC', 
                    'LEV', 
                    'CMV',
                    'FACR',
                    #盈利
                    'NI_p', 
                    'NI_n', 
                    'GPM',
                    'ROE',
                    'ROA',
                    'OPTP',
                    #成长
                    'PEG',
                    'g', 
                    'G_p',
                    #行业哑变量
                    'HY001', 'HY002', 'HY003', 'HY004', 'HY005', 'HY006', 'HY007', 'HY008', 'HY009', 'HY010', 'HY011']
    #'''

# ================================================================================
# 每天开盘前
# ================================================================================

#每天开盘前要做的事情
def before_trading_start(context):
    # 当天是否交易
    g.if_trade = False                       
    # 每g.refresh_rate天，调仓一次
    if g.days % g.refresh_rate == 0:
        g.if_trade = True                           
        # 设置手续费与手续费
        set_slip_fee(context)                       
        # 设置初始股票池
        sample = get_index_stocks(g.secCode)
        # 设置可交易股票池
        #g.feasible_stocks = set_feasible_stocks(sample,context)
        g.__feasible_stocks = set_feasible_stocks(sample,context)
        # 因子获取Query
        g.__q = get_q_Factor(g.__feasible_stocks)
    g.days+=1

#5
# 根据不同的时间段设置滑点与手续费
# 输入：context（见API）
# 输出：none
def set_slip_fee(context):
    # 将滑点设置为0
    set_slippage(FixedSlippage(0)) 
    # 根据不同的时间段设置手续费
    dt = context.current_dt
    if dt > datetime.datetime(2013,1, 1):
        set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, close_today_commission=0, min_commission=5), type='stock')
    elif dt > datetime.datetime(2008,9, 18):
        set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.001, close_commission=0.