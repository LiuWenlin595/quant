#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚宽一键回测脚本：打开聚宽登录页 → 用手机号+密码登录（仅一次）→ 策略列表 → 自己文件夹
→ 对同一文件夹下多个策略依次：新建策略（各自在新窗口）→ 改名 → 注入代码 → 回测 → 保存指标。

用法:
  python run_jq_backtest.py -u 手机号 -w 密码
  python run_jq_backtest.py -u 13800138000 -w mypassword -d 策略目录 --max 5
  python run_jq_backtest.py -f 单个策略.py -n "策略名"   # 单策略模式

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
DEFAULT_STRATEGY_DIR = Path(__file__).resolve().parent / (
    "Selection_Strategy/classify/01_小市值与微盘股/2024_1_origin_py"
)
DEFAULT_STRATEGY_FILE = DEFAULT_STRATEGY_DIR / "5.尝试用机器学习批量生产小盘策略.py"
DEFAULT_STRATEGY_NAME = "5.尝试用机器学习批量生产小盘策略"
DEFAULT_MAX_STRATEGIES = 10
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


def _get_strategy_files(strategy_dir: Path, max_count: int) -> list[Path]:
    """从目录中取前 max_count 个 .py 策略文件（按文件名排序）。"""
    strategy_dir = Path(strategy_dir)
    if not strategy_dir.is_dir():
        raise FileNotFoundError(f"策略目录不存在: {strategy_dir}")
    files = sorted(strategy_dir.glob("*.py"))
    return files[:max_count]


def _strategy_display_name(strategy_file: Path) -> str:
    """策略显示名称：父文件夹名/文件名（无后缀）。"""
    return f"{strategy_file.parent.name}/{strategy_file.stem}"


def _load_done_keys(csv_path: Path) -> set[tuple[str, str, str, str]]:
    """从已有结果 CSV 读取 (策略名称, 回测开始, 回测结束, 本金) 集合，用于去重。"""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        return set()
    keys = set()
    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)  # 跳过表头
        for row in reader:
            if len(row) >= 4:
                keys.add((row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()))
    return keys


def run(
    strategy_files: list[Path],
    start_date: str,
    capital: str,
    phone: str,
    password: str,
    results_csv: Path,
    headless: bool = False,
):
    import os
    # 若 Cursor 等环境注入了指向沙箱的浏览器路径且该路径无 arm64 浏览器，改用系统默认
    pw_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if "cursor-sandbox-cache" in pw_path or (pw_path and not Path(pw_path).exists()):
        os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)

    # 结束日期：昨天，避免“结束时间不能大于前一个交易日”
    end_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    for f in strategy_files:
        if not f.exists():
            raise FileNotFoundError(f"策略文件不存在: {f}")

    # 跳过已运行：起始时间、结束时间、本金、策略名称完全一致则不再重复跑
    done_keys = _load_done_keys(results_csv)
    to_run = [
        f for f in strategy_files
        if (_strategy_display_name(f), start_date, end_date, str(capital)) not in done_keys
    ]
    skipped = len(strategy_files) - len(to_run)
    if skipped:
        print(f"已跳过 {skipped} 个在相同参数下已跑过的策略。")
    if not to_run:
        print("当前参数（起始/结束日期、本金）下所有策略均已跑过，无需重复运行。")
        return

    total = len(to_run)
    with sync_playwright() as p:
        browser = None
        try:
            print("[1/4] 启动浏览器并打开聚宽页面...")
            browser = p.chromium.launch(
                headless=headless,
                slow_mo=80,
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 800})
            page.goto(LOGIN_URL, wait_until="domcontentloaded")

            # ---------- 仅执行一次登录 ----------
            try:
                page.get_by_text("进入策略列表").wait_for(state="visible", timeout=5000)
                print("[2/4] 已登录，跳过登录步骤。")
            except PlaywrightTimeout:
                print("[2/4] 未登录，执行密码登录...")
                page.get_by_text("密码登录").click()
                page.wait_for_timeout(300)
                page.locator("input.pwd-phone").fill(phone)
                page.locator("input.jq-login__password").fill(password)
                page.locator("#agreementBox").check()
                page.locator("button.btnPwdSubmit").click()
                try:
                    page.get_by_text("进入策略列表").wait_for(state="visible", timeout=12000)
                    print("      登录成功。")
                except PlaywrightTimeout:
                    print("      可能出现了滑块/验证码，请在浏览器中手动完成验证。")
                    print("      完成后回到终端按回车继续...")
                    input()
                    page.get_by_text("进入策略列表").wait_for(state="visible", timeout=60000)
                    print("      登录成功。")

            print("[3/4] 进入策略列表并进入「自己」文件夹...")
            page.get_by_text("进入策略列表").click()
            page.get_by_text("新建策略").first.wait_for(state="visible", timeout=15000)
            page.get_by_text("自己").click()
            page.get_by_text("新建策略").first.wait_for(state="visible", timeout=10000)
            list_url = page.url
            print(f"      策略列表 URL 已记录，将依次在独立新窗口中回测 {total} 个策略。")

            # ---------- 对每个策略：新窗口内新建策略 → 回测 → 保存指标，不关浏览器 ----------
            for idx, strategy_file in enumerate(to_run, start=1):
                strategy_name = _strategy_display_name(strategy_file)
                code = strategy_file.read_text(encoding="utf-8")
                print(f"\n[4/4] 策略 {idx}/{total}: {strategy_name}")

                page.get_by_text("新建策略").first.click()
                page.wait_for_timeout(800)
                page.locator('a[href*="type=empty"]').first.wait_for(state="attached", timeout=12000)

                editor_ctx = browser.new_context()
                editor_window = editor_ctx.new_page()
                editor_window.set_viewport_size({"width": 1280, "height": 800})
                used_editor_ctx = False

                try:
                    with page.expect_popup(timeout=8000) as popup_info:
                        page.evaluate("""
                            (function(){
                                var links = document.querySelectorAll('a[href*="type=empty"]');
                                if (links.length) links[links.length - 1].click();
                            })();
                        """)
                    editor_page = popup_info.value
                    editor_window.close()
                    editor_ctx.close()
                    print("      策略编辑器已在新标签页打开。")
                except PlaywrightTimeout:
                    print("      策略编辑器在本页打开，正在迁移到新窗口...")
                    page.wait_for_selector("h2.algo-title", timeout=15000)
                    page.wait_for_timeout(1500)
                    editor_url = page.url
                    try:
                        editor_ctx.add_cookies(page.context.cookies())
                    except Exception:
                        pass
                    editor_window.goto(editor_url)
                    editor_window.wait_for_selector("h2.algo-title", timeout=15000)
                    editor_page = editor_window
                    used_editor_ctx = True
                    print("      已在新窗口打开策略编辑器。")

                # 关闭新建策略后的弹窗（教程/提示）
                editor_page.wait_for_selector("h2.algo-title", timeout=15000)
                editor_page.wait_for_timeout(1800)
                try:
                    editor_page.get_by_text("跳过").first.click(timeout=2500)
                    editor_page.wait_for_timeout(900)
                except PlaywrightTimeout:
                    pass
                try:
                    no_more_tip = editor_page.get_by_text("不再提示").first
                    if no_more_tip.is_visible():
                        no_more_tip.click(timeout=1500)
                        editor_page.wait_for_timeout(500)
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
                editor_page.wait_for_timeout(800)

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

                print(f"      回测区间: {start_date} ~ {end_date}, 本金: ￥{capital}")
                editor_page.click("#algo-save-button")
                editor_page.wait_for_timeout(1200)
                editor_page.locator("#daily-new-backtest-button").click()

                try:
                    editor_page.get_by_text("回测完成", exact=True).first.wait_for(state="visible", timeout=5 * 60 * 1000)
                    print("      回测完成。")
                except PlaywrightTimeout:
                    print("      在设定时间内未检测到“回测完成”，请稍后手动查看。")

                # 先轮询直到至少一项关键指标就绪（避免「回测完成」误匹配旧 DOM 导致过早采集）
                for _ in range(24):
                    editor_page.wait_for_timeout(3000)
                    m = _extract_backtest_metrics(editor_page)
                    v = (m or {}).get("策略收益", "") or (m or {}).get("策略年化收益", "")
                    if v and "正在加载" not in str(v) and str(v).strip() not in ("", "--"):
                        break
                # 再固定等 12s 后，循环采集直到无「正在加载」或超时（最多约 75s）
                editor_page.wait_for_timeout(12000)
                metrics = _extract_backtest_metrics(editor_page)
                for _ in range(15):
                    loading = [k for k, v in (metrics or {}).items() if v and "正在加载" in str(v)]
                    if not loading:
                        break
                    editor_page.wait_for_timeout(5000)
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
                    print("      未解析到指标。")

                editor_page.close()
                if used_editor_ctx:
                    editor_ctx.close()

                # 回到策略列表页，供下一个策略使用
                if idx < total:
                    page.goto(list_url)
                    page.get_by_text("新建策略").first.wait_for(state="visible", timeout=15000)
                    page.get_by_text("自己").click()
                    page.get_by_text("新建策略").first.wait_for(state="visible", timeout=10000)

            print("\n全部策略回测结束。")
            print(f"回测参数：{start_date} ~ {end_date}，本金 ￥{capital}")
        finally:
            if browser is not None:
                browser.close()
                print("浏览器已关闭。")


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
    parser = argparse.ArgumentParser(description="聚宽一键回测：用本地策略脚本在聚宽新建策略并运行回测（多策略时同目录下多文件，各在新窗口）")
    parser.add_argument(
        "-d",
        "--dir",
        type=Path,
        default=DEFAULT_STRATEGY_DIR,
        help="策略所在目录，将按文件名排序取前 --max 个 .py 文件",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=DEFAULT_MAX_STRATEGIES,
        metavar="N",
        help=f"同一目录下最多回测的策略数量，默认 {DEFAULT_MAX_STRATEGIES}",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        default=None,
        help="单策略模式：指定单个 .py 文件（与 -n 配合使用策略名）",
    )
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        default=None,
        help="单策略模式下的策略名称（未指定则用文件名）",
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

    if args.file is not None:
        strategy_files = [Path(args.file)]
        if not strategy_files[0].exists():
            raise FileNotFoundError(f"策略文件不存在: {strategy_files[0]}")
    else:
        strategy_files = _get_strategy_files(args.dir, args.max)
        if not strategy_files:
            raise SystemExit(f"目录下未找到 .py 策略文件: {args.dir}")

    run(
        strategy_files=strategy_files,
        start_date=args.start,
        capital=args.capital,
        phone=args.phone,
        password=args.password,
        results_csv=args.output,
        headless=args.headless,
    )


if __name__ == "__main__":
    main()
