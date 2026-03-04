#!/usr/bin/env python
# coding: utf-8

# 引言

# 研究目的
# 本文参考方正证券《A股“跳一跳”：隔夜跳空选股因子》，采用研报内的方法对隔夜跳空因子进行研究。根据研报分析，选股上隔夜涨跌幅既不呈现反转也不呈现动量，过大或者过小在后一月都具有负向收益，因此引入隔夜涨跌幅的绝对值来衡量这种隔夜跳空异动的现象。从技术形态上解释，涨跌幅的绝对值可以理解为跳空缺口，是K线图中常见的一种技术图形。俗话说“跳空缺口，逢缺必补”，古老技术分析的经验，和研究结论是一致的。从交易行为解释，跳空缺口的形成其实是短期激进的交易行为导致的。开盘价格异动，和集合竞价成交占比提高、换手率提升、股价抬高、成交量相对价格抢跑等特征一样，都反映了股市短期的股价操纵行为。 
# 
# 根据此结论，本文对研报里面的结果进行了分析，并对股票隔夜价格变动进行了研究，从其中提取出 alpha 因子，从而实现对股票未来收益的预测。

# 研究内容
# 本文的研究始于隔夜涨跌幅，该指标衡量今日开盘价与昨日收盘价之间的变化。总体来看，开盘价与收盘价是一天最为重要的两个时间截点，多空双方在这两个关键时点上的博弈最激烈，信息含量最大。按照这个思路，展开研究：
# 
# 1）我们取每个股票过去 10 个交易日的隔夜涨跌幅平均值来作为研究对象，为构建因子提供思路 
# 
# 2）构建了跳空因子，只考虑价格的绝对变动水平。通过分层回测、多空组合等多种方式分析因子的有效性。测试时段： 2016 年 6 月-2018 年 12 月（剔除成分股内上市未满6个月的股票）；样本空间： 全A股； 调仓方式： 在每个月底，将各股票按总得分排序，划分为五组， 分别持有至下个月月末；得分最高的组合为多头组合，得分最低的组合为空头组合
# 
# 3）常用因子相关性检验：市值、 动量和换手作为已知的有效常用因子，可能会对新挖掘的因子有一定的影响。 我们对其进行检验
# 
# 4） 因子变形：因子可能的一个变形是计算个股开盘涨跌幅与均值的距离替代与 0 的距离，这个变形考虑到受市场行情影响，股票可能会有系统性的高开或者低开的情况。并对变形后的因子进行测试
# 
# 5） 因子在指数上的表现：因子在沪深300和中证500的表现

# 研究结论
# 1）隔夜无论价格变动方向如何， 变动绝对值越大的个股在未来收益越不理想，按月换仓，持有变动值最大分组在回测区间平均年化收益为-25%。
# 
# 2）隔夜价格变动因子有着显著的区分作用，在全A股范围内多空净值曲线的年化均超过了20%，最大回撤控制在了7%以内，卡玛比超过3.
# 
# 3）随着回看时间的拉长，隔夜涨跌幅这种性质逐渐减弱， 因子的预测能力时间上衰减较快。回看期窗口为10天最优，小于10天噪声太大，偶然性太高，若回看窗口为60天，120天，则分组效果不明显。
# 
# 因子结果展示：
# ![11.png](attachment:11.png)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from jqdata import *
import math
import matplotlib.dates as mdate
from  datetime import datetime,timedelta
from scipy.stats import spearmanr


# 1.数据获取
# 股票池: 全A股
# 股票筛选：剔除上市 6 个月内的股票，每只股票视作一个样本，选取样本的区间在2016年6月到2018年12月

#去除上市距beginDate不足6个月的股票，剔除ST股，剔除停牌，退市等股票
def delect_stock(stocks,beginDate,n=180):
    #去除上市距beginDate不足6个月的股票
    stockList = []
    beginDate = datetime.strptime(beginDate, "%Y-%m-%d")
    for stock in stocks:
        start_date = get_security_info(stock).start_date
        if start_date < (beginDate-timedelta(days = n)).date():
            stockList.append(stock)
    #剔除ST股
    st_data = get_extras('is_st', stockList, count = 1, end_date=beginDate)
    stockList = [stock for stock in stockList if not st_data[stock][0]]
    return stockList
#获取数据，构建隔夜跳变百分比因子，选取30日的隔夜股价跳变百分比的平均值作为研究对象
start, end = '2016-06-01', '2018-12-29'
#选取沪深300作为股票池代表A股市场
stocks = np.array(get_index_stocks('000001.XSHG'))
stocks = delect_stock(list(stocks),start)
data = get_price(stocks, start_date=start, end_date=end, frequency='daily', fields=None, skip_paused=False, fq='pre')


# 提取数据后，首先我们选取每个股票过去 10 个交易日的隔夜涨跌幅平均值来作为研究对象。 

open = data.loc['open'].iloc[1:]
close = data.loc['close']
close_p = np.array(data.loc['close'].iloc[0:-1])
open_p = np.array(data.loc['open'].iloc[1:])
jump = pd.DataFrame(multiply(open_p,1/close_p) - 1,columns = open.columns,index = open.index)
#10日滑动平均.rolling(12).mean()
mv_jump = jump.rolling(10).mean().iloc[0:].fillna(0).iloc[10:]
print(mv_jump.head(5))


# 2.因子的描述
# 以2018年12月29日为例，下图给出的是10日（N=10）隔夜涨跌幅水平的分布直方图和描述性统计。

import math
#描述性统计
def calc(data):
    n = len(data)
    niu = 0.0
    niu2 = 0.0
    niu3 = 0.0
    for a in data:
        niu += a
        niu2 += a**2
        niu3 += a**3
    niu/= n   #这是求E(X)
    niu2 /= n #这是E(X^2)
    niu3 /= n #这是E(X^3)
    sigma = math.sqrt(niu2 - niu*niu) #这是D（X）的开方，标准差
    return [niu,sigma,niu3] #返回[E（X）,标准差，E（X^3）]

def calc_stat(data):
    median = data[len(data)//2] if len(data)%2==1 else "%.1f"%(0.5*(data[len(data)//2-1]+data[len(data)//2]))
    [niu,sigma,niu3] = calc(data)
    n = len(data)
    niu4 = 0.0
    for a in data:
        a -= niu
        niu4 += a ** 4
    niu4 /= n   
    skew = (niu3 - 3*niu*sigma**2 - niu**3)/(sigma**3)
    kurt =  niu4/(sigma**2)
    return [niu,sigma,skew,kurt,median] #返回了均值，标准差，偏度，峰度，中位数
#画出隔夜涨跌幅水平的分布直方图
tem_jump = list(mv_jump.iloc[-1])
plt.hist(tem_jump, bins= 50, normed= False, weights= None, cumulative= False, 
         bottom= None, histtype= 'bar', align= 'mid', orientation= 'vertical', rwidth= None, log= False, color= 'r', 
         label='直方图', stacked= False)
plt.show()
print('均值，标准差，偏度，峰度,中位数')
print(calc_stat(tem_jump))


# 无论是直观的从分布直方图观测还是根据统计数值来看，数据均值为负，且集中度较高，主要集中在-0.001附近。这说明从隔夜涨跌幅来看，当天A股市场股票普遍小幅低开。
# 忽略时间维度，我们将 2016年6月至2018年12月的隔夜涨跌幅水平做相同的统计，结果如下。数据均值依然为负，且集中度更高