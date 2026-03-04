#!/usr/bin/env python
# coding: utf-8

# #### Barra模型初探，A股市场风格解析

# **研究目的**
# 
# 本篇内容是参考方正金工研究报告“星火” 多因子系列报告的第一篇《Barra模型初探，A股市场风格解析》，主要对Barra模型的基本原理进行介绍，对模型的细节部分进行说明，试图构建多因子收益归因模型，并利用风险收益模型对A股市场的风格进行解析，探讨 Barra 模型在 A 股市场上的用武之地。
# 
# **内容分布**
# 
# - 1.模型介绍
#     - 1-1.多因子模型介绍
#     - 1-2.因子标准化
#     - 1-3.加权最小二乘法
#     - 1-4.barra风险收益归因模型介绍
# - 2.市场主流因子介绍
#     - 2-1.因子值计算存储
#     - 2-2.因子值处理（加入收益）
# - 3.因子收益率计算
#     - 3-1.进行因子收益计算
#     - 3-2.因子收益统计分析
# - 4.组合收益归因
#     - 4-1.构建组合统计收益
#     - 4-2.组合收益分解

# ##############################################################

# **多因子模型介绍**
# 
# 多因子模型的基础理论认为：股票的收益是由一些共同的因子来驱动的，不能被这些因子解释的部分被称为股票的“特质收益率”， 而每支股票的特质收益率之间是互不相关的。那关于这些共同的因子，和股票收益的关系，可以参考下面的内容

# ![2C6C1AA3CE7D44F4A68E1405561384D0.jpg](attachment:2C6C1AA3CE7D44F4A68E1405561384D0.jpg)

# **结构化因子风险模型的作用**
# 
# 风险因子也称为贝塔因子，和 Alpha 因子不同， 风险因子的风险溢价在时间序列上的均值绝对值可以很小，用这个因子来做选股长期可能没有明显超额收益，但在月度横截面上风险因子可以影响显著影响股票收益，方向可正可负。
# 
# 
# 因子收益率波动大，控制组合对风险因子的风险暴露，可以提升组合收益的稳定性。同时，通过因子暴露和因子收益率的计算，分析投资组合历史和当前的风险风险暴露，可以进行收益分析。
# 
# 
# 在组合优化方面，传统样本协方差矩阵估计方法在股票数量较多时，矩阵可能不满秩或者矩阵条件数
# 太大，无法直接用于组合优化过程。结构化因子风险模型通过降维的方式减小了股票收益率协方差矩阵的估计误差，便于风险预测。
# 下面看下处理的一些细节
# 
# **因子标准化**
# 
# 由于不同因子在数量级上存在差别， 在实际回归中需要对单个因子在横截面上进行标准化， 从而得到均值为 0、标准差为 1 的标准化因子，这里需要特别注意一下的是，为保证全市场基准指数对每个风格因子的暴露程度均为 0，我们需要对每个因子减去其市值加权均值，再除以其标准差，计算方法如下
# ![1.jpg](attachment:1.jpg)
# 考虑一个由市值加权构成的投资组合， 可以通过如下验证看出，该投资组合对于任意因子的暴露度均为0。
# ![2.jpg](attachment:2.jpg)
# 
# **加权最小二乘法**
# 
# 前面提到，在 Barra 模型中我们假设每只股票的特质收益率互不相关，但是每只股票的特质收益率列的方差并不相同，这就导致了回归模型出现异方差性。为解决这一问题，可以采用加权最小二乘WLS 方法进行回归，对不同的股票赋予不同的权重。
# ![3.jpg](attachment:3.jpg)
# 股票特质收益率方差通常与股票的市值规模成反比，即大市值股票的特质收益率方差通常较小，因此在这里的回归公式中，我们将以市值的平方根占比作为每只股票的回归权重，将其带入公式进行计算，然后在我们实际计算的过程中，由于X为奇异矩阵，并不能顺利求出收益率f，于是我们采用下面的方法进行处理
# 
# **风险收益模型介绍**
# 
# 这里先来看下在USE4版本的barra模型下，收益表达式
# ![4.jpg](attachment:4.jpg)
# 截距项因子的加入导致自变量因子之间存在多
# 重共线性， 因此因子的拟合无法直接通过解析解求得，模型的求解转变成一个带约束条件的加权最小二乘法求解：
# ![barra1.jpg](attachment:barra1.jpg)
# 注意， 此处w是指单只股票 n 的市值权重，而w表示的是行业i内所有股票的市值占全体样本股票市值的比例。
# 
# **市场风格因子**
# 
# 基于研报中对 Barra 模型框架构建及求解过程的介绍， 我们参考并构建多因子风险收益归因模型， 并将其运用到 A 股市场上， 从截距项、行业收益、风格收益三方面验证模型正确性， 观察市场风格的变化及投资组合的风险收益来源。
# 
# 这里我们选取的风格因子可以通过聚宽因子库，风格因子获取，具体字段及说明如下
# ![sty.jpg](attachment:sty.jpg)
# 
# 风格因子获取地址：
# https://www.joinquant.com/help/api/help?name=factor_values#%E9%A3%8E%E6%A0%BC%E5%9B%A0%E5%AD%90
# 
# 此处我们采用以上因子作为模型的解释变量，进行下面的研究。
# 
# 
# 选 定 2016.6.1-2019.6.3 为 样 本 考 察 期 间 ， 以 中 证 500指数（000905.XSHG） 成分股为考察样本，对市场风格因子的表现进行实证研究，在实际计算中还需对数据进行如下处理：
# 
# - 1） 剔除上市时间小于63天的股票；
# - 2） 剔除标记为ST、*ST的股票；
# - 3） 剔除任意因子为 NaN 的股票；
# 
# 参考研报中为避免回归模型中自变量之间产生多重共线性的情况，而引入相关强度指标RSI，对各风格因子之间的相关程度进行检查，该指标的构造方法如下
# ![4.jpg](attachment:4.jpg)
# 
# 
# 其中，corr 是指在截面 t 期，所有股票的 A、 B 因子之间的相关系数。类似于绩效评价中的信息比率 IC_IR，RSI指标 综合考虑了因子的平均相关系数以及相关系数的稳定性大小，下面的计算中有展示2016年到2019年期间各风格因子之间的相关强度，其中市值因子与杠杆因子之间、残差波动率因子与流动性因子之间存在较强的正相关关系；而市值因子与非线性市值因子之间、杠杆因子与非线性市值之间存在较强的负相关关系。
# 

# 工具包、工具函数
# 工具函数
import time
from datetime import datetime, timedelta
from jqdata import *
import numpy as np
import pandas as pd
import math
from statsmodels import regression
import statsmodels.api as sm
import matplotlib.pyplot as plt
import datetime
from scipy import stats
from jqfactor import *
from scipy.optimize import minimize
import warnings  
warnings.filterwarnings('ignore') 

# 设置画图样式
plt.style.use('ggplot')

# 获取日期列表
def get_tradeday_list(start,end,frequency=None,count=None):
    if count != None:
        df = get_price('000001.XSHG',end_date=end,count=count)
    else:
        df = get_price('000001.XSHG',start_date=start,end_date=end)
    if frequency == None or frequency =='day':
        return df.index
    else:
        df['year-month'] = [str(i)[0:7] for i in df.index]
        if frequency == 'month':
            return df.drop_duplicates('year-month').index
        elif frequency == 'quarter':
            df['month'] = [str(i)[5:7] for i in df.index]
            df = df[(df['month']=='01') | (df['month']=='04') | (df['month']=='07') | (df['month']=='10') ]
            return df.drop_duplicates('year-month').index
        elif frequency =='halfyear':
            df['month'] = [str(i)[5:7] for i in df.index]
            df = df[(df['month']=='01')