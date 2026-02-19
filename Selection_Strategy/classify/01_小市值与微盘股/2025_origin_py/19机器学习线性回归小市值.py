# 克隆自聚宽文章：https://www.joinquant.com/post/48426
# 标题：机器学习线性回归小市值
# 作者：MarioC

# 克隆自聚宽文章：https://www.joinquant.com/post/40981
# 标题：差不多得了
# 作者：wywy1995

# 克隆自聚宽文章：https://www.joinquant.com/post/40407
# 标题：wywy1995大侠的小市值AI因子选股 5组参数50股测试
# 作者：Bruce_Lee

#https://www.joinquant.com/view/community/detail/30684f8d65a74eef0d704239f0eec8be?type=1&page=2
#导入函数库
from jqdata import *
from jqfactor import *
import numpy as np
import pandas as pd



#初始化函数 
def initialize(context):
    # 设定基准
    set_benchmark('000905.XSHG')
    # 用真实价格交易
    set_option('use_real_price', True)
    # 打开防未来函数
    set_option("avoid_future_data", True)
    # 将滑点设置为0
    set_slippage(FixedSlippage(0))
    # 设置交易成本万分之三，不同滑点影响可在归因分析中查看
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, close_today_commission=0, min_commission=5),type='stock')
    # 过滤order中低于error级别的日志
    log.set_level('order', 'error')
    #初始化全局变量
    g.no_trading_today_signal = False
    g.stock_num = 1
    g.hold_list = [] #当前持仓的全部股票    
    g.yesterday_HL_list = [] #记录持仓中昨日涨停的股票
    g.factor_list = [
        (#ARBR-SGAI-NPtTORttm-RPps
            [
                'ARBR', #情绪类因子 ARBR
                'SGAI', #质量类因子 销售管理费用指数
                'net_profit_to_total_operate_revenue_ttm', #质量类因子 净利润与营业总收入之比
                'retained_profit_per_share' #每股指标因子 每股未分配利润
            ],
[-3.894481386287797e-19, 6.051549381361553e-05,-0.00013489470173496827,
 -0.0006228721291235472]
        ),
        (#P1Y-TPtCR-VOL120
            [
                'Price1Y', #动量类因子 当前股价除以过去一年股价均值再减1
                'total_profit_to_cost_ratio', #质量类因子 成本费用利润率
                'VOL120' #情绪类因子 120日平均换手率
            ],
[-0.007686604605324844 ,-0.001064082235156668 ,-0.0006372186835828526]
        ),
        (#PNF-TPtCR-ITR
            [
                'price_no_fq', #技术指标因子 不复权价格因子
                'total_profit_to_cost_ratio', #质量类因子 成本费用利润率
                'inventory_turnover_rate' #质量类因子 存货周转率
            ],
[-0.00022239096483198066, -0.0003400190412564607, -1.2360751761544718e-08]
        ),
        (#DtA-OCtORR-DAVOL20-PNF-SG
            [
                'debt_to_assets', #风格因子 资产负债率
                'operating_cost_to_operating_revenue_ratio', #质量类因子 销售成本率
                'DAVOL20', #情绪类因子 20日平均换手率与120日平均换手率之比
                'price_no_fq', #技术指标因子 不复权价格因子
                'sales_growth' #风格因子 5年营业收入增长率
            ],
[-0.0013461722141220884, 0.001285717224773847, -0.003021350121015241,
 -0.00023334854089909846, 0.0002343967416749908]
        ),
        (#TVSTD6-CFpsttm-SR120-NONPttm
            [
                'TVSTD6', #情绪类因子 6日成交金额的标准差
                'cashflow_per_share_ttm', #每股指标因子 每股现金流量净额
                'sharpe_ratio_120', #风险类因子 120日夏普率
                'non_operating_net_profit_ttm' #基础科目及衍生类因子 营业外收支净额TTM
            ],
[-6.694922635779981e-11 ,-0.00016142377647805555 ,-0.0005529870175398643,
 9.167393894186556e-12]
        )
    ]
    # 设置交易运行时间
    run_daily(prepare_stock_list, '9:05')
    run_weekly(weekly_adjustment, 1, '9:30')
    run_daily(check_limit_up, '14:00') #检查持仓中的涨停股是否需要卖出
    run_daily(close_account, '14:30')
    run_daily(print_position_info, '15:10')



#1-1 准备股票池
def prepare_stock_list(context):
    #获取已持有列表
    g.hold_list= []
    for position in list(context.portfolio.positions.values()):
        stock = position.security
        g.hold_list.append(stock)
    #获取昨日涨停列表
    if g.hold_list != []:
        df = get_price(g.hold_list, end_date=context.previous_date, frequency='daily', fields=['close','high_limit'], count=1, panel=False, fill_paused=False)
        df = df[df['close'] == df['high_limit']]
        g.yesterday_HL_list = list(df.code)
    else:
        g.yesterday_HL_list = []
    #判断今天是否为账户资金再平衡的日期
    g.no_trading_today_signal = today_is_between(context, '04-05', '04-30')
    
#1-2 选股模块
def get_stock_list(context):
    #指定日期防止未来数据
    yesterday = context.previous_date
    today = context.current_dt
    #获取初始列表
    initial_list = get_all_securities('stock', today).index.tolist()
    initial_list = filter_new_stock(context, initial_list)
    initial_list = filter_kcbj_stock(initial_list)
    initial_list = filter_st_stock(initial_list)
    final_list = []
    #MS
    for factor_list,coef_list in g.factor_list:
        factor_values = get_factor_values(initial_list,factor_list, end_date=yesterday, count=1)
        df = pd.DataFrame(index=initial_list, columns=factor_values.keys())
        for i in range(len(factor_list)):
            df[factor_list[i]] = list(factor_values[factor_list[i]].T.iloc[:,0])
        df = df.dropna()
        df['total_score'] = 0
        for i in range(len(factor_list)):
            df['total_score'] += coef_list[i]*df[factor_list[i]]
        df = df.sort_values(by=['total_score'], ascending=False) #分数越高即预测未来收益越高，排序默认降序
        complex_factor_list = list(df.index)[:int(0.1*len(list(df.index)))]
        q = query(valuation.code,valuation.circulating_market_cap,indicator.eps).filter(valuation.code.in_(complex_factor_list)).order_by(valuation.circulating_market_cap.asc())
        df = get_fundamentals(q)
        df = df[df['eps']>0]
        lst  = list(df.code)
        lst = filter_paused_stock(lst)
        lst = filter_limitup_stock(context, lst)
        lst = filter_limitdown_stock(context, lst)
        lst = lst[:min(g.stock_num, len(lst))]
        for stock in lst:
            if stock not in final_list:
                final_list.append(stock)
    return final_list

#1-3 整体调整持仓
def weekly_adjustment(context):
    if g.no_trading_today_signal == False:
        #获取应买入列表 
        target_list = get_stock_list(context)
        #调仓卖出
        for stock in g.hold_list:
            if (stock not in target_list) and (stock not in g.yesterday_HL_list):
                log.info("卖出[%s]" % (stock))
                position = context.portfolio.positions[stock]
                close_position(position)
            else:
                log.info("已持有[%s]" % (stock))