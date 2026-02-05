#!/usr/bin/env python
# coding: utf-8

from IPython.core.display import display, HTML

display(HTML("<style>.container { width:90% !important; }</style>"))
#display(HTML("<style>.container { height:80% !important; }</style>"))
#display(HTML("<style>.output_wrapper, .output {height:auto; max-height:800px; width:auto; max-width:1350px;}</style>"))


# <span style="color:red; font-size:32px; font-weight:bold">热点行业和热点概念-成分股-及龙一龙二龙三 </span> 

# 目的：  
# 1、单个概念找龙头  
# 2、过去N天找回流  

# <span style="color:red; font-size:18px; font-weight:bold">牛市找龙头，龙头买不进去只能选补涨，电风扇行情熊市找潜伏…… </span> 

# 库
import jqdata
from jqdata import *
import datetime as dt
import time
import warnings

import numpy as np
import seaborn as sns
program_start_dt = dt.datetime.now()

import pandas as pd
pd.options.display.float_format = '{:.2f}'.format

# 设置 Jupyter Notebook 的页面宽度
pd.set_option('display.width', 1200)        # 设置显示宽度
pd.set_option('display.max_columns', None)  # 显示所有列
pd.set_option('display.max_rows', None)


# 为了把代码迁移到聚宽回测环境中复用，
# 把全局变量定义为一个class，定义一个类和g.实例  
class a(): 
    pass
g=a()
context=a()


# <span style="color:red; font-size:32px; font-weight:bold">指定本程序的参数 </span> 

#注意检查日期，特别是跨月要修改月份
#注意检查日期，特别是跨月要修改月份

g.auc_date = get_trade_days(count=10)[-1].strftime('%Y-%m-%d')
g.end_date = get_trade_days(count=10)[-2].strftime('%Y-%m-%d')
#g.end_date = '2024-10-28' # 最后一个完整K线数据日期
#g.auc_date = '2024-10-25' # 竞价日期，
g.watch_days = 7 #看多少天的热点概念，可以看11天；但因为大盘10月8号开始大跌，到10月16日共6个交易日，看看哪些不跌
g.remove_concept_with_more_than_N_stocks = 300 #其值为Fase或一个数值，比如200
    
if True: #只是为了少占屏幕显示区
    # 将日期格式标准化为 %Y-%m-%d; 比如将 '2024-9-6' 改为 '2024-09-06'
    g.end_date = dt.datetime.strptime(g.end_date, '%Y-%m-%d').strftime('%Y-%m-%d')
    g.auc_date = dt.datetime.strptime(g.auc_date, '%Y-%m-%d').strftime('%Y-%m-%d')
    print (f'将使用下列数据进行分析：')
    print (f'1、竞价日期         {g.auc_date}')
    print (f'2、K线最后一个交易日 {g.end_date}')
    print (f'3、观察{g.watch_days}天的数据')


# # 函数群

# 获取股票名称
def get_stock_name(stock_code):
    security_info = get_security_info(stock_code)
    if security_info is not None:
        return security_info.display_name
    else:
        print (f'接收到证券代码{stock_code}，get_stock_name找不到证券名字')
        return 'Unknown'  # Return a default name if the stock code is not found


# # 行业和概念分析的代码写进了一个Python类

# 读取概念库 并 统计最热概念板块

# 分类热度统计，默认实现聚宽支持的行业分类，还有 同花顺 数据的概念分类
class Category:
    def __init__(self,industries_type='sw_l3'):
        warnings.filterwarnings('ignore')
        #g.WarningType.ShowWarning = False
        self.industries_type = industries_type
        self.industry_category = self.stock_industry(industries_type=industries_type)
        #概念库可以三选一：1同花顺概念；2同花顺行业和概念混合，也就是说把行业也当成概念；3聚宽概念库
        #同花顺的概念库比聚宽好，聚宽都没有跨境支付这个概念，而2024年10月11日跨境支付概念股票大涨
        #self.concept_category = self.stock_concepts_ths_20240831()
        self.concept_category = self.stock_concepts_and_industry_ths_20240928()
        #self.concept_category=self.stock_concepts_jq()

    #可以使用同花顺行业个概念混合而成的概念
    def stock_concepts_and_industry_ths_20240928(self, keep_concept_with_below_N_stocks=200):
        print('采用2024年12月9日同花顺行业和概念库，需每月更新一次')
        concept_stocks_file = 'cpt_ind_stocks_20240928.csv'
        concepts_file = 'cpt_ind_20240928.csv'

        # Step 1: 读取两个CSV文件
        concept_stocks = pd.read_csv(concept_stocks_file, encoding='utf-8')
        concepts = pd.read_csv(concepts_file, encoding='utf-8')

        # Step 2: 根据概念/行业代码获取对应的名称
        merged_df = concept_stocks.merge(concepts[['Unnamed: 0', 'name', 'type']], 
                                         left_on='index', right_on='Unnamed: 0', how='left')

        # 如果找不到对应的概念名或行业名，则设置为‘未知概念/行业’
        merged_df['name'].fillna('未知概念/行业', inplace=True)

        # Step 3: 修改股票代码后缀
        merged_df['stock'] = merged_df['stock'].str.replace('.SZ', '.XSHE', regex=False)
        merged_df['stock'] = merged_df['stock'].str.replace('.SH', '.XSHG', regex=False)

        # Step 4: 删除所有证券代码以8或4开头的行
        merged_df = merged_df[~merged_df['stock'].str.startswith(('8', '4', '68', '9'))]

        # Step 5: 找出type为C的概念，并统计其股票数量
        #concept_stock_counts = merged_df[merged_df['type'] == 'C']['name'].value_counts()

        # Step 6: 找出股票数量大于N的独特name概念
        #concepts_to_remove = concept_stock_counts[concept_stock_counts > keep_concept_with_below_N_stocks].index

        # Step 7: 删除这些概念对应的行
        #merged_df = merged_df[~merged_df['name'].isin(concepts_to_remove)]

        # Step 8: 构建最终的 DataFrame
        final_df = merged_df[['stock', 'name']]
        final_df.columns = ['code', 'category']  # 统一列名

        return final_df

    #可以使用同花顺概念
    def stock_concepts_ths_20240831(self, keep_concept_with_below_N_stocks=200):
        print ('采用同花顺股票概念库')
        """所有股票的同花顺概念列表"""
        # Step 1: 读取两个CSV文件
        concept_stocks_file = 'concept_stocks_20241209.csv'
        concepts_file = 'concepts_20241209.csv'

        # 读取concept_stocks和concepts数据
        concept_stocks = pd.read_csv(concept_stocks_file)
        concepts = pd.read_csv(concepts_file)

        # Step 2: 根据concept_stocks_20240831中的concept，获取concepts_20230831的concept_name
        # 如果找不到对应的概念名，则设置为‘未知概念’
        merged_df = concept_stocks.merge(concepts[['concept_thscode', 'concept_name']], 
                                         left_on='concept', right_on='concept_thscode', how='left')

        merged_df['concept_name'].fillna('未知概念', inplace=True)

        # Step 3: 修改股票代码后缀
        # SZ -> XSHE, SH -> XSHG
        merged_df['stock'] = merged_df['stock'].str.replace('.SZ', '.XSHE', regex=False)
        merged_df['stock'] = merged_df['stock'].str.replace('.SH', '.XSHG', regex=False)

        # Step 4: 统计每个概念对应的股票数量
        #concept_stock_counts = merged_df['concept_name'].value_counts()

        # Step 5: 找出股票数量大于N的概念
        #concepts_to_remove = concept_stock_counts[concept_stock_counts > keep_concept_with_below_N_stocks].index

        # Step 6: 删除这些概念对应的行
        #merged_df = merged_df[~merged_df['concept_name'].isin(concepts_to_remove)]

        # Step 7: 将合并后的数据放进df中
        df = merged_df[['stock', 'concept_name']]
        df.columns = ['code', 'category']  # 重命名列

        # 输出前几行查看数据
        df.head(10)
        return df
    
    #可以使用聚宽概念
    def stock_concepts_jq(self, keep_concept_with_below_N_stocks = 200):
        print ('采用聚宽股票概念库')
        """所有股票的聚宽概念列表"""
        q = query(jy.LC_ConceptList.ConceptCode, jy.LC_ConceptList.ConceptName)
        dict_concept = jy.run_query(q).set_index('ConceptCode')['ConceptName'].to_dict()
        stocks = jy.run_query(query(jy.SecuMain.InnerCode, jy.SecuMain.SecuCode).filter(jy.SecuMain.SecuCategory == 1,
                                                                                        jy.SecuMain.SecuMarket.in_(
                                                                                            [83, 90]),
                                                                                        jy.SecuMain.ListedState.in_(
                                                                                            [1])))
        s_code = stocks.set_index("InnerCode")['SecuCode']

        dfs = []
        min_id = 9953668143482
        while len(dfs) < 30 and min_id > 0:
            q = query(
                jy.LC_COConcept
            ).filter(jy.LC_COConcept.IndiState == 1, jy.LC_COConcept.ID < min_id).order_by(jy.LC_COConcept.ID.desc())
            df = jy.run_query(q)
            min_id = df.ID.min()
            if len(df) > 0:
                dfs.append(df)
            else:
                break
        df = pd.concat(dfs, ignore_index=True)

        sc = df.groupby('InnerCode').apply(
            lambda dx: ",".join([dict_concept[code] for code in dx.ConceptCode.unique()]))
        df_concept = pd.DataFrame({"concept": sc, 'code': s_code})
        df_concept['symbol'] = df_concept.code.map(normalize_code, na_action='ignore')
        s_concept = df_concept.dropna().set_index('symbol')['concept']
        df = pd.DataFrame(s_concept.str.split(',').tolist(), index=s_concept.index).stack()
        df = df.reset_index([0, 'symbol'])
        df.columns = ['code', 'category']

        # Step 5: 计算每个概念包含多少成分股
        #concept_stock_counts = df['category'].value_counts()

        # Step 6: 将成分股太多的概念删掉
        #concepts_to_remove = concept_stock_counts[concept_stock_counts > keep_concept_with_below_N_stocks].index
        #df = df[~df['category'].isin(concepts_to_remove)]
    
        return df


    def remove_category_with_stocks_more_than_N(self, N=300):
        """
        从 self.concept_category 中删除包含股票数量大于 N 的分类。

        :param N: 允许的最大股票数量，默认是 300。
        """
        # Step 1: 统计每个 category 中的股票数量
        category_counts = self.concept_category.groupby('category')['code'].nunique()

        # Step 2: 筛选出股票数量小于或等于 N 的分类
        valid_categories = category_counts[category_counts <= N].index

        # Step 3: 更新 self.concept_category，保留股票数量小于或等于 N 的分类行
        self.concept_category = self.concept_category[self.concept_category['category'].isin(valid_categories)]

    # 获取股票的行业代码
    def stock_industry(self,stocks_list=list(get_all_securities().index), industries_type="sw_l3"):
        stocks_industry_dict = get_industry(stocks_list)
        stocks_industry_df = pd.DataFrame(stocks_industry_dict).T[[industries_type]]
        stocks_industry_df[industries_type] = stocks_industry_df[industries_type].dropna().apply(
            lambda x: x['industry_name'])
        df_category = stocks_industry_df[[industries_type]].dropna().reset_index()
        df_category.columns = ['code', 'category']
        return df_category
    
    # 行业层级展示方法
    def industry_hierarchy(self, industries_type='sw_l3'):
        """
        展示行业的层级结构，默认为申万三级行业结构（sw_l3）。
        可以通过参数 industries_type 修改为其他层级。
        """
        # 获取股票列表
        stocks_list = list(get_all_securities().index)

        # 获取行业数据
        stocks_industry_dict = get_industry(stocks_list)
        
        # 将行业数据转换为 DataFrame
        df_industry = pd.DataFrame(stocks_industry_dict).T
        
        # 提取一级、二级和三级行业
        df_industry['一级行业'] = df_industry['sw_l1'].apply(lambda x: x['industry_name'] if pd.notna(x) else '未知')
        df_industry['二级行业'] = df_industry['sw_l2'].apply(lambda x: x['industry_name'] if pd.notna(x) else '未知')
        df_industry['三级行业'] = df_industry['sw_l3'].apply(lambda x: x['industry_name'] if pd.notna(x) else '未知')

        # 去除无效数据
        df_industry = df_industry[['一级行业', '二级行业', '三级行业']].dropna().drop_duplicates().reset_index(drop=True)

        return df_industry

    #先对个股打分：按日拉涨幅攻击超过9个点
    def score_by_return(self,stock_list=list(get_all_securities().index), return_days=1, return_filter=0.099,
                            end_dt=dt.datetime.now(), count=60, debug=False):

        """
        :param stock_list:  股票代码
        :param return_days: 收益率统计周期
        :param return_filter: 收益率阈值过滤
        :param end_date: 截止日期
        :param count: 查看的周期
        :return:
        """
        stock_list = [stock for stock in stock_list if stock[0] != '4' and stock[0] != '8' and stock[0] != '9' and stock[:2] != '68']
        close = get_price(stock_list, end_date=end_dt, count=count + return_days, fields=['close'], panel=True)[
            'close']

        if debug: 
            print(f'get_price获取{end_dt}的行情数据最后五行和最后五列(看看基于最后哪一天的数据来统计热点）：')
            print(close.iloc[-5:, -5:])

        df_return = (close / close.shift(return_days) - 1).iloc[return_days:]
        df_filter = (df_return > return_filter).astype(int)
        df_filter.index = df_return.index.strftime('%Y-%m-%d')
        return df_filter.T

    #先对个股打分：按日攻击超过9个点
    def score_by_attack(self, stock_list=list(get_all_securities().index), return_days=1, return_filter=0.099,
                        end_dt=dt.datetime.now(), count=60, debug=False):
        """
        :param stock_list: 股票代码
        :param return_days: 收益率统计周期
        :param return_filter: 收益率阈值过滤
        :param end_date: 截止日期
        :param count: 查看的周期
        :return:
        """
        stock_list = [stock for stock in stock_list if stock[0] != '4' and stock[0] != '8' and stock[0] != '9' and stock[:2] != '68']
        # 获取指定周期内的 pre_close 和 high 数据
        prices = get_price(stock_list, end_date=end_dt, count=count + return_days, fields=['pre_close', 'high'], panel=False)

        if debug:
            print(f'get_price获取{end_dt}的行情数据：')
            print(prices.head())  # 打印前几行以供调试

        # 计算是否满足攻击条件：high > (1 + return_filter) * pre_close
        prices['attack'] = (prices['high'] > (1 + return_filter) * prices['pre_close']).astype(int)

        # 格式化时间为字符串
        prices['time'] = prices['time'].dt.strftime('%Y-%m-%d')

        # 将数据透视为每只股票的