#!/usr/bin/env python
# coding: utf-8

# In[1]:


import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn import metrics
from sklearn.metrics import mean_squared_error
from sklearn.metrics import accuracy_score
import joblib
import pydotplus
from sklearn.tree import export_graphviz
from sklearn.model_selection import GridSearchCV
import lightgbm as lgb
from lightgbm import plot_importance
import matplotlib.pyplot as plt
# get_ipython().run_line_magic('matplotlib', 'inline')


# In[70]:


file = 'trainData_20211101_all.txt'
with open(file, 'r') as f:
    data =  f.readlines()
print(f'data length = {len(data)}')


# In[71]:


# 全部
codeList = []
train = []
label = []
for line in data[:]:
    tmp = list(line.replace('True', '1').replace('False', '0').replace(' ', '').split(','))
    code = tmp[0].replace('\'', '')
#     codeList.append(code)
    train.append([float(i) for i in tmp[1:-1]])
    label.append(float(tmp[-1]))
#     print(f'tmp={tmp}')

# print(f'codeList={codeList}')
# print(f'label={label}')
# print(f'train={train}')

label_1_thre = 0.03 # 涨幅多少才算上涨的阈值
final_label = [int(i > label_1_thre) for i in label]


# In[29]:


# 创业板
codeList = []
train = []
label = []
for line in data[:]:
    tmp = list(line.replace('True', '1').replace('False', '0').replace(' ', '').split(','))
    code = tmp[0].replace('\'', '')
#     print(f'code={code}')
    if '30' != code[:2]:
        codeList.append(code)
        train.append([float(i) for i in tmp[1:-1]])
        label.append(float(tmp[-1]))
#     print(f'tmp={tmp}')

# print(f'codeList={codeList}')
# print(f'label={label}')
# print(f'train={train}')

label_1_thre = 0.03 # 涨幅多少才算上涨的阈值
final_label = [int(i > label_1_thre) for i in label]


# In[34]:


codeList[:10]


# ### 均分label为1和0的

# In[72]:


len_label_1 = sum(final_label)
len_label_0 = len(final_label) - sum(final_label)
print(f'len_label_1={len_label_1}')
print(f'len_label_0={len_label_0}')
min_num = min(len_label_1, len_label_0)

avg_train = []
avg_label = []
count_0 = 0
count_1 = 0
for i in range(len(final_label)):
    if final_label[i] == 1 and count_1 < min_num:
        avg_train.append(train[i])
        avg_label.append(final_label[i])
        count_1 += 1
    if final_label[i] == 0 and count_0 < min_num:
        avg_train.append(train[i])
        avg_label.append(final_label[i])
        count_0 += 1
print('done')
print(f'now trainSet length = {len(avg_train)}, label length = {len(avg_label)}')


# In[73]:


x_train, x_test, y_train, y_test = train_test_split(avg_train, avg_label, train_size=0.8, random_state=666)
x_train = np.array(x_train)
x_test = np.array(x_test)
y_train = np.array(y_train)
y_test = np.array(y_test)


# In[22]:


x_train[0]


# In[12]:


def get_acc_for_T_F(predict, label):
    sum_1 = 0
    sum_0 = 0
    right_1 = 0
    right_0 = 0
    pred_1 = 0
    real_1 = 0
    pred_0 = 0
    real_0 = 0
    for i in range(len(label)):
        if label[i] == 1:
            sum_1 += 1
            if predict[i] == 1:
                right_1 += 1
        elif label[i] == 0:
            sum_0 += 1
            if predict[i] == 0:
                right_0 += 1
    
    for i in range(len(label)):
        if predict[i] == 1:
            pred_1 += 1
            if label[i] == 1:
                real_1 += 1
        elif predict[i] == 0:
            pred_0 += 1
            if label[i] == 0:
                real_0 += 1
    print(f'right1/sum1={right_1}/{sum_1}={round(right_1/sum_1*100, 2)}%')
    print(f'right0/sum0={right_0}/{sum_0}={round(right_0/sum_0*100, 2)}%')
    if pred_1 > 0:
        print(f'real_1/pred_1={real_1}/{pred_1}={round(real_1/pred_1*100, 2)}%')
        print(f'real_0/pred_0={real_0}/{pred_0}={round(real_0/pred_0*100, 2)}%')
    else:
        print('没有预测为涨的')


# ### Step 1 调整max_depth 和 num_leaves

# In[23]:


# fit时不需要转成gbm的data格式

# 为lightgbm准备Dataset格式数据
# lgb_train = lgb.Dataset(x_train, y_train)
# lgb_eval = lgb.Dataset(x_test, y_test, reference=lgb_train)
parameters = {
    'max_depth': list(range(8, 13, 2),
    'num_leaves': list(range(100, 501, 100)),
}

gbm = lgb.LGBMClassifier(objective = 'binary',
                         is_unbalance = True,
                         metric = 'binary_logloss,auc',
                         max_depth = 6,
                         num_leaves = 40,
                         learning_rate = 0.1,
                         feature_fraction = 0.7,
                         min_child_samples=21,
                         min_child_weight=0.001,
                         bagging_fraction = 1,
                         bagging_freq = 2,
                         reg_alpha = 0.001,
                         reg_lambda = 8,
                         cat_smooth = 0,
                         num_iterations = 200,   
                        )

gsearch = GridSearchCV(gbm, param_grid=parameters, scoring='roc_auc', cv=3)

print('Start training...')

gsearch.fit(x_train, y_train)

print('参数的最佳取值:{0}'.format(gsearch.best_params_))
print('最佳模型得分:{0}'.format(gsearch.best_score_))
print(gsearch.cv_results_['mean_test_score'])
print(gsearch.cv_results_['params'])


# ### Step2 调整min_data_in_leaf 和 min_sum_hessian_in_leaf

# In[28]:


parameters = {
    'min_child_samples': list(range(100, 501, 100)),
    'min_child_weight': [0.