#!/usr/bin/env python
# coding: utf-8

# In[1]:

from jqdata import *
import numpy as np
import pandas as pd


# In[2]:

end_date = '2022-04-12'
check_days = 15 # end_date之前的15个交易日
window = 252  # 此参数为创新高统计周期
gap = 60  # 此参数为创新高间隔，即间隔期内未突破前期新高，只在今天创下新高


# In[3]:

# 原 Jupyter Magic 命令转换 (%%time)
by_date = get_trade_days(end_date=end_date, count=window+check_days)[0]   
# 确保end_date之前的window+check_days个交易日已经上市，从而确保get_price取数的正确性
stock_list = get_all_securities(date=by_date).index.tolist()
#
new_high_list_dic={}
newhigh_percent = pd.Series()
#
prices = get_price(stock_list, end_date=end_date, frequency='daily', 
                   fields='close', count=window+check_days, panel=False
                  ).pivot(index='time', columns='code',values='close')
#
for i in range(check_days):
    check_date = prices.index[window+i].date()
    price = prices.iloc[i+1:window+i+1]
    s_result = price.apply(lambda x: np.argmax(x.values) == (len(x) -1) and np.argmax(x.values[:-1])<(len(x)-1-gap))
    new_high_list = s_result[s_result].index.tolist()
    newhigh_percent.loc[check_date] = 100*(len(new_high_list) / len(stock_list))
    new_high_list_dic[check_date]=new_high_list


# In[4]:

newhigh_percent.tail()


# In[5]:

new_high_list_dic[datetime.datetime.strptime(end_date,"%Y-%m-%d").date()]


# In[ ]: