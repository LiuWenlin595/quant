#!/usr/bin/env python
# coding: utf-8

# 第一模块 数据准备

import pandas as pd
import numpy as np
import time
import datetime
import statsmodels.api as sm
import pickle
import warnings
from jqdata import *
warnings.filterwarnings('ignore')


# 此代码在自己机器上运行时使用，在聚宽平台上跑数据不需要
# from jqdatasdk import *
# auth('用户名','密码')



start_date = '2013-01-01'
end_date = '2014-01-01'


all_trade_days = (get_trade_days(start_date=start_date,end_date=end_date)).tolist() #所有交易日
trade_days = all_trade_days[::20] #每隔20天取一次数据，基本面数据更新频率较慢，数据获取频率尽量与之对应

securities = get_all_securities()
start_data_dt = datetime.datetime.strptime(start_date,'%Y-%m-%d').date()
securities_after_start_date = securities[(securities['start_date']<start_data_dt)] #选择起始时间之前上市的股票
all_stocks = list(securities_after_start_date.index)

INDUSTRY_NAME = 'sw_l1'

ttm_factors = []


# 基本面数据及缺失值填充函数


'''
基本面因子映射
'''
fac_dict = {
    'MC':valuation.market_cap, # 总市值
    'GP':indicator.gross_profit_margin * income.operating_revenue, # 毛利润
    'OP':income.operating_profit,
    'OR':income.operating_revenue, # 营业收入
    'NP':income.net_profit, # 净利润
    'EV':valuation.market_cap + balance.shortterm_loan+balance.non_current_liability_in_one_year+balance.longterm_loan+balance.bonds_payable+balance.longterm_account_payable - cash_flow.cash_and_equivalents_at_end,
    
    'TOE':balance.total_owner_equities, # 股东权益合计(元)
    'TOR':income.total_operating_revenue, # 营业总收入
    'EBIT':income.net_profit+income.financial_expense+income.income_tax_expense,
    
    'TOC':income.total_operating_cost,#营业总成本
    'NOCF/MC':cash_flow.net_operate_cash_flow / valuation.market_cap, #经营活动产生的现金流量净额/总市值
    'OTR':indicator.ocf_to_revenue, #经营活动产生的现金流量净额/营业收入(%) 
    
    
    'GPOA':indicator.gross_profit_margin * income.operating_revenue / balance.total_assets,  #毛利润 / 总资产 = 毛利率*营业收入 / 总资产
    'GPM':indicator.gross_profit_margin, # 毛利率
    'OPM':income.operating_profit / income.operating_revenue, #营业利润率
    'NPM':indicator.net_profit_margin, # 净利率
    'ROA':indicator.roa, # ROA
    'ROE':indicator.roe, # ROE
    'INC':indicator.inc_return, # 净资产收益率(扣除非经常损益)(%)
    'EPS':indicator.eps, # 净资产收益率(扣除非经常损益)(%)
    'AP':indicator.adjusted_profit, # 扣除非经常损益后的净利润(元)
    'OP':indicator.operating_profit, # 经营活动净收益(元)
    'VCP':indicator.value_change_profit, # 价值变动净收益(元) = 公允价值变动净收益+投资净收益+汇兑净收益
    
    'ETTR':indicator.expense_to_total_revenue, # 营业总成本/营业总收入(%)
    'OPTTR':indicator.operation_profit_to_total_revenue, # 营业利润/营业总收入(%)
    'NPTTR':indicator.net_profit_to_total_revenue, # 净利润/营业总收入(%)
    'OETTR':indicator.operating_expense_to_total_revenue, # 营业费用/营业总收入
    'GETTR':indicator.ga_expense_to_total_revenue, # 管理费用/营业总收入(%)
    'FETTR':indicator.financing_expense_to_total_revenue, # 财务费用/营业总收入(%)	
    
    'OPTP':indicator.operating_profit_to_profit, # 经营活动净收益/利润总额(%)
    'IPTP':indicator.invesment_profit_to_profit, # 价值变动净收益/利润总额(%)
    'GSASTR':indicator.goods_sale_and_service_to_revenue, # 销售商品提供劳务收到的现金/营业收入(%)
    'OTR':indicator.ocf_to_revenue, # 经营活动产生的现金流量净额/营业收入(%)
    'OTOP':indicator.ocf_to_operating_profit, # 经营活动产生的现金流量净额/经营活动净收益(%)
    
    'ITRYOY':indicator.inc_total_revenue_year_on_year, # 营业总收入同比增长率(%)
    'ITRA':indicator.inc_total_revenue_annual, # 营业总收入环比增长率(%)
    'IRYOY':indicator.inc_revenue_year_on_year, # 营业收入同比增长率(%)
    'IRA':indicator.inc_revenue_annual, # 营业收入环比增长率(%)
    'IOPYOY':indicator.inc_operation_profit_year_on_year, # 营业利润同比增长率(%)
    'IOPA':indicator.inc_operation_profit_annual, # 营业利润环比增长率(%)
    'INPYOY':indicator.inc_net_profit_year_on_year, # 净利润同比增长率(%)
    'INPA':indicator.inc_net_profit_annual, # 净利润环比增长率(%)
    'INPTSYOY':indicator.inc_net_profit_to_shareholders_year_on_year, # 归属母公司股东的净利润同比增长率(%)
    'INPTSA':indicator.inc_net_profit_to_shareholders_annual, # 归属母公司股东的净利润环比增长率(%)
    'INPTSA':indicator.inc_net_profit_to_shareholders_annual, # 归属母公司股东的净利润环比增长率(%)
    
    
    'ROIC':(income.net_profit+income.financial_expense+income.income_tax_expense)/(balance.total_owner_equities+balance.shortterm_loan+balance.non_current_liability_in_one_year+balance.longterm_loan+balance.bonds_payable+balance.longterm_account_payable),
    'OPTT':income.operating_profit / income.total_profit, # 营业利润占比
    'TP/TOR':income.total_profit / income.total_operating_revenue, #利润总额/营业总收入
    'OP/TOR':income.operating_profit / income.total_operating_revenue,
    'NP/TOR':income.net_profit / income.total_operating_revenue,

    'NP':income.net_profit, # 净利润
    
    'TA':balance.total_assets, # 总资产

    'DER':balance.total_liability / balance.equities_parent_company_owners, # 产权比率 = 负债合计/归属母公司所有者权益合计
    'FCFF/TNCL':(cash_flow.net_operate_cash_flow - cash_flow.net_invest_cash_flow) / balance.total_non_current_liability, #自由现金流比非流动负债
    'NOCF/TL': cash_flow.net_operate_cash_flow / balance.total_liability, # 经营活动产生的现金流量净额/负债合计
    'TCA/TCL':balance.total_current_assets / balance.total_current_liability, # 流动比率

    'PE':valuation.pe_ratio, # PE 市盈率
    'PB':valuation.pb_ratio, # PB 市净率
    'PR':valuation.pcf_ratio, # PR 市现率
    'PS':valuation.ps_ratio, # PS 市销率
    
    'TOR/TA':income.total_operating_revenue / balance.total_assets, #总资产周转率
    'TOR/FA':income.total_operating_revenue / balance.fixed_assets, #固定资产周转率
    'TOR/TCA':income.total_operating_revenue / balance.total_current_assets, #流动资产周转率
    'LTL/OC':balance.longterm_loan / income.operating_cost, #长期借款/营业成本
    
    'TL/TA':balance.total_liability / balance.total_assets, #总资产/总负债
    'TL/TOE':balance.total_liability / balance.total_owner_equities,#负债权益比
    
    }

adjust_factors = {
    'TOR/TA':income.total_operating_revenue / balance.total_assets, #总资产周转率
    'TOR/FA':income.total_operating_revenue / balance.fixed_assets, #固定资产周转率
    'TOR/TCA':income.total_operating_revenue / balance.total_current_assets, #流动资产周转率
    'LTL/OC':balance.longterm_loan / income.operating_cost, #长期借款/营业成本
    
    'TL/TA':balance.total_liability / balance.total_assets, #总资产/总负债
    'TL/TOE':balance.total_liability / balance.total_owner_equities,#负债权益比
    
    'DER':balance.total_liability / balance.equities_parent_company_owners, # 产权比率 = 负债合计/归属母公司所有者权益合计
    'FCFF/TNCL':(cash_flow.net_operate_cash_flow - cash_flow.net_invest