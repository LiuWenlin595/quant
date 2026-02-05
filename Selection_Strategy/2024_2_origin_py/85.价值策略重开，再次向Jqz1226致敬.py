# 克隆自聚宽文章：https://www.joinquant.com/post/36092
# 标题：价值策略重开，再次向Jqz1226致敬
# 作者：南开小楼

from jqdata import *
import statsmodels.api as sm
import pandas as pd
import numpy as np
import datetime
import scipy.stats as stats
import warnings
warnings.filterwarnings('ignore')





def initialize(context):
    set_param(context) #设置参数
    
    #9:00先计算mode2_flag如果为0则用rsrs计算mode1_flag，取flag为1的模式的buy_list作为当日操作
    run_monthly(mode2_pe_check_month, 1,time='09:00')
    run_weekly(mode2_pe_check_week, 1,time='09:05')
    run_daily(before_markt_open, time='09:10', reference_security='000300.XSHG')
    
    
    #9:16卖出flag为1的不在buy_list的股票
    run_daily(before_markt_open_trade_sell, time='09:16', reference_security='000300.XSHG')
    
    
    #9:26买入flag为1的buy_list的股票
    run_daily(before_markt_open_trade_buy, time='09:26', reference_security='000300.XSHG')
    # run_daily(before_markt_open_trade_buy, time='09:27', reference_security='000300.XSHG')
    # run_daily(before_markt_open_trade_buy, time='09:28', reference_security='000300.XSHG')
    # run_daily(before_markt_open_trade_buy, time='09:29', reference_security='000300.XSHG')
    
    #开盘复核买入
    run_daily(markt_open_trade, time='09:30', reference_security='000300.XSHG')
    
    #模式2的票盘中交易
    run_daily(mode2_stop_loss, '10:30', reference_security='000300.XSHG')
    run_daily(mode2_stop_loss, '11:30', reference_security='000300.XSHG')
    run_daily(mode2_stop_loss, '13:30', reference_security='000300.XSHG')
    run_daily(mode2_stop_loss, '14:30', reference_security='000300.XSHG')
    run_daily(mode2_stop_holds, '14:50', reference_security='000300.XSHG')

    
    
    #10:00买入etf_list 中的股票
    run_daily(during_markt_open_trade, time='10:00', reference_security='000300.XSHG')
    
    
    #周一到周四尾盘卖出511880，买入逆回购（需券商支持自动购买1日逆回购），周五持有511880
    run_weekly(before_markt_close_trade, weekday=1, time='14:50', reference_security='000300.XSHG')
    run_weekly(before_markt_close_trade, weekday=2, time='14:50', reference_security='000300.XSHG')
    run_weekly(before_markt_close_trade, weekday=3, time='14:50', reference_security='000300.XSHG')
    run_weekly(before_markt_close_trade, weekday=4, time='14:50', reference_security='000300.XSHG')
    #收盘后打印持仓情况
    run_daily(after_market_close,time='after_close', reference_security='000300.XSHG')
    
    

    
def set_param(context):
    #1.初始化系统参数
    set_base_param(context)
    #2.初始化股票参数
    set_mode1_param(context)
    set_mode2_param(context)

    
def set_base_param(context):
    #显示所有列
    pd.set_option('display.max_columns', None)
    #显示所有行
    pd.set_option('display.max_rows', None)
    #设置value的显示长度为100，默认为50
    pd.set_option('max_colwidth',100)
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 过滤掉order系列API产生的比error级别低的log
    log.set_level('order', 'error')
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    #风险参考基准
    g.security = '000300.XSHG'
    #卖出股票后对冲基金
    g.etf_list = '511880.XSHG'
    
    #统计持仓量的历史天数
    g.days_number = 15
    
    #用于存放历史value的list，len为g.days_number
    g.old_portfolio_values = []
    
    #30 天清理一次g.risky_stocks
    g.days_count = 0
    
    g.risk_incr_pct = 0.1
    
    g.risk_flag = 0
    
    g.risky_stocks = []
    
    
def set_mode1_param(context):
    #模式1买入列表
    g.mode1_buy_list=[]
    #模式1买入总数量
    g.mode1_stock_num = 5
    #模式1判断开仓方向
    g.mode1_flag = 0
    #中间列表
    g.fin=pd.DataFrame()


def set_mode2_param(context):
    #模式2买入列表
    g.mode2_temp_list = []
    g.mode2_buy_list = []
    #模式2买入总数量
    g.mode2_stock_num = 2
    #模式2判断开仓方向
    g.mode2_flag = 0


def before_markt_open(context):
    log.info("-------------------------------------------------------------------")

    if g.mode2_flag == 1:
		log.info("Pe上行，操作股票:")
		
		mode2_check_stock(context)
    else:
        log.info("Pe下行或超出中位数值，空仓:")
        mode1_check_rsrs(context)


def mode1_check_rsrs(context):
    previous_date = context.current_dt - datetime.timedelta(days=1)
    hs300_data = get_price('000300.XSHG',end_date=previous_date,count=1150,fields=['high','low']) 
    hs300_rsrs = calc_rsrs(hs300_data['high'].values,hs300_data['low'].values,hs300_data['high'].index,800,18)
    zscore_rightdev = hs300_rsrs.RSRS_negative_r.iloc[-1]
   
    log.info("【RSRS斜率: %.2f】",zscore_rightdev)
    if zscore_rightdev > 0.7:
        g.mode1_flag = 1
        
        
    if zscore_rightdev < -0.7:
        g.mode1_flag = 0
    if g.mode1_flag == 1:
        log.info("    市场风险在合理范围,持有股票")
        mode1_check_stock(context)
    if g.mode1_flag == 0:
        log.info("    市场风险过大，持有货币基金")

    
'''
#=================================交易流程=======================================#
'''


def before_markt_open_trade_sell(context):
    etf_list = g.etf_list
    #队列装满以后，每天比较上上周的账户value 和上周的账户value
    if len(g.old_portfolio_values) == g.days_number:
        incr_rate = (g.old_portfolio_values[-6] - g.old_portfolio_values[-11])/g.old_portfolio_values[-11]
    else:
        incr_rate = 0
    log.info('incr_rate is:',incr_rate)
    log.info('g.risk_incr_pct is:',g.risk_incr_pct)
    #判别账户value是否暴涨
    if incr_rate >= g.risk_incr_pct:
            sell_list = context.portfolio.positions.keys()
            sell_list = [s for s in sell_list if s != etf_list]
            #计算沪深300 是否黄昏之星,如果是risk_flag == 1
            dp_df_2w = attribute_history(count = 2, unit='5d', security='000300.XSHG')
            dp_stock_last_2w = dp_df_2w.iloc[0]
            dp_stock_last_1w = dp_df_2w.iloc[1]
            #计算上上周涨幅
            log.info('dp_stock_last_2w.close is:',dp_stock_last_2w.close)
            log.info('dp_stock_last_2w.open is:',dp_stock_last_2w.open)
            dp_cr_last_2w = (dp_stock_last_2w.close - dp_stock_last_2w.open)/dp_stock_last_2w.open
            dp_ub_rate_last_1w = 0
            dp_ba_rate_last_1w = 0
            #计算上周上影线/箱体高度比例，比例越大上影线越长
            if dp_stock_last_1w.close >= dp_stock_last_1w.open:
                dp_ub_rate_last_1w = (dp_stock_last_1w.high - dp_stock_last_1w.close)/(dp_stock_last_1w.close - dp_stock_last_1w.open + 0.00001)
            else:
                dp_ub_rate_last_1w = (dp_stock_last_1w.high - dp_stock_last_1w.open)/(dp_stock_last_1w.open - dp_stock_last_1w.close + 0.00001)
            #如果上周股价下跌，计算箱体高度/振幅比例,比例越大箱体越长
            if dp_stock_last_1w.close <= dp_stock_last_1w.open:
                dp_ba_rate_last_1w = (dp_stock_last_1w.open - dp_stock_last_1w.close)/(dp_stock_last_1w.high - dp_stock_last_1w.low+0.00001)
            log.info('dp_cr_last_2w is:',dp_cr_last_2w)
            log.info('dp_ub_rate_last_1w is:',dp_ub_rate_last_1w)
            log.info('dp_ba_rate_last_1w is:',dp_ba_rate_last_1w)
            if dp_cr_last_2w >= 0.04 and (dp_ub_rate_last_1w > 2 or dp_ba_rate_last_1w > 1/3):
                log.info('大盘黄昏之星，g.risk_flag = 1')
                g.risk_flag = 1
                g.days_count = 0
                #判别个股是否黄昏之星
                for sell_code in sell_list:
                    log.info('sell_code is:',sell_code)
                    df_2w = attribute_history(count =2, unit='5d', security=sell_code)
                    stock_last_2w = df_2w.iloc[0]
                    stock_last_1w = df_2w.iloc[1]
                    #计算上上周涨幅
                    cr_last_2w = (stock_last_2w.close - stock_last_2w.open)/stock_last_2w.open
                    ub_rate_last_1w = 0
                    ba_rate_last_1w = 0
                    #计算上影线/箱体高度比例，比例越大上影线越长
                    if stock_last_1w.close >= stock_last_1w.open:
                        ub_rate_last_1w = (stock_last_1w.high - stock_last_1w.close)/(stock_last_1w.close - stock_last_1w.open + 0.00001)
                    else:
                        ub_rate_last_1w = (stock_last_1w.high - stock_last_1w.open)/(stock_last_1w.open - stock_last_1w.close + 0.00001)
                    #如果上周股价下跌，计算箱体高度/下影线比例,比例越大箱体越长
                    if stock_last_1w.close <= stock_last_1w.open:
                        ba_rate_last_1w = (stock_last_1w.open - stock_last_1w.close)/(stock_last_1w.high - stock_last_1w.low+0.00001)
                    log.info('cr_last_2w is:',cr_last_2w)
                    log.info('ub_rate_last_1w is:',ub_rate_last_1w)
                    log.info('ba_rate_last_1w is:',ba_rate_last_1w)
                    #if cr_last_2w >= 0.09 and (cr_last_2w > 2 or cr_last_2w > 1/3):
                    if cr_last_2w >= 0.09 and (ub_rate_last_1w > 2 or ba_rate_last_1w > 1/3):
                        code_number = context.portfolio.positions[sell_code].closeable_amount
                        log.info('可平仓数 is:',code_number)
                        if  code_number > 0:
                            last_price = history(1, unit='1d', field='close', security_list=sell_code).iloc[-1,0]
                            limit_price = last_price*0.91 #即为跌停价
                            order_target_value(sell_code,0,LimitOrderStyle(limit_price))
                            g.risky_stocks.append(sell_code)
                            log.info("【该股黄昏之星且前期涨幅过快，执行竞价减仓交易】")
                            log.info('    执行竞价减仓交易: %s,  委托价格: %.2f',sell_code,limit_price)

            
    
    mode1_buy_list=g.mode1_buy_list
    all_value=context.portfolio.total_value
    
    # 如果上一时间点的R