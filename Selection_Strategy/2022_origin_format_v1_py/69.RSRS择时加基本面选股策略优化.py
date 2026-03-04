# 克隆自聚宽文章：https://www.joinquant.com/post/21249
# 标题：RSRS择时加基本面选股策略优化
# 作者：luvymhq

enable_profile()
# 策略思路：
# 选股：财务指标选股
# 择时：RSRS择时
# 持仓：有开仓信号时持有3-5只股票，不满足时保持空仓


# 导入函数库
import statsmodels.api as sm
import numpy as np
from pandas.stats.api import ols
from jqfactor import neutralize
from jqlib.technical_analysis import *
import datetime as dt


# 初始化函数，设定基准等等
def initialize(context):
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 过滤掉order系列API产生的比error级别低的log
    log.set_level('order', 'info')
    set_parameter(context)
    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.00015, close_commission=0.00015, min_commission=5), type='stock')
    
    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG') 
      # 开盘时运行
    run_daily(market_open_sell, time='open',reference_security='000300.XSHG')
    run_daily(market_open_buy, time='open+10m', reference_security='000300.XSHG')
      # 收盘后运行
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')
    

# ==============================参数设置部分================================
def set_parameter(context):
    # 设置RSRS指标中N, M的值
    #统计周期
    g.N = 18
    #统计样本长度
    g.M = 800
    #首次运行判断
    g.init = True
    #止损系数(占总资金的比例)
    g.stopindex = -0.05
    #止损开关
    g.stop = True
    #风险参考基准
    g.security = '000300.XSHG'
    g.etf = '511010.XSHG'
    # 设定策略运行基准
    set_benchmark(g.security)
    #记录策略运行天数
    g.days = 0
    g.stock_num = 4
    # 买入阈值
    g.buy = 0.7
    g.sell = -0.7
    #用于记录回归后的beta值，即斜率
    g.ans = []
    #用于计算被决定系数加权修正后的贝塔值
    g.ans_rightdev= []
    #用于当天的选股
    g.stock_list=[]
    g.hold_list=[]
    #标准分
    g.zscore_rightdev=0
    g.hs300=0 
    g.zz500=0
    
    # 计算2005年1月5日至回测开始日期的RSRS斜率指标
    prices = get_price(g.security, '2005-01-05', context.previous_date, '1d', ['high', 'low'])
    highs = prices.high
    lows = prices.low
    for i in range(len(highs))[g.N:]:
        data_high = highs.iloc[i-g.N+1:i+1]
        data_low = lows.iloc[i-g.N+1:i+1]
        X = sm.add_constant(data_low)
        model = sm.OLS(data_high,X)
        results = model.fit()
        g.ans.append(results.params[1])
        #计算r2
        g.ans_rightdev.append(results.rsquared)
    
## 开盘前运行函数     
def before_market_open(context):
    #获取总资金
    g.totalValue = context.portfolio.total_value
    # 输出运行时间
    log.info('##########################新的一天日志####################################')
    #log.info('函数运行时间(before_market_open)：'+str(context.current_dt.time()))
    
    #hs300 = list(get_price('000300.XSHG',start_date='2005-04-08',end_date=context.current_dt.date(),frequency='1d',fields='close').close)
    #zz500 = list(get_price('000905.XSHG',start_date='2007-01-15',end_date=context.current_dt.date(),frequency='1d',fields='close').close)
    #hs300_in = (hs300[-1]-hs300[0])/hs300[0]
    #zz500_in = (zz500[-1]-zz500[0])/zz500[0]
    
    #tempDate = str(context.current_dt.year)+'-'+str(context.current_dt.month)+'-1'
    #startDate = dt.datetime.strptime(tempDate,'%Y-%m-%d').strftime('%Y-%m-%d')
    
    if 1<=context.current_dt.month <=3:
        startDate = str(context.current_dt.year)+'-01-01'
    elif 4<=context.current_dt.month <=6:
        startDate = str(context.current_dt.year)+'-04-01'
    elif 7<=context.current_dt.month <=9:
        startDate = str(context.current_dt.year)+'-07-01'
    else:
         startDate = str(context.current_dt.year)+'-10-01'
    
    if startDate == context.current_dt.date().strftime('%Y-%m-%d'):
       startDate = context.previous_date
    
    i=1
    while len(list(get_price('000300.XSHG',start_date=startDate,end_date=context.previous_date,frequency='1d',fields='close').close))==0:
         startDate = (dt.datetime.strptime(startDate,'%Y-%m-%d')+dt.timedelta(-i)).strftime('%Y-%m-%d')
         i += 1
        
    hs300 = list(get_price('000300.XSHG',start_date=startDate,end_date=context.previous_date,frequency='1d',fields='close').close)
    zz500 = list(get_price('000905.XSHG',start_date=startDate,end_date=context.previous_date,frequency='1d',fields='close').close)
    hs300_in = (hs300[-1]-hs300[0])/hs300[0]
    zz500_in = (zz500[-1]-zz500[0])/zz500[0]
    
    log.info("hs300百分比:%s,zz500百分比:%s" %(hs300_in,zz500_in))
    
    #选出当日股票list
    if  zz500_in>=hs300_in:#(hs300_in-zz500_in)/hs300_in<=0.2:
        g.zz500 += 1
        g.stock_list = trade_list(context,'neutralize')
    else:
        g.hs300 += 1
        g.stock_list = trade_list(context,'basic')
    log.info("zz500:%s days,hs300:%s days" %(g.zz500,g.hs300))
    #持仓列表
    g.hold_list = context.portfolio.positions.keys()
    log.info("选出股票列表：%s"%g.stock_list)
    g.days += 1
    #计算标准分
    beta=0
    r2=0
    if g.init:
        g.init = False
    else:
        #RSRS斜率指标定义
        prices = attribute_history(g.security, g.N, '1d', ['high', 'low'])
        highs = prices.high
        lows = prices.low
        X = sm.add_constant(lows)
        model = sm.OLS(highs, X)
        beta = model.fit().params[1]
        g.ans.append(beta)
        #计算r2
        r2=model.fit().rsquared
        g.ans_rightdev.append(r2)
    
    # 计算标准化的RSRS指标
    # 计算均值序列    
    section = g.ans[-g.M:]
    # 计算均值序列
    mu = np.mean(section)
    # 计算标准化RSRS指标序列
    sigma = np.std(section)
    zscore = (section[-1]-mu)/sigma  
    #计算右偏RSRS标准分
    g.zscore_rightdev= zscore*beta*r2
    log.info("==今日标准分为:%s==" % g.zscore_rightdev)
    
    if g.zscore_right