#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辩论系统历史回测脚本

对历史数据进行回测，验证辩论系统的有效性。
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.data_aggregator import DataAggregator
from run_debate import run_full_debate


def run_backtest(
    symbol: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000
) -> dict:
    """
    运行历史回测
    
    Args:
        symbol: 股票代码
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        initial_capital: 初始资金
    
    Returns:
        回测结果
    """
    print("\n" + "="*60)
    print("📈 历史回测：{}".format(symbol))
    print("   期间：{} 至 {}".format(start_date, end_date))
    print("   初始资金：{:,} 元".format(int(initial_capital)))
    print("="*60 + "\n")
    
    # 回测状态
    state = {
        "cash": initial_capital,
        "positions": {},
        "trades": [],
        "daily_values": []
    }
    
    # 生成日期序列 (简化：实际应该获取交易日)
    dates = generate_date_range(start_date, end_date)
    
    print("回测天数：{} 天\n".format(len(dates)))
    
    # 逐日回测
    for i, date in enumerate(dates):
        print("第 {} 天：{}".format(i+1, date))
        
        # 运行辩论
        try:
            result = run_full_debate(
                symbol=symbol,
                use_real_data=False  # 简化：使用模拟数据
            )
            
            # 提取决策
            trader = result.get("trader_decision", {})
            decision = trader.get("decision", "HOLD")
            action = trader.get("action", {})
            
            print("   决策：{}".format(decision))
            
            # 执行交易 (简化)
            if decision == "BUY" and result.get("final_action") == "execute":
                # 买入逻辑 (简化)
                pass
            elif decision == "SELL":
                # 卖出逻辑 (简化)
                pass
            
            # 记录每日净值
            daily_value = calculate_portfolio_value(state, date)
            state["daily_values"].append({
                "date": date,
                "value": daily_value,
                "cash": state["cash"]
            })
            
        except Exception as e:
            print("   ❌ 错误：{}".format(e))
            continue
        
        if (i + 1) % 10 == 0:
            print("   ... 已处理 {} 天".format(i+1))
    
    # 计算回测指标
    metrics = calculate_metrics(state, initial_capital)
    
    print("\n" + "="*60)
    print("回测完成")
    print("="*60)
    print_metrics(metrics)
    
    return {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "initial_capital": initial_capital,
        "final_value": state["daily_values"][-1]["value"] if state["daily_values"] else initial_capital,
        "metrics": metrics,
        "trades": state["trades"],
        "daily_values": state["daily_values"]
    }


def generate_date_range(start_date: str, end_date: str) -> list:
    """生成日期范围"""
    dates = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    return dates


def calculate_portfolio_value(state: dict, date: str) -> float:
    """计算组合价值"""
    # 简化实现
    return state["cash"]


def calculate_metrics(state: dict, initial_capital: float) -> dict:
    """计算回测指标"""
    final_value = state["daily_values"][-1]["value"] if state["daily_values"] else initial_capital
    
    total_return = (final_value - initial_capital) / initial_capital
    
    # 简化指标
    return {
        "total_return": total_return,
        "total_return_pct": "{:.2%}".format(total_return),
        "final_value": final_value,
        "trade_count": len(state["trades"]),
        "max_drawdown": "N/A (简化版)",
        "sharpe_ratio": "N/A (简化版)",
        "win_rate": "N/A (简化版)"
    }


def print_metrics(metrics: dict):
    """打印回测指标"""
    print("\n回测指标:")
    print("   总收益率：{}".format(metrics["total_return_pct"]))
    print("   最终价值：{:,} 元".format(int(metrics["final_value"])))
    print("   交易次数：{}".format(metrics["trade_count"]))
    print("   最大回撤：{}".format(metrics["max_drawdown"]))
    print("   夏普比率：{}".format(metrics["sharpe_ratio"]))
    print("   胜率：{}".format(metrics["win_rate"]))


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="辩论系统历史回测")
    parser.add_argument("--symbol", type=str, default="600519.SH", help="股票代码")
    parser.add_argument("--start", type=str, default="2026-01-01", help="开始日期")
    parser.add_argument("--end", type=str, default="2026-03-17", help="结束日期")
    parser.add_argument("--capital", type=float, default=100000, help="初始资金")
    parser.add_argument("--output", type=str, default="backtest_result.json", help="输出文件")
    
    args = parser.parse_args()
    
    # 运行回测
    result = run_backtest(
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end,
        initial_capital=args.capital
    )
    
    # 保存结果
    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    
    print("\n✅ 回测结果已保存至：{}".format(output_path))


if __name__ == "__main__":
    main()
