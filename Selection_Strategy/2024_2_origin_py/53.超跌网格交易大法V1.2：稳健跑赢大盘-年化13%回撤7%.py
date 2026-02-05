# 克隆自聚宽文章：https://www.joinquant.com/post/36039
# 标题：超跌网格交易大法V1.2：稳健跑赢大盘-年化13%回撤7%
# 作者：wwr

enable_profile()
from jqlib.technical_analysis import*
from jqdata import *
import time
import numpy as np
import copy
import datetime
import pandas as pd
from jqfactor import get_factor_values


#股票版本
origin_param_list_0 = [
         ('000063.XSHE',50000,5000,1080,0.95,1.1,1.3)
        ,('601088.XSHG',50000,5000,1080,0.95,1.1,1.3)
        ,('601111.XSHG',50000,5000,1080,0.95,1.1,1.3)
        ,('510050.XSHG',50000,5000,1080,0.95,1.1,1.3)
        ,('600104.XSHG',50000,5000,1080,0.95,1.1,1.3)
        ,('002415.XSHE',50000,5000,1080,0.95,1.1,1.3)
        ,('601166.XSHG',50000,5000,1080,0.95,1.1,1.3)
        ,('600547.XSHG',50000,5000,1080,0.95,1.1,1.3)
        ,('513100.XSHG',50000,5000,1080,0.95,1.1,1.3)
        ,('601318.XSHG',50000,5000,1080,0.95,1.1,1.3)
        ,('600900.XSHG',50000,5000,1080,0.95,1.1,1.3)
        ,('601688.XSHG',