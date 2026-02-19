# 克隆自聚宽文章：https://www.joinquant.com/post/34881
# 标题：可能是最接近实盘的“基本面三角”
# 作者：美吉姆优秀毕业代表

# 克隆自聚宽文章：https://www.joinquant.com/post/34881
# 标题：可能是最接近实盘的“基本面三角”
# 作者：嘟嘟嘟5

# 克隆自聚宽文章：https://www.joinquant.com/post/34881
# 标题：可能是最接近实盘的“基本面三角”
# 作者：嘟嘟嘟5

# 克隆自聚宽文章：https://www.joinquant.com/post/34825
# 标题：【股票池轮动】不可多得的基本面三角，3年200%
# 作者：潜水的白鱼

#作者白鱼对代码进行了改进，根据作者多年的投资经验，意识到一些行业容易有财务造假已经利润不可持续性
#对股票池中的增加了行业筛选函数，剔除医药等容易搞假的行业。

# 克隆自聚宽文章：https://www.joinquant.com/post/34544
# 标题：韶华研究之七--不可多得的基本面三角
# 作者：韶华不负

##策略介绍
#7.26 参考海通的基本面三角组合(盈利，增长，现金流(采用与营收的相对比))，采用静态组合(ROE/inc_total_revenue_year_on_year/ocf_to_revenue)(回测效果为负)，采用三年动态组合

# 导入函数库
from jqdata import *
from kuanke.wizard import * #不能和technical_analysis共存
from sklearn.linear_model import LinearRegression
from jqfactor import get_factor_values
from jqlib.technical_analysis import *
from six import BytesIO

# 初始化函数，设定基准等等
def after_code_changed(context):
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    unschedule_all()

    set_params()    #1 设置策略参数
    set_variables() #2 设置中间变量
    set_backtest()  #3 设置回测条件

    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=