#!/usr/bin/env python3
"""
美股等权持仓策略管理

策略说明:
- 持仓范围: S&P 500 成分股（或自定义股票池）
- 权重分配: 每只股票等权重 (1/N)
- 再平衡: 每月/季度再平衡一次
- 调仓规则: 偏离目标权重 > 阈值时触发调仓

配置参数:
- rebalance_frequency: 再平衡频率 ('monthly' | 'quarterly')
- weight_threshold: 权重偏离阈值 (默认 5%)
- max_positions: 最大持仓数量 (0=全部)
- min_liquidity: 最小日均成交额过滤 (美元)
"""

import datetime
import json
import os
import pandas as pd
from pathlib import Path

# 配置
DATA_ROOT = Path(os.path.expanduser("~/wuhoo-workspace/data"))
CONFIG = {
    "strategy": "equal_weight",
    "market": "US",
    "rebalance_frequency": "monthly",  # monthly 或 quarterly
    "weight_threshold": 0.05,  # 5% 偏离阈值触发调仓
    "max_positions": 100,  # 最大持仓数 (0=全部)
    "min_liquidity": 1000000,  # 最小日均成交额 $1M
    "cash_reserve": 0.02,  # 2% 现金储备
}

def get_us_stock_list():
    """获取美股可投资股票列表"""
    stock_list_path = DATA_ROOT / "us/stock_info.csv"
    
    if not stock_list_path.exists():
        print("❌ 美股股票列表不存在，请先运行数据更新脚本")
        return []
    
    df = pd.read_csv(stock_list_path)
    symbols = df["symbol"].tolist()
    
    # 限制最大持仓数
    if CONFIG["max_positions"] > 0:
        symbols = symbols[:CONFIG["max_positions"]]
    
    print(f"✓ 美股可投资股票: {len(symbols)} 只")
    return symbols

def calculate_equal_weight(symbols):
    """计算等权权重"""
    n = len(symbols)
    if n == 0:
        return {}
    
    # 扣除现金储备后等权分配
    investable_weight = 1.0 - CONFIG["cash_reserve"]
    weight_per_stock = investable_weight / n
    
    weights = {sym: weight_per_stock for sym in symbols}
    weights["CASH"] = CONFIG["cash_reserve"]
    
    return weights

def load_current_positions(portfolio_path=None):
    """加载当前持仓"""
    if portfolio_path is None:
        portfolio_path = DATA_ROOT / "us/portfolio.json"
    
    if not portfolio_path.exists():
        print("📝 无历史持仓记录，将新建组合")
        return {}
    
    with open(portfolio_path, "r") as f:
        return json.load(f)

def save_portfolio(portfolio, path=None):
    """保存持仓配置"""
    if path is None:
        path = DATA_ROOT / "us/portfolio.json"
    
    path.parent.mkdir(parents=True, exist_ok=True)
    
    portfolio["metadata"] = {
        "strategy": CONFIG["strategy"],
        "updated_at": datetime.datetime.now().isoformat(),
        "rebalance_frequency": CONFIG["rebalance_frequency"],
        "weight_threshold": CONFIG["weight_threshold"],
        "total_positions": len([k for k in portfolio if k != "CASH"]),
    }
    
    with open(path, "w") as f:
        json.dump(portfolio, f, indent=2, ensure_ascii=False)
    
    print(f"💾 持仓已保存: {path}")

def check_rebalance_needed(portfolio):
    """检查是否需要再平衡"""
    if not portfolio or "metadata" not in portfolio:
        return True, "无历史持仓记录"
    
    last_update = datetime.datetime.fromisoformat(portfolio["metadata"]["updated_at"])
    now = datetime.datetime.now()
    
    # 检查时间间隔
    if CONFIG["rebalance_frequency"] == "monthly":
        days_since = (now - last_update).days
        if days_since >= 30:
            return True, f"距离上次再平衡已 {days_since} 天 (月度策略)"
    elif CONFIG["rebalance_frequency"] == "quarterly":
        days_since = (now - last_update).days
        if days_since >= 90:
            return True, f"距离上次再平衡已 {days_since} 天 (季度策略)"
    
    # 检查权重偏离
    if "weights" in portfolio:
        current_weights = portfolio["weights"]
        symbols = [k for k in current_weights if k != "CASH"]
        n = len(symbols)
        if n > 0:
            target_weight = (1.0 - CONFIG["cash_reserve"]) / n
            max_deviation = 0
            
            for sym, weight in current_weights.items():
                if sym == "CASH":
                    continue
                deviation = abs(weight - target_weight) / target_weight
                max_deviation = max(max_deviation, deviation)
            
            if max_deviation > CONFIG["weight_threshold"]:
                return True, f"最大权重偏离 {max_deviation:.1%} 超过阈值 {CONFIG['weight_threshold']:.1%}"
    
    return False, "无需再平衡"

def generate_rebalance_orders(target_weights, current_portfolio=None):
    """生成再平衡调仓订单"""
    if current_portfolio is None:
        current_portfolio = {"weights": {}}
    
    current_weights = current_portfolio.get("weights", {})
    all_symbols = set(list(target_weights.keys()) + list(current_weights.keys()))
    
    orders = []
    for sym in all_symbols:
        if sym == "CASH":
            continue
        
        target = target_weights.get(sym, 0)
        current = current_weights.get(sym, 0)
        diff = target - current
        
        if abs(diff) > 0.001:  # 忽略微小差异
            action = "BUY" if diff > 0 else "SELL"
            orders.append({
                "symbol": sym,
                "action": action,
                "weight_change": abs(diff),
                "target_weight": target,
                "current_weight": current,
            })
    
    # 按调整幅度排序
    orders.sort(key=lambda x: x["weight_change"], reverse=True)
    
    return orders

def run_rebalance():
    """执行再平衡"""
    print("=" * 60)
    print(f"🔄 美股等权持仓再平衡 - {datetime.datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 60)
    
    # 1. 获取股票列表
    symbols = get_us_stock_list()
    if not symbols:
        print("❌ 无可用股票列表")
        return
    
    # 2. 计算目标权重
    target_weights = calculate_equal_weight(symbols)
    print(f"📊 目标权重: 每只 {target_weights[symbols[0]]:.2%} ({len(symbols)} 只)")
    
    # 3. 加载当前持仓
    current_portfolio = load_current_positions()
    
    # 4. 检查是否需要再平衡
    needs_rebalance, reason = check_rebalance_needed(current_portfolio)
    print(f"📋 再平衡检查: {'需要' if needs_rebalance else '不需要'} - {reason}")
    
    if not needs_rebalance:
        print("✅ 当前持仓无需调整")
        return
    
    # 5. 生成调仓订单
    orders = generate_rebalance_orders(target_weights, current_portfolio)
    
    if not orders:
        print("✅ 无需调仓")
        # 更新时间戳
        current_portfolio["metadata"]["updated_at"] = datetime.datetime.now().isoformat()
        save_portfolio(current_portfolio)
        return
    
    print(f"\n📝 调仓订单 ({len(orders)} 笔):")
    print("-" * 60)
    
    buy_orders = [o for o in orders if o["action"] == "BUY"]
    sell_orders = [o for o in orders if o["action"] == "SELL"]
    
    print(f"  买入: {len(buy_orders)} 笔")
    print(f"  卖出: {len(sell_orders)} 笔")
    
    # 显示前 10 笔最大调整
    print("\n  最大调整 (前 10):")
    for order in orders[:10]:
        print(f"    {order['action']} {order['symbol']}: {order['weight_change']:.2%} "
              f"(目标 {order['target_weight']:.2%}, 当前 {order['current_weight']:.2%})")
    
    # 6. 保存新持仓
    new_portfolio = {
        "weights": target_weights,
        "orders": orders,
        "last_rebalance": datetime.datetime.now().isoformat(),
    }
    
    save_portfolio(new_portfolio)
    
    # 7. 保存调仓报告
    report_path = DATA_ROOT / "us/rebalance_report.json"
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "total_orders": len(orders),
        "buy_count": len(buy_orders),
        "sell_count": len(sell_orders),
        "reason": reason,
        "orders": orders,
    }
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 调仓报告已保存: {report_path}")
    print("=" * 60)

def show_current_portfolio():
    """显示当前持仓"""
    portfolio = load_current_positions()
    
    if not portfolio or "weights" not in portfolio:
        print("📝 当前无持仓记录")
        return
    
    weights = portfolio["weights"]
    symbols = [k for k in weights if k != "CASH"]
    
    print("=" * 60)
    print(f"📊 美股等权持仓组合")
    print("=" * 60)
    print(f"  股票数量: {len(symbols)}")
    print(f"  现金比例: {weights.get('CASH', 0):.2%}")
    print(f"  单股权重: {weights[symbols[0]]:.2%}" if symbols else "")
    
    if "metadata" in portfolio:
        print(f"  最后更新: {portfolio['metadata']['updated_at']}")
        print(f"  策略: {portfolio['metadata'].get('strategy', 'N/A')}")
    
    print("=" * 60)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="美股等权持仓策略管理")
    parser.add_argument("action", choices=["rebalance", "show", "check"], 
                        help="rebalance=执行再平衡, show=查看持仓, check=检查是否需要再平衡")
    parser.add_argument("--force", action="store_true", help="强制执行再平衡")
    args = parser.parse_args()
    
    if args.action == "rebalance":
        if args.force:
            print("⚠️ 强制执行再平衡...")
            # 临时修改检查逻辑
            symbols = get_us_stock_list()
            if symbols:
                target_weights = calculate_equal_weight(symbols)
                current_portfolio = load_current_positions()
                orders = generate_rebalance_orders(target_weights, current_portfolio)
                
                new_portfolio = {
                    "weights": target_weights,
                    "orders": orders,
                    "last_rebalance": datetime.datetime.now().isoformat(),
                }
                save_portfolio(new_portfolio)
                print(f"✅ 强制再平衡完成，共 {len(orders)} 笔调仓订单")
        else:
            run_rebalance()
    
    elif args.action == "show":
        show_current_portfolio()
    
    elif args.action == "check":
        current_portfolio = load_current_positions()
        needs_rebalance, reason = check_rebalance_needed(current_portfolio)
        status = "需要" if needs_rebalance else "不需要"
        print(f"📋 再平衡检查: {status} - {reason}")

if __name__ == "__main__":
    main()
