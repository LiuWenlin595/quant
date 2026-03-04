#!/usr/bin/env python
# coding: utf-8

# 引言

# 研究目的

# 参考国泰君安证券研报《20181128-基于CCK模型的股票市场羊群效应研究》，对市场上存在的个别股票的涨跌引起相关股票收益率联动的现象进行分析探究。根据研报构建CCK模型，并进行改良，寻找更多联动信号，并正确分析市场趋势。

# 研究思路

# 1.根据研究报告，计算市场回报率并进行改良
# 2.在CCK模型的基础上，增加过滤指标进行分析和改良
# 3.通过改良后，并在此基础上进行回测分析。

# 研究结论

# 1.在本文进行改良后，模型信号出现的次数更多，但是纯度下降了。
# 2.不管标的指数是宽基还是行业，做多策略都明显优于做空策略，但是策略的收益率不是很出众。
# 3.与研报相同的是，策略有效性和标的指数的市值风格和风格纯度有关，市值越高出效果越好。
# 4.通过回测判断，板块间确实存在羊群效应，而且CCK模型也能很好分析出羊群效应出现的时间点，但是不足的是在区分市场方向上并不是很好，甚至会出现错误区分市场方向导致大额亏损的状况
# 5.最后，羊群效应确实如研报所言，确实存在，不过本文认为羊群效应不管多空都发生在短期，且人为区分信号所反映的市场方向更好


# 本文中所涉及的A股综合日市场回报率指标资料源自国泰安数据库，以下是国泰安数据库(CSMAR)的网址
# 
# http://www.gtarsc.com/Login/index?ReturnUrl=%2fHome%2fIndex  
# 
# 下文代码中涉及国泰安数据的都会用CSMAR进行前缀标记
# 
# （下文中提到的CSMAR的市场回报率全称为）
#      
#     （——考虑现金红利再投资的A股综合日市场回报率（流通市值加权平均法））


from jqdata import *
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import *
import time
import statsmodels.api as sm 
from sklearn.preprocessing import scale
import warnings

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号


# 展示CSMAR的A股综合日市场回报率表格
TRD = pd.read_excel('TRD20090101-20101231.xlsx')
CSMAR_market = TRD[TRD['综合市场类型']==5]
CSMAR_market.index= CSMAR_market.datetime
del CSMAR_market['Market_return_rate.1']
CSMAR_market_sample = CSMAR_market[(CSMAR_market.datetime>'2010-10-12'
                                   )&(CSMAR_market.datetime<='2010-11-06')
                                  ].sort_values('datetime',ascending=True)
print('国泰安数据库提供的考虑现金红利再投资的A股综合日市场回报率（流通市值加权平均法）')
print('')
display(CSMAR_market_sample.tail())


#     国泰安的数据库仅能免费提供2009年1月1日到2010年12月31日综合日市场回报率的数据，在文章仅在刚开始引用国泰安库的A股综合日市场的市场回报率。如果要购买所有年份的数据的话至少要543元才能获得，基于本文作者穷苦生活现状分析，购买这一指标并不现实所有改为由自己构建指标进行回测。
# 


###展示医药生物指数收盘价、相关龙头股收盘价及离散程度
t0 = time.time()
"获取申万一级医药生物行业在10年11月6号之前的成份分股代码"
pharmaceutical_industry_stock = get_industry_stocks('801150',date='2010-11-06')

###根据成份股，获取出该段时间内每日每股的股价###
pharmaceutical_industry = pd.DataFrame([])
for i in pharmaceutical_industry_stock:
    close = get_price(i,start_date='2010-10-13',end_date='2010-11-06',fields='close')
    pharmaceutical_industry[i]=close.close
print('')
print('医药生物行业在10年10月13到11月06这段时间内每股每日的收盘价')
display(pharmaceutical_industry.tail())

    
"获取医药生物龙头股通化东宝收盘价"
A600867 = get_price('600867.XSHG',start_date='2010-10-13',end_date='2010-11-06')
CriValue_600867=finance.run_query(query(finance.SW1_DAILY_PRICE
                          ).filter(finance.SW1_DAILY_PRICE.code=='801150',
                                    finance.SW1_DAILY_PRICE.date < '2010-11-06',
                                    finance.SW1_DAILY_PRICE.date > '2010-10-12'))
###统一日期索引###
CriValue_600867.index=A600867.index  
    
    
"计算医药生物板块指数与市场回报率的截面绝对离散程度"

###利用申万一级行业的医药生物板块的所有成分股，先输出每只成分股的收益率数据，再进行绝对加总运算。

###如果仅使用医药生物行业的指数收益率作为T时刻股票组合的截面收益率的话，会收到指数加权算法的影响，
###导致较大的误差

pharmaceutical_industry_rate = pharmaceutical_industry.pct_change(1).fillna(0)###获取医药生物板块横截面收益率
CSAD_list = pd.DataFrame([0]*len(pharmaceutical_industry_rate))
for i in range(len(pharmaceutical_industry_rate)):
    CSAD = abs(pharmaceutical_industry_rate.iloc[i,:]-CSMAR_market_sample.Market_return_rate[i]).sum(
                                )/len(pharmaceutical_industry_rate.iloc[i,:])
    CSAD_list.iloc[i,:] = CSAD
    
    
###运用sklearn的模块进行归一化###
A600867_close = scale(A600867.close)
pharmaceutical_industry = scale(CriValue_600867.close)
CSAD = scale(CSAD_list)
market_sample_rate = scale(CSMAR_market_sample.Market_return_rate)

dataframe = pd.DataFrame([A600867_close,pharmaceutical_industry,CSAD
                 ],index=['A600867_close','pharmaceutical_industry','CSAD']).T

###统一日期索引###
dataframe.index=CriValue_600867.index 
print('')
print('医药生物指数收盘价、相关龙头股收盘价及离散程度的数据表格')
display(dataframe.tail())
    

t1 = time.time()
print('获取数据完成 耗时 %s 秒' %round((t1-t0),3))  
print('')
fig = plt.subplots(figsize=(13,8))
plt.plot(dataframe.A600867_close,'r')
plt.plot(dataframe.pharmaceutical_industry,'blue')
plt.plot(dataframe.CSAD,'g')
plt.grid(True)
plt.title('医药生物行业指数收盘价及相关龙头股票收盘价',fontsize=20)
plt.legend(['A600867_close','pharmaceutical_industry','CSAD'],fontsize=15) 
plt.show()
    


# 2010年10月，医药生物行业龙头股通化东宝大涨，随后行业指数也跟着跟风上涨。
# 
# 上图可以很直观地看出，在10月15日通化东宝大涨后，医药板块指数收益率与上证指数收益率的离散程度明显变大，而在之后医药板块股跟风上涨后，离散程度逐渐减少。
# 


# 对A股综合日市场回报率指标进行构建

# 本文构建的市场回报率计算公式为：
# 
#     上证A股指数的收益率*上证A股的总流通市值占比
#                      +
#     深证A股指数的收益率*深证A股的总流通市值占比
# 而总流通市值 = 当日指数成份股流通市值的总和


###计算深证A股每日的流通市值
t0 = time.time()
def get_SZ_CriValue():
    A399107 = get_index_stocks('399107.XSHE',date='2019-09-01')
    A399107_market_value = pd.DataFrame([])
    for i in A399107:
        q = query(valuation.circulating_market_cap).filter(valuation.code==i)
        panel = get_fundamentals_continuously(q, end_date='2019-09-01', count=3100)
        stock_market = panel.minor_xs(i)
    ###删除后缀的原因是本文作者常用数据库时Mongodb，