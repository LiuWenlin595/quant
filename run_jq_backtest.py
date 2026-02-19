#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚宽一键回测脚本：打开聚宽登录页 → 用手机号+密码登录 → 策略列表 → 自己文件夹
→ 新建策略 → 改名 → 注入代码 → 设置回测与本金 → 保存并运行回测。

用法:
  python run_jq_backtest.py -u 手机号 -w 密码
  python run_jq_backtest.py -u 13800138000 -w mypassword -f 策略.py -n "策略名"

安装（首次，国内慢时用 -i 指定镜像）:
  pip install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple
  export PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright && playwright install
"""

import argparse
import csv
import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("请先安装: pip install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple")
    print("再下载浏览器: export PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright && playwright install")
    raise SystemExit(1)

# ===== 默认参数（可通过命令行覆盖） =====
DEFAULT_STRATEGY_FILE = Path(__file__).resolve().parent / (
    "Selection_Strategy/classify/01_小市值与微盘股/2024_1_origin_py/"
    "5.尝试用机器学习批量生产小盘策略.py"
)
DEFAULT_STRATEGY_NAME = "5.尝试用机器学习批量生产小盘策略"
DEFAULT_START_DATE = "2026-02-01"
DEFAULT_CAPITAL = "500000"
LOGIN_URL = "https://www.joinquant.com/view/user/floor?type=mainFloor"

# 收益概述中要采集的指标（顺序即 CSV 列顺序）
BACKTEST_METRIC_LABELS = [
    "策略收益", "策略年化收益", "超额收益", "基准收益", "阿尔法", "贝塔", "夏普比率",
    "胜率", "盈亏比", "最大回撤", "索提诺比率", "日均超额收益", "超额收益最大回撤",
    "超额收益夏普比率", "日胜率", "盈利次数", "亏损次数", "信息比率", "策略波动率",
    "基准波动率", "最大回撤区间",
]
# 回测结果保存路径（默认与脚本同目录，可追加多轮回测）
DEFAULT_RESULTS_CSV = Path(__file__).resolve().parent / "joinquant_backtest_results.csv"


def run(
    strategy_file: Path,
    strategy_name: str,
    start_date: str,
    capital: str,
    phone: str,
    password: str,
    results_csv: Path,
    headless: bool = False,
):
    # 结束日期：昨天，避免“结束时间不能大于前一个交易日”
    end_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    if not strategy_file.exists():
        raise FileNotFoundError(f"策略文件不存在: {strategy_file}")

    code = strategy_file.read_text(encoding="utf-8")

    with sync_playwright() as p:
        print("[1/10] 启动浏览器并打开聚宽页面...")
        browser = p.chromium.launch(headless=headless, slow_mo=150)
        page = browser.new_page()
        page.goto(LOGIN_URL, wait_until="domcontentloaded")

        # 若已是登录态（直接看到进入策略列表）则跳过登录
        try:
            page.get_by_text("进入策略列表").wait_for(state="visible", timeout=5000)
            print("[2/10] 已登录，跳过登录步骤。")
        except PlaywrightTimeout:
            print("[2/10] 未登录，执行密码登录...")
            page.get_by_text("密码登录").click()
            page.wait_for_timeout(300)
            page.locator("input.pwd-phone").fill(phone)
            page.locator("input.jq-login__password").fill(password)
            # 勾选「阅读并接受聚宽用户协议及隐私政策」
            page.locator("#agreementBox").check()
            page.locator("button.btnPwdSubmit").click()
            page.get_by_text("进入策略列表").wait_for(state="visible", timeout=25000)
            print("      登录成功。")

        print("[3/10] 进入策略列表...")
        page.get_by_text("进入策略列表").click()
        print("[4/10] 进入「自己」文件夹...")
        page.get_by_text("新建策略").first.wait_for(state="visible", timeout=15000)
        page.get_by_text("自己").click()
        print("[5/10] 新建策略（空白模版）...")
        page.get_by_text("新建策略").first.wait_for(state="visible", timeout=10000)
        page.get_by_text("新建策略").first.click()
        page.get_by_text("空白模版").wait_for(state="visible", timeout=5000)

        try:
            with page.expect_popup(timeout=8000) as popup_info:
                page.get_by_text("空白模版").click()
            editor_page = popup_info.value
            print("      策略编辑器已在新标签页打开。")
        except PlaywrightTimeout:
            editor_page = page
            print("      策略编辑器在本页打开。")

        print("      关闭新建策略后的弹窗（教程/提示），避免卡住...")
        editor_page.wait_for_selector("h2.algo-title", timeout=15000)
        editor_page.wait_for_timeout(1200)  # 等待弹窗渲染
        # 弹窗1：使用 Python 语言编辑策略 → 点「跳过」
        try:
            editor_page.get_by_text("跳过").first.click(timeout=2500)
            editor_page.wait_for_timeout(400)
        except PlaywrightTimeout:
            pass
        # 弹窗2：回测时长/积分提示 → 勾选「不再提示」后点「确定」
        try:
            no_more_tip = editor_page.get_by_text("不再提示").first
            if no_more_tip.is_visible():
                no_more_tip.click(timeout=1500)
                editor_page.wait_for_timeout(200)
        except Exception:
            pass
        try:
            editor_page.get_by_role("button", name="确定").click(timeout=2500)
        except PlaywrightTimeout:
            try:
                editor_page.get_by_text("确定").first.click(timeout=2000)
            except PlaywrightTimeout:
                try:
                    editor_page.get_by_text("确 定").first.click(timeout=2000)
                except PlaywrightTimeout:
                    pass
        try:
            editor_page.get_by_role("button", name="Close").click(timeout=1500)
        except PlaywrightTimeout:
            try:
                editor_page.locator("button:has-text('Close'), .modal .close, [data-dismiss='modal']").first.click(timeout=1500)
            except Exception:
                pass
        editor_page.wait_for_timeout(400)

        print("[6/10] 设置策略名称并注入代码...")
        editor_page.locator("h2.algo-title").click()
        title_box = editor_page.locator("#title-box")
        title_box.fill(strategy_name)
        title_box.press("Enter")

        editor_page.wait_for_selector("#ide-container", timeout=10000)
        editor_page.evaluate(
            """
            (code) => {
                const el = document.getElementById('ide-container');
                if (el && typeof ace !== 'undefined') {
                    const ed = ace.edit(el);
                    ed.setValue(code);
                    ed.clearSelection();
                }
            }
            """,
            code,
        )

        editor_page.fill("#daily_backtest_capital_base_box", capital)
        editor_page.evaluate(
            """
            (function(args) {
                var s = document.getElementById('startTime');
                var e = document.getElementById('endTime');
                if (s) { s.value = args.start; s.dispatchEvent(new Event('change', { bubbles: true })); }
                if (e) { e.value = args.end; e.dispatchEvent(new Event('change', { bubbles: true })); }
            })
            """,
            {"start": start_date, "end": end_date},
        )

        print("[7/10] 设置回测参数（日期与本金）...")
        print(f"      回测区间: {start_date} ~ {end_date}, 本金: ￥{capital}")
        print("[8/10] 保存策略并运行回测...")
        editor_page.click("#algo-save-button")
        editor_page.wait_for_timeout(400)
        # 使用按钮 id 避免与页面说明文案「点击"运行回测"」冲突
        editor_page.locator("#daily-new-backtest-button").click()

        print("[9/10] 等待回测结束（最多 5 分钟）...")
        try:
            editor_page.get_by_text("回测完成", exact=True).first.wait_for(state="visible", timeout=5 * 60 * 1000)
            print("      回测完成！")
        except PlaywrightTimeout:
            print("      在设定时间内未检测到“回测完成”，请手动在页面查看状态。")

        print("[10/10] 采集收益概述指标并保存到本地表格...")
        editor_page.wait_for_timeout(2000)  # 等待数字稳定
        metrics = _extract_backtest_metrics(editor_page)
        if metrics:
            _append_backtest_row(
                csv_path=results_csv,
                strategy_name=strategy_name,
                start_date=start_date,
                end_date=end_date,
                capital=capital,
                metrics=metrics,
            )
            print(f"      已追加到: {results_csv}")
        else:
            print("      未解析到指标，请检查页面是否在「回测详情」收益概述。")

        print("回测流程结束。")
        print(f"回测参数：{start_date} ~ {end_date}，本金 ￥{capital}")
        print("按回车关闭浏览器。")
        input()
        browser.close()


def _extract_backtest_metrics(page) -> dict:
    """从当前页「收益概述」区域提取指标名→值的字典。先尝试按 DOM 取相邻值，再尝试按整块文本按行配对。"""
    out = page.evaluate(
        """
        (labels) => {
            const result = {};
            for (const label of labels) result[label] = '';

            const all = document.querySelectorAll('*');
            for (const label of labels) {
                for (const el of all) {
                    const text = el.textContent.trim();
                    if (text !== label) continue;
                    if (el.children.length > 0) continue;
                    let valueEl = el.nextElementSibling
                        || (el.parentElement && el.parentElement.nextElementSibling)
                        || (el.closest('tr') && el.closest('tr').querySelector('td:last-child'))
                        || (el.parentElement && Array.from(el.parentElement.children).find(c => c !== el));
                    if (valueEl) { result[label] = valueEl.textContent.trim(); break; }
                }
            }

            if (Object.values(result).every(v => !v)) {
                const panel = Array.from(document.querySelectorAll('*')).find(el =>
                    el.textContent.includes('收益概述') && el.textContent.includes('策略收益')
                );
                if (panel) {
                    const lines = (panel.innerText || panel.textContent).split(/\\r?\\n/).map(s => s.trim()).filter(Boolean);
                    for (let i = 0; i < lines.length - 1; i++) {
                        if (labels.includes(lines[i]) && !result[lines[i]]) result[lines[i]] = lines[i + 1];
                    }
                }
            }
            return result;
        }
        """,
        BACKTEST_METRIC_LABELS,
    )
    return out


def _append_backtest_row(
    csv_path: Path,
    strategy_name: str,
    start_date: str,
    end_date: str,
    capital: str,
    metrics: dict,
) -> None:
    """将一行回测结果追加到 CSV（无则写表头）。"""
    csv_path = Path(csv_path)
    header = ["策略名称", "回测开始", "回测结束", "本金"] + BACKTEST_METRIC_LABELS
    row = [str(strategy_name), start_date, end_date, str(capital)] + [
        metrics.get(k, "") for k in BACKTEST_METRIC_LABELS
    ]
    file_exists = csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(header)
        w.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="聚宽一键回测：用本地策略脚本在聚宽新建策略并运行回测")
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        default=DEFAULT_STRATEGY_FILE,
        help="本地策略 .py 文件路径",
    )
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        default=DEFAULT_STRATEGY_NAME,
        help="聚宽中显示的策略名称（建议带序号）",
    )
    parser.add_argument(
        "-s",
        "--start",
        type=str,
        default=DEFAULT_START_DATE,
        help="回测开始日期，如 2024-02-01",
    )
    parser.add_argument(
        "-c",
        "--capital",
        type=str,
        default=DEFAULT_CAPITAL,
        help="初始资金，如 500000",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="无头模式（不推荐，需手动登录时用有头模式）",
    )
    parser.add_argument(
        "-u",
        "--user",
        dest="phone",
        type=str,
        default="13153149814",
        help="聚宽登录手机号",
    )
    parser.add_argument(
        "-w",
        "--password",
        type=str,
        default="Taotao@988595.",
        help="聚宽登录密码",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_RESULTS_CSV,
        help="回测指标保存的 CSV 路径，默认 joinquant_backtest_results.csv",
    )
    args = parser.parse_args()

    run(
        strategy_file=args.file,
        strategy_name=args.name,
        start_date=args.start,
        capital=args.capital,
        phone=args.phone,
        password=args.password,
        results_csv=args.output,
        headless=args.headless,
    )


if __name__ == "__main__":
    main()
