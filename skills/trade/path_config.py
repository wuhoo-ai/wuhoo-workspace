#!/usr/bin/env python3
"""
统一路径配置 — 供 ~/wuhoo-workspace/trade/ 下各脚本引用
"""
from pathlib import Path

HOME = Path.home()

# ============== 基础路径 ==============
TRADE_DIR = HOME / 'wuhoo-agents' / 'trade'
DATA_DIR = TRADE_DIR / 'data'
ENV_FILE = HOME / '.hermes' / '.env'

# ============== Skills 路径 ==============
SKILLS_DIR = HOME / 'wuhoo-skills'
FUTU_API_SCRIPTS = SKILLS_DIR / 'futu-api' / 'scripts'
STOCK_PICK_SCRIPT = SKILLS_DIR / 'wuhoo-stock-pick' / 'stock_pick.py'
STOCK_PICK_VENV = SKILLS_DIR / 'wuhoo-stock-pick' / 'venv' / 'bin' / 'activate'

# ============== 数据路径 ==============
PICK_RESULT_DIR = HOME / '.hermes' / 'data' / 'stock-pick' / 'factors'
DAILY_DATA_DIR = HOME / '.hermes' / 'data' / 'stock-pick' / 'daily_data'

# ============== AI-Trader 路径 (待确认，保持兼容) ==============
AI_TRADER_DIR = HOME / '.hermes' / 'workspace' / 'projects' / 'AI-Trader'
AI_TRADER_AGENT_DATA = AI_TRADER_DIR / 'data' / 'agent_data' / 'trade-agent'
POSITION_FILE = AI_TRADER_AGENT_DATA / 'position' / 'position.jsonl'
LOG_DIR = AI_TRADER_AGENT_DATA / 'log'

# ============== 市场账户配置 ==============
ACCOUNT_IDS = {
    'CN': 18767295,
    'HK': 18767294,
    'US': 18767299,  # 注: 模拟盘中此 ID 可能不存在，需实际验证
}
