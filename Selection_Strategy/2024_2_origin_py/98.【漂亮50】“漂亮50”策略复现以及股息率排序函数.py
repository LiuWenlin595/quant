# 克隆自聚宽文章：https://www.joinquant.com/post/36018
# 标题：【漂亮50】“漂亮50”策略复现以及股息率排序函数
# 作者：山东大鹧鸪

# 克隆自聚宽文章：https://www.joinquant.com/post/35174
# 标题：【漂亮50 2.0止损版本】为了降低回撤，加入择时止损模块
# 作者：潜水的白鱼

#文章优化思路：在中证500里面选
#导入函数库
#如有问题，b站私信：“潜水的白鱼”



from jqdata import *
from jqfactor import get_factor_values
import numpy as np
import pandas as pd

#初始化函数 
def initialize(context):
    set_benchmark('000905.XSHG') #参考中证500
    # 用真实价格交易
    set_option('use_real_price', True)
    # 打开防未来函数
    set_option("avoid_future_data", True)
    # 将滑点设置为0
    set_slippage(FixedSlippage(0))
    # 设置交易成本万分之三
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, close_today_commission=0, min_commission=5),type='fund')
    # 过滤order中低于error级别的日志
    log.set_level('order', 'error')
    #选股参数
    g.stock_num = 10 #持仓数
    #交易周期
    g.shiftdays = 10           #换仓周期，5-周，20-月，60-季，120-半年
    g.day_count = 0   
    
    
    # 设置交易时间，每天运行
    run_daily(my_trade, time='9:30', reference_security='000300.XSHG')
    run_daily(zheshi_trade, time='14:55', reference_security='000300.XSHG')
    # run_daily(print_trade_info, time='15:30', reference_security='000300.XSHG')




# ========================主函数-盘中交易部分=======================================================


#4-5 交易模块-择时交易
#结合择时模块综合信号进行交易
def my_trade(context):
    
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

    
    #获取选股列表并过滤掉:st,st*,退市,涨停,跌停,停牌
    check_out_list = get_stock_list(context)                            #调用2-2选股模块
    check_out_list = filter_limitup_stock(context, check_out_list)      #调用过滤函数，排除涨停板和跌停板
    check_out_list = filter_limitdown_stock(context, check_out_list)
    check_out_list = filter_paused_stock(check_out_list)                #以及停牌的股票
    check_out_list = check_out_list[:g.stock_num]                       #选择持仓个数上鞋的作为股票池
    print('今日自选股:{}'.format(check_out_list))
    adjust_position(context, check_out_list)                            #调用4-4调仓模块


# ========================主函数-择时卖出止损模块=======================================================
def zheshi_trade(context):
    #每天都运行
    #对每支持仓股票进行审视
    for stock in context.portfolio.positions:
        #计算这只股票的当前价格
        price = context.portfolio.positions[stock].price
        #获取这只股票近30日最高价
        close30 = history(5, unit='1d', field='close',  security_list=stock, df=True, skip_paused=False, fq='pre')
        max_prices = close30[stock].max()
        
        ret = ((max_prices/price)-1)
        # print(ret)
        if ret >= 0.15:
            # print('hh')
            position = context.portfolio.positions[stock]
            close_position(position)

	






# ========================主函数-尾盘打印持仓信息=======================================================

#5-1 复盘模块-打印
#打印每日持仓信息
def print_trade_info(context):
    #打印当天成交记录
    trades = get_trades()
    for _trade in trades.values():
        print('成交记录：'+str(_trade))
    #打印账户信息
    for position in list(context.portfolio.positions.values()):
        securities=position.security
        cost=position.avg_cost
        price=position.price
        ret=100*(price/cost-1)
        value=position.value
        amount=position.total_amount    
        print('代码:{}'.format(securities))
        print('成本价:{}'.format(format(cost,'.2f')))
        print('现价:{}'.format(price))
        print('收益率:{}%'.format(format(ret,'.2f')))
        print('持仓(股):{}'.format(amount))
        print('市值:{}'.format(format(value,'.2f')))
        print('———————————————————————————————————')
    print('———————————————————————————————————————分割线————————————————————————————————————————')
    
#
# ========================所有需要调用的核心函数=======================================================

#2-1 选股模块
def get_factor_filter_list(context,stock_list,jqfactor,sort,p1,p2):
    yesterday = context.previous_date
    score_list = get_factor_values(stock_list, jqfactor, end_date=yesterday, count=1)[jqfactor].iloc[0].tolist()
    df = pd.DataFrame(columns=['code','score'])
    df['code'] = stock_list
    df['score'] = score_list
    df.dropna(inplace=True)
    df.sort_values(by='score', ascending=sort, inplace=True)
    filter_list = list(df.code)[int(p1*len(stock_list)):int(p2*len(stock_list))]
    return filter_list

#2-2 选股模块 #原先
def get_stock_list(context):
    # initial_list = get_all_securities().index.tolist()
    initial_list = get_index_stocks('000905.XSHG', date = None)
    initial_list = filter_new_stock(context,initial_list)
    initial_list = filter_kcb_stock(context, initial_list)
    initial_list = filter_st_stock(initial_list)

    #按流通市值排序,市值最小的20%剔除
    q = query(valuation.code,valuation.circulating_market_cap).filter(valuation.code.in_(initial_list)).order_by(valuation.circulating_market_cap.asc())
    df = get_fundamentals(q)
    shizhi_list = list(df.code)
    num_1 = int(len(shizhi_list)/4) #前20%这么多不要 ，由小到大
    shizhi_list1 = shizhi_list[num_1:-1]
    print('initial_list:%s'%(len(initial_list)))
    print('shizhi:%s'%(len(shizhi_list1)))
    
    
    indus = get_industries(name='sw_l1', date=context.current_dt) #返回申万指数的标签
    hy_code_list = indus.index.tolist() #行业代码
    print(hy_code_list)
    
    #筛选出各行业前2/3
    peg_all = []
    for hy_code in hy_code_list:
        i_stocklist1 = get_industry_stocks(hy_code, date=None) #获取该行业的成分股
        hyshizhi_list = [x for x in i_stocklist1 if x in shizhi_list1] #得到又在我们股票池又在该行业的成分股
        peg_list=[]
        #####
        if hyshizhi_list:   #如果列表不为空
            #选择peg位于最低2/3
            peg_list = get_factor_filter_list(context, hyshizhi_list, 'PEG', True, 0, 0.7)  #取最小的0.66
        
        else:
            print('列表为空')
    

        for code in peg_list:
            peg_all.append(code)
    print('peg_all:%s'%(len(peg_all)))
    
    
    
    # 同理,筛选出各行业前2/3
    npgr_all = []
    for hy_code in hy_code_list:
        i_stocklist1 = get_industry_stocks(hy_code, date=None) #获取该行业的成分股
        hyshizhi_list = [x for x in i_stocklist1 if x in shizhi_list1] #该行业，peg筛选后的股票
        npgr_list=[]
        if hyshizhi_list:   #如果列表不为空
        #取净利润增长率net_profit_growth_rate最高的2/3
            npgr_list = get_factor_filter_list(context, hyshizhi_list, 'net_profit_growth_rate', False, 0, 0.7)   #取最大的0.7
        else:
            print('列表为空')
    
    
        for code in  npgr_list:
            npgr_all.append(code)
    
    print('npgr_all:%s'%(len(npgr_all)))
    
    #同理,筛选出各行业前1/3
    roe_all = []
    for hy_code in hy_code_list:
        i_stocklist1 = get_industry_stocks(hy_code, date=None) #获取该行业的成分股
        hyshizhi_list = [x for x in i_stocklist1 if x in shizhi_list1] #该行业，npgr筛选后的股票
         #roe最高的1/3
        q1 = query( indicator.code, indicator.roe).filter(indicator.code.in_(hyshizhi_list)).order_by(indicator.roe.desc())  #desc从大到小，asc,从小到大
        df1 = get_fundamentals(q1)
        roe_list = list(df1.code)
        num_2 = int(len(roe_list)/3) #只用前1/3
        roe_list1 = roe_list[0:num_2]
        
        for code in roe_list1:
            roe_all.append(code)
    
    print('roe_all:%s'%(len(roe_all)))
    PNR_all=[]
    for i in peg_all:
        if((i in npgr_all)and(i in roe_all)):
            PNR_all.append(i)

    q3 = query(valuation.code,valuation.circulating_market_cap).filter(valuation.code.in_( PNR_all)).order_by(valuation.circulating_market_cap.desc())
    df3 = get_fundamentals(q3)
    result_list = list(df3.code)#[20:-1]   ##看看到底哪部分比较赚钱：选市值最大的收益率130，市值最小的跑不过大盘，所以选中间的次优龙头
    
    return result_list



# ========================函数2-2调用的筛选st，退市，科创板的股票=======================================================


#3-1 过滤模块-过滤停牌股票
#输入选股列表，返回剔除停牌股票后的列表
def filter_paused_stock(stock_list):
	current_data = get_current_data()
	return [stock for stock in stock_list if not current_data[stock].paused]

#3-2 过滤模块-过滤ST及其他具有退市标签的股票
#输入选股列表，返回剔除ST及其他具有退市标签股票后的列表
def filter_st_stock(stock_list):
	current_data = get_current_data()
	return [stock for stock in stock_list
			if not current_data[stock].is_st
			and 'ST' not in current_data[stock].name
			and '*' not in current_data[stock].name
			and '退' not in current_data[