# 克隆自聚宽文章：https://www.joinquant.com/post/32630
# 标题：3年复合200+%收益+超低回撤11%以内，无惧大跌
# 作者：Sunj3001

# 标题：python 2/3无杠杆，稳定盈利的回撤更小的非行业etf轮动2021版 对2020年收益进行了优化
# 作者：sunny 参考：jqz1226 热爱大自然 智习 last modify by sunny by 2020.10.12-16 对风控回撤和收益均大量优化
#非行业14.1.1-20.10.15=724+%收益   2016年回撤最大时20%回撤，15年15%左右   
#非行业17.1.1-20.10.15=376+%收益   4年回撤最大10%左右   
#非行业2019.1.1-2020.10.15=226% 回撤8.9%
#非行业双保险版 2019-1-1-2020-10-15=126% 回撤7.67% 收益比单个要低，回撤接近 近3年回撤优化降至10%以内

#last fixed by 2020.11.5 for python2/3判断通用
#2020/11/6 加上单支ETF止盈 以提高收益, 止损优化
#2020/11/9 ETF印花税为0
#2020/11/11 对于上涨过快进行空仓回撤保护,下跌过快也进行空仓回撤保护
#加入了12月中下旬后保护当年不再交易,加入zz500大盘风控对行情不好时效果有一定改善
#2020/11/13 对选股时也进行上涨和下跌风控改进，对回撤和收益均有显著提升，回撤降至10%以下，收益2020升到320%以上
#特别是对2020年/2018年的提升最为明显，但对2019、2015上半年上涨过快时的效果不如以前了
#last modify by 2020/1/1

from jqdata import *
import pandas as pd
import talib
import numpy
import sys

'''
原理：在多个(行业)种类的ETF中(持续更新中)，持仓1个，ETF池相应的指数分别是
        '159915.XSHE' #创业板、
        '159949.XSHE' #创业板50
        '510300.XSHG' #沪深300
        '510500.XSHG' #中证500
        '510880.XSHG' #上证红利ETF
        '159905.XSHE' #深红利
        '510180.XSHG' #上证180
        '510050.XSHG' #上证50
        '000852.XSHG' #中证1000
        #纳指ETF
        #行业ETF
持仓原则：
    1、对泸深指数的成交量进行统计，如果连续6（lag）天成交量小于7（lag0)天成交量的，空仓处理（购买货币基金511880 银华日利或国债 511010 ）
    2、13个交易日内（lag1）涨幅大于1的，并且“均线差值”大于0的才进行考虑。
    3、对符合考虑条件的ETF的涨幅进行排序，买涨幅最高的1个。
'''


def initialize(context):
    set_params()
    #
    #set_option("avoid_future_data", True) #for python3
    set_option('use_real_price', True)  # 用真实价格交易
    set_benchmark('000300.XSHG')
    log.set_level('order', 'error')
    #
    # 将滑点设置为0
    set_slippage(FixedSlippage(0))
    # 手续费: 采用系统默认设置
    # 股票类每笔交易时的手续费是：买入时佣金万分之2.5，卖出时佣金万分之2.5加千分之一印花税（ETF印花税为0）, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.000, open_commission=0.00025, close_commission=0.00025, min_commission=5), type='stock')

    # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    # 11:30 计算大盘信号
    run_daily(get_signal_back, time='09:58') #优化高收益的回测 止盈
    run_daily(get_signal, time='14:37')
    # 14:40 进行交易
    run_daily(ETFtradeSell, time='14:38')
    run_daily(ETFtradeBuy, time='14:39')

    # 14:53 收盘前检查订单
    run_daily(before_market_close, time='14:53')

# 1 设置参数
def set_params():
    g.ispython3 = (sys.version_info>=(3,0))  #2020/11/05
    print("version:",g.ispython3,sys.version)

    g.use_dynamic_target_market = True  # 是否动态改变大盘热度参考指标
    g.target_market = '000300.XSHG'
    #g.target_market = '399001.XSHE'
    g.empty_keep_stock = '511880.XSHG'  # 闲时买入的标的 ''表示空

    g.signal = 'WAIT'  # 交易信号初始化
    g.emotion_rate = 0  # 市场热度
    g.lag = 6  # 大盘成交量连续跌破均线的天数，发出空仓信号
    g.lag0 = 7  # 大盘成交量监控周期
    g.lag1 = 13  # 比价均线周期
    g.lag2 = 13  # 价格涨幅计算周期
    g.emptyforthreeday = 10.6 #三天最大收益百分比后调仓
    g.emptyforallday = 31 #周期最大收益百分比后调仓
    g.emptymaxday = 3  #最大空仓天数
    g.emptyholdday = 0 #当前空仓天数计数,大于1时有效，为0时不需要空仓处理
    #
    g.buy = []  # 购买股票列表
    # 指数、基金对, 所有想交易的etf都可以，会自动过滤掉交易时没有上市的
    g.ETF_targets =  {
        '399001.XSHE':'150019.XSHE',#深证指数 深证100ETF增强 2010.5 21亿 银华锐进 
        #'399905.XSHE':'159902.XSHE',#中小板指  2006 12亿 华夏
        #'159901.XSHE':'159901.XSHE',#深100etf 2006 78亿 易方达
        '162605.XSHE':'162605.XSHE',#景顺长城鼎益LOF  2005 7亿
        '000016.XSHG':'510050.XSHG',#上证50 2004 484亿 华夏
        '000010.XSHG':'510180.XSHG',#上证180 2006 227亿 华安
        '000015.XSHG':'510880.XSHG',#红利ETF 2006 54亿 华泰柏瑞 #上证红利50指数
        '399324.XSHE':'159905.XSHE',#深红利 工银瑞信 2010.11  36亿 #深证红利40指数
        #'000922.XSHG':'515080.XSHG', #中证红利100深沪 2019.11 3亿 招商 成交量300-2000万
        #'399006.XSHE':'159915.XSHE',#创业板 2011.9 171亿 易方达
        #'150153.XSHE':'150153.XSHE',#创业板B 2013.9 12亿 富国
        #'150152.XSHE':'150152.XSHE',#创业板A 2013.9 9亿 富国
        '399673.XSHE':'159949.XSHE',#创业板50 华安 116亿 2016.6
        
        '000300.XSHG':'510300.XSHG',#沪深300 华泰柏瑞 399亿 2012.5
        #'510330.XSHG':'510330.XSHG',#沪深300 华夏 278亿 2012.12
        #'159919.XSHE':'159919.XSHE',#沪深300 嘉实 242亿 2012.5
        
        '000905.XSHG':'510500.XSHG',#中证500 南方 379亿 2013.2
        #'512500.XSHG':'512500.XSHG',#中证500 华夏 49亿 2015.5
        #'510510.XSHG':'510510.XSHG', #中证500 广发 29亿 2013.4
        '399906.XSHE':'515800.XSHG', #中证800 2019.10 23亿 汇添富
        #'399903.XSHE':'512910.XSHG', #中证100 2019.5 5亿 广发  日成交量800万左右
        #'000852.XSHG':'512100.XSHG', #中证1000  2016.9 2亿 南方 日成交量1000万-1亿左右

        #'515090.XSHG':'515090.XSHG', #可持续 2020.1 3亿 博时 成交量小
        '159966.XSHE':'159966.XSHE', #创蓝筹 2019.6 20亿 华夏
        '159967.XSHE':'159967.XSHE', #创成长ETF 2019.6 9亿 华夏创业动量成长
        #2020.10.19---

        #2020.10.27  科创50 000688.XSHG 待加入
        #'501083.XSHG':'501083.XSHG', #科创银华 15亿 2019.7  成交量300-2000万 科创主题3年封闭3年灵活混合 
        #2020/11/16有效
        #'588000.XSHG':'588000.XSHG', #科创板50指数 华夏上证科创板50 51亿
        #'588080.XSHG':'588080.XSHG', #科创板50指数 易方达上证科创板50 51亿
        
        #'511010.XSHG':'511010.XSHG', #5年期国债ETF 2013.3 11亿 国泰
        '511380.XSHG':'511380.XSHG', #转债ETF 2020.3 11亿 博时
        #'399376.XSHE':'159906.XSHE', #深成长40 2010.12 2亿 大成 日交易100-500万左右
        #'160916.XSHE':'160916.XSHE', #大成优选混合LOF 2012.7 5亿 日交易100-800万左右 成交量低的实盘成交不及时
        #'515200.XSHG':'515200.XSHG', #中证研发创新100指数 2019.10 2亿 早万菱信

        '513500.XSHG':'513500.XSHG',  #标普500 2013.12 22亿 博时  QDII中国人民币ETF基金
        '513100.XSHG':'513100.XSHG',  #纳指ETF 2013.4 11亿 国泰 QDII中国人民币ETF基金
        #'513600.XSHG':'513600.XSHG',  #恒指ETF 2014.12 2.7亿 南方 QDII中国人民币ETF基金
        #'159920.XSHE':'159920.XSHE', #恒生ETF 2012.8 89亿 华夏
        '510900.XSHG':'510900.XSHG', #H股ETF 2012.8 102亿 易方达
        #'513030.XSHG':'513030.XSHG', #德国30ETF 2014.8 10亿 华安DAX龙头 QDII
        #'513000.XSHG':'513000.XSHG', #日经ETF 2019.6 0.7亿 易方达 QDII 规模小交易量低
        #'513050.XSHG':'513050.XSHG', #中概互联 2017.1 45亿 易方达 规模好 QDII 
        #'518880.XSHG':'518880.XSHG', #黄金ETF 2013.7 117亿 #不符合股市大盘规律 降收益了
        
        #'515770.XSHG':'515770.XSHG', #上投摩根MSCI中国 2020.5 5亿
        #'512990.XSHG':'512990.XSHG', #MSCI A股 2015.2 6亿 华夏
        '512160.XSHG':'512160.XSHG' #MSCI中国 2018.4 13.5亿 南方
        
    }
    #
    stocks_info = "\n股票池:\n"
    for security in g.ETF_targets.values():
        s_info = get_security_info(security)
        stocks_info += "【%s】%s 上市日期:%s\n" % (s_info.code, s_info.display_name, s_info.start_date)
    log.info(stocks_info)

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
        return all_date[all_date <= date].tail(count).values[0]
    else:
        return all_date[all_date >= date].head(count).values[-1]


def before_market_open(context):
    if g.emptyholdday > 0: #开盘时计算已经空仓的天数
        g.emptyholdday = g.emptyholdday - 1
    # 确保交易标的已经上市g.lag1个交易日以上
    yesterday = context.previous_date
    list_date = get_before_after_trade_days(yesterday, g.lag1)  # 今天的前g.lag1个交易日的日期
    g.ETFList = {}
    all_funds = get_all_securities(types='fund', date=yesterday)  # 上个交易日之前上市的所有基金
    '''all_idxes = get_all_securities(types='index', date=yesterday)  # 上个交易日之前就已经存在的指数
    for idx in g.ETF_targets:
        if idx in all_idxes.index:
            if all_idxes.loc[idx].start_date <= list_date:  # 指数已经在要求的日期前上市
                symbol = g.ETF_targets[idx]
                if symbol in all_funds.index:
                    if all_funds.loc[symbol].start_date <= list_date:  # 对应的基金也已经在要求的日期前上市
                        g.ETFList[idx] = symbol  # 则列入可交易对象中
    '''
    # fix by sunny 不在要求必须对应的指数，可以用自己基金作为数据
    for idx in g.ETF_targets:
        symbol = g.ETF_targets[idx]
        if symbol in all_funds.index:
            if all_funds.loc[symbol].start_date <= list_date:  # 对应的基金也已经在要求的日期前上市
                g.ETFList[idx] = symbol  # 则列入可交易对象中
    
    #
    return


# 每日交易时for卖出信号，卖和买分开，防止没有立即卖出买不了影响交易
def ETFtradeSell(context):
    if g.signal == 'CLEAR':
        for stock in context.portfolio.positions:
            if stock == g.empty_keep_stock:
                continue
            log.info("清仓: %s" % stock)
            order_target(stock, 0)
        #if (context.current_dt>=datetime.datetime.strptime('2020-10-20', '%Y-%m-%d')): #实盘后发邮件
        #    send_qq_email(str(context.current_dt.date())+"信号:CLEAR","交易日期："+str(context.current_dt.date())+"\n清仓:CLEAR")
    elif g.signal == 'BUY':  #1支时没有用
        if g.empty_keep_stock != '' and g.empty_keep_stock in context.portfolio.positions:
            order_target(g.empty_keep_stock, 0)
        #
        holdings = set(context.portfolio.positions.keys())  # 现在持仓的
        targets = set(g.buy)  # 想买的目标
        #
        # 1. 卖出不在targets中的
        sells = holdings - targets
        for code in sells:
            log.info("卖出: %s" % code)
            order_target(code, 0)
        #if (context.current_dt>=datetime.datetime.strptime('2020-10-20', '%Y-%m-%d')): #实盘后发邮件
        #    send_qq_email(str(context.current_dt.date())+"信号,调","交易日期：