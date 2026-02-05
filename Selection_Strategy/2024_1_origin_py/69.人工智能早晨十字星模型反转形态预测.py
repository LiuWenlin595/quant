# 克隆自聚宽文章：https://www.joinquant.com/post/44949
# 标题：人工智能早晨十字星模型（反转形态预测）
# 作者：MarioC

from jqdata import *
from jqfactor import *
import numpy as np
import pandas as pd
import pickle
import pandas as pd
import torch
import torch.nn as nn
from tqdm import tqdm
industry_code = ['HY001', 'HY002', 'HY003', 'HY004', 'HY005', 'HY006', 'HY007', 'HY008', 'HY009', 'HY010', 'HY011']


# 初始化函数
def initialize(context):
    # 设定基准
    set_benchmark('000985.XSHG')#000037 #'000985.XSHG'
    # 用真实价格交易
    set_option('use_real_price', True)
    # 打开防未来函数
    set_option("avoid_future_data", True)
    # 将滑点设置为0
    set_slippage(FixedSlippage(0))
    # 设置交易成本万分之三，不同滑点影响可在归因分析中查看
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003,
                             close_today_commission=0, min_commission=5), type='stock')
    # 过滤order中低于error级别的日志
    log.set_level('order', 'error')
    # 初始化全局变量
    g.no_trading_today_signal = False
    g.stock_num = 3
    g.hold_list = []  # 当前持仓的全部股票
    g.yesterday_HL_list = []  # 记录持仓中昨日涨停的股票

                     






    # 设置交易运行时间
    run_daily(prepare_stock_list, '9:05')
    run_weekly(weekly_adjustment, 1, '9:30')
    # run_monthly(weekly_adjustment, 1, '9:30')
    run_daily(check_limit_up, '14:00')  # 检查持仓中的涨停股是否需要卖出
    run_daily(close_account, '14:50')


def min_max_scaling(lst):
    min_val = min(lst)
    max_val = max(lst)
    scaled_lst = [(x - min_val) / (max_val - min_val) for x in lst]
    return scaled_lst
# 1-1 准备股票池
def prepare_stock_list(context):
    # 获取已持有列表
    g.hold_list = []
    for position in list(context.portfolio.positions.values()):
        stock = position.security
        g.hold_list.append(stock)
    # 获取昨日涨停列表
    if g.hold_list != []:
        df = get_price(g.hold_list, end_date=context.previous_date, frequency='daily', fields=['close', 'high_limit'],
                       count=1, panel=False, fill_paused=False)
        df = df[df['close'] == df['high_limit']]
        g.yesterday_HL_list = list(df.code)
    else:
        g.yesterday_HL_list = []


model_path1 = r'ZCSZX_0.pt'
model_path2 = r'ZCSZX_1.pt'
model_path3 = r'ZCSZX_2.pt'

class model(nn.Module):

    def __init__(self,
                 fc1_size=2000,
                 fc2_size=1000,
                 fc3_size=100,
                 fc1_dropout=0.2,
                 fc2_dropout=0.2,
                 fc3_dropout=0.2,
                 num_of_classes=50):
        super(model, self).__init__()

        self.f_model = nn.Sequential(
            nn.Linear(2816, fc1_size),  # 887
            nn.BatchNorm1d(fc1_size),
            nn.ReLU(),
            nn.Dropout(fc1_dropout),
            nn.Linear(fc1_size, fc2_size),
            nn.BatchNorm1d(fc2_size),
            nn.ReLU(),
            nn.Dropout(fc2_dropout),
            nn.Linear(fc2_size, fc3_size),
            nn.BatchNorm1d(fc3_size),
            nn.ReLU(),
            nn.Dropout(fc3_dropout),
            nn.Linear(fc3_size, 2),

        )

        self.conv_layers1 = nn.Sequential(
            nn.Conv1d(6, 16, kernel_size=1),
            nn.BatchNorm1d(16),
            nn.Dropout(fc3_dropout),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2),
            nn.Conv1d(16, 32, kernel_size=1),
            nn.BatchNorm1d(32),
            nn.Dropout(fc3_dropout),
            nn.ReLU(),
        )

        self.conv_2D = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=2),
            nn.BatchNorm2d(16),
            nn.Dropout(fc3_dropout),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2),
            nn.Conv2d(16, 32, kernel_size=2),
            nn.BatchNorm2d(32),
            nn.Dropout(fc3_dropout),
            nn.ReLU(),
        )
        hidden_dim = 32
        self.lstm = nn.LSTM(input_size=hidden_dim, hidden_size=hidden_dim, num_layers=4, batch_first=True,
                            # dropout=fc3_dropout,
                            bidirectional=True)

        for name, module in self.named_modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_normal_(module.weight, mode='fan_in', nonlinearity='relu')
            if isinstance(module, nn.Conv2d):
                nn.init.kaiming_normal_(module.weight, mode='fan_in', nonlinearity='relu')
            if isinstance(module, nn.Conv1d):
                nn.init.kaiming_normal_(module.weight, mode='fan_in', nonlinearity='relu')

    def forward(self, x):
        min_vals, _ = torch.min(x, dim=1, keepdim=True)
        max_vals, _ = torch.max(x, dim=1, keepdim=True)
        x = (x - min_vals) / (max_vals - min_vals + 0.00001)

        xx = x.unsqueeze(1)
        xx = self.conv_2D(xx)
        xx = torch.reshape(xx, (xx.shape[0], xx.shape[1] * xx.shape[2] * xx.shape[3]))
        x = x.transpose(1, 2)
        x = self.conv_layers1(x)
        out = x.transpose(1, 2)
        out2, _ = self.lstm(out)
        out2 = torch.reshape(out2, (out2.shape[0], out2.shape[1] * out2.shape[2]))

        IN = torch.cat((xx, out2), dim=1)
        out = self.f_model(IN)
        return out
            
import io
buffer = io.BytesIO(read_file(model_path1))

model_t1 = model()
model_t1.load_state_dict(torch.load(buffer))
model_t1.eval()  # 0.54

buffer = io.BytesIO(read_file(model_path2))
model_t2 = model()
model_t2.load_state