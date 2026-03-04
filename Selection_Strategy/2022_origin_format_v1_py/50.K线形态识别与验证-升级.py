#!/usr/bin/env python
# coding: utf-8

# 导入必备模块
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import datetime as dt
import talib as tb  # 当前重点库 TA-LIB
import seaborn as sns
from jqdata import *
sns.set()


### 定义形态查寻函数
def find_pattern(function):
    '''从全市场中“随机”的挑选标的，快速的找到一个符合形态的标的与对应时间
    Args:
        function: ta-lib 库中的一个方法
    Return:
        返回(stock, date)
    '''
    
    # 打乱全市场标的顺序
    stock_list = get_all_securities().index.tolist()
    np.random.shuffle(stock_list)
    
    # 构造时间序列的结点，从10天之前的时间序列查找
    trade_date = get_trade_days(end_date=dt.datetime.now(), count=15)
    check_date = trade_date[-10]
    
    for stock in stock_list:
        try:
            price = get_price(stock, end_date=check_date, count=244 * 5)
            signal = function(price['open'], price['high'],
                              price['low'], price['close'])
            signal = signal[signal != 0]
            if len(signal) > 0:
                return stock, signal.index[0]
        except:
            continue


### k 线刻画数据处理
def get_k_value(pattern, count):
    '''将开、高、低、收价格数据进行处理，以支持K线图展示
    Args:
        pattern: 形态函数返回的标的与时间元组
        count: 形态数量
    Return:
        返回处理后的价格数据，类型为df
    '''

    # 获取21个价格序列值，并且让形态时间大致处于中间
    security = pattern[0]
    check_date = pattern[1]
    pattern_date = get_trade_days(end_date=check_date, count=count)
    orther_count = (21 - count) // 2
    trade_date = get_trade_days(start_date=check_date, end_date=dt.datetime.now())
    end_date = trade_date[9]
    price = get_price(security, end_date=end_date, 
                      count=21)[['open', 'high', 'low', 'close']]
    y_list = {'y1': [], 'y2': [], 'y3': [], 'y4': [], 'c': [], 'al': []}
    
    # 数据处理
    for i in range(price.shape[0]):
        # 计算各bar的透明度
        if price.index[i].date() in pattern_date:
            y_list['al'].append(1)
        else:
            y_list['al'].append(0.2)
        
        # 计算各实体的长度
        if price.open[i] > price.close[i]:
            y_list['y1'].append(price.close[i])
            y_list['y2'].append(price.open[i] - price.close[i])
            y_list['c'].append('g')
        else:
            y_list['y1'].append(price.open[i])
            y_list['y2'].append(price.close[i] - price.open[i])
            y_list['c'].append('r')
        
        # 计算各影线的长度
        if price.high[i] > price.low[i]:
            y_list['y3'].append(price.low[i])
            y_list['y4'].append(price.high[i] - price.low[i])
        else:
            y_list['y3'].append(price.high[i])
            y_list['y4'].append(price.low[i] - price.high[i])
            
    for name, value in y_list.items():
        price.loc[:, name] = value

    return price


### k 线形态刻画 
def show_bar(data, title='None'):
    '''将价格数据按实体与影线进行组合
    Args:
        data: 处理好的价格数据，df类型
        title: 图片标题，可选
    Return:
        None
    '''

    # 整合 x 轴与 y 轴数据
    x = [str(date.date()) for date in data.index]
    y1 = data['y1']
    y2 = data['y2']

    y3 = data['y3']
    y4 = data['y4']
    
    fig = plt.figure(figsize=(18, 5))
    # 画影线，要求对应不同的颜色与透明度
    for i in range(len(data)):
        plt.bar(x[i], y3[i], align='center', alpha=0)
        plt.bar(x[i], y4[i], align='center', color=data['c'][i], 
                alpha=data['al'][i], bottom=y3[i], width=0.1)

    # 画实体，要求对应不同的颜色与透明度
    for j in range(len(data)):
        plt.bar(x[j], y1[j], align='center', alpha=0)
        plt.bar(x[j], y2[j], align='center', color=data['c'][j], 
                alpha=data['al'][j], bottom=y1[j])
    
    _min = data[['open', 'high', 'low', 'close']].min().min() - 0.1
    _max = data[['open', 'high', 'low', 'close']].max().max() + 0.1

    plt.ylim(_min, _max)
    plt.title(title)
    plt.xticks(rotation=45)
    plt.show()


### 函数组合-形态检测
def check_bar(fuc, bar_count):
    # 查询形态
    pattern = find_pattern(fuc)
    # bar 数据处理
    k_value = get_k_value(pattern, bar_count)
    # 形态展示
    show_bar(k_value, pattern[0] + ': ' + fuc.__name__)


# CDL2CROWS - Two Crows
# > 函数名：CDL2CROWS   
# 名称：Two Crows 两只乌鸦   
# 简介：三日K线模式，第一天长阳，第二天高开收阴，第三天再次高开继续收阴，
# 收盘比前一日收盘价低，预示股价下跌。
# 
# integer = CDL2CROWS(open, high, low, close)


check_bar(tb.CDL2CROWS, 3)


# CDL3BLACKCROWS - Three Black Crows
# > 函数名：CDL3BLACKCROWS   
# 名称：Three Black Crows 三只乌鸦   
# 简介：三日K线模式，连续三根阴线，每日收盘价都下跌且接近最低价，
# 每日开盘价都在上根K线实体内，预示股价下跌。   
# 
# integer = CDL3BLACKCROWS(open, high, low, close)


check_bar(tb.CDL3BLACKCROWS, 3)


# CDL3INSIDE - Three Inside Up/Down
# > 函数名：CDL3INSIDE   
# 名称： Three Inside Up/Down 三内部上涨和下跌   
# 简介：三日K线模式，母子信号+长K线，以三内部上涨为例，K线为阴阳阳，
# 第三天收盘价高于第一天开盘价，第二天K线在第一天K线内部，预示着股价上涨。
#    
# integer = CDL3INSIDE(open, high, low, close)


check_bar(tb.CDL3INSIDE, 3)


# CDL3LINESTRIKE - Three-Line Strike 
# > 函数名：CDL3LINESTRIKE   
# 名称： Three-Line Strike 三线打击   
# 简介：四日K线模式，前三根阳线，每日收盘价都比前一日高，
# 开盘价在前一日实体内，第四日市场高开，收盘价低于第一日开盘价，预示股价下跌。
#    
# integer = CDL3LINESTRIKE(open, high, low, close)


check_bar(tb.CDL3LINESTRIKE, 4)


# CDL3OUTSIDE - Three Outside Up/Down
# > 函数名：CDL3OUTSIDE  
# 名称：Three Outside Up/Down 三外部上涨和下跌   
# 简介：三日K线模式，与三内部上涨和下跌类似，K线为阴阳阳，但第一日与第二日的K线形态相反，
# 以三外部上涨为例，第一日K线在第二日K线内部，预示着股价上涨。  
# 
# integer = CDL3OUTSIDE(open, high, low, close)


check_bar(tb.CDL3OUTSIDE, 3)


# CDL3STARSINSOUTH - Three Stars In The South
# > 函数名：CDL3STARSINSOUTH  
# 名称：Three Stars In The South 南方三星  
# 简介：三日K线模式，与大敌当前相反，三日K线皆阴，第一日有长下影线，
# 第二日与第一日类似，K线整体小于第一日，第三日无下影线实体信号，
# 成交价格都在第一日振幅之内，预示下跌趋势反转，股价上升。  
# 
# integer = CDL3STARSINSOUTH(open, high, low, close)


check_bar(tb.CDL3STARSINSOUTH,