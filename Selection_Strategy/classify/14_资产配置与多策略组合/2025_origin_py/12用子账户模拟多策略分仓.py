# 克隆自聚宽文章：https://www.joinquant.com/post/47344
# 标题：用子账户模拟多策略分仓
# 作者：赌神Buffett

'''
多策略分子账户并行

用到的策略：
wywy1995：机器学习多因子小市值
wywy1995、hayy：ETF核心资产轮动-添油加醋
Ahfu、伺底而动：大市值价值投资（改称PB策略）
开心果、十足的小市值迷、wzg3768、langcheng999：经典大妈买菜选股法高股息低价股

'''
# 导入函数库
from jqdata import *
from jqfactor import get_factor_values
import datetime


# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    # 过滤掉order系列API产生的比error级别低的log
    log.set_level('order', 'error')
    
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    set_slippage(PriceRelatedSlippage(0.01), type='stock')

    # 临时变量
    
    # 持久变量
    g.strategys = {}
    g.portfolio_value_proportion = [0.2,0.2,0.3,0.3]
    
    # 创建策略实例
    set_subportfolios([
        SubPortfolioConfig(context.portfolio.starting_cash*g.portfolio_value_proportion[0], 'stock'), 
        SubPortfolioConfig(context.portfolio.starting_cash*g.portfolio_value_proportion[1], 'stock'),
        SubPortfolioConfig(context.portfolio.starting_cash*g.portfolio_value_proportion[2], 'stock'),
        SubPortfolioConfig(context.portfolio.starting_cash*g.portfolio_value_proportion[3], 'stock'),
    ])
    
    params = {
        'max_hold_count': 1,    # 最大持股数
        'max_select_count': 1,  # 最大输出选股数
    }
    etf_strategy = ETF_Strategy(context, subportfolio_index=0, name='ETF轮动策略', params=params)
    g.strategys[etf_strategy.name] = etf_strategy
    
    params = {
        'max_hold_count': 1,        # 最大持股数
        'max_select_count': 3,      # 最大输出选股数
    }
    pb_strategy = PB_Strategy(context, subportfolio_index=1, name='PB策略', params=params)
    g.strategys[pb_strategy.name] = pb_strategy
    
    params = {
        'max_hold_count': 3,        # 最大持股数
        'max_select_count': 5,      # 最大输出选股数
        'use_empty_month': True,    # 是否在指定月份空仓
        'empty_month': [4],         # 指定空仓的月份列表
        'use_stoplost': True,       # 是否使用止损
    }
    xsz_strategy = XSZ_Strategy(context, subportfolio_index=2, name='小市值策略', params=params)
    g.strategys[xsz_strategy.name] = xsz_strategy

    params = {
        'max_hold_count': 1,        # 最大持股数
        'max_select_count': 3,      # 最大输出选股数
        # 'use_empty_month': True,    # 是否在指定月份空仓
        # 'empty_month': [4],         # 指定空仓的月份列表
        'use_stoplost': True,       # 是否使用止损
    }
    dama_strategy = DaMa_Strategy(context, subportfolio_index=3, name='菜场大妈策略', params=params)
    g.strategys[dama_strategy.name] = dama_strategy

    # 执行计划
    if g.portfolio_value_proportion[0] > 0:
        run_daily(etf_select, '7:40') 
        run_daily(etf_adjust, '10:00')
    if g.portfolio_value_proportion[1] > 0:
        run_daily(pb_day_prepare, time='7:30')
        run_monthly(pb_select, 1, time='7:40')
        run_daily(pb_open_market, time='9:30')
        run_monthly(pb_adjust, 1, time='9:35')
        run_daily(pb_sell_when_highlimit_open, time='14:00')
        run_daily(pb_sell_when_highlimit_open, time='14:50')
    if g.portfolio_value_proportion[2] > 0:
        run_daily(xsz_day_prepare, time='7:30')
        run_weekly(xsz_select, 1, time='7:40')
        run_daily(xsz_open_market, time='9:30')
        run_weekly(xsz_adjust, 1, time='9:35')
        run_daily(xsz_sell_when_highlimit_open, time='14:00')
        run_daily(xsz_sell_when_highlimit_open, time='14:50')
    if g.portfolio_value_proportion[3] > 0:
        run_daily(dama_day_prepare, time='7:30')
        run_monthly(dama_select, 15, time='7:40')
        run_daily(dama_open_market, time='9:30')
        run_monthly(dama_adjust, 15, time='10:30')
        run_daily(dama_sell_when_highlimit_open, time='14:00')
        run_daily(dama_sell_when_highlimit_open, time='14:50')
        
    # run_daily(print_trade_info, time='15:01')


def etf_select(context):
    g.strategys['ETF轮动策略'].select(context)

def etf_adjust(context):
    g.strategys['ETF轮动策略'].adjust(context)


def pb_day_prepare(context):
    g.strategys['PB策略'].day_prepare(context)

def pb_select(context):
    g.strategys['PB策略'].select(context)
        
def pb_adjust(context):
    g.strategys['PB策略'].adjust(context)

def pb_open_market(context):
    g.strategys['PB策略'].close_for_stoplost(context)

def pb_sell_when_highlimit_open(context):
    g.strategys['PB策略'].sell_when_highlimit_open(context)


def xsz_day_prepare(context):
    g.strategys['小市值策略'].day_prepare(context)

def xsz_select(context):
    g.strategys['小市值策略'].select(context)

def xsz_adjust(context):
    g.strategys['小市值策略'].adjust(context)

def xsz_open_market(context):
    g.strategys['小市值策略'].close_for_empty_month(context)
    g.strategys['小市值策略'].close_for_stoplost(context)

def xsz_sell_when_highlimit_open(context):
    g.strategys['小市值策略'].sell_when_highlimit_open(context)


def dama_day_prepare(context):
    g.strategys['菜场大妈策略'].day_prepare(context)

def dama_select(context):
    g.strategys['菜场大妈策略'].select(context)

def dama_adjust(context):
    g.strategys['菜场大妈策略'].adjust(context)

def dama_open_market(context):
    g.strategys['菜场大妈策略'].close_for_empty_month(context)
    g.strategys['菜场大妈策略'].close_for_stoplost(context)

def dama_sell_when_highlimit_open(context):
    g.strategys['菜场大妈策略'].sell_when_highlimit_open(context)
    
    
# 打印交易记录
def print_trade_info(context):
    orders = get_orders()
    for _order in orders.values():
        print('成交记录：'+str(_order))
        

# 策略基类
# 同一只股票只买入1次，卖出时全部卖出
class Strategy:
    def __init__(self, context, subportfolio_index, name, params):
        self.subportfolio_index = subportfolio_index
        # self.subportfolio = context.subportfolios[subportfolio_index]
        self.name = name
        self.params = params
        self.max_hold_count = self.params['max_hold_count'] if 'max_hold_count' in self.params else 1                       # 最大持股数
        self.max_select_count = self.params['max_select_count'] if 'max_select_count' in self.params else 5                 # 最大输出选股数
        self.hold_limit_days = self.params['hold_limit_days'] if 'hold_limit_days' in self.params else 20                   # 计算最近持有列表的天数
        self.use_empty_month = self.params['use_empty_month'] if 'use_empty_month' in self.params else False                # 是否有空仓期
        self.empty_month = self.params['empty_month'] if 'empty_month' in self.params else []                               # 空仓月份
        self.use_stoplost = self.params['use_stoplost'] if 'use_stoplost' in self.params else False                         # 是否使用止损
        self.stoplost_silent_days = self.params['stoplost_silent_days'] if 'stoplost_silent_days' in self.params else 20    # 止损后不交易的天数
        self.stoplost_level = self.params['stoplost_level'] if 'stoplost_level' in self.params else 0.2                     # 止损的下跌幅度（按买入价）

        self.select_list = []
        self.hold_list = []                 # 昨收持仓
        self.history_hold_list = []         # 最近持有列表
        self.not_buy_again_list = []        # 最近持有不再购买列表
        self.yestoday_high_limit_list = []  # 昨日涨停列表
        self.stoplost_date = None           # 止损日期，为None是表示未进入止损


    def day_prepare(self, context):
        subportfolio = context.subportfolios[self.subportfolio_index]
        
        # 获取昨日持股列表
        self.hold_list = list(subportfolio.long_positions)
        
        # 获取最近一段时间持有过的股票列表
        self.history_hold_list.append(self.hold_list)
        if len(self.history_hold_list) >= self.hold_limit_days:
            self.history_hold_list = self.history_hold_list[-self.hold_limit_days:]
        temp_set = set()
        for lists in self.history_hold_list:
            for stock in lists:
                temp_set.add(stock)
        self.not_buy_again_list = list(temp_set)
        
        # 获取昨日持股涨停列表
        if self.hold_list != []:
            df = get_price(self.hold_list, end_date=context.previous_date, frequency='daily', fields=['close','high_limit'], count=1, panel=False, fill_paused=False)
            df = df[df['close'] == df['high_limit']]
            self.yestoday_high_limit_list = list(df.code)
        else:
            self.yestoday_high_limit_list = []
        
        # 检查空仓期
        self.check_empty_month(context)
        # 检查止损
        self.check_stoplost(context)
        
    
    # 基础股票池
    def stockpool(self, context, pool_id=1):
        lists = list(get_all_securities(types=['stock'], date=context.previous_date).index)
        if pool_id ==0:
            pass
        elif pool_id == 1:
            lists = self.filter_kcbj_stock(lists)
            lists = self.filter_st_stock(lists)
            lists = self.filter_paused_stock(lists)
            lists = self.filter_highlimit_stock(context, lists)
            lists = self.filter_lowlimit_stock(context, lists)
            
        return lists
        
    
    # 选股
    def select(self, context):
        # 空仓期控制
        if self.use_empty_month and context.current_dt.month in (self.empty_month):
            return
        # 止损期控制
        if self.stoplost_date is not None:
            return
        select.select_list = []
    
    
    # 打印交易计划
    def print_trade_plan(self, context, select_list):
        subportfolio = context.subportfolios[self.subportfolio_index]
        current_data = get_current_data()   # 取股票名称
    
        content = context.current_dt.date().strftime("%Y-%m-%d") + ' ' + self.name + " 交易计划：" + "\n"

        for stock in subportfolio.long_positions:
            if stock not in select_list[:self.max_hold_count]:
                content = content + stock + ' ' + current_data[stock].name + ' 卖出\n'

        for stock in select_list:
            if stock not in subportfolio.long_positions and stock in select_list[:self.max_hold_count]:
                content = content + stock + ' ' + current_data[stock].name + ' 买入\n'
            elif stock in subportfolio.long_positions and stock in select_list[:self.max_hold_count]:
                content = content + stock + ' ' + current_data[stock].name + ' 继续持有\n'
            else:
                content = content + stock + ' ' + current_data[stock].name + '\n'

        if ('买' in content) or ('卖' in content):
            print(content)


    # 调仓
    def adjust(self, context):
        # 空仓期控制
        if self.use_empty_month and context.current_dt.month in (self.empty_month):
            return
        # 止损期控制
        if self.stoplost_date is not None:
            return
        
        # 先卖后买
        hold_list = list(context.subportfolios[self.subportfolio_index].long_positions)
        sell_stocks = []
        for stock in hold_list:
            if stock not in self.select_list[:self.max_hold_count]:
                sell_stocks.append(stock)
        self.sell(context, sell_stocks)
        self.buy(context, self.select_list)


    # 涨停打开卖出
    def sell_when_highlimit_open(self, context):
        if self.yestoday_high_limit_list != []:
            for stock in self.yestoday_high_limit_list:
                if stock in context.subportfolios[self.subportfolio_index].long_positions:
                    current_data = get_price(stock, end_date=context.current_dt, frequency='1m', fields=['close','high_limit'], 
                        skip_paused=False, fq='pre', count=1, panel=False, fill_paused=True)
                    if current_data.iloc[0,0] < current_data.iloc[0,1]:
                        self.sell(context, [stock])
                        content = context.current_dt.date().strftime("%Y-%m-%d") + ' ' + self.name + ': {}涨停打开，卖出'.format(stock) + "\n"
                        print(content)


    
    # 空仓期检查
    def check_empty_month(self, context):
        subportfolio = context.subportfolios[self.subportfolio_index]
        if self.use_empty_month and context.current_dt.month in (self.empty_month) and len(subportfolio.long_positions) > 0:
            content = context.current_dt.date().strftime("%Y-%m-%d") + self.name + ': 进入空仓期' + "\n"
            for stock in subportfolio.long_positions:
                content = content + stock + "\n"
            print(content)


    # 进入空仓期清仓
    def close_for_empty_month(self, context):
        subportfolio = context.subportfolios[self.subportfolio_index]
        if self.use_empty_month and context.current_dt.month in (self.empty_month) and len(subportfolio.long_positions) > 0:
            self.sell(context, list(subportfolio.long_positions))


    # 止损检查
    def check_stoplost(self, context):
        subportfolio = context.subportfolios[self.subportfolio_index]
        if self.use_stoplost:
            if self.stoplost_date is None: