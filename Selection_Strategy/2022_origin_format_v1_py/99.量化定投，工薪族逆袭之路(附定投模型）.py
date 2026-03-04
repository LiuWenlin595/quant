# 克隆自聚宽文章：https://www.joinquant.com/post/21541
# 标题：量化定投，工薪族逆袭之路(附定投模型）
# 作者：东南有大树

"""说明：
1. 可以绑定微信每月接收定投提醒。
2. 国债ETF价位高，可自行在基金市场选择净值低的债券。
3. 由于交易的是ETF，而ETF都是近几年成立的，因此交易时间不要选择的太久远。
4. 定投参数的选择，一定符合切身情况。

"""

import numpy as np
import pandas as pd
from jqdata import *
from six import BytesIO
import prettytable as pt


## 初始化函数
def initialize(context):
    # ======================个性化定投参数设置======================
    g.Take_Risk = True  # 你愿意承担一定的风险吗？（True表示愿意，False表示不愿意）
    g.Have_Work = True  # 当前与未来一段时间，你是否有稳定的工作与收入？（True表示有，False表示没有）
    g.Need_Pay = False  # 当前与未来一段时间，你是否有大量的负债需要偿还？（True表示有，False表示没有）
    g.Base_Money_Min = 10000  # 你最少愿意每个月拿出的定投金额是多少？（默认为1000元）
    g.Base_Money_Max = 100000  # 你最多愿意每个月拿出的定投金额是多少？（默认为4000）
    g.How_Long = 10  # 这项投资你多愿意持仓多久？（默认是10年）
    g.Trade_Security = '000300.XSHG'  # 选择您想参加定投的指数（支持上证50，沪深300，中证500）
    # 评估
    if not evaluate_results():
        return
    # ==============================================================
    
    # 保存pe/pb值
    g.df_pe_pb = None
    # pe百分位值
    g.df_pe_quantile = None
    # 用于计算近N年pe百分位高度
    g.quartile_long = 7
    # 当前应投入金额
    g.save_money = 0
    # 国债ETF
    g.national_debt = '511010.XSHG'
    # 指数与ETF对应关系
    g.index_etf = {'000016.XSHG': '510800.XSHG',
                   '000300.XSHG': '159919.XSHE',
                   '000905.XSHG': '512500.XSHG'}
    # 交易使用的etf
    g.trade_etf = g.index_etf[g.Trade_Security]
    
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，
    # 卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, 
    close_commission=0.0003, min_commission=5), type='stock')

    run_daily(before_trading, time='7:00', reference_security='000300.XSHG')
    run_monthly(inform, monthday=1, time='7:30', reference_security='000300.XSHG')
    run_monthly(month_trade, monthday=1, time='09:30', reference_security='000300.XSHG')


## 开盘前运行函数
def before_trading(context):
    # 1. 计算pe/pb
    g.df_pe_pb = get_pe_pb(context, g.Trade_Security, g.df_pe_pb)
    
    # 2. 计算百分位高度
    g.df_pe_quantile = get_quantile(context, g.Trade_Security, g.df_pe_pb, 'pe', g.quartile_long)

    # 3. 报告近5日估值情况
    tb = pt.PrettyTable(["日期", "pe", "pb", "近" + str(g.quartile_long) + "年pe百分位高度"])
    for i in range(1, 6):
        tb.add_row([str(g.df_pe_pb.index[-i]), 
                    str(g.df_pe_pb['pe'][-i]),
                    str(g.df_pe_pb['pb'][-i]), 
                    str(g.df_pe_quantile['quantile'][-i])])
    index_name = get_security_info(g.Trade_Security).display_name
    log.info('每日报告，' + index_name + '近5个交易日估值信息：\n' + str(tb))
    # 如果想每天接收估值报告，可以打开下面代码
    # send_message('每日报告，' + index_name + '近5个交易日估值信息：\n' + str(tb))
    

## 每月交易函数
def month_trade(context):
    save_money_tuple = get_save_money(context)
    if save_money_tuple[0] == 2:  # 清仓
        inout_cash(save_money_tuple[1], pindex=0)
        order(g.national_debt, save_money_tuple[1])
        log.info('买入{}{}元。'.format(g.national_debt, save_money_tuple[1]))
        order_target_value(g.trade_etf, 0)
        log.info('清仓卖出{}。'.format(g.national_debt))
    elif save_money_tuple[0] == 0:  # 买入国债，等待行情
        inout_cash(save_money_tuple[1], pindex=0)
        order(g.national_debt, save_money_tuple[1])
        log.info('买入{}{}元。'.format(g.national_debt, save_money_tuple[1]))
    elif save_money_tuple[0] == 1:  # 买入指数
        inout_cash(save_money_tuple[1], pindex=0)
        order(g.trade_etf, save_money_tuple[1])
        log.info('买入{}{}元。'.format(g.trade_etf, save_money_tuple[1]))
    else:  # 卖出指数，并买入国债
        inout_cash(save_money_tuple[1], pindex=0)
        order(g.national_debt, save_money_tuple[1])
        log.info('买入{}{}元。'.format(g.national_debt, save_money_tuple[1]))
        order(g.trade_etf, -save_money_tuple[1])
        log.info('卖出{}{}元。'.format(g.national_debt, save_money_tuple[1]))
    
    tb = pt.PrettyTable(["日期", "pe", "pb", "近" + str(g.quartile_long) + "年pe百分位高度"])
    for i in range(1, 6):
        tb.add_row([str(g.df_pe_pb.index[-i]), 
                    str(g.df_pe_pb['pe'][-i]),
                    str(g.df_pe_pb['pb'][-i]), 
                    str(g.df_pe_quantile['quantile'][-i])])

## 风险评估与参数计算
def evaluate_results():
    # 评估结果请查看日志
    tb = pt.PrettyTable(["参数", "值"])
    tb.add_row(["Take_Risk",g.Take_Risk])
    tb.add_row(["Have_Work",g.Have_Work])
    tb.add_row(["Need_Pay", g.Need_Pay])
    tb.add_row(["Base_Money_Min", g.Base_Money_Min])
    tb.add_row(["Base_Money_Max", g.Base_Money_Max])
    tb.add_row(["How_Long", g.How_Long])
    tb.add_row(["Trade_Security", g.Trade_Security])
    
    if not g.Take_Risk or not g.Have_Work or g.Need_Pay:
        result_message = '不建议您参加定投，请先合理规划好生活与工作安排！'
        tb.add_row(["Result", result_message])
        log.info('定投评估：\n' + str(tb))
        return False
    elif g.How_Long < 5:
        result_message = '建议您定投时间参与5年以上，否则不建议参加定投计划！'
        tb.add_row(["Result", result_message])
        log.info('定投评估：\n' + str(tb))
        return False
    elif g.Base_Money_Min < 100:
        result_message = '建议每月定投金额大于100元！'
        tb.add_row(["Result", result_message])
        log.info('定投评估：\n' + str(tb))
        return False
    elif g.Base_Money_Min > g.Base_Money_Max:
        result_message = '每月最大定投额度不得小于每月最小定投额度！'
        tb.add_row(["Result", result_message])
        log.info('定投评估：\n' + str(tb))
        return False
    else:
        result_message = '符合定投计划!'
        tb.add_row(["Result", result_message])
        log.info('定投评估