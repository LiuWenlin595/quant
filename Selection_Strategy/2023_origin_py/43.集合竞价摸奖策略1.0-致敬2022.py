# 克隆自聚宽文章：https://www.joinquant.com/post/36149
# 标题：集合竞价摸奖策略1.0-致敬2022
# 作者：矢南

# 标题：集合竞价摸奖策略1.0
# 作者：矢量化 ；公众号：矢量化
'''
策略思路：
龙头股一般从涨停板开始，涨停板是多空双方最准确的攻击信号，能涨停的个股极有可能是龙头，那么中奖的机会就在涨停板的股票列表里。
打板手法又可以分为打首板，一进二板，二进三板，三进四板，四进五板及更高，博取的是打板次日的情绪或者惯性溢价，所以涨停当日能够
封死涨停及其关键。据网友统计：首板的封死成功率70%；二板的封死成功率20%；三板的封死成功率33%；四板的封死成功率46%；五板的封死
成功率46%。可见，首板成功率较高；二板之后晋级概率较高而且连板的溢价较高；但高板之后因是高位接盘回调幅度相对也较大。故本策略
选的是1板票、3板的股票，力图最高成功率和收益最大化。
1.圈选：昨天收盘后选出1板票、3板票。
2.观察：交易日9:25观察第1步选好的股票，筛选攻击力强的股票，同时技术规避陷阱，准备摸奖。
3.摸奖：开盘即均仓买入第2步选好的股票（或开盘前提高一些价格比如提高1个点挂单）。
4.中奖：等待中奖，或止损
5.策略回测效果：
    集合竞价摸奖策略1.0回测效果：2021年7月15至12月15日，5个月收益122.90%，年化599.72%。
    集合竞价摸奖策略2.0回测效果：2021年7月15至12月15日，5个月收益239.45%，年化1842.21%。
继续努力改进...欢迎进微信群交流分享想法，有兴趣的联系微信：Shi_liang_hua。
'''

# 导入函数库
from jqdata import *
from jqlib.technical_analysis import *
import talib
import warnings
warnings.filterwarnings('ignore')

# 替换代码
def after_code_changed(context):
    unschedule_all()
    set_run_daily()
    
#########################################################################################################
# 初始化函数，设定基准等等
def initialize(context):
    set_option("avoid_future_data", True)
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    log.info('初始函数开始运行且全局只运行一次')
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    #设置运行时间
    set_run_daily()
    # 待买列表
    g.buy_list=[]  

#设置运行时间
def set_run_daily():
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    run_daily(market_open, time='open', reference_security='000300.XSHG')
    run_daily(Call_auction, time='09:25', reference_security='000300.XSHG')
    run_daily(market_open_sell_buy, time='every_bar', reference_security='000300.XSHG')
    run_daily(before_closing, time='14:55', reference_security='000300.XSHG')
    run_daily(after_market_close, time='after