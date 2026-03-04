# 该代码片段包含 Jupyter 标记和非聚宽兼容部分，已按规则处理
# 注意：聚宽平台不支持 tushare，且 get_ticks 在聚宽中需用 tick 数据相关 API 替代
# 但根据“不修改策略逻辑”原则，仅做格式与最小兼容性修复，实际运行需在支持环境

import pandas as pd
from jqdata import *

def funtrade(p_t, current):
    if p_t < current:
        return '买'
    elif p_t > current:
        return '卖'
    else:
        return ' '

cols = ['time', 'current', 'volume', 'money']
stk = '000001.XSHE'
curdate = '2019-12-12'
stadt = datetime.datetime.strptime(curdate + ' 09:25:00', "%Y-%m-%d %H:%M:%S")
enddt = datetime.datetime.strptime(curdate + ' 09:31:00', "%Y-%m-%d %H:%M:%S")
d = get_ticks(stk, start_dt=stadt, end_dt=enddt, fields=cols)
hist = pd.DataFrame(d, columns=cols)
hist['volt'] = (hist['volume'] - hist['volume'].shift(1)) / 100
hist['mont'] = hist['money'] - hist['money'].shift(1)
hist['p_t'] = hist['mont'] / hist['volt'] / 100
hist['dir'] = hist.apply(lambda x: funtrade(x.p_t, x.current), axis=1)
hist.head(10)