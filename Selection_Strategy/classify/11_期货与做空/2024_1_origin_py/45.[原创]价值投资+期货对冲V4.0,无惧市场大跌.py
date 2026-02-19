# 克隆自聚宽文章：https://www.joinquant.com/post/42256
# 标题：[原创]价值投资+期货对冲V4.0,无惧市场大跌
# 作者：Eddie79163

# 引入库函数
import numpy as np
import pandas as pd
import datetime as dt
from jqdata import *
# 导入函数库
#from jqdata import *
from jqlib.technical_analysis  import *
#import pandas as pd
from jqfactor import get_factor_values
import numpy as np
import warnings

def initialize(context):
    # 设置系统
    set_option('use_real_price', True)
    set_option("avoid_future_data", True)
    g.benchmark = '000905.XSHG'
    set_benchmark(g.benchmark)
    # 设置信息格式
    log.set_level('order', 'error')
    pd.set_option('display.max_rows', 100)
    pd.set_option('display.max_columns', 10)
    pd.set_option('display.width', 500)
    
    
    #设置初始账户资金分配
    g.stock_share = 0.7#指增子账户占总账户资金比例
    g.future_share = 0.3#期货子账户占总账户资金比例
    g.future_position = 0.35 #期货持仓所需保证金占用的期货子账户资金比例
    set_subportfolios([SubPortfolioConfig(cash=context.portfolio.starting_cash * g.stock_share, type='stock'),
                       SubPortfolioConfig(cash=context.portfolio.starting_cash * g.future_share, type='futures')])
    
    
    # 设置策略
    run_daily(handle_trader,time='13:45')# weekday=1,,force=True) #weekday=1,
    # 设置参数
    g.index = '399317.XSHE' #投资指数
    g.num = 5 #选股数
    g.stocks = [] #股票池
    
    ### 期货相关设定 ###~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    g.future_type = 'IC'
    g.futures_margin_rate = 0.15#保证金比例(现在好像是14%，懒得改了)
    g.unitprice = 200 
    g.long_days = 5 # 几日均线以下开空
    g.short_days = 2 # 几日以上均线开多
    
    #ATR止损模块参数
    g.ATRdays = 20 #计算ATR的时间区间长度
    g.boundrydays  = 5#计算最高最低价格的区间长度
    g.stop = 5 # ATR止损倍数
    
    #根据短期ATR和长期ATR的差确定波动率volatility。如果 短ATR-para*长ATR，表明即将变盘，可适当仓位重
    g.shortdays = 20
    g.longdays = 50
    g.para = 1
    
    # 期货类每笔交易时的手续费是：买入时万分之0.23,卖出时万分之0.23,平今仓为万分之0.23
    set_order_cost(OrderCost(open_commission=0.000023, close_commission=0.000023,close_today_commission=0.0023), type='index_futures')
    # 设定保证金比例
    set_option('futures_margin_rate', g.futures_margin_rate)
    # 设置期货交易的滑点
    set_slippage(StepRelatedSlippage(2))

    # 设置样本序列长度、模型占位、拟合模型时间间隔、时间计数
    g.day = 20#每个月期货到期，20日为一个周期
    g.day_count = int(g.day)
    g.k = 1#初始交易期货手数
    ### 期货相关设定 ###~~~~~~~~~~~~~~~~~~~~~
    
    ### 期货交易运行 ###~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 开盘前运行
    run_daily( before_market_open_future, time='9:00', reference_security='IF8888.CCFX')
    # 开盘时运行
    #run_daily( market_trade_future, time='11:25', reference_security='IF8888.CCFX')
    
    #run_daily( market_trade_future, time='9:45', reference_security='IF8888.CCFX')
    #run_daily( market_trade_future, time='10:00', reference_security='IF8888.CCFX')
    #run_daily( market_trade_future, time='10:15', reference_security='IF8888.CCFX')
    #run_daily( market_trade_future, time='10:30', reference_security='IF8888.CCFX')
    #run_daily( market_trade_future, time='10:45', reference_security='IF8888.CCFX')
    #run_daily( market_trade_future, time='11:00', reference_security='IF8888.CCFX')
    run_daily( market_trade_future, time='11:15', reference_security='IF8888.CCFX')
    #run_daily( market_trade_future, time='13:00', reference_security='IF8888.CCFX')
    #run_daily( market_trade_future, time='13:15', reference_security='IF8888.CCFX')
    #run_daily( market_trade_future, time='13:30', reference_security='IF8888.CCFX')
    #run_daily( market_trade_future, time='13:45', reference_security='IF8888.CCFX')
    #run_daily( market_trade_future, time='14:00', reference_security='IF8888.CCFX')
    #run_daily( market_trade_future, time='14:15', reference_security='IF8888.CCFX')
    #run_daily( market_trade_future, time='14:30', reference_security='IF8888.CCFX')
    #run_daily( market_trade_future, time='14:45', reference_security='IF8888.CCFX')
    

    ### 期货交易运行 ###~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    

def handle_trader(context):
    # 按年更新
    if context.current_dt.month in [5]:
        g.stocks = choice_stocks(context, g.index, g.num)
    # 卖出
    cdata = get_current_data()
    for s in context.portfolio.positions:
        if s not in g.stocks and not cdata[s].paused:
            log.info('sell', s, cdata[s].name)
            order_target(s, 0)
    # 买进
    position = 0.99*context.portfolio.total_value / max(1, len(g.stocks))
    for s in g.stocks:
        if s not in context.portfolio.positions and not cdata[s].paused and\
            context.portfolio.available_cash > position:
            log.info('buy', s, cdata[s].name)
            order_value(s, position)

def choice_stocks(context, index, num):
    # 股票池
    stocks = get_index_stocks(index)
    #stocks = ['601288.XSHE','601988.XSHE','601328.XSHG','601398.XSHG','601658.XSHG','600016.XSHG','601939.XSHG','601818.XSHG']
    # 提取市值，基本面过滤
    sdf = get_fundamentals(query(
            valuation.code,
            valuation.market_cap, #单位，亿元
        ).filter(
            valuation.code.in_(stocks),
            valuation.pb_ratio <3,
            valuation.pb_ratio > 0.0,
            #indicator.gross_profit_margin>0,
            #indicator.pcf_ratio >0,
            indicator.roe>0.1,
            balance.cash_equivalents>0.4*balance.shortterm_loan,
            indicator.roa>0.05*indicator.roe,
            balance.total_assets/balance.total_liability>1,
            indicator.roa>0,
            valuation.pe_ratio > 0,
            valuation.ps_ratio > 0,
            #valuation.pe_ratio < 30,
            valuation.pcf_ratio > 0,
            indicator.inc_revenue_year_on_year >10,
            indicator.inc_net_profit_to_shareholders_year_on_year >10,
            #valuation.pb_ratio > 0.15*valuation.pe_ratio,#市净率
        )).dropna().set_index('code')
    stocks = list(sdf.index)
    #log.info('选股', stocks)
    # 最近三年的股息
    dt_3y = context.current_dt.date() - dt.timedelta(days=3*365)
    ddf = finance.run_query(query(
            finance.STK_XR_XD.code,
            finance.STK_XR_XD.company_name,
            finance.STK_XR_XD.board_plan_pub_date,
            finance.STK_XR_XD.bonus_amount_rmb, #单位，万元
        ).filter(
            finance.STK_XR_XD.code.in_(stocks),
            finance.STK_XR_XD.board_plan_pub_date > dt_3y,
            finance.STK_XR_XD.bonus_amount_rmb > 0
        )).dropna()
    stocks = list(set(ddf.code))
    # 累计分红
    divy = pd.Series(data=zeros(len(stocks)), index=stocks)
    for k in ddf.index:
        s = ddf.code[k]
        divy[s] += ddf.bonus_amount_rmb[k]
    # 建立数据表
    sdf = sdf.reindex(stocks)
    sdf['div_3y'] = divy
    # 计算股息率
    sdf['div_ratio'] = 1e-2 * sdf.div_3y / sdf.market_cap
    # report
    sdf['name'] = [get_security_info(s).display_name for s in sdf.index]
    sdf = sdf.sort_values(by='div_ratio', ascending=False)
    log.info('\n', sdf[:5])
    return list(sdf.head(num).index)
# end



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 资金划转代码

#对冲比例调整+账户间资金划转
def rebalance(context):
    # 计算资产总价值
    total_value = context.portfolio.total_value
    # 计算预期的股票账户价值
    expected_stock_value = total