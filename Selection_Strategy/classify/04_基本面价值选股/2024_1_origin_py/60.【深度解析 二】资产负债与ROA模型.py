# 克隆自聚宽文章：https://www.joinquant.com/post/44328
# 标题：【深度解析 二】资产负债与ROA模型
# 作者：加百力

# 导入函数库
from   jqdata import *
import warnings


# 初始化函数，设置基准等等
# context 是由系统维护的上下文环境
# 包含买入均价、持仓情况、可用资金等资产组合相关信息
def initialize(context):
    
    # 设置的滑点较高（不设置滑点的话用默认的0.00246）
    set_slippage(FixedSlippage(0.02))
    
    # 设置沪深300股指作为基准
    # 如果不设置，默认的基准也是沪深300股指
    set_benchmark('000300.XSHG') 
    
    # 开启动态复权模式(使用真实价格)
    set_option('use_real_price', True)
    
    # 避免使用未来数据
    set_option('avoid_future_data', True)
    
    # 过滤掉order系列API产生的比error级别低的log
    # 默认是 'debug' 参数。最低的级别，日志信息最多
    # 系统推荐尽量使用'debug'参数或不显式设置，方便找出所有错误
    log.set_level('order', 'error')
    
    # 过滤 'ignore' 级别的警告信息
    warnings.filterwarnings('ignore')


    # g. 开头的是全局变量
    # 一经声明整个程序都可以使用
    
    # 选股参数
    
    # 最大股票持仓数量
    g.stock_num = 5
    
    # 仓位比例。计算仓位时使用
    g.position = 1  

    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣 5 元钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
     
    # 设置交易时间
    # 每个月第一个交易日，上午 10:00 调用 my_trade() 函数
    run_monthly(my_trade, monthday=1, time='10:00', reference_security='000300.XSHG')
    



# 交易函数
# 过滤、筛选、排序生成待买入股票列表
# 并根据待交易股票列表开仓或调整仓位
def my_trade(context):
    
    # 过滤：次新股，ST,ST*,退市,涨停,跌停,停牌 股票
    # 根据 资产负债率、不良资产率、优质资产周转率、ROA 增长量等财务指标过滤、排序股票
    # 生成待买入股票列表
    check_out_list = get_stock_list(context)
    
    # 在日志中输出今日准备购买的股票列表
    log.info('今日准备购买的股票:%s' % check_out_list)
    
    # 调整头寸规模
    # 卖出不再列表中的股票
    # 买入新选出的股票
    adjust_position(context, check_out_list)




# 选股模块
def get_stock_list(context):
    
    # 获取当前时间的行情数据
    # 获取当前单位时间（当天/当前分钟）的涨跌停价, 是否停牌，当天的开盘价等
    # 回测时, 通过其他获取数据的API获取到的是前一个单位时间(天/分钟)的数据
    # 而有些数据, 我们在这个单位时间是知道的, 比如涨跌停价, 是否停牌, 当天的开盘价
    curr_data = get_current_data()
    
    # 获取前一个交易日的日期
    yesterday = context.previous_date
    
    # 生成数据框保存每次过滤后，符合条件股票数量
    df_stocknum = pd.DataFrame(columns=['当前符合条件股票数量'])
    
    
    # 过滤次新股
    # datetime.timedelta(days=1200) 获得时间变化量
    # 365*3=1095 天。1200 日是 3 年还多 3 个月
    # by_date 是三年多前的 老日期
    by_date = yesterday - datetime.timedelta(days=1200)
    
    
    # get_all_securities(date=by_date) by_date 日期时在交易的所有股票数据
    # get_all_securities() 可以查询正在交易的 股票、基金、期货、期权 信息
    # 默认查询的时股票数据
    # date=by_date 指定查询的日期是三年多前的 老日期
    # .index 获得的数据类型是 数据框。这个数据框的行索引正是 股票代码
    # .tolist() 转换成列表数据类型
    initial_list = get_all_securities(date=by_date).index.tolist()
    


    # 对初步得到的股票列表做过滤
    # 过滤 当时已经 涨停、跌停 的股票
	# 过滤 当日暂停交易 的股票    
	# 过滤 含有 ST、* 及退市标签 的股票
	# 外围 [] 用于生成列表
	# 内部是一个 for...in 表达式
	# 针对 initial_list 股票列表中的每一只股票代码做分析过滤
	# 括号里面是连续的 or 逻辑表达式，只要满足一个条件就