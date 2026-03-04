#!/usr/bin/env python
# coding: utf-8

# 本文参考中国银河证券研报《多因子系列: 多因子模型体系之因子组合的确定》，感谢分析师 黎鹏 在研报中提供的思路和方法，以下的内容我们通过数据和代码尝试进行了分析例证。  
# 
# <b>研究目的：</b>  
# 
# 根据研报分析，专注于对多因子框架进行研究，本报告完成模型的第一步: 因子组合的确定。从分类的角度看，因子可认为是用于分类的标签。在股票市场中，股票代码是最细分的分类。多因子模型的一个主要作用是简化计算，因为如果用较少的共同因子来代替股票的各种特征，则可以将股票这个最细分的分类用少数的因子代替，从而大大降低计算的复杂度。但是因子的选择一直是个难点，因为基础因子的个数很多，算上衍生因子复杂度更是上升。为了降低构建因子组合的难度，本文认为可以尝试从基准的特征出发来确定因子。因为从股票组合管理的角度来看，因子最大的作用在于风险描述继而对冲，从而获得 Alpha收益。所以基准明显的特征应该是基准的明显风险点，应该首先得到关注。
# 
# <b>研究内容：</b>  
# 
# （1）首先，从基准的角度获取较为通用的因子。考虑到常见基准和是否有对应期货两方面因素，本文的基础基准设定为上证 50（IH），沪深 300（IF）和中证 500（IC），考虑到这三个基准的编制方式以及个股的通用性质，本文对以下 8 个因子进行研究：市值、股本、roe、净利润增长率（成长性因子）、PE（价值）、换手率、EPS 以及成交量。  
# （2）根据因子在指数成分股中的暴露分析，从基准的角度看，因子是否通用，是否能代表基准明显的特征；  
# （3）分析因子之间的相关性，避免相关性过高的因子进入因子组合，相关性过高的因子对于线性模型而言，往往导致模型出现较大误差，使得模型的预测能力下降；  
# （4）通过研究因子 IC，分析因子解释力度是否较强，判断因子对个股未来收益的预测能力。
# 
# <b>研究结论：</b>  
# 
# 组合的评判标准分为三点：因子暴露度、因子相关强度和因子选个股能力，相关结论如下：  
# （1） 三大股指的市值和股本因子的偏离度均是最高的。中等偏离度的因子包括，换手率、ROE、PE、EPS 因子。偏离度最小的是净利润增长率因子。  
# （2） 相关强度最低的组合为净利润增长率和成交量，换手率和 EPS，ROE 和换手率，股本和换手率。  
# （3） 除了换手率因子较强，净利润增长率较弱之外，其他因子的选股能力区别不大。  
# 综合选择暴露度高、相关强度低和选股能力强的因子，股本和换手率作为因子组合较为合适。
# 
# **注:** 相关研报已上传为附件,文末可以下载 

# # 1 数据获取

# ## 1.1 日期列表获取

# 研报以日为频率对不同风格的因子进行分析，但是由于研究环境内存限制，全市场日频数据量较多，无法保存并进行处理，因此本文考虑以周为频率对不同风格因子进行分析，每周的日期列表获取方式具体如下所示。  
# 输入参数分别为 peroid、start_date 和 end_date，其中 peroid 进行周期选择，可选周期为周(W)、月(M)和季(Q)，start_date 和end_date 分别为开始日期和结束日期。  
# 本文取 peroid 为 W，函数返回值为对应的周末日期。本文选取开始日期为 2014.1.1，结束日期为 2019.1.1。

from jqdata import *
import datetime
import pandas as pd
import numpy as np
from six import StringIO
import warnings
import time
import pickle
from jqfactor import winsorize_med
from jqfactor import neutralize
from jqfactor import standardlize
import statsmodels.api as sm
warnings.filterwarnings("ignore")
matplotlib.rcParams['axes.unicode_minus']=False


# 获取指定周期的日期列表 'W、M、Q'
def get_period_date(peroid,start_date, end_date):
    #设定转换周期period_type  转换为周是'W',月'M',季度线'Q',五分钟'5min',12天'12D'
    stock_data = get_price('000001.XSHE',start_date,end_date,'daily',fields=['close'])
    #记录每个周期中最后一个交易日
    stock_data['date']=stock_data.index
    #进行转换，周线的每个变量都等于那一周中最后一个交易日的变量值
    period_stock_data=stock_data.resample(peroid,how='last')
    date=period_stock_data.index
    pydate_array = date.to_pydatetime()
    date_only_array = np.vectorize(lambda s: s.strftime('%Y-%m-%d'))(pydate_array )
    date_only_series = pd.Series(date_only_array)
    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    start_date=start_date-datetime.timedelta(days=1)
    start_date = start_date.strftime("%Y-%m-%d")
    date_list=date_only_series.values.tolist()
    date_list.insert(0,start_date)
    TradeDate = []
    for i in date_list:
        temp = list(get_trade_days(end_date=i, count=1))[0]
        TradeDate.append(str(temp))
    return TradeDate
np.array(get_period_date('W', '2018-01-01', '2019-01-01'))


# 上述代码实现的功能为获取开始时间为 2018.1.1，结束日期为 2019.1.1 的每周的可交易日期列表。利用该函数可实现对任意时间区间的每周的可交易日期列表。

# ## 1.2 数据获取

# 为了形成最初的因子组合，我们可通过对基准编制规则进行解读，从直观上对基准的特征有所了解。然后形成逻辑且具有经济意义的初步因子组合列表。下表我们分别展示了上证 50 (000016)，沪深 300(000300)和中证 500(000905)指数的样本股编制规则：   
# 
# | 指数名称      | 股票池           | 股票个数  |加权方法  |选股条件  |对应因子  |
# | ------------- |:-------------:| -----:| -----:| -----:| -----:|
# | 上证 50       | 上证180     | 50     | 派许加权 + 调整股本     |规模、流动性     |流通市值、成交金额     |
# | 沪深 300      | 全 A 股      |   300 |派许加权 + 调整股本     |规模     |日均总市值     |
# | 中证 500      | 全 A 股扣除市值最大的 300 只      |    500 |派许加权 + 调整股本     |规模     |日均总市值     |
# 
# 从指数样本股选取标准上看，市值是重点考虑的方面。从加权方式上看股本需要加入初步的因子库。考虑到个股的通用性质，初步加入了 roe、 净利润增长率（成长性因子）、PE（价值）、换手率等因子。具体因子如下表所示：  
# 
# | 因子名称      | 计算方法           | 因子描述  |
# | ------------- |:-------------:| -----:|
# | 市值       | 总市值 = 个股当日股价 $\times$ 当日总股本  | 规模相关，信息包含股本和股价     | 
# | 股本      | 报表科目，详见会计报表     |  规模相关 |
# | EPS     | 当期净利润 / 普通股加权平均   |  业绩相关 |
# | Roe      | 归属母公司股东的净利润占比 $\times$ 销售净利率 $\times$ 资产周转率 $\times$ 权益乘数     |  盈利能力相关 |
# | 净利润增长率   | (本期 -上年同期调整数 ) / ABS上年同期调整数 $\times$ 100%   |  成长能力相关 |
# | PE   | 市值 / 当期净利润   |  估值因子 |
# | 换手率   | 成交量 / 总股数   |  行情相关 |

start = time.clock()
begin_date = '2014-01-01'
end_date = '2019-01-01'
TradeDate = get_period_date('W',begin_date, end_date)
factorData = {}
for date in TradeDate:
    stockList = get_index_stocks('000