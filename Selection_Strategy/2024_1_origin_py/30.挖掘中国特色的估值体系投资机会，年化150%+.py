# 克隆自聚宽文章：https://www.joinquant.com/post/41763
# 标题：挖掘中国特色的估值体系投资机会，年化150%+
# 作者：子匀

#导入函数库
from jqdata import *
from jqfactor import get_factor_values
import numpy as np
import pandas as pd


def initialize(context):
    # 设定基准
    set_benchmark('000300.XSHG')
    # 用真实价格交易
    set_option('use_real_price', True)
    # 打开防未来函数
    set_option("avoid_future_data", True)
    # 将滑点设置为0
    set_slippage(FixedSlippage(0))
    # 设置交易成本万分之三，不同滑点影响可在归因分析中查看
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, 
                            close_today_commission=0, min_commission=5),type='stock')
    # 过滤order中低于error级别的日志
    log.set_level('order', 'error')      
    log.set_level('system', 'error')
    #初始化全局变量
    g.stock_num = 4        #最大持仓数
    g.limit_up_list = []   #记录持仓中涨停的股票
    g.hold_list = []       #当前持仓的全部股票
    g.limit_days = 20      #不再买入的时间段天数
    g.target_list = []     #开盘前预操作股票池
    do_schedule(context)


def after_code_changed(context):
    # 取消所有定时运行
    unschedule_all()
    do_schedule(context)

    
def do_schedule(context):    
    # 设置交易运行时间
    run_daily(get_stock_list, time='8:00', reference_security='000300.XSHG')                    #准备预操作股票池
    run_daily(prepare_trade,  time='8:05',  reference_security='000300.XSHG')                   #准备预操作股票池
    run_daily(check_limit_up, time='14:00', reference_security='000300.XSHG')                   #检查持仓中的涨停股是否需要卖出
    run_weekly(weekly_adjustment, weekday=1, time='9:30', reference_security='000300.XSHG')     #默认周一开盘调仓，收益最高
    run_weekly(print_position_info, weekday=1, time='15:10', reference_security='000300.XSHG')  #打印复盘信息



#1-1 选股模块
def get_stock_list(context):
    yesterday = context.previous_date
    # 直属国企，央企
    stocklists = ['601919.XSHG', '300073.XSHE', '600536.XSHG', '000951.XSHE', '601628.XSHG', '600036.XSHG', \
            '601818.XSHG', '001289.XSHE', '601111.XSHG', '600787.XSHG', '688396.XSHG', '601611.XSHG', '600795.XSHG',\
            '601390.XSHG', '600489.XSHG', '600007.XSHG', '600938.XSHG', '688187.XSHG', '600026.XSHG', '601898.XSHG', \
            '000066.XSHE', '600862.XSHG', '601658.XSHG', '300374.XSHE', '600900.XSHG', '601881.XSHG', '000999.XSHE', \
            '000009.XSHE', '601106.XSHG', '000928.XSHE', '000797.XSHE', '003816.XSHE', '688779.XSHG', '000807.XSHE', \
            '600845.XSHG', '601965.XSHG', '600158.XSHG', '601319.XSHG', '601989.XSHG', '600916.XSHG', '601668.XSHG',\
            '600760.XSHG', '601398.XSHG', '600905.XSHG', '600176.XSHG', '000996.XSHE', '601766.XSHG', '601328.XSHG', \
            '600028.XSHG', '601808.XSHG', '600150.XSHG', '601800.XSHG', '600875.XSHG', '600486.XSHG', '600030.XSHG', \
            '600685.XSHG', '000777.XSHE', '600970.XSHG', '000617.XSHE', '601336.XSHG', '600019.XSHG', '001979.XSHE', \
            '000733.XSHE', '002080.XSHE', '002013.XSHE', '601318.XSHG', '601117.XSHG', '000927.XSHE', '600705.XSHG', \
            '600737.XSHG', '600977.XSHG', '601857.XSHG', '600372.XSHG', '600061.XSHG', '600025.XSHG', '601995.XSHG', \
            '601618.XSHG', '600730.XSHG', '000877.XSHE', '600406.XSHG', '601888.XSHG', '601006.XSHG', '000786.XSHE',\
            '000166.XSHE', '601985.XSHG', '601601.XSHG', '601816.XSHG', '601179.XSHG', '600050.XSHG', '000758.XSHE', \
            '601088.XSHG', '601868.XSHG', '601598.XSHG', '601698.XSHG', '000625.XSHE', '000629.XSHE', '601186.XSHG', \
            '000768.XSHE', '002401.XSHE', '601858.XSHG', '000069.XSHE', '600999.XSHG', '002179.XSHE', '601872.XSHG', \
            '000799.XSHE', '601728.XSHG', '601600.XSHG', '601788.XSHG', '600764.XSHG', '600886.XSHG', '000708.XSHE',\
            '600056.XSHG', '600011.XSHG', '600893.XSHG', '600941.XSHG', '002268.XSHE', '601236.XSHG', '002415.XSHE', \
            '600048.XSHG', '600027.XSHG', '601939.XSHG', '600118.XSHG', '002116.XSHE', '601988.XSHG', '002051.XSHE', \
            '000800.XSHE', '601998.XSHG', '600765.XSHG', '300140.XSHE', '603126.XSHG', '601288.XSHG', '600115.XSHG', \
            '601669.XSHG', '600029.XSHG', '002916.XSHE', '301269.XSHE', '600482.XSHG']

    stocklists = filter_st_stock(stocklists)
    # 2. 剔除预期增长的后15%
    factor_data = get_factor_values(securities=stocklists, factors=['growth'], end_date=yesterday,count=1)['growth'].iloc[0]
    growth_list = factor_data.sort_values(ascending=False).index.tolist()
    growth_list = growth_list[:int(len(growth_list)*0.80)]

    # 3.按PE、PB复合排序
    df=get_valuation(growth_list,  end_date=yesterday, fields=['pe_ratio','pb_ratio'], count=1).set_index('code')
    # 4.行业比重
    df['sw_code']= ''
    dict1=get_industry(security=growth_list, date=context.previous_date)
    for stock in growth_list :
        df.loc[stock,'sw_code'] = dict1[stock].get('sw_l1')['industry_code']
    # 5 只留下前五年表现极差的四傻 801180	房地产I	801780	银行I	801790	非银金融I	801720	建筑装饰I	    
    df = df[df['sw_code'].isin(['801180','801780','801790','801720'])]    
    df['dense']= df.groupby('sw_code')['pb_ratio'].rank(method='min',ascending=True,pct=True)    
    df['score']=df['dense'] * 0.8+df.pe_ratio.rank(method='min',ascending=True,pct=True)*0.2

    pb_list = (df.sort_values('score',ascending=True)).index.tolist()
    g.target_list = pb_list[:g.stock_num+2] 
    return g.target_list



#1-3 准备交易，推送信息
def prepare_trade(context):
    #1.获取已持有列表
    g.hold_list= list(context.portfolio.positions.keys())
    #2.获取昨日涨停列表
    g.high_limit_list = []
    if g.hold_list != []:
        df = get_price(g.hold_list, end_date=context.previous_date, frequency='daily', fields=['close','high_limit'], count=1, panel=False, fill_paused=False)
        df = df[df['close'] == df['high_limit']]
        g.high_limit_list = list(df.code)



#1-4 整体调整持仓
def weekly_adjustment(context):

    g.target_list = filter_paused