#!/usr/bin/env python3
"""
wuhoo-stock-deep-analysis — Workflow B 入口脚本
单股深度分析与决策建议报告

用法:
    python wuhoo_stock_deep_analysis.py --symbol 600519.SH
    python wuhoo_stock_deep_analysis.py --symbol 00700.HK --name 腾讯控股
"""
import sys
from pathlib import Path

# 添加 trade 目录到路径
trade_dir = Path(__file__).resolve().parent.parent / 'agents' / 'trade'
sys.path.insert(0, str(trade_dir))

from workflow_b_strategy_report import main

if __name__ == "__main__":
    main()
