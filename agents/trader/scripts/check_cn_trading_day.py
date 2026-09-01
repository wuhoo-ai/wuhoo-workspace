#!/usr/bin/env python3.11
"""A股交易日检查 — cronjob pre-exec script"""
import sys, json
sys.path.insert(0, '/home/admin/wuhoo-workspace/scripts')
from check_trading_day import check_cn_trading_day
from datetime import date
result = check_cn_trading_day(date.today())
print(json.dumps({"check_date": str(date.today()), "results": [result]}, ensure_ascii=False))
