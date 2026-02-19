#!/usr/bin/env python
# coding: utf-8

# Note book 内容提要：
#     1. 欧式期权定价公式和隐含波动率求解
#     2. SVI 隐含波动率参数化
#     3. 使用有限差分方法计算 Dupire 局部波动率的数值方法
#     4. 傅里叶变换方法求解 BCC 随机波动率加跳模型
# 
# 一、 欧式期权定价通常会采用两个方程：
# 
#     (1) 以现货资产为标的物的BSM方程，这类期权称为“现货期权”；
#     (2) 以期货合约做为标的物的Black方程，这类期权称为“期货期权”。
#     
# 两者其实没有实质差别，但是在计算中会体现出差异。
# 目前郑商所、大商所的期权都是以期货合约为标的物的期货合约，沪深两所的300ETF和50ETF期权则是以现货资产作为标的物的期权。比较有意思的的是中金所IO，中金所IO的标的是沪深300指数现货，但是IO的交割日期与IF的交割日期一致，所以IO也可以看作是以相同到期月期货合约为标的的期货期权。
# 
# 期权定价的解析公式是通过求解BSM方程或Black方程获得到的显式解，所以只有边界条件清晰的期权才能获得明确的解析公式（这里不解释什么叫“边界条件”），简言之就是简单的期权可以通过直接求解方程的，所谓简单的期权主要包括欧式期权和美式看涨期权。在风险中性的测度下，不提前行权是美式看涨期权多头的最优策略，所以在定价时可以将美式看涨期权当作欧式看涨期权进行处理，但是美式看跌期权则不能通过简单的解析公式获得期权的价格，而是需要和复杂的奇异期权一样采用数值方法求解。
# 
# 二、 常用的数值方法可以概括为四类：
# 
#     (1) 有限差分法；
#     (2) 树形方法；
#     (3) 傅里叶变换；
#     (4) 蒙特卡洛模拟。
# 
# 这四种数值方法涵盖了几乎所有期权定价问题中会涉及到的数值方法，四种方法各有优势，在进行隐含波动率建模时应当根据建模的方法来选择数值方法。
# 本篇采用的建模方法是基于概率密度的建模方法，数值方法主要是有限差分和隐含树形两种。本篇中主要会用到的方法是有限差分法，主要就是为了偷个懒，很早以前我就写过了一版有限差分的代码，这次直接搬到帖子里就行。选择差分方法的另外一个原因是差分方法可以适用于几乎所有模型，只要对Black-Scholes方程或Black方程进行离散化，根据期权的特性给出对应的边界条件即可。
# 在利用随机波动率、跳跃扩散、CEV等建模方法时，通常可以采用傅里叶变换的方法来快速得到期权价格，尽管有限差分法可能会更精确，但是傅里叶变换在求解的速度上优势更明显。
# 蒙特卡洛模拟则可以更直观地获得期权定价，但是代价就是计算成本会比较高，毕竟需要重复数十万次的计算，但是在交易频率相对较低的场景下这中计算成本也不是不可容忍，甚至是可以忽略的。

import datetime
import jqdata as jq
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import root
from scipy.optimize import minimize

def get_option_ticks(option_list,minute,frequency = '1m'):
    # 每1分钟为一个最小的单元，查看期权的tick数据，简单化处理，考虑在买一和卖一之间
    fields = ['time','current','position','volume',
              'a1_p','b1_p','a1_v','b1_v']
    
    t = int(frequency[:-1])
    opt_ticks = []
    for opt in option_list:
        # 行权价有时候会因为标的价格波动而调整造成同一到期日下有两组行权价相同的认购认沽，
        # 这种情况下我仍然把这两个认购期权看作是同一个期权，两个认沽同理。
        ticks = pd.DataFrame(get_ticks(opt,
                             start_dt = minute - datetime.timedelta(seconds = int(60 * t)),
                             end_dt = minute, fields = fields), columns = fields)
        if len(ticks) > 0:
            ticks.loc[:,'code'] = opt
            opt_ticks.append(ticks)
    if len(opt_ticks) > 0:
        opt_ticks = pd.concat(opt_ticks,
                               axis = 0).reset_index(drop = True
                                                    ).sort_values('time',
                                                                  ascending = True)#.to_dict()
    else:
        opt_ticks = pd.DataFrame()
    return opt_ticks

underlying_code = '000300.XSHG'
date = '2021-10-18'
date_zero = datetime.date(2021,10,18)
minute = datetime.datetime(2021,10,18,14,30,0)

contract = jq.opt.run_query(query(jq.opt.OPT_CONTRACT_INFO
                                      ).filter(jq.opt.OPT_CONTRACT_INFO.underlying_symbol == underlying_code
                                              ).filter(jq.opt.OPT_CONTRACT_INFO.list_date <= date
                                                      ).filter(jq.opt.OPT_CONTRACT_INFO.last_trade_date >= date)
                                   ).set_index('code')

contract = contract[contract.contract_type == 'CO']
option_list = contract.index.tolist()
ticks = get_option_ticks(option_list,minute).sort_values('time')
ticks = ticks.groupby('code').tail(1).set_index('code')

underlying = {'future_code':{},'future_price':{},'spot_price':{}}
for i in option_list:
    underlying['future_code'][i] = 'IF' + i[2:6] + '.CCFX'
    underlying['spot_price'][i] = get_price(underlying_code, 
                                       start_date = minute, end_date = minute, 
                                       frequency = '30m', fields = 'close').iloc[0,0]

    try:
        underlying['future_price'][i] = get_price(underlying['future_code'][i], 
                                           start_date = minute, end_date = minute, 
                                           frequency = '30m', fields = 'close').iloc[0,0]
    except:
        pass
    
risk_free = 0.0232 # 查了当天深交所91天国债逆回购的收盘利率
q = 0 # 假设红绿率为0
common = list(set(ticks.index) & set(contract.index))
maturity_days = (contract.loc[common,'expire_date'] - date_zero)
maturity = maturity_days / datetime.timedelta(days = 365)
maturity_days = maturity * 365

maturity_days.name = 'maturity_days'
maturity.name = 'maturity'

underlying = pd.DataFrame(underlying).loc[common,:]

moneyness = np.log(underlying.future_price.fillna(underlying.spot_price) / contract.exercise_price).loc[common]
moneyness_spot = np.log(underlying.spot_price / contract.exercise_price).loc[common]

moneyness.name = 'moneyness'
moneyness_spot.name = 'moneyness_spot'

contract_ticks = pd.concat([underlying,
                            contract.loc[common,['exercise_price','expire_date']],
                            maturity_days, maturity,moneyness,moneyness_spot,
                            ticks.loc[common,:]], axis = 1).sort_values('maturity', axis = 0)
contract_ticks

# 这一节是基础的欧式期权定价公式
# 整理一下，只分bsm和black两个函数
def bsm(s0,sigma,t,r,q,strike,model = 'black', out_put = 'greeks'):
    discount = np.exp(-r * t)
    if model == 'black':
        d1 = (np.log(s0 / strike) + (0.5 * sigma**2) * t) / (sigma * np.sqrt(t))
    
    elif model == 'bsm':
        d1 = (np.log(s0 / strike) + (r - q + 0.5 * sigma**2) * t) / (sigma * np.sqrt(t))
        
    d2 = d1 - sigma * np.sqrt(t)
    p = norm.cdf(d2)
    
    if out_put == 'greeks':
        call = {}
        call['delta'] = norm.cdf(d1)
        call['gamma'] = norm.pdf(d1) / (s0 * sigma * np.sqrt(t