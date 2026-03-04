#!/usr/bin/env python
# coding: utf-8

# 1 引言

# 研究目的：
# 本文参考方正证券《行业轮动的黄金律：日内动量与隔夜反转》，对研报里面的结果进行了分析，并对比了传统动量因子策略和将传统动量因子拆分后日内涨跌幅因子和隔夜涨跌幅因子的效果。
#
# 研究内容：
# 不同的交易者群体，会有不同的行为模式。 在交易日内的不同时段，交易者的成分可能存在系统性差异， 因而会导向不同的市场行为
# 特征，最终形成各式各样的日内模式（intraday patterns）。按照这个思路，为了研究动量效应的日内精细规律，本文将行业指数的每
# 日收益率拆解为日内收益率（今收/今开-1） 和隔夜收益率（今开/昨收-1）。
#
# 1）将过去 15 个交易日的日内收益率加总，命名为日内涨跌幅因子 M0；将过去 15 个交易日的隔夜收益率加总，称为隔夜涨跌幅因子M1。
# 2）将这两个效应结合在一起， 构建新的行业轮动模型。 在具体操作上,我们将 N 个行业指数按照 M0 因子值从低到高分别打 1 分至 N 分,按照 M1 因子值从高到低分别打1分至N分，将两项打分相加,得到每个行业的总得分，此因子命名为黄金律因子M_gold。
#
#
# 3）行业轮动的回测框架如下：
#    测试时段： 2006 年 1 月-2017 年 11 月；
#    样本空间： 申万一级行业指数（共 28 个）；
#    调仓方式： 在每个月初，将行业指数按总得分排序，划分为五组，分别持有至月末；得分最高的组合为多头组合，得分最低的组合
#               为空头组合
#
#
# 本文所用因子构建细节：
# 根据研究内容，我们列出本文所用的四个因子构建细则：
#
# 1）传统动量因子：前十五天涨跌幅
#
# 2）日内涨跌幅因子M0：前十五日内收益率加总，其中日内收益率为今收/今开-1
#
# 3）隔夜涨跌幅因子M1:前十五日隔夜收益率加总，其中隔夜收益率为今开/昨收-1
#
# 4）黄金律因子M_gold：将日内涨跌幅因子和隔夜涨跌幅因子根据打分法等权加总构成黄金律因子，其中日内涨跌幅因子由于动量效应采取从低到高分别打1-N分，而隔夜涨跌幅因子由于反转效应由高到底分别打1-N分。
#
# 研究结论：
# 1）本文将传统的动量因子（即前十五日涨跌幅）进行分拆，对交易者的行为模式进行进一步细化，可以发现交易者存在不同的日内交易模式，这为构建新的因子提供思路。
#
# 2）可以发现行业指数存在“日内动量”与“隔夜反转”的黄金律：即日内涨跌幅因子 M0（前15天的日内收益率加总） 呈现显著的动量效应，因子越大的组合能够带来更大的收益， 而隔夜涨跌幅因子 M1 （前十五日隔夜收益率加总）则呈现反转效应，因子值越小的组合超额收益更加明显。
#
# 3）将两个因子按照打分法等权结合得到的黄金律因子构建行业轮动组合，可以发现顶部组合年化收益约有7%的提升，同时最大回撤情况也有明显改善。 对比传统的动量因子夏普比率0.68，黄金律因子的夏普比率可达0.87。
#
#
#
# 研究耗时：
# 1）数据准备部分：大约需要20min，数据采集部分需要注意，目前平台暂无提供直接的API获取行业数据，以下的内容都是调用了聚源数据库进行的操作，具体数据源可以参考这个链接
#       https://www.joinquant.com/help/data/data?name=jy#nodeId=17
# 2）策略构建部分：大约需要30min，主要对模型进行调整。

import pandas as pd
import numpy as np
from  datetime import datetime,timedelta
import pickle
from matplotlib import pyplot as plt
import matplotlib.dates as mdate
import seaborn as sns
from jqdata import jy

sns.set_style("whitegrid", {"axes.facecolor": ".99"})
sns.set_context("notebook",font_scale=1.2, rc={"lines.linewidth": 1.5})
plt.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family']='sans-serif'


# 2.导入数据

# 目前平台暂无提供直接的API获取行业数据，以下的内容都是调用了聚源数据库进行的操作，具体数据源可以参考这个链接
# https://www.joinquant.com/help/data/data?name=jy#nodeId=17， 我们利用get_SW_index这个函数提取每一个申万二级行业指数的数据，利用index_list确定提取指标，如收盘价‘ClosePrice’等，其中codelist为申万二级指数的代码汇总，我们可以利用get_SW_index函数提取出交易数据
#
# 设置开始回测的开始时间和结束时间，将index_list设置为收盘价与开盘价，利用get_SW_index分别提取出所有申万二级指数的收盘价和开盘价

def get_SW_index(SW_index,start_date,end_date,index_list = ['ClosePrice']):
    jydf = jy.run_query(query(jy.SecuMain).filter(jy.SecuMain.SecuCode==str(SW_index)))
    link=jydf[jydf.SecuCode==str(SW_index)]
    rows=jydf[jydf.SecuCode==str(SW_index)].index.tolist()
    result=link['InnerCode'][rows]
    df = jy.run_query(query(jy.QT_SYWGIndexQuote).filter(jy.QT_SYWGIndexQuote.InnerCode==str(result[0]),                                                   jy.QT_SYWGIndexQuote.TradingDay>=start_date,                                                         jy.QT_SYWGIndexQuote.TradingDay<=end_date
                                                        ))
    df.index = df['TradingDay']
    df = df[index_list]
    df.columns = [SW_index]
    return df

codelist = [801010,801020,801030,801040,801050,801080,801110,801120,801130,801140,801150,801160,801170,801180,801200,801210,801230,801710,801720,801730,801740,801750,801760,801770,801780,801790,801880,801890]

start_date=datetime(2005,12,1)
end_date=datetime(2017,12,31)

price_close = pd.DataFrame()
for i in range(0,len(codelist)):
    df = get_SW_index(SW_index = codelist[i],start_date=start_date,end_date=end_date,index_list = ['ClosePrice'])
    price_close = pd.concat([price_close,df],axis=1)

price_open = pd.DataFrame()
for i in range(0,len(codelist)):
    df = get_SW_index(SW_index = codelist[i],start_date=start_date,end_date=end_date,index_list = ['OpenPrice'])
    price_open = pd.concat([price_open,df],axis=1)


# 3. 黄金律：日内动量+隔夜反转

# 不同的交易者群体，会有不同的行为模式。在交易日内的不同时段，交易者的成分可能存在系统性差异， 因而会导向不同的市场行为
# 特征，最终形成各式各样的日内模式（intraday patterns）。按照这个思路，为了研究动量效应的日内精细规律， 报告将行业指数的每日收益率拆解为日内收益率（今收/今开-1） 和隔夜收益率（今开/昨收-1）。
# 在本篇报告中，我们将过去 15 个交易日的日内收益率加总，命名为日内涨跌幅因子 M0；将过去 15 个交易日的隔夜收益率加总，称
# 为隔夜涨跌幅因子 M1。

# 首先我们设置回测的一些参数，即开始回测时间和年份

start='2006'
end='2017'
u1=[23,17,11,5,0]
u2=[27,22,16,10,4]


# 下面的def_alpha函数