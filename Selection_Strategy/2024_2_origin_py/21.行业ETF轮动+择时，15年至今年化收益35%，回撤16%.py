# 克隆自聚宽文章：https://www.joinquant.com/post/36544
# 标题：行业ETF轮动+择时，15年至今年化收益35%，回撤16%
# 作者：Jacobb75

"""

程序运行原理：
1、给定大盘指数：上证，深成指，创业板指数，科创50，沪深300，中证500,1000指数
2、给定17只行业指数基金
3、判断指数基金是否正常上市
4、判断5个大盘是否处于上涨趋势（获取大盘上涨最大的代码）
5、判断17只大盘指数基金的中期BBI指标（多空指标）
6、如果涨幅最好的大盘指数是上涨的（市场今天可以），则买入BBI指标中多头最强的指数基金（大概率也是指数对应的基金)

7、下一周期重新进入1-5的判断，如果大盘都是下跌的，清仓，套现的钱买银华日利
                            如果表现做好的大盘是上涨的，则买入BBI最小的基金，清空持有的基金，套现的钱买银华日利
                            如果买入BBI最小的基金已经持仓，则不操作
如果大盘不好（300etf 5日均线空头排列），清仓，买入银华日利基金；
如果大盘上涨，则买入BBI指标中的多头最强的，第二天循环判断
程序实现了亏小，赢大的可能

为什么选周三运行？
不清楚，只是周三运行表现最好；我判断可能因为周三是周内情绪发酵的拐点，变数最大

为什么选中午11：15交易？
牛市11：15开盘原因：各大机构收盘后制定第二套买卖计划，会在9点30到10点30之间完成，有买入的这段
时间都是上涨的，之后会有一段时间回落，在回落时间段内，我们买入。（一般来说中午收盘前都可以，模型表现差异不大，自己选个时间就好）

"""

# 导入聚宽函数库
import jqdata
from jqlib.technical_analysis  import *
from jqdata import *

# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
   
    set_slippage(FixedSlippage(0.004))
    #没有滑点设置的话使用系统默认的PriceRelatedSlippage(0.00246)
    set_option("avoid_future_data", True)
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')

    set_benchmark('000300.XSHG')
    ### 股票相关设定 ###
    # ETF基金场内交易类每笔交易时的手续费是：买入时佣金万分之一点五，卖出时佣金万分之一点五，无印花税, 每笔交易佣金最低扣0块钱
    set_order_cost(OrderCost(close_tax=0.00, open_commission=0.00015, close_commission=0.00015, min_commission=5), type='fund')
    
    ## 运行函数
    # 开盘时运行
    run_daily(make_sure_etf_ipo, time='9:15')
    run_weekly(market_buy, weekday=3,time='11:15')#每周三中午11：15交易

    # 最强指数涨了多少，可以开仓
    g.dapan_threshold = 0#大盘阈值
    g.signal= 'BUY'
    g.niu_signal = 1 # 牛市就上午开仓，熊市就下午
    g.position = 1
    
    # 基金上市了多久可以买卖
    g.lag1 =20
    g.decrease_days = 0 #递减
    g.increase_days = 0 #递增
    # bbi动量的单位
    g.unit = '30m'
    g.bond = '511880.XSHG'#清仓状态资金买入银华日利货币基金）
    
    #python中的中括号[ ]，代表list列表数据类型

    
    #大盘指数
    g.zs_list = [
        '000001.XSHG',#上证综指
        '399001.XSHE',#深证成指
        '000300.XSHG',#沪深300
        '000905.XSHG',#中证500
        '000852.XSHG',#中证1000
        '399006.XSHE',#创业板
        '000688.XSHG',#科创50
        ]  
        
    #python大括号{ }花括号：代表dict字典数据类型，字典是由键对值组组成。冒号':'分开键和值，逗号','隔开组
    # 指数、基金对, 所有想交易的etf都可以，会自动过滤掉交易时没有上市的
    
    #行业指数：指数对应的基金
    g.ETF_list =  {
        '000986.XSHG':'515220.XSHG', # 传统能源(煤）
        '000827.XSHG':'516070.XSHG', # 新能源
        '399967.XSHE':'512660.XSHG', # 军工
        '000995.XSHG':'159611.XSHE', # 电力
        '000987.XSHG':'159944.XSHE', # 材料
        '000813.XSHG':'516120.XSHG', # 化工
        '000989.XSHG':'159928.XSHE', # 消费
        '399997.XSHE':'512690.XSHG', # 白酒
        '000991.XSHG':'512170.XSHG', # 医药
        '399971.XSHE':'512980.XSHG', # 传媒
        '399986.XSHE':'512800.XSHG', # 银行
        '399975.XSHE':'159841.XSHE', # 证券
        '000993.XSHG':'512480.XSHG', # 信息
        '000922.XSHG':'515080.XSHG', # 中证红利
        '399440.XSHE':'515210.XSHG', # 钢铁
        '399814.XSHE':'159825.XSHE', # 农业
        '399995.XSHE':'516970.XSHG', # 基建
    }
    
    #复制g.EFT_list到g.not_ipo_list
    #copy() 函数用于复制列表，类似于 a[:]
    g.not_ipo_list = g.ETF_list.copy()
    g.available_indexs = []
    
    
    
    
##  交易！
def market_buy(context):
    #log.info(context.current_dt.hour)#信息输出：当前时间的小时段
    
    # for etf in g.ETF_targets:
    #建立df_index表，字段为：指数代码，周期动量
    df_index = pd.DataFrame(columns=['指数代码', '周期动量'])
    # 判断四大指数是否值得开仓
    #建立df_incre表，字段为：大盘代码，周期涨幅，当前价格
    df_incre = pd.DataFrame(columns=['大盘代码','周期涨幅','当前价格'])
    """
    BBI2 = BBI(g.available_indexs, check_date=context.current_dt, timeperiod1=3, timeperiod2=6, timeperiod3=12, timeperiod4=24,unit=unit,include_now=True)
    BBI2 = BBI(股票列表, check_date=日期, timeperiod1=统计天数N1, timeperiod2=统计天数N2, timeperiod3=统计天数N3, timeperiod4=统计天数N4,unit=统计周期,include_now=是否包含当前周期)
    返回结果类型：字典(dict)：键(key)为股票代码，值(value)为数据。
    用法注释：1.股价位于BBI 上方，视为多头市场； 2.股价位于BBI 下方，视为空头市场。
    计算方法：BBI=(3日均价+6日均价+12日均价+24日均价)÷4
    判断指数的BBI，多空指数
    """
    unit =g.unit
    BBI2 = BBI(g.available_indexs, check_date=context.current_dt, timeperiod1=21, timeperiod2=34, timeperiod3=55, timeperiod4=89,unit=unit,include_now=True)#斐波那契数列的中期BBI

    for index in g.available_indexs:#运行中的指数
        df_close = get_bars(index, 1, unit, ['close'],  end_dt=context.current_dt,include_now=True,)['close']#读取index当天的收盘价
        val =   BBI2[index]/df_close[0]#BBI除以交易当天11:15分的价格，大于1表示空头，小于1表示多头
        df_index = df_index.append({'指数代码': index, '周期动量': val}, ignore_index=True)#将数据写入df_index表格，索引重置
    #按'周期动量'进行从大到小的排列。ascending=true表示降序排列,ascending=false表示升序排序，inplace = True：不创建新的对象，直接对原始对象进行修改
    df_index.sort_values(by='周期动量', ascending=False, inplace=True)
    log.info(df_index)
    
    target = df_index['指数代码'].iloc[-1]#读取最后一行的指数代码
    target_bbi = df_index['周期动量'].iloc[-1]#读取最后一行的周期动量

    for index in g.zs_list:#大的指数判断
        df_close = get_bars(index, 3, '1d', ['close'],  end_dt=context.current_dt,include_now=True,)['close']#读取当前日期的前2天日K线图，包括当天的收盘价格，今天的收盘价，这是不是未来指数
        #print(df_close