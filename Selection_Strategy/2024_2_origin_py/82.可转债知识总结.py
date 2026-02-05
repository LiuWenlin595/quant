#!/usr/bin/env python
# coding: utf-8

# In[1]: (已注释)


from jqdata import *
import pandas as pd
import numpy as np
import datetime
from scipy import stats
warnings.filterwarnings("ignore")
from scipy.optimize import curve_fit
print('done')


# In[2]: (已注释)


# 季度时期调用函数(1个最新季度和13个过往季度<==确保能有12个sample)：
def season_selection(end_date):
    year = int(end_date[:4])
    if int(end_date[5]) > 0:
        month = int(end_date[5:7])
    else:
        month = int(end_date[6])

    # 确认最近的季度时间，取当前月份的前一个季度（例如2/3月份则取去年12月4季度的数据）
    month_dict = {3:4,6:1,9:2,12:3}
    for m in month_dict.keys():
        if month <= m:
            start_month = month_dict[m]
            break
    if start_month != 4:
        start_year = year
        start_season = str(year) + 'q' + str(start_month)
    else:
        start_year = year - 1
        start_season = str(start_year) + 'q' + str(start_month)
    
    # 取出过后的13个季度，合并到一起作为取出的季度
    sample = []
    while len(sample) < 13:
        if start_month > 1:
            start_month -= 1
            season = str(start_year) + 'q' + str(start_month)
            sample.append(season)
        
        else:
            start_month = 4
            start_year -= 1
            season = str(start_year) + 'q' + str(start_month)
            sample.append(season)

    return start_season, sample


# In[3]: (已注释)


# 转债成长因子（营业收入超额预期）：
def SUE_factoring(stock_list, end_date):
    # 取出过去14个季度的营业收入数据，计算最新季度数据对应过去数据的超预期准值（standardised）
    start_season, sample = season_selection(end_date)
    q = query(income.code,income.statDate,income.operating_revenue).filter(income.code.in_(stock_list))
    newest_profit = get_fundamentals(q,statDate = start_season)
    
    # 如果当前最新的数据还没有更新，则取sample里最新的
    if newest_profit.empty:
        newest_profit = get_fundamentals(q,statDate = sample[0])
        sample = sample[1:]
    
    # 然后取出12个最新的数据,计算过往平均值和标准差：
    sample_data = {}
    for date in sample[-12:]:
        sample_data[date] = get_fundamentals(q,statDate = date)
    sample_data = pd.concat(sample_data.values(), axis = 0)
    mean_data = sample_data.groupby('code').mean()
    mean_data.columns = ['mean']
    std_data = sample_data.groupby('code').std()
    std_data.columns = ['std']
    
    # 合并数据，计算成长因子——超额预期营业收入:
    newest_profit = newest_profit.merge(mean_data, on = 'code', how = 'left')
    newest_profit = newest_profit.merge(std_data, on = 'code', how = 'left')
    newest_profit['SUE_drift'] = (newest_profit['operating_revenue'] - newest_profit['mean']) / newest_profit['std']
    
    return newest_profit


# In[4]: (已注释)


#估值合成因子计算函数:
def epbp_factoring(stock_list, end_date): 
    
    # 这里取的估值倒数都是最新季度的(这里数据是按天更新，但是无法取固定日期的数据，所以还是取最新季度日期的来避免使用未来数据)
    start_season, sample = season_selection(end_date)
    v = get_fundamentals(query(valuation).filter(valuation.code.in_(stock_list)),statDate = start_season)
    #
    if v.empty:
        v = get_fundamentals(query(valuation).filter(valuation.code.in_(stock_list)),statDate = sample[0])

    # 整理数据倒数
    #ep_ttm（