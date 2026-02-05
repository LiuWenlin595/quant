# 克隆自聚宽文章：https://www.joinquant.com/post/47559
# 标题：234板介入-2023年14倍-无未来
# 作者：Clarence.罗

from jqlib.technical_analysis import *
from jqfactor import *
from jqdata import *
import datetime as dt
import pandas as pd
#from jq_sendMsg import *
#from wxpusher import *
import MySQLdb

def initialize(context):
    # 系统设置
    set_option('use_real_price', True)
    # set_option('avoid_future_data', True)
    log.set_level('system', 'error')
    pd.set_option('display.max_columns', None)

    #假定：
    #1 游资手上2亿
    #2 选股看的是流通市值: 50亿以下
    #2 持有了一定的筹码：
    #3 拉升到二板上没多少人卖了，绝对值小于NN？LB小于1.5？
    g.max_free_market_cap = 50 #亿，没用到
    g.max_actual_turnover_ratio = 30 #没用到，仅作提示

    g.max_turnover_ratio = 30
    g.max_LB_1d = 1.875 #比前一天的量比，不是比5日均量

#实盘变更代码后重设全部参数                
def after_code_changed(context):
    unschedule_all()
    # 分仓数量
    g.ps = 1
    # 盘前选股
    g.target_list =[]
    g.strategy = "首板低开200"

    g.sort = True
    g.jqfactor = 'VOL5'
    # 每日运行
    run_daily(get_stock_list, '09:25')


    run_daily(sell_234_if_open_lower_than_96pct, '09:30') #低开太多先跑
    run_daily(sell_if_open_lower_than_92pct, '09:30') #垃圾股先跑
    run_daily(buy_all_cluo, '09:30') #确保卖出了再买

    run_daily(sell_lt, '11:29:00')
    run_daily(sell_lt, '14:52:00')

    #run_daily(sell_if_profit_and_not_HL, '13:59:30') #止盈
    #run_daily(sell_if_not_HL, '14:49:30') #止损
    #run_daily(log_stocks_bought, '15:02')


def sell_lt(context):

  
    #基本信息
    date = transform_date(context.previous_date, 'str')
    hold_list = context.portfolio.positions.keys()
    current_data = get_current_data()
    stock_list = []
    for s in hold_list:
        
        # 条件1：不涨停
        if not (current_data[s].last_price == current_data[s].high_limit):
            if context.portfolio.positions[s].closeable_amount != 0:
                
                # 条件2.1：持有一定时间
                start_date = transform_date(context.portfolio.positions[s].init_time, 'str')
                target_date = get_shifted_date(start_date, 2, 'T')
                current_date = transform_date(context.current_dt, 'str')
                
                # 条件2.2：已经盈利
                cost = context.portfolio.positions[s].avg_cost
                price = context.portfolio.positions[s].price
                ret = 100 * (price/cost-1)
                
                # 在满足条件1的前提下，条件2中只要满足一个即卖出
                if current_date >= target_date or ret > 0:
                    order_target_value(s, 0)
                    print('龙头卖出', [s, get_security_info(s, date).display_name])
                    print('———————————————————————————————————')


# 选股
def get_stock_list(context):
    
    # 基础信息: 昨天开始算
    date = transform_date(context.previous_date, 'str')
    current_data = get_current_data()
    
    # 初始列表（过滤函数兼容研究与回测）
    initial_list = prepare_stock_list(date)

    #昨日
    date_1d = transform_date(context.previous_date, 'str')
    #两天前
    date_2d = get_shifted_date(date_1d, -1, days_type='T')
    #三天前
    date_3d = get_shifted_date(date_2d, -1, days_type='T')
    #三天前
    date_4d = get_shifted_date(date_3d, -1, days_type='T')
    date_5d = get_shifted_date(date_4d, -1, days_type='T')

    hl_list_1d = filter_yzb(get_hl_stock(initial_list, date_1d),date_1d)
    hl_list_2d = get_hl_stock(initial_list, date_2d)
    #hl_list_2d = filter_yzb(get_hl_stock(initial_list, date_2d),date_1d)
    hl_list_3d = get_hl_stock(initial_list, date_3d)
    hl_list_4d = get_hl_stock(initial_list, date_4d)
    hl_list_5d = get_hl_stock(initial_list, date_5d)

    #昨日非一字板，已经放到hl_list_1d = filter_yzb(get_hl_stock(initial_list, date_1d),date_1d)里了
    # def filter_yzb(stock_list, date):
    #stock_list = filter_yzb(stock_list, date_1d)
    #print ("昨日非一字板",stock_list)    

    #stock_list = list( set(hl_list_1d).intersection(set(hl_list_2d)).intersection(set(hl_list_3d)) - set(hl_list_4d)) - set(hl_list_5d) )
    #print ("昨日三连板，且昨日非一字板", stock_list)
    #stock_list = list( set(hl_list_1d).intersection(set(hl_list_2d)) - set(hl_list_3d) - set(hl_list_4d) - set(hl_list_5d) )
    #print ("昨日二连板，且昨日非一字板", stock_list)

    #昨日二、三、四板，且不考虑断板，断板就不是启动的逻辑了
    stock_list = list( set(hl_list_1d).intersection(set(hl_list_2d)).intersection(set(hl_list_3d)).intersection(set(hl_list_4d)) - set(hl_list_5d) )
    #print ("昨日四连板，且昨日非一字板", stock_list)
    stock_list.extend( list( set(hl_list_1d).intersection(set(hl_list_2d)).intersection(set(hl_list_3d)) - set(hl_list_4d) - set(hl_list_5d) ) )
    #print ("昨日三四连板，且昨日非一字板",stock_list)
    stock_list.extend( list( set(hl_list_1d).intersection(set(hl_list_2d)) - set(hl_list_3d) - set(hl_list_4d) - set(hl_list_5d) ) )
    print ("昨日二三四板，且昨日非一字板",stock_list)

    #昨日三、四板，且不考虑断板，断板就不是启动的逻辑了
    #stock_list = list( set(hl_list_1d).intersection(set(hl_list_2d)).intersection(set(hl_list_3d)).intersection(set(hl_list_4d)) - set(hl_list_5d) )
    #print ("昨日四连板，且昨日非一字板", stock_list)
    #stock_list.extend( list( set(hl_list_1d).intersection(set(hl_list_2d)).intersection(set(hl_list_3d)) - set(hl_list_4d) - set(hl_list_5d) ) )
    #print ("昨日三四连板，且昨日非一字板",stock_list)

    #昨日二三板
    #stock_list = list( set(hl_list_1d).intersection(set(hl_list_2d)).intersection(set(hl_list_3d)) - set(hl_list_4d) - set(hl_list_5d) ) 
    #print ("昨日三连板，且昨日非一字板", stock_list)
    #stock_list.extend( list( set(hl_list_1d).intersection(set(hl_list_2d)) - set(hl_list_3d) - set(hl_list_4d) - set(hl_list_5d) ) )
    #print ("昨日二、三板，且昨日非一字板",stock_list)

    #stock_list = list( set(hl_list_1d).intersection(set(hl_list_2d)) - set(hl_list_3d) )
    #print ("昨日二连板，且昨日非一字板", stock_list)
    

    #昨日二三板，可能包含断板，断板就不是启动主升浪的逻辑了，不考虑
    #stock_list = list(set(hl_list_1d).intersection(set(hl_list_2d)))
    #stock_list = list(set(stock_list) - set(hl_list_3d) - set(hl_list_4d))
    #print ("昨日二、三板，且昨日非一字板",stock_list)
    
    # 90日内未出现3连板及以上情况
    if len(stock_list) > 0:
        df = get_continue_count_df1(stock_list, date_4d, 90) 
        #df1 = df[df['count'] >= 4]
        #print ("90日内3连扳过", list(df1.index))
        df = df[df['count'] < 4]
        df = df[df['count'] > 0]
        stock_list = list(df.index)
        print ("此前90日内涨停过有主力，且最高连扳不高于3板的股票", list(stock_list))


    #昨日换手率<g.max_turnover_ratio
    stock_list = [ s for s in stock_list[:] if HSL([s], date_1d)[0][s] < g.max_turnover_ratio ]
    print ("昨日换手率<g.max_turnover_ratio",stock_list)

    #昨天交易量比前天小
    #def get_money(stock_code, N_days_ago=1):
    stock_list = [ s for s in stock_list[:] if get_money(s,1) < get_money(s,2) * g.max_LB_1d ]
    print ("昨天交易量不大于前天g.max_LB_1d倍",stock_list)

    stock_list_with_low_actual_turnover_ratio = []
    for s in stock_list[:]:
        print('———————————————————————————————————')
        free_market_cap, actual_turnover_ratio = get_free_market_cap_and_actual_turnover_ratio(s, date_1d)
        print (s + "【"+ get_security_info(s).display_name + "】")
        print ("流通市值" + str(get_circulating_market_cap(context, s)) + "，换手率" + str( HSL([s], date_1d)[0][s]) )
        print ("自由流通市值" + str(free_market_cap) + "，实际换手率" + str(actual_turnover_ratio))
        if actual_turnover_ratio < g.max_actual_turnover_ratio :
            stock_list_with_low_actual_turnover_ratio.append(s)
        else:
            print ("====>实际换手率过大" + str(actual_turnover_ratio) + "，忽略不要？")
            pass
    #stock_list = stock_list_with_low_actual_turnover_ratio
    print('———————————————————————————————————')

    #昨日收盘价 高于 120 最高价
    #def get_historical_high(stock