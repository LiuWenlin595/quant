# 克隆自聚宽文章：https://www.joinquant.com/post/36489
# 标题：《趋势永存》持续16年跑赢大盘的真正靠谱策略
# 作者：Ahfu

# 克隆自聚宽文章：https://www.joinquant.com/post/26035
# 标题：读《趋势永存：打败市场的动量策略》后的回测经历
# 作者：慕长风

from jqdata import *
import talib
import numpy as np
import math


def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 用真实价格交易
    set_option('use_real_price', True)
    # 规避未来数据
    set_option('avoid_future_data', True)
    # 将滑点设置为0
    set_slippage(FixedSlippage(0))
    # 设置交易成本
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003,
                             close_commission=0.0003, min_commission=5), type='stock')
    # 初始化各类全局变量
    initial_config()
    # 每周交易一次
    run_weekly(trade, weekday=3, time='9:32')
    # 每两周调仓一次（根据波动风险率调整股票仓位）
    run_weekly(adjust_position, weekday=3, time='9:35')


def initial_config():
    log.set_level('order',