# 克隆自聚宽文章：https://www.joinquant.com/post/34876
# 标题：【基本面三角3.0】看过之前策略的就略过吧
# 作者：潜水的白鱼

#作者：白鱼
#标题：三角基本面选股3.0

##策略介绍
#7.26 参考海通的基本面三角组合(盈利，增长，现金流(采用与营收的相对比))，采用静态组合(ROE/inc_total_revenue_year_on_year/ocf_to_revenue)(回测效果为负)，采用三年动态组合
#剔除医药行业，加入择时高位卖出，卖出后补仓的部分
# 导入函数库
from jqdata import *
from kuanke.wizard import * #不能和technical_analysis共存
from sklearn.linear_model import LinearRegression
from jqfactor import get_factor_values
from jqlib.technical_analysis import *
from six import BytesIO
import talib

# 初始化函数，设定基准等等
def after_code_changed(context):
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    unschedule_all()
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')
    set_params()    #1 设置策略参数
    set_variables() #2 设置中间变量
    set_backtest()  #3 设置回测条件

    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
    run_daily(before_market_open, time='7:00')
      # 开盘时运行
    run_daily(market_open, time='9:30')
      # 收盘后运行
    run_daily(market_last,time = '9:32')
    
    run_daily(after_market_close,time ='15:00')


#1 设置策略参数
def set_params():
    #设置全局参数
    #基准及票池
    g.index ='zz'      #all-全A,ZZ100,HS300,ZZ800,ZZ500,ZZ1000
    
    #计分系列，计分方式和计分基准
    g.strategy = 'D'            
    #Delta,基本面三角组合(盈利，增长，现金流(采用与总资产的相对比))，采用静态组合(ROE/inc_total_revenue_year_on_year/OCFOA)

#2 设置中间变量
def set_variables():
    #暂时未用，测试用全池
    g.stocknum = 0              #持仓数，0-代表全取
    g.poolnum = 1*g.stocknum    #参考池数
    #换仓间隔，也可用weekly或monthly
    g.shiftdays = 20           #换仓周期，5-周，20-月，60-季，120-半年
    g.day_count = 0             #换仓日期计数器
    
#3 设置回测条件
def set_backtest():
    ## 设定g.index作为基准
    if g.index == 'all' or g.index == 'zz':
        set_benchmark('000001.XSHG')
    else:
        set_benchmark(g.index)
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    set_option("avoid_future_data", True)
    #显示所有列
    pd.set_option('display.max_columns', None)
    #显示所有行
    pd.set_option('display.max_rows', None)
    log.set_level('order', 'error')    # 设置报错等级
    
## 开盘前运行函数
def before_market_open(context):
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：'+str(context.current_dt.time()))
    #初始化相关参数
    today_date = context.current_dt.date()
    all_data = get_current_data()
    g.poollist =[]
    g.buylist =[]
    g.selllist =[]

        
    #0，判断计数器是否开仓
    if (g.day_count % g.shiftdays ==0): #只管定期换仓
    #if (g.day_count % g.shiftdays ==0) or len(g.selllist) !=0: #去损后动态换仓
        log.info('今天是换仓日，开仓')
        #2，计数器+1
        g.adjustpositions = True  #未知
        g.day_count += 1
    else:
        log.info('今天是旁观日，持仓')
        #2，计数器+1
        g.day_count += 1
        g.adjustpositions = False
        return
    
    #1，若开仓，先根据策略种类进行标的池的积分计算
    #1.1，圈出原始票池，去ST去退去当日停去新(一年),其他特定过滤条件参考全局参数
    if g.index =='all':
        stocklist = list(get_all_securities(['stock']).index)   #取all
    elif g.index == 'zz':
        stocklist = get_index_stocks('000906.XSHG', date = None) + get_index_stocks('000852.XSHG', date = None) #中证800和中证1000
    else:
        stocklist = get_index_stocks(g.index, date = None)
        
    stocklist = [stockcode for stockcode in stocklist if not all_data[stockcode].paused]
    stocklist = [stockcode for stockcode in stocklist if not all_data[stockcode].is_st]
    stocklist = [stockcode for stockcode in stocklist if'退' not in all_data[stockcode].name]
    stocklist = [stockcode for stockcode in stocklist if (today_date-get_security_info(stockcode).start_date).days>365]
    log.info('原始票池%s只' % len(stocklist))
    num1,num2,num3=0,0,0    #用于过程追踪
    #1.2，根据策略种类取相关数据进行积分计算，并根据全局参数返回符合的过滤票池
    #主要策略过滤
    if g.strategy =='D':
        g.poollist = get_delta_stocks(context,stocklist,today_date)   #基本面三角组合
        num1 = len(g.poollist)
    else:
        log.info('没有挑选主要策略')
        return
    
    #次要策略过滤
    
    #先记录票池  
    for stockcode in g.poollist:
        stockname = get_security_info(stockcode).display_name
        write_file('score_log.csv', str('%s,focus,%s,%s\n' % (today_date,stockcode,stockname)),append = True)
        #write_file('value_log.csv', str('%s,focus,%s,%s\n' % (today_date,stockcode,stockname)),append = True)

    #根据预设的持仓数和池数进行标的的选择        
    if g.stocknum ==0 or len(g.poollist) <= g.stocknum:
        g.buylist = g.poollist
    else:
        g.poollist = g.poollist[:g.poolnum]
        g.buylist = g.poollist[:g.stocknum]
        
    # 剔除容易搞假的行业
    z_list = []
    stock_yiyao = get_industry_stocks('C27') #一列医药行业
    for stockcode in g.buylist:
        if stockcode not in stock_yiyao:
            z_list.append(stockcode)
        else:
            pass
    g.buylist = z_list

    return

## 开盘时运行函数
def market_open(context):
    log.info('函数运行时间(market_open):'+str(context.current_dt.time()))
    today_date = context.current_dt.date()
    current_data = get_current_data()

    #0,判断是否换仓日,如果没到换仓的时候直接打断函数
    if g.adjustpositions ==False:
        log.info('今天是持仓日')
        return
    
    #测试自然进出，取消池外卖出
    #1，持仓不在池的卖出
    #因为定期选出的票池数目不固定，全部清出后再重新分配资金买入，以便分析
    #先运行卖出函数

    for stockcode in context.portfolio.positions:
        if current_data[stockcode].paused == True:#这句函数没看懂，这句代表判断是否停牌了，停牌就返回ture
            continue
        if stockcode in g.buylist: #只取前stocknum的
        #if stockcode in g.poollist: #取池内的
            continue
        #非停不在买单则清仓
        sell_stock(context,stockcode,0)
    
    #再运行买入函数
    #2，判断持股数，平均分配买信
    if (len(context.portfolio.positions) >= len(g.buylist)):# and (context.portfolio.available_cash < 0.1*context.portfolio.total_value):
        return
    else:
        cash = context.portfolio.total_value/len(g.buylist)
        for stockcode in g.buylist:
            if current_data[stockcode].paused == True:
                continue
            #不光新买，旧仓也做平衡均分
            buy_stock(context,stockcode,cash)

## 尾盘时运行函数
def market_last(context):
    log.info(str('函数运行时间(after_market_close):'+str(context.current_dt.time())))
    #总结当日持仓情况
    today_date = context.current_dt.date()
    print("t:%s"%(today_date))
    pre_date = context.previous_date
    print(pre_date)
    
    has_sell = []
    for stockcode in context.portfolio.positions:
        cost = context.portfolio.positions[stockcode].avg_cost  # 开仓均价
        price = context.portfolio.positions[stockcode].price    #当前行情价格
        value = context.portfolio.positions[stockcode].value    #总价值
        intime= context.portfolio.positions[stockcode].init_time  #建仓时间
        ret = price/cost - 1 
        #获得5日前价格
        close27 = history(30, unit='1d', field='close',  security_list=stockcode, df=True, skip_paused=False, fq='pre')
        zhangfu_5d = close27[stockcode][-1] / close27[stockcode][-27]-1
        print('zhangfu:%s'%( zhangfu_5d))
        #
        duration=len(get_trade_days(intime,today_date))
        if ret > 0.1 :
            macd = MACD_Direction(stockcode, pre_date)
            if macd == 1 :
                sell_stock(context,stockcode,0)
                has_sell.append(stockcode)
                #同时进行
                #进行补仓    
                for stockcode in context.portfolio.positions:
                    cost = context.portfolio.positions[stockcode].avg_cost  # 开仓均价
                    price = context.portfolio.positions[stockcode].price    #当前行情价格
                    ret = price/cost - 1  
                    if ret > 0 and stockcode not in has_sell :
                        macd = MACD_Direction(stockcode, pre_date)
                        if macd == 2 :
                            cash1 = context.portfolio.available_cash
                            buy_stock(context,stockcode,cash1)
        elif zhangfu_5d > 0.6:
            sell_stock(context,stockcode,0)
            has_sell.append(stockcode)
            #同时进行
            #进行补仓    
            for stockcode in context.portfolio.positions:
                cost = context.portfolio.positions[stockcode].avg_cost  # 开仓均价
                price = context.portfolio.positions[stockcode].price    #当前行情价格
                ret = price/cost - 1  
                if ret > 0 and stockcode not in has_sell :
                    macd = MACD_Direction(stockcode, pre_date)
                    if macd == 2 :
                        cash1 = context.portfolio.available_