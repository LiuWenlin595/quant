# 克隆自聚宽文章：https://www.joinquant.com/post/35605
# 标题：因子看板多因子模型---由量化课堂多因子模型修改
# 作者：游星

# 克隆自聚宽文章：https://www.joinquant.com/post/1399
# 标题：【量化课堂】多因子策略入门
# 作者：JoinQuant量化课堂

#多因子策略入门
# 2015-01-01 到 2016-03-08, ￥2000000, 每天


'''
================================================================================
总体回测前
================================================================================
'''
import jqfactor
import pandas as pd
import numpy as np
from jqfactor import get_factor_values


#总体回测前要做的事情
def initialize(context):
    set_benchmark('000300.XSHG')
    set_params()        #1设置策参数
    set_variables() #2设置中间变量
    set_backtest()   #3设置回测条件
    set_option("avoid_future_data", True)
#1
#设置策参数
def set_params():
    g.tc=30  # 调仓频率
    g.yb=63  # 样本长度
    g.N=30  # 持仓数目

    g.factors=['total_asset_growth_rate','np_parent_company_owners_growth_rate','financing_cash_growth_rate','net_interest_expense','goods_service_cash_to_operating_revenue_ttm','DAVOL20']
    #因子看板里面因子的名字，因子看板网址https://www.joinquant.com/view/factorlib/list
    g.weights=[[-1],[-1],[-1],[1],[1],[1]]
    # 因子等权重里1表示因子值越小越好，-1表示因子值越大越好
    

#2
#设置中间变量
def set_variables():
    g.t=0              #记录回测运行的天数
    g.if_trade=False   #当天是否交易
    
    
#3
#设置回测条件
def set_backtest():
    set_option('use_real_