#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 2023-2025 四批策略按「策略主体+变种」归类到 classify/ 下各策略族子文件夹。
依赖：四批 *_origin_explain/*策略分类总结.md 与 *_origin_explain/*.md、*_origin_py/*.py
"""

import os
import re
import csv
import shutil
from pathlib import Path
from collections import defaultdict

# 项目根目录（Selection_Strategy）
BASE = Path(__file__).resolve().parent
BATCHES = ['2023_origin_explain', '2024_1_origin_explain', '2024_2_origin_explain', '2025_origin_explain']
BATCHES_PY = ['2023_origin_py', '2024_1_origin_py', '2024_2_origin_py', '2025_origin_py']

# 策略族定义：id -> (显示名, 英文目录名)
FAMILIES = {
    '01': ('小市值与微盘股', '01_小市值与微盘股'),
    '02': ('ETF轮动', '02_ETF轮动'),
    '03': ('打板与龙头', '03_打板与龙头'),
    '04': ('基本面价值选股', '04_基本面价值选股'),
    '05': ('择时策略', '05_择时策略'),
    '06': ('技术指标与形态', '06_技术指标与形态'),
    '07': ('趋势跟踪与动量', '07_趋势跟踪与动量'),
    '08': ('机器学习与AI', '08_机器学习与AI'),
    '09': ('行业板块轮动', '09_行业板块轮动'),
    '10': ('北向资金', '10_北向资金'),
    '11': ('期货与做空', '11_期货与做空'),
    '12': ('超跌反弹', '12_超跌反弹'),
    '13': ('可转债', '13_可转债'),
    '14': ('资产配置与多策略组合', '14_资产配置与多策略组合'),
    '15': ('其他', '15_其他'),
}

# 原分类 -> 策略族 id（默认映射）
CATEGORY_TO_FAMILY = {
    '龙头/涨停板策略': '03',
    '龙头/打板策略': '03',
    '打板策略类': '03',
    'ETF轮动策略': '02',
    'ETF轮动策略类': '02',
    '基本面选股策略': '04',
    '价值投资类': '04',
    '技术指标策略': '06',
    '技术指标与形态': '06',
    '北向资金策略': '10',
    '机器学习策略': '08',
    '机器学习/AI策略类': '08',
    '股指期货策略': '11',
    '期货策略': '11',
    '期货/做空': '11',
    '趋势跟踪策略': '07',
    '趋势跟踪/动量策略': '07',
    '超跌反弹策略': '12',
    '板块轮动策略': '09',
    '行业轮动策略类': '09',
    '行业/板块轮动': '09',
    '可转债策略': '13',
    '择时策略类': '05',
    '多策略组合类': '14',
    '资产配置与多策略组合': '14',
    '资产配置策略': '14',
    '多因子策略': '04',
    '基金策略': '02',  # 基金溢价、指数增强等与ETF/轮动接近
    '其他策略': '15',
    '其他策略类': '15',
    '其他': '15',
}


def parse_summary_file(batch: str) -> list:
    """解析一个批次的策略分类总结.md，返回 [(num, name, category), ...]"""
    if batch == '2025_origin_explain':
        path = BASE / batch / '2025策略分类总结.md'
    elif batch == '2024_1_origin_explain':
        path = BASE / batch / '2024_1策略分类总结.md'
    elif batch == '2024_2_origin_explain':
        path = BASE / batch / '2024_2策略分类总结.md'
    else:
        path = BASE / batch / '2023策略分类总结.md'
    if not path.exists():
        return []
    text = path.read_text(encoding='utf-8')
    # 按 ## 分割块
    blocks = re.split(r'\n##\s+', text)
    result = []
    for block in blocks[1:]:  # 跳过文档说明
        lines = block.strip().split('\n')
        if not lines:
            continue
        # 第一行如 "一、龙头/涨停板策略 (共15套)" 或 "一、龙头/涨停板策略（15+个策略）"
        first = lines[0].strip()
        m = re.match(r'^[一二三四五六七八九十\d]+[、．.]\s*(.+?)(?:\s*[（(].*?[)）])?$', first)
        if m:
            category = m.group(1).strip()
        else:
            category = first.split('(')[0].split('（')[0].strip()
        # 找表格行：| 数字 | 策略名 | ...
        for line in lines:
            line = line.strip()
            if not line.startswith('|') or line.startswith('|------') or '策略名称' in line or '编号' in line:
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 3 and parts[1].isdigit():
                num = int(parts[1])
                name = parts[2] if len(parts) > 2 else ''
                result.append((num, name, category))
    return result


def category_to_family(category: str, name: str) -> str:
    """原分类 + 策略名 -> 策略族 id。应用「小市值」「超跌反弹」等重写规则。"""
    name_lower = (name or '').lower()
    text = (category + ' ' + (name or '')).lower()
    # 超跌反弹优先
    if '超跌反弹' in name or '超跌' in category:
        return '12'
    # 小市值/微盘/小盘/菜场大妈/股息率小市值 -> 小市值与微盘股
    if any(k in text for k in ['小市值', '微盘', '小盘股', '小盘', '菜场大妈', '股息率小市值', '国九条', '微盘400', '微盘三正', '正黄旗大妈']):
        if not any(k in (name or '') for k in ['价值投资', '价投', '大市值', '排除小市值', '无小市值因子']) and '价值投资' not in category and '价投' not in category:
            return '01'
    # 择时相关：拥挤率、情绪指数、大盘择时、微盘择时
    if any(k in text for k in ['拥挤率', '情绪指数', '择时', '大盘预测', '顶底判断']):
        if 'etf' not in text and '轮动' not in text:  # 避免把 ETF择时轮动 误判为纯择时
            return '05'
    # 桥水/全天候/多策略整合/子账户
    if any(k in text for k in ['桥水', '全天候', '多策略整合', '多策略分仓', '子账户']):
        return '14'
    # 基金溢价、EPO 优化 -> ETF/轮动相关
    if '基金溢价' in name or 'epo' in name.lower() or ('增强型投资组合' in name and 'etf' in category):
        return '02'
    fid = CATEGORY_TO_FAMILY.get(category)
    if not fid:
        for cat, f in CATEGORY_TO_FAMILY.items():
            if cat in category or category in cat:
                fid = f
                break
    return fid or '15'


def extract_num_from_filename(filename: str) -> int | None:
    """从文件名提取前导数字。如 28.正黄旗 -> 28, 6国九 -> 6"""
    base = Path(filename).stem
    m = re.match(r'^(\d+)', base)
    return int(m.group(1)) if m else None


def collect_summary_mappings():
    """从四批总结中收集 (batch, num) -> (name, category)，再映射到 family。"""
    mapping = {}   # (batch, num) -> (name, category, family)
    for batch in BATCHES:
        rows = parse_summary_file(batch)
        for num, name, category in rows:
            family = category_to_family(category, name)
            mapping[(batch, num)] = (name, category, family)
    return mapping


def list_strategy_files():
    """列出所有策略 .md 和 .py 文件（排除总结与 process_log）。"""
    files = []
    for batch in BATCHES:
        d = BASE / batch
        if not d.exists():
            continue
        for f in d.iterdir():
            if f.suffix != '.md' or '策略分类总结' in f.name or 'process_log' in f.name:
                continue
            files.append(('md', batch, f.name, d))
    for batch in BATCHES_PY:
        d = BASE / batch
        if not d.exists():
            continue
        for f in d.iterdir():
            if f.suffix != '.py' or 'process_log' in f.name:
                continue
            files.append(('py', batch, f.name, d))
    return files


def main():
    os.chdir(BASE)
    summary = collect_summary_mappings()
    files = list_strategy_files()

    # 批次名 -> 对应 explain 批次（用于查表）
    batch_for_num = {
        '2023_origin_py': '2023_origin_explain',
        '2024_1_origin_py': '2024_1_origin_explain',
        '2024_2_origin_py': '2024_2_origin_explain',
        '2025_origin_py': '2025_origin_explain',
    }

    # 为每个文件分配 family
    file_assignments = []  # (ftype, batch, fname, family, name, category)
    for ftype, batch, fname, dirpath in files:
        num = extract_num_from_filename(fname)
        lookup_batch = batch_for_num.get(batch, batch)
        key = (lookup_batch, num) if num is not None else None
        name, category, family = '', '', '15'
        if key and key in summary:
            name, category, family = summary[key]
        elif num is not None and (lookup_batch, num) in summary:
            name, category, family = summary[(lookup_batch, num)]
        file_assignments.append((ftype, batch, fname, family, name, category))

    # 写出 classification_report.csv
    out_dir = BASE / 'classify'
    out_dir.mkdir(exist_ok=True)
    report_path = out_dir / 'classification_report.csv'
    with open(report_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['ftype', 'batch', 'filename', 'family_id', 'family_name', 'strategy_name', 'original_category'])
        for ftype, batch, fname, family, name, category in file_assignments:
            fam_name = FAMILIES.get(family, ('', ''))[0]
            w.writerow([ftype, batch, fname, family, fam_name, name, category])
    print('Wrote', report_path)

    # 按 family 分组
    by_family = defaultdict(list)
    for ftype, batch, fname, family, name, category in file_assignments:
        by_family[family].append((ftype, batch, fname, name, category))

    # 创建各策略族目录并复制文件
    for fid, (fam_name, dir_name) in FAMILIES.items():
        fam_dir = out_dir / dir_name
        fam_dir.mkdir(exist_ok=True)
        for sub in BATCHES + BATCHES_PY:
            (fam_dir / sub).mkdir(exist_ok=True)
        items = by_family.get(fid, [])
        for ftype, batch, fname, name, category in items:
            src = BASE / batch / fname
            dst = fam_dir / batch / fname
            if src.exists():
                shutil.copy2(src, dst)
        print('Family', fid, fam_name, '->', len(items), 'files')

    # 为每个策略族写 README（主体方法 + 变种说明 + 文件清单）
    for fid, (fam_name, dir_name) in FAMILIES.items():
        fam_dir = out_dir / dir_name
        items = by_family.get(fid, [])
        readme_lines = [
            '# ' + fam_name,
            '',
            '## 策略主体方法',
            '',
            _get_family_description(fid),
            '',
            '## 本族策略与变种概览',
            '',
            '| 批次 | 类型 | 文件名 | 策略名/备注 |',
            '|------|------|--------|------------|',
        ]
        for ftype, batch, fname, name, category in sorted(items, key=lambda x: (x[1], x[2])):
            readme_lines.append(f'| {batch} | {ftype} | {fname} | {name or "-"} |')
        readme_lines.extend(['', '## 文件清单', ''])
        for ftype, batch, fname, _, _ in sorted(items, key=lambda x: (x[1], x[2])):
            readme_lines.append(f'- `{batch}/{fname}`')
        (fam_dir / 'README.md').write_text('\n'.join(readme_lines), encoding='utf-8')
    print('READMEs written.')
    return report_path


def _get_family_description(fid: str) -> str:
    """各策略族的主体方法说明（简短）。"""
    descs = {
        '01': '以「定期买入市值最小的一批股票并持有、再调仓」为核心。变种包括：基本面/盈利过滤、股息率、国九条与分红要求、1月4月空仓、机器学习或保形回归选股、微盘400/微盘三正、止损止盈与动态仓位等。',
        '02': '在ETF池内按动量等指标轮动持仓，强者恒强。变种包括：RSRS择时、EPO优化、波动率/相关性最小化、多品种/核心资产、盘中止损、股债平衡等。',
        '03': '围绕涨停/首板/连板/龙头进行交易。变种包括：首板低开、集合竞价、弱转强、龙虎榜、二板排板、一进二、高开低开混合等。',
        '04': '以财务、估值、股息等基本面选股（不以市值为核心结构）。变种包括：高股息、ROIC/ROE、F-Score、PEG、多因子、价值成长、CANSLIM等。',
        '05': '判断大盘或市场时机以决定是否入场或仓位。变种包括：大盘择时、RSRS、微盘扩散指数、拥挤率、情绪指数等。',
        '06': '以均线、MACD、布林、K线形态等技术分析进行交易。变种包括：均线金叉、布林突破、缠论、形态识别、海龟突破等。',
        '07': '跟踪趋势或动量因子持仓。变种包括：趋势永存、动量轮动、强弱轮动等。',
        '08': '用机器学习或AI模型做选股或择时。变种包括：随机森林、SVR、XGBoost、DQN、BiLSTM、保形回归等。',
        '09': '按行业或板块强弱轮动。变种包括：行业动量、热点概念、基金抱团等。',
        '10': '以北向资金流向选股或与择时结合。',
        '11': '期货或做空标的交易。变种包括：期指、商品CTA、融券做空等。',
        '12': '超跌后博反弹。变种包括：超跌+ROE、创新低反弹等。',
        '13': '可转债双低等轮动。',
        '14': '多资产或多策略组合、风控平衡。变种包括：全天候、多策略整合、子账户分仓等。',
        '15': '未归入以上或描述不清的策略。',
    }
    return descs.get(fid, '见总报告。')


if __name__ == '__main__':
    main()
