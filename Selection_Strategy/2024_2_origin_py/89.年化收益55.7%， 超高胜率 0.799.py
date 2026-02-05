# 克隆自聚宽文章：https://www.joinquant.com/post/37957
# 标题：年化收益55.7%， 超高胜率 0.799！
# 作者：Ethan.Liu

import numpy as np
import pandas
import scipy as sp
import scipy.optimize
import datetime as dt
import talib
from prettytable import PrettyTable
from scipy import linalg as sla
from scipy import spatial
from jqdata import *
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import statsmodels.api as sm
from jqlib.technical_analysis import *

def initialize(context):
    #用沪深 300 做回报基准
    set_benchmark('000300.XSHG')
    # 滑点、真实价格
    #set_slippage(FixedSlippage(0.000))
    set_option('use_real_price', True)

    # 关闭部分log
    log.set_level('order', 'error')
    after_code_changed(context)
    run_daily(fun_main, '10:50')
    

def after_trading_end(context):
    g.quantlib.get_portfolio_info_text(context)
    g.quantlib.reset_param(context)
    g.quantlib.fun_set_var(context, 'op_buy_stocks', [])
    if  context.curve_protect_days == 0:
        print('追加收益:{}'.format(context.portfolio.total_value))
        context.value_list.append(context.portfolio.total_value)



def after_code_changed(context):

    # 变量都挪到 after_code_changed 里
    g.quantlib = quantlib()
    # 策略起停标志位
    
    g.quantlib.fun_set_var(context, 'algo_enable', True)
    # 定义风险敞口
    g.quantlib.fun_set_var(context, 'riskExposure', 0.03)
    # 正态分布概率表，标准差倍数以及置信率
    # 1.96, 95%; 2.06, 96%; 2.18, 97%; 2.34, 98%; 2.58, 99%; 5, 99.9999%
    g.quantlib.fun_set_var(context, 'confidencelevel', 1.96)
    # 调仓参数
    g.quantlib.fun_set_var(context, 'hold_cycle', 20)
    g.quantlib.fun_set_var(context, 'hold_periods', 0)
    g.quantlib.fun_set_var(context, 'stock_list', [])
    g.quantlib.fun_set_var(context, 'position_price', {})
    g.quantlib.fun_set_var(context, 'recal_periods', 0)
    g.quantlib.fun_set_var(context, 'version', 1.0)
    
    g.quantlib.fun_set_var(context, 'stock_num', 10)
    
    g.quantlib.fun_set_var(context, 'op_buy_stocks', [])
    g.quantlib.fun_set_var(context, 'index2', '000016.XSHG')  # 上证50指数
    g.quantlib.fun_set_var(context, 'index8', '399333.XSHE')  # 中小板R指数
    g.quantlib.fun_set_var(context, 'index_growth_rate', 0.01)
    
    g.quantlib.fun_set_var(context, 'is_day_curve_protect', False)
    g.quantlib.fun_set_var(context, 'curve_protect_days', 0)
    g.quantlib.fun_set_var(context, 'value_list', [])
    

    if context.version < 1.0:
        context.hold_periods = 0
        context.riskExposure = 0.03
        context.version = 1.0



def before_trading_start(context):
    # 定义股票池
    pass

#def handle_data(context, data):
#    if not context.is_day_curve_protect:
#        if g.quantlib.equity_curve_protect(context):
#            g.quantlib.clear_position(context)
#            del context.value_list[:]
    

def fun_main(context):

    # 引用 lib
    g.value_factor = value_factor_lib()
    
    #print(g.lowPEG.fun_cal_stock_PEG(context))
    g.quantlib     = quantlib()
    context.msg    = ""

    # 止损
    #print(g.quantlib.stock_clean_by_mom(context))
    #print(context.pe_ratio_median>90)
    #if context.curve_protect_days<>0:
    #    if context.pe_ratio_median<70:
    #        context.curve_protect_days +=1
    #    return 0
    g.quantlib.get_pe_median(context)    
    if g.quantlib.stock_clean_by_mom(context) and  context.pe_ratio_median>80:
        g.quantlib.clear_position(context)
        return 0
        
    moneyfund = ['511880.XSHG','511010.XSHG','511220.XSHG']
    # 上市不足 60 天的剔除掉
    
    context.moneyfund = g.quantlib.fun_delNewShare(context, moneyfund, 60)
    
    
    # 检查是否需要调仓
    rebalance_flag, context.position_price, context.hold_periods, msg = \
            g.quantlib.fun_needRebalance(context,'algo-maxcap', context.moneyfund, context.stock_list, context.position_price, \
                context.hold_periods, context.hold_cycle, 0.25)
    
    context.msg += msg
    
    statsDate = context.current_dt.date() - dt.timedelta(1)
    
    
    
    #context.algo_enable, context.recal_periods, rebalance_flag = g.quantlib.fun_check_algo(context.algo_enable, context.recal_periods, rebalance_flag, statsDate)
    log.info(rebalance_flag)
    trade_style = False    # True 会交易进行类似 100股的买卖，False 则只有在仓位变动 >25% 的时候，才产生交易
    if rebalance_flag:
        stock_list = []
        if context.algo_enable:
            #获取坏股票列表，将会剔除
            bad_stock_list = g.quantlib.fun_get_bad_stock_list(statsDate)
            # 低估值策略
            value_factor_stock_list = g.value_factor.fun_get_stock_list(context, context.stock_num, statsDate, bad_stock_list)
            stock_list = value_factor_stock_list

        # 分配仓位
        equity_ratio, bonds_ratio = g.quantlib.fun_assetAllocationSystem(stock_list, context.moneyfund, context.confidencelevel, statsDate)

        risk_ratio = 0
        if len(equity_ratio.keys()) >= 1:
            risk_ratio = context.riskExposure / len(equity_ratio.keys())

        # 分配头寸，根据预设的风险敞口，计算交易时的比例
        position_ratio = g.quantlib.fun_calPosition(equity_ratio, bonds_ratio, 1.0, risk_ratio, context.moneyfund, context.portfolio.portfolio_value, context.confidencelevel, statsDate)
        trade_style = True
        context.stock_list = position_ratio.keys()

        # 更新待购价格
        context.position_price = g.quantlib.fun_update_positions_price(position_ratio)
        # 卖掉已有且不在待购清单里的股票
        for stock in context.portfolio.positions.keys():
            if stock not in position_ratio:
                position_ratio[stock] = 0
        context.position_ratio = position_ratio

        # 调仓，执行交易
        g.quantlib.fun_do_trade(context, context.position_ratio, context.moneyfund, trade_style)
    log.info(context.msg)
class value_factor_lib():
    
        
    def fun_get_stock_list(self, context, hold_number, statsDate=None, bad_stock_list=[]):
        
        #low_ps = self.fun_get_low_ps(context, statsDate)
        
        # 去行业数据
        industry_list = g.quantlib.fun_get_industry(cycle=None)
        max_stock = []
        for industry in industry_list:
            
            stock_list = g.quantlib.fun_get_industry_stocks(industry, 2, statsDate)
            if len(stock_list)>5:
                df = get_fundamentals(query(valuation.code).filter(valuation.code.in_(stock_list)).order_by(valuation.market_cap.desc()).limit(1), date = statsDate)
                max_stock = max_stock + list(df.code)
        print max_stock
            
        #max_stock = list(set(max_stock) & set(low_ps))
        
        
        q = query(indicator.code).filter(indicator.code.in_(max_stock)).order_by(indicator.roe.desc())
        
        stock_list = list(get_fundamentals(q).code)
       
  
        positions_list = context.portfolio.positions.keys()
        stock_list = g.quantlib.unpaused(stock_list, positions_list)
        stock_list = g.quantlib.remove_st(stock_list, statsDate)
        stock_list = g.quantlib.fun_delNewShare(context, stock_list, 80)
        
        #stock_list = stock_list[:hold_number*10]
        stock_list = g.quantlib.remove_bad_stocks(stock_list, bad_stock_list)
        stock_list = g.quantlib.remove_limit_up(stock_list, positions_list)
        
        
        #if hold_number>5:
        #    stock_list = g.quantlib.fun_diversity_by_industry(stockpool, 2, statsDate)
        #elif hold_number>1 and hold_number<=5:
        #    stock_list = g.quantlib.fun_diversity_by_industry(stockpool, 1, statsDate)
        
        
            
        
        print stock_list
        return stock_list[:hold_number]


    



class quantlib():
    def get_fundamentals_sum(self, table_name=indicator, search=indicator.adjusted_profit, statsDate=None):
        # 取最近的五个季度财报的日期
        def __get_quarter(table_name, statsDate):
            '''
            返回最近 n 个财报的日期
            返回每个股票最近一个财报的日期
            '''
            # 取最新一季度的统计日期
            if table_name == 'indicator':
                q = query(indicator.code, indicator.statDate)
            elif table_name == 'income':
                q = query(income.code, income.statDate)
            elif table_name == 'cash_flow':
                q = query(cash_flow.code, cash_flow.statDate)
            elif table_name == 'balance':
                q = query(balance.code, balance.statDate)

            df = get_fundamentals(q, date = statsDate)
            stock_last_statDate = {}
            tmpDict = df.to_dict()
            for i in range(len(tmpDict['statDate'].keys())):
                # 取得每个股票的代码，以及最新的财报发布日
                stock_last_statDate[tmpDict['code'][i]] = tmpDict['statDate'][i]

            df = df.sort(columns='statDate', ascending=False)
            # 取得最新的财报日期
            last_statDate = df.iloc[0,1]

            this_year = int(str(last_statDate)[0:4])
            this_month = str(last_statDate)[5:7]

            if this_month == '12':
                last_quarter       = str(this_year)     + 'q4'
                last_two_quarter   = str(this_year)     + 'q3'
                last_three_quarter = str(this_year)     + 'q2'
                last_four_quarter  = str(this_year)     + 'q1'
                last_five_quarter  = str(this_year - 1) + 'q4'

            elif this_month == '09':
                last_quarter       = str(this_year)     + 'q3'
                last_two_quarter   = str(this_year)     + 'q2'
                last_three_quarter = str(this_year)     + 'q1'
                last_four_quarter  = str(this_year - 1) + 'q4'
                last_five_quarter  = str(this_year - 1) + 'q3'

            elif this_month == '06':
                last_quarter       = str(this_year)     + 'q2'
                last_two_quarter   = str(this_year)     + 'q1'
                last_three_quarter =