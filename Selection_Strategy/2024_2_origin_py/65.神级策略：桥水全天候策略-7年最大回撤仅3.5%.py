# 克隆自聚宽文章：https://www.joinquant.com/post/37928
# 标题：神级策略：桥水全天候策略-7年最大回撤仅3.5%
# 作者：easy184

# 克隆自聚宽文章：https://www.joinquant.com/post/37611
# 标题：致敬经典作品——小兵哥《一致性风险度量》——极速版
# 作者：jqz1226

# 克隆自聚宽文章：https://www.joinquant.com/post/2116
# 标题：一致性风险度量（桥水全天候为例）
# 作者：小兵哥

import datetime as dt
import math
from jqdata import *
# from kuanke.user_space_api import *


def initialize(context):
    set_benchmark('511010.XSHG')
    set_option('use_real_price', True)
    # 关闭部分log
    log.set_level('order', 'error')
    set_slippage(FixedSlippage(0.002))
    # 交易记录，
    g.transactionRecord, g.trade_ratio, g.positions = {}, {}, {}
    g.hold_periods, g.hold_cycle = 0, 30

    g.QuantLib = QuantLib()

    # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    # 开盘时运行
    run_daily(market_open, time='open', reference_security='000300.XSHG')
    # 收盘后运行
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')


# initialize parameters
def fun_initialize(context):
    """
    因为模拟交易时，会保留参数历史赋值，重新赋值需改名。
    为了避免参数变更后在模拟交易里不生效，单独赋值一次，
    需保留状态的参数，不能放此函数内
    """

    # g.equity = ['510300.XSHG','510500.XSHG','159915.XSHE','510050.XSHG']
    g.equity = ['510300.XSHG']
    # g.commodities = ['160216.XSHE','518880.XSHG','162411.XSHE']
    g.commodities = ['518880.XSHG']
    # g.bonds = ['511010.XSHG','511220.XSHG']
    g.bonds = ['511010.XSHG']
    # g.money_fund = ['513100.XSHG','513500.XSHG']
    g.money_fund = ['513100.XSHG']

    g.confidence_level = 2.58

    # 上市不足 60 天的剔除掉
    # g.equity = g.QuantLib.fun_delNewShare(context, g.equity, 60)
    # g.commodities = g.QuantLib.fun_delNewShare(context, g.commodities, 60)
    # g.bonds = g.QuantLib.fun_delNewShare(context, g.bonds, 60)
    # g.money_fund = g.QuantLib.fun_delNewShare(context, g.money_fund, 60)

    g.pools = g.equity + g