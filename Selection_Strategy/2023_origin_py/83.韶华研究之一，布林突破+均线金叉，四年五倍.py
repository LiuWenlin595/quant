# 克隆自聚宽文章：https://www.joinquant.com/post/32129
# 标题：韶华研究之一，布林突破+均线金叉，四年五倍
# 作者：韶华不负

# 导入函数库
from jqdata import *
from six import BytesIO
from jqlib.technical_analysis import *

# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000852.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    set_option("avoid_future_data", True)
    
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')
    
    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    
    g.buylist=[]
    g.selllist=[]
    
    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行--读取brain文件，载入list，供盘中使用
    run_daily(before_market_open, time='before_open')
      # 开盘时运行，开盘、14：05，14：55、收盘--上帝之手的运行部分
    run_daily(market_open, time='open')
    #run_daily(market_run, time ='9:45')
    #run_daily(market_run, time ='14:05')
    run_daily(market_close, time ='14:55')
      # 收盘后运行--总结
    run_daily(after_market_close, time='20:00')
      # 收盘后运行--小强之眼，逐日抓取符合BOLL通道要求的信号，并保存在eye文件中
    run_daily(after_close_eye, time='21:00')
      # 收盘后运行--小强之脑，读取eye文件，抓取之前5日信号，逐条判断金叉信号，分buy和focus,sell，并保存在brain文件中
    run_daily(after_close_brain, time='22:00')
    
## 开盘前运行函数     
def before_market_open(context):
    log.info(str('函数运行时间(before_market_open):'+str(context.current_dt.time())))
    today_date = context.current_dt.date()
    lastd_date = get_trade_days(end_date=today_date, count=2)[0]
    
    g.buylist=[]
    g.selllist=[]

    #第一步，先读入brain文件中昨日信息
    df_list = pd.read_csv(BytesIO(read_file('bug_brain.csv')))
    df_list['date'] = pd.to_datetime(df_list['date']).dt.date
    df_list= df_list[df_list['date'] == lastd_date]
    
    #纳入到四个全局列表中
    for i in range(len(df_list)):
        stockcode = df_list.iloc[i,2]
        if df_list.iloc[i,1] == 'buy':
            if stockcode not in g.buylist:
                g.buylist.append(stockcode)
        elif df_list.iloc[i,1] == 'sell':
            if stockcode not in g.selllist:
                g.selllist.append(stockcode)
    
## 开盘时运行函数
def market_open(context):
    log.info(str('函数运行时间(market_open):'+str(context.current_dt.time())))
    current_data = get_current_data()
    today_date = context.current_dt.date()
    
    ##先是卖的操作
    #1，9：30，根据卖出清单执行
    for key in g.selllist:
        cost = context.portfolio.positions[key].avg_cost
        price = context.portfolio.positions[key].price
        value = context.portfolio.positions[key].value
        intime= context.portfolio.positions[key].init_time
        ret = price/cost - 1
        duration=len(get_trade_days(intime,today_date))
        
        if current_data[key].paused != True:
            if order_target(key,0) != None:
                write_file('bug_log.csv', str('%s,开盘清仓,%s,周期:%s,盈利:%s\n' % (context.current_dt.time(),key,duration,ret)),append = True)
                print('%s开场清仓' % key)
    ##接着买的操作
    if context.portfolio.available_cash <10000: #钱不够了
        return
    
    #资金分配，一只全买，两只以上只买两只
    buy_num =len(g.buylist)
    all_cash = context.portfolio.available_cash
    if buy_num == 0:
        return
    elif buy_num == 1:
        cash_perstk = all_cash
    else:
        cash_perstk = all_cash/2

    for key in g.buylist:
        if context.portfolio.available_cash <10000: #钱不够了
            return
        if current_data[key].paused != True:
            if order_target_value(key,cash_perstk) != None:
                write_file('bug_log.csv', str('%s,开场买入,%s\n' % (context.current_dt.time(),key)),append = True)
                print('%s开场买入%s' % (key,cash_perstk))
    
    #清理buylist，以免盘中混乱        
    for key in g.buylist:
        if key in context.portfolio.positions:
            g.buylist.remove(key)

## 收盘时运行函数
def market_close(context):
    log.info('函数运行时间(market_close):'+str(context.current_dt.time()))
    
    today_date = context.current_dt.date()
    today_time = context.current_dt.time()
    lastd_date = get_trade_days(end_date=today_date, count=2)[0]
    current_data = get_current_data()
    
    buy_num = len(g.buylist)        
    ##先是卖的操作
    #2，根据持仓个股，实时判断盈利率/止损率是否需要清仓
    #盘中清仓条件适当放大，有波动
    for key in context.portfolio.positions:
        cost = context.portfolio.positions[key].avg_cost
        price = context.portfolio.positions[key].price
        value = context.portfolio.positions[key].value
        intime= context.portfolio.positions[key].init_time
        ret = price/cost - 1
        duration=len(get_trade_days(intime,today_date))
        #两种盈速计算方式：起价和低价
        rise_ratio = ret/duration
        
        #df_price = get_price(key, count = duration-1, end_date=lastd_date, frequency='daily', fields=['close'])
        #close_min = df_price['close'].min()
        #rise_ratio = (price/close_min-1)/duration
        
        #创板股提高盈速要求
        if key[0:3] == '688' or key[0:3] == '300':
            if today_date >= datetime.date(2020,9,1):
                rise_ratio = rise_ratio/2
                
        #BOLL蛰伏，优质筛选后可以不用考虑跌停控制
        """
        df_price = get_price(key, count = 3, end_date=lastd_date, frequency='daily', fields=['low_limit', 'high_limit', 'close']) #先老后新  
        if current_data[key].last_price < 1.01*current_data[key].low_limit:
            if order_target(key,0) != None:
                write_file('bug_log.csv', str('%s,收盘跌停卖出,%s,周期:%s,盈利:%s\n' % (today_time,key,duration,ret)),append = True)
                continue
        """
        if ret < -0.1:
            if order_target(key,0) != None:
                write_file('bug_log.csv', str('%s,收盘止损卖出,%s,周期:%s,盈利:%s\n' % (today_time,key,duration,ret)),append = True)
                continue
        elif ret > 0.5:
            if order_target(key,0) != None:
                write_file('bug_log.csv', str('%s,收盘超盈卖出,%s,周期:%s,盈利:%s\n' % (today_time,key,duration,ret)),append = True)
                continue
          
        if duration > 3 and ret < -0.05:
            if order_target(key,0) != None:
                write_file('bug_log.csv', str('%s,收盘长损卖出,%s,周期:%s,盈利:%s\n' % (today_time,key,duration,ret)),append = True)
                continue

        if rise_ratio < 0.015:
            if buy_num == 0:
                continue
            else:
                if duration < 6 and ret > -0.01:
                    continue
                if order_target(key,0) != None:
                    write_file('bug_log.csv', str('%s,收盘后慢处理,%s,周期:%s,盈利:%s\n' % (today_time,key,duration,ret)),append = True)
                    continue


    ##接着买的操作
    #2，先根据买入买入，再监测关注清单，实时判断个股是否站上MA5/10均线，站上即买
    if context.portfolio.available_cash <10000: #钱不够了
        return
    
    for key in g.buylist:
        if key in context.portfolio.positions or current_data[key].paused == True:
            continue
        all_cash = context.portfolio.available_cash
        if buy_num == 1:
            if current_data[key].paused != True:
                if order_target_value(key,all_cash) != None:
                    write_file('bug_log.csv', str('%s,收盘买入,%s\n' % (context.current_dt.time(),key)),append = True)
                    print('%s收盘买入%s' % (key,all_cash))
        else:
            if all_cash > 50000:
                if current_data[key].paused != True:
                    if order_target_value(key,50000) != None:
                        write_file('bug_log.csv', str('%s,收盘买入,%s\n' % (context.current_dt.time(),key)),append = True)
                        print('%s收盘买入%s' % (key,all_cash))
            else:
                if current_data[key].paused != True:
                    if order_target_value(key,all_cash) != None:
                        write_file('bug_log.csv', str('%s,收盘买入,%s\n' % (context.current_dt.time(),key)),append = True)
                        print('%s收盘买入%s' % (key,all_cash))
        
        if context.portfolio.available_cash <10000: #钱不够了
            return
                     
## 收盘后运行函数  
def after_market_close(context):
    log.info(str('函数运行时间(after_market_close):'+str(context.current_dt.time())))
    #总结当日持仓情况
        #盘后遍历持仓，最后每日总结
    today_date = context.current_dt.date()
    
    for stk in context.portfolio.positions:
        cost = context.portfolio.positions[stk].avg_cost
        price = context.portfolio.positions[stk].price
        value = context.portfolio.positions[stk].value
        intime= context.portfolio.positions[stk].init_time
        ret = price/cost - 1
        duration=len(get_trade_days(intime,today_date))
        
        print('股票(%s)共有:%s,入时:%s,成本:%s,现价:%s,收益:%s' % (stk,value,intime,cost,price,ret))
        write_file('bug_log.csv', str('股票:%s,共有:%s,入时:%s,成本:%s,现价:%s,收益:%s\n' % (stk,value,intime,cost,price,ret)),append = True)
        
    print('总资产:%s,持仓:%s' %(context.portfolio.total_value,context.portfolio.positions_value))
    write_file('bug_log.csv', str('%s,总资产:%s,持仓:%s\n' %(context.current_dt.date(),context.portfolio.total_value,context.portfolio.positions_value)),append = True)

## 收盘后运行眼函数
def after_close_eye(context):
    log.info(str('函数运行时间(after_close_eye):'+str(context.current_dt.time())))
    #得到今天的日期和数据
    today_date = context.current_dt.date()
    back_date = get_trade_days(end_date=today_date, count=10)[0]
    rep_back_date = get_trade_days(end_date=today_date, count=60)[0]#eye文件读取的截止日
    all_data = get_current_data()
    
    #1，抓取所有股票列表，过滤ST，退市
    ##排除暂停、ST、退，得到三小特征票
    stockcode_list = list(get_all_securities(['stock']).index)
    stockcode_list = [stockcode for stockcode in stockcode_list if not all_data[stockcode].paused]
    stockcode_list = [stockcode for stockcode in stockcode_list if not all_data[stockcode].is_st]
    stockcode_list = [stockcode for stockcode in stockcode_list if'退' not in all_data[stockcode].name]
    s1_num = len(stockcode_list)
    
    #1，读入eye文件中指定日期段(当前日期往前10天)，用于表内排除
    df_waiting = pd.read_csv(BytesIO(read_file('bug_eye.csv')))
    df_waiting['date'] = pd.to_datetime(df_waiting['date']).dt.date
    df_waiting= df_waiting[(df_waiting['date'] <= today_date) & (df_waiting['date'] >= back_date)]
    wait_list = df_waiting['code'].values.tolist()

    s2_num = 0
    s3_num = 0
    s4_num = 0
    #2，循环小强股，依次过滤仓内的、次新的，十天前已在eye文件中出现的，非boll通道相关特征（狭窄+突破上轨）
    for stockcode in stockcode_list:
        #在仓内、三年内、表内去除
        if stockcode in context.portfolio.positions:
            continue
        if (today_date - get_security_info(stock