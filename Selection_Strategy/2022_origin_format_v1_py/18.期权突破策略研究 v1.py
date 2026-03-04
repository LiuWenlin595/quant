#!/usr/bin/env python
# coding: utf-8

# 趋势突破策略与期权——以Dual Thrust为例

# 引言

# 在程序化交易中，趋势交易是最主要的交易方式，如果我们能想办法抓住这个趋势，就能够获得这部分趋势行情的收益。那么如何能够抓住趋势呢？最简单常用的一种方式就是均线，我们认为当短期均线向上突破长期均线时，接下来行情将上涨；反之，短期均线向下突破长期均线时认为行情将下跌。以这种方式来预估未来趋势，这就是常用的突破策略。突破策略通常是价格向上突破设定的价格（称为上轨）时认为是上涨趋势则做多，或者向下突破设定的下轨认为是下跌趋势则做空。本文我们将十大经典交易策略中的Dual Thrust应用在期权上，来获得期权行情上涨下跌的收益，形成一个简单有效的策略。Dula Thrust是一种非常经典的趋势跟踪策略，在实际中取得过极其优秀的效果。而期权具有明显的尖峰厚尾效应，同时具有很高的杠杆，是一种非常适合投机交易的资产。

# 期权策略

# Dual Thrust策略

# 在金融衍生品策略当中，最主要的投机策略就是趋势策略。资产价格变动的方向是趋势策略进行趋势跟踪的依据，总的来说，在股指期货和商品期货上，具有“低胜率高盈亏比”的特点，具有显著的盈利机会。经典的CTA趋势策略就是开盘区间突破策略。通常情况下，突破策略进场做多是在股指期货价格高于某个价位的时候，同理进场做空就是低于某个价位的时候。区间突破策略的一个典型指的就是开盘区间突破策略。其突破价格的计算是：突破上界=当日开盘价+区间宽度值，突破下界=开盘价-区间宽度值。计算区间宽度是有很多种方法的，本文选取经典的Dual Thrust策略来计算区间，之后再乘上由样本内优化获得的系数 $K$来确定。系数 $K$包含上轨系数$Ks$和下轨系数$Kx$。  
# Dual Thrust是一个趋势跟踪系统，由Michael Chalek在20世纪80年代开发，曾被Future Thruth杂志评为最赚钱的策略之一。Dual Thrust系统具有简单易用、适用度广的特点，其思路简单、参数很少，配合不同的参数、止盈止损和仓位管理，可以为投资者带来长期稳定的收益，被投资者广泛应用于股票、货币、贵金属、债券、能源及股指期货市场等。在Dual Thrust交易系统中，对于震荡区间的定义非常关键，这也是该交易系统的核心和精髓。Dual Thrust趋势系统使用  $$Range = Max(HH-LC,HC-LL)$$  来描述震荡区间的大小。其中$HH$是N日最大的最高价，$LC$是N日最低的收盘价，$HC$是N日最大的收盘价，$LL$是N日最小的最低价。  
# 当价格向上突破上轨时，如果当时持有空仓，则先平仓，再开多仓；如果没有仓位，则直接开多仓；  
# 当价格向下突破下轨时，如果当时持有多仓，则先平仓，再开空仓；如果没有仓位，则直接开空仓。
# <img src="http://img0.ph.126.net/hGIFYliICAa0l0n_EQXEaw==/6631238190003744507.jpg" />

# 合约选择

# 和股指期货相比，期权的不同点就在于：在同一时间市场上进行交易的，有很多行权价格和行权日期不一样的认购期权和认沽期权。不一样的期权交易量和成交量有着非常大的区别，其中一部分期权的流动性很差。所以在交易之前，我们需要在每一个交易日里挑选出适合的期权合约。总的原则是个选择流动性好的期权，期权流动性强弱的判断指标就是持仓量和成交量。一般来说期权的当月合约具有较大的成交量和持仓量，具有的流动性最好，所以我们选择当月合约。  
# 此外，我们知道期权总共包含两大类：认沽期权和认购期权。按行权价格的不同可以被分成实值期权、平值期权、虚值期权。对认沽期权来说，行权价低于标当前价格的期权叫做虚值期权，高于标的价格的期权叫做实值期权，而与标的价格最接近的期权叫做平值期权；与之相反，认购期权行权价高于标的当前价格的期权叫做虚值期权，高低于标的价格的期权叫做实值期权，与标的价格最接近的期权叫做平值期权。因此我们能够将期权区分为6大类，分别是：平值认购、平值认沽、虚值认购、虚值认沽、实值认购、实值认沽。在接下的实验验证中，我们对这些合约进行回测，找出效果最好的合约类型。

# 交易信号

# 区间突破策略利用历史数据来预测未来的走势。一般来说，预测的标的与交易的资产应该相同。但是由于期权价格常常剧烈变化，日内波动太大，容易出现“假”突破信号，影响趋势判断的方向，发出错误的交易信号，对整个策略影响很大。而50ETF期权的标的日内价格相对于期权价格走势更加平稳，不容易产生假信号。因此选用50ETF产生突破信号，然后交易50ETF期权。

# 风险控制

# 一般情况下，趋势策略和择时策略通过设置止损的方式来降低风险。因为期权的波动非常大，通常情况下合理的止损阈值会很大，不然容易触发止损平仓，可是一旦在这样会致使单次交易对净值造成的亏损非常大。所以为了单次交易对净值的影响尽可能降低，本文利用降低仓位的方法进行风险控制。具体做法是，在每次交易的时候，最多占用资金的10%给期权做权利金。当然这样的话买入期权就会有90%的资金处于闲置状态；但是对于卖出期权的交易，交易保证金用剩余现金就充足了。因此通过控制仓位，使得单次交易的净值波动不会太大。

# 研究内容

# 我们选择的交易时间是从2017-1-1到2019-5-20，将这个时间段划分为样本内（2017-1-1至2018-5-20）和样本外（2018-5-21-2019-5-20），接下来的研究我们统统选择在样本内进行分析。  
# 首先，我们进行期权交易的可行性分析。由于50ETF价格每日变化，每日的期权合约也有可能变化，所以我们首先将每日的期权合约代码取下来，存放在三个列表中，分别是：平值期权合约列表（Code_atm）,实值期权合约列表（Code_itm），虚值期权合约列表（Code_otm)。每个列表包含两列，第一列是看涨期权代码，第二列是看跌期权代码。实值期权与虚值期权分别只取除平值外实一档或者虚一档的期权。代码如下：

import warnings
import matplotlib 
import numpy as np
import pandas as pd
import datetime as dt
from jqdata import *
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
warnings.filterwarnings('ignore')  #过滤代码运行过程中烦人的警告
matplotlib.rcParams['axes.unicode_minus']=False #解决画图中负数显示问题


def option_code(df,price,ContractType):
    df=df.sort_values(by='StrikePrice')
    df=df.reset_index()
    df.loc[:,'StrikePrice']=abs(df.loc[:,'StrikePrice']-price)
    idx=df.loc[:,'StrikePrice'].idxmin()
    code=df.loc[idx-1:idx+1,'ContractCode'].values
    if ContractType=='p':
        code=code[::-1]
    return code
def get_option_code(date):
    price=get_price('510050.XSHG',count=1,end_date=date,fq='none',fields=['open'])['open'].values[0]
    q=query(jy.Opt_DailyPreOpen).filter(jy.Opt_DailyPreOpen.TradingDate==date,jy.Opt_DailyPreOpen.ULAName=='50ETF')
    df=jy.run_query(q)
    df=df.loc[:,['ContractCode','TradingCode','StrikePrice','ExerciseDate']]
    df=df[df['ExerciseDate']==df['ExerciseDate'].min()].reset_index()
    row,col=df.shape
    if row>0:
        for i in range(row):
            scode=df.loc[i,'TradingCode']
            if scode[6]=='C' and scode[11]=='M':
                df.loc[i,'CP']='c'
            elif scode[6]=='P' and scode[11]=='M':
                df.loc[i,'CP']='p' 
        df1=df[df['CP']=='c']
        df2=df[df['CP']=='p']
        code1=option_code(df1,price,'c')
        code2=option_code(df2,price,'p')
        code1=[str(code)+'.XSHG' for code in code1]
        code2=[str(code)+'.XSHG' for code in code2]
        return code1,code2
    else:
        print(date,'这一天取不到期权合约！！')
        return 'None','None'  


###运行时间约1分钟，耐心等待！！

Code_itm=[] ###实值期权代码列表
Code