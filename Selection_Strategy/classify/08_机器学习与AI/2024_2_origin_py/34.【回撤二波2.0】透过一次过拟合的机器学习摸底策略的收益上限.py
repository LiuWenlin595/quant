# 克隆自聚宽文章：https://www.joinquant.com/post/35253
# 标题：【回撤二波2.0】透过一次过拟合的机器学习摸底策略的收益上限
# 作者：_查尔斯葱_

# 标题：回撤二波
# 作者：查尔斯葱

# 导入函数库
from jqdata import *
from jqlib.technical_analysis import *
import lightgbm as lgb
import pickle

# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')
    # g 内置全局变量
    g.my_security = '000300.XSHG'
    set_universe([g.my_security])
    g.stock_list = []
    # 买入股票数
    g.buy_stock_num = 5
    
    # g.model_path = './gbm_model_v1_all.pkl'
    # g.model_path = './gbm_model_v1_unbalanced.pkl'
    g.model_zb_path = './gbm_fit_model_v1_zb.pkl'
    g.model_cyb_path = './gbm_fit_model_v1_cyb.pkl'
    g.model_zb = pickle.loads(read_file(g.model_zb_path)) # 加载模型
    g.model_cyb = pickle.loads(read_file(g.model_cyb_path)) # 加载模型
    
    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
    # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    # 开盘时运行
    run_daily(market_open_buy, time='09:30', reference_security='000300.XSHG')
    # run_daily(market_open_sell, time='14:00', reference_security='000300.XSHG')
    run_daily(market_open_sell, time='every_bar', reference_security='000300.XSHG')# every_bar 每分钟

    # 收盘后运行before_open
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')


# 买入函数
def market_open_buy(context):
    if len(context.portfolio.positions) < g.buy_stock_num:
        new_buy_stock_num = g.buy_stock_num - len(context.portfolio.positions)
        buy_cash = context.portfolio.available_cash / new_buy_stock_num
        for s in g.stock_list[:new_buy_stock_num]:
            if s not in context.portfolio.positions and\
                context.portfolio.available_cash >= buy_cash >= 100 * get_current_data()[s].last_price:
                order_target_value(s, buy_cash)
                print(f'买入股票：{s}')
                send_message(f'买入股票：{s}')
    
    
## 开盘时运行函数
def market_open_sell(context):
    sells = list(context.portfolio.positions)
    for s in sells:
        keep_days = context.current_dt - context.portfolio.positions[s].init_time
        keep_days = keep_days.days
        loss = context.portfolio.positions[s].price / context.portfolio.positions[s].avg_cost
        s_sell, sell_msg = check_sell_point(context, s)
        if s_sell or loss < 0.95:
            if keep_days >= 0 and context.portfolio.positions[s].closeable_amount>0:
                order_target_value(s, 0)
                print(f'卖出股票：{s}, sell_msg={sell_msg}')
                send_message(f'卖出股票：{s}, sell_msg={sell_msg}')

def check_sell_point(context, stock):
    s_sell = False
    
    #持仓股票的当前价
    current_price = get_current_data()[stock].last_price
    # == context.portfolio.positions[stock].price 
    # 按天交易，【尾盘】跌破MA5或日内高点回撤5个点即撤
    bars = get_bars(stock, 60, '1d', ['close'], include_now=True)
    _close = bars['close']
    _close[-1] = current_price
    # ma3 & ma5
    ma3 = _close[-3:].mean()
    ma5 = _close[-5:].mean()
    ma55 = _close[-55:].mean()
    ma55_ = _close[-56:-1].mean()
    
    # # 按