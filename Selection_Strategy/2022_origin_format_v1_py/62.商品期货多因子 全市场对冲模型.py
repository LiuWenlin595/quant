# 克隆自聚宽文章：https://www.joinquant.com/post/16126
# 标题：商品期货多因子 全市场对冲模型
# 作者：1342631xxxx

# 期货日频多品种，横截面多因子模型
# 建议给予1000000元，2012年1月1日至今回测
# 导入函数库
# 3因子定稿

from jqdata import * 
import talib
from math import isnan
import re
from jqfactor import get_factor_values
from jqfactor import standardlize
from jqfactor import winsorize_med
from six import StringIO


def initialize(context):
    # 设置参数
    set_parameter(context)
    # 价格列表初始化
    set_future_list(context)
    # 导入写入CSV文件
    csv_setting(context)
    # 设定基准银华日利，在多品种的回测当中基准没有参考意义
    set_benchmark('511880.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 过滤掉order系列API产生的比error级别低的log
    log.set_level('order', 'error')
    ### 期货相关设定 ###
    # 设定账户为金融账户
    set_subportfolios([SubPortfolioConfig(cash=context.portfolio.starting_cash, type='futures')])
    # 期货类每笔交易时的手续费是：买入时万分之1,卖出时万分之1,平今仓为万分之1
    set_order_cost(OrderCost(open_commission=0.0001, close_commission=0.0001,close_today_commission=0.0001), type='futures')
    # 设定保证金比例
    set_option('futures_margin_rate', 0.15)
    # 设置滑点（单边万5，双边千1）
    set_slippage(PriceRelatedSlippage(0.001),type='future')
    # 开盘前运行
    run_daily( before_market_open, time='before_open', reference_security=get_future_code('RB'))
    # 开盘时运行
    run_weekly(market_open, 1,time='open', reference_security=get_future_code('RB'))
    # 交易运行 
    run_weekly(Trade, 1, time='open', reference_security=get_future_code('RB'))
    # 收盘后运行
    run_daily( after_market_close, time='after_close', reference_security=get_future_code('RB'))


# 参数设置函数
def set_parameter(context):
    
    #######变量设置########
    g.domMonth = {
        'MA': ['01', '05', '09'],
		'IC':['01','02','03','04','05','06','07','08','09','10','11','12'],
		'IF':['01','02','03','04','05','06','07','08','09','10','11','12'],
		'IH':['01','02','03','04','05','06','07','08','09','10','11','12'],
		'TF':['03','06','09','12'],
		'T':['03','06','09','12'],
		'CU':['01','02','03','04','05','06','07','08','09','10','11','12'],
		'AL':['01','02','03','04','05','06','07','08','09','10','11','12'],
		'ZN':['01','02','03','04','05','06','07','08','09','10','11','12'],
		'PB':['01','02','03','04','05','06','07','08','09','10','11','12'],
		'NI':['01', '05', '09'],
		'SN':['01', '05', '09'],
		'AU':['06', '12'],
		'AG':['06', '12'],
		'RB':['01', '05', '10'],
		'HC':['01', '05', '10'],
		'BU':['06', '09', '12'],
		'RU':['01', '05', '09'],
		'M':['01', '05', '09'],
		'Y':['01', '05', '09'],
		'A':['01', '05', '09'],
		'P':['01', '05', '09'],
		'C':['01', '05', '09'],
		'CS':['01', '05', '09'],
		'JD':['01', '05', '09'],
		'L':['01', '05', '09'],
		'V':['01', '05', '09'],
		'PP':['01', '05', '09'],
		'J':['01', '05', '09'],
		'JM':['01', '05', '09'],
		'I':['01', '05', '09'],
		'SR':['01', '05', '09'],
		'CF':['01', '05', '09'],
		'ZC':['01', '05', '09'],
		'FG':['01', '05', '09'],
		'TA':['01', '05', '09'],
		'MA':['01', '05', '09'],
		'OI':['01', '05', '09'],
		'RM':['01', '05', '09'],
		'SF':['01', '05', '09'],
		'SM':['01', '05', '09'],
		'AP':['01', '05', '10'],
    }
    
    g.LastRealPrice = {} # 最新真实合约价格字典(用于吊灯止损）
    g.HighPrice = {} # 各品种最高价字典（用于吊灯止损）
    g.LowPrice = {} # 各品种最低价字典（用于吊灯止损）
    g.future_list = []  # 设置期货品种列表
    g.TradeLots = {}  # 各品种的交易手数信息
    g.PriceArray = {} # 信号计算价格字典
    g.Price_dict = {} # 各品种价格列表字典
    g.MappingReal = {} # 真实合约映射（key为symbol，value为主力合约）
    g.MappingIndex = {} # 指数合约映射 （key为 symbol，value为指数合约
    g.StatusTimer = {} # 当前状态计数器
    g.ATR = {}
    g.CurrentPrice = 0
    g.Price_DaysAgo = 0
    g.Momentum = {}
    g.ClosePrice = {}
    g.ILLIQ = {}
    g.MarginRate = 0.1
    g.Score = {}
    g.MappingNext = {}     # 映射合约
    g.NextPrice = {}       # 远期价格序列
    g.RealPrice = {}       # 主力价格序列
    g.RollYield = {}              # 展期收益率
    g.Volume = {}          # 成交量序列
    g.VSTD_Volume = {}     # 成交量变异系数
    g.SkewPrice = {}       # 偏度价格序列
    g.Skew = {}            # 偏度
    g.Basis = {}           # 基本面因子：基差
    g.Hycc = {}            # 基本面因子：会员持仓
    
    #######参数设置########
    g.ATRWindow = 20       # ATR回溯窗口长度
    g.MomentumWindow = 30  # 截面动量长度
    g.ILLIQWindow = 10     # 流动性因子长度
    g.Range = 0.3          # 做多做空名单的头尾长度
    g.NATR_stop = 2        # 追踪止损长度
    # 交易的期货品种信息
    g.instruments = ['AL','NI','CU','PB','AG',
                    'RU','MA','PP','TA','L','V',
                    'M','P','Y','OI','C','CS','JD','SR',
                    'HC','J','I','SF','RB','ZC','FG']


# 导入读入csv文件
def csv_setting(context):
    # 基差setting
    body1=read_file("Basis_xzh1.csv")
    df1 = pd.read