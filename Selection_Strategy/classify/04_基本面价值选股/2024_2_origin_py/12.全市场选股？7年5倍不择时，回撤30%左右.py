# 克隆自聚宽文章：https://www.joinquant.com/post/35307
# 标题：全市场选股？7年5倍不择时，回撤30%左右
# 作者：Jacobb75

# 克隆自聚宽文章：https://www.joinquant.com/post/34964
# 标题：这个策略太牛逼了，今年赚了那么多
# 作者：wgl

# 克隆自聚宽文章：https://www.joinquant.com/post/34964
# 标题：这个策略太牛逼了，今年赚了那么多
# 作者：wgl

# 克隆自聚宽文章：https://www.joinquant.com/post/34862
# 标题：ROE+PB模型的优化
# 作者：wywy1995

# 导入函数库
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
    #by_date = yesterday
    #by_date = datetime.timedelta(days=1200)
    by_date = yesterday - datetime.timedelta(days=1200)  # 三年
    initial_list = get_all_securities(date=by_date).index.tolist()


    # 0. 过滤创业板，科创板，st，今天涨跌停的，停牌的
    initial_list = [stock for stock in initial_list if not (
            (curr_data[stock].day_open == curr_data[stock].high_limit) or
            (curr_data[stock].day_open == curr_data[stock].low_limit) or
            curr_data[stock].paused 
            #curr_data[stock].is_st
            #('ST' in curr_data[stock].name) or
            #('*' in curr_data[stock].name) 
            #('退' in curr_data[stock].name) or
            #(stock.startswith('300')) or
            #(stock.startswith('688')) or
            #(stock.startswith('002'))
    )]
    
    df_stocknum =  df_stocknum.append({'当前符合条件股票数量': len(initial_list)}, ignore_index=True)


    # 1，选出资产负债率由高到低后70%的，low_liability_list
    df = get_fundamentals(
        query