# 克隆自聚宽文章：https://www.joinquant.com/post/43375
# 标题：大盘ETF动量轮动RSRS择时策略-无纳指（5年半861%）
# 作者：Gerald3





from jqdata import *
import numpy as np
from jqlib.technical_analysis import *

#初始化函数 
def initialize(context):
    set_benchmark('399006.XSHE')
    set_option('use_real_price', True)
    set_option("avoid_future_data", True)  # 避免引入未来信息
    set_slippage(FixedSlippage(0.001))
    #set_slippage(PriceRelatedSlippage(0.002))
    set_order_cost(OrderCost(open_tax=0, close_tax=0.000, open_commission=0.0001, close_commission=0.0001, close_today_commission=0, min_commission=0),
                   type='fund')
    log.set_level('order', 'error')
    g.stock_pool = [
        # ======== 大盘 ===================
        '510300.XSHG', # 沪深300ETF
        '510050.XSHG', # 上证50ETF
        '159949.XSHE', # 创业板50 

    ]
    
    
    g.stock_num = 1 #买入评分最高的前stock_num只股票
    g.momentum_day = 20 #最新动量参考最近momentum_day的
    g.ref_stock = '000300.XSHG' #用ref_stock做择时计算的基础数据
    g.N = 18 # 计算最新斜率slope，拟合度r2参考最近N天
    g.M = 600 # 计算最新标准分zscore，rsrs_score参考最近M天(600)
    g.K = 8 # 计算 zscore 斜率的窗口大小
    g.biasN = 90 #乖离动量的时间天数
    g.lossN = 20 #止损MA20---60分钟
    g.lossFactor = 1.005 #下跌止损的比例，相对前一天的收盘价
    g.SwitchFactor = 1.04 # 换仓位的比例，待换股相对当前持股的分数
    g.Motion_1diff = 19 # 股票前一天动量变化速度门限
    g.raiser_thr = 4.8 # 股票前一天上涨的比例门限
    g.hold_stock = 'null'
    g.score_thr = -0.68 # rsrs标准分指标阈值
    g.score_fall_thr = -0.43 # 当股票下跌趋势时候， 卖出阀值rsrs
    g.idex_slope_raise_thr = 12 # 判断大盘指数强势的斜率门限
    g.slope_series,g.rsrs_score_history= initial_slope_series() # 除去回测第一天的slope，避免运行时重复加入
    g.stock_motion = initial_stock_motion(g.stock_pool) # 除去回测第一天的动量
    
    run_daily(my_trade_prepare, time='7:00', reference_security='000300.XSHG')
    run_daily(my_trade, time='9:30', reference_security='000300.XSHG')
    run_daily(my_sell2buy, time='9:35', reference_security='000300.XSHG')
    run_daily(check_lose, time='open', reference_security='000300.XSHG')
    # run_daily(print_trade_info, time='15:10', reference_security='000300.XSHG')
    run_daily(pre_hold_check, time='11:25')
    run_daily(hold_check, time='11:27')

# 初始化准备数据,除去回测第一天的slope,zscores
def initial_slope_series():
    length = g.N+g.M+g.K
    data = attribute_history(g.ref_stock, length, '1d', ['high', 'low', 'close'])
    multe_data = [get_ols(data.low[i:i+g.N], data.high[i:i+g.N]) for i in range(length-g.N)]
    slopes = [i[1] for i in multe_data]
    r2s = [i[2] for i in multe_data]
    zscores =[(get_zscore(slopes[i+1:i+1+g.M])*r2s[i+g.M])  for i in range(g.K)]
    return (slopes,zscores)
    
    
## 获取初始化动量因子，除去回测第一天
def initial_stock_motion(stock_pool):
    stock_motion = {}
    for stock in stock_pool:
        motion_que = []
        data = attribute_history(stock, g.biasN + g.momentum_day + 1, '1d', ['close'])
        data = data[:-1]
        bias = (data.close/data.close.rolling(g.biasN).mean())[-g.momentum_day:] # 乖离因子
        score = np.polyfit(np.arange(g.momentum_day),bias/bias[0],1)[0].real*10000 # 乖离动量拟合
        motion_que.append(score)
        stock_motion[stock] = motion_que
    return(stock_motion)
    
    
## 持仓检查，盘中动态止损：早盘结束后，若60分钟周期跌破MA20均线
## 并且当前价格相对昨天没有上涨，则卖出
def pre_hold_check(context):
    if context.portfolio.positions:
        for stk in context.portfolio.positions:
            dt = attribute_history(stk,g.lossN+2,'60m',['close'])
            dt['man'] = dt.close/dt.close.rolling(g.lossN).mean()
            if(dt.man[-1] < 1.0):
                stk_dict = context.portfolio.positions[stk]
                log.info("盘中可能止损，卖出：{}".format(stk))
                send_message("盘中可能止损，卖出：{}".format(stk))
                    
## 并且当前价格相对昨天没有上涨，则卖出
def hold_check(context):
    current_data = get_current_data()
    if context.portfolio.positions:
        for stk in context.portfolio.positions:
            yesterday_di = attribute_history(stk,1,'1d',['close'])
            dt = attribute_history(stk,g.lossN+2,'60m',['close'])
            dt['man'] = dt.close/dt.close.rolling(g.lossN).mean()
            #log.info("man=%0f, last_price=%0f, yester=%0f"%(dt.man[-1], current_data[stk].last_price*1.006, yesterday_di['close'][-1]))
            if((dt.man[-1] < 1.0) and (current_data[stk].last_price*g.lossFactor <= yesterday_di['close'][-1])):
            #if (dt.man[-1] < 1.0):
                stk_dict = context.portfolio.positions[stk]
                log.info('准备平仓，总仓位:{}, 可卖出：{}, '.format(stk_dict.total_amount,stk_dict.closeable_amount))
                send_message("盘中止损，卖出：{}".format(stk))
                if(stk_dict.closeable_amount):
                    order_target_value(stk,0)
                    log.info('盘中止损',stk)
                else:
                    log.info('无法止损',stk)

## 动量因子：由收益率动量改为相对MA90均线的乖离动量
def get_rank(context,stock_pool):
    rank = []
    for stock in stock_pool:
        data = attribute_history(stock, g.biasN + g.momentum_day, '1d', ['close'])
        bias = (data.close/data.close.rolling(g.biasN).mean())[-g.momentum_day:] # 乖离因子
        score = np.polyfit(np.arange(g.momentum_day),bias/bias[0],1)[0].real*10000 # 乖离动量拟合
        adr = 100*(data.close[-1] - data.close[-2])/data.close[-2] #股票的涨跌幅度
        if(stock == g.hold_stock): raise_x = g.SwitchFactor
        else: raise_x = 1
        # data = attribute_history(stock, g.momentum_day, '1d', ['close'])
        # score = np.polyfit(np.arange(g.momentum_day),data.close/data.close[0],1)[0].real # 乖离动量拟合
        #log.info("计算data.close[-1]=%f, data.close[-2]=%f,adr=%f"%(data.close[-1], data.close[-2], adr))