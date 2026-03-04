#!/usr/bin/env python
# coding: utf-8

# 引言

# 研究目的

# 参考光大证券研报《20190615-光大证券-多因子系列报告之二十二：再论动量因子》，对传统动量因子进行分析探究，并根据研报方式对传统动量因子进行改造，寻找提升因子效果的方法

# 研究思路

# 1.模仿研报方式，对各传统动量因子进行相应的分析
# 
# 2.参考研报方式对传统动量因子进行改造，并模仿研报方式进行类似的分析以及和原动量因子的对比
# 
# 3.根据自己的理解，对构造的各因子进行进一步的分析
# 
# 4.结合模仿研报的分析以及自己对各因子的分析，尝试寻找表现最优的动量相关因子，并尝试借此构建策略

# 研究结论

# 1.和研报不同，构造的一个月传统动量因子本身的单调性等表现不错，因此模仿研报方式改造的前几个动量因子相较于一个月传统动量因子并没有十分显著的提升
# 
# 2.
# 
# 6.尽管和研报结论有一定出入，但成交额改造k线下的因子确实多头表现优秀，综合各种测试，选用表现最好的改造k线因子并结合传统动量因子构建策略，策略在13-17年，19年确实有不错的表现

# 研究设置

# 时间范围：日度因子：2006.01.01 - 2019.05.31
# 
#                  分钟数据因子：2009.01.01 - 2017.12.31
# 
# 股票池： 中证全指


''' --------------------↓      开始研究      ↓-------------------- '''


# 1.导入库


import pandas as pd
import numpy as np
from jqdata import * 
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.cm as cm
from tqdm import tqdm
import statsmodels.api as sm #剔除流动性时使用
from statsmodels.regression.linear_model import OLS  #这里是用截面OLS取残差，有一定缺陷
from scipy.stats import ttest_1samp  #t检验
from IPython.display import display
from jqfactor import neutralize  #主要用于行业市值中性化
from jqfactor import get_factor_values   #获取大类因子
import time
import datetime
import os
import warnings
warnings.filterwarnings('ignore')
sns.set()
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号


# 2.数据读取、计算和储存

# （1）基本数据的读取和储存


save_path = r'D:\mom'
os.chdir(save_path)  #开始计算和存储数据，设定存储路径
zzqz = get_index_stocks('000985.XSHG')  #在中证全指测试
open_close = get_price(zzqz,fields=['close','open','paused'],start_date='2006-01-01',end_date='2019-05-31')  #收盘开盘停牌
paused = open_close['paused']
open_ = open_close['open']
close = open_close['close']
st = get_extras('is_st', zzqz, start_date='2006-01-01', end_date='2019-05-31') #st
st.to_csv('st06.csv') #储存
open_.to_csv('open_06.csv')
close.to_csv('close06.csv')
paused.to_csv('paused06.csv')


# （2）大类因子的读取、计算、储存


#循环读取各大类因子
factors = ['liquidity','market_cap','circulating_market_cap','size','book_to_price_ratio','VOL20','roe_ttm']  
for fac_name in factors:
    dic = {}
    for date in tqdm(close.index): #循环日期读取，读取时间区间和前面一致，这里由于get_factor_values有最大返回条数限制，只好一天一天读了
        dic[date] = get_factor_values(zzqz,factors=[fac_name],start_date=date,end_date=date)[fac_name].iloc[0]
    factor = pd.DataFrame.from_dict(dic,'index')
    name = fac_name + '.csv'
    factor.to_csv(name)
#计算研报中大类因子fc_mc，自由流通市值/总市值
market_cap = pd.read_csv('market_cap.csv',index_col=0,parse_dates=True)
circulating_market_cap = pd.read_csv('circulating_market_cap.csv',index_col=0,parse_dates=True)
fc_mc = circulating_market_cap/market_cap
fc_mc.to_csv('fc_mc.csv')


# （3）常用动量因子


'''
滚动计算，最后测试的因子结论和研报有些地方不同，个人认为有很多原因，这里应该是一个，不清楚研报是否用的收盘价，以及是否滚动，滚动的话是多少天
这些计算方式上的差异都可能导致最后结果和研报并不完全相同，后面涉及到相应的计算部分会进一步解释
'''
mom_1m = close.pct_change(20) #用收盘价计算动量
mom_3m = close.pct_change(60)
mom_6m = close.pct_change(120)
mom_12m = close.pct_change(240)
mom_24m = close.pct_change(480)
mom_1m_max = close.pct_change().rolling(20,min_periods=12).max()[close.notnull()] #一个月收益率最大值


# （4）预处理函数


def winsorize(df, nsigma=3): #去极值，MAD法，超过md +/- 3*mad的部分将按大小排序拉回
    md = df.median(axis=1)
    mad = 1.483 * (df.sub(md, axis=0)).abs().median(axis=1)
    up = df.apply(lambda k: k > md + mad * nsigma)
    down = df.apply(lambda k: k < md - mad * nsigma)
    df[up] = df[up].rank(axis=1, pct=True).multiply(mad * 0.5, axis=0).add(md + mad * nsigma, axis=0)

    df[down] = df[down].rank(axis=1, pct=True).multiply(mad * 0.5, axis=0).add(md - mad * (0.5 + nsigma), axis=0)

    return df
def standarize(df): #截面标准化
    return df.sub(df.mean(axis=1),axis=0).div(df.std(axis=1),axis=0)
    '''
#横截面行业市值中性化，对数市值和申万1级行业，这里是和研报不同的另一个地方，研报采用中信1级行业，可能也是导致后续结论略不同的原因之一
    '''
#因为要循环横截面中性化，比较耗时
#本来是想用中信1级的但是没在聚宽找着这个分类。。就干脆用申万1级了
def neutralize_(df):  
    res_dic = {}
    for date in tqdm(df.index):
        res_dic[date] = neutralize(df.loc[date,:], how=['sw_l1','size'], date=date, axis=1)
    return pd.DataFrame.from_dict(res_dic,'index')
def format_factor(factor):  #综合上面的三个函数，预处理因子，去极值、标准化、行业市值中性化
    adjfactor = winsorize(factor)
    adjfactor = standarize(adjfactor)
    adjfactor = neutralize_(adjfactor)
    return adjfactor


# （5）预处理动量因子


mom_1m = format_factor(mom_1m)  #计算并存储预处理后的因子
mom_3m = format_factor(mom_3m)
mom_6m = format_factor(mom_6m)
mom_12m = format_factor(mom_12m)
mom_24m = format_factor(mom_24m)
mom_1m_max = format_factor(mom_1m_max)
mom_1m.to_csv('mom_1m_fmt.csv')
mom_3m.to_csv('mom_3m_fmt.csv')
mom_6m.to_csv('mom_6m_fmt.csv')
mom_12m.to_csv('mom_12m_fmt.csv')
mom_24m.to_csv('mom_24m_fmt.csv')
mom_1m_max.to_csv('mom_1m_max_fmt.csv')


# （6）趋势动量因子的计算和储存


#趋势动量因子的计算
'''
#这里是简单计算了移动平均MA，这里也涉及到计算方式不同的问题
#比如用开盘价还是用收盘价，是否加Min_periods（因为滚动期太长，不然可能很多空值，例如不加的话一天空值会导致后面240天的滚动都是空值）
#以及是否用MA计算收益率作为趋势动量因子
'''
ma_20 = close.rolling(2