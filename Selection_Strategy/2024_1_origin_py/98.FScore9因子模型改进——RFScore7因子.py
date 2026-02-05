#!/usr/bin/env python
# coding: utf-8

from typing import (List,Tuple,Dict,Callable,Union)

import datetime as dt
import numpy as np
import pandas as pd
import empyrical as ep

import graphviz
from sklearn.tree import export_graphviz
from sklearn.ensemble import RandomForestClassifier

from tqdm import tqdm_notebook

import alphalens as al

from jqdata import *
from jqfactor import (calc_factors,Factor)

import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif']=['SimHei'] #用来正常显示中文标签
plt.rcParams['axes.unicode_minus']=False #用来正常显示负号

# 股票池筛选
# 获取年末季末时点
def get_trade_period(start_date: str, end_date: str, freq: str = 'ME') -> list:
    '''
    start_date/end_date:str YYYY-MM-DD
    freq:M月，Q季,Y年 默认ME E代表期末 S代表期初
    ================
    return  list[datetime.date]
    '''
    days = pd.Index(pd.to_datetime(get_trade_days(start_date, end_date)))
    idx_df = days.to_frame()

    if freq[-1] == 'E':
        day_range = idx_df.resample(freq[0]).last()
    else:
        day_range = idx_df.resample(freq[0]).first()

    day_range = day_range[0].dt.date

    return day_range.dropna().values.tolist()


# 筛选股票池
class Filter_Stocks(object):
    '''
    获取某日的成分股股票
    1. 过滤st
    2. 过滤上市不足N个月
    3. 过滤当月交易不超过N日的股票
    ---------------
    输入参数：
        index_symbol:指数代码,A等于全市场,
        watch_date:日期
    '''
    
    def __init__(self,symbol:str,watch_date:str)->None:
        
        if isinstance(watch_date,str):
            
            self.watch_date = pd.to_datetime(watch_date).date()
            
        else:
            
            self.watch_date = watch_date
            
        self.symbol = symbol
        self.get_index_component_stocks()
        
    def get_index_component_stocks(self)->list:
        
        '''获取指数成分股'''
        
        if self.symbol == 'A':
            
            wd:pd.DataFrame = get_all_securities(types=['stock'],date=self.watch_date)
            self.securities:List = wd.query('end_date != "2200-01-01"').index.tolist()
        else:
            
            self.securities:List = get_index_stocks(self.symbol,self.watch_date)
    
    def filter_paused(self,paused_N:int=1,threshold:int=None)->list:
        
        '''过滤停牌股
        -----
        输入:
            paused_N:默认为1即查询当日不停牌
            threshold:在过paused_N日内停牌数量小于threshold
        '''
        
        if (threshold is not None) and (threshold > paused_N):
            raise ValueError(f'参数threshold天数不能大于paused_N天数')
            
        
        paused = get_price(self.securities,end_date=self.watch_date,count=paused_N,fields='paused',panel=False)
        paused = paused.pivot(index='time',columns='code')['paused']
        
        # 如果threhold不为None 获取过去paused_N内停牌数少于threshodl天数的股票
        if threshold:
            
            sum_paused_day = paused.sum()
            self.securities = sum_paused_day[sum_paused_day < threshold].index.tolist()
        
        else:
            
            paused_ser = paused.iloc[-1]
            self.securities = paused_ser[paused_ser == 0].index.tolist()

    def filter_zdt(self)->list:
        
        '''过滤zdt股
        0是满足非涨跌，非停板
        '''
        zdt = get_price(self.securities,end_date=self.watch_date,fields=['close','high_limit','low_limit','paused'],count=1,panel=False,fq='post')
        zdt['zdt_raw'] = zdt.apply(lambda x :1 if ((x['close']==x['high_limit']) or (x['close']==x['low_limit'])) else 0, axis = 1)
        zdt['zdt'] = zdt.apply(lambda x: 0 if ((x['paused']==0) and (x['zdt_raw']==0)) else 1, axis = 1)
        
        zdt = zdt.pivot(index='time',columns='code')['zdt']
        zdt_ser = zdt.iloc[-1]
        self.securities = zdt_ser[zdt_ser == 0].index.tolist()
    
    def filter_st(self)->list:
        
        '''过滤ST'''
              
        extras_ser = get_extras('is_st',self.securities,end_date=self.watch_date,count=1).iloc[-1]
        
        self.securities = extras_ser[extras_ser == False].index.tolist()
    
    def filter_ipodate(self,threshold:int=180)->list:
        
        '''
        过滤上市天数不足以threshold天的股票
        -----
        输入：
            threhold:默认为180日
        '''
        
        def _check_ipodate(code:str,watch_date:dt.date)->bool:
            
            code_info = get_security_info(code)
            
            if (code_info is not None) and ((watch_date - code_info.start_date).days > threshold):
                
                return True
            
            else:
                
                return False

        self.securities = [code for code in self.securities if _check_ipodate(code,self.watch_date)]
    
    
    
    def filter_industry(self,industry:Union[List,str],level:str='sw_l1',method:str='industry_name')->list:
        '''过略行业'''
        ind = get_stock_ind(self.securities,self.watch_date,level,method)
        target = ind.to_frame('industry').query('industry != @industry')
        self.securities = target.index.tolist()
        
def get_stock_ind(securities:list,watch_date:str,level:str='sw_l1',method:str='industry_code')->pd.Series:
    
    '''
    获取行业
    --------
        securities:股票列表
        watch_date:查询日期
        level:查询股票所属行业级别
        method:返回行业名称or代码
    '''
    
    indusrty_dict = get_industry(securities, watch_date)

    indusrty_ser = pd.Series({k: v.get(level, {method: np.nan})[
                             method] for k, v in indusrty_dict.items()})
    
    indusrty_ser.name = method.upper()
    
    return indusrty_ser

# 风险指标
# 风险指标


def Strategy_performance(return_df: pd.DataFrame,
                         periods='daily') -> pd.DataFrame:
    '''计算风险指标 默认为月度:月度调仓'''

    ser: pd.DataFrame = pd.DataFrame()
    ser['年化收益率'] = ep.annual_return(return_df, period=periods)
    ser['累计收益'] = ep.cum_returns(return_df).iloc[-1]
    ser['波动率'] = return_df.apply(
        lambda x: ep.annual_volatility(x, period=periods))
    ser['夏普'] = return_df.apply(ep.sharpe_ratio, period=periods)
    ser['最大回撤'] = return_df.apply(lambda x: ep.max_drawdown(x))
    
    if 'benchmark' in return_df.columns:

        select_col = [col for col in return_df.columns if col != 'benchmark']

        ser['IR'] = return_df[select_col].apply(
            lambda x: information_ratio(x, return_df['benchmark']))
        ser['Alpha'] = return_df[select_col].apply(
            lambda x: ep.alpha(x, return_df['benchmark'], period=periods))
        
        ser['超额收益'] = ser['年化收益率'] - ser.loc[
            'benchmark', '年化收益率']  #计算相对年化波动率
        
    return ser.T


def information_ratio(returns, factor_returns):
    """
    Determines the Information ratio of a strategy.

    Parameters
    ----------
    returns : :py:class:`pandas.Series` or pd.DataFrame
        Daily returns of the strategy, noncumulative.
        See full explanation in :func:`~empyrical.stats.cum_returns`.
    factor_returns: :class:`float` / :py:class:`pandas.Series`
        Benchmark return to compare returns against.

    Returns
    -------
    :class:`float`
        The information ratio.

    Note
    -----
    See https://en.wikipedia.org/wiki/information_ratio for more details.

    """
    if len(returns) < 2:
        return np.nan

    active_return = _adjust_returns(returns, factor_returns)
    tracking_error = np.std(active_return, ddof=1)
    if np.isnan(tracking_error):
        return 0.0
    if tracking_error == 0:
        return np.nan
    return np.mean(active_return) / tracking_error


def _adjust_returns(returns, adjustment_factor):
    """
    Returns a new :py:class:`pandas.Series` adjusted by adjustment_factor.
    Optimizes for the case of adjustment_factor being 0.

    Parameters
    ----------
    returns : :py:class:`pandas.Series`
    adjustment_factor : :py:class:`pandas.Series` / :class:`float`

    Returns
    -------
    :py:class:`pandas.Series`
    """
    if isinstance(adjustment_factor, (float, int)) and adjustment_factor == 0:
        return returns.copy()
    return returns - adjustment_factor

# 标记得分
def sign(ser: pd.Series) -> pd.Series:
    '''标记分数,正数为1,负数为0'''
    
    return ser.apply(lambda x: np.where(x > 0, 1, 0))

class FScore(Factor):
    '''
    FScore原始模型
    '''
    name = 'FScore'
    max_window = 1

    watch_date = None
    # paidin_capital 实收资本 股本变化会反应在该科目中
    dependencies = [
        'roa', 'roa_4', 'net_operate_cash_flow', 'total_assets',
        'total_assets_1', 'total_assets_4', 'total_assets_5',
        'operating_revenue', 'operating_revenue_4',
        'total_non_current_assets', 'total_non_current_liability',
        'total_non_current_assets_4', 'total_non_current_liability_4',
        'total_current_assets', 'total_current_liability',
        'total_current_assets_4', 'total_current_liability_4',
        'gross_profit_margin', 'gross_profit_margin_4', 'paidin_capital',
        'paidin_capital_4'
    ]

    def calc(self, data: Dict) -> None:

        roa: pd.DataFrame = data['roa'] # 单位为百分号

        cfo: pd.DataFrame = data['net_operate_cash_flow'] /             data['total_assets']

        delta_roa: pd.DataFrame = roa / data['roa_4'] - 1

        accrual: pd.DataFrame = cfo - roa * 0.01

        # 杠杆变化
        ## 变化为负数时为1，否则为0 取相反
        leveler: pd.DataFrame = data['total_non_current_liability'] /             data['total_non_current_assets']

        leveler1: pd.DataFrame = data['total_non_current_liability_4'] /             data['total_non_current_assets_4']

        delta_leveler: pd.DataFrame = -(leveler / leveler1 - 1)

        # 流动性变化
        liquid: pd.DataFrame = data['total_current_assets'] /             data['total_current_liability']

        liquid_1: pd.DataFrame = data['total_current_assets_4'] /             data['total_current_liability_4']

        delta_liquid: pd.DataFrame = liquid / liquid_1 - 1

        # 毛利率变化
        delta_margin: pd.DataFrame = data['gross_profit_margin'] /             data['gross_profit_margin_4'] - 1

        # 是否发行普通股权
        eq_offser: pd.DataFrame = -(data['paidin_capital'] / data[
            'paidin_capital_4'] - 1)

        # 总资产周转率
        total_asset_turnover_rate: pd.DataFrame = data[
            'operating_revenue'] / (data['total_assets'] +
                                          data['total_assets_1']).mean()

        total_asset_turnover_rate_1: pd.DataFrame = data[
            'operating_revenue_4'] / (data['total_assets_4'] +
                                            data['total_assets_5']).mean()

        # 总资产周转率同比
        delta_turn: pd.DataFrame = total_asset_turnover_rate /             total_asset_turnover_rate_1 - 1

        indicator_tuple: Tuple = (roa, cfo, delta_roa, accrual, delta_leveler,
                                  delta_liquid, delta_margin, delta_turn,
                                  eq_offser)

        # 储存计算FFscore所需原始数据
        self.basic: pd.DataFrame = pd.concat(indicator_tuple).T.replace([-np.inf,np.inf],np.nan)

        self.basic.columns = [
            'ROA', 'CFO', 'DELTA_ROA', 'ACCRUAL', 'DELTA_LEVELER',
            'DLTA_LIQUID', 'DELTA_MARGIN', 'DELTA_TURN', 'EQ_OFFSER'
        ]
        
        self.fscore: pd.Series = self.basic.apply(sign).sum(axis=1)

# 因子获取
def get_FFScore(
    symbol: str,
    factor: Factor,
    periods: List,
    filter_industry: Union[List,
                           str] = None) -> Tuple[pd.Series, pd.DataFrame]:
    '''
    获取FFScore得分
    ------
    输入参数：
        symbol:输入A表示全A股票池或者输入指数代码
        factor:不同的ffscore模型
        periods:计算得分的时间序列
        filter_industry:传入需要过滤的行业
    ------
    return 最终得分,财务数据
    '''
    for trade in tqdm_notebook(periods, desc='FFScore因子获取'):

        # 获取股票池
        stock_pool_func = Filter_Stocks(symbol, trade)
        stock_pool_func.filter_zdt()
        stock_pool_func.filter_paused(22, 21)  # 过滤22日停牌超过21日的股票
        stock_pool_func.filter_st()  # 过滤st
        stock_pool_func.filter_ipodate(180)  # 过滤次新
        # 是否过滤行业
        if filter_industry:

            stock_pool_func.filter_industry(filter_industry)

        my_factor = factor()
        my_factor.watch_date = trade
        calc_factors(stock_pool_func.securities,[my_factor],start_date=trade,end_date=trade)
        
        yield my_factor

def quantile_trans(df, tau):
    df_trans = df.apply(lambda x: -1 * (x - x.quantile(tau))**2, axis=1)
    return df_trans

def get_factor_price(security: Union[List, str],
                     periods: List) -> pd.DataFrame:
    '''获取对应频率的收盘价'''
    for trade in tqdm_notebook(periods, desc='获取收盘价数据'):

        yield get_price(security,
                        end_date=trade,
                        count=1,
                        fields='close',
                        fq = 'post',
                        panel=False)


def get_factor_pb_ratio(securities: Union[list, str],
                        periods: list) -> pd.DataFrame:
    '''获取PB数据'''
    for trade in tqdm_notebook(periods, desc='获取PB数据'):

        yield get_valuation(securities,
                            end_date=trade,
                            fields=['pb_ratio'],
                            count=1)

def get_factor_pe_ratio(securities: Union[list, str],
                        periods: list) -> pd.DataFrame:
    '''获取PE数据'''
    for trade in tqdm_notebook(periods, desc='获取PE数据'):

        yield get_valuation(securities,
                            end_date=trade,
                            fields=['pe_ratio'],
                            count=1)        
        
def get_factor_ps_ratio(securities: Union[list, str],
                        periods: list) -> pd.DataFrame:
    '''获取PS数据'''
    for trade in tqdm_notebook(periods, desc='获取PS数据'):

        yield get_valuation(securities,
                            end_date=trade,
                            fields=['ps_ratio'],
                            count=1) 
        
def get_factor_pcf_ratio(securities: Union[list, str],
                        periods: list) -> pd.DataFrame:
    '''获取PCF数据'''
    for trade in tqdm_notebook(periods, desc='获取PCF数据'):

        yield get_valuation(securities,
                            end_date=trade,
                            fields=['pcf_ratio'],
                            count=1)         

        
def get_DP(security,watch_date,days):
    
    # 获取股息数据
    one_year_ago=watch_date-datetime.timedelta(days=days)
    
    q1=query(finance.STK_XR_XD.a_registration_date,finance.STK_XR_XD.bonus_amount_rmb,            finance.STK_XR_XD.code           ).filter(finance.STK_XR_XD.a_registration_date>= one_year_ago,                    finance.STK_XR_XD.a_registration_date<=watch_date,                    finance.STK_XR_XD.code.in_(security[0:int(len(security)*0.3)]))
    q2=query(finance.STK_XR_XD.a_registration_date,finance.STK_XR_XD.bonus_amount_rmb,            finance.STK_XR_XD.code           ).filter(finance.STK_XR_XD.a_registration_date>= one_year_ago,                    finance.STK_XR_XD.a_registration_date<=watch_date,                    finance.STK_XR_XD.code.in_(security[int(len(security)*0.3):int(len(security)*0.6)]))
    q3=query(finance.STK_XR_XD.a_registration_date,finance.STK_XR_XD.bonus_amount_rmb,            finance.STK_XR_XD.code           ).filter(finance.STK_XR_XD.a_registration_date>= one_year_ago,                    finance.STK_XR_XD.a_registration_date<=watch_date,                    finance.STK_XR_XD.code.in_(security[int(len(security)*0.6):]))
    
    
    df_data1=finance.run_query(q1)
    df_data2=finance.run_query(q2)
    df_data3=finance.run_query(q3)
    df_data=pd.concat([df_data1,df_data2,df_data3],axis=0,sort=False)
    df_data.fillna(0,inplace=True)
    
    df_data=df_data.set_index('code')
    df_data=df_data.groupby('code').sum()
    
    #获取市值相关数据
    q01=query(valuation.code,valuation.market