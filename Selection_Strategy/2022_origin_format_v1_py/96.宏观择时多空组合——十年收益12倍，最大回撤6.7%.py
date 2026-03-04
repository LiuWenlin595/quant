#!/usr/bin/env python
# coding: utf-8

from jqdata import *
import numpy as np
import pandas as pd
import datetime as dt
from six import StringIO
from dateutil.parser import parse
import pickle
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt
import os
import statsmodels.api as sm
import scipy
import talib as tl
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

mpl.rcParams['font.family']='serif'
mpl.rcParams['axes.unicode_minus']=False # 处理负号


def get_profit(data,start_date,end_date,rate_riskfree=0):
    '''
    data:计算好的带有position的数据，决定每月的买入卖出决策
    '''
    df_pct=pd.DataFrame()
    prices = get_price('000300.XSHG',start_date=start_date,end_date=end_date,fields='close')['close']
    df_pct['pct']=prices.pct_change()
    rate_riskfree = 0
    df_pct = pd.concat([df_pct,data],axis=1)[start_date:end_date].dropna()
    df_pct['net_value'] =(df_pct['pct']+1).cumprod()
    df_pct['net_value_timing'] = (df_pct['pct']*df_pct['position']+rate_riskfree*(1-df_pct['position'])+1).cumprod()
    df_pct[['net_value','net_value_timing']].plot(figsize=(15,6))
    return df_pct


def get_month_list(start_date, end_date):
    sy = int(start_date[:4])
    ey = int(end_date[:4])
    sm = int(start_date[5:7])
    em = int(end_date[5:7])
    l = []
    for y in range(sy, ey + 1):
        if y == sy:
            for i in range(sm, 13):
                if i < 10:
                    s = str(y) + '-' + '0' + str(i)
                    l.append(s)
                else:
                    s = str(y) + '-' + str(i)
                    l.append(s)

        elif y == ey:
            for i in range(1, em + 1):
                if i < 10:
                    s = str(y) + '-' + '0' + str(i)
                    l.append(s)
                else:
                    s = str(y) + '-' + str(i)
                    l.append(s)
        else:
            for i in range(1, 13):
                if i < 10:
                    s = str(y) + '-' + '0' + str(i)
                    l.append(s)
                else:
                    s = str(y) + '-' + str(i)
                    l.append(s)
    return l

#获取label值
def get_profit_monthly(start_date,end_date,cut_list=[-0.00,0.00],label=True,rate_riskfree=0):
    '''
    data:position数据，1列，前期计算出择时position
    start_date:datetime or str, 开始时间，此时间要和data时间有交集，通常是对应
    end_date:结束时间
    rate_riskfree:无风险利率
    cut_list:分类切点，注意二分类和多分类时后续算法的区别
    label:决定输出的是分类结果还是连续结果
    '''
    df_pct=pd.DataFrame()
    prices = get_price('000300.XSHG',start_date=start_date,end_date=end_date,fields='close')['close']
    prices_M = prices.resample('M',how='last')
    month_list = get_month_list(start_date,end_date)
    prices_M.index = month_list
    df_pct['pct']=prices_M.pct_change().dropna()
    def fun(x):
        if x > cut_list[-1]:
            y = 1
        elif x < cut_list[0]:
            y = -1
        else:
            y = 0
        return y
    if label:
        df_pct = df_pct.applymap(lambda x: fun(x))
    return df_pct

#计算最大回撤
def find_max_drawdown(returns):
    # 定义最大回撤的变量
    result = 0
    # 记录最高的回报率点
    historical_return = 0
    # 遍历所有日期
    for i in range(len(returns)):
        # 最高回报率记录
        historical_return = max(historical_return, returns[i])
        # 最大回撤记录
        drawdown = 1 - (returns[i]) / (historical_return)
        # 记录最大回撤
        result = max(drawdown, result)
    # 返回最大回撤值
    return result

def get_profit_res(data,start_date,end_date,rate_riskfree=0,plot=True):
    '''
    data:position数据，1列，前期计算出择时position,index必须是日期
    start_date:datetime or str, 开始时间，此时间要和data时间有交集，通常是对应
    end_date:结束时间
    rate_riskfree:无风险利率
    '''
    df_pct=pd.DataFrame()
    prices = get_price('000300.XSHG',start_date=start_date,end_date=end_date,fields='close')['close']
    prices_M = prices.resample('M',how='last')
    month_list = get_month_list(start_date,end_date)
    prices_M.index = month_list
    df_pct['pct']=prices_M.pct_change()
    df_pct['pct_position'] = df_pct['pct']
    df_pct['pct_position'][df_pct['pct_position']>0] = 1
    df_pct['pct_position'][df_pct['pct_position']<0] = 0
    rate_riskfree = 0
    df_pct = pd.concat([df_pct,data],axis=1).loc[month_list].dropna()
    #计算胜率
    win_rate = df_pct['position'] * df_pct['pct_position']
    win_rate = win_rate.sum()/df_pct['position'].sum()
    df_pct['net_value'] =(df_pct['pct']+1).cumprod()
    df_pct['net_value_timing'] = (df_pct['pct']*df_pct['position']+rate_riskfree*(1-df_pct['position'])+1).cumprod()
    if plot == True:
        f = plt.figure(figsize=(15,6))
        ax = f.add_subplot(1,1,1)
        ax.plot(df_pct[['net_value','net_value_timing']])
        ax.set_xticks(month_list[::12])
    profit_res = df_pct.ix[-1,['net_value','net_value_timing']].to_frame().stack().unstack(0)
    profit_res['win_rate'] = win_rate
    profit_res['profit_ratio'] = profit_res['net_value_timing'] / profit_res['net_value']
    return profit_res


def get_profit_res_for_sell(data,start_date,end_date,rate_riskfree=0,plot=True):
    '''
    data:position数据，1列，前期计算出择时position
    start_date:datetime or str, 开始时间，此时间要和data时间有交集，通常是对应
    end_date:结束时间
    rate_riskfree:无风险利率
    '''
    df_pct=pd.DataFrame()
    prices = get_price('000300.XSHG',start_date=start_date,end_date=end_date,fields='close')['close']
    prices_M = prices.resample('M',how='last')
    month_list = get_month_list(start_date,end_date)
    prices_M.index = month_list
    df_pct['pct']=prices_M.pct_change()
    df_pct['pct_position'] = df_pct['pct']
    df_pct['pct_position'][df_pct['pct_position']>0]= 0
    df_pct['pct_position'][df_pct['pct_position']<0] = 1 #空头
    rate_riskfree = 0
    df_pct = pd.concat([df_pct,data],axis=1).loc[month_list].dropna()
    #计算胜率
    win_rate = df_pct['position'] * df_pct['pct_position']
    win_rate = win_rate.sum()/df_pct['position'].sum()
    df_pct['net_value'] =(df_pct['pct']+1).cumprod()
    df_pct['timing_for_sell'] = (-df_pct['pct']*df_pct['position']+rate_riskfree*(1-df_pct['position'])+1).cumprod()
    df_pct['net_value_timing'] = (df_pct['pct']*df_pct['position']+rate_riskfree*(1-df_pct['position'])+1).cumprod()
    if plot == True:
        f = plt.figure(figsize=(15,6))
        ax = f.add_subplot(1,1,1)
        ax.plot(df_pct[['net_value','timing_for_sell']])
        ax.set_xticks(month_list[::12])
    profit_res = df_pct.ix[-1,['net_value','timing_for_sell']].to_frame().stack().unstack(0)
    profit_res['win_rate'] = win_rate
    profit_res['profit_ratio'] = profit_res['timing_for_sell'] / profit_res['net_value']
    return profit_res


def get_rolling_positon(data,n,delay=2,how='up