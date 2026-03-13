#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚宽一键回测脚本：打开聚宽登录页 → 用手机号+密码登录（仅一次）→ 策略列表 → 2024_2_origin文件夹
→ 对同一文件夹下多个策略依次：新建策略（各自在新窗口）→ 改名 → 注入代码 → 回测 → 保存指标。

用法:
  python run_jq_backtest.py -u 手机号 -w 密码   # 默认有头、以最小化打开，不抢前台
  python run_jq_backtest.py --headless -u 手机号 -w 密码   # 无头模式，不显示任何浏览器窗口
  python run_jq_backtest.py -u 13800138000 -w mypassword -d 策略目录 --max 5
  python run_jq_backtest.py -s 2023-09-01 -e 2026-02-22   # 指定回测起止日期
  python run_jq_backtest.py -f 单个策略.py -n "策略名"   # 单策略模式
  python run_jq_backtest.py --max-runtime 3600   # 最多运行 1 小时后强制退出进程

安装（首次，国内慢时用 -i 指定镜像）:
  pip install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple
  export PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright && playwright install
"""

import argparse
import csv
import datetime
import os
import threading
import traceback
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("请先安装: pip install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple")
    print("再下载浏览器: export PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright && playwright install")
    raise SystemExit(1)

# ===== 默认参数（可通过命令行覆盖） =====
DEFAULT_STRATEGY_DIR = Path(__file__).resolve().parent / ("Selection_Strategy/2024_2_origin_py")
DEFAULT_MAX_STRATEGIES = 200
DEFAULT_START_DATE = "2023-09-01"
DEFAULT_END_DATE = "2026-02-21"
DEFAULT_CAPITAL = "200000"
LOGIN_URL = "https://www.joinquant.com/view/user/floor?type=mainFloor"

# 收益概述中要采集的指标（顺序即 CSV 列顺序）
BACKTEST_METRIC_LABELS = [
    "策略收益", "策略年化收益", "超额收益", "基准收益", "阿尔法", "贝塔", "夏普比率",
    "胜率", "盈亏比", "最大回撤", "索提诺比率", "日均超额收益", "超额收益最大回撤",
    "超额收益夏普比率", "日胜率", "盈利次数", "亏损次数", "信息比率", "策略波动率",
    "基准波动率", "最大回撤区间",
]
BACKTEST_DURATION_COLUMN = "回测耗时"
# 点击回测后，等待「回测完成」或「回测失败」的最长时间（秒），超时则停止回测并进入下一策略
BACKTEST_WAIT_SECONDS = 10000 * 60
# 策略编辑页出现以下任一文案时视为「免费回测时间不足」提示，脚本将直接终止进程
INSUFFICIENT_BACKTEST_TIME_MARKERS = [
    "免费回测时间不足",
    "继续运行可能会消耗积分",
]
DEFAULT_RESULTS_DIR = Path(__file__).resolve().parent
# RESULTS_CSV_PREFIX = "joinquant_backtest_results"
RESULTS_CSV_PREFIX = "2024_2_origin"


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


def _normalize_date_for_key(s: str) -> str:
    """将日期字符串规范为 YYYY-MM-DD，便于与 CSV 中 2023/9/1 等格式对齐去重。"""
    if not s:
        return s
    s = s.strip().replace(" ", "")
    # 统一为 YYYY-MM-DD（补零）
    for sep in ["/", "-", "."]:
        if sep in s:
            parts = s.split(sep)
            if len(parts) == 3:
                y, m, d = parts[0].strip(), parts[1].strip(), parts[2].strip()
                try:
                    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
                except ValueError:
                    pass
            break
    return s


def _results_csv_path(results_output: Path, start_date: str, end_date: str) -> Path:
    """根据起止日期得到本轮回测结果 CSV 路径（与起止时间强绑定）。"""
    results_output = Path(results_output)
    if str(results_output).lower().endswith(".csv"):
        output_dir = results_output.parent
    else:
        output_dir = results_output
    return output_dir / f"{RESULTS_CSV_PREFIX}_{start_date}_{end_date}.csv"


def _skipped_csv_path(results_output: Path, start_date: str, end_date: str) -> Path:
    """与起止日期绑定的「未入结果表」记录 CSV（已取消/失败/超时/异常），用于去重避免反复重跑。"""
    results_output = Path(results_output)
    if str(results_output).lower().endswith(".csv"):
        output_dir = results_output.parent
    else:
        output_dir = results_output
    return output_dir / f"{RESULTS_CSV_PREFIX}_skipped_{start_date}_{end_date}.csv"


def _load_done_keys(csv_path: Path) -> set[tuple[str, str, str, str]]:
    """从已有结果 CSV 读取 (策略名称, 回测开始, 回测结束, 本金) 集合，用于去重。日期统一规范为 YYYY-MM-DD 以便与命令行参数对齐。"""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        return set()
    keys = set()
    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)  # 跳过表头
        for row in reader:
            if len(row) >= 4:
                name = row[0].strip()
                start = _normalize_date_for_key(row[1])
                end = _normalize_date_for_key(row[2])
                cap = row[3].strip()
                keys.add((name, start, end, cap))
    return keys


def _load_skipped_keys(csv_path: Path) -> set[tuple[str, str, str, str]]:
    """从「未入结果表」CSV 读取 (策略名称, 回测开始, 回测结束, 本金) 集合，与主表一起参与去重。"""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        return set()
    keys = set()
    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) >= 4:
                name = row[0].strip()
                start = _normalize_date_for_key(row[1])
                end = _normalize_date_for_key(row[2])
                cap = row[3].strip()
                keys.add((name, start, end, cap))
    return keys


def _append_skipped_row(
    csv_path: Path,
    strategy_name: str,
    start_date: str,
    end_date: str,
    capital: str,
    reason: str,
) -> None:
    """将未入结果表的一笔（已取消/失败/超时/异常）追加到 skipped CSV，无则写表头。写入失败仅打日志不抛异常。"""
    try:
        csv_path = Path(csv_path)
        header = ["策略名称", "回测开始", "回测结束", "本金", "原因"]
        row = [str(strategy_name), start_date, end_date, str(capital), str(reason)]
        file_exists = csv_path.exists()
        with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(header)
            w.writerow(row)
    except OSError as e:
        print(f"      写入未入表记录文件失败，跳过: {e}")


def _page_has_insufficient_time_dialog(page) -> bool:
    """检测当前页是否出现「免费回测时间不足，继续运行可能会消耗积分」类提示，出现则返回 True。"""
    try:
        body = page.evaluate("() => document.body.innerText || ''")
        return any(m in body for m in INSUFFICIENT_BACKTEST_TIME_MARKERS)
    except Exception:
        return False


def run(
    strategy_files: list[Path],
    start_date: str,
    end_date: str,
    capital: str,
    phone: str,
    password: str,
    results_csv: Path,
    headless: bool = False,
    max_runtime_seconds: int | None = None,
):
    # 最大运行时长：超时后强制退出进程（便于后台运行时自动收尾）
    if max_runtime_seconds is not None and max_runtime_seconds > 0:
        def _force_exit():
            print("\n已超过最大运行时长，强制退出进程。", flush=True)
            os._exit(1)

        timer = threading.Timer(float(max_runtime_seconds), _force_exit)
        timer.daemon = True
        timer.start()
        print(f"已设定最大运行时长: {max_runtime_seconds} 秒 ({max_runtime_seconds // 3600} 小时 {max_runtime_seconds % 3600 // 60} 分钟)，超时将强制退出。")

    # 若 Cursor 等环境注入了指向沙箱的浏览器路径且该路径无 arm64 浏览器，改用系统默认
    pw_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if "cursor-sandbox-cache" in pw_path or (pw_path and not Path(pw_path).exists()):
        os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)

    # 回测表格与起止时间强绑定：只读写该起止时间对应的 CSV
    results_csv = _results_csv_path(results_csv, start_date, end_date)
    skipped_csv = _skipped_csv_path(results_csv.parent, start_date, end_date)
    results_csv.parent.mkdir(parents=True, exist_ok=True)
    print(f"本轮回测结果表: {results_csv.name}")

    for f in strategy_files:
        if not f.exists():
            raise FileNotFoundError(f"策略文件不存在: {f}")

    # 双文件去重：成功记录在主表，已取消/失败/超时/异常记录在 skipped 表，两者都参与排除
    done_keys = _load_done_keys(results_csv)
    skipped_keys = _load_skipped_keys(skipped_csv)
    if done_keys:
        print(f"已从 {results_csv.name} 加载 {len(done_keys)} 条成功记录，用于去重。")
    if skipped_keys:
        print(f"已从 {skipped_csv.name} 加载 {len(skipped_keys)} 条未入表记录（已取消/失败/超时/异常），用于去重。")
    start_norm = _normalize_date_for_key(start_date)
    end_norm = _normalize_date_for_key(end_date)
    cap_str = str(capital).strip()
    to_run = [
        f for f in strategy_files
        if (_strategy_display_name(f), start_norm, end_norm, cap_str) not in done_keys
        and (_strategy_display_name(f), start_norm, end_norm, cap_str) not in skipped_keys
    ]
    skipped = len(strategy_files) - len(to_run)
    if skipped:
        print(f"已跳过 {skipped} 个在相同参数下已跑过或已记录为未入表的策略。")
    if not to_run:
        print("当前参数（起始/结束日期、本金）下所有策略均已跑过，无需重复运行。")
        return

    total = len(to_run)
    with sync_playwright() as p:
        browser = None
        try:
            print("[1/4] 启动浏览器并打开聚宽页面...")
            launch_args = ["--disable-blink-features=AutomationControlled"]
            if not headless:
                # 有窗口时以最小化启动，避免每次弹窗抢占前台、打断当前工作
                launch_args.append("--start-minimized")
            browser = p.chromium.launch(
                headless=headless,
                slow_mo=80,
                args=launch_args,
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
                    print("      本脚本将每 30 秒自动检查一次是否已登录成功，期间请勿关闭浏览器窗口，如需终止可在终端按 Ctrl+C。")
                    total_wait = 0
                    max_wait_minutes = 20
                    while True:
                        try:
                            page.get_by_text("进入策略列表").wait_for(state="visible", timeout=5000)
                            print("      检测到已登录，继续后续步骤。")
                            break
                        except PlaywrightTimeout:
                            total_wait += 30
                            if total_wait >= max_wait_minutes * 60:
                                raise PlaywrightTimeout(
                                    f"在等待验证码通过的 {max_wait_minutes} 分钟内未检测到已登录成功，请在浏览器检查登录状态后重试。"
                                )
                            print(f"      仍未检测到已登录，已等待 {total_wait} 秒，将在后台继续轮询…")
                            page.wait_for_timeout(30000)

            print("[3/4] 进入策略列表并进入「2024_2_origin」文件夹...")
            page.get_by_text("进入策略列表").click()
            page.get_by_text("新建策略").first.wait_for(state="visible", timeout=15000)
            page.get_by_text("2024_2_origin", exact=True).click()
            page.get_by_text("新建策略").first.wait_for(state="visible", timeout=10000)
            list_url = page.url
            print(f"      策略列表 URL 已记录，将依次在独立新窗口中回测 {total} 个策略。")

            # ---------- 对每个策略：新窗口内新建策略 → 回测 → 保存指标，不关浏览器 ----------
            for idx, strategy_file in enumerate(to_run, start=1):
                strategy_name = _strategy_display_name(strategy_file)
                editor_page = None
                editor_ctx = None
                used_editor_ctx = False
                editor_is_main_page = False
                is_done = False
                backtest_duration = ""
                metrics = None
                try:
                    code = strategy_file.read_text(encoding="utf-8")
                    print(f"\n[4/4] 策略 {idx}/{total}: {strategy_name}")

                    page.get_by_text("新建策略").first.click()
                    page.wait_for_timeout(800)
                    page.locator('a[href*="type=empty"]').first.wait_for(state="attached", timeout=12000)

                    editor_ctx = browser.new_context()
                    editor_window = editor_ctx.new_page()
                    editor_window.set_viewport_size({"width": 1280, "height": 800})

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
                        try:
                            page.wait_for_selector("h2.algo-title", timeout=15000)
                        except PlaywrightTimeout:
                            try:
                                page.wait_for_load_state("domcontentloaded", timeout=5000)
                                page.wait_for_selector("h2.algo-title", timeout=10000)
                            except PlaywrightTimeout:
                                editor_window.close()
                                editor_ctx.close()
                                print("      本页未在限定时间内加载出编辑器，跳过该策略。")
                                _append_skipped_row(skipped_csv, _strategy_display_name(strategy_file), start_date, end_date, capital, "未进入回测")
                                if idx < total:
                                    page.goto(list_url)
                                    page.get_by_text("新建策略").first.wait_for(state="visible", timeout=15000)
                                    page.get_by_text("2024_2_origin", exact=True).click()
                                    page.get_by_text("新建策略").first.wait_for(state="visible", timeout=10000)
                                continue
                        page.wait_for_timeout(1500)
                        editor_url = page.url
                    try:
                        editor_ctx.add_cookies(page.context.cookies())
                    except Exception:
                        pass
                    try:
                        editor_window.goto(editor_url)
                        editor_window.wait_for_selector("h2.algo-title", timeout=15000)
                        editor_page = editor_window
                        used_editor_ctx = True
                        print("      已在新窗口打开策略编辑器。")
                    except Exception as e:
                        if "ERR_INVALID_HANDLE" in str(e) or "Timeout" in type(e).__name__:
                            editor_window.close()
                            editor_ctx.close()
                            editor_page = page
                            used_editor_ctx = False
                            editor_is_main_page = True
                            print("      迁移新窗口失败，改用本页作为编辑器继续。")
                        else:
                            raise

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
    
                    editor_page.locator("h2.algo-title").click(force=True)
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

                    # 轮询：若出现「免费回测时间不足」则直接终止进程；否则等待回测完成/失败/已取消
                    timeout_ms = int(BACKTEST_WAIT_SECONDS * 1000)
                    poll_interval_ms = 3000
                    elapsed_ms = 0
                    backtest_ended = False
                    try:
                        while elapsed_ms < timeout_ms:
                            if _page_has_insufficient_time_dialog(editor_page):
                                print("\n检测到提示：您的免费回测时间不足，继续运行可能会消耗积分。脚本已终止进程。", flush=True)
                                os._exit(1)
                            try:
                                editor_page.get_by_text("回测完成").or_(editor_page.get_by_text("回测失败")).or_(editor_page.get_by_text("已取消")).first.wait_for(
                                    state="visible", timeout=poll_interval_ms
                                )
                                backtest_ended = True
                                break
                            except PlaywrightTimeout:
                                elapsed_ms += poll_interval_ms
                                continue
                        if not backtest_ended:
                            raise PlaywrightTimeout("回测等待超时")
                    except PlaywrightTimeout:
                        print("      在设定时间内未检测到「回测完成」/「回测失败」/「已取消」，可能是平台排队或算力不足，先尝试停止回测再关闭。")
                        backtest_duration = ""
                        is_done = False
                        metrics = None
                        _try_stop_backtest(editor_page)
                        _append_skipped_row(skipped_csv, strategy_name, start_date, end_date, capital, "回测超时")
                    else:
                        # 任一状态出现后等待 10 秒，再按 10 秒后页面的最终展示判断
                        print("      已出现回测完成/失败/已取消之一，等待 10 秒后按最终状态判断…")
                        editor_page.wait_for_timeout(10000)
                        status_and_duration = editor_page.evaluate(
                            """
                            () => {
                                const body = document.body.innerText || '';
                                if (body.includes('已取消')) {
                                    const m = body.match(/实际耗时\\s*[：:]?\\s*([\\d]+分[\\d]+秒)/);
                                    return { status: 'cancelled', duration: m ? m[1].trim() : '', reason: '用户或系统已取消回测' };
                                }
                                if (body.includes('回测失败')) {
                                    let reason = '';
                                    const sel = document.querySelector('.backtest-log, .log-content, .error-msg, pre, [class*="error"], [class*="log"]');
                                    if (sel && sel.innerText) reason = sel.innerText.trim().slice(0, 500);
                                    if (!reason) {
                                        const idx = body.indexOf('回测失败');
                                        if (idx >= 0) reason = body.slice(idx, idx + 400).replace(/\\s+/g, ' ').trim();
                                    }
                                    return { status: 'fail', duration: '', reason: reason || '(未抓到页面错误信息)' };
                                }
                                const m = body.match(/实际耗时\\s*[：:]?\\s*([\\d]+分[\\d]+秒)/);
                                return { status: 'done', duration: m ? m[1].trim() : '', reason: '' };
                            }
                            """
                        )
                        is_done = status_and_duration.get("status") == "done"
                        backtest_duration = status_and_duration.get("duration", "")
                        fail_reason = status_and_duration.get("reason", "")
                        status = status_and_duration.get("status", "")
                        if is_done:
                            print(f"      回测完成，耗时: {backtest_duration or '(未解析)'}")
                        elif status == "cancelled":
                            print(f"      回测已取消，耗时: {backtest_duration or '(未解析)'}，不追加到结果表。")
                            metrics = None
                            _append_skipped_row(skipped_csv, strategy_name, start_date, end_date, capital, "已取消")
                        elif status == "fail":
                            print("      回测失败。")
                            if fail_reason:
                                for line in (fail_reason[:800] + ("..." if len(fail_reason) > 800 else "")).split("\n")[:12]:
                                    if line.strip():
                                        print(f"        {line.strip()}")
                            metrics = None
                            _append_skipped_row(skipped_csv, strategy_name, start_date, end_date, capital, "回测失败")
                        else:
                            print(f"      回测状态未知 ({status!r})，记入未入表并跳过。")
                            metrics = None
                            _append_skipped_row(skipped_csv, strategy_name, start_date, end_date, capital, "未知状态")
                        editor_page.wait_for_timeout(2000)
    
                    if is_done:
                        metrics = _extract_backtest_metrics(editor_page)
                        # 胜率/盈亏比/最大回撤等可能异步晚于「回测完成」渲染，轮询直到无「正在加载」或超时（最多约 60s）
                        for poll in range(20):
                            loading = [k for k, v in (metrics or {}).items() if v and "正在加载" in str(v)]
                            if not loading:
                                break
                            if poll == 0:
                                print("      部分指标仍在加载，等待中…")
                            editor_page.wait_for_timeout(3000)
                            metrics = _extract_backtest_metrics(editor_page)
                    if metrics:
                        _append_backtest_row(
                            csv_path=results_csv,
                            strategy_name=strategy_name,
                            start_date=start_date,
                            end_date=end_date,
                            capital=capital,
                            backtest_duration=backtest_duration,
                            metrics=metrics,
                        )
                        print(f"      已追加到: {results_csv}")
                    elif not is_done:
                        pass
                    else:
                        print("      未解析到指标。")
                        _append_skipped_row(skipped_csv, strategy_name, start_date, end_date, capital, "未解析到指标")

                    if not editor_is_main_page:
                        editor_page.close()
                    if used_editor_ctx:
                        editor_ctx.close()
                    # 回到策略列表页，供下一个策略使用
                    if idx < total:
                        page.goto(list_url)
                        page.get_by_text("新建策略").first.wait_for(state="visible", timeout=15000)
                        page.get_by_text("2024_2_origin", exact=True).click()
                        page.get_by_text("新建策略").first.wait_for(state="visible", timeout=10000)
                except Exception as e:
                    print(f"      本策略异常，跳过: {e}")
                    traceback.print_exc()
                    print("      继续下一个策略。")
                    _append_skipped_row(skipped_csv, _strategy_display_name(strategy_file), start_date, end_date, capital, "异常")
                    if editor_page is not None and not editor_is_main_page:
                        try:
                            editor_page.close()
                        except Exception:
                            pass
                    if editor_ctx is not None:
                        try:
                            editor_ctx.close()
                        except Exception:
                            pass
                    if idx < total:
                        try:
                            page.goto(list_url)
                            page.get_by_text("新建策略").first.wait_for(state="visible", timeout=15000)
                            page.get_by_text("2024_2_origin", exact=True).click()
                            page.get_by_text("新建策略").first.wait_for(state="visible", timeout=10000)
                        except Exception:
                            pass

            print("\n全部策略回测结束。")
            print(f"回测参数：{start_date} ~ {end_date}，本金 ￥{capital}")
        finally:
            if browser is not None:
                browser.close()
                print("浏览器已关闭。")


def _try_stop_backtest(editor_page, wait_after_ms: int = 3000) -> None:
    """超时后点击「取消」停止回测，在确认弹窗中点击「确认」，界面会变为「已取消，实际耗时…」。"""
    # 聚宽固定：停止按钮 id=cancel-backtest-button，文案为「取 消」；点击后弹出「确实要取消?」需再点「确认」
    try:
        editor_page.locator("#cancel-backtest-button").click(timeout=4000)
        editor_page.wait_for_timeout(800)
    except (PlaywrightTimeout, Exception):
        try:
            editor_page.get_by_text("取 消").first.click(timeout=2500)
            editor_page.wait_for_timeout(800)
        except (PlaywrightTimeout, Exception):
            try:
                editor_page.get_by_text("取消").first.click(timeout=2500)
                editor_page.wait_for_timeout(800)
            except (PlaywrightTimeout, Exception):
                print("      未找到取消按钮，直接关闭页面。")
                return
    # 确认弹窗「确实要取消?」中点击「确认」
    try:
        editor_page.locator(".modal.in .modal-footer button.btn-primary").click(timeout=4000)
        editor_page.wait_for_timeout(wait_after_ms)
        print("      已取消回测并确认，关闭页面。")
    except (PlaywrightTimeout, Exception):
        editor_page.wait_for_timeout(wait_after_ms)
        print("      已点击取消，确认弹窗未找到或已关闭，关闭页面。")


def _extract_backtest_metrics(page) -> dict:
    """从当前页「收益概述」提取指标。最大回撤优先用 #max_drawdown；其他指标用 DOM 相邻取值。"""
    out = page.evaluate(
        """
        (labels) => {
            const result = {};
            for (const label of labels) result[label] = '';
            const loading = '正在加载';

            // 最大回撤：聚宽收益概述里固定 id="max_drawdown"，直接取避免与策略收益等错位
            const maxDrawdownEl = document.getElementById('max_drawdown');
            if (maxDrawdownEl) {
                const v = maxDrawdownEl.textContent.trim();
                if (v && v.indexOf(loading) < 0) result['最大回撤'] = v;
            }

            const all = document.querySelectorAll('*');
            for (const label of labels) {
                if (label === '最大回撤' && result['最大回撤']) continue;
                for (const el of all) {
                    const text = el.textContent.trim();
                    if (text !== label) continue;
                    if (el.children.length > 0) continue;
                    let valueEl = el.nextElementSibling
                        || (el.parentElement && el.parentElement.nextElementSibling)
                        || (el.closest('tr') && el.closest('tr').querySelector('td:last-child'))
                        || (el.parentElement && Array.from(el.parentElement.children).find(c => c !== el));
                    if (valueEl) {
                        const v = valueEl.textContent.trim();
                        if (v && v.indexOf(loading) < 0) result[label] = v;
                        break;
                    }
                }
            }

            const sectionTitle = '收益概述';
            const isLabelOrTitle = (s) => labels.includes(s) || s === sectionTitle;
            const looksLikeValue = (s) => s && /[\\d.%]/.test(s) && !isLabelOrTitle(s) && s.indexOf(loading) < 0;

            const panel = Array.from(document.querySelectorAll('*')).find(el =>
                el.textContent.includes('收益概述') && el.textContent.includes('策略收益')
            );
            if (panel) {
                const raw = (panel.innerText || panel.textContent).replace(/\\r\\n/g, '\\n');
                const lines = raw.split(/\\n/).map(s => s.trim()).filter(Boolean);
                for (const label of labels) {
                    if (result[label] && result[label].indexOf(loading) < 0) continue;
                    for (let i = 0; i < lines.length; i++) {
                        if (lines[i].indexOf(label) === 0 && lines[i].length > label.length) {
                            const rest = lines[i].slice(label.length).trim().replace(/^[\\s，,]+/, '');
                            if (looksLikeValue(rest)) { result[label] = rest; break; }
                        }
                        if (lines[i] === label) {
                            for (let j = i + 1; j < lines.length; j++) {
                                if (looksLikeValue(lines[j])) { result[label] = lines[j]; break; }
                                if (isLabelOrTitle(lines[j])) continue;
                            }
                            break;
                        }
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
    backtest_duration: str,
    metrics: dict,
) -> None:
    """将一行回测结果追加到 CSV（无则写表头）。"""
    csv_path = Path(csv_path)
    header = ["策略名称", "回测开始", "回测结束", "本金", BACKTEST_DURATION_COLUMN] + BACKTEST_METRIC_LABELS
    row = [str(strategy_name), start_date, end_date, str(capital), str(backtest_duration or "")] + [
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
        "-e",
        "--end",
        type=str,
        default=DEFAULT_END_DATE,
        dest="end_date",
        help="回测结束日期，如 2026-02-22，默认昨天",
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
        help="无头模式，不显示任何浏览器窗口（默认有头、以最小化打开不抢前台）",
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
        default=DEFAULT_RESULTS_DIR,
        help="回测结果目录（或旧版单文件路径），将生成 joinquant_backtest_results_开始日期_结束日期.csv",
    )
    parser.add_argument(
        "--max-runtime",
        type=int,
        default=3600*6,
        metavar="SEC",
        help="最大运行时长（秒），超时后强制退出进程；不指定则不限制。例: 3600 表示 1 小时",
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
        end_date=args.end_date,
        capital=args.capital,
        phone=args.phone,
        password=args.password,
        results_csv=args.output,
        headless=args.headless,
        max_runtime_seconds=args.max_runtime,
    )


if __name__ == "__main__":
    main()
