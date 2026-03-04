#!/usr/bin/env python
# coding: utf-8

# 量化排雷

from jqdata import *
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
import time
import datetime
import math
import warnings
#用来正常显示中文标签
mpl.rcParams['font.sans-serif']=['SimHei'] 
#用来正常显示负号
mpl.rcParams['axes.unicode_minus']=False 
warnings.filterwarnings('ignore') 


#获取属性所在的表格
def params(param):
    valuation=['code','day','capitalization','circulating_cap','market_cap','circulating_market_cap','turnover_ratio',
               'pe_ratio','pe_ratio_lyr','pb_ratio','ps_ratio','pcf_ratio']
    balance=['code','pubDate','statDate','cash_equivalents','settlement_provi','lend_capital','trading_assets','bill_receivable','account_receivable',
             'advance_payment','insurance_receivables','reinsurance_receivables','reinsurance_contract_reserves_receivable','interest_receivable',
             'dividend_receivable','other_receivable','bought_sellback_assets','inventories','non_current_asset_in_one_year','other_current_assets',
             'total_current_assets','loan_and_advance','hold_for_sale_assets','hold_to_maturity_investments','longterm_receivable_account',
             'longterm_equity_invest','investment_property','fixed_assets','constru_in_process','construction_materials','fixed_assets_liquidation',
             'biological_assets','oil_gas_assets','intangible_assets','development_expenditure','good_will','long_deferred_expense','deferred_tax_assets',
             'other_non_current_assets','total_non_current_assets','total_assets','shortterm_loan','borrowing_from_centralbank','deposit_in_interbank',
             'borrowing_capital','trading_liability','notes_payable','accounts_payable','advance_peceipts','sold_buyback_secu_proceeds','commission_payable',
             'salaries_payable','taxs_payable','interest_payable','dividend_payable','other_payable','reinsurance_payables','insurance_contract_reserves',
             'proxy_secu_proceeds','receivings_from_vicariously_sold_securities','non_current_liability_in_one_year','other_current_liability','total_current_liability',
             'longterm_loan','bonds_payable','longterm_account_payable','specific_account_payable','estimate_liability','deferred_tax_liability',
             'other_non_current_liability','total_non_current_liability','total_liability','paidin_capital','capital_reserve_fund','treasury_stock',
             'specific_reserves','surplus_reserve_fund','ordinary_risk_reserve_fund','retained_profit','foreign_currency_report_conv_diff',
             'equities_parent_company_owners','minority_interests','total_owner_equities','total_sheet_owner_equities']
    cash_flow=['code','pubDate','statDate','goods_sale_and_service_render_cash','net_deposit_increase','net_borrowing_from_central_bank',
               'net_borrowing_from_finance_co','net_original_insurance_cash','net_cash_received_from_reinsurance_business',
               'net_insurer_deposit_investment','net_deal_trading_assets','interest_and_commission_cashin','net_increase_in_placements',
               'net_buyback','tax_levy_refund','other_cashin_related_operate','subtotal_operate_cash_inflow','goods_and_services_cash_paid',
               'net_loan_and_advance_increase','net_deposit_in_cb_and_ib','original_compensation_paid','handling_charges_and_commission',
               'policy_dividend_cash_paid','staff_behalf_paid','tax_payments','other_operate_cash_paid','subtotal_operate_cash_outflow',
               'net_operate_cash_flow','invest_withdrawal_cash','invest_proceeds','fix_intan_other_asset_dispo_cash','net_cash_deal_subcompany',
               'other_cash_from_invest_act','subtotal_invest_cash_inflow','fix_intan_other_asset_acqui_cash','invest_cash_paid',
               'impawned_loan_net_increase','net_cash_from_sub_company','other_cash_to_invest_act','subtotal_invest_cash_outflow',
               'net_invest_cash_flow','cash_from_invest','cash_from_mino_s_invest_sub','cash_from_borrowing','cash_from_bonds_issue',
               'other_finance_act_cash','subtotal_finance_cash_inflow','borrowing_repayment','dividend_interest_payment','proceeds_from_sub_to_mino_s',
               'other_finance_act_payment','subtotal_finance_cash_outflow','net_finance_cash_flow','exchange_rate_change_effect',
               'cash_equivalent_increase','cash_equivalents_at_beginning','cash_and_equivalents_at_end']
    income=['code','pubDate','statDate','total_operating_revenue','operating_revenue','interest_income','premiums_earned',
            'commission_income','total_operating_cost','operating_cost','interest_expense','commission_expense','refunded_premiums',
            'net_pay_insurance_claims','withdraw_insurance_contract_reserve','policy_dividend_payout','reinsurance_cost','operating_tax_surcharges',
            'sale_expense','administration_expense','financial_expense','asset_impairment_loss','fair_value_variable_income','investment_income',
            'invest_income_associates','exchange_income','operating_profit','non_operating_revenue','non_operating_expense','disposal_loss_non_current_liability',
            'total_profit','income_tax_expense','net_profit','np_parent_company_owners','minority_profit','basic_eps','diluted_eps',
            'other_composite_income','total_composite_income','ci_parent_company_owners','ci_minority_owners']
    indicator=['code','pubDate','statDate','eps','adjusted_profit','operating_profit','value_change_profit','roe','inc_return',
               'roa','net_profit_margin','gross_profit_margin','expense_to_total_revenue','operation_profit_to_total_revenue',
               'net_profit_to_total_revenue','operating_expense_to_total_revenue','ga_expense_to_total_revenue','financing_expense_to_total_revenue',
               'operating_profit_to_profit','invesment_profit_to_profit','adjusted_profit_to_profit','goods_sale_and_service_to_revenue',
               'ocf_to_revenue','ocf_to_operating_profit','inc_total_revenue_year_on_year','inc_total_revenue_annual','inc_revenue_year_on_year',
               'inc_revenue_annual','inc_operation_profit_year_on_year','inc_operation_profit_annual','inc_net_profit_year_on_year','inc_net_profit_annual',
               'inc_net_profit_to_shareholders_year_on_year','inc_net_profit_to_shareholders_annual']
    if param in valuation:
        tab='valuation.'+param
    elif param in balance:
        tab='balance.'+param
    elif param in cash_flow:
        tab='cash_flow.'+param
    elif param in income:
        tab='income.'+param
    elif param in indicator:
        tab='indicator.'+param
    return tab


def statDate(date=None,num=1):
    # date:格式%Y-%m-%d,把str时间处理成time格式
# freq:'q'表现查询季报，‘y’表示查询年报
# num:获取的日期数
    if date:
        tt=time.strptime(date,"%Y-%m-%d")
    else:
        tt=time.localtime()
    a1=tt.tm_year-1
    if tt.tm_mon<5:
        loc_y=[str(a1-i) for i in range(1,num+1)]
    else:
        loc_y=[str(a1-i) for i in range(num)]
    return loc_y


#占比函数，param1/param2
def Proportion(code,param1,param2,date=None):
    tt=statDate(date=date,num=1)[0]
    tab1=params(param1)
    tab2=params(param2)
    df=get_fundamentals(query(valuation.code
                              ,valuation.day
                              ,valuation.capitalization
                              ,eval(tab1)#‘eval’把字符串转为可执行代码
                              ,eval(tab2)
                             ).filter(
        valuation.code==code
        ),statDate=tt)
    rece_r=df.loc[0,param1]/df.loc[0,param2]
    return rece_r
code='000005.XSHE'
Proportion(code,'account_receivable','operating_revenue',date=None)


#占比变动率
def Rate_of_change(code,param1,param2,date=None):
    tt=statDate(date=date,num=2)
    tab1=params(param1)
    tab2=params(param2)
    df1=get_fundamentals(query(valuation.code
                              ,valuation.day
                              ,valuation.capitalization
                              ,eval(tab1)#‘eval’把字符串转为可执行代码
                              ,eval(tab2)
                             ).filter(
        valuation.code==code
        ),statDate=tt[0])
    df2=get_fundamentals(query(valuation.code
                              ,valuation.day
                              ,valuation.capitalization
                              ,eval(tab1)#‘eval’把字符串转为可执行代码
                              ,eval(tab2)
                             ).filter(
        valuation.code==code
        ),statDate=tt[1])
    df=df1.append(df2,ignore_index=True)
    df['ratio']=df[param1]/df[param2]
    cha=df.loc[0,'ratio']/df.loc[1,'ratio']-1
    return cha
Rate_of_change(code,'account_receivable','total_sheet_owner_equities',date=None) 


# （