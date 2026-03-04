#!/usr/bin/env python
# coding: utf-8

# 1 引言
# 研究目的：
# 本文参考广发证券《基于日内高频数据的短周期选股因子研究-高频数据因子研究系列一》，对研报构造的因子做了实现，并复现了里面的结果，做出了分析。其中用个股日内高频数据构造选股因子，低频调仓的思路是一个很好的方向。
#
# 研究内容：
# 基于个股日内高频数据，构建了已实现波动(Realized Volatility) 𝑅𝑉𝑜𝑙，已实现偏度(Realized Skewness)𝑅𝑆𝑘𝑒𝑤、已实现峰度(Realized Kurtosis)𝑅𝐾𝑢𝑟𝑡因子指标，考察这三个因子在回测区间内对个股收益率 的区别度。
#
# 研究结论：
# 在三个因子中偏度$RSkew$因子最有效，分组区分度高，比较稳定，收益最高。

# 2 因子构建
# 因子构建过程摘自研报，具体因子指标构建如下:
#
# 1. 对于每个个股在交易日t，首先计算个股在特定分钟频率下第i个的收益率 $r_{t,i}$， $r_{t,i}$ = $p_{t,i}$ − $p_{t,i-1}$，其中$p_{t,i}$表示在交易日t，个股在第i个特定分钟频率下的对数价格，$p_{t,i-1}$表示在交易日t，个股在第i−1个特定分钟频率下的对数价格。
#
# 2. 对于每个个股，根据𝑟𝑡,𝑖分别计算个股在交易日t下的已实现方差(Realized Variance) $RDVar_t$、已实现偏度(Realized Skewness) $RDSkew_t$，已实现峰度(Realized kurtosis) $RDKurt_t$。其中:
#
# <font face="黑体" size=5>
# $$RDVar_t = \sum\limits_{ i=1}^{n}r_{t,i}^2$$
# </font>
#
# <font face="黑体" size=5>
# $$RDSkew_t =  \frac {\sqrt N\sum\limits_{ i=1}^{n}r_{t,i}^3}{RDVar_t^{3/2}}$$
# </font>
#
# <font face="黑体" size=5>
# $$RDKurt_t =  \frac {N \sum\limits_{ i=1}^{n}r_{t,i}^4}{RDVar_t^2}$$
# </font>
#
# 其中N表示个股在交易日t中特定频率的分钟级别数据个数，如在1分钟行情级别下，数据个数N为60*4=240；在5分钟行情级别下，数据个数N为240/5=48。
#

# 3. 对于每个个股在交易日t计算累计已实现波动(Realized Volatility)$RVol_t$， 已实现偏度(Realized Skewness)$RSkew_t$、已实现峰度(Realized Kurtosis) $RKurt_t$ ，其中:
# <font face="黑体" size=5>
# $$RVol_t = \left(\frac{242}{n} {\sum\limits_{ i=0}^{n}}RDVar_{t-i}\right)^{1/2}$$
# </font>
#
# <font face="黑体" size=5>
# $$RSkew_t =  \frac{1}{n}{\sum\limits_{ i=0}^{n}}RDSkew_{t-i}$$
# </font>
#
# <font face="黑体" size=5>
# $$RKurt_t =  \frac{1}{n}{\sum\limits_{ i=0}^{n}}RDKurt_{t-i}$$
# </font>
#
# 4. 在每期调仓日截面上，按照上述公式计算每个个股的已实现波动(Realized Volatility)$RVol_t$，已实现偏度(Realized Skewness)$RSkew_t$、已实现峰度(Realized Kurtosis)$RKurt_t$指标，针对每个由高频数据计算得到的因子指标在历史上的分档组合表现，试图寻找出相对有效的因子指标。

# 3 构造因子数据
#
# 计算因子值的过程比较慢，大概耗时1小时左右。如果直接下载我构造好的数据文件（factor_dict.pkl）上传到研究里可以跳过这一步，直接到因子特征展示开始执行。
#
# 以下开始计算因子值：

import pandas as pd
import numpy as np
from jqdata import *
import math
from pandas import *
from datetime import date, timedelta

N = 48
n = 5


# 获取某个交易日的因子值
def get_one_trade_day_data(cache = {}, stocks = None, trade_date = None):
#     print(trade_date)

    # 后面需要在交易日t计算累计已实现波动等数据，需要获取交易日t到交易日t-n之间的交易日
    trade_days = get_trade_days(start_date=None, end_date=trade_date, count=n)

    # dataframe的index，为股票code
    factor_df_index = []

    # 计算得到的因子数值
    factor_df_data = []
    for security in stocks:
#         print(security)

        # 获取收盘价、是否停牌。
        price_info = get_price(security, start_date=None, end_date=trade_date, frequency='daily',
                               fields=['paused', 'close'], skip_paused=False, fq='pre',
                               count=n)

        # 交易日t 当日的收盘价
        t_close = price_info.iloc[-1]['close']

        # 过滤停牌数据(如果过去n日某天有停牌，后面计算偏度时的分母是0会报除0异常)
        # 如果有paused为1的数据，会被drop掉 则长度是0
        if len(price_info.T.replace(1.0, np.nan).dropna().index.values.tolist()) == 0:
#             print("含有停牌数据,continue")
            continue

        # 前n个交易日已实现方差之和
        sum_rd_var = 0.0

        # 前n个交易日已实现偏度之和
        sum_rd_skew = 0.0

        # 前n个交易日已实现峰度之和
        sum_rd_kurt = 0.0

        # 遍历t-n交易日 到 t交易日
        for trade_day in trade_days:
            # 如果重复调用get_bars实在是太慢了，这里缓存一下数据
            if trade_day in cache.keys() and security in cache[trade_day].keys():
                bars = cache[trade_day][security]
            else:
                # 这里要获取交易日当天的数据 所以end_dt要+1
                # 研报中N为48，对应的频率为5分钟(一个交易日有60*4=240分钟，240/48 = 5)
                bars = get_bars(security, N, unit='5m',
                                fields=['date', 'open', 'high', 'low', 'close'],
                                include_now=False, end_dt=trade_day + timedelta(days=1), fq_ref_date=None)
                if trade_day not in cache.keys():
                    cache[trade_day] = {}
                cache[trade_day][security] = bars

            # 个股收益率平方、立方、4次方之和
            sum_rt2 = 0.0
            sum_rt3 = 0.0
            sum_rt4 = 0.0

            for i in range(1, N):
                # 个股在第i个特定分钟频率 下的对数价格
                pi = math.log(bars[i]['close'])

                # 个股在第i-1个特定分钟频率 下的对数价格
                pi_1 = math.log(bars[i - 1]['close'])

                # 个股在特定分钟频率下第i个的收益率
                rt = pi - pi_1

                sum_rt2 += math.pow(rt, 2)
                sum_rt3 += math.pow(rt, 3)
                sum_rt4 += math.pow(rt, 4)

            # 交易日t下的已实现方差
            rd_var = sum_rt2

            # 交易日t下的已实现偏度
            if sum_rt3 == 0:
                rd_skew = 0
            else:
                rd_skew = math.sqrt(N) * sum_rt3 / (math.pow(rd_var, 3 / 2))

            # 交易日t下的已实现峰度
            if sum_rt4 == 0:
                rd_kurt = 0
            else:
                rd_kurt = N * sum_rt4 / (math.pow(rd_var, 2))

            sum_rd_var += rd_var
            sum_rd_skew += rd_skew
            sum_rd_kurt += rd_kurt

        # 累计已实现波动
        r_vol = math.sqrt((242.0 / n) * sum_rd_var)

        # 已实现偏度