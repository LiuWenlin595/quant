# 克隆自聚宽文章：https://www.joinquant.com/post/35463
# 标题：缠论交易策略
# 作者：quancker

# 导入函数库
from jqdata import *
from datetime import datetime
import numpy as np
from typing import Any
from copy import copy

security=None
class BarData:
    def __init__(self, datetime, high_price, low_price, volume=0, open_interest=0, close_price=0, open_price=0):
        """初始化属性"""
        self.high_price = high_price
        self.low_price = low_price
        self.datetime = datetime
        self.volume = volume
        self.open_interest = open_interest
        self.close_price = close_price
        self.open_price = open_price

def SMA(close_price: np.array, timeperiod=5):
    """简单移动平均

    https://baike.baidu.com/item/%E7%A7%BB%E5%8A%A8%E5%B9%B3%E5%9D%87%E7%BA%BF/217887

    :param close_price: np.array
        收盘价序列
    :param timeperiod: int
        均线参数
    :return: np.array
    """
    res = []
    for i in range(len(close_price)):
        if i < timeperiod:
            seq = close_price[0: i + 1]
        else:
            seq = close_price[i - timeperiod + 1: i + 1]
        res.append(seq.mean())
    return np.array(res, dtype=np.double).round(4)


def EMA(close_price: np.array, timeperiod=5):
    """
    https://baike.baidu.com/item/EMA/12646151

    :param close_price: np.array
        收盘价序列
    :param timeperiod: int
        均线参数
    :return: np.array
    """
    res = []
    for i in range(len(close_price)):
        if i < 1:
            res.append(close_price[i])
        else:
            ema = (2 * close_price[i] + res[i - 1] * (timeperiod - 1)) / (timeperiod + 1)
            res.append(ema)
    return np.array(res, dtype=np.double).round(4)


def MACD(close_price: np.array, fastperiod=12, slowperiod=26, signalperiod=9):
    """MACD 异同移动平均线
    https://baike.baidu.com/item/MACD%E6%8C%87%E6%A0%87/6271283

    :param close_price: np.array
        收盘价序列
    :param fastperiod: int
        快周期，默认值 12
    :param slowperiod: int
        慢周期，默认值 26
    :param signalperiod: int
        信号周期，默认值 9
    :return: (np.array, np.array, np.array)
        diff, dea, macd
    """
    ema12 = EMA(close_price, timeperiod=fastperiod)
    ema26 = EMA(close_price, timeperiod=slowperiod)
    diff = ema12 - ema26
    dea = EMA(diff, timeperiod=signalperiod)
    macd = (diff - dea) * 2
    return diff.round(4), dea.round(4), macd.round(4)



class Chan_Strategy:
    author = "jc"
    parameters = []
    variables = []

    def __init__(self, include=True, build_pivot=False):
        self.k_list = []
        self.chan_k_list = []
        self.fx_list = []
        self.stroke_list = []
        self.line_list = []
        self.line_index = {}
        self.line_feature = []
        self.s_feature = []
        self.x_feature = []

        self.pivot_list = []
        self.trend_list = []
        self.buy_list = []
        self.x_buy_list = []
        self.sell_list = []
        self.x_sell_list = []
        self.macd = {}
        # 头寸控制
        self.buy1 = 100
        self.buy2 = 200
        self.buy3 = 200
        self.sell1 = 100
        self.sell2 = 200
        self.sell3 = 200
        # 动力减弱最小指标
        self.dynamic_reduce = 0
        # 笔生成方法，new, old
        # 是否进行K线包含处理
        self.include = include
        # 中枢生成方法，stroke, line
        # 使用笔还是线段作为中枢的构成, true使用线段
        self.build_pivot = build_pivot


    def on_bar(self, bar: BarData):
        self.on_period(bar)

    def on_period(self, bar: BarData):
        self.k_list.append(bar)
        if self.include:
            self.on_process_k_include(bar)
        else:
            self.on_process_k_no_include(bar)

    def on_process_k_include(self, bar: BarData):
        """合并k线"""
        if len(self.chan_k_list) < 3:
            self.chan_k_list.append(bar)
        else:
            pre_bar = self.chan_k_list[-2]
            last_bar = self.chan_k_list[-1]
            if (last_bar.high_price >= bar.high_price and last_bar.low_price <= bar.low_price) or (
                    last_bar.high_price <= bar.high_price and last_bar.low_price >= bar.low_price):
                if last_bar.high_price > pre_bar.high_price:
                    new_bar = copy(bar)
                    new_bar.high_price = max(last_bar.high_price, new_bar.high_price)
                    new_bar.low_price = max(last_bar.low_price, new_bar.low_price)
                    # new_bar.open = max(last_bar.open, new_bar.open)
                    # new_bar.close_price = max(last_bar.close_price, new_bar.close_price)
                else:
                    new_bar = copy(bar)
                    new_bar.high_price = min(last_bar.high_price, new_bar.high_price)
                    new_bar.low_price = min(last_bar.low_price, new_bar.low_price)
                    # new_bar.open = min(last_bar.open, new_bar.open)
                    # new_bar.close_price = min(last_bar.close_price, new_bar.close_price)

                self.chan_k_list[-1] = new_bar
                print("combine k line: " + str(new_bar.datetime))
            else:
                self.chan_k_list.append(bar)
            # 包含和非包含处理的k线都需要判断是否分型了
            self.on_process_fx(self.chan_k_list)

    def on_process_k_no_include(self, bar: BarData):
        """不用合并k线"""
        self.chan_k_list.append(bar)
        self.on_process_fx(self.chan_k_list)

    def on_process_fx(self, data):
        if len(data) > 2:
            flag = False
            if data[-2].high_price > data[-1].high_price and data[-2].high_price > data[-3].high_price:
                # 形成顶分型 [high_price, low, dt, direction, index of chan_k_list]
                self.fx_list.append([data[-2].high_price, data[-2].low_price, data[-2].datetime, 'up', len(data) - 2])
                flag = True

            if data[-2].low_price < data[-1].low_price and data[-2].low_price < data[-3].low_price:
                # 形成底分型
                self.fx_list.append([data[-2].high_price, data[-2].low_price, data[-2].datetime, 'down', len(data) - 2])
                flag = True

            if flag:
                self.on_stroke(self.fx_list[-1])
                print("fx_list: ")
                print(self.fx_list[-1])

    def on_stroke(self, data):
        """生成笔"""
        if len(self.stroke_list) < 2:
            self.stroke_list.append(data)
        else:
            last_fx = self.stroke_list[-1]
            cur_fx = data
            # 分型之间需要超过三根chank线
            # 延申也是需要条件的
            if last_fx[3] == cur_fx[3]:
                if (last_fx[3] == 'down' and cur_fx[1] < last_fx[1]) or (
                        last_fx[3] == 'up' and cur_fx[0] > last_fx[0]):
                    # 笔延申
                    self.stroke_list[-1] = cur_fx
                    # 修正倒数第二个分型是否是最高的顶分型或者是否是最低的底分型
                    start = -2
                    stroke_change = None
                    if cur_fx[3] == 'down':
                        while len(self.fx_list) > abs(start) and self.fx_list[start][2] > last_fx[2]:
                            if self.fx_list[start][3] == 'up' and self.fx_list[start][0] > self.stroke_list[-2][0]:
                                stroke_change = self.fx_list[start]
                            start -= 1
                    else:
                        while len(self.fx_list) > abs(start) and self.fx_list[start][2] > last_fx[2]:
                            if self.fx_list[start][3] == 'down' and self.fx_list[start][1] < self.stroke_list[-2][1]:
                                stroke_change = self.fx_list[start]
                            start -= 1
                    if stroke_change:
                        print('stroke_change')
                        print(stroke_change)

                        # 更新中枢的信息
                        if self.pivot_list:
                            last_pivot = self.pivot_list[-1]
                            if self.stroke_list[-2][2] == last_pivot[4][3][2]:
                                last_pivot[1] = stroke_change[2]
                                if stroke_change[3] == 'up':
                                    ZG = min(self.stroke_list[-4][0], self.stroke_list[-2][0])
                                    last_pivot[3] = ZG
                                else:
                                    ZD = max(self.stroke_list[-4][0], self.stroke_list[-2][0])
                                    last_pivot[2] = ZD
                                print('pivot_change')
                                print(self.pivot_list[-1])

                        self.stroke_list[-2] = stroke_change
                        if len(self.stroke_list) > 2:
                            cur_fx = self.stroke_list[-2]
                            last_fx = self.stroke_list[-3]
                            self.macd[cur_fx[2]] = self.cal_macd(last_fx[2], cur_fx[2])

                        if cur_fx[4] - self.stroke_list[-2][4] < 4:
                            self.stroke_list.pop()

            else:
                if (cur_fx[4] - last_fx[4] > 3) and (
                        (cur_fx[3] == 'down' and cur_fx[1] < last_fx[1] and cur_fx[0] < last_fx[0]) or (
                        cur_fx[3] == 'up' and cur_fx[0] > last_fx[0] and cur_fx[1] > last_fx[1])):
                    # 笔新增
                    self.stroke_list.append(cur_fx)
                    print("stroke_list: ")
                    print(self.stroke_list[-1])
                    # print(self.stroke_list)

            if self.build_pivot:
                self.on_line(self.stroke_list)
            else:
                if len(self.stroke_list) > 1:
                    cur_fx = self.stroke_list[-1]
                    last_fx = self.stroke_list[-2]
                    self.macd[cur_fx[2]] = self.cal_macd(last_fx[2], cur_fx[2])
                self.on_line(self.stroke_list)
                self.on_pivot(self.stroke_list)

    def on_line(self, data):
        # line_list保持和stroke_list结构相同，都是由分型构成的
        # 特征序列则不同，
        if len(data) > 4:
            # print('line_index:')
            # print(self.line_index)
            if data[-1][3] == 'up' and data[-3][0] >= data[-1][0] and data[-3][0] >= data[-5][0]:
                if not self.line_list or self.line_list[-1][3] == 'down':
                    if not self.line_list or (len(self.stroke_list) - 3) - self.line_index[
                        str(self.line_list[-1][2])] > 2:
                        # 出现顶
                        self.line_list.append(data[-3])
                        self.line_index[str(self.line_list[-1][2])] = len(self.stroke_list) - 3
                else:
                    # 延申顶
                    if self.line_list[-1][0] < data[-3][0]:
                        self.line_list[-1] = data[-3]
                        self.line_index[str(self.line_list[-1][2])] = len(self.stroke_list) - 3
            if data[-1][3] == 'down' and data[-3][1] <= data[-1][1] and data[-3][1] <= data[-5][1]:
                if not self.line_list or self.line_list[-1][3] == 'up':
                    if not self.line_list or (len(self.stroke_list) - 3) - self.line_index[
                        str(self.line_list[-1][2])] > 2:
                        # 出现底
                        self.line_list.append(data[-3])
                        self.line_index[str(self.line_list[-1][2])] = len(self.stroke_list) - 3
                else:
                    # 延申底
                    if self.line_list[-1][1] > data[-3][1]:
                        self.line_list[-1] = data[-3]
                        self.line_index[str(self.line_list[-1][2])] = len(self.stroke_list) - 3
            if self.line_list and self.build_pivot:
                if len(self.line_list) > 1:
                    cur_fx = self.line_list[-1]
                    last_fx = self.line_list[-2]
                    self.macd[cur_fx[2]] = self.cal_macd(last_fx[2], cur_fx[2])
                print('line_list:')
                print(self.line_list[-1])
                self.on_pivot(self.line_list)

    def on_pivot(self, data):
        # 中枢列表[[日期1，日期2，中枢低点，中枢高点, []]]]
        # 日期1：中枢开始的时间
        # 日期2：中枢结束的时间，可能延申
        # []: 构成中枢分型列表
        if len(data) > 4:
            # 构成笔或者是线段的分型
            cur_fx = data[-1]
            last_fx = data[-2]
            new_pivot = None
            # 构成新的中枢
            # if not self.pivot_list or (self.pivot_list and data[-2][2] > self.pivot_list[-1][1]):
            if not self.pivot_list or (self.pivot_list and data[-4][2] > self.pivot_list[-1][1]):
                cur_pivot = [data[-4][2], cur_fx[2]]
                if cur_fx[3] == 'down' and data[-2][0] > data[-4][0] and data[-2][1] > data[-4][1]:
                    ZD = max(data[-3][1], data[-1][1])
                    ZG = min(data[-4][0], data[-2][0])
                    if ZG > ZD:
                        cur_pivot.append(ZD)
                        cur_pivot.append(ZG)
                        cur_pivot.append(data[-4:])
                        new_pivot = cur_pivot
                        self.pivot_list.append(cur_pivot)
                if cur_fx[3] == 'up' and data[-2][0] < data[-4][0] and data[-2][1] < data[-4][1]:
                    ZD = max(data[-4][1], data[-2][1])
                    ZG = min(data[-3][0], data[-1][0])
                    if ZG > ZD:
                        cur_pivot.append(ZD)
                        cur