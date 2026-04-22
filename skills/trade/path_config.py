#!/usr/bin/env python3
"""
统一路径配置 — wuhoo-workspace 唯一事实源

所有路径基于 ~/wuhoo-workspace，不再引用 wuhoo-agents 或 wuhoo-skills。
"""
from pathlib import Path

HOME = Path.home()
WORKSPACE = HOME / 'wuhoo-workspace'

# ============== 基础路径 ==============
TRADE_DIR = WORKSPACE / 'skills' / 'trade'
DATA_DIR = WORKSPACE / 'data'
ENV_FILE = HOME / '.hermes' / '.env'

# ============== Skills 路径 ==============
SKILLS_DIR = WORKSPACE / 'skills'
FUTU_API_SCRIPTS = SKILLS_DIR / 'futu-api' / 'scripts'
STOCK_PICK_SCRIPT = SKILLS_DIR / 'stock-pick' / 'stock_pick.py'
STOCK_PICK_VENV = None  # 统一使用系统 python3.11 + pip 依赖

# ============== 数据路径 ==============
PICK_RESULT_DIR = HOME / '.hermes' / 'data' / 'stock-pick' / 'factors'
DAILY_DATA_DIR = HOME / '.hermes' / 'data' / 'stock-pick' / 'daily_data'

# ============== 各市场数据路径 ==============
CN_DATA_DIR = DATA_DIR / 'cn'
HK_DATA_DIR = DATA_DIR / 'hk'
US_DATA_DIR = DATA_DIR / 'us'
US_PORTFOLIO_FILE = US_DATA_DIR / 'portfolio.json'

# ============== 等权策略路径 ==============
US_EQUAL_WEIGHT_SCRIPT = WORKSPACE / 'scripts' / 'us_equal_weight_portfolio.py'

# ============== 市场账户配置 ==============
# 模拟盘账户 (Futu SIMULATE 环境)
ACCOUNT_IDS = {
    'CN': 18767295,   # CASH, SIMULATE, CN
    'HK': 18767294,   # CASH, SIMULATE, HK
    'US': 18767293,   # MARGIN, SIMULATE, US
}
