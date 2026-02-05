#!/usr/bin/env python
# coding: utf-8

import numpy as np
import pandas as pd
import datetime as dt
from sklearn.cluster import KMeans

pd.set_option('display.width', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

nday = 243
Rf = 2.0
n_cluster = 10
n_class = 5
rday = sqrt(nday)

dt_now = dt.datetime.now().date()
dt_now

# 基金
all_fund = get_all_securities('fund', dt_now)
len(all_fund)

# 一年前上市
dt_1y = dt_now - dt.timedelta(365)
funds = all_fund[all_fund.start_date < dt_1y].index.tolist()
len(funds)

# 流动性
hm = history(nday, '1d', 'money', funds).mean()
funds = hm[hm > 1e6].index.tolist()
len(funds)

# 提取历史价格
p = history(nday, '1d', 'close', funds).dropna(axis=1)
r = np.log(p).diff()[1:]

# K-means聚类
cluster = KMeans(n_clusters=n_cluster).fit(r.T)

# 分类
y = cluster.fit_predict(r.T)

# 标签
c = pd.Series(y, r.columns)
c.head()

df = pd.DataFrame(columns=['Cluster', 'Name'])
for k in range(n_cluster):
    choice = []
    for s in c.index:
        if c[s] == k:
            choice.append(s) 
    print(k, len(choice))
    xm = hm[choice].sort_values(ascending=False).head(n_class)
    for s in xm.index:
        df.loc[s] = [k, get_security_info(s).display_name]
len(df)

df.sort_values(by=['Cluster', 'Name'], ascending=True)