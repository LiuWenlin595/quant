# 克隆自聚宽文章：https://www.joinquant.com/post/45648
# 标题：基金溢价（模拟效果好！）
# 作者：大山深处

# 克隆自聚宽文章：https://www.joinquant.com/post/33636
# 标题：etf基金溢价-改进版-高收益低回撤-速度已最优
# 作者：发锅
# 修订：王巨明  
# 增加大盘风控函数，设法减少回撤
# 2023-6-20
#   (1) 0620,510210.XSHG错误买入，因为没有处理好分红的前复权问题
#   (2) 对于一段时间没有买入的情况，将修改g.least_premium，由2.5下降，直接到1.5
##
from jqdata import *
import datetime
import talib
from jqlib.technical_analysis  import *
import sys
import requests     #爬基金的VALUE和IOPV 
##
## 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启异步报单
    #set_option('async_order', True)
    # 根据实际行情限制每个订单的成交量
    # 0.05：对限价单，即每分钟成交量的5%    set_option('order_volume_ratio', 0.05)
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 是否未来函数
    set_option("avoid_future_data", True)
    # 设置费率
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0, open_commission=0.00025, 
        close_commission=0.00025, close_today_commission=0, min_commission=5), 
        type='fund')
    # 过滤掉order系列API产生的比error级别低的log
    log.set_level('order', 'error')
    # 至少的溢价百分数，默认为2.5%
    g.least_premium=2.5
    # 没有买入时,则g.least_premium=max(g.least_premium-0.1,1.5)
    # 一旦买入，则g.no_buy_days=0, g.least_premium=2.5
    # 至少达到的成交量，单位为元，默认为1000万元
    g.least_money=1.0e7
    # 交易费的费率g.trade_fee_ratio，暂定为万2.5，用于计算最少买入金额＝5/g.trade_fee_ratio
    g.trade_fee_ratio=0.00025
    # 最大的持有ETF数量，默认为2只
    g.ETFNum_hold = 2
    # 临时存放基金的全局表列
    g.etf_df=[]
    # 执行所有定时运行
    do_schedule(context)
##
def after_code_changed(context):
    # 取消所有定时运行
    unschedule_all()
    do_schedule(context)
##    
def do_schedule(context):   
    run_daily(pre_process, '09:15', reference_security='000300.XSHG')
    # 买卖操作
    # 卖出时间：在回测时9:30，在模拟或实盘时应在9:27
    run_daily(exe_sell, '09:30', reference_security='000300.XSHG')
    run_daily(exe_buy, '09:30', reference_security='000300.XSHG')
##    
## 预处理函数：得到符合要求的溢价基金    
def pre_process(context):
    etf_list = get_all_securities(['etf'], context.previous_date).index.tolist()
    # 成交金额过滤
    df = history(count=1, unit='1d', field="money", security_list=etf_list).T
    df.columns=['money']
    #成交金额限制（原版是对容量的限制）。这对实盘时的容量影响很大！
    df = df[df.money > g.least_money]
    # 如果是历史净值，读取聚宽平台数据；如果昨日净值，则由爬虫函数get_etf_value获得
    # 现实的日期today，策略运行日的日期current_dt；策略运行时间为09:15，所以当天聚宽函数get_extras读取不到基金净值
    today = datetime.datetime.now().date()
    # 模拟或实盘时注销下面一句，在交易日调试时需要下面这语句！！
    #today=today-datetime.timedelta(days = 1)
    today=today.strftime("%Y-%m-%d")
    print("现实中净值日期：%s" % today)
    current_dt=context.current_dt.strftime("%Y-%m-%d")
    print("策略运行的日期：%s" % current_dt)
    #if current_dt < today:
    if current_dt < today:
        # 1. 聚宽函数获取净值
        df = get_extras('unit_net_value', df.index.tolist(), end_date=context.previous_date, df=True, count=1).T
        df.columns=['unit_net_value']
        g.etf_df = df
        # df的第一列是代码，第二列是成交金额，第三列是净值
        print("ETF净值由聚宽函数get_extras提供。")
    else:
        # 通过自编的爬虫函数get_etf_value及时得到净值，聚宽支持而一创平台不支持
        df['unit_net_value'] = [get_etf_value(etf) for etf in df.index.tolist()]
        #通过爬虫函数get_etf_value，获取货币基金等的净值时用-1代替，此时删除
        df = df[df.unit_net_value != -1]
        print("ETF净值由爬虫函数get_etf_value提供。")
    g.etf_df = df
    # df的第一列是代码（index），第二列是净值unit_net_value
##
## 卖出
def exe_sell(context):
    df = g.etf_df
    current = get_current_data()
    #获得基金开盘价【最早在9:27读取】，并计算溢价'premium'
    df['day_open'] = [current[c].day_open for c in df.index.tolist()]
    df['premium'] = (df.day_open / df.unit_net_value - 1) * 100
    # 因510210.XSHG在2023-06-19分红，导致计算premium错误而在2023-06-20买入，完善如下：
    df['factor'] = [attribute_history(c, 1, '1d', fields=['factor'])['factor'][-1] for c in df.index.tolist()]
    # 为简单处理：对于昨日分红的基金，则不考虑，直接删除
    df=df[df['factor']==1]    
    # 溢价必须在±20%之内，否则净值不合理而删除
    df=df[abs(df['premium'])<20]
    # df的第一列是代码，第二列是成交金额，第三列净值，第四列是最新价，第五列为溢价的百分数
    ## 根据溢价大小排序
    if hasattr(df, 'sort'):
        df = df.sort(['premium'], ascending = True)
    else:
        df = df.sort_values(['premium'], ascending = True)
    print("df=\n%s" % df.head(5))
    df = df[(df.premium < -1.0*g.least_premium)] 
    order_etf = df[:g.ETFNum_hold].index.tolist()
    # 显示需要卖出的etf列表
    etf_to_sell=list(set(context.portfolio.positions.keys())-set(order_etf))
    if len( etf_to_sell)>0:
        log.info(" ## In exe_sell， 需要卖出的ETF列表 ## %s" % etf_to_sell)
        message="需卖："
        N=len( etf_to_sell)
        for i in range(N):
            message=message + etf_to_sell[i][:6]
            if i<N:
                message=message + ","
        send_message(message, channel='weixin')
    # 限价单：为确保卖出，