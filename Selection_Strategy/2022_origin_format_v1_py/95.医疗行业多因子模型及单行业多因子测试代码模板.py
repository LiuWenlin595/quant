# 克隆自聚宽文章：https://www.joinquant.com/post/16766
# 标题：医疗行业多因子模型及单行业多因子测试代码模板
# 作者：Alfred_YY

# 导入函数库
import time
import math
from datetime import datetime,timedelta
import jqdata
from jqdata import finance
import numpy as np
import pandas as pd
import math
from statsmodels import regression
import statsmodels.api as sm
from jqfactor import get_factor_values
import datetime
from scipy import stats
from jqfactor import winsorize_med
from jqfactor import neutralize
from jqfactor import standardlize
from six import StringIO

'''
====================================================
配套函数设置区
====================================================
'''
def get_all_data():
    csv = read_file('医疗IC.csv')
    frame = pd.read_csv(StringIO(csv))
    frame.index = frame['code']
    index = g.factor[:]
    index.extend(['code','date','pct'])
    frame = frame.loc[:,index].copy()
    g.pool = list(set(list(frame['code'])))
    g.trade_day = list(set(list(frame['date'])))
    g.trade_day.sort()
    #frame.set_index(["date","code"],append=False,drop=True,inplace=True)
    g.factor_data = frame

#获取股票池
def get_stock(industry,date):
    #这里可以设定选择的行业板块
    stock_list = get_industry_stocks(industry_code = industry,date=date)
    return stock_list

def tradedays_before(date,count):
    date = get_price('000001.XSHG',end_date=date,count=count+1).index[0]
    return date

#获取时间为date的全部因子数据
def get_factor_data(stock,date):
    data_1=pd.DataFrame(index=stock)
    q = query(valuation,balance,cash_flow,income,indicator).filter(valuation.code.in_(stock))
    df = get_fundamentals(q, date)
    df['market_cap']=df['market_cap']*100000000
    factor_data_1=get_factor_values(stock,['roe_ttm','roa_ttm','total_asset_turnover_rate',\
                               'net_operate_cash_flow_ttm','net_profit_ttm','net_profit_ratio',\
                              'cash_to_current_liability','current_ratio',\
                             'gross_income_ratio','non_recurring_gain_loss',\
                            'operating_revenue_ttm','net_profit_growth_rate',\
                            'total_asset_growth_rate','net_asset_growth_rate',\
                            'long_debt_to_working_capital_ratio','net_operate_cash_flow_to_net_debt',\
                            'net_operate_cash_flow_to_total_liability'],end_date=date,count=1)
    factor=pd.DataFrame(index=stock)
    for i in factor_data_1.keys():
        factor[i]=factor_data_1[i].iloc[0,:]
    df.index = df['code']
    data_1['code'] = df['code']
    del df['code'],df['id']
    #合并得大表
    df=pd.concat([df,factor],axis=1)
    #PE值
    data_1['pe_ratio']=df['pe_ratio']
    #PB值
    data_1['pb_ratio']=df['pb_ratio']
    #总市值
    data_1['size']=df['market_cap']
    #总市值取对数
    data_1['size_lg']=np.log(df['market_cap'])
    #净利润(TTM)/总市值
    data_1['EP']=df['net_profit_ttm']/df['market_cap']
    #净资产/总市值
    data_1['BP']=1/df['pb_ratio']
    #营业收入(TTM)/总市值
    data_1['SP']=1/df['ps_ratio']
    #净现金流(TTM)/总市值
    data_1['NCFP']=1/df['pcf_ratio']
    #经营性现金流(TTM)/总市值
    data_1['OCFP']=df['net_operate_cash_flow_ttm']/df['market_cap']
    #经营性现金流量净额/净收益
    data_1['ocf_to_operating_profit']=df['ocf_to_operating_profit']
    #经营性现金流量净额/营业收入
    data_1['ocf_to_revenue']=df['ocf_to_revenue']
    #净利润同比增长率
    data_1['net_g'] = df['net_profit_growth_rate']
    #净利润(TTM)同比增长率/PE_TTM
    data_1['G/PE']=df['net_profit_growth_rate']/df['pe_ratio']
    #ROE_ttm
    data_1['roe_ttm']=df['roe_ttm']
    #ROE_YTD
    data_1['roe_q']=df['roe']
    #ROA_ttm
    data_1['roa_ttm']=df['roa_ttm']
    #ROA_YTD
    data_1['roa_q']=df['roa']
    #净利率
    data_1['netprofitratio_ttm'] = df['net_profit_ratio']
    #毛利率TTM
    data_1['grossprofitmargin_ttm']=df['gross_income_ratio']
    #毛利率YTD
    data_1['grossprofitmargin_q']=df['gross_profit_margin']
    #销售净利率TTM
    data_1['net_profit_margin']=df['net_profit_margin']
    #净利润同比增长率
    data_1['inc_net_profit_year_on_year']=df['inc_net_profit_year_on_year']
    #营业收入同比增长率
    data_1['inc_revenue_year_on_year']=df['inc_revenue_year_on_year']
    #营业利润/营业总收入
    data_1['operation_profit_to_total_revenue']=df['operation_profit_to_total_revenue']
    #扣除非经常性损益后净利润率YTD
    data_1['profitmargin_q']=df['adjusted_profit']/df['operating_revenue']
    #资产周转率TTM
    data_1['assetturnover_ttm']=df['total_asset_turnover_rate']
    #总资产周转率YTD 营业收入/总资产
    data_1['assetturnover_q']=df['operating_revenue']/df['total_assets']
    #经营性现金流/净利润TTM
    data_1['operationcashflowratio_ttm']=df['net_operate_cash_flow_ttm']/df['net_profit_ttm']
    #经营性现金流/净利润YTD
    data_1['operationcashflowratio_q']=df['net_operate_cash_flow']/df['net_profit']
    #经营性现金流/营业收入
    data_1['operationcashflow_revenue']=df['net_operate_cash_flow_ttm']/df['operating_revenue']
    #净资产
    df['net_assets']=df['total_assets']-df['total_liability']
    #总资产/净资产
    data_1['financial_leverage']=df['total_assets']/df['net_assets']
    #非流动负债/净资产
    data_1['debtequityratio']=df['total_non_current_liability']/df['net_assets']
    #现金比率=(货币资金+有价证券)÷流动负债
    data_1['cashratio']=df['cash_to_current_liability']
    #流动比率=流动资产/流动负债*100%
    data_1['currentratio']=df['current_ratio']
    #现金流动负债率
    data_1['net_operate_cash_flow_to_net_debt']=df['net_operate_cash_flow_to_net_debt']
    #现金负债率
    data_1['net_operate_cash_flow_to_total_liability']=df['net_operate_cash_flow_to_total_liability']
    #长期负债与营运现金比率
    data_1['long_debt_to_working_capital_ratio']=df['long_debt_to_working_capital_ratio']
    #总资产增长率
    data_1['total_asset_growth_rate']=df['total_asset_growth_rate']
    #净资产增长率
    data_1['net_asset_growth_rate']=df['net_asset_growth_rate']
    #总市值取对数
    data_1['ln_capital']=np.log(df['market_cap'])
    #TTM所需时间
    his_date = [pd.to_datetime(date) - datetime.timedelta(90*i) for i in range(0, 4)]
    tmp = pd.DataFrame()
    tmp['code']=list(stock)
    for i in his_date:
        tmp_adjusted_dividend = get_fundamentals(query(indicator.code, indicator.adjusted_profit, \
                                                     cash_flow.dividend_interest_payment).
                                               filter(indicator.code.in_(stock)), date = i)
        tmp=pd.merge(tmp,tmp_adjusted_dividend,how='outer',on='code')

        tmp=tmp.rename(columns={'adjusted_profit':'adjusted_profit'+str(i.month), \
                                'dividend_interest_payment':'dividend_interest_payment'+str(i.month)})
    tmp=tmp.set_index('code')
    tmp_columns=tmp.columns.values.tolist()
    tmp_adjusted=sum(tmp[[i for i in tmp_columns if 'adjusted_profit'in i ]],1)
    tmp_dividend=sum(tmp[[i for i in tmp_columns if 'dividend_interest_payment'in i ]],1)
    #扣除非经常性损益后净利润(TTM)/总市值
    data_1['EPcut']=tmp_adjusted/df['market_cap']
    #近12个月现金红利(按除息日计)/总市值
    data_1['DP