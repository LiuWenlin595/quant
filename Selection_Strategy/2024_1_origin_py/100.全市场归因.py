#!/usr/bin/env python
# coding: utf-8

# (已移除或注释) # In[34]:


from datetime import datetime, timedelta
import datetime

from jqdata import *
from jqfactor import *

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns

import math
import statsmodels.api as sm
from statsmodels import regression
from scipy.optimize import minimize
from scipy import stats
import scipy.stats as st

import warnings  
warnings.filterwarnings('ignore') 

mpl.rcParams['font.sans-serif'] = ['SimHei']    
mpl.rcParams['axes.unicode_minus'] = False     
sns.set_style({'font.sans-serif':['simhei', 'Arial']})
pd.set_option('display.max_rows', 200)
pd.set_option('display.max_columns', 200)
pd.set_option('display.width', 200)
plt.style.use('ggplot')


# # 1.函数构造

# ## 1.1获取指定频率交易日数据

# (已移除或注释) # In[35]:


#获取交易日列表，返回DatetimeIndex对象
def get_tradeday_list(start,end,frequency=None,count=None):
    if count != None:
        df = get_price('000001.XSHG',end_date=end,count=count)#有计数n，返回后n天
    else:
        df = get_price('000001.XSHG',start_date=start,end_date=end)#否则返回始末日期之间
    if frequency == None or frequency =='D':
        return df.index
    else:
        df['year-month'] = [str(i)[0:7] for i in df.index]#返回年月
        if frequency == 'M':
            return df.drop_duplicates('year-month').index#根据年月去重
        elif frequency == 'Q':
            df['month'] = [str(i)[5:7] for i in df.index]
            df = df[(df['month']=='01') | (df['month']=='04')                    | (df['month']=='07') | (df['month']=='10') ]#返回1、4、7、10月
            return df.drop_duplicates('year-month').index#去重
        elif frequency =='H-Y':
            df['month'] = [str(i)[5:7] for i in df.index]
            df = df[(df['month']=='01') | (df['month']=='06')]#返回1、6月
            return df.drop_duplicates('year-month').index#去重


# ## 1.2 筛选股票池

# (已移除或注释) # In[36]:


#返回指定交易日下一个交易日
def ShiftTradingDay(date,shift):
    # 获取所有的交易日(从2005年开始),返回一个包含所有交易日的 list,元素值为 datetime.date 类型.
    tradingday = get_all_trade_days()
    # 得到date之后shift天那一天在列表中的行标号 返回一个数
    date = datetime.date(int(str(date)[:4]),int(str(date)[5:7]),int(str(date)[8:10]))
    shiftday_index = list(tradingday).index(date)+shift
    # 根据行号返回该日日期 为datetime.date类型
    return tradingday[shiftday_index] 

#进行新股、St股过滤，返回筛选后的股票
#！！！不能过滤停牌股票
def filter_stock(stockList,date,days=21*3,limit=0):
    #去除上市距beginDate不足3个月的股票
    def delect_stop(stocks,beginDate,n=days):
        stockList=[]
        beginDate = datetime.datetime.strptime(beginDate, "%Y-%m-%d")
        for stock in stocks:
            start_date=get_security_info(stock).start_date
            if start_date<(beginDate-datetime.timedelta(days=n)).date():
                stockList.append(stock)
        return stockList
    
    #剔除ST股
    st_data=get_extras('is_st',stockList, count = 1,end_date=date)
    stockList = [stock for stock in stockList if not st_data[stock][0]]
    
    # 判断当天是否全天停牌
    is_susp = get_price(stockList,end_date=date, count=1,fields='paused'                        ,panel=False).set_index('code')[['paused']]
    stockList = is_susp[is_susp==1].index.tolist()
    
    #新股及退市股票
    stockList=delect_stop(stockList,date)
    
    #剔除开盘涨跌停股票
    if limit == 1:
        #如果需要收盘涨跌停可以改字段即可
        df = get_price(stockList,end_date=date,                       fields=['open','high_limit','low_limit'],count=1).iloc[:,0,:]
        df['h_limit']=(df['open']==df['high_limit'])
        df['l_limit']=(df['open']==df['low_limit'])
        stockList = [df.index[i] for i in range(len(df)) if not                     (df.h_limit[i] or df.l_limit[i])] #过滤涨跌停股票
    return stockList


# ## 1.3 行业标记

# (已移除或注释) # In[37]:


#为股票池添加行业标记,return df格式 ,为中性化函数的子函数   
def get_industry_exposure1(stock_list,date):
    stock_list = list(stock_list)
    df = pd.DataFrame(index=get_industries(name='sw_l1').index, columns=stock_list)
    s = get_industry(security=stock_list, date=date)
    ind_dict = {}#创建一个每个股票所在行业的字典（'sw_l1'标准）
    for idx,stock in enumerate(stock_list):
        #自从2019年后存在找不到'sw_l1'的股票情况
        if 'sw_l1' in s[stock].keys() :
            ind_dict[stock] = s[stock]['sw_l1']['industry_code']
        else:
            # 以相邻股票行业作为自己的行业
            ind_dict[stock] = ind_dict[stock_list[idx-1]]
    
    for stock in stock_list:
        df.loc[ind_dict[stock],stock] = 1

    return df.fillna(0)


# ## 1.4IC统计相关函数

# (已移除或注释) # In[38]:


def dict_to_df(dct,index,name=None):
    df = pd.DataFrame(dct,index=index).T
    df.index = pd.to_datetime(df.index)
    if name:
        df.index.name = name
    return df

def evaluation(ic_df, beta_df, t_df):
    '''
    ic_df: df
    beta_df: df
    t_df: df
    return:
    '''
    eval_dict = {}
    # ----ic----
    ic_mean = []
    ic_002 = []
    ir = []
    # ---beta----
    beta_mean = []
    t_test = []
    p_value = []
    # ----t----
    t_mean = []
    t_2 = []

    for factor in ic_df.columns:
        # 计算ic均值
        mean_temp = np.around(ic_df[factor].mean(), 4)
        # ic绝对值大于0.02的比例
        ratio_002 = np.around(np.sum(ic_df[factor].abs() > 0.02)                              / len(ic_df.index) * 100, 2)
        # IR
        IR = np.around(mean_temp / ic_df[factor].std(), 4)

        # 添加进列表
        ic_mean.append(mean_temp)
        ic_002.append(str(ratio_002) + '%')
        ir.append(IR)
    print("ic表处理完毕!")
    
    for factor in beta_df.columns:
        # 因子收益率均值
        mean_temp = np.around(beta_df[factor].mean(), 4)
        # t检验
        t, p = np.around(st.ttest_1samp((beta_df[factor]), 0), 4)
        # 添加进列表
        beta_mean.append(mean_temp)
        t_test.append(t)
        p_value.append(p)
    print("beta表处理完毕!")
    
    for factor in t_df.columns:
        # t值绝对值的均值
        mean_temp = np.around(t_df[factor].abs().mean(), 4)
        # 大于2的占比
        ratio_2 = np.around(np.sum(t_df[factor].abs() > 2) / len(t_df.index) * 100, 2)

        # 添加列表
        t_mean.append(mean_temp)
        t_2.append(str(ratio_2) + '%')
    print("t值表处理完毕!")
    
    # 添加进字典
    eval_dict['IC均值'] = ic_mean
    eval_dict['|IC|>0.02'] = ic_002
    eval_dict['IR'] = ir
    eval_dict['因子收益率均值'] = beta_mean
    eval_dict['因子收益率t检验'] = t_test
    eval_dict['p值'] = p_value
    eval_dict['|t|均值'] = t_mean
    eval_dict['|t|大于2的占比'] = t_2
    
    # 字典转df
    eval_df = pd.DataFrame(eval_dict,index=t_df.columns)
    eval_df['score'] = eval_df.apply(score,axis=1)
    eval_df = eval_df.sort_values('score',ascending=False)#降序
    
    return eval_df

def score(series):
    """
    打分函数
    """
    score = 0
    if abs(series['IC均值'])>0.02:
        score +=1
    if abs(series['因子收益率t检验'])> 1.8:#存在问题
        score +=1
    if abs(series['IR'])>0.3:
        score +=1
    if series['|t|均值']>2:
        score +=1
    return score


# ## 1.5相关性画图函数

# (已移除或注释) # In[39]:


def plot_heat(ic_df,eval_df):
    # 截取表现好的因子
    eval_df = eval_df[eval_df['score']>=2]
    ic_df = ic_df.loc[:,eval_df.index]
    corr = np.around(ic_df.corr('spearman'),2)
    fig,ax = plt.subplots(figsize=(20,10))
    sns.heatmap(corr.abs(),annot=True,cmap='RdPu',ax=ax)
    return corr


# # 2 数据获取

# ## 2.1初始设置

# (已移除或注释) # In[40]:


#设置统计数据区间
index = '000985.XSHG' #设置股票池，和对比基准，这里是中证500
#stocks_list=list(get_all_securities(['stock']).index)

#设置统计起止日期
date_start = '2023-07-08'
date_end   = '2023-07-14'

#设置调仓频率
trade_freq = 'day' #month每个自然月；day每个交易日；输入任意数字如 5，则为5日调仓 

#获取调仓时间列表
if trade_freq == 'month':  
    #获取交易日列表，每月首个交易日
    date_list = get_tradeday_list(start=date_start,end=date_end,frequency='M',count=None) #自然月的第一天
elif trade_freq == 'day': 
    date_list = get_tradeday_list(start=date_start,end=date_end,count=None)#获取回测日期间的所有交易日
else:
    date_day_list = get_tradeday_list(start=date_start,end=date_end,count=None)#获取回测日期间的所有交易日
    date_list = [date_day_list[i]