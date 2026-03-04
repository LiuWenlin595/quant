# 克隆自聚宽文章：https://www.joinquant.com/post/17302
# 标题：MACD+波动率过滤+追踪止损 期货择时汇总
# 作者：cicikml

# 导入函数库
from jqdata import * 
import talib 
from math import isnan
import re

def initialize(context):
    # 设置参数
    set_parameter(context)
    # 不设定基准，在多品种的回测当中基准没有参考意义
    set_benchmark('511880.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 过滤掉order系列API产生的比error级别低的log
    log.set_level('order', 'error')
    
    ### 期货相关设定 ###
    # 设定账户为金融账户
    set_subportfolios([SubPortfolioConfig(cash=context.portfolio.starting_cash, type='futures')])
    # 期货类每笔交易时的手续费是：买入时万分之01,卖出时万分之1,平今仓为万分之1
    set_order_cost(OrderCost(open_commission=0.0001, close_commission=0.0001,close_today_commission=0.0001), type='index_futures')
    # 设定保证金比例
    set_option('futures_margin_rate', 0.15)
    # 设置滑点双边万分之2
    set_slippage(PriceRelatedSlippage(0.0002),type='future')
    
    # 开盘前运行
    run_daily( before_market_open, time='09:00', reference_security=get_future_code('RB'))
    # 开盘时运行
    run_daily(market_open, time='09:00', reference_security=get_future_code('RB'))
    run_daily(Trade,time='09:00', reference_security=get_future_code('RB'))
    run_daily(TrailingStop,time='09:00', reference_security=get_future_code('RB'))
    # 收盘后运行
    run_daily( after_market_close, time='15:30', reference_security=get_future_code('RB'))
   
# 参数设置函数
def set_parameter(context):
    
    #######变量设置########
    g.LastRealPrice = {} # 最新真实合约价格字典
    g.HighPrice = {} # 各品种最高价字典（用于吊灯止损）
    g.LowPrice = {} # 各品种最低价字典（用于吊灯止损）
    g.TradeLots = {}  # 各品种的交易手数信息
    g.Price_dict = {} # 各品种价格列表字典
    g.Times = {} # 计数器（用于防止止损重入）

    g.ATR = {} # ATR值字典
    g.MACD = {} # MACD值字典
    g.PriceArray = {} # 信号计算价格字典
    g.Filter ={} # 过滤器金额（计算买卖条件）
    g.MappingReal = {} # 真实合约映射（key为symbol，value为主力合约）
    g.Highest_high_2_20 ={}
    g.Lowest_low_2_20= {} 
    g.CurrentPrice = {}
    g.BuyFuture = []
    g.SellFuture = []
    g.dontbuy = {}
    g.dontsellshort = {}
    g.Signal = {}
    g.filter_var = None
    g.cal_var = {}
    
    #######参数设置########
    g.ATRWindow = 10
    g.Cross = 0 # 均线交叉判定信号
    g.NATR_stop = 3 # ATR止损倍数
    g.fastperiod = 3
    g.slowperiod = 7
    g.signalperiod = 7
    # 交易的期货品种信息
    g.instruments = ['AL','NI','CU','PB','AG',
                    'RU','MA','PP','TA','L','V',
                    'M','P','Y','C','CS','JD','SR',
                    'HC','J','I','SF','RB','ZC']
#                    'ZN','SN','BU','A','CF','OI','AP','JM','FG',]
    # 价格列表初始化
    set_future_list(context)


def set_future_list(context):
    for ins in g.instruments:
        idx = get_future_code(ins)
        dom = get_dominant_future(ins)
        # 填充映射字典
        g.MappingReal[ins] = dom
        #设置主力合约已上市的品种基本参数
        if dom == '':
            pass
        else:
            g.HighPrice[dom] = False
            g.LowPrice[dom] = False
            g.Highest_high_2_20[dom] = False
            g.Lowest_low_2_20[dom]=False  
            g.Times[dom] = 0
            
## 开盘前运行函数
def before_market_open(context):
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：'+str(context.current_dt.time()))
    send_message('开始交易')
    
    # 过滤无主力合约的品种，传入并修改期货字典信息
    for ins in g.instruments:
        dom = get_dominant_future(ins)
        if dom == '':
            pass
        else:
            # 判断是否执行replace_old_futures
            if dom == g.MappingReal[ins]:
                pass
            else:
                replace_old_futures(context,ins,dom)
                g.HighPrice[dom] = False
                g.LowPrice[dom] = False
                g.Highest_high_2_20[dom] = False
                g.Lowest_low_2_20[dom]=False  
                g.Times[dom] = 0
                g.MappingReal[ins] = dom


## 开盘时运行函数
def market_open(context):
    
    # 以下是主循环
    g.filter_var = []
    for ins in g.instruments:
        # 过滤空主力合约品种
        if g.MappingReal[ins] != '':
            RealFuture = g.MappingReal[ins]
            # 获取当月合约交割日期
            end_date = get_CCFX_end_date(RealFuture)
            # 当月合约交割日当天不开仓
            if (context.current_dt.date() == end_date):
                return
            else:
                g.LastRealPrice[RealFuture] = attribute_history(RealFuture,1,'1d',['close'])['close'][-1]
                # 获取价格list
                g.PriceArray[RealFuture] = attribute_history(RealFuture,50,'1d',['close','open','high','low'])
                g.CurrentPrice[RealFuture] = g.PriceArray[RealFuture]['close'][-1]
                g.ClosePrice = g.PriceArray[RealFuture]['close']
                # 如果没有数据，返回
                if len(g.PriceArray[RealFuture]['close']) < 50:
                    return
                else:
                    #获取数组型价格信息
                    close = np.array(g.PriceArray[RealFuture]['close'])
                    high =  np.array(g.PriceArray[RealFuture]['high'])
                    low = np.array(g.PriceArray[RealFuture]['low'])
                    
                    # 可交易品种波动率收集
                    g.cal_var[ins] = close[-19:].var()
                    #计算MACD
                    g.MACD[RealFuture] = {}
                    g.MACD[RealFuture]['diff'],g.MACD[RealFuture]['dea'],g.MACD[RealFuture]['macd'] = talib.MACD(close,g.fastperiod ,g.slowperiod,g.signalperiod)
                    
                    DontTrade = []
                    # 刚刚上市的RealFuture可能出现NaN的情况，如果报错则禁止交易该品种
                    try:
                        # 计算ATR
                        g.ATR[RealFuture] = talib.ATR(high,low,close, g.ATRWindow)[-1]
                            # 跌破20日最高点，达到3ATR，禁止开仓
                            # 设置最高价与最低价（注意：需要错一位，不能算入当前价格）
                        g.Highest_high_2_20[RealFuture] = g.PriceArray[RealFuture]['high'][-21:-1].max()
                        g.Lowest_low_2_20[RealFuture] = g.PriceArray[RealFuture]['low'][-21:-1].min()
                            
                        if(g.Highest_high_2_20[RealFuture] - g.LastRealPrice[RealFuture] > 3*g.ATR[RealFuture]):
                            g.dontbuy[ins] = 1
                        else:
                            g.dontbuy[ins] = -1
                        if(g.LastRealPrice[RealFuture] - g.Lowest_low_2_20[RealFuture] > 3*g.ATR[RealFuture]):
                            g.dontsellshort[ins] = 1
                        else:
                            g.dontsellshort[ins] = -1
                            
                    except:
                        print('报错')
                        DontTrade.append(ins)
                        
                    if not isnan(g.MACD[RealFuture]['diff'][-1]) :
                
                        # 判断MACD交叉模式1
                        '''
                        if g.MACD[RealFuture]['