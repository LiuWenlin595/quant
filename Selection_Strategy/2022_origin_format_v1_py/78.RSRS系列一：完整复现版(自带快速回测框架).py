#!/usr/bin/env python
# coding: utf-8

from jqdata import jy
from jqdata import *
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from scipy import stats
import warnings 
warnings.filterwarnings('ignore')


data_panel = get_price('000300.XSHG',start_date = '2003-01-01', end_date = '2019-07-04',fields = ['close','open','high','low','volume'])
data_panel = data_panel.dropna()


data_panel['close'].plot()


#回撤函数
def max_drawdown(pnl):
    pnl = pnl[~np.isnan(pnl)]
    high = pnl[0]
    low = high
    max_draw = 0
    for i in range(len(pnl)-1):
        if pnl[i+1]>high:
            high = pnl[i+1]
            low = high
        elif pnl[i+1]<low:
            low = pnl[i+1]
            if max_draw< 1-low/high:
                max_draw = 1 - low/high
    return max_draw

#夏普函数
def sharp_ratio(pnl,r=0.03):
    pnl = pnl[~np.isnan(pnl)]
    #print(pnl)
    return_rate_year = (pnl[-1]/pnl[0])**(250/len(pnl))-1
    std_year = np.std(np.diff(pnl)/pnl[:-1]-1)*np.sqrt(250)
    return (return_rate_year-r)/std_year


#均线策略
data_test = data_panel.copy()
data_test['Ma_10'] = data_test['close'].rolling(10).mean()
data_test['Ma_20'] = data_test['close'].rolling(20).mean()
data_test = data_test.dropna()

OPEN = data_test.open.values
CLOSE = data_test.close.values
Indexs = data_test.index
Ma_10 = data_test.Ma_10.values
Ma_20 = data_test.Ma_20.values

buyfee = 0.0013
sellfee = 0.0013

pnl = pd.Series(index = Indexs)
position = 0

for idx,time_stamp in enumerate(Indexs):
    if idx<=1:
        pnl.iloc[idx]=1
        continue
    
    
    if Ma_20[idx-1]<=CLOSE[idx-1]:
        if position==0:
            position = pnl.iloc[idx-1]/OPEN[idx]/(1+buyfee)
            pnl.iloc[idx] = position * CLOSE[idx]
        else:
            pnl.iloc[idx] = position * CLOSE[idx]
    else:
        if position>0:
            pnl.iloc[idx] = position* OPEN[idx]*(1-sellfee)
            position = 0
        else:
            pnl.iloc[idx]=pnl.iloc[idx-1]

plt.figure(figsize = (20,10))
pnl.plot(label = '均线策略')
(data_test['close'].loc[pnl.index]/(data_test['close'].loc[pnl.index][0])).plot(label = 'hs300')
plt.legend()
plt.grid()


#布林带策略
data_test = data_panel.copy()
data_test['Std_14'] = data_test['close'].rolling(14).std()
data_test['Ma_14'] = data_test['close'].rolling(14).mean()

data_test = data_test.dropna()

OPEN = data_test.open.values
CLOSE = data_test.close.values
Indexs = data_test.index
Ma_14 = data_test.Ma_14.values
Std_14 = data_test.Std_14.values

#费率+滑点
buyfee = 0.0013
sellfee = 0.0013

pnl = np.full(len(Indexs), np.nan)
position = 0

for idx,time_stamp in enumerate(Indexs):
    if idx<=1:
        pnl[idx]=1
        continue
    
    #买入条件
    if CLOSE[idx-1]-Ma_14[idx-1]>=Std_14[idx-1]*2:
        if position==0:
            position = pnl[idx-1]/OPEN[idx]/(1+buyfee)
            pnl[idx] = position * CLOSE[idx]
        else:
            pnl[idx] = position * CLOSE[idx]
    #卖出条件
    elif CLOSE[idx-1]-Ma_14[idx-1]<=-Std_14[idx-1]*2:
        if position>0:
            pnl[idx] = position* OPEN[idx]*(1-sellfee)
            position = 0
        else:
            pnl[idx]=pnl[idx-1]
    else:
        if position>0:
            pnl[idx] = position* CLOSE[idx]
        else:
            pnl[idx]=pnl[idx-1]

pnl = pnl[~np.isnan(pnl)]
    
plt.figure(figsize = (20,10))
plot(pnl,label = '布林带策略')
plot(CLOSE[-len(pnl):]/CLOSE[-(len(pnl))],label='hs300')
plt.legend()
plt.grid()


#无标准分与标准分分布和走势
#无标准化斜率
N = 18
data_test =data_panel.copy()
data_test = data_test.dropna()

Indexs = data_test.index
High = data_test.high.values
Low = data_test.low.values

slope = np.full(len(Indexs), np.nan)

for i in range(len(data_test)):
    if i<N:
        continue
    slope[i] = np.polyfit(x = Low[(i+1-N):(i+1)],y=High[(i+1-N):(i+1)],deg=1)[0]

slope = slope[~np.isnan(slope)]


#画直方图观察分布
plt.figure(figsize =(10,4))
plt.hist(slope, bins=100)  # arguments are passed to np.histogram
plt.title("slope without std")
plt.show()


#计算相关统计量
print("mean:%.4f" % np.mean(slope))
print("std:%.4f" % np.std(slope))
print("skew:%.4f" % stats.skew(slope)) 
print("kurtosis:%.4f" % stats.kurtosis(slope))


#观察各时期的均值变化
plt.figure(figsize = (8,4))
slope = pd.Series(slope,index = Indexs[-len(slope):])
slope.rolling(250).mean().plot()
plt.grid()


#标准化斜率
M = 600
slope_std = np.full(len(slope), np.nan)

for i in range(len(slope)):
    if i<M:
        continue
    slope_std[i] = (slope[i] - np.mean(slope[(i+1-M):(i+1)]))/np.std(slope[(i+1-M):(i+1)])
slope_std = slope_std[~np.isnan(slope_std)]


#画直方图观察分布
plt.figure(figsize = (10,4))
plt.hist(slope_std, bins=100)  # arguments are passed to np.histogram
plt.title("slope with std")
plt.show()


#计算相关统计量
print("mean:%.4f" % np.mean(slope_std))
print("std:%.4f" % np.std(slope_std))
print("skew:%.4f" % stats.skew(slope_std)) 
print("kurtosis:%.4f" % stats.kurtosis(slope_std))


#观察各时期的均值变化
plt.figure(figsize = (8,4))
slope_std = pd.Series(slope_std,index = Indexs[-len(slope_std):])
slope.rolling(250).mean().plot()
plt.grid()


#无标准分策略与标准分策略比较
#无标准化斜率策略

#数据初始化
data_test = data_panel.copy()
data_test = data_test.dropna()
data_test['slope'] = slope
data_test['slope_std'] = slope_std

data_test = data_test.dropna()

OPEN = data_test.open.values
CLOSE = data_test.close.values
Indexs = data_test.index
Slope = data_test.slope
Slope_std = data_test.slope_std

#策略初始化
buyfee = 0.0013
sellfee = 0.0013

pnl = np.full(len(Indexs), np.nan)
position = 0

for idx,time_stamp in enumerate(Indexs):
    if idx<=1:
        pnl[idx]=1
        continue
    
    ##定义买入条件
    if Slope[idx-1]>1:
        if position==0:
            position = pnl[idx-1]/OPEN[idx]/(1+buyfee)
            pnl[idx] = position * CLOSE[idx]
        else:
            pnl[idx] = position * CLOSE[idx]
    ##定义卖出条件
    elif Slope[idx-1]<0.8:
        if position>0:
            pnl[idx] = position* OPEN[idx]*(1-sellfee)
            position = 0
        else:
            pnl[idx]=pnl[idx-1]
    else:
        if position>0:
            pnl[idx] = position* CLOSE[idx]
        else:
            pnl[idx]=pnl[idx-1]

pnl = pd.Series(pnl,index =Indexs)
pnl = pnl.dropna()
pnl_slope = pnl.copy()


#标准化斜率策略

#数据初始化
data_test = data_panel.copy()
data_test = data_test.dropna()
data_test['slope