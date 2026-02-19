# 克隆自聚宽文章：https://www.joinquant.com/post/30606
# 标题：筹码选股
# 作者：sonnet_me

from jqdata import *
from datetime import datetime,timedelta
import pandas as pd

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
    #股东人数变动表
    g.shareholder_table=[]
    #十大流通股东持股变动表
    g.institutional_table=[]

    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
    run_monthly(main, monthday=1)
    run_daily(func,time="every_bar")
    #调仓月份
    g.tiao=[5,9,11]
    g.stock=[]
    #延迟买入
    g.delay_buy=[]
    #延迟卖出
    g.delay_sell=[]
    g.max_num = 20
    
# 过滤涨跌停板股票
def limit_price(security_list):
    current_data=get_current_data()
    security_list=[stock for stock in security_list if current_data[stock].last_price!=current_data[stock].high_limit]
    security_list=[stock for stock in security_list if current_data[stock].last_price!=current_data[stock].low_limit]
    return security_list
#过滤停牌、退市、ST股票
def tx_filter(security_list):
    current_data=get_current_data()
    security_list = [stock for stock in security_list if not current_data[stock].paused]
    security_list = [stock for stock in security_list if not '退' in current_data[stock].name]
    security_list = [stock for stock in security_list if not current_data[stock].is_st]
    return security_list

def main(context):
    if context.current_dt.month in g.tiao:
        #提取全市场的个股的代码
        # g.stocks = list(get_all_securities(['stock']).index)
        
        g.stocks = get_index_stocks('000905.XSHG')
        #过滤停牌，ST股，退市股
        g.stocks=tx_filter(g.stocks)
        #获取股东户数选股结果的列表
        Buylist1=check_stock1(context,g.stocks)
        # print('股东户数选股结果：',Buylist1,len(Buylist1))
        #获取机构持股选股的列表
        Buylist2=check_stock2(context,g.stocks)
        # print('机构持股选股结果：',Buylist2,len(Buylist2))
        #使用集合去重两个最终的列表
        final_Buylist=list(set(Buylist1+Buylist2))
        print('去重结果：',final_Buylist,len(final_Buylist))
        q = query(
                valuation.code,
                indicator.inc_revenue_annual
            ).filter(
		        valuation.code.in_(final_Buylist)
	        ).order_by(
		        valuation.pe_ratio < 15,
		        indicator.roa.desc()
		    )
        final_Buylist = list(get_fundamentals(q).code)[:g.max_num]
        print('筛选结果：',final_Buylist,len(final_Buylist))
        trade(context,final_Buylist)