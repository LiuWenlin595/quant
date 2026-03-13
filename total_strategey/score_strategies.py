#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客观打分标准：对 total_strategy.csv 中每条策略按加权指标计算综合分，并追加到 CSV。
"""

import csv
import re
from pathlib import Path

# 列名与索引（与 total_strategy.csv 表头一致）
HEADER = [
    "策略名称", "回测开始", "回测结束", "本金", "回测耗时",
    "策略收益", "策略年化收益", "超额收益", "基准收益",
    "阿尔法", "贝塔", "夏普比率", "胜率", "盈亏比", "最大回撤",
    "索提诺比率", "日均超额收益", "超额收益最大回撤", "超额收益夏普比率",
    "日胜率", "盈利次数", "亏损次数", "信息比率",
    "策略波动率", "基准波动率", "最大回撤区间",
]
# 新增列（含「下单时段分」：非 9:30 开盘下单得 100，9:30 下单得 0，考虑盘中/尾盘滑点更小）
SCORE_COLUMNS = [
    "综合分",
    "夏普分", "回撤分", "信息比率分", "年化分", "胜率分",
    "盈亏比分", "交易次数分", "阿尔法分", "索提诺分", "下单时段分",
    "打分细节",
]

# 权重（和为 1）。下单时段 10%：不考虑 9:30 下单，只考虑盘中或尾盘下单（滑点更低）
WEIGHTS = {
    "夏普分": 0.225,
    "回撤分": 0.18,
    "信息比率分": 0.135,
    "年化分": 0.09,
    "胜率分": 0.072,
    "盈亏比分": 0.063,
    "交易次数分": 0.045,
    "阿尔法分": 0.045,
    "索提诺分": 0.045,
    "下单时段分": 0.10,
}


def pct_to_float(s):
    """将 '12.00%' 或 '12' 转为 12.0，无效返回 None。"""
    if s is None or (isinstance(s, str) and not s.strip()):
        return None
    s = str(s).strip().replace(",", "").replace("%", "")
    try:
        return float(s)
    except ValueError:
        return None


def int_safe(s):
    if s is None or (isinstance(s, str) and not s.strip()):
        return None
    s = str(s).strip().replace(",", "")
    try:
        return int(float(s))
    except ValueError:
        return None


def score_sharpe(v):
    """夏普比率 0-100。越高越好。"""
    if v is None:
        return None
    if v <= 0:
        return 0
    if v >= 4:
        return 100
    # 0.5->25, 1->45, 1.5->65, 2->80, 2.5->90, 3->95
    if v <= 0.5:
        return 25 * (v / 0.5)
    if v <= 1:
        return 25 + 20 * (v - 0.5) / 0.5
    if v <= 1.5:
        return 45 + 20 * (v - 1) / 0.5
    if v <= 2:
        return 65 + 15 * (v - 1.5) / 0.5
    if v <= 2.5:
        return 80 + 10 * (v - 2) / 0.5
    if v <= 3:
        return 90 + 5 * (v - 2.5) / 0.5
    return 95 + 5 * min(1, (v - 3) / 1)


def score_max_drawdown(pct):
    """最大回撤(%) 0-100。越小越好。"""
    if pct is None:
        return None
    # 取绝对值，回撤一般为正数表示
    x = abs(float(pct))
    if x >= 100:
        return 0
    if x >= 60:
        return 5
    if x >= 50:
        return 15
    if x >= 40:
        return 30
    if x >= 30:
        return 45
    if x >= 25:
        return 55
    if x >= 20:
        return 65
    if x >= 15:
        return 78
    if x >= 12:
        return 88
    if x >= 10:
        return 92
    if x >= 5:
        return 97
    return 100


def score_info_ratio(v):
    """信息比率 0-100。"""
    if v is None:
        return None
    if v < 0:
        return max(0, 20 + v * 20)  # 负的给 0~20
    if v >= 2.5:
        return 100
    if v >= 2:
        return 90
    if v >= 1.5:
        return 80
    if v >= 1:
        return 65
    if v >= 0.5:
        return 45
    return 20 + 25 * (v / 0.5)


def score_annual_return(pct):
    """策略年化收益(%) 0-100。"""
    if pct is None:
        return None
    x = float(pct)
    if x < 0:
        return max(0, 15 + x / 2)  # 负收益给低分
    if x >= 200:
        return 100
    if x >= 150:
        return 90
    if x >= 100:
        return 80
    if x >= 80:
        return 70
    if x >= 50:
        return 55
    if x >= 20:
        return 35
    if x >= 0:
        return 15 + (x / 20) * 20
    return 15


def score_win_rate(v):
    """胜率 0-1。0.55-0.75 最佳，过高可能过拟合。"""
    if v is None:
        return None
    x = float(v)
    if x <= 0.4:
        return 30
    if x <= 0.45:
        return 45
    if x <= 0.5:
        return 60
    if x <= 0.55:
        return 72
    if x <= 0.6:
        return 82
    if x <= 0.65:
        return 88
    if x <= 0.7:
        return 92
    if x <= 0.75:
        return 88
    if x <= 0.8:
        return 75
    if x <= 0.85:
        return 55
    return 40


def score_profit_loss_ratio(v):
    """盈亏比 0-100。"""
    if v is None or float(v) < 0:
        return None
    x = float(v)
    if x >= 3:
        return 100
    if x >= 2.5:
        return 90
    if x >= 2:
        return 80
    if x >= 1.5:
        return 65
    if x >= 1:
        return 45
    if x >= 0.5:
        return 20
    return 0


def score_trade_count(n):
    """交易次数 = 盈利+亏损。样本越多越可信。"""
    if n is None or n < 0:
        return None
    if n >= 300:
        return 100
    if n >= 200:
        return 92
    if n >= 150:
        return 88
    if n >= 100:
        return 82
    if n >= 80:
        return 72
    if n >= 50:
        return 60
    if n >= 30:
        return 45
    if n >= 20:
        return 30
    return 20


def score_alpha(v):
    """阿尔法 0-100。"""
    if v is None:
        return None
    x = float(v)
    if x < 0:
        return max(0, 25 + x * 25)
    if x >= 0.8:
        return 100
    if x >= 0.6:
        return 85
    if x >= 0.4:
        return 70
    if x >= 0.2:
        return 50
    return 25 + 25 * (x / 0.2)


def score_sortino(v):
    """索提诺比率 0-100。"""
    if v is None:
        return None
    x = float(v)
    if x <= 0:
        return 0
    if x >= 3:
        return 100
    if x >= 2.5:
        return 92
    if x >= 2:
        return 85
    if x >= 1.5:
        return 72
    if x >= 1:
        return 55
    if x >= 0.5:
        return 30
    return 15


def is_order_at_0930(strategy_name: str, strategy_dir: Path) -> bool:
    """
    检测策略是否在 9:25～9:30 下单（开盘集中成交、滑点大）。
    若在 run_daily(..., '09:25'～'09:30' 或 "9:25"～"9:30") 中执行下单，返回 True；
    否则（盘中/尾盘下单或找不到代码）返回 False，该项给满分。
    """
    if not strategy_name or not strategy_dir or not strategy_dir.exists():
        return False
    # 策略名如 "2025_origin_py/62基金溢价（模拟效果好！）" -> Selection_Strategy/2025_origin_py/62....py
    py_path = strategy_dir / f"{strategy_name.strip()}.py"
    if not py_path.exists():
        return False
    try:
        content = py_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    # run_daily( ... '09:25'～'09:30' 或 "9:25"～"9:30"（9:25~9:30 开盘集中下单、滑点大，可能跨行）
    if re.search(r"run_daily\s*\([\s\S]*?['\"]0?9:(2[5-9]|30)['\"]", content):
        return True
    return False


def score_row(row, col_indices, strategy_name: str = "", strategy_dir: Path = None):
    """对一行计算各子分与综合分。"""
    def get(col_key):
        idx = col_indices.get(col_key)
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    def pct(col_key):
        return pct_to_float(get(col_key))

    sharpe = pct("夏普比率") if "夏普比率" in col_indices else None
    if sharpe is None:
        try:
            sharpe = float(get("夏普比率"))
        except (TypeError, ValueError):
            pass
    dd = pct("最大回撤")
    ir = None
    raw_ir = get("信息比率")
    if raw_ir is not None:
        try:
            ir = float(str(raw_ir).strip().replace(",", ""))
        except ValueError:
            pass
    annual = pct("策略年化收益")
    wr = None
    raw_wr = get("胜率")
    if raw_wr is not None:
        try:
            wr = float(str(raw_wr).strip().replace(",", ""))
        except ValueError:
            pass
    plr = None
    raw_plr = get("盈亏比")
    if raw_plr is not None:
        try:
            plr = float(str(raw_plr).strip().replace(",", ""))
        except ValueError:
            pass
    win_cnt = int_safe(get("盈利次数"))
    lose_cnt = int_safe(get("亏损次数"))
    n_trades = (win_cnt or 0) + (lose_cnt or 0) if (win_cnt is not None or lose_cnt is not None) else None
    alpha = None
    raw_alpha = get("阿尔法")
    if raw_alpha is not None:
        try:
            alpha = float(str(raw_alpha).strip().replace(",", ""))
        except ValueError:
            pass
    sortino = None
    raw_sortino = get("索提诺比率")
    if raw_sortino is not None:
        try:
            sortino = float(str(raw_sortino).strip().replace(",", ""))
        except ValueError:
            pass

    s_sharpe = score_sharpe(sharpe)
    s_dd = score_max_drawdown(dd)
    s_ir = score_info_ratio(ir)
    s_annual = score_annual_return(annual)
    s_wr = score_win_rate(wr)
    s_plr = score_profit_loss_ratio(plr)
    s_nt = score_trade_count(n_trades)
    s_alpha = score_alpha(alpha)
    s_sortino = score_sortino(sortino)
    # 下单时段：9:30 下单 0 分，盘中/尾盘或找不到代码 100 分
    s_order_time = 0 if (strategy_dir and is_order_at_0930(strategy_name, strategy_dir)) else 100

    components = {
        "夏普分": s_sharpe,
        "回撤分": s_dd,
        "信息比率分": s_ir,
        "年化分": s_annual,
        "胜率分": s_wr,
        "盈亏比分": s_plr,
        "交易次数分": s_nt,
        "阿尔法分": s_alpha,
        "索提诺分": s_sortino,
        "下单时段分": s_order_time,
    }
    # 综合分：缺失项按 0 分参与加权
    total = 0
    for k, w in WEIGHTS.items():
        val = components.get(k)
        total += (val if val is not None else 0) * w
    total = round(total, 1)
    # 打分细节：简短字符串
    detail_parts = []
    for k in ["夏普分", "回撤分", "信息比率分", "年化分", "胜率分", "盈亏比分", "交易次数分", "阿尔法分", "索提诺分", "下单时段分"]:
        v = components.get(k)
        if v is not None:
            detail_parts.append(f"{k.replace('分','')}:{int(round(v))}")
    detail_str = " ".join(detail_parts) if detail_parts else ""

    return total, components, detail_str


def main():
    base = Path(__file__).resolve().parent
    csv_path = base / "total_strategy.csv"
    out_path = base / "total_strategy.csv"
    strategy_dir = base.parent / "Selection_Strategy"

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        print("CSV 为空")
        return

    header = rows[0]
    # 找到各列索引（按表头名）
    col_indices = {}
    for i, h in enumerate(header):
        h_clean = (h or "").strip()
        if h_clean and h_clean not in col_indices:
            col_indices[h_clean] = i
    if "夏普比率" not in col_indices and len(header) > 11:
        col_indices["夏普比率"] = 11
    if "最大回撤" not in col_indices and len(header) > 14:
        col_indices["最大回撤"] = 14
    if "信息比率" not in col_indices and len(header) > 22:
        col_indices["信息比率"] = 22
    if "策略年化收益" not in col_indices and len(header) > 6:
        col_indices["策略年化收益"] = 6
    if "胜率" not in col_indices and len(header) > 12:
        col_indices["胜率"] = 12
    if "盈亏比" not in col_indices and len(header) > 13:
        col_indices["盈亏比"] = 13
    if "盈利次数" not in col_indices and len(header) > 20:
        col_indices["盈利次数"] = 20
    if "亏损次数" not in col_indices and len(header) > 21:
        col_indices["亏损次数"] = 21
    if "阿尔法" not in col_indices and len(header) > 9:
        col_indices["阿尔法"] = 9
    if "索提诺比率" not in col_indices and len(header) > 15:
        col_indices["索提诺比率"] = 15

    new_header = [h for h in header if (h or "").strip()]
    if not new_header:
        new_header = list(header[:26])
    while len(new_header) < 26:
        new_header.append("")
    new_header = new_header[:26] + SCORE_COLUMNS

    score_col_names = ["夏普分", "回撤分", "信息比率分", "年化分", "胜率分", "盈亏比分", "交易次数分", "阿尔法分", "索提诺分", "下单时段分"]

    new_rows = [new_header]
    for i, row in enumerate(rows[1:], start=1):
        r = list(row)
        while len(r) < 26:
            r.append("")
        r = r[:26]
        strategy_name = (r[0] or "").strip()
        total, components, detail_str = score_row(r, col_indices, strategy_name, strategy_dir)
        r.append(str(total))
        for col in score_col_names:
            v = components.get(col)
            r.append(str(int(round(v))) if v is not None else "")
        r.append(detail_str)
        new_rows.append(r)

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(new_rows)

    print(f"已写入 {out_path}，共 {len(new_rows)-1} 条策略")
    # 综合分列索引：26
    data_rows = [(float(new_rows[i][26]) if new_rows[i][26].strip() else 0, new_rows[i][0]) for i in range(1, len(new_rows))]
    data_rows.sort(key=lambda x: -x[0])
    print("综合分 Top10:")
    for score, name in data_rows[:10]:
        print(f"  {score:.1f}  {name[:60]}")
    # 统计 9:30 下单策略数量
    order_open_count = sum(1 for i in range(1, len(new_rows)) if new_rows[i][36].strip() == "0")
    print(f"其中 9:25～9:30 下单（下单时段分=0）策略数: {order_open_count}")


if __name__ == "__main__":
    main()
