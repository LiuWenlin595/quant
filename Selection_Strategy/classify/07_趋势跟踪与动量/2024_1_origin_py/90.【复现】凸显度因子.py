#!/usr/bin/env python
# coding: utf-8

# In[1]: (已清理)


import empyrical as ep
import pandas as pd
import numpy as np
import qlib
from qlib.data import D
from qlib.workflow import R  # 实验记录管理器
# from qlib.workflow.record_temp import PortAnaRecord, SigAnaRecord, SignalRecord
from qlib.data.dataset.loader import StaticDataLoader
from qlib.data.dataset.handler import DataHandlerLP
from qlib.data.dataset import DatasetH
from qlib.data.dataset.processor import DropnaLabel, ProcessInf, CSRankNorm, Fillna
# from qlib.utils import init_instance_by_config
from typing import List, Tuple, Dict

from scr.core import calc_sigma, calc_weight
from scr.factor_analyze import clean_factor_data, get_factor_group_returns
from scr.qlib_workflow import run_model
from scr.plotting import model_performance_graph, report_graph

import matplotlib.pyplot as plt
import seaborn as sns

# plt中文显示
plt.rcParams["font.sans-serif"] = ["SimHei"]
# plt显示负号
plt.rcParams["axes.unicode_minus"] = False


# In[2]: (已清理)


qlib.init(provider_uri="qlib_data", region="cn")


# In[3]: (已清理)


# 使用D.feature与DataLoader,DataHandlerLP,DatasetH获取数据的数据MutiIndex索引不同
# 前者Instrument,datetime后者是datetime,Instrument
POOLS: List = D.list_instruments(D.instruments("pool"), as_list=True)
pct_chg: pd.DataFrame = D.features(POOLS, fields=["$close/Ref($close,1)-1"])
pct_chg: pd.DataFrame = pct_chg.unstack(level=0)["$close/Ref($close,1)-1"]

# 未来期收益
next_ret: pd.DataFrame = D.features(POOLS, fields=["Ref($open,-2)/Ref($open,-1)-1"])
next_ret.columns = ["next_ret"]
next_ret: pd.DataFrame = next_ret.swaplevel()
next_ret.sort_index(inplace=True)

# 基准
bench: pd.DataFrame = D.features(["000300.SH"], fields=["$close/Ref($close,1)-1"])
bench: pd.Series = bench.droplevel(level=0).iloc[:, 0]


# # 原始构造
# 
# ## 理论基础
# 
# 有效市场假说认为股票价格反映了所有可用信息，投资者无法通过观察市场变化或者分析市场数据来预测未来
# 股票价格的走势。尽管如此，仍有大量的实证研究表明金融市场中存在许多资产定价模型所无法解释的异象。为了
# 解释这些异象，许多学者开始从行为金融学的角度对投资者进行投资决策时的心理展开研究，数十年来涌现了大量
# 高质量的行为金融学实证研究文献。
# 
# 在行为金融学领域中，最具代表性的人物之一莫过于 2002 年因提出前景理论（Prospect Theory, 1979）而获得
# 诺贝尔经济学奖的学者 Kahneman 及其搭档 Tversky。前景理论研究了人们如何对未来事件做出预测、决策和行为
# 选择，以及这些决策和行为选择如何受到情绪、偏见和其他心理因素的影响。投资者在多项资产中进行选择时，可
# 能会出现不同的结果，每个结果都存在相应的发生概率。因此，某个决策的最终价值等于所有可能发生的结果的概
# 率加权平均，投资者会在所有的决策中选择价值最高的作为最终决策，即∑ 𝜋(𝑥)