# 克隆自聚宽文章：https://www.joinquant.com/post/46331
# 标题：WY大神的“龙头打板”策略小改
# 作者：苗老八

# 克隆自聚宽文章：https://www.joinquant.com/post/44926
# 标题：连板龙头策略
# 作者：wywy1995

from jqdata import *
from jqfactor import *
from jqlib.technical_analysis import *
import datetime as dt
import pandas as pd



def initialize(context):
    # 系统设置
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    log.set_level('system', 'error')
    # 分仓数量
    g.ps = 10 #同时最高板龙头一般不会超过10个
    # 聚宽因子
    g.jqfactor = 'VOL5' #5日平均换手率（只是做为示例）
    g.sort = True #选取因子值最小
    
    g.notBuylst = [] # 买入失败的列表 第二天选股时剔除
    
    # 每日运行
    run_daily(get_stock_list, '9:01')
    run_daily(buy, '09:30')
    run_daily(stoploss, '10:30')
    run_daily(stoploss, '13:00')
    run_daily(stoploss, '14:00')
    run_daily(sell, 'every_bar')
    run_daily(print_position_info, '15:02')



# 选股
def get_stock_list(context): 

    # 文本日期
    date = context.previous_date
    date = transform_date(date, 'str')
    
    # 初始列表
    initial_list = prepare_stock_list(date)
    
    # 当日涨停
    hl_list = get_hl_stock(initial_list, date)
    
    # 全部连板股票
    ccd = get_continue_count_df(hl_list, date, 20) if len(hl_list) != 0 else pd.DataFrame(index=[], data={'count':[],'extreme_count':[]})
    
    # 最高连板
    M = ccd['count'].max() if len(ccd) != 0 else 0
    
    # 龙头
    ccd0 = pd.DataFrame(index=[], data={'count':[],'extreme_count':[]})
    CCD = ccd[ccd['count'] == M] if M != 0 else ccd0
    lt = list(CCD.index)

    #可以利用多个因子对lt进行进一步筛选大幅提高收益并降低回撤，使用到的因子见代码末尾

    #打印全部合格股票
    df = get_factor_filter_df(context, lt, g.jqfactor, g.sort)
    stock_list = list(df.index)
    
    #################
    stock_list = remove_values(stock_list,g.notBuylst) 
    #################
    
    
    #根据仓位截取列表
    g.target_list = stock_list[:(g.ps - len(context.portfolio.positions))]
    



# 定义一个函数，用于从list1中移除list2中存在的值
def remove_values(list1, list2):
    return [value for value in list1 if value not in list2]

# 交易
def buy(context):
    current_data = get_current_data()
    value = context.portfolio.total_value / g.ps
    
    for s in g.target_list:
        #由于关闭了错误日志，不加这一句，不足一手买入失败也会打印买入，造成日志不准确
        if context.portfolio.available_cash/current_data[s].last_price>100: 
            # 如果开盘涨停，用限价单排板
            if current_data[s].last_price == current_data[s].high_limit:
                order_value(s, value, LimitOrderStyle(current_data[s].day_open))
                print('限价单买入' + s)
                print('———————————————————————————————————')
            # 如果开盘未涨停，用市价单即刻买入
            else:
                order_value(s, value, MarketOrderStyle(current_data[s].day_open))
                print('市价单买入' + s)
                print('———————————————————————————————————')
                

            # 每日收盘后  查看今日买入和今日选股的列表是否一致  
            # 若不一致则说明有买入失败  则在每日剔除该个股
                
                

def sell(context):
    hold_list = list(context.portfolio.positions)
    current_data = get_current_data()
    hour = context.current_dt.hour
    minute = context.current_dt.minute

    # ------------------处理卖出-------------------
    if minute > 50 and hour == 14:
        for s in hold_list:
            # 条件1：不涨停
            if not (current_data[s].last_price == current_data[s].high_limit):