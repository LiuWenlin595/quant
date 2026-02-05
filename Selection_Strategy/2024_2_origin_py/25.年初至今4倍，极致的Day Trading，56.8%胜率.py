# 克隆自聚宽文章：https://www.joinquant.com/post/38940
# 标题：年初至今4倍，极致的Day Trading，56.8%胜率
# 作者：Dr.QYQ

'''
优化说明:
    1.使用修正标准分
        rsrs_score的算法有：
            仅斜率slope，效果一般；
            仅标准分zscore，效果不错；
            修正标准分 = zscore * r2，效果最佳;
            右偏标准分 = 修正标准分 * slope，效果不错。
    2.将原策略的每次持有两只etf改成只买最优的一个，收益显著提高
    3.将每周调仓换成每日调仓，收益显著提高
    4.因为交易etf，所以手续费设为万分之三，印花税设为零，未设置滑点
    5.修改股票池中候选etf，删除银行，红利等收益较弱品种，增加纳指etf以增加不同国家市场间轮动的可能性
    6.根据研报，默认参数介已设定为最优
    7.加入防未来函数
    8.增加择时与选股模块的打印日志，方便观察每笔操作依据
'''

# 导入函数库
from jqdata import *
from jqlib.technical_analysis import *
import numpy as np
from datetime import datetime, timedelta
import pandas as pd

# 初始化函数


def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 用真实价格交易
    set_option('use_real_price', True)
    # 打开防未来函数
    set_option("avoid_future_data", True)
    # 将滑点设置为0
    set_slippage(FixedSlippage(0.001))
    # 设置交易成本万分之三
    # set_order_cost(OrderCost(open_tax=0, close_tax=0, open_commission=0.0003, close_commission=0.0003, close_today_commission=0, min_commission=5),
    #               type='fund')
    # 股票类每笔交易时的手续费是：买入时无佣金，卖出时佣金万分之1.5，印花税0.1%, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001,
                   close_commission=0.00015, min_commission=5), type='stock')
    # 过滤order中低于error级别的日志
    log.set_level('order', 'error')
    # 初始化各类全局变量

    # 动量轮动参数
    g.stock_num = 5  # 筛选的标的支数。
    g.stock_tobuy = 1  # 需要购买的股票数
    g.momentum_day = 29  # 最新动量参考最近momentum_day的
    g.num_days = 5  # 计算分数变化
    # rsrs择时参数
    g.ref_stock = '000300.XSHG'  # 用ref_stock做择时计算的基础数据
    g.N = 14  # 计算最新斜率slope，拟合度r2参考最近N天
    g.M = 600  # 计算最新标准分zscore，rsrs_score参考最近M天
    g.score_threshold = 0.7  # rsrs标准分指标阈值
    # 个股择时参数
    g.sec_data_num = 5  # 个股数据点数
    # g.take_profit = 0.12 # 移动止盈
    # ma择时参数
    g.mean_day = 7  # 计算ref_stock结束ma收盘价，参考最近mean_day
    # 计算初始ma收盘价，参考(mean_day + mean_diff_day)天前，窗口为mean_diff_day的一段时间
    g.mean_diff_day = 10
    g.slope_series = initial_slope_series()[:-1]  # 除去回测第一天的slope，避免运行时重复加入
    # 设置交易时间，每天运行
    run_daily(my_trade, time='09:31', reference_security='000300.XSHG')
    run_daily(check_lose, time='14:50', reference_security='000300.XSHG')
    # run_daily(check_profit, time='10:00')
    run_daily(print_trade_info, time='15:05', reference_security='000300.XSHG')

# 0-0 选取股票池


def get_stock_pool():
    # preday = str(date.today() - timedelta(1)) # get previous date
    # 从多个热门概念中选出市值在50亿以上,500亿以下的标的。
    concept_names = list(set([
        "虚拟现实",
        "元宇宙",
        "锂电池",
        "集成电路",
        "国产软件",
        "MiniLED",
        "智能穿戴",
        "智能电网",
        "智能医疗",
        "风电",
        "核电",
        "电力物联网",
        "电力改革",
        "量子通信",
        "互联网+",
        "光伏",
        "工业4.0",
        "特高压",
        "氟化工",
        "煤化工",
        "稀土永磁",
        "白酒",
        "煤炭",
        "钴",
        "盐湖提锂",
        "磷化工",
        "草甘膦",
        "航运",
        "第三代半导体",
        "太阳能",
        "柔性屏",
        "芯片",
        "新能源",
        "智能音箱",
        "苹果",
        "特斯拉",
        "宁德时代",
        "碳中和",
        "军工",
        "军民融合",
        "海工装备",
        "超级电容",
        "区块链",
        "边缘计算",
        "云计算",
        "数字货币",
        "人工智能",
        "汽车电子",
        "无人驾驶",
        "车联网",
        "网约车",
        "充电桩",
        "冷链物流",
        "OLED",
        "大飞机",
        "大数据",
        "燃料电池",
        "医疗器械",
        "生物疫苗",
        "生物医药",
        "辅助生殖",
        "健康中国",
        "基因测序",
        "超级真菌",
        "节能环保",
        "装配式建筑",
        "乡村振兴",
        "建筑节能",
        "文化传媒",
        "电子竞技",
        "网络游戏",
        "数据中心",
        "高端装备",
        '三胎',
        '养老',
        "稀缺资源",
        "稀土永磁",
        "新材料",
        "绿色电力"
    ]))

    all_concepts = get_concepts()
    concept_codes = []
    for name in concept_names:
        #print(f'concept is:{name}')
        code = all_concepts[all_concepts['name'] == name].index[0]
        concept_codes.append(code)

    all_concept_stocks = []

    for concept in concept_codes:
        all_concept_stocks += get_concept_stocks(concept)

    q = query(valuation.code).filter(valuation.market_cap >= 30,
                                     valuation.market_cap <= 1000, valuation.code.in_(all_concept_stocks))
    stock_df = get_fundamentals(q)
    stock_pool = [code for code in stock_df['code']]
    # 移除创业板和科创板标的
    stock_pool = [code for code in stock_pool if not (
        code.startswith('30') or code.startswith('688'))]
    stock_pool = filter_st_stock(stock_pool)  # 去除st
    stock_pool = filter_paused_stock(stock_pool)  # 去除停牌
    return stock_pool

# 1-1 选股模块-动量因子轮动
# 基于股票年化收益和判定系数打分,并按照分数从大到小排名


def get_rank(stock_pool, context):
    '''get rank score for stocks in stock pool'''
    send_info = []
    stock_dict_list = []
    for stock in stock_pool:
        score_list = []
        pre_dt = context.current_dt - timedelta(1)
        data = get_price(
            stock,
            end_date=context.current_dt,
            count=100,  # 多取几天以防数据不够
            frequency="120m",
            fields=["close"],
            skip_paused=True,
        )  # 最新的在最下面
        security_info = get_security_info(stock)
        stock_name = security_info.display_name
        # print(f'stock name {stock_name}')
        # 对于次新股票，可能没有数据，所以要drop NA
        data = data.dropna()
        # 收盘价
        y = data["log"] = np.log(data.close)
        # print(f'{len(y)} data points')
        # 分析的数据个数（天）
        x = data["num"] = np.arange(data.log.size)
        # 拟合 1 次多项式
        # y = kx + b, slope 为斜率 k，intercept 为截距 b
        # slope, intercept = np.polyfit(x, y, 1)
        # 直接连接首尾点计算斜率
        if len(y) < g.momentum_day + g.num_days:
            print("次新股，用所有数据")
            slope = (y.iloc[-1] - y.iloc[0]) / g.momentum_day   # 最新的