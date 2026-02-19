# 克隆自聚宽文章：https://www.joinquant.com/post/30551
# 标题：敢于直接实盘的—八仙过海V2
# 作者：Funine

from jqdata import *
import pandas as pd
import talib

def initialize(context):
    set_params()
    #
    set_option("avoid_future_data",True)
    set_option('use_real_price', True)  # 用真实价格交易
    set_benchmark('000300.XSHG')
    log.set_level('order', 'error')
    #
    # 将滑点设置为0
    set_slippage(FixedSlippage(0.00))
    # 手续费: 采用系统默认设置 
    set_order_cost(OrderCost(close_tax=0.00, open_commission=0.0001, close_commission=0.0001, min_commission=5),
                   type='stock')
    # 开盘前运行L
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    #run_daily(get_signal, time='11:00')
    run_daily(get_signal, time='14:30')
    
    
# 1 设置参数
def set_params():
    g.use_dynamic_target_market = True  # 是否动态改变大盘热度参考指标
    # g.target_market = '000300.XSHG'
    g.target_market = '000300.XSHG'
    g.empty_keep_stock = '511880.XSHG'  # 闲时买入的标的
    # g.empty_keep_stock = '601318.XSHG'#闲时买入的标的
    g.signal = 'BUY'  # 交易信号初始化
    g.lag = 60  #获取前多少天的数据 
    #
    g.buy = []  # 购买股票列表
    g.ETFList = []
    g.cang = {}
    g.allCang = 0
    
def get_before_after_trade_days(date, count, is_before=True):
    """
    来自： https://www.joinquant.com/view/community/detail/c9827c6126003147912f1b47967052d9?type=1
    date :查询日期
    count : 前后追朔的数量
    is_before : True , 前count个交易日  ; False ,后count个交易日
    返回 : 基于date的日期, 向前或者向后count个交易日的日期 ,一个datetime.date 对象
    """
    all_date = pd.Series(get_all_trade_days())
    if isinstance(date, str):
        date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    if isinstance(date, datetime.datetime):
        date = date.date()

    if is_before:
        return all_date[all_date <=