#!/usr/bin/env python3.11
"""
双色球预测工具 — CLI 入口

用法：
    python3.11 ssq_predict.py --update          # 更新数据
    python3.11 ssq_predict.py --analyze          # 分析报告
    python3.11 ssq_predict.py --predict          # 预测号码
    python3.11 ssq_predict.py --backtest         # 回测验证
    python3.11 ssq_predict.py --full             # 完整流程
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from scripts.fetch_history import (
    fetch_history,
    incremental_update,
    get_latest_code,
)
from scripts.analysis_engine import (
    load_data,
    run_full_analysis,
    load_stats,
)
from scripts.predictor import (
    generate_predictions,
    get_blue_recommendations,
    load_config,
)
from scripts.monte_carlo import (
    run_comparison,
    monte_carlo_simulation,
    print_backtest_report,
)
from scripts.money_management import (
    generate_advice,
    format_advice,
)


def ensure_data(updated: bool = False) -> bool:
    """确保数据存在，如不存在则下载
    
    Args:
        updated: 是否强制更新
    
    Returns:
        数据是否就绪
    """
    df = load_data()
    
    if df.empty or updated:
        if updated:
            print("🔄 更新数据...")
            incremental_update(verbose=True)
        else:
            print("📥 首次运行，下载历史数据...")
            fetch_history(verbose=True)
        return True
    
    return False


def format_predictions(predictions: list[dict], next_issue: str, next_date: str) -> str:
    """格式化预测输出"""
    lines = []
    lines.append("")
    lines.append("══════════════════════════════════════════════")
    lines.append(f"  🎯 双色球预测 — 第 {next_issue} 期")
    lines.append(f"  预测时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"  预计开奖: {next_date} 21:15")
    lines.append("══════════════════════════════════════════════")
    
    lines.append("")
    lines.append("  推荐号码:")
    lines.append("  ┌─────┬──────────────────────────┬──────┬─────────────────┐")
    lines.append("  │ 注  │ 红球                     │ 蓝球 │ 策略共识        │")
    lines.append("  ├─────┼──────────────────────────┼──────┼─────────────────┤")
    
    for i, pred in enumerate(predictions, 1):
        red_str = " ".join(str(x).zfill(2) for x in pred["red"])
        blue_str = str(pred["blue"]).zfill(2)
        strategies = ", ".join(pred.get("strategies", ["random_fill"])[:2])
        lines.append(f"  │ {i:<3} │ 🔴 {red_str}            │ 🔵{blue_str} │ {strategies:<15} │")
    
    lines.append("  └─────┴──────────────────────────┴──────┴─────────────────┘")
    
    return "\n".join(lines)


def format_analysis_report(stats: dict) -> str:
    """格式化分析报告"""
    lines = []
    lines.append("")
    lines.append("══════════════════════════════════════════════")
    lines.append("  📊 双色球历史数据分析报告")
    lines.append(f"  数据范围: {stats.get('date_range', 'N/A')}")
    lines.append(f"  总期数: {stats.get('total_draws', 0)}")
    lines.append("══════════════════════════════════════════════")
    
    # 频率分析
    freq = stats.get("frequency", {})
    lines.append("")
    lines.append("  🔥 热号 (全量)")
    lines.append(f"  红球: {' '.join(freq.get('hot_red', []))}")
    lines.append(f"  蓝球: {' '.join(freq.get('hot_blue', []))}")
    
    lines.append("")
    lines.append("  ❄️  冷号 (全量)")
    lines.append(f"  红球: {' '.join(freq.get('cold_red', []))}")
    lines.append(f"  蓝球: {' '.join(freq.get('cold_blue', []))}")
    
    # 近期热号
    freq_50 = stats.get("frequency_recent_50", {})
    lines.append("")
    lines.append("  🔥 近期热号 (最近50期)")
    lines.append(f"  红球: {' '.join(freq_50.get('hot_red', []))}")
    lines.append(f"  蓝球: {' '.join(freq_50.get('hot_blue', []))}")
    
    # 遗漏
    omission = stats.get("omission", {})
    high_red = omission.get("high_omission_red", [])
    high_blue = omission.get("high_omission_blue", [])
    lines.append("")
    lines.append("  ⏰ 高遗漏号码")
    if high_red:
        lines.append(f"  红球: {' '.join(high_red[:10])}")
    if high_blue:
        lines.append(f"  蓝球: {' '.join(high_blue)}")
    lines.append(f"  红球平均遗漏: {omission.get('red_avg_omission', 'N/A')} 期")
    lines.append(f"  蓝球平均遗漏: {omission.get('blue_avg_omission', 'N/A')} 期")
    
    # 区间分布
    zone = stats.get("zone", {})
    lines.append("")
    lines.append("  📐 三区分布")
    lines.append(f"  推荐三区比: {zone.get('recommended_ratio', 'N/A')}")
    for ratio_info in zone.get("common_ratios", [])[:3]:
        lines.append(f"    {ratio_info['ratio']}: {ratio_info['rate']}%")
    
    # 奇偶比
    odd_even = stats.get("odd_even", {})
    lines.append("")
    lines.append("  🔢 奇偶比")
    lines.append(f"  推荐: {odd_even.get('recommended', 'N/A')}")
    for ratio_info in odd_even.get("ratios", [])[:3]:
        lines.append(f"    {ratio_info['ratio']}: {ratio_info['rate']}%")
    
    # 和值
    sum_stats = stats.get("sum", {})
    lines.append("")
    lines.append("  📈 和值分析")
    lines.append(f"  平均值: {sum_stats.get('mean', 'N/A')}")
    lines.append(f"  中位数: {sum_stats.get('median', 'N/A')}")
    lines.append(f"  标准差: {sum_stats.get('std', 'N/A')}")
    
    # AC值
    ac = stats.get("ac_value", {})
    lines.append("")
    lines.append("  🧮 AC值 (号码复杂度)")
    lines.append(f"  平均值: {ac.get('mean', 'N/A')}")
    lines.append(f"  推荐范围: {ac.get('recommended_range', 'N/A')}")
    
    # 连号
    consec = stats.get("consecutive", {})
    lines.append("")
    lines.append("  🔗 连号分析")
    lines.append(f"  含连号概率: {consec.get('has_consecutive_rate', 'N/A')}%")
    
    # 同期
    same = stats.get("same_period", {})
    if same.get("available"):
        lines.append("")
        lines.append(f"  📅 历史同期 ({same.get('period_type', 'N/A')}, {same.get('total_draws', 0)} 期)")
        lines.append(f"  热号: {' '.join(same.get('hot_red', [])[:6])}")
        lines.append(f"  蓝球: {' '.join(same.get('hot_blue', [])[:3])}")
    
    lines.append("")
    lines.append("══════════════════════════════════════════════")
    
    return "\n".join(lines)


def format_blue_recommendations(recs: list[dict]) -> str:
    """格式化蓝球推荐"""
    lines = []
    lines.append("")
    lines.append("  🔵 蓝球推荐")
    lines.append("  ┌──────┬──────┬────────┬────────┐")
    lines.append("  │ 号码 │ 评分 │ 历史频率 │ 遗漏   │")
    lines.append("  ├──────┼──────┼────────┼────────┤")
    
    for rec in recs:
        lines.append(
            f"  │ {rec['key']}  │ {rec['score']:<4} │ {rec['rate']:<6.1f}% │ {rec['omission']:<6} │"
        )
    
    lines.append("  └──────┴──────┴────────┴────────┘")
    
    return "\n".join(lines)


def cmd_update(args):
    """更新数据"""
    ensure_data(updated=True)


def cmd_analyze(args):
    """运行分析"""
    ensure_data()
    df = load_data()
    print(f"📊 数据量: {len(df)} 期")
    
    stats = run_full_analysis(df)
    print(format_analysis_report(stats))


def cmd_predict(args):
    """预测号码"""
    ensure_data(updated=args.update)
    df = load_data()
    
    print(f"📊 加载 {len(df)} 期数据...")
    stats = run_full_analysis(df)
    
    config = load_config()
    if args.seed is not None:
        config["random_seed"] = args.seed
    
    count = args.count if args.count else config.get("generate_count", 5)
    predictions = generate_predictions(stats, config, count=count)
    
    # 获取下期期号
    latest = get_latest_code()
    # 推算下期期号
    if latest and len(latest) == 5:
        year_part = int(latest[:2])
        seq_part = int(latest[2:])
        next_seq = seq_part + 1
        if next_seq > 160:
            next_year = year_part + 1
            next_seq = 1
        else:
            next_year = year_part
        next_issue = f"{next_year:02d}{next_seq:03d}"
    else:
        next_issue = "未知"
    
    # 下期日期推算（周二四日）
    next_date = get_next_draw_date()
    
    print(format_predictions(predictions, next_issue, next_date))
    
    # 蓝球推荐
    blue_strategy = config.get("blue_ball_strategy", "cold_blue")
    blue_recs = get_blue_recommendations(stats, count=5, strategy=blue_strategy)
    print(format_blue_recommendations(blue_recs))
    
    # 购买建议
    if not args.no_advice:
        advice = generate_advice(monthly_budget=args.budget, months=1)
        print(format_advice(advice))


def cmd_backtest(args):
    """回测验证"""
    ensure_data()
    df = load_data()
    print(f"📊 数据量: {len(df)} 期")
    
    if args.monte_carlo:
        print(f"\n🎲 蒙特卡洛模拟 ({args.monte_carlo} 次)...")
        mc = monte_carlo_simulation(df, simulations=args.monte_carlo, predict_count=args.count)
        print(f"\n  模拟次数: {mc['simulations']}")
        print(f"  平均 ROI: {mc['avg_roi']:.2f}%")
        print(f"  ROI 标准差: {mc['std_roi']:.2f}%")
        print(f"  最大 ROI: {mc['max_roi']:.2f}%")
        print(f"  最小 ROI: {mc['min_roi']:.2f}%")
        print(f"  总体 ROI: {mc['roi']:.2f}%")
    else:
        print(f"\n🔄 策略回测 ({args.periods} 期, 每期 {args.count} 注)...")
        results = run_comparison(df, periods=args.periods, predict_count=args.count)
        print_backtest_report(results)


def cmd_full(args):
    """完整流程：更新 + 分析 + 预测"""
    print("📥 步骤 1/3: 更新数据")
    ensure_data(updated=True)
    
    print("\n📊 步骤 2/3: 分析数据")
    df = load_data()
    stats = run_full_analysis(df)
    print(format_analysis_report(stats))
    
    print("\n🎯 步骤 3/3: 生成预测")
    config = load_config()
    count = args.count if args.count else config.get("generate_count", 5)
    predictions = generate_predictions(stats, config, count=count)
    
    latest = get_latest_code()
    if latest and len(latest) == 5:
        year_part = int(latest[:2])
        seq_part = int(latest[2:])
        next_seq = seq_part + 1
        if next_seq > 160:
            next_year = year_part + 1
            next_seq = 1
        else:
            next_year = year_part
        next_issue = f"{next_year:02d}{next_seq:03d}"
    else:
        next_issue = "未知"
    next_date = get_next_draw_date()
    
    print(format_predictions(predictions, next_issue, next_date))
    
    blue_strategy = config.get("blue_ball_strategy", "cold_blue")
    blue_recs = get_blue_recommendations(stats, count=5, strategy=blue_strategy)
    print(format_blue_recommendations(blue_recs))
    
    if not args.no_advice:
        advice = generate_advice(monthly_budget=args.budget, months=1)
        print(format_advice(advice))


def get_next_draw_date() -> str:
    """推算下期开奖日期（周二、四、日）"""
    from datetime import datetime, timedelta
    
    today = datetime.now()
    weekday = today.weekday()  # 0=周一, 6=周日
    weekday_map = ["一", "二", "三", "四", "五", "六", "日"]
    
    # 开奖日：周二(1)、四(3)、日(6)
    draw_days = [1, 3, 6]
    
    # 找到下一个开奖日
    for day in draw_days:
        if day > weekday:
            next_draw = today + timedelta(days=day - weekday)
            wd = weekday_map[next_draw.weekday()]
            return f"{next_draw.strftime('%Y-%m-%d')} (周{wd})"
    
    # 如果本周没有，下周二的
    days_until_tuesday = (7 - weekday) + 1
    next_draw = today + timedelta(days=days_until_tuesday)
    wd = weekday_map[next_draw.weekday()]
    return f"{next_draw.strftime('%Y-%m-%d')} (周{wd})"


def main():
    parser = argparse.ArgumentParser(
        description="🎯 双色球预测工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3.11 ssq_predict.py --update          # 更新数据
  python3.11 ssq_predict.py --analyze         # 分析报告
  python3.11 ssq_predict.py --predict         # 预测 5 注
  python3.11 ssq_predict.py --predict --count 10  # 预测 10 注
  python3.11 ssq_predict.py --backtest        # 策略回测
  python3.11 ssq_predict.py --full            # 完整流程
        """
    )
    
    # 全局参数
    parser.add_argument("--update", action="store_true", help="先更新数据")
    parser.add_argument("--count", type=int, default=5, help="预测注数")
    parser.add_argument("--seed", type=int, help="随机种子")
    parser.add_argument("--budget", type=float, default=20, help="月预算（元）")
    parser.add_argument("--no-advice", action="store_true", help="不显示购买建议")
    
    # 命令
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--analyze", action="store_true", help="运行历史分析")
    group.add_argument("--predict", action="store_true", help="预测号码")
    group.add_argument("--backtest", action="store_true", help="回测验证")
    group.add_argument("--full", action="store_true", help="完整流程（更新+分析+预测）")
    
    # 回测参数
    parser.add_argument("--periods", type=int, default=100, help="回测期数")
    parser.add_argument("--monte-carlo", type=int, default=0, help="蒙特卡洛模拟次数")
    
    args = parser.parse_args()
    
    # 如果没有指定命令，默认预测
    if not any([args.analyze, args.predict, args.backtest, args.full]):
        args.predict = True
    
    try:
        if args.analyze:
            cmd_analyze(args)
        elif args.predict:
            cmd_predict(args)
        elif args.backtest:
            cmd_backtest(args)
        elif args.full:
            cmd_full(args)
        elif args.update:
            cmd_update(args)
    
    except FileNotFoundError as e:
        print(f"❌ 数据文件缺失: {e}")
        print("   请先运行: python3.11 ssq_predict.py --update")
    except Exception as e:
        print(f"❌ 执行出错: {e}")
        raise


if __name__ == "__main__":
    main()
