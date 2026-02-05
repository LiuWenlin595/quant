#!/usr/bin/env python
# coding: utf-8

import sys
from pathlib import Path

this_file_path = Path().resolve()
sys.path.append(str(this_file_path.parents[0]))

import pandas as pd
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt


# # 数据获取并转换

from scr.data_service import get_ts_etf_price,get_ts_index_price


etf_price: pd.DataFrame = get_ts_etf_price(
    start_date="2014-01-01",
    end_date="2023-02-17",
    fields=["open", "high", "low", "close", "vol",'amount'],
)
etf_price['vol'] *= 100
etf_price['amount'] *= 1000
etf_price.rename(columns={"vol": "volume"}, inplace=True)
etf_price["factor"] = 1

benchmark: pd.DataFrame = get_ts_index_price(
    "000300.SH",
    "2014-01-01",
    "2023-02-17",
    fields=["open", "high", "low", "close", "volume",'amount'],
)

benchmark['volume'] *= 100
benchmark['amount'] *= 1000
benchmark['factor'] = 1


data_all:pd.DataFrame = pd.concat((etf_price,benchmark))


ETF_PRICE:str = "../行业有效量价因子/etf_price"


for code,df in data_all.groupby('code'):
    csv_name:str = '{1}{0}'.format(*code.split('.')).upper() + ".csv"
    df.to_csv(str(ETF_PRICE/csv_name))


#!cd D:\WrokSpace\visualization_stock_market\sqlalchemy_to_data\qlib_scripts && python dump_bin.py dump_all --csv_path D:\WrokSpace\visualization_stock_market\sqlalchemy_to_data\行业有效量价因子\etf_price --qlib_dir D:\WrokSpace\visualization_stock_market\sqlalchemy_to_data\行业有效量价因子\qlib_etf_data --date_field_name "trade_date" --exclude_fields ('code',)


# get_ipython().system('cd e:\\WorkSpace\\visualization_stock_market\\sqlalchemy_to_data\\qlib_scripts && python dump_bin.py dump_all --csv_path e:\\WorkSpace\\visualization_stock_market\\sqlalchemy_to_data\\行业有效量价因子\\etf_price --qlib_dir e:\\WorkSpace\\visualization_stock_market\\sqlalchemy_to_data\\行业有效量价因子\\qlib_etf_data --date_field_name "trade_date" --exclude_fields (\'code\',)')


# # 初始化qlib

import qlib
from qlib.workflow import R  # 实验记录管理器
from qlib.data import D # 基础行情数据服务的对象
from qlib.utils import init_instance_by_config, flatten_dict
from qlib.constant import REG_CN
from qlib.workflow.record_temp import SignalRecord, SigAnaRecord


qlib.init(provider_uri="qlib_etf_data", region=REG_CN) # 初始化


# # 训练模型实例化

# ## 价量因子构造
# 
# |大类因子|因子名称|计算公式|
# |--|--|--|
# |动量|二阶动量|$EWMA(\frac{Close_{t}-mean(Close_{t-window_{1:t}})}{mean(Close_{t-window_{1:t}})}-delay(\frac{Close_{t}-mean(Close_{t-window1:t})}{mean(Close_{t-window1:t})},window2),window)$|
# |动量|动量期限差|$\frac{Close_{t}-Close_{t-window1}}{Close_{t-window_{1}}}-\frac{Close_{t}-Close_{t-window_{2}}}{Close_{t-window2}}$,window1>window2|
# |波动率|成交金额波动|$-STD(Amount)$|
# |波动率|成交量波动|$-STD(Volume)$|
# |换手率|换手率变化|$\frac{Mean(turnover_{t-window_{1:t}})}{Mean(turnover_{t-window_{2:t}})}$,window1>window2|
# |多空对比|多空对比总量|$-\sum^{i=t}_{i=t-window}\frac{Close_{i}-Low_{i}}{Hight_{i}-Close_{i}}$|
# |多空对比|多空对比变化|$EWMA(Volume*\frac{(Close-Low)-(High-Close)}{High-Low},window_{1})-EWNA(Volume*\frac{(Close-Low)-(High-Close)}{High-Low},window_{2})$,$window_1>window_2$|
# |量价背离|量价背离协方差(收盘价)|$-rank\{covariance[rank(Close),rank(Volume),window]\}$|
# |量价背离|量价相关系数(收盘价)|$-correlation(Close,Volume,window)$|
# |量价背离|一阶量价背离|$-correlation[Rank(\frac{Volume_{i}}{Volume_{i-1}}-1),Rank(\frac{Close_{i}}{Open_{i}}-1),window]$|
# |量幅同向|量幅同向|$correlation[Rank(\frac{Volume_{i}}{Volume_{i-1}}-1),Rank(\frac{High_{i}}{Low_{i}}-1),window]$|

# 由于研报未给出具体窗口参数。所以再构造因子时使用了5,10,20,60,120,180这几个常用的窗口期,共生成了192个因子。

# 下图为行业ETF的数量变动情况,在2020年ETF行业占比才到全部行业etf的60%,一共68支，总的来说时间过短。所以后续我们使用全部etf作为标的池。

industry_etf:pd.DataFrame = pd.read_csv('../行业有效量价因子/qlib_etf_data/instruments/industry_etf.txt',delimiter='\t',header=None,parse_dates=[1,2])
industry_etf.columns = ['symbol','begin_dt','end_dt']

fig,axes = plt.subplots(1,2,figsize=(10,4))
bar_ax = industry_etf["begin_dt"].dt.year.value_counts().sort_index().plot.bar(ax=axes[0])

line_ax = industry_etf["begin_dt"].dt.year.value_counts().div(
    len(industry_etf)
).sort_index().cumsum().plot(marker='o',ax=axes[1])


###################################
# 参数配置
###################################
# 数据处理器参数配置：整体数据开始结束时间，训练集开始结束时间，股票池
TARIN_PERIODS: Tuple = ("2014-01-01", "2017-12-31")
VALID_PERIODS: Tuple = ("2018-01-01", "2020-12-31")
TEST_PERIODS: Tuple = ("2021-01-01", "2023-02-17")

data_handler_config:Dict = {
    "start_time": TARIN_PERIODS[0],
    "end_time": TEST_PERIODS[1],
    "fit_start_time": TARIN_PERIODS[0],
    "fit_end_time": TARIN_PERIODS[1],
    "instruments": "market",
}

# 任务参数配置
task:Dict = {
    # 机器学习模型参数配置
    "model": {
        # 模型类
        "class": "LGBModel",
        # 模型类所在模块
        "module_path": "qlib.contrib.model.gbdt",
        # 模型类超参数配置，未写的则采用默认值。这些参数传给模型类
        "kwargs": {  # kwargs用于初始化上面的class
            "loss": "mse",
            "colsample_bytree": 0.8879,
            "learning_rate": 0.0421,
            "subsample": 0.8789,
            "lambda_l1": 205.6999,
            "lambda_l2": 580.9768,
            "max_depth": 15,
            "num_leaves": 210,
            "num_threads": 20,
            "early_stopping_rounds": 200,  # 训练迭代提前停止条件
            "num_boost_round": 1000,  # 最大训练迭代次数
        },
    },
    "dataset": {  # 　因子数据集参数配置
        # 数据集类，是Dataset with Data(H)andler的缩写，即带数据处理器的数据集
        "class": "DatasetH",
        # 数据集类所在模块
        "module_path": "qlib.data.dataset",
        # 数据集类的参数配置
        "kwargs": {
            "handler": {  # 数据集使用的数据处理器配置
                "class": "VolumePriceFactor192",  # 数据处理器类，继承自DataHandlerLP
                "module_path": "scr.factor_expr", # 数据处理器类所在模块
                "kwargs": data_handler_config,  # 数据处理器参数配置
            },
            "segments": {  # 数据集时段划分
                "train": TARIN_PERIODS,  # 训练集时段
                "valid": VALID_PERIODS,  # 验证集时段
                "test": TEST_PERIODS,  # 测试集时段
            },
        },
    },
}


# 实例化模型对象
model = init_instance_by_config(task["model"])
# 实例化数据集，从基础行情数据计算出的包含所有特征（因子）和标签值的数据集。
dataset = init_instance_by_config(task["dataset"])  # 类型DatasetH


# 保存数据方便后续使用
dataset.config(dump_all=True,recursive=True)
dataset.to_pickle(path="dataset.pkl",dump_all=True)


# 读取dataset
import pickle

with open("dataset.pkl", "rb") as file_dataset:
    dataset = pickle.load(file_dataset)


# # dataset数据查询：特征，标签

# 返回（原始数据集中）训练集、验证集、测试集的全部特征和标签数据
# dara_key = "raw"表示返回原始数据 不加则是预处理后的数据
df_train, df_valid, df_test =  dataset.prepare(segments=["train", "valid", "test"], data_key = "raw") 


df_test.head()


# ## 查看特征定义

fea_expr, fea_name = dataset.handler.get_feature_config()
print('fea_expr',fea_expr)
print()
print('fea_name',fea_name)
print()
print(f'特征个数:{len(fea_expr)}')


# # 模型训练

# R变量可以理解为实验记录管理器。
with R.start(experiment_name="train"): # 注意，设好实验名
    # 可选：记录task中的参数到运行记录下的params目录
    R.log_params(**flatten_dict(task))

    # 训练模型，得到训练好的模型model
    model.fit(dataset)
    
    # 可选：训练好的模型以pkl文件形式保存到本次实验运行记录目录下的artifacts子目录，以备后用  
    R.save_objects(trained_model=model)

    # 打印本次实验记录器信息，含记录器id，experiment_id等信息
    print('info', R.get_recorder().info)


# # 预测:在测试集上测试

with R.start(experiment_name="predict"):
 
    # 当前实验的实验记录器：预测实验记录器
    predict_recorder = R.get_recorder()

    # 生成预测结果文件: pred.pkl, label.pkl存放在运行记录目录下的artifacts子目录   
    # 本实验默认是站在t日结束时刻，预测t+2日收盘价相对t+1日开盘价的收益率，计算公式为 Ref($open, -2)/Ref($open, -1) - 1
    sig_rec = SignalRecord(model, dataset, predict_recorder)  # 将训练好的模型、数据集、预测实验记录器传递给信号记录器      
    sig_rec.generate()
    
    # 生成预测结果分析文件，在artifacts\sig_analysis 目录生成ic.pkl,ric.pkl文件
    sigAna_rec = SigAnaRecord(predict_recorder) # 信号分析记录器
    sigAna_rec.generate()

    print('info', R.get_recorder().info)


# # 预测结果查询

# 加载pkl文件 
with R.start():
    train_recorder = R.get_recorder(experiment_id='1',recorder_id='3b6e1cdcc6fa4bfca9dbb96a8d834e52')
    model = train_recorder.load_object("trained_model")
    predict_recorder = R.get_recorder(experiment_id='2',recorder_id='ea512bd4a0c34b9ca523f8f94fc90bdc')


# 这个pkl文件记录的是测试集未经数据预处理的原始标签值
label_df = predict_recorder.load_object("label.pkl") 
# 修改列名LABEL0为label 这个label其实就是下一期得收益率
label_df.columns = ['label'] 

pred_df = predict_recorder.load_object("pred.pkl") # 加载测试集预测结果到dataframe

print('label_df', label_df) # 预处理后的测试集标签值 
print('pred_df', pred_df) # 测试集对标签的预测值，score就是预测值


# ## IC,Rank IC查询

ic_df = predict_recorder.load_object("sig_analysis/ic.pkl")

ric_df = predict_recorder.load_object("sig_analysis/ric.pkl")

# 所有绩效指标
print("list_metrics", predict_recorder.list_metrics())
# IC均值：每日IC的均值，一般认为|IC|>0.03说明因子有效，注意 -0