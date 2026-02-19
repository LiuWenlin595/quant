#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 classify/ 下每个策略族生成「变种策略汇总」文档：
- 本族策略主干思想
- 各子策略的变种要点与变种原因
"""

import re
from pathlib import Path
from collections import OrderedDict

BASE = Path(__file__).resolve().parent
CLASSIFY = BASE / 'classify'
BATCHES_EXPLAIN = ['2023_origin_explain', '2024_1_origin_explain', '2024_2_origin_explain', '2025_origin_explain']

# 策略族 id -> 主干思想（可在此扩展更完整描述）
FAMILY_CORE_IDEAS = {
    '01': '本族策略以「定期买入市值最小的一批股票并持有、再调仓」为核心逻辑：在满足基本可投资条件的前提下，按市值排序取最小若干只，按周或月调仓，赚取小盘成长与轮动溢价。',
    '02': '本族策略以「在ETF池内按动量等指标轮动持仓」为核心逻辑：在若干宽基/行业/跨境ETF中，选取近期动量最强（或结合其他指标）的标的持有，定期再选、强者恒强。',
    '03': '本族策略以「围绕涨停、首板、连板与龙头股进行短线交易」为核心逻辑：利用涨停信号、集合竞价、首板低开、弱转强、龙虎榜等捕捉情绪与资金驱动的短线机会。',
    '04': '本族策略以「基于财务、估值、股息等基本面指标选股」为核心逻辑（不以市值为核心结构）：通过ROE/ROIC、股息率、PEG、F-Score等多因子筛选优质或低估标的并持有调仓。',
    '05': '本族策略以「判断大盘或市场时机以决定是否入场或仓位」为核心逻辑：用RSRS、拥挤率、情绪指数、扩散指数等判断多空环境，控制仓位或空仓避险。',
    '06': '本族策略以「均线、MACD、布林、K线形态等技术分析作为买卖依据」为核心逻辑：通过趋势、突破、形态识别等技术信号进行中短线交易。',
    '07': '本族策略以「跟踪趋势或动量因子持仓」为核心逻辑：顺势而为，持有近期表现强势的标的，定期再平衡。',
    '08': '本族策略以「用机器学习或AI模型做选股或择时」为核心逻辑：用随机森林、SVR、XGBoost、DQN、BiLSTM、保形回归等模型生成信号并执行。',
    '09': '本族策略以「按行业或板块强弱轮动」为核心逻辑：根据行业动量、热点概念、资金抱团等选择强势行业或板块内的标的。',
    '10': '本族策略以「以北向资金流向选股或与择时结合」为核心逻辑：跟踪外资持仓或净买入变化，作为选股或仓位依据。',
    '11': '本族策略以「期货或做空标的交易」为核心逻辑：在期指、商品期货或融券等标的上执行趋势、套利或对冲。',
    '12': '本族策略以「超跌后博反弹」为核心逻辑：在价格或指标超跌时介入，博弈短期修复。',
    '13': '本族策略以「可转债双低等轮动」为核心逻辑：在可转债中按双低值等指标轮动持仓。',
    '14': '本族策略以「多资产或多策略组合、风控平衡」为核心逻辑：通过全天候、多策略整合、子账户分仓等方式分散风险、平滑收益。',
    '15': '本族为未归入以上或描述不清的策略，需结合具体文件判断主体思路。',
}

# 各策略族常见变种维度（用于「三、变种维度归纳」）
FAMILY_VARIANT_DIMENSIONS = {
    '01': ['选股过滤：纯市值 / +盈利 / +股息率 / +国九条与分红 / +成长因子 / 微盘400·三正', '调仓频率：每周 / 每月 / 每日再平衡', '择时与空仓：1月4月空仓避财报雷 / 大小盘择时 / 大盘止损', '风控：个股止损·止盈 / 涨停打开卖出 / 分散持仓'],
    '02': ['动量定义：N日收益 / 乖离率动量 / R-squared', '择时：RSRS / 北向 / MA乖离 / 盘中止损', '标的：宽基 / 行业 / 多品种 / 核心资产', '优化：EPO / 相关性最小 / 波动率过滤 / 股债平衡'],
    '03': ['介入点：首板低开 / 集合竞价 / 一进二 / 连板龙头 / 弱转强 / 龙虎榜', '卖出：11:25止盈 / 14:30清仓 / 涨停打开卖出 / 固定止损', '过滤：不追高 / 不接高位连板 / 剔除新股'],
    '04': ['因子：高股息 / ROE·ROIC / F-Score / PEG / 多因子 / CANSLIM', '持仓与调仓：月度·季度调仓 / 大市值·中等市值', '风控：分散 / 基本面筛除ST'],
    '05': ['信号来源：RSRS / 拥挤率 / 情绪指数 / 微盘扩散指数 / 大盘技术', '用途：控制仓位或空仓 / 与其他选股策略结合'],
    '06': ['指标：均线 / MACD / 布林 / 缠论 / 形态识别 / 海龟突破', '周期：日线 / 周线 / 分钟级'],
    '07': ['动量定义与标的：个股动量 / 行业动量 / 趋势强度', '调仓与持有周期'],
    '08': ['模型：随机森林 / SVR / XGBoost / DQN / BiLSTM / 保形回归', '应用：选股 / 择时 / 与小市值等规则结合'],
    '09': ['行业选择：动量 / 景气度 / 热点概念', '个股：龙一龙二龙三 / 基金抱团'],
    '10': ['北向持股比例 / 净买入 / 与ETF·择时结合'],
    '11': ['标的：期指 / 商品CTA / 融券做空', '逻辑：趋势 / 折溢价 / 对冲'],
    '12': ['超跌定义与反弹条件 / ROE等质量过滤'],
    '13': ['双低值 / 溢价率 / 轮动频率'],
    '14': ['全天候 / 多策略整合 / 子账户分仓 / 一致性风险度量'],
    '15': ['见各文件具体说明'],
}


def parse_md_sections(content: str) -> dict:
    """解析 .md 内容，按 ## 标题切分为 {标题: 正文}。"""
    sections = OrderedDict()
    current = None
    buf = []
    for line in content.split('\n'):
        if line.startswith('## '):
            if current is not None:
                sections[current] = '\n'.join(buf).strip()
            current = line.replace('## ', '').strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = '\n'.join(buf).strip()
    return sections


def clean_text(s: str, max_len: int = 220) -> str:
    """去掉多余空白与列表符，截断到 max_len 内。"""
    if not s:
        return ''
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'^\s*[\*\-]\s*', '', s)
    s = re.sub(r'^\s*\d+\.\s*', '', s)
    s = s.strip()
    if len(s) > max_len:
        s = s[:max_len].rsplit('，', 1)[0].rsplit('。', 1)[0] + '…'
    return s


def extract_variant_summary(sections: dict) -> tuple:
    """
    从 sections 中提取 变种要点、变种原因。
    返回 (变种要点, 变种原因)。
    """
    overview = ''
    core_idea = ''
    risk = ''
    for title, body in sections.items():
        if '策略概述' in title or '概述' == title.strip():
            overview = body
        elif '核心思路' in title or '核心逻辑' in title:
            core_idea = body
        elif '风险控制' in title or '风险' in title:
            risk = body

    # 变种要点：优先策略概述首段，否则用核心思路首段
    variant_point = ''
    if overview:
        first_block = overview.split('\n\n')[0] if overview else ''
        variant_point = clean_text(first_block, 220)
    if not variant_point and core_idea:
        first_block = core_idea.split('\n\n')[0]
        variant_point = clean_text(first_block, 220)
    if not variant_point:
        variant_point = '（见原文件）'

    # 变种原因：从风险控制或核心思路中找「目的/为了/避免/防止/规避/降低/提高/确保」等
    reason = ''
    for text in (risk, core_idea):
        if not text:
            continue
        for line in text.split('\n'):
            line = line.strip()
            if not line or len(line) < 10:
                continue
            if any(k in line for k in ('目的', '为了', '避免', '防止', '规避', '降低', '提高', '确保', '保证', '控制回撤', '控制风险', '躲')):
                reason = clean_text(line, 120)
                break
        if reason:
            break
    if not reason and risk:
        first_risk = risk.split('\n')[0].strip()
        reason = clean_text(first_risk, 120)
    if not reason:
        reason = '（见原文件风险控制与核心思路）'

    return variant_point, reason


def collect_md_per_family():
    """收集每个策略族下所有 .md 路径（仅 explain，排除 README 与 变种策略汇总）。"""
    by_family = {}
    for subdir in sorted(CLASSIFY.iterdir()):
        if not subdir.is_dir() or not subdir.name[0].isdigit():
            continue
        fid = subdir.name[:2] if len(subdir.name) >= 2 else subdir.name
        by_family[fid] = []
        for batch in BATCHES_EXPLAIN:
            d = subdir / batch
            if not d.exists():
                continue
            for f in sorted(d.iterdir()):
                if f.suffix != '.md' or f.name in ('README.md', '变种策略汇总.md'):
                    continue
                by_family[fid].append((batch, f.name, f))
    return by_family


def main():
    by_family = collect_md_per_family()
    for subdir in sorted(CLASSIFY.iterdir()):
        if not subdir.is_dir() or not subdir.name[:1].isdigit():
            continue
        fid = subdir.name[:2] if len(subdir.name) >= 2 else subdir.name[0]
        items = by_family.get(fid, [])
        if not items:
            continue
        fam_dir = subdir
        core_idea = FAMILY_CORE_IDEAS.get(fid, '（见本族 README。）')
        variant_dims = FAMILY_VARIANT_DIMENSIONS.get(fid, [])
        lines = [
            '# 变种策略汇总',
            '',
            '## 一、本族策略主干思想',
            '',
            core_idea,
            '',
            '## 二、变种维度归纳',
            '',
            '本族内各子策略主要在以下维度上形成变种（可对照下表查看每个策略的具体实现）：',
            '',
        ]
        for dim in variant_dims:
            lines.append('- ' + dim)
        lines.extend([
            '',
            '## 三、各子策略变种与原因',
            '',
            '| 批次 | 策略文件名 | 变种要点 | 变种原因 |',
            '|------|------------|----------|----------|',
        ])
        for batch, fname, path in sorted(items, key=lambda x: (x[0], x[1])):
            try:
                content = path.read_text(encoding='utf-8')
            except Exception:
                content = ''
            sections = parse_md_sections(content)
            variant_point, reason = extract_variant_summary(sections)
            # 表格中避免 | 破坏格式
            variant_point = variant_point.replace('|', '｜')
            reason = reason.replace('|', '｜')
            lines.append(f'| {batch} | {fname} | {variant_point} | {reason} |')
        lines.extend(['', '---', '', '*本文档由脚本根据各策略说明 .md 自动抽取生成；「变种要点」来自策略概述与核心思路，「变种原因」来自风险控制与核心思路。若为「见原文件」可打开对应 .md 查看。*'])
        out = fam_dir / '变种策略汇总.md'
        out.write_text('\n'.join(lines), encoding='utf-8')
        print('Wrote', out.relative_to(BASE), '(%d strategies)' % len(items))
    print('Done.')


if __name__ == '__main__':
    main()
