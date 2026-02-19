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
    # 每日运行
    run_daily(get_stock_list, '9:01')
    run_daily(buy, '09:30')
    run_daily(sell, '14:50')
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
    
    #根据仓位截取列表
    g.target_list = stock_list[:(g.ps - len(context.portfolio.positions))]



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
                print('买入' + s)
                print('———————————————————————————————————')
            
            # 如果开盘未涨停，用市价单即刻买入
            else:
                order_value(s, value, MarketOrderStyle(current_data[s].day_open))
                print('买入' + s)
                print('———————————————————————————————————')
        

def sell(context):
    hold_list = list(context.portfolio.positions)
    current_data = get_current_data()
    
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
                    if current_data[s].last_price > current_data[s].low_limit:
                        order_target_value(s, 0)
                        print('卖出' + s)
                        print('———————————————————————————————————')

# 可以收盘后判断风险决定第二天是否提前卖出，可以降低回撤

############################################################################################################################################################################

# 处理日期相关函数
def transform_date(date, date_type):
    if type(date) == str:
        str_date = date
        dt_date = dt.datetime.strptime(date, '%Y-%m-%d')
        d_date = dt_date.date()
    elif type(date) == dt.datetime:
        str_date = date.strftime('%Y-%m-%d')
        dt_date = date
        d_date = dt_date.date()
    elif type(date) == dt.date:
        str_date = date.strftime('%Y-%m-%d')
        dt_date = dt.datetime.strptime(str_date, '%Y-%m-%d')
        d_date = date
    dct = {'str':str_date, 'dt':dt_date, 'd':d_date}
    return dct[date_type]

def get_shifted_date(date, days, days_type='T'):
    #获取上一个自然日
    d_date = transform_date(date, 'd')
    yesterday = d_date + dt.timedelta(-1)
    #移动days个自然日
    if days_type == 'N':
        shifted_date = yesterday + dt.timedelta(days+1)
    #移动days个交易日
    if days_type == 'T':
        all_trade_days = [i.strftime('%Y-%m-%d') for i in list(get_all_trade_days())]
        #如果上一个自然日是交易日，根据其在交易日列表中的index计算平移后的交易日        
        if str(yesterday) in all_trade_days:
            shifted_date = all_trade_days[all_trade_days.index(str(yesterday)) + days + 1]
        #否则，从上一个自然日向前数，先找到最近一个交易日，再开始平移
        else:
            for i in range(100