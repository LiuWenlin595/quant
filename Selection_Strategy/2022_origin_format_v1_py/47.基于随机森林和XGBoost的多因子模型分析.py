#!/usr/bin/env python
# coding: utf-8

# 1.概述

# Bagging和Boosting都是分类器的集成算法。Bagging以并行方法集成算法，先构建一些小的分类器，然后基于每个分类器的结果做均值计算得到最终模型。Bagging方法因为其方差小，所以比单个分类器的效果更好。Boosting以串行方法集成，每个分类器顺序参与模型评估，并试图降低最终模型的偏差。Boosting方法的准确率较高，且鲁棒性较强。本文中，分别使用了RandomForest和XGBoost两种机器学习算法作为代表，对传统多因子模型进行分析和比较。两者都是基于决策树算法的延伸，前者基于Bagging方法，后者基于Boosting方法。具体的研究包括：
# （1）特征数量对RandomForest和XGBoost预测能力的影响评价	
# （2）	RandomForest和XGBoost的参数（模型复杂度）对于预测能力的影响评价
# （3）	RandomForest和XGBoost的预测能力的评价
# （4）	RandomForest和XGBoost的特征重要度

import pandas as pd
import numpy as np
import math
import jqdata
import time
import datetime
from jqfactor import standardlize
from jqfactor import winsorize_med
from jqfactor import get_factor_values
from jqfactor import neutralize
from sklearn.model_selection import StratifiedKFold, cross_val_score  # 导入交叉检验算法
from sklearn.feature_selection import SelectPercentile, f_classif  # 导入特征选择方法库
from sklearn.pipeline import Pipeline  # 导入Pipeline库
from sklearn.metrics import accuracy_score  # 准确率指标
from sklearn.metrics import roc_auc_score
from jqlib.technical_analysis import *
from xgboost.sklearn import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import seaborn as sns

# 2. 数据获取和预处理

# 2.1 股票池设定

# 中证全指成分股。剔除ST股票，剔除每个截面期下一交易日停牌的股票，剔除上市3个月内的股票，每只股票视作一个样本。

#去除上市距beginDate不足n天的股票
def delete_stop(stocks,beginDate,n):
    stockList=[]
    beginDate = datetime.datetime.strptime(beginDate, "%Y-%m-%d")
    for stock in stocks:
        start_date=get_security_info(stock).start_date
        if start_date<(beginDate-datetime.timedelta(days=n)).date():
            stockList.append(stock)
    return stockList

#剔除ST股
def delete_st(stocks,begin_date):
    st_data=get_extras('is_st',stocks, count = 1,end_date=begin_date)
    stockList = [stock for stock in stocks if not st_data[stock][0]]
    return stockList

# 2.2 时间区间

# 2014年1月1日-2018年12月31日的5年区间。其中前4年区间（48个月）作为训练集，后1年区间（12个月）作为测试集。

#按月区间取值
peroid = 'M'
#样本区间（训练集+测试集的区间为2014-1-31到2018-12-31）
start_date = '2014-02-01'
end_date = '2019-01-31'
#训练集长度
train_length = 48
#聚宽一级行业
industry_code = ['HY001', 'HY002', 'HY003', 'HY004', 'HY005', 'HY006', 'HY007', 'HY008', 'HY009', 'HY010', 'HY011']

#股票池，获取中证全指
securities_list = delete_stop(get_index_stocks('000985.XSHG'),start_date,90)
securities_list = delete_st(securities_list,start_date)

# 2.3 特征和标签提取

# 每个自然月的最后一个交易日，计算因子暴露度，作为样本的原始特征；计算下期收益率，作为样本的标签

jqfactors_list = ['current_ratio',
                  'net_profit_to_total_operate_revenue_ttm',
                  'gross_income_ratio',
                  'roe_ttm',
                  'roa_ttm',
                  'total_asset_turnover_rate',\
                  'net_operating_cash_flow_coverage',
                  'net_operate_cash_flow_ttm',
                  'net_profit_ttm',\
                  'cash_to_current_liability',
                  'operating_revenue_growth_rate',
                  'non_recurring_gain_loss',\
                  'operating_revenue_ttm',
                  'net_profit_growth_rate']

def get_jq_factor(date):
    factor_data = get_factor_values(securities=securities_list,                                     factors=jqfactors_list,                                     count=1,                                     end_date=date)
    df_jq_factor=pd.DataFrame(index=securities_list)
    
    for i in factor_data.keys():
        df_jq_factor[i]=factor_data[i].iloc[0,:]
    
    return df_jq_factor

q = query(valuation.code, 
      valuation.market_cap,#市值
      valuation.circulating_market_cap,
      valuation.pe_ratio, #市盈率（TTM）
      valuation.pb_ratio, #市净率（TTM）
      valuation.pcf_ratio, #CFP
      valuation.ps_ratio, #PS
      balance.total_assets,
      balance.total_liability,
      balance.development_expenditure, #RD
      balance.dividend_payable,
      balance.fixed_assets,  
      balance.total_non_current_liability,
      income.operating_profit,
      income.total_profit, #OPTP
      #
      indicator.net_profit_to_total_revenue, #净利润/营业总收入
      indicator.inc_revenue_year_on_year,  #营业收入增长率（同比）
      indicator.inc_net_profit_year_on_year,#净利润增长率（同比）
      indicator.roe,
      indicator.roa,
      indicator.gross_profit_margin #销售毛利率GPM
    ).filter(
      valuation.code.in_(securities_list)
    )

#获取指定周期的日期列表 'W、M、Q'
def get_period_date(peroid,start_date, end_date):
    #设定转换周期period_type  转换为周是'W',月'M',季度线'Q',五分钟'5min',12天'12D'
    stock_data = get_price('000001.XSHE',start_date,end_date,'daily',fields=['close'])
    #记录每个周期中最后一个交易日
    stock_data['date']=stock_data.index
    #进行转换，周线的每个变量都等于那一周中最后一个交易日的变量值
    period_stock_data=stock_data.resample(peroid).last()
    date = period_stock_data.index
    pydate_array = date.to_pydatetime()
    date_only_array = np.vectorize(lambda s: s.strftime('%Y-%m-%d'))(pydate_array )
    date_only_series = pd.Series(date_only_array)
    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    start_date = start_date-datetime.timedelta(days=1)
    start_date = start_date.strftime("%Y-%m-%d")
    date_list = date_only_series.values.tolist()
    date_list.insert(0,start_date)
    return date_list

def initialize_df(df,date):
    
    #净资产
    df['net_assets']=df['total_assets']-df['total_liability']

    df_new = pd.DataFrame(index=securities_list)
        
    #估值因子
    df_new['EP'] = df['pe_ratio'].apply(lambda x: 1/x)
    df_new['BP'] = df['pb_ratio'].apply(lambda x: 1/x)
    df_new['SP'] = df['ps_ratio'].apply(lambda x: 1/x)
    df_new['DP'] = df['dividend_payable']/(df['market_cap']*100000000)
    df_new['RD'] = df['development_expenditure']/(df['market_cap']*100000000)
    df_new['CFP'] = df['pcf_ratio'].apply(lambda x: 1/x)
    
    #杠杆因子
    #对数流通市值
    df_new['CMV'] = np.log(df['circulating_market_cap'])
    #总资产/净资产
    df_new['financial_leverage']=df['total_assets']/df['net_assets']
    #非流动负债/净资产
    df_new['debtequityratio']=df['total_non_current_liability']/df['net_assets']
    #现金比率=(货币资金+有价证券)÷流动负债
    df_new['cashratio']=df['cash_to_current_liability']
    #流动比率=流动资产/流动负债*100%
    df_new['currentratio']=df['current_ratio']
    
    #财务质量因子
    # 净利润与营业总收入之比
    df_new['NI'] = df['net_profit_to_total_operate_revenue_ttm']
    df_new['GPM'] = df['gross_income_ratio']
    df_new['ROE'] = df['roe_ttm']
    df_new['ROA'] =