# 克隆自聚宽文章：https://www.joinquant.com/post/42706
# 标题：基于XGBoost_6m滚动选股策略
# 作者：雨汪

# 导入函数库
from jqdata import *
import numpy as np
import datetime
import pandas as pd
from jqfactor import get_factor_values
from jqfactor import winsorize_med
from jqfactor import standardlize
from jqfactor import neutralize
from scipy import stats
import statsmodels.api as sm
from statsmodels import regression
from jqlib.technical_analysis import *
from sklearn import svm
from xgboost import XGBClassifier
from sklearn.model_selection import GridSearchCV
from sklearn import metrics
import pickle


# 初始化函数，设定基准等等
def initialize(context):
    # 设定基准
    # g.benchmark = '000300.XSHG' #沪深300
    # g.benchmark = '000852.XSHG' #中证1000
    g.benchmark = '399905.XSHE' #中证500
    # g.benchmark = '399006.XSHE' #创业板指

    set_benchmark(g.benchmark)
    # 开启防未来函数
    set_option('avoid_future_data', True)
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    # 过滤掉order系列API产生的比error级别低的log
    log.set_level('order', 'error')

    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    set_slippage(PriceRelatedSlippage(0)) 
    
    g.all_A = True #是否全A选股
    g.signal = True #开仓信号
    g.alllist = [] #股票池
    g.hold_list = [] # 今日持有的股票
    g.high_limit_list = [] # 前日涨停的股票
    g.stock_num = 10 #最大持仓个数
    
    g.windows = 6 #滚动训练窗口大小
    g.factor_cache = {} #因子缓存器
    
    g.regressor = XGBClassifier # 选用模型
    g.params = {'max_depth': 3, 'learning_rate': 0.05, 'subsample': 0.8} #经验参数
    # g.parameters = {'subsample':(0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1),
    #              'max_depth':(3, 4, 5, 6, 7, 8)} #交叉验证参数
    
    # g.regressor = svm.SVC # 选用模型
    # g.params = {'C': 3, 'gamma': 0.03} #经验参数
    # g.parameters = {'C':(0.01, 0.03, 0.1, 0.3, 1, 3, 10),
    #             'gamma':[1e-4, 3e-4, 1e-3, 3e-3, 0.01, 0.03, 0.1, 0.3, 1]} #交叉验证参数

    g.is_cv = False #是否交叉验证    

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
    # 开盘前运行
    run_daily(before_market_open, time='9:05', reference_security='000300.XSHG')
    # 开盘时运行
    run_daily(market_open, time='9:30', reference_security='000300.XSHG')
    # 开板止盈
    run_daily(check_limit_up, time='14:30', reference_security='000300.XSHG')

    

## 开盘前运行函数
def before_market_open(context):
    # 获取持仓的昨日涨停列表
    # 获取持仓
    g.hold_list = list(context.portfolio.positions)
    #获取昨日涨停列表
    if g.hold_list != []:
        yesterday = datetime.datetime.strftime(context.previous_date, '%Y-%m-%d')
        df = get_price(g.hold_list, end_date=yesterday, frequency='daily', fields=['close','high_limit'], count=1, panel=False, fill_paused=False)
        df = df[df['close'] == df['high_limit']]
        g.high_limit_list = list(df.code)
    else:
        g.high_limit_list = []
    
    
    today = datetime.datetime.strftime(context.current_dt, '%Y-%m-%d')
    pre_m = datetime.datetime.strftime(context.previous_date, '%m')
    cur_m = datetime.datetime.strftime(context.current_dt, '%m')
    
    if cur_m != pre_m:
        start = datetime.datetime.now()
        # print('previous_date:%s current_dt:%s' % (context.previous_date, context.current_dt))
        g.signal = True
        stock_list = select_stocks(context)
        if g.all_A:
            # 沪深两市
            curr_stock_list = get_index_stocks('000002.XSHG', today) + get_index_stocks('399107.XSHE', today)
            # #沪深300、中证1000、中证500
            # curr_stock_list = get_index_stocks('000300.XSHG', today) + get_index_stocks('000852.XSHG', today) + get_index_stocks('399905.XSHE', today)
            curr_stock_list = list(set(curr_stock_list))
        else:
            curr_stock_list = get_index_stocks(g.benchmark, today)
            
        g.alllist = [stk for stk in stock_list if stk in curr_stock_list]
        end = datetime.datetime.now()
        print('选股总耗时:', (end-start))
    else:
        g.signal = False
        g.alllist = []

def select_stocks(context):
    # 1.获取截面T-m到T的所有交易日，其中T-m到T-1为训练数据，T为测试数据
    tody = datetime.datetime.strftime(context.current_dt, '%Y-%m-%d')
    yesterday = datetime.datetime.strftime(context.previous_date, '%Y-%m-%d')
    start_date = datetime.datetime.strftime(context.previous_date - datetime.timedelta(days=200), '%Y-%m-%d')
    date_list = get_period_date('M', start_date, yesterday)
    assert len(date_list) > g.windows
    if len(g.factor_cache) != 0:
        date_list = date_list[-g.windows-1:]
    else:
        t_m = int(g.windows/2) if g.windows > 1 else 1
        date_list = date_list[-t_m-1:]
    # 2.获取截面日期的因子值
    for date in g.factor_cache.copy().keys():
        if date not in date_list:
            del g.factor_cache[date]
    
    for date in date_list:
        if date in g.factor_cache:
            continue
        if g.all_A:
            #沪深两市
            stock_list = get_index_stocks('000002.XSHG', date) + get_index_stocks('399107.XSHE', date)
            # #沪深300、中证1000、中证500
            # stock_list = get_index_stocks('000300.XSHG', date) + get_index_stocks('000852.XSHG', date) + get_index_stocks('399905.XSHE', date)
            stock_list = list(set(stock_list))
        else:
            stock_list = get_index_stocks(g.benchmark, date)
            
        print('候选个数',len(stock_list), end=' ')
        # 排除st、科创板、北交所、次新股
        stock_list = filter_skbc_stock(context, stock_list)
        # 获取因子值
        print ('%s get_factor_data...' % date, end=' ')
        factor_origl_data = get_factor_data(stock_list, date)
        # print(factor_origl_data[:10])
        # 数据预处理
        print ('%s data_preprocessing...' % date, end=' ')
        industry_code = list(get_industries('sw_l1', date).index)
        factor_solve_data = data_preprocessing(factor_origl_data, stock_list, industry_code, date)
        # has_nan = factor_solve_data.isna().any()
        # cols_with_nan = has_nan[has_nan].index.tolist()
        # if len(cols_with_nan) != 0:
        #     print(cols_with_nan)
        # assert len(cols_with_nan) == 0
        factor_solve_data = factor_solve_data.dropna()
        assert factor_solve_data.shape[0] > 0
        
        # 添加下月收益
        if date_list.index(date) < len(date_list) - 1:
            stockList = list(factor_solve_data.index)
            data_close = pd.DataFrame()
            # print('%s %s'%(date, date_list[date_list.index(date)+1]))
            for stock in stockList:
                data_close[stock] = get_price(stock, date, date_list[date_list.index(date)+1], '1d', 'close')['close']
            factor_solve_data['pchg'] = data_close.iloc[-1] / data_close.iloc[0] - 1
            # has_nan = factor_solve_data.isna().any()
            # cols_with_nan = has_nan[has_nan].index.tolist()
            # if len(cols_with_nan) != 0:
            #     print('factor_cache,pchg',cols_with_nan)
            # assert len(cols_with_nan) == 0
            factor_solve_data = factor_solve_data.dropna()
            assert factor_solve_data.shape[0] > 0
        
        g.factor_cache[date] = factor_solve_data
    
    # 3.构造训练集
    train_data = pd.DataFrame()
    for date in date_list[:-1]:
        print(date, end=' ')
        traindf = g.factor_cache[date]
        if 'pchg' not in traindf:
            #取收益率数据
            stockList = list(traindf.index)
            data_close = pd.DataFrame()
            # print('%s %s'%(date, date_list[-1]))
            for stock in stockList:
                data_close[stock] = get_price(stock, date, date_list[-1], '1d', 'close')['close']
            # print(data_close[:1])
            # print(data_close[-1:])
            # a = data_close.iloc[-1] / data_close.iloc[0]
            # print(a[:10])
            traindf['pchg'] = data_close.iloc[-1] / data_close.iloc[0] - 1
            # has_nan = traindf.isna().any()
            # cols_with_nan = has_nan[has_nan].index.tolist()
            # print('train_data,pchg',cols_with_nan)
            # has_nan = traindf.isna().any(axis=1)
            # row_with_nan = has_nan[has_nan].index.tolist()
            # print('train_data,pchg',row_with_nan)
            # assert len(cols_with_nan) == 0
            traindf = traindf.dropna()
            assert traindf.shape[0] > 0
        #选取前后各30%的股票，剔除中间的噪声
        traindf = traindf.sort_values(by='pchg')
        traindf = traindf.iloc[:len(traindf['pchg'])//10*3,:].append(traindf.iloc[len(traindf['pchg'])//10*7:,:])
        traindf['label'] = list(traindf['pchg'].apply(lambda x:1 if x>np.mean(list(traindf['pchg'])) else -1))
        if train_data.empty:
            train_data = traindf
        else:
            train_data = train_data.append(traindf)
    train_target = train_data['label']
    train_feature= train_data.copy()
    del train_feature['pchg']
    del train_feature['label']
    
    # 4.创建网格搜索，进行时序交叉验证
    if g.is_cv:
        start = datetime.datetime.now()
        print ('\n开始交叉验证')
        clf = GridSearchCV(g.regressor, g.parameters, scoring='roc_auc',
                            cv=3, verbose=1)
        clf.fit(train_feature.values, train_target.values)
        print (clf.best_params_)
        print('交叉验证时长：', datetime.datetime.now()-start)
        g.params = clf.best_params_
    
    # 5.模型训练
    # ***************需要调整的地方****************
    clf = g.regressor(max_depth=g.params['max_depth'],
                       learning_rate=g.params['learning_rate'],
                       subsample=g.params['subsample'])
    # clf = g.regressor(C=g.params['C'],
    #              gamma=g.params['gamma'],
    #              probability=True)
    # *******************************
    
    starttime = datetime.datetime.now()
    print ('开始训练模型...')
    clf.fit(train_feature.values, train_target.values)
    endtime = datetime.datetime.now()
    print ('模型训练时长：%.4f 分钟'%float((endtime - starttime).seconds/60))
    
    # 6.测试集选股
    date = date_list[-1]
    print(date, end=' ')
    test_feature = g.factor_cache[date]
    prob = clf.predict_proba(test_feature.values)[:, 1]
    # 按得分从高往低排
    df = pd.DataFrame(index=test_feature.index)
    df['score'] = list(prob)
    df = df.sort_values(by='score', ascending=False)
    # df = df[df['score'] > 0.6]
    # print(df[:10])
    # return list(df.index)
    
    
    df = df[:int(0.1*df.shape[0])]
    # df = df[df['score'] > 0.6]
    # print(df.shape)
    print(df[:10])
    stocks = list(df.index)
    q = query(valuation.code, indicator.eps).filter(valuation.code.in_(stocks)).order_by(valuation.circulating_market_cap.asc())
    df = get_fundamentals(q, yesterday).dropna()
    df = df[df['eps']>0]
    # print(df[:10])
    return list(df['code'])


## 开盘时运行函数
def market_open(context):
    # # 加入止盈
    # for stock in context.portfolio.positions:
    #     info = context.portfolio.positions[stock]
    #     cost = info.avg_cost
    #     price = info.price
    #     ret = price / cost - 1
    #     if ret >= 0.2 and stock not in g.high_limit_list:
    #         print('股票：%s 价格: %s 成本: %s 收益: %s' % (stock, price, cost, ret))
    #         order = order_target_value(stock, 0)
    #         if order != None:
    #             print('止盈卖出：%s 下单数量：%s 成交数量：%s'%(stock, order.amount, order.filled))
    #         else:
    #             print('止盈卖出[%s]失败。。。' % stock)
    
    # # # 加入超跌
    # down_buy_in = []
    # today = int(datetime.datetime.strftime(context.current_dt, '%d'))
    # for stock in context.portfolio.positions:
    #     info = context.portfolio.positions[stock]
    #     cost = info.avg_cost
    #     price = info.price
    #     ret = price / cost - 1
    #     if ret <= -0.2 and stock not in g.high_limit_list and not g.signal:
    #         # print("超跌..")
    #         print('股票：%s 价格: %s 成本: %s 收益: %s' % (stock, price, cost, ret))
    #         down_buy_in.append(stock)
    
    # target_num = len(down_buy_in)
    # if target_num > 0:
    #     value = context.portfolio.cash / target_num
    #     for stock in down_buy_in:
    #         order = order_value(stock, value)
    #         if order != None:
    #             print('超跌买入：%s 下单数量：%s 成交数量：%s'%(stock, order.amount, order.filled))
    #         else:
    #             print('超跌买入[%s]失败。。。' % stock)
    
    
    if not g.signal:
        return
    
    buylist = filter_limit_stock(context, g.alllist)[:g.stock_num]
    
    print('待买入股票池：%s'%str(buylist))
    print('待买入股票个数：%s'%len(buylist))
    # 调仓卖出
    for stock in context.portfolio.positions:
        if stock not in buylist and stock not in g.high_limit_list:
            order = order_target_value(stock, 0)
            if order != None:
                print('卖出股票：%s 下单数量：%s 成交数量：%s'%(stock, order.amount, order.filled))
            else:
                print('卖出股票[%s]失败。。。' % stock)
                
    # 调仓买入
    target_num = len(buylist)
    if target_num <= 0:
        return
    value = context.portfolio.total_value / target_num
    for stock in buylist:
        order = order_target_value(stock, value)
        if order != None:
            print('调仓：%s 调整至金额：%s 下单数量：%s 成交数量：%s'%(stock, value, order.amount, order.filled))
        else:
            print('调仓[%s]失败。。。' % stock)


## 排除st、科创板、北交所、次新股
def filter_skbc_stock(context, stock_list):
    e_stocks = []
    current_data = get_current_data()
    for stk in stock_list:
        # 排除st股票
        if current_data[stk].is_st or 'ST' in current_data[stk].name or\
        '*' in current_data[stk].name or '退' in current_data[stk].name:
            continue
        
        # 排除科创板
        if stk.startswith('688'):
            continue
        
        # 排除北交所
        if stk.startswith('43') or stk.startswith('8'):
            continue
        
        # 排除次新股(上市不足3个月)
        if (context.previous_date - datetime.timedelta(days=90)) < get_security_info(stk).start_date:
            continue
        
        e_stocks.append(stk)
        
    return e_stocks

def get_period_date(peroid, start_date, end_date):
    df = get_price('000001.XSHE', start_date, end_date, fields=['close'])
    df_sample = df.resample(peroid).last()
    date = df_sample.index
    pydate_array = date.to_pydatetime()
    date_array = np.vectorize(lambda x:x.strftime('%Y-%m-%d'))(pydate_array)
    date_list = list(date_array)
    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d') - datetime.timedelta(days=1)
    start_date = start_date.strftime('%Y-%m-%d')
    date_list = [start_date] + date_list
    return date_list

# 辅助线性回归的函数
def linreg(X, Y, columns=3):
    X = sm.add_constant(array(X))
    Y = array(Y)
    if len(Y) > 1:
        results = regression.linear_model.OLS(Y, X).fit()
        return results.params
    else:
        return [float("nan")] * (columns+1)
    
#取股票对应行业
def get_industry_name(i_Constituent_Stocks, value):
    return [k for k, v in i_Constituent_Stocks.items() if value in v]

#缺失值处理
def replace_nan_indu(factor_data, stockList, industry_code, date):
    #把nan用行业平均值代替，依然会有nan，此时用所有股票平均值代替
    i_Constituent_Stocks = {}
    data_temp = pd.DataFrame(index=industry_code, columns=factor_data.columns)
    for i in industry_code:
        temp = get_industry_stocks(i, date)
        i_Constituent_Stocks[i] = list(set(temp).intersection(set(stockList)))
        data_temp.loc[i] = mean(factor_data.loc[i_Constituent_Stocks[i], :])
    for factor in data_temp.columns:
        #行业缺失值用所有行业平均值代替
        null_industry = list(data_temp.loc[pd.isnull(data_temp[factor]), factor].keys())
        for i in null_industry:
            data_temp.loc[i,factor] = mean(data_temp[factor])
        null_stock = list(factor_data.loc[pd.isnull(factor_data[factor]), factor].keys())
        for i in null_stock:
            industry = get_industry_name(i_Constituent_Stocks, i)
            if industry:
                factor_data.loc[i, factor] = data_temp.loc[industry[0], factor] 
            else:
                factor_data.loc[i, factor] = mean(factor_data[factor])
    return factor_data

#数据预处理
def data_preprocessing(factor_data, stockList, industry_code, date):
    #去极值
    factor_data = winsorize_med(factor_data, scale=5, inf2nan=False,axis=0)
    #缺失值处理
    factor_data = replace_nan_indu(factor_data, stockList, industry_code, date)
    #中性化处理
    factor_data = neutralize(factor_data, how=['sw_l1', 'market_cap'], date=date, axis=0)
    #标准化处理
    factor_data = standardlize(factor_data, axis=0)
    return factor_data

#获取时间为date的全部因子数据
def get_factor_data(stock, date):
    data = pd.DataFrame(index=stock)
    q = query(valuation.market_cap, valuation.code, valuation.pb_ratio, valuation.ps_ratio, valuation.pcf_ratio, valuation.pe_ratio,