#!/usr/bin/env python
# coding: utf-8

# 导入函数库
from jqdata import *
import numpy as np
import pandas as pd
import talib as tl
import datetime
from math import isnan
import warnings

warnings.filterwarnings('ignore')


# 策略开始
def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    log.info('初始函数开始运行且全局只运行一次')
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),
                   type='stock')
    # 设定相关参数
    set_params()
    if g.run_monthly == True:
        run_monthly(before_market_open, monthday=1, time='09:30')
        run_monthly(market_open, monthday=1, time='09:30')
    else:
        run_daily(before_market_open, time='open')
        run_daily(market_open, time='open')


def set_params():
    g.n = 3  # 移动平均窗口
    g.bulin_n = 25  # 布林带数据长度
    g.position = 0
    g.stocks = '000300.XSHG'
    g.bulin_upper_dev = 1.8  # 布林带上限标准差倍数
    g.bulin_lower_dev = 1.8
    g.run_monthly = True
    g.num_date = 90
    g.reserve_ratio_delay = 120  # 存款准备金率取之前数据的周期
    g.weight = [1, 1, 2, 1, 1]  # 'monetary','forex','credit','boom','inflation'


## 开盘前运行函数
def before_market_open(context):
    log.info('函数运行时间(before_market_open)：' + str(context.current_dt.time()))
    #
    current_date = context.current_dt.date()
    last_five_months = get_last_month(current_date, g.n + 2)  # ['2019-10','2019-09',...]
    previous_date = context.previous_date.strftime('%Y-%m-%d')

    # 过去g.num_date个交易日的列表（不含今天）
    past_90_trade_days = [datetime.date.strftime(x, '%Y-%m-%d') for x in
                          get_trade_days(end_date=previous_date, count=g.num_date - 1)]

    # ts_data = change_to_tushare_date(trade_days_one_month)

    # PMI择时: PMI的三个月MA，上月超过了前月：1,否则：0
    pmi_position = get_PMI(last_five_months)  # 1, 0
    # SHIBOR利率择时
    shibor_position = get_SHIBOR(past_90_trade_days)
    # 国债择时
    gz_position = get_gz(past_90_trade_days)
    # 企业债择时
    qyz_position = get_qyz(past_90_trade_days)
    # M1 - M2同比剪刀差择时
    mc_position = get_M1_M2(last_five_months)
    # # 存款准备金率择时
    # reserve_ratio_position = get_reserve_ratio_from_csv(previous_date)
    # 社会融资总额择时
    aggregate_fin_position = get_aggregate_financing(last_five_months)
    # 汇率择时
    huilv_position = get_exchange_rate(past_90_trade_days)
    # 通胀指数 PPI - CPI 择时
    inf_position = get_inflation_index(last_five_months)
    # 货币政策择时指标=利率+期限利差+信用利差
    # 考虑存款准备金率
    huobi_position = (shibor_position + gz_position + qyz_position) / 3.0
    # 信贷择时指标 = M1、M2剪刀差 + 社融指标
    credit_loan_postition = (mc_position + aggregate_fin_position) / 2.0
    # 汇总择时指标
    all_position = [huobi_position, huilv_position, credit_loan_postition, pmi_position, inf_position]
    # 计算分值
    all_position = np.array(all_position)
    weight = np.array(g.weight)
    position = (all_position * weight).sum() / len(weight)
    if position > 0.55:
        g.position = 1
    elif position < 0.45:
        g.position = -1
    else:
        g.position = 0


# ------------代码第2部分-------------------#
def market_open(context):
    all_value = context.portfolio.total_value
    if g.position == 1:
        log.info('开始下单:全仓')
        order_target_value(g.stocks, all_value)
    # elif g.position == 0:
    #     log.info('开始下单:半仓')
    #     order_target_value(g.stocks, all_value / 2)
    else:
        if len(context.portfolio.positions) > 0:
            log.info('清仓')
            order_target(g.stocks, 0)


##################################工具函数###################################################
def get_last_month(p_date, n):
    # type: (datetime.date, int) -> List[str]
    '''
    返回过去的n=5个月的升序列表：['2019-06', '2019-07', '2019-08', '2019-09', '2019-10']
    '''
    _date = p_date
    list_month = []
    for i in range(n):
        _date = _date.replace(day=1) - datetime.timedelta(days=1)  # 本月1号减1天，得到上个月月末日期
        list_month.insert(0, datetime.date.strftime(_date, '%Y-%m'))
    return list_month


# 获取PMI数据 OK
def get_PMI(month_list):
    # type: (list) -> int
    a = macro.MAC_MANUFACTURING_PMI
    q = query(a.stat_month, a.pmi).filter(a.stat_month.in_(month_list))
    pmi = macro.run_query(q)
    pmi_mean = pmi['pmi'].rolling(g.n).mean()
    return 1 if pmi_mean.values[-1] > pmi_mean.values[-2] else 0


# 获取货币供应量数据 OK
def get_M1_M2(month_list):
    m_s = pd.read_csv('money_supply_05-19.csv')
    m_s = m_s.set_index(m_s.columns[0])
    m_select = m_s.loc[month_list]
    m_s_diff: pd.Series = (m_select['m1_yoy'] - m_select['m2_yoy'])
    diff_mean = m_s_diff.rolling(g.n).mean()
    # M1,M2一般在次月中上旬发布，例如2018年12月11日发布了2018年11月的数据，因此当月的择时需参考上上个月的指标
    return 1 if diff_mean.values[-2] > diff_mean.values[-3] else 0


# 社会融资规模 OK
def get_aggregate_financing(month_list):
    af = pd.read_csv('aggretate_signal_data_02_19.csv')
    af = af.set_index(af.columns[0])
    res = af.loc[month_list]
    res_mean = res.iloc[:, 0].rolling(g.n).mean()
    #
    return 1 if res_mean.values[-2] > res_mean.values[-3] else 0  # 参考上上个月


# 获取通胀指数 PPI - CPI: OK
def get_inflation_index(month_list):
    inf = pd.read_csv('cpi_ppi_0501_1902.csv')
    inf = inf.set_index(inf.columns[0])
    inf = inf.loc[month_list]
    inf_diff: pd.Series = inf['ppi同比'] - inf['cpi同比']
    inf_diff_mean = inf_diff.rolling(g.n).mean()
    inf_position = 1 if inf_diff_mean.values[-2] < inf_diff_mean.values[-3] else 0  # 参考上上个月, 下降为1
    label = 1 if 0 <= inf_diff_mean.values[-2] < 5 else 0  # good_cpi: 0~5
    return inf_position * label


# 获取shibor数据 OK
def get_SHIBOR(date_list):
    shibor = pd.read_csv('shibor.csv')
    shibor = shibor.set_index(shibor.columns[0])
    shibor = shibor.loc[date_list]
    shibor = shibor.drop_duplicates()
    # 一个月利率
    shibor_1m: np.ndarray = shibor['1m'].values
    # position
    return bbands_select_time(shibor_1m, 'lower', g.bulin_n, g.bulin_upper_dev, g.bulin_lower_dev)


# 汇率数据: OK
def get_exchange_rate