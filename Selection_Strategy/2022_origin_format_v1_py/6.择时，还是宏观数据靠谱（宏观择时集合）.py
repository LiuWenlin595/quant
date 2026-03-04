# 克隆自聚宽文章：https://www.joinquant.com/post/19349
# 标题：择时，还是宏观数据靠谱（宏观择时集合）
# 作者：云帆

# 导入函数库
from jqdata import *
import numpy as np
import pandas as pd
import talib as tl
import pickle
import datetime
import tushare as ts
from six import StringIO
import warnings
warnings.filterwarnings('ignore')

# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')
    set_params()
    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
    if g.run_monthly == True:
        run_monthly(before_market_open, monthday=1, time='09:30')
          # 开盘时运行
        run_monthly(market_open, monthday=1, time='09:30')
    else:
        run_daily(before_market_open, time='open')
        run_daily(market_open, time='open')
        
        
def set_params():
    g.n = 3 #移动平均窗口
    g.bulin_n = 25 #布林带数据长度
    g.position = 0
    g.stocks = '000300.XSHG'
    g.bulin_upper_dev = 1.8 #布林带上限标准差倍数
    g.bulin_lower_dev = 1.8
    g.run_monthly = True
    g.num_date = 90
    g.reserve_ratio_delay = 120 #存款准备金率取之前数据的周期
    g.weight = [1,1,2,1,1]  #'monetary','forex','credit','boom','inflation'
    g.combine_weights = [1,0.5,1,0.5,1]  #'PMI','import_idx','primary_yoy','satisfaction_idx','confidence_idx'

## 开盘前运行函数
def before_market_open(context):
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：'+str(context.current_dt.time()))
    current_day = context.current_dt.day
    current_month = context.current_dt.month
    current_year = context.current_dt.year
    last_month = get_last_month(current_year,current_month,g.n+15)
    current_date = context.current_dt.date()
    print(current_date)
    previous_date = context.previous_date
    previous_date = datetime.datetime.strftime(previous_date,'%Y-%m-%d')
    trade_days_one_month = get_trade_days(end_date=current_date,count=g.num_date)
    trade_days_one_month = datetime_to_str(trade_days_one_month)
    trade_days_one_month.pop() #将当天值去除
    ts_data = change_to_tushare_date(trade_days_one_month)
    '''
    #PMI择时
    pmi = get_PMI(last_month)
    pmi_position = (pmi['pmi'].rolling(g.n).mean() > pmi['pmi'].rolling(g.n).mean().shift(1))*1
    pmi_position = pmi_position.values[-1]
    #print(pmi_position)
   # SHIBOR利率择时
    shibor = get_SHIBOR(trade_days_one_month)
    #一个月利率
    shibor_1m = shibor[['1m']]
    shibor_position = bbands_select_time(shibor_1m,'lower')
    #国债择时
    gz = get_gz(trade_days_one_month)
    gz_position = bbands_select_time(gz,'upper')    
    #企业债择时
    qyz = get_qyz(trade_days_one_month)
    qyz_position = bbands_select_time(qyz,'lower')  
    #M1 - M2同比剪刀差择时
    money_change = get_M1_M2(last_month)
    mc_position = (money_change.rolling(g.n).mean() > money_change.rolling(g.n).mean().shift(1)) * 1
    #M1,M2一般在次月中上旬发布，例如2018年12月11日发布了2018年11月的数据，因此当月的择时需参考上上个月的指标
    mc_position = mc_position.values[-2]

    #存款准备金率择时
    reserve_ratio_position = get_reserve_ratio_from_csv(previous_date)

    #社会融资总额择时
    aggregate_fin = get_aggregate_financing(last_month)
    aggregate_fin_position = (aggregate_fin.rolling(g.n).mean() > aggregate_fin.rolling(g.n).mean().shift(1))*1
    aggregate_fin_position = aggregate_fin_position.values[-2]
    #汇率择时
    huilv = get_exchange_rate(trade_days_one_month)
    huilv_position = bbands_select_time(huilv,'lower')
    #通胀指数 PPI - CPI 择时
    inf = get_inflation_index(last_month)
    def good_cpi(x):
        if x<0:
            y=0.
        elif x<5.:
            y=1.
        else:
            y=0
        return y
    inf_position = (inf.rolling(g.n).mean() < inf.rolling(g.n).mean().shift(1))*1
    label = (inf.rolling(g.n).mean().apply(good_cpi))
    inf_position = inf_position * label
    inf_position = inf_position.values[-2]
    #货币政策择时指标=利率+期限利差+信用利差
    #考虑存款准备金率
    huobi_position = (shibor_position + gz_position + qyz_position) / 3 + 0.3 * reserve_ratio_position
    if huobi_position > 1:
       huobi_position = 1
    #huobi_position = (shibor_position + gz_position + qyz_position) / 3.0   
    #信贷择时指标 = M1、M2剪刀差 + 社融指标
    credit_loan_postition = (mc_position + aggregate_fin_position) / 2.0
    #print([shibor_position, gz_position, qyz_position,reserve_ratio_position])

    #汇总择时指标
    all_position = [huobi_position,huilv_position,credit_loan_postition,pmi_position,inf_position]
    all_position = np.array(all_position)
    weight = np.array(g.weight)
    position = (all_position * weight).sum()/len(weight)
    print(position)
    if position > 0.55:
        all_position1 = 1
    elif position < 0.45:
        all_position1 = 0
    else:
        all_position1 = 0.5
    print(all_position1)
    '''
    #新指标
    pmi2_position = get_pmi_position(last_month)
    import_position = get_import_position(last_month)
    primary_position = get_primary_position(last_month)
    satisfaction_position = get_satisfaction_position(last_month)
    confidence_position = get_confidence_position(last_month)
    combine_position = [pmi2_position,import_position,primary_position,satisfaction_position,confidence_position]
    combine_position = np.array(combine_position).flatten()
    #print(combine_position)
    combine_weights = np.array(g.combine_weights)
    position = (combine_position * g.combine_weights).sum()
    position = position/combine_weights.sum()
    print(position)
    if position > 0.45:
        g.position = 1
    elif position < 0.4:
        g.position = -1
    else:
        g.position = 0
    
## 开盘时运行函数
def market_open(context):
    previous_date = context.previous_date
    previous_date = datetime.datetime.strftime(previous_date,'%Y-%m-%d')
    cash = context.portfolio.available_cash
    all_cash = context.portfolio.total_value
    '''
    if g.position == 1:
            log.info('开始下单')
            order_value(g.stocks, cash)
    else:
        order_target(g.stocks, 0)
    '''
    #大盘止损，上月跌幅超5%则卖出
    price = get_price(g.stocks,end_date=previous_date, fields=['close'],count=21)['close']
    pct_change = price.pct_change(20).values[-1]

    if g.position == 1:
        log.info('开始下单')