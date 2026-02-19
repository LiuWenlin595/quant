# 克隆自聚宽文章：https://www.joinquant.com/post/47624
# 标题：国九条：三年分红5千万以下且占净利润30%以下将被ST
# 作者：Clarence.罗

# 克隆自聚宽文章：https://www.joinquant.com/post/47523
# 标题：十年回测  年化103.32%  最大回撤23.89%
# 作者：jason_99

# 克隆自聚宽文章：https://www.joinquant.com/post/47346
# 标题：14-24【年化86%|胜率66%|回撤33%】无未来函数
# 作者：zycash

#导入函数库
from jqdata import *
from jqfactor import *
import numpy as np
import pandas as pd
import random
from datetime import time
#import datetime
#初始化函数 
def initialize(context):
    # 开启防未来函数，设定基线，真实价格，滑点及交易成本
    # set_option('avoid_future_data', True)
    set_benchmark('000001.XSHG')
    set_option('use_real_price', True)

    #统一费率
    #set_slippage(PriceRelatedSlippage(0.01), type='stock')
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=2.5/10000, close_commission=2.5/10000, close_today_commission=0, min_commission=5),type='stock')

    g.stock_num = 10

    # 过滤order中低于error级别的日志
    log.set_level('order', 'error')
    log.set_level('system', 'error')
    log.set_level('strategy', 'debug')
    #初始化全局变量 bool
    g.no_trading_today_signal = False  # 是否为可交易日
    g.pass_april = True  # 是否四月空仓
    g.run_stoploss = True  # 是否进行止损
    #全局变量list
    g.hold_list = [] #当前持仓的全部股票    
    g.yesterday_HL_list = [] #记录持仓中昨日涨停的股票
    g.target_list = []  # 准备买入的标的
    g.not_buy_again = []    # 不再买入的标的
    #全局变量float/str
    g.m_days = 5 #取值参考天数
    g.up_price = 80  # 设置股票单价
    g.reason_to_sell = ''
    g.stoploss_strategy = 3  # 1为止损线止损，2为市场趋势止损, 3为联合1、2策略
    g.stoploss_limit = 0.07  # 止损线
    g.stoploss_market = 0.05  # 市场趋势止损参数
    g.c = 0     # 止损天数计数器
    # 设置交易运行时间
    run_daily(prepare_stock_list, '8:00')       # 每天开盘前更新全局参数，持仓和昨日涨停
    run_weekly(weekly_adjustment,2,'10:00')     # 每周二上午10点检查并调仓，不会更新卖出原因
    run_daily(sell_stocks, time='10:30')        # 每天检查止损函数，止损会更新卖出原因
    run_daily(sell_stocks, time='14:00')        # 每天检查止损函数，止损会更新卖出原因
    # 涨停可能提前止盈并更新卖出原因，查看剩余金额，结合卖出原因决定是否需要买入，并重置卖出原因
    run_daily(trade_afternoon, time='14:30') 
    run_daily(close_account, '14:30')   # 特殊月份提前清仓
    # run_weekly(print_position_info, 5, time='15:30', reference_security='000300.XSHG')  # 每周5结束后统计持仓盈亏
    # run_daily(log_stocks_bought, '15:02')

#1-1 更新全局参数，每天开盘前运行
def prepare_stock_list(context):
    # 更新已持有列表
    g.hold_list= list(context.portfolio.positions.keys())
    # 更新持有股票中昨日涨停的股票
    if g.hold_list != []:
        df = get_price(g.hold_list, end_date=context.previous_date, frequency='daily', 
            fields=['close','high_limit','low_limit'], count=1, panel=False, fill_paused=False)
        df = df[df['close'] == df['high_limit']]
        g.yesterday_HL_list = list(df.code)
    else:
        g.yesterday_HL_list = []
    #判断今天是否为账户资金再平衡的日期，判断是否为特殊日期
    g.no_trading_today_signal = today_is_between(context)

#1-2 选股模块，每周运行一遍
def get_stock_list(context):
    final_list = []
    initial_list = get_index_stocks('399101.XSHE')          # 从中小综指中选股
    initial_list = filter_new_stock(context, initial_list)  # 过滤次新股，上市不满1年的
    initial_list = filter_kcbj_stock(initial_list)          # 过滤科创北交所股票，改为保留沪深主板股票
    initial_list = filter_st_stock(initial_list)            # 过滤ST股票
    initial_list = get_dividend_ratio_filter_list(context, initial_list, False, 0, 0.8)  #股息筛选

    q = query(valuation.code,valuation.market_cap).filter(valuation.code.in_(initial_list),
        valuation.market_cap.between(5,50)).order_by(valuation.market_cap.asc())    # 5到30亿市值，从小到大排列
    df_fun = get_fundamentals(q)[:100]

    initial_list = list(df_fun.code)
    initial_list = filter_paused_stock(initial_list)                # 过滤停牌股票
    initial_list = filter_limitup_stock(context, initial_list)      # 过滤昨日涨停股票，持仓股不在此列
    initial_list = filter_limitdown_stock(context, initial_list)    # 过滤昨日跌停股票，持仓股不在此列
    initial_list = filter_highprice_stock(context, initial_list)    # 过滤股价过高的票，持仓股不在此列

    print('initial_list中含有{}只股票'.format(len(initial_list)))
    q = query(valuation.code,valuation.market_cap).filter(
        valuation.code.in_(initial_list)).order_by(valuation.market_cap.asc())
    df_fun = get_fundamentals(q)[:50]
    final_list  = list(df_fun.code)
    return final_list   # 返回前50只

#1-1 最近三年分红需大于5000万 或 最近三年分红需大于30%，按股息率排序
#借用aqa的代码：
#根据上交所新规，增加了3个筛选条件：
# 1.盈利且上年度未分配利润大于0，
# 2 三个会计年度累计现金分红总额大于年均净利润的30%，
# 3.累计分红金额大于5,000万元。
def get_dividend_ratio_filter_list(context, stock_list, is_small_to_big, p1, p2):
    time1 = context.previous_date
    time0 = time1 - datetime.timedelta(days=365)
    print('按付息5000万或30%以上筛选前的股票数量：',len(stock_list))
    #获取分红数据，由于finance.run_query最多返回4000行，以防未来数据超限，最好把stock_list拆分后查询再组合
    interval = 1000 #某只股票可能一年内多次分红，导致其所占行数大于1，所以interval不要取满4000
    list_len = len(stock_list)
    #截取不超过interval的列表并查询
    q = query(
        finance.STK_XR_XD.code, 
        finance.STK_XR_XD.a_registration_date, 
        finance.STK_XR_XD.bonus_amount_rmb
    ).filter(
        finance.STK_XR_XD.a_registration_date >= time0,
        finance.STK_XR_XD.a_registration_date <= time1,
        finance.STK_XR_XD.code.in_(stock_list[:min(list_len, interval)]))
    df = finance.run_query(q)
    #对interval的部分分别查询并拼接
    if list_len > interval:
        df_num = list_len // interval
        for i in range(df_num):
            q = query(
                finance.STK_XR_XD.code,
                finance.STK_XR_XD.a_registration_date,
                finance.STK_XR_XD.bonus_amount_rmb
            ).filter(
                finance.STK_XR_XD.a_registration_date >= time0,
                finance.STK_XR_XD.a_registration_date <= time1,
                finance.STK_XR_XD.code.in_(stock_list[interval*(i+1):min(list_len,interval*(i+2))]))
            temp_df = finance.run_query(q)
            df = df.append(temp_df)
    dividend = df.fillna(0)
    dividend = dividend.set_index('code')
    dividend = dividend.groupby('code').sum()
    temp_list = list(dividend.index) #query查询不到无分红信息的股票，所以temp_list长度会小于stock_list

    #获取过去三年净利润数据
    if time1.month>=5:#5月后取去年
        start_year=str(time1.year-1)
    else:   #5月前取前年
        start_year=str(time1.year-2)
    #获取3年净利润数据
    np=get_history_fundamentals(temp_list,  fields=[income.net_profit], watch_date=None, 
                                stat_by_year=True, stat_date=start_year, interval='1y', count=3)
    np = np.set_index('code')
    np = np.groupby('code').mean()
    
    #获取市值相关数据，用于计算股息率
    q = query(valuation.code,valuation.market_cap).filter(valuation.code.in_(temp_list))
    cap = get_fundamentals(q, date=time1)
    cap = cap.set_index('code')
    
    #筛选 过去三年累计分红大于平均净利润的30% 或 累计分红>5000万
    DR = pd.concat([dividend,np,cap], axis=1)
    DR=DR[((DR['bonus_amount_rmb']*10000)>(DR['net_profit']*0.3)) | (DR['bonus_amount_rmb']>5000)]

    #计算股息率
    DR['dividend_ratio'] = (DR['bonus_amount_rmb']/10000) / DR['market_cap']
    print('按付息5000万或30%以上筛选后的股票数量：：',len(list(DR.index)))

    #按股息率排序并筛选
    #DR = DR.sort_values(by=['dividend_ratio'], ascending=is_small_to_big)
    #final_list = list(DR.index)[int(p1*len(DR)):int(p2*len(DR))]

    #C罗改：暂时直接
    final_list = list(DR.index)

    return final_list
    
#1-3 每周调整持仓
def weekly_adjustment(context):
    if g.no_trading_today_signal == False:
        #获取应买入列表 
        g.not_buy_again = []    # 每周重置g.not_buy_again的股票
        g.target_list = get_stock_list(context) # 选取50只符合条件的股票
        target_list = g.target_list[:g.stock_num]
        # target_list = random.sample(target_list[:8],g.stock_num)    # 前8个中随机选5
        log.info(str(target_list))
        #调仓卖出，没有更新卖出原因
        for stock in g.hold_list:
            if (stock not in target_list) and (stock not in g.yesterday_HL_list):   # 卖出非目标且非昨日涨停的股票
                position = context.portfolio.positions[stock]
                if close_position(position):    # 卖出股票操作
                    log.info("卖出[%s]" % (stock))
                else:
                    log.info("！！！卖出失败[%s]" % (stock))
            else:
                log.info("已持有[%s]" % (stock))
        #调仓买入
        buy_security(context,target_list)
        #记录已买入股票
        for stock in list(context.portfolio.positions.keys()):
            g.not_buy_again.append(stock)

#1-7 每天定点检查止损
def sell_stocks(context):
    if g.run_stoploss == True:
        if g.stoploss_strategy == 1:
            for stock in context.portfolio.positions.keys():
                # 股票盈利大于等于100%则卖出
                if context.portfolio.positions[stock].price >= context.portfolio.positions[stock].avg_cost * 2:
                    order_target_value(stock, 0)
                    log.debug("收益100%止盈,卖出{}".format(stock))
                # 止损
                elif context.portfolio.positions[stock].price < context.portfolio.positions[stock].avg_cost * (1-g.stoploss_limit):
                    order_target_value(stock, 0)
                    log.debug("收益止损,卖出{}".format(stock))
                    g.reason_to_sell = 'stoploss'
        elif g.stoploss_strategy == 2:
            stock_df = get_price(security=get_index_stocks('399101.XSHE'), end_date=context.previous_date, 
                frequency='daily', fields=['close', 'open'], count=1,panel=False)
            #down_ratio = (stock_df['close'] / stock_df['open'] < 1).sum() / len(stock_df)
            down_ratio = abs((stock_df['close'] / stock_df['open'] - 1).mean())
            if down_ratio >= g.stoploss_market:
                g.reason_to_sell = 'stoploss'
                log.debug("大盘惨跌,平均降幅{:.2%}".format(down_ratio))
                for stock in context.portfolio.positions.keys():
                    order_target_value(stock, 0)
        elif g.stoploss_strategy == 3:
            stock_df = get_price(security=get_index_stocks('399101.XSHE'), end_date=context.previous_date, 
                frequency='daily', fields=['close', 'open'], count=1,panel=False)
            down_ratio = abs((stock_df['close'] / stock_df['open'] - 1).mean())
            if down_ratio >= g.stoploss_market:
                g.reason_to_sell = 'stoploss'
                log.debug("基准指数暴跌,平均降幅{:.2%},全部清仓".format(down_ratio))
                for stock in context.portfolio.positions.keys():
                    order_target_value(stock, 0)
            else:
                for stock in context.portfolio.positions.keys():
                    if context.portfolio.positions[stock].price < context.portfolio.positions[stock].avg_cost * (1-g.stoploss_limit):
                        order_target_value(stock, 0)
                        log.debug("达到止损,卖出{}".format(stock))
                        g.reason_to_sell = 'stoploss'

#1-4 昨日涨停股票确定是否止盈，卖出时会记录卖出原因
def check_limit_up(context):
    now_time = context.current_dt   # 当前时间
    if g.yesterday_HL_list != []:
        #对昨日涨停股票观察到尾盘如不涨停则提前卖出，如果涨停即使不在应买入列表仍暂时持有
        for stock in g.yesterday_HL_list:
            current_data = get_price(stock, end_date=now_time, frequency='1m', fields=['close','high_limit'], 
                skip_paused=False, fq='pre', count=1, panel=False, fill_paused=True)
            if current_data.iloc[0,0] < current_data.iloc[0,1]:
                position = context.portfolio.positions[stock]
                if close_position(position):
                    log.info("[%s]涨停打开，卖出" % (stock))
                    g.reason_to_sell = 'limitup'
            else:
                log.info("[%s]涨停，继续持有" % (stock))

#1-5 如果账户还有金额则执行此操作，会重置卖出原因
def check_remain_amount(context):
    if g.reason_to_sell is 'limitup': #判断售出原因，如果是涨停售出则可以再次交易，如果是止损售出则不交易
        g.hold_list= list(context.portfolio.positions.keys())
        if len(g.hold_list) < g.stock_num:
            target_list = g.target_list     # 每周更新的股票池
            target_list = filter_not_buy_again(target_list)     # 是排除本周调仓时已经持仓的股票
            target_list = target_list[:min(g.stock_num, len(target_list))]
            log.info('有余额可用'+str(round((context.portfolio.cash),2))+'元。'+ str(target_list))
            buy_security(context,target_list)
        g.reason_to_sell = ''
    else:
        g.c+=1
        log.info('刚刚止损，隔1天再交易')
        if g.c % 2 ==0:
            g.reason_to_sell = ''

#1-6 下午检查交易
def trade_afternoon(context):
    if g.no_trading_today_signal == False:
        check_limit_up(context)
        check_remain_amount(context)


#2-1 过滤停牌股票
def