# 克隆自聚宽文章：https://www.joinquant.com/post/43393
# 标题：稳健趋势策略，回测小，无未来函数
# 作者：语桐

import jqdata
from jqlib.technical_analysis  import *
from jqdata import *
import warnings

# 初始化函数
def initialize(context):
    # 滑点高（不设置滑点的话用默认的0.00246）
    set_slippage(FixedSlippage(0.02))
    # 国证A指数作为基准  
    set_benchmark('399317.XSHE') 
    # 用真实价格交易
    set_option('use_real_price', True)
    set_option("avoid_future_data", True)
    # 过滤order中低于error级别的日志
    log.set_level('order', 'error')
    warnings.filterwarnings("ignore")

    # 选股参数
    g.stock_num = 10 # 持仓数
    g.position = 1 # 仓位
    g.bond = '511880.XSHG'
    # 手续费
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0005, close_commission=0.0005, min_commission=5), type='stock')
     
    # 设置交易时间
    #run_weekly(my_trade, weekday=4, time='9:45', reference_security='000852.XSHG')
    run_monthly(my_trade, monthday=-4, time='11:30', reference_security='000852.XSHG')



# 开盘时运行函数
def my_trade(context):
    # 获取选股列表并过滤掉:st,st*,退市,涨停,跌停,停牌
    check_out_list = get_stock_list(context)
    log.info('今日自选股:%s' % check_out_list)
    adjust_position(context, check_out_list)


# 2-2 选股模块
# 选出资产负债率后20%且大于0，优质资产周转率前20%，roa改善最多的股票列表
def get_stock_list(context):
    # type: (Context) -> list
    curr_data = get_current_data()
    yesterday = context.previous_date
    df_stocknum = pd.DataFrame(columns=['当前符合条件股票数量'])
    # 过滤次新股
    #