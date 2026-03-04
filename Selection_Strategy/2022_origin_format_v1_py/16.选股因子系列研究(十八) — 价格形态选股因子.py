#!/usr/bin/env python
# coding: utf-8

# 研究目的：
# 
# 本文参考海通证券冯佳睿、袁林青撰写的《选股因子系列研究(十八)——价格形态选股因子》，根据研报分析，主要测试了开盘冲高、盘低回升以及均价偏离这三种价格类因子。基于该文章，本文对文章中提到的三种价格类因子进行因子有效性分析，从而实现对股票未来收益的预测，为 alpha 因子的挖掘提供了一定思路。 
# 
# 研究内容：
# 
# （1）构建分别以月和半月为观察期的三种价格类因子；  
# （2）对构建出来的因子进行因子有效性分析，分别包括因子 IC/IR 分析，分层回测组合分析等，并根据结果分析因子的预测能力以及不同观察期对预测能力的影响；   
# （3）对每个因子，加入行业、市值、贝塔、动量、残差波动率以及非线性市值这 6 个因子进行正交化处理，分析正交化后因子对组合收益的贡献及其预测效果；  
# （4）对因子进行多因子模型回测分析，分析不同因子对组合收益带来的贡献等。 
# 
# 研究结论：
# 
# （1）通过对这三种价格类因子的因子有效性分析结果来看，三种因子均有较好的选股能力，针对不同的观察期，月度因子比半月度因子具有更强的选股能力，但是相对而言，这三种因子的分层回测单调性不足；  
# （2）通过将这三种因子与行业、市值、贝塔、动量、残差波动率以及非线性市值这 6 个因子进行正交化处理，分析结果可知正交化因子预测稳定性得到较大提升，因子的分层回测单调性得到增强；  
# （3）对多因子模型进行回测分析，分别从横截面收益率回归和纯多头组合这两方面进行分析，根据分析结果来看，在加入因子 HighOpen 或者因子 VwapClose 后，模型收益能力和风险控制能力相比原始模型均得到了较大提升。

# 1 因子构建

# 通过对 K 线的研究，不难发现，常见价格信息，如高、开、低、收等，也能够很好地实现对股票收益的刻画，且对于大多数散户而言，K 线是其主要研究对象，从中提取特征信息，如 K 线的上影线、下影线等等。  
# 参考研报内容，考虑引入开盘、盘高、盘低以及均价构建相关指标刻画股票日内的形态特征。共引入三个指标：开盘冲高、盘低回升以及均价偏离。具体指标计算方式如下所示：  
# （1）开盘冲高：log(盘高/开盘价)。该指标越大，表示股票盘中冲高幅度越大。  
# （2）盘低回升：log(收盘价/盘低)。该指标越大，表示股票从盘低回升的幅度也就越大。  
# （3）均价偏离：log(均价/收盘价)。该指标体现了股票成交均价相对于收盘价的偏离。  
# 紧接着，设计因子实现上述指标，在每个月或者每半个月的时间窗口下，计算上述三个因子过去 1 个月或者半个月的均值，具体计算公式如下所示：  
# <center> $ HighOpen = 1/K * \sum_{i=t-k}^{t-1}log(high_i / open_i)$ </center>
# <center> $ CLoseLow = 1/K * \sum_{i=t-k}^{t-1}log(close_i / low_i)$ </center>
# <center> $ VwapClose = 1/K * \sum_{i=t-k}^{t-1}log(vwap_i / close_i)$ </center>

# 1.1 日期列表获取

# 在每个月的月末对因子数据进行提取，因此需要对每个月的月末日期进行统计。  
# 输入参数分别为 peroid、start_date 和 end_date，其中 peroid 进行周期选择，可选周期为周(W)、月(M)和季(Q)，start_date和end_date 分别为开始日期和结束日期。  
# 函数返回值为对应的日期。本文选取开始日期为 2013.1.1，结束日期为 2018.1.1。周期如月取 “W”，半月取 “2W”。

from jqdata import *
import datetime
import pandas as pd
import numpy as np
from six import StringIO
import warnings
import time
import pickle
import scipy.stats as st
from jqfactor import winsorize_med
from jqfactor import neutralize
from jqfactor import standardlize
import statsmodels.api as sm
import seaborn as sns
warnings.filterwarnings("ignore")


# 获取指定周期的日期列表 'W、M、Q'
def get_period_date(peroid,start_date, end_date):
    #设定转换周期period_type  转换为周是'W',月'M',季度线'Q',五分钟'5min',12天'12D'
    stock_data = get_price('000001.XSHE',start_date,end_date,'daily',fields=['close'])
    #记录每个周期中最后一个交易日
    stock_data['date']=stock_data.index
    #进行转换，周线的每个变量都等于那一周中最后一个交易日的变量值
    period_stock_data=stock_data.resample(peroid,how='last')
    date=period_stock_data.index
    pydate_array = date.to_pydatetime()
    date_only_array = np.vectorize(lambda s: s.strftime('%Y-%m-%d'))(pydate_array )
    date_only_series = pd.Series(date_only_array)
    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    start_date=start_date-datetime.timedelta(days=1)
    start_date = start_date.strftime("%Y-%m-%d")
    date_list=date_only_series.values.tolist()
    date_list.insert(0,start_date)
    return date_list


# 1.2 股票列表获取

# 股票池: 全 A 股  
# 股票筛选：剔除 ST 股票，剔除上市 3 个月内的股票，每只股票视作一个样本  


# 去除上市距beginDate不足 3 个月的股票
def delect_stop(stocks,beginDate,n=30*3):
    stockList = []
    beginDate = datetime.datetime.strptime(beginDate, "%Y-%m-%d")
    for stock in stocks:
        start_date = get_security_info(stock).start_date
        if start_date < (beginDate-datetime.timedelta(days = n)).date():
            stockList.append(stock)
    return stockList

# 获取股票池
def get_stock_A(begin_date):
    begin_date = str(begin_date)
    stockList = get_index_stocks('000002.XSHG',begin_date)+get_index_stocks('399107.XSHE',begin_date)
    #剔除ST股
    st_data = get_extras('is_st', stockList, count = 1, end_date=begin_date)
    stockList = [stock for stock in stockList if not st_data[stock][0]]
    #剔除停牌、新股及退市股票
    stockList = delect_stop(stockList, begin_date)
    return stockList


# 1.3 数据获取

# 参考上面实现因子构建的公式，在每个月以及每半个月最后一天，分别根据对应的时间窗口，对因子进行计算，并将计算得到的因子数据分别保存在变量 factorData_M 以及 factorData_2W 中。

start = time.clock()
# 时间窗口
N = 20
begin_date = '2013-01-01'
end_date = '2018-01-01'
# 获取月度日期列表
dateList = get_period_date('M',begin_date, end_date)
factorData_M = {}
for date in dateList:
    stockList = get_stock_A(date)
    # 获取价格类数据
    df_data = get_price(stockList, count = N, end_date = date, frequency='1d', fields=['high', 'open', 'low', 'close', 'avg'])
    # 因子计算
    temp1 = log(df_data["high"] / df_data["open"]).mean()
    temp2 = log(df_data["close"] / df_data["low"]).mean()
    temp3 = log(df_data["avg"] / df_data["close"]).mean()
    tempData = pd.DataFrame()
    tempData["HighOpen"] = temp1
    tempData["CloseLow"] = temp2
    tempData["VwapClose"] = temp3
    tempData = standardlize(tempData, axis=0)
    factorData_M[date] = tempData
elapsed = (time.clock() - start)
print("Time used:",elapsed)


start = time.clock()
N = 10
begin_date = '2013-01-01'
end_date = '2018-01-01'
# 获取半月日期列表
dateList = get_period_date('2W',begin_date, end_date)
factorData_2W = {}
for date in dateList:
    stockList = get