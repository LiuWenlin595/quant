# 克隆自聚宽文章：https://www.joinquant.com/post/32130
# 标题：韶华研究之二，顺势而为，年化140
# 作者：韶华不负

# 导入函数库
from jqdata import *
from six import BytesIO
from jqlib.technical_analysis import *
import pandas as pd
import os

# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    g.benchmark = '000300.XSHG'
    set_benchmark(g.benchmark)

    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    set_option("avoid_future_data", True)
    
    #18-20年数据回测后所得行业白名单
    g.indus_list = ['801010','801080','801120','801140','801150','801210','801710','801750','801760','801780','801790','801880']
    g.buylist=[]
    g.selllist=[]
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')

    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.000