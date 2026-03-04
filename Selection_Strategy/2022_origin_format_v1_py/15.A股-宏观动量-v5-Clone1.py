#!/usr/bin/env python
# coding: utf-8

from jqdata import *
import numpy as np
import pandas as pd
import datetime as dt
from six import StringIO
from dateutil.parser import parse
import cPickle as pickle
import seaborn as sns
import matplotlib as mpl
import os
import statsmodels.api as sm
import scipy
import talib as tl


mpl.rcParams['font.family']='serif'
mpl.rcParams['axes.unicode_minus']=False # 处理负号

load_data={}

path = '/home/jquser/Macro'

class backtest_result():
    def __init__(self,data):
        self.data = data
        self.total_returns = data.iloc[-1]-1
        self.annualized_returns = data.iloc[-1]**(12./len(data))-1
        self.annualized_volatility = data.pct_change().std()*(12.**0.5)
    def Max_Drawback(self):
        net_value=self.data
        max_value=0
        df_tmp=pd.DataFrame(net_value)
        df_tmp.columns=['value']
        for j in range(0,len(net_value),1):
            max_value=max(max_value,df_tmp.ix[j,'value'])
            df_tmp.ix[j,'drawback']=1-df_tmp.ix[j,'value']/max_value
            drawback=df_tmp['drawback'].max()
        return drawback
    def Sharpe(self):
        net_value=self.data
        bench_pct=0.03
        df_tmp=pd.DataFrame(net_value)
        df_tmp.columns=['value']
        df_tmp['pct']=df_tmp['value'].pct_change()
        annual_pct = df_tmp.ix[-1,'value']**(12./len(df_tmp))-1
        sharpe = (annual_pct-bench_pct)/(df_tmp['pct'].std()*12**0.5)
        return sharpe
    def Calmar(self):
        clamar = self.annualized_returns/self.Max_Drawback()
        return clamar


# PMI择时
body=read_file(path+'/PMI组合.xls')
df_boom=pd.read_excel(StringIO(body))
print df_boom.columns
col =u'PMI'
df_boom=df_boom.set_index(u'日期')
df_boom.plot(figsize=(15,6),title='PMI')
n=3
df_boom['position']=(pd.rolling_mean(df_boom[col],n).shift(1)>pd.rolling_mean(df_boom[col],n).shift(2))*1.
prices = get_price('000300.XSHG',start_date='2006-01-01',end_date='2018-11-30',fields='close')['close']
prices_M = prices.resample('M',how='last')
rate_riskfree = 0
df_pct=pd.DataFrame()
df_pct['pct']=prices_M.pct_change()
df_pct['position']=df_boom['position']
df_pct['net_value'] =(df_pct['pct']+1).cumprod()
df_pct['net_value_timing'] = (df_pct['pct']*df_pct['position']+rate_riskfree*(1-df_pct['position'])+1).cumprod()
df_pct[['net_value','net_value_timing']].plot(figsize=(15,6),title='PMI择时')


# 利率择时
body=read_file(path+'/SHIBOR数据.xls')
df_interest=pd.read_excel(StringIO(body))
col = u'SHIBOR:1个月'
df_interest=df_interest.set_index(u'日期')

df_interest.iloc[:,1:2].plot(figsize=(15,6),title='SHIBOR')
df_interest=df_interest[[col]]
upperband,middleband,lowerband = (tl.BBANDS(df_interest[col].values, timeperiod=12, nbdevup=1.8, nbdevdn=1.8))
# print df_1

df_interest['BBAND_upper']=upperband
df_interest['BBAND_middle']=middleband
df_interest['BBAND_lower']=lowerband

pre_position = 0
for date in df_interest.index:
    if df_interest.loc[date,col]>df_interest.loc[date,'BBAND_middle']:
        df_interest.loc[date,'position']=0
    elif df_interest.loc[date,col]<df_interest.loc[date,'BBAND_lower']:
        df_interest.loc[date,'position']=1.0
    else:
        df_interest.loc[date,'position']=pre_position
    pre_position=df_interest.loc[date,'position']
df_interest['position']=df_interest['position'].shift(1)

df_pct=pd.DataFrame()
prices = get_price('000300.XSHG',start_date='2005-01-01',end_date='2018-11-30',fields='close')['close']
df_pct['pct']=prices.pct_change()

rate_riskfree = 0
df_pct = pd.concat([df_pct,df_interest],axis=1)['2006-01-01':'2018-11-30'].dropna()
df_pct['net_value'] =(df_pct['pct']+1).cumprod()
df_pct['net_value_timing'] = (df_pct['pct']*df_pct['position']+rate_riskfree*(1-df_pct['position'])+1).cumprod()
df_pct[['net_value','net_value_timing']].plot(figsize=(15,6),title='SHIBOR:1M择时')
# df_pct
# df_1['2007-01-01':'2018-11-30'].iloc[:1000].plot(figsize=(15,10))
# print backtest_result(df_pct['net_value_timing']).Sharpe()


# 获取国债期限利差数据
body=read_file(path+'/国债到期收益率.xls')
df_gz=pd.read_excel(StringIO(body))
df_gz.set_index(u'日期',inplace=True)
print df_gz.columns
df_gz=df_gz.fillna(method='ffill')
term_spread_gz = df_gz[u'中债国债到期收益率:10年']-df_gz[u'中债国债到期收益率:1个月']
term_spread_gz_diff = term_spread_gz.diff(21)
term_spread_gz=pd.rolling_mean(term_spread_gz,1)
term_spread_gz.plot(figsize=(15,6),title='10年-1年国债期限利差')


# 期限利差择时
df_termspread=pd.DataFrame()
col='termspread'
df_termspread=term_spread_gz.to_frame('termspread')
upperband,middleband,lowerband = (tl.BBANDS(df_termspread[col].values, timeperiod=25, nbdevup=1.8, nbdevdn=1.8))
# print df_termspread

df_termspread['BBAND_upper']=upperband
df_termspread['BBAND_middle']=middleband
df_termspread['BBAND_lower']=lowerband
# df_termspread
df_termspread.head()
pre_position = 0
for date in df_termspread.index:
    if df_termspread.loc[date,col]<df_termspread.loc[date,'BBAND_middle']:
        df_termspread.loc[date,'position']=0
    elif df_termspread.loc[date,col]>df_termspread.loc[date,'BBAND_upper']:
        df_termspread.loc[date,'position']=1.0
    else:
        df_termspread.loc[date,'position']=pre_position
    pre_position=df_termspread.loc[date,'position']
df_termspread['position']=df_termspread['position'].shift(1)
df_termspread.head().append(df_termspread.tail())

df_pct=pd.DataFrame()
prices = get_price('000300.XSHG',start_date='2005-01-01',end_date='2018-11-30',fields='close')['close']
df_pct['pct']=prices.pct_change()

rate_riskfree = 0
df_pct = pd.concat([df_pct,df_termspread],axis=1)['2007-01-01':'2018-11-30'].dropna()
df_pct['net_value'] =(df_pct['pct']+1).cumprod()
df_pct['net_value_timing'] = (df_pct['pct']*df_pct['position']+rate_riskfree*(1-df_pct['position'])+1).cumprod()
df_pct[['net_value','net_value_timing']].plot(figsize=(15,6),title='国债期限利差择时')


# 获取信用利差数据
body=read_file(path+'/企业债到期收益率(AAA).xls')
df_qyz=pd.read_excel(StringIO(body))
df_qyz.set_index(u'日期',inplace=True)
df_qyz=df_qyz.fillna(method='ffill')

credit_spread = df_qyz[u'中债企业债到期收益率(AAA):1个月']-df_gz[u'中债国债到期收益率:1个月']

credit_spread=pd.rolling_mean(credit_spread,1)
credit_spread['2006-01-01':].plot(figsize=(15,6),title='AAA企业债信用利差:1个月')


# 信用利差择时
df_creditspread=pd.DataFrame()
col='creditspread'
df_creditspread=credit_spread.to_frame('creditspread')
upperband,middleband,lowerband = (tl.BBANDS(df_creditspread[col].values, timeperiod=