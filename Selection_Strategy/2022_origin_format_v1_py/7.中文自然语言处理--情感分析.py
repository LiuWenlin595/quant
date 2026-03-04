#!/usr/bin/env python
# coding: utf-8

# 中文自然语言处理用于情感分析

# 本文内容大部分非原创，借用前人内容，只是在思路上向金融量化靠近。
# 
# 原创连接：https://www.youtube.com/watch?v=-mcrmLmNOXA
# 
# 需要的库
# 
# numpy
# 
# jieba 用于分词
# 
# gensim 用于加载预训练的词向量
# 
# tensorflow 用于构建神经网络
# 
# matplotlib

# 首先加载必用的库
import numpy as np
import matplotlib.pyplot as plt
import re
import jieba # 结巴分词
# gensim用来加载预训练word vector
from gensim.models import KeyedVectors
import warnings
warnings.filterwarnings("ignore")

# 导入预训练词向量
# 
# 本文使用了北京师范大学中文信息处理研究所与中国人民大学 DBIIR 实验室的研究者开源的"chinese-word-vectors" 
# 
# github链接为：
# https://github.com/Embedding/Chinese-Word-Vectors
# 
# 云盘连接：https://pan.baidu.com/s/1O6bmpFXM58G2_wVMQuZp8Q
# 
# 提取码：pp2z
# 
# 将下载的文件解压到自己指定的目录，由于聚宽云平台上存储空间有限，本文未使用金融行业词向量，因为这个要1.2G左右，所以使用知乎内容训练的词向量，如果在本机跑数据，直接更换即可。

# 使用gensim加载预训练中文分词embedding
cn_model = KeyedVectors.load_word2vec_format('sgns.zhihu.bigram', 
                                          binary=False)

# 词向量模型  
# 在这个词向量模型里，每一个词是一个索引，对应的是一个长度为300的向量，我们今天需要构建的LSTM神经网络模型并不能直接处理汉字文本，需要先进行分次并把词汇转换为词向量。
# 
# 第一步：使用jieba进行分词，将文章句子转化成切分成词语
# 
# 第二步：将词语索引化，加载的词向量模型中包括所有中文词语，按照使用频率大小排列，每个词语对应一个索引值
# 
# 第三步：词向量化。每个索引对应一个词向量，词向量就是用向量方式描述词语，成功实现由语言向数值的转换。一般常用的词向量都是300维的，也就是说一个汉语词语用一个300维的向量表示，向量数值已经标准化，取值在[-1,1]之间
# 
# 第四步：构建循环神经网络，可以使用RNN,GRU,LSTM具体那个方法好取决于不同的问题，需要多尝试。
# 
# 第五步：使用构建好的语料训练神经网络，最后用训练好的神经网络做预测。

# 由此可见每一个词都对应一个长度为300的向量，取值在[-1,1]之间
embedding_dim = cn_model['经济'].shape[0]
print('词向量的长度为{}'.format(embedding_dim))
cn_model['经济']

# 模型自带的api可以计算相似度，原理是计算两个向量的余弦相似度，即向量点乘后除以两个向量的模。
cn_model.similarity('橘子', '橙子')

# dot（'橘子'/|'橘子'|， '橙子'/|'橙子'| ）
np.dot(cn_model['橘子']/np.linalg.norm(cn_model['橘子']), 
cn_model['橙子']/np.linalg.norm(cn_model['橙子']))

# 找出最相近的10个词，余弦相似度,此功能可用于扩大同类词范围，在使用贝叶斯方法时，可以填充备选词库
cn_model.most_similar(positive=['牛市'], topn=10)

# 找出不同的词
test_words = '老师 会计师 程序员 律师 医生 老人'
test_words_result = cn_model.doesnt_match(test_words.split())
print('在 '+test_words+' 中:\n不是同一类别的词为: %s' %test_words_result)

#
cn_model.most_similar(positive=['女人','女儿'], negative=['男人'], topn=1)

# 训练语料  
# 
# 语料下载和上面词向量云盘下载在一个地方。
# 
# 解压后分别为pos和neg，每个文件夹里有2000个txt文件，每个文件内有一段评语，共有4000个训练样本，这样大小的样本数据在NLP中属于非常迷你的：

# 获得样本的索引，样本存放于两个文件夹中，
# 分别为 正面评价'pos'文件夹 和 负面评价'neg'文件夹
# 每个文件夹中有2000个txt文件，每个文件中是一例评价
import os
pos_txts = os.listdir('pos')
neg_txts = os.listdir('neg')

print( '样本总共: '+ str(len(pos_txts) + len(neg_txts)) )

# 现在我们将所有的评价内容放置到一个list里

train_texts_orig = [] # 存储所有评价，每例评价为一条string

# 添加完所有样本之后，train_texts_orig为一个含有4000条文本的list
# 其中前2000条文本为正面评价，后2000条为负面评价

for i in range(len(pos_txts)):
    with open('pos/'+pos_txts[i], 'r', errors='ignore') as f:
        text = f.read().strip()
        train_texts_orig.append(text)
for i in range(len(neg_txts)):
    with open('neg/'+neg_txts[i], 'r', errors='ignore') as f:
        text = f.read().strip()
        train_texts_orig.append(text)

len(train_texts_orig)

# 我们使用tensorflow的keras接口来建模
from tensorflow.python.keras.models import Sequential
from tensorflow.python.keras.layers import Dense, GRU, Embedding, LSTM, Bidirectional
from tensorflow.python.keras.preprocessing.text import Tokenizer
from tensorflow.python.keras.preprocessing.sequence import pad_sequences
from tensorflow.python.keras.optimizers import RMSprop
from tensorflow.python.keras.optimizers import Adam
from tensorflow.python.keras.callbacks import EarlyStopping, ModelCheckpoint, TensorBoard, ReduceLROnPlateau

# 分词和tokenize  
# 首先我们去掉每个样本的标点符号，然后用jieba分词，jieba分词返回一个生成器，没法直接进行tokenize，所以我们将分词结果转换成一个list，并将它索引化，这样每一例评价的文本变成一段索引数字，对应着预训练词向量模型中的词。

# 进行分词和tokenize
# train_tokens是一个长长的list，其中含有4000个小list，对应每一条评价
train_tokens = []
for text in train_texts_orig:
    # 去掉标点
    text = re.sub("[\s+\.\!\/_,$%^*(+\"\']+|[+——！，。？、~@#￥%……&*（）]+", "",text)
    # 结巴分词
    cut = jieba.cut(text)
    # 结巴分词的输出结果为一个生成器
    # 把生成器转换为list
    cut_list = [ i for i in cut ]
    for i, word in enumerate(cut_list):
        try:
            # 将词转换为索引index
            cut_list[i] = cn_model.vocab[word].index
        except KeyError:
            # 如果词不在字典中，则输出0
            cut_list[i] = 0
    train_tokens.append(cut_list)

# 索引长度标准化  
# 因为每段评语的长度是不一样的，我们如果单纯取最长的一个评语，并把其他评填充成同样的长度，这样十分浪费计算资源，所以我们取一个折衷的长度。

# 获得所有tokens的长度
num_tokens = [ len(tokens) for tokens in train_tokens ]
num_tokens = np.array(num_tokens)

# 平均tokens的长度
np.mean(num_tokens)

# 最长的评价tokens的长度
np.max(num_tokens)

plt.hist(np.log(num_tokens), bins = 100)
plt.xlim((0,10))
plt.ylabel('number of tokens')
plt.xlabel('length of tokens')
plt.title('Distribution of tokens length')
plt.show()

# 取tokens平均值并加上两个tokens的标准差，
# 假设tokens长度的分布为正态分布，则max_tokens这个值可以涵盖95%左右的样本
max_tokens = np.mean(num_tokens) + 2 * np.std(num_tokens)
max_tokens = int(max_tokens)
max_tokens

# 取tokens的长度为236时，大约95%的样本被涵盖
# 我们对长度不足的进行padding，超长的进行修剪
np.sum( num_tokens < max_tokens ) / len(num_tokens)

# 反向tokenize  
# 我们定义一个function，用来把索引转换成可阅读的文本，这对于debug很重要。

# 用来