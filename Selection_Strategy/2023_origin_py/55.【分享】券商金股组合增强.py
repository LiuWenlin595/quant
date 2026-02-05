# 克隆自聚宽文章：https://www.joinquant.com/post/33881
# 标题：【分享】券商金股组合增强
# 作者：Hugo2046

'''
Author: Hugo
Date: 2021-05-19 10:38:22
LastEditTime: 2021-06-24 14:45:25
LastEditors: Hugo
Description: 券商金股策略

每月初（第2个交易日）获取券商的金股数据（此部分数据来源于手动整理的文件gold_stock_20210609.csv）其数据结构
见read_gold_stock；
每周使用动量因子对月初获取的金股进行筛选，获取得分前N的股票(g.handle_num进行控制)；
'''

from jqdata import *
from jqfactor import (Factor,calc_factors)
# 聚宽的组合优化
from jqlib.optimizer import (portfolio_optimizer,
                             MaxProfit,
                             MaxSharpeRatio,
                             RiskParity,
                             MinVariance,
                             WeightConstraint, Bound)

import functools
from dateutil.parser import parse

from scipy import stats
from scipy import optimize
import statsmodels.api as sm
from sklearn.covariance import ledoit_wolf

import numpy as np
import pandas as pd
import datetime as dt
from typing import (List, Tuple, Union,Callable)
from six import BytesIO  # 文件读取


def initialize(context):

    set_params()
    set_variables()
    set_backtest()
    g.in_week = 5  # 周内第五个交易日

    # 每月的第五个交易日调仓
    run_monthly(get_target_securities, 2, 'open',
                reference_security='000300.XSHG')
    run_weekly(trade_func, g.in_week, 'open', reference_security='000300.XSHG')

# 配置基础参数


def set_params():

    # 是否使用因子进行辅助
    # 为True使用动量因子,False使用券商推荐率
    g.use_factor = True

    # 设置持仓
    g.handle_num = 15

    # 获取金股数据
    read_gold_stock()
    
    # 是否组合优化
    # 可选项:MaxSharpeRatio，MaxProfit,MinVariance,RiskParity
    # False为不组合优化
    g.optimizer_mod = 'MaxProfit'  # 'MaxSharpeRatio'

# 基础变量


def set_variables():

    g.base_target: pd.DataFrame = None  # 储存当月金股

# 回测设置


def set_backtest():

    set_option("avoid_future_data", True)  # 避免数据
    set_option("use_real_price", True)  # 真实价格交易
    set_option('order_volume_ratio', 1)  # 根据实际行情限制每个订单的成交量
    set_benchmark('000300.XSHG')  # 设置基准
    #log.set_level("order", "debuge")
    log.set_level('order', 'error')


# 每日盘前运行 设置不同区间手续费
def before_trading_start(context):

    # 手续费设置
    # 将滑点设置为0.002
    set_slippage(FixedSlippage(0.002))

    # 根据不同的时间段设置手续费
    dt = context.current_dt

    if dt > datetime.datetime(2013, 1, 1):
        set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5))

    elif dt > datetime.datetime(2011, 1, 1):
        set_commission(PerTrade(buy_cost=0.001, sell_cost=0.002, min_cost=5))

    elif dt > datetime.datetime(2009, 1, 1):
        set_commission(PerTrade(buy_cost=0.002, sell_cost=0.003, min_cost=5))

    else:
        set_commission(PerTrade(buy_cost=0.003, sell_cost=0.004, min_cost=5))


# 读取金股的储存文件


def read_gold_stock() -> None:

    # 读取储存金股的文件 起始日期2019年7月
    '''
    文件结构：
        ----------------------------------------------
        |所属日期|推荐机构|股票名称|所属行业|股票代码 |
        ----------------------------------------------
        |2019/7/1|安信证券|科大讯飞|  计算机|002230.SZ|
        -----------------------------------------------
    '''
    g.gold_stock_frame = pd.read_csv(BytesIO(read_file('gold_stock_20210609.csv')),
                                     index_col='所属日期', parse_dates=['所属日期'])

    # 过滤港股
    g.gold_stock_frame = g.gold_stock_frame[(
        g.gold_stock_frame['股票代码'].str[-2:] != 'HK')]
    # 股票代码转为聚宽的代码格式
    g.gold_stock_frame['股票代码'] = g.gold_stock_frame['股票代码'].apply(
        normalize_code)
    # 将索引转为年-月形式
    g.gold_stock_frame.index = g.gold_stock_frame.index.strftime('%Y-%m')


# 其他

@functools.lru_cache()
def get_weekofyear_date() -> pd.DataFrame:
    '''
    获取 周度交易日期
    ------
        return index=date columns date num_week:周度中的第N个交易日
    '''
    idx = get_all_trade_days()
    days = pd.DataFrame(idx, index=pd.DatetimeIndex(idx), columns=['date'])
    days['num_week'] = days.groupby([
        days.index.year, days.index.weekofyear
    ])['date'].transform(lambda x: range(1,
                                         len(x) + 1))

    return days

def get_num_weekly_trade_days(days: pd.DataFrame, N: int) -> pd.Series:
    '''
    获取周度的第N个交易日
    ------
    输入参数:
        days:index=date columns date num_week
        N:第N个交易日
    ------
    return pd.DataFrame
           index-datetime.datetime columns-datetime.date
    '''

    cond = days.groupby([days.index.year, days.index.weekofyear
                         ])['num_week'].apply(lambda x: x == min(len(x), N))
    target = days[cond]

    return target.drop(columns=['num_week'])
    
def get_past_weekly_days(watch_date: str, weekly_n: int, count: int) -> list:
    '''
    查询过去N期的周度节点日期
    ------
    输入参数:
        watch_date:观察期
        weekly_n:周内第N个交易日
        count:获取前N期
    -----
        return list-datetime.date
    '''

    if isinstance(watch_date, str):
        watch_date = parse(watch_date)

    days = get_weekofyear_date()
    weekly = get_num_weekly_trade_days(days.loc[:watch_date], weekly_n)

    return weekly['date'].iloc[-count - 1:].values.tolist()
    
def get_next_returns(factor_df: pd.DataFrame,
                     last_date: str = None) -> pd.DataFrame:
    '''
    获取下期收益率
    ------
    输入:
        factor_df:MuliIndex-level0-datetime.date level1-code columns - factors
        last_date:最后一期时间
    '''
    if last_date:
        days = pd.to_datetime(
            factor_df.index.get_level_values('date').unique().tolist() +
            [last_date])
    else:
        days = pd.to_datetime(
            factor_df.index.get_level_values('date').unique().tolist())

    dic = {}
    for s, e in zip(days[:-1], days[1:]):

        stocks = factor_df.loc[s.date()].index.get_level_values(
            'code').unique().tolist()

        a = get_price(stocks, end_date=s, count=1, fields='close',
                      panel=False).set_index('code')['close']

        b = get_price(stocks, end_date=e, count=1, fields='close',
                      panel=False).set_index('code')['close']

        dic[s] = b / a - 1

    df = pd.concat(dic).to_frame('next_ret')

    df.index.names = ['date', 'code']
    return df
    
def prepare_data(securities: list, watch_date: str, N: int,
                 count: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    '''
    获取当期股票池 过去N期的因子值及未来期收益率
    T期没有未来期收益,仅T-1至T-N期有
    ------
    输入参数:
        securities:股票列表
        watch_date:观察期
        N:周度交易日
        count:过去N期
    ------
    return 
        factor_df, next_ret
    '''

    periods = get_past_weekly_days(watch_date, N, count)

    f_dict = {}

    for trade in periods:

        f_dict[trade] = get_momentum_factor(securities, trade)

    f_df = pd.concat(f_dict, names=['date', 'code'])

    next_ret = get_next_returns(f_df)

    return f_df, next_ret


def composition_factors(securities:list,watchDt:str,in_week: int,window: int) -> pd.DataFrame:
    '''
    获取回测范围内的因子合成值
    ------
    输入参数
        securities:金股数据表
        in_week:每周的最后一日进行调仓
        num_trade:每月的第N个交易日获取到金股并交易
        window:回看窗口期为12周
    
    '''
   
    # 获取T至T-N期因子值
    f_df, next_ret = prepare_data(securities, watchDt, in_week, window)

    # 调用因子合成类
    fw = FactorWeight(f_df, next_ret)

    # 获取不同因子合成的值
    method_dic = {
        '等权法': fw.fac_eqwt(),
        '历史因子收益率加权法': fw.fac_ret_half(False),
        '历史因子收益率半衰加权法': fw.fac_ret_half(True),
        '历史因子IC加权法': fw.fac_ic_half(2),
        '最大化IC_IR加权法': fw.fac_maxicir_samp(),
        '最大化 IC_IR 加权法(Ledoit)': fw.fac_maxicir(),
        '最大化IC_IR加权法': fw.fac_maxic()
    }

    df = pd.concat((ser for ser in method_dic.values()), axis=1)
    df.columns = list(method_dic.keys())

    
    return df
    
def time2str(watch_date: dt.datetime, fmt='%Y-%m-%d') -> str:
    '''日期转文本'''
    if isinstance(watch_date, (dt.datetime, dt.date)):
        return watch_date.strftime(fmt)
    else:
        return time2str(parse(watch_date))



# 金股筛选指标

# 计算券商推荐率


def get_net_promoter_score(target_df: pd.DataFrame) -> pd.Series:
    '''计算券商推荐率'''

    return target_df.groupby('股票代码')['推荐机构'].count() / len(target_df['推荐机构'].unique())


# 因子构造

# 因子合成方法
class FactorWeight(object):
    '''
    参考:《20190104-华泰证券-因子合成方法实证分析》
    -------------
    传入T期因子及收益数据 使用T-1至T-N期数据计算因子的合成权重
    
    现有方法：
    1. fac_eqwt 等权法
    2. fac_ret_half 历史因子收益率（半衰）加权法
    3. fac_ic_half 历史因子 IC（半衰）加权法
    4. fac_maxicir_samp 最大化 IC_IR 加权法 样本协方差
       fac_maxicir  Ledoit压缩估计方法计算协方差
    5. fac_maxic 最大化IC加权法 Ledoit压缩估计方法计算协方差
    ------
    输入参数:
        factor:MuliIndex level0为date,level1为code,columns为因子值
            -----------------------------------
                date    |    asset   |
            -----------------------------------
                        |   AAPL     |   0.5
                        -----------------------
                        |   BA       |  -1.1
                        -----------------------
            2014-01-01  |