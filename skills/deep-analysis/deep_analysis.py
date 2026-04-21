#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow B 增强版 — 单股深度分析与决策建议报告（整合 akshare 财务数据）

报告结构:
  第一部分：定性分析 — 商业模式与经济护城河
  第二部分：定量分析 — 财务健康与盈利能力
  第三部分：估值分析 — 内在价值与安全边际
  第四部分：投资决策建议 — 综合研判与交易计划

用法:
    python workflow_b_deep_analysis.py --code 600519
    python workflow_b_deep_analysis.py --code 00700 --name 腾讯控股
"""

import os
import sys
import json
import math
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================
# 环境变量加载
# ============================================================
env_file = Path.home() / '.openclaw' / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key and value and key not in os.environ:
                    os.environ[key] = value

# ============================================================
# 路径设置
# ============================================================
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR
TRADE_DIR = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'trade'
DEBATE_DIR = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'debate'
sys.path.insert(0, str(DEBATE_DIR / 'adapters'))

# ============================================================
# 数据获取模块
# ============================================================

def safe_float(val) -> Optional[float]:
    """安全转浮点数"""
    if val is None or val == '' or val == '--' or val == 'N/A':
        return None
    try:
        v = float(str(val).replace('%', '').replace(',', ''))
        return v if not math.isnan(v) and not math.isinf(v) else None
    except (ValueError, TypeError):
        return None


def safe_str(val, default='--') -> str:
    if val is None or val == '' or val == '--':
        return default
    return str(val)


class AkshareFetcher:
    """akshare 财务数据获取器（仅 A 股）"""

    def __init__(self):
        self.ak = None
        self.pd = None
        self._available = False
        try:
            import akshare as ak
            import pandas as pd
            self.ak = ak
            self.pd = pd
            self._available = True
        except ImportError:
            pass

    def is_available(self) -> bool:
        return self._available

    def fetch_all(self, code: str, name: str = '') -> Dict:
        """获取所有 akshare 数据"""
        if not self._available:
            return {"error": "akshare 未安装", "available": False}

        result = {
            "code": code,
            "name": name,
            "available": True,
            "fetch_time": datetime.now().isoformat()
        }

        # 1. 基本信息
        result["basic"] = self._get_basic(code)
        # 2. 财务指标
        result["indicators"] = self._get_indicators(code)
        # 3. 利润表
        result["income"] = self._get_income(code)
        # 4. 资产负债表
        result["balance"] = self._get_balance(code)
        # 5. 现金流
        result["cashflow"] = self._get_cashflow(code)
        # 6. 估值历史
        result["valuation_history"] = self._get_valuation_history(code)
        # 7. 股东
        result["holders"] = self._get_holders(code)
        # 8. 分红
        result["dividend"] = self._get_dividend(code)

        return result

    def _get_basic(self, code: str) -> Dict:
        try:
            df = self.ak.stock_individual_info_em(symbol=code)
            info = {}
            for _, row in df.iterrows():
                info[row['item']] = row['value']
            return {
                "name": info.get("股票简称", ""),
                "industry": info.get("行业", ""),
                "area": info.get("地区", ""),
                "market_cap": safe_float(info.get("总市值")),
                "pe_ttm": safe_float(info.get("市盈率(动态)")),
                "pb": safe_float(info.get("市净率")),
                "listing_date": info.get("上市时间", ""),
                "raw": info
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_indicators(self, code: str, limit: int = 10) -> List[Dict]:
        try:
            df = self.ak.stock_financial_abstract(symbol=code)
            if df is not None and not df.empty:
                records = df.head(limit).to_dict(orient='records')
                for r in records:
                    for k, v in r.items():
                        # 保留字符串列（"指标"、"选项"），仅转换数值列
                        if k in ('指标', '选项'):
                            r[k] = v
                        else:
                            r[k] = safe_float(v)
                return records
            return []
        except Exception:
            return []

    def _get_income(self, code: str) -> List[Dict]:
        try:
            df = self.ak.stock_profit_sheet_by_report_em(symbol=code)
            if df is not None and not df.empty:
                records = df.head(10).to_dict(orient='records')
                for r in records:
                    for k, v in r.items():
                        r[k] = safe_float(v)
                return records
            return []
        except Exception:
            return []

    def _get_balance(self, code: str) -> List[Dict]:
        try:
            df = self.ak.stock_balance_sheet_by_report_em(symbol=code)
            if df is not None and not df.empty:
                records = df.head(10).to_dict(orient='records')
                for r in records:
                    for k, v in r.items():
                        r[k] = safe_float(v)
                return records
            return []
        except Exception:
            return []

    def _get_cashflow(self, code: str) -> List[Dict]:
        try:
            df = self.ak.stock_cash_flow_sheet_by_report_em(symbol=code)
            if df is not None and not df.empty:
                records = df.head(10).to_dict(orient='records')
                for r in records:
                    for k, v in r.items():
                        r[k] = safe_float(v)
                return records
            return []
        except Exception:
            return []

    def _get_valuation_history(self, code: str) -> Dict:
        try:
            df = self.ak.stock_a_ttm_lyr(symbol=code)
            if df is None or df.empty:
                return {}
            result = {
                "history_count": len(df),
                "latest": df.iloc[-1].to_dict() if not df.empty else {}
            }
            # 计算历史分位
            for col in ['pe_ttm', 'pb', 'ps_ttm']:
                if col in df.columns:
                    series = df[col].dropna()
                    if len(series) > 0:
                        latest = series.iloc[-1]
                        result[f"{col}_latest"] = latest
                        result[f"{col}_min"] = float(series.min())
                        result[f"{col}_max"] = float(series.max())
                        result[f"{col}_median"] = float(series.median())
                        result[f"{col}_percentile"] = float((series < latest).mean() * 100)
            return result
        except Exception:
            return {}

    def _get_holders(self, code: str) -> Dict:
        result = {}
        # 前十大股东（快速，单 API 调用）
        try:
            df = self.ak.stock_gdfx_top_10_em(symbol=code)
            if df is not None and not df.empty:
                result["top_10"] = df.head(10).to_dict(orient='records')
        except Exception:
            pass
        # 注意：stock_zh_a_gdhs 逐条迭代 833 个交易日，耗时 ~28 分钟
        # 且报告生成中从未使用 holder_count_history，故已移除
        return result

    def _get_dividend(self, code: str) -> List[Dict]:
        try:
            df = self.ak.stock_history_dividend_detail(symbol=code, indicator="分红")
            if df is not None and not df.empty:
                return df.head(10).to_dict(orient='records')
            return []
        except Exception:
            # 降级尝试
            try:
                df = self.ak.stock_dividend_cninfo(symbol=code)
                if df is not None and not df.empty:
                    return df.head(10).to_dict(orient='records')
            except Exception:
                pass
            return []


class FactorDataLoader:
    """从 DataAggregator 加载因子数据"""

    def __init__(self):
        self.aggregator = None
        self._available = False
        try:
            from adapters.data_aggregator import DataAggregator
            self.aggregator = DataAggregator()
            self._available = True
        except Exception:
            pass

    def is_available(self) -> bool:
        return self._available

    def load_all(self, symbol: str, name: str = '') -> Dict:
        if not self._available:
            return {"error": "DataAggregator 不可用", "available": False}
        try:
            return self.aggregator.get_all_data(symbol, name if name else None)
        except Exception as e:
            return {"error": str(e), "available": False}


class DebateRunner:
    """多空辩论执行器"""

    def __init__(self):
        self._available = False

    def is_available(self) -> bool:
        return self._available

    def run(self, symbol: str, name: str, output_dir: Path, akshare_data: Dict = None) -> Dict:
        try:
            import sys
            debate_dir = Path.home() / "wuhoo-agents" / "debate"
            if str(debate_dir) not in sys.path:
                sys.path.insert(0, str(debate_dir))
            from run_debate import run_full_debate
            self._available = True
            result = run_full_debate(
                symbol, name,
                output_dir=str(output_dir),
                use_real_data=True
            )
            return self._normalize_full_debate(result)
        except Exception:
            return self._quick_analysis_from_akshare(akshare_data or {})

    @staticmethod
    def _normalize_full_debate(result: Dict) -> Dict:
        """将完整辩论结果扁平化为报告所需格式"""
        bull_view = result.get("bull_view", {})
        bear_view = result.get("bear_view", {})
        trader = result.get("trader_decision", {})
        risk = result.get("risk_approval", {})
        final = result.get("final_action", {})

        bull_points = bull_view.get("key_points", [])
        bear_points = bear_view.get("key_points", [])

        # 映射交易决策
        decision_map = {"BUY": "看多", "SELL": "看空", "HOLD": "中性"}
        rec = decision_map.get(trader.get("decision", "HOLD"), "中性")
        conf = round(trader.get("confidence", 0.5) * 100)

        return {
            "method": "full",
            "bull_points": bull_points,
            "bear_points": bear_points,
            "recommendation": rec,
            "confidence": conf,
            "trader_decision": trader.get("decision", "HOLD"),
            "risk_approved": risk.get("approved", False),
            "final_action": final.get("action", "hold"),
            "final_reason": final.get("reason", ""),
            "consensus": result.get("consensus_points", []),
            "disagreements": result.get("disagreement_points", []),
            "stop_loss": bull_view.get("stop_loss", 0),
            "take_profit": bull_view.get("target_price", 0),
            "position_suggestion": bull_view.get("position_suggestion", 0),
        }

    def _quick_analysis_from_akshare(self, akshare_data: Dict) -> Dict:
        """从 akshare 数据提取基础指标进行简化分析"""
        basic = akshare_data.get("basic", {})
        indicators = akshare_data.get("indicators", [])
        pe = safe_float(basic.get("pe_ttm", 0))
        market_cap = safe_float(basic.get("market_cap", 0))

        # 从 indicators 提取最新 ROE
        roe = 0.0
        if indicators:
            for row in indicators:
                if row.get("指标") == "加权净资产收益率(%)":
                    # 取最新年度数据
                    dates = [k for k in row if k not in ("指标", "选项")]
                    if dates:
                        roe = safe_float(row[dates[-1]]) / 100  # 百分比转小数
                    break

        # 如果 PE 为空，用市值/净利润估算
        if not pe and market_cap > 0 and indicators:
            for row in indicators:
                if row.get("指标") == "归母净利润":
                    dates = [k for k in row if k not in ("指标", "选项")]
                    if dates:
                        net_profit = safe_float(row[dates[-1]])
                        if net_profit > 0:
                            pe = market_cap / net_profit
                    break

        return self._quick_analysis(
            {"pe": pe, "roe": roe},
            {"rsi": 50, "trend": "sideways"},
            {}
        )

    def _quick_analysis(self, fundamental: Dict, technical: Dict, sentiment: Dict) -> Dict:
        pe = safe_float(fundamental.get('pe', 0))
        roe = safe_float(fundamental.get('roe', 0))
        rsi = safe_float(technical.get('rsi', 50))
        trend = technical.get('trend', 'sideways')

        bull_points = []
        bear_points = []

        if pe and 0 < pe < 20:
            bull_points.append(f"市盈率 {pe:.1f}x，估值合理")
        elif pe and pe > 40:
            bear_points.append(f"市盈率 {pe:.1f}x，估值偏高")
        if roe and roe > 0.15:
            bull_points.append(f"ROE {roe:.1%}，盈利能力强")
        elif roe and roe < 0.05:
            bear_points.append(f"ROE {roe:.1%}，盈利能力弱")
        if trend == 'uptrend':
            bull_points.append("技术面处于上升趋势")
        elif trend == 'downtrend':
            bear_points.append("技术面处于下降趋势")
        if rsi and rsi < 30:
            bull_points.append(f"RSI {rsi:.1f}，超卖反弹机会")
        elif rsi and rsi > 70:
            bear_points.append(f"RSI {rsi:.1f}，超买回调风险")

        bull_score = len(bull_points)
        bear_score = len(bear_points)
        if bull_score > bear_score:
            rec = "看多"
        elif bear_score > bull_score:
            rec = "看空"
        else:
            rec = "中性"

        return {
            "bull_points": bull_points,
            "bear_points": bear_points,
            "recommendation": rec,
            "confidence": 50 + abs(bull_score - bear_score) * 10,
            "method": "quick_analysis"
        }


# ============================================================
# 财务分析引擎
# ============================================================

class FinancialAnalyzer:
    """深度财务分析引擎"""

    def __init__(self, akshare_data: Dict):
        self.data = akshare_data

    def analyze_debt(self) -> Dict:
        """债务分析"""
        balance = self.data.get('balance', [])
        indicators = self.data.get('indicators', [])

        result = {"trend": [], "assessment": "", "alerts": []}

        for item in balance[:8]:
            total_assets = item.get('资产总计') or item.get('TOTALASSETS') or 0
            total_liab = item.get('负债合计') or item.get('TOTALLIABILITY') or 0
            if total_assets > 0:
                ratio = total_liab / total_assets
                period = item.get('REPORT_DATE_NAME') or item.get('end_date') or ''
                result["trend"].append({
                    "period": period,
                    "total_assets": total_assets / 1e4,  # 万元
                    "total_liab": total_liab / 1e4,
                    "debt_ratio": ratio
                })

        if result["trend"]:
            latest_ratio = result["trend"][0]["debt_ratio"]
            if len(result["trend"]) > 1:
                old_ratio = result["trend"][-1]["debt_ratio"]
                if latest_ratio < old_ratio:
                    result["trend_direction"] = "改善（负债率下降）"
                elif latest_ratio > old_ratio:
                    result["trend_direction"] = "恶化（负债率上升）"
                else:
                    result["trend_direction"] = "稳定"

            if latest_ratio < 0.4:
                result["assessment"] = "负债率低，财务结构非常稳健"
            elif latest_ratio < 0.6:
                result["assessment"] = "负债率适中，财务风险可控"
            elif latest_ratio < 0.8:
                result["assessment"] = "负债率偏高，需关注偿债能力"
            else:
                result["assessment"] = "负债率过高，财务风险较大"
                result["alerts"].append("资产负债率超过 80%")

        return result

    def analyze_profitability(self) -> Dict:
        """盈利能力分析"""
        indicators = self.data.get('indicators', [])

        result = {"trend": [], "avg_roe": None, "assessment": ""}

        for item in indicators[:8]:
            period = item.get('日期') or item.get('end_date') or ''
            roe = item.get('加权净资产收益率(%)') or item.get('净资产收益率(%)')
            gross_margin = item.get('销售毛利率(%)')
            net_margin = item.get('销售净利率(%)')

            if roe is not None or gross_margin is not None:
                result["trend"].append({
                    "period": period,
                    "roe": roe,
                    "gross_margin": gross_margin,
                    "net_margin": net_margin
                })

        if result["trend"]:
            roe_values = [t["roe"] for t in result["trend"] if t.get("roe") is not None]
            if roe_values:
                result["avg_roe"] = sum(roe_values) / len(roe_values)

                roe_above_15 = sum(1 for r in roe_values if r > 15)
                if result["avg_roe"] > 20 and roe_above_15 >= len(roe_values) * 0.7:
                    result["assessment"] = "优秀 — 持续高 ROE（>20%），具备强竞争优势"
                elif result["avg_roe"] > 15 and roe_above_15 >= len(roe_values) * 0.5:
                    result["assessment"] = "良好 — ROE 大多高于 15%，盈利能力较强"
                elif result["avg_roe"] > 10:
                    result["assessment"] = "一般 — ROE 在 10-15% 之间，盈利能力中等"
                else:
                    result["assessment"] = "较弱 — ROE 持续低于 10%，盈利能力不足"

            # 毛利率趋势
            margins = [t["gross_margin"] for t in result["trend"] if t.get("gross_margin") is not None]
            if len(margins) >= 3:
                if margins[0] > margins[-1]:
                    result["margin_trend"] = "毛利率改善（上升）"
                elif margins[0] < margins[-1]:
                    result["margin_trend"] = "毛利率下滑"
                else:
                    result["margin_trend"] = "毛利率稳定"

        return result

    def analyze_growth(self) -> Dict:
        """成长性分析"""
        income = self.data.get('income', [])
        indicators = self.data.get('indicators', [])

        result = {"revenue_cagr": None, "profit_cagr": None, "assessment": ""}

        # 从利润表获取营收和净利润
        revenues = []
        net_profits = []

        for item in income[:8]:
            period = item.get('REPORT_DATE_NAME') or ''
            revenue = item.get('营业总收入') or item.get('TOTALOPERATEREVE')
            net_profit = item.get('净利润') or item.get('NETPROFIT')

            if revenue and revenue > 0:
                revenues.append({"period": period, "value": revenue / 1e4})
            if net_profit is not None:
                net_profits.append({"period": period, "value": net_profit / 1e4})

        if len(revenues) >= 2:
            first = revenues[-1]["value"]
            last = revenues[0]["value"]
            n = len(revenues) - 1
            if first > 0:
                cagr = (last / first) ** (1 / n) - 1
                result["revenue_cagr"] = cagr
                result["revenue_first"] = first
                result["revenue_last"] = last
                result["revenue_periods"] = n + 1

        if len(net_profits) >= 2:
            first = net_profits[-1]["value"]
            last = net_profits[0]["value"]
            n = len(net_profits) - 1
            if first > 0 and last > 0:
                cagr = (last / first) ** (1 / n) - 1
                result["profit_cagr"] = cagr
            elif first < 0 and last > 0:
                result["profit_cagr"] = "扭亏为盈"
            elif first > 0 and last < 0:
                result["profit_cagr"] = "由盈转亏"

        if result["revenue_cagr"] is not None:
            if result["revenue_cagr"] > 0.2:
                result["assessment"] = "高成长（营收 CAGR > 20%）"
            elif result["revenue_cagr"] > 0.1:
                result["assessment"] = "稳健成长（营收 CAGR 10-20%）"
            elif result["revenue_cagr"] > 0:
                result["assessment"] = "低速成长（营收 CAGR < 10%）"
            else:
                result["assessment"] = "营收收缩"

        result["revenue_history"] = revenues
        result["net_profit_history"] = net_profits
        return result

    def analyze_cashflow(self) -> Dict:
        """现金流分析"""
        cashflow = self.data.get('cashflow', [])
        income = self.data.get('income', [])

        result = {"trend": [], "fcf_positive_years": 0, "assessment": ""}

        for i, cf_item in enumerate(cashflow[:8]):
            period = cf_item.get('REPORT_DATE_NAME') or ''
            op_cf = cf_item.get('经营活动产生的现金流量净额') or 0
            invest_cf = cf_item.get('投资活动产生的现金流量净额') or 0
            fin_cf = cf_item.get('筹资活动产生的现金流量净额') or 0

            # 自由现金流 ≈ 经营现金流 - 资本支出
            capex = cf_item.get('购建固定资产、无形资产和其他长期资产支付的现金') or 0
            fcf = op_cf - capex

            result["trend"].append({
                "period": period,
                "operating_cf": op_cf / 1e4,
                "investing_cf": invest_cf / 1e4,
                "financing_cf": fin_cf / 1e4,
                "capex": capex / 1e4,
                "fcf": fcf / 1e4
            })

        if result["trend"]:
            fcf_values = [t["fcf"] for t in result["trend"]]
            result["fcf_positive_years"] = sum(1 for v in fcf_values if v > 0)

            latest_fcf = fcf_values[0]
            if latest_fcf > 0:
                result["assessment"] = f"最新一期自由现金流为正（{latest_fcf:.0f} 万元），具备内生增长能力"
            else:
                result["assessment"] = f"最新一期自由现金流为负（{latest_fcf:.0f} 万元），需关注资金压力"

            # FCF/净利润 比率
            if income and len(income) > 0:
                latest_net_profit = income[0].get('净利润') or 0
                if latest_net_profit > 0 and latest_fcf > 0:
                    ratio = latest_fcf / (latest_net_profit / 1e4)
                    result["fcf_to_netprofit_ratio"] = ratio
                    if ratio > 1:
                        result["fcf_quality"] = "优秀（FCF > 净利润，盈利质量高）"
                    elif ratio > 0.7:
                        result["fcf_quality"] = "良好（FCF 接近净利润）"
                    else:
                        result["fcf_quality"] = "一般（FCF < 净利润，需关注应收账款/存货）"

        return result

    def analyze_financial_health(self) -> Dict:
        """综合财务健康分析"""
        indicators = self.data.get('indicators', [])

        result = {"metrics": {}, "alerts": []}

        if indicators:
            latest = indicators[0]
            for key, label in [
                ('流动比率', 'current_ratio'),
                ('速动比率', 'quick_ratio'),
                ('资产负债率(%)', 'debt_ratio'),
                ('总资产周转率(次)', 'asset_turnover'),
            ]:
                val = latest.get(key)
                if val is not None:
                    result["metrics"][label] = safe_float(val)

            # 流动性评估
            cr = result["metrics"].get('current_ratio')
            if cr is not None:
                if cr < 1:
                    result["alerts"].append(f"流动比率 {cr:.2f} < 1，短期偿债压力大")
                elif cr < 1.5:
                    result["alerts"].append(f"流动比率 {cr:.2f}，流动性偏紧")

        return result


# ============================================================
# DCF 估值引擎
# ============================================================

class DCFValuator:
    """三阶段 DCF 估值"""

    def __init__(self, financial_data: Dict, current_price: float, shares_outstanding: float):
        self.financial = financial_data
        self.current_price = current_price
        self.shares = shares_outstanding  # 亿股

    def calculate(self) -> Dict:
        """三阶段 DCF"""
        # 获取基础数据
        income = self.financial.get('income', [])
        indicators = self.financial.get('indicators', [])
        cashflow = self.financial.get('cashflow', [])

        # 获取最新的净利润和 FCF
        latest_net_profit = 0
        latest_fcf = 0

        if income:
            latest_net_profit = income[0].get('净利润') or 0

        # Fallback: 如果 income 为空，尝试从 indicators 中提取
        # indicators 是转置格式（"指标"列为行名，日期为列名）
        # akshare 使用 "归母净利润" 字段名
        if latest_net_profit == 0 and indicators:
            latest_net_profit = self._extract_metric_from_indicators(indicators, '归母净利润')
            if latest_net_profit == 0:
                latest_net_profit = self._extract_metric_from_indicators(indicators, '净利润')

        if cashflow:
            capex = cashflow[0].get('购建固定资产、无形资产和其他长期资产支付的现金') or 0
            op_cf = cashflow[0].get('经营活动产生的现金流量净额') or 0
            latest_fcf = op_cf - capex

        # Fallback: 如果 cashflow 为空，用净利润的 80% 近似 FCF（经验值）
        if latest_fcf == 0 and latest_net_profit > 0:
            latest_fcf = latest_net_profit * 0.8

        # 如果净利润和 FCF 都为负，无法做 DCF
        if latest_net_profit <= 0 and latest_fcf <= 0:
            return {
                "available": False,
                "reason": f"净利润({latest_net_profit/1e8:.1f}亿)和自由现金流({latest_fcf/1e8:.1f}亿)均为负或为零，不适合 DCF 估值",
                "latest_net_profit": latest_net_profit,
                "latest_fcf": latest_fcf
            }

        # 使用净利润作为基础（如果 FCF 为负但利润为正，用利润近似）
        base_earnings = max(latest_net_profit, latest_fcf) / 1e4  # 转为万元

        # 增长率估算
        growth_analyzer = FinancialAnalyzer(self.financial)
        growth_result = growth_analyzer.analyze_growth()
        historical_cagr = growth_result.get("revenue_cagr", 0.1)

        if historical_cagr and isinstance(historical_cagr, (int, float)):
            base_growth = max(0.03, min(0.25, historical_cagr))
        else:
            base_growth = 0.10

        # 三情景
        scenarios = {
            "悲观": {
                "stage1_growth": base_growth * 0.5,
                "stage2_growth": base_growth * 0.25,
                "stage1_years": 3,
                "terminal_growth": 0.02,
                "discount_rate": 0.12
            },
            "中性": {
                "stage1_growth": base_growth,
                "stage2_growth": base_growth * 0.5,
                "stage1_years": 5,
                "terminal_growth": 0.03,
                "discount_rate": 0.10
            },
            "乐观": {
                "stage1_growth": base_growth * 1.5,
                "stage2_growth": base_growth * 0.75,
                "stage1_years": 7,
                "terminal_growth": 0.04,
                "discount_rate": 0.08
            }
        }

        results = {}
        for name, params in scenarios.items():
            value = self._run_dcf(
                base_earnings=base_earnings,
                stage1_growth=params["stage1_growth"],
                stage2_growth=params["stage2_growth"],
                stage1_years=params["stage1_years"],
                terminal_growth=params["terminal_growth"],
                discount_rate=params["discount_rate"]
            )
            results[name] = value

        # 理想买入价 = 悲观估值 * 0.7
        bear_value = results["悲观"]["value_per_share"]
        ideal_buy = bear_value * 0.7

        return {
            "available": True,
            "base_earnings": round(base_earnings, 2),
            "base_growth_rate": round(base_growth, 2),
            "scenarios": results,
            "ideal_buy_price": round(ideal_buy, 2),
            "current_price": self.current_price,
            "margin_of_safety": round((1 - self.current_price / bear_value) * 100, 1) if bear_value > 0 else None
        }

    def _extract_metric_from_indicators(self, indicators: list, metric_name: str) -> float:
        """从 indicators 中提取指标值（支持转置格式和列表格式）"""
        # 格式 1: 字典列表，直接取键
        if isinstance(indicators, list) and indicators:
            if isinstance(indicators[0], dict):
                for item in indicators:
                    if metric_name in item and item.get(metric_name):
                        return float(item[metric_name])
                # 转置格式: 每行有 "指标" 列，其余列为各期数值
                if '指标' in indicators[0]:
                    for item in indicators:
                        if item.get('指标') == metric_name:
                            # 取第一个非日期列的值（最新一期）
                            for key in item:
                                if key not in ('指标', '选项') and item[key]:
                                    return float(item[key])
        return 0

    def _run_dcf(self, base_earnings, stage1_growth, stage2_growth,
                  stage1_years, terminal_growth, discount_rate) -> Dict:
        """单情景 DCF 计算"""
        pv_sum = 0
        current_earnings = base_earnings
        stage2_start = stage1_years + 1

        # Stage 1: 高增长期
        stage1_details = []
        for year in range(1, stage1_years + 1):
            current_earnings *= (1 + stage1_growth)
            pv = current_earnings / ((1 + discount_rate) ** year)
            pv_sum += pv
            stage1_details.append({
                "year": year,
                "earnings": round(current_earnings, 2),
                "pv": round(pv, 2)
            })

        # Stage 2: 过渡期（3 年）
        stage2_details = []
        for year in range(stage2_start, stage2_start + 3):
            current_earnings *= (1 + stage2_growth)
            pv = current_earnings / ((1 + discount_rate) ** year)
            pv_sum += pv
            stage2_details.append({
                "year": year,
                "earnings": round(current_earnings, 2),
                "pv": round(pv, 2)
            })

        # Stage 3: 永续期
        terminal_year_earnings = current_earnings * (1 + terminal_growth)
        if discount_rate > terminal_growth:
            terminal_value = terminal_year_earnings / (discount_rate - terminal_growth)
            pv_terminal = terminal_value / ((1 + discount_rate) ** (stage2_start + 2))
            pv_sum += pv_terminal
        else:
            pv_terminal = 0

        total_value = pv_sum
        # total_value 单位是万元，shares 单位是亿股
        # 元/股 = (total_value × 1e4) ÷ (shares × 1e8) = total_value / shares × 1e-4
        value_per_share = (total_value / self.shares * 0.0001) if self.shares > 0 else 0

        return {
            "stage1_years": stage1_years,
            "stage1_growth": round(stage1_growth, 3),
            "stage2_growth": round(stage2_growth, 3),
            "terminal_growth": terminal_growth,
            "discount_rate": round(discount_rate, 3),
            "stage1_pv": round(sum(d["pv"] for d in stage1_details), 2),
            "stage2_pv": round(sum(d["pv"] for d in stage2_details), 2),
            "terminal_pv": round(pv_terminal, 2),
            "total_value": round(total_value, 2),
            "value_per_share": round(value_per_share, 2),
            "stage1_details": stage1_details,
            "stage2_details": stage2_details
        }


# ============================================================
# 行业知识库
# ============================================================

INDUSTRY_KNOWLEDGE = {
    "白酒": {
        "model": "品牌驱动的高毛利消费品。通过品牌溢价和渠道管控获取超额利润。",
        "moat_type": "品牌 + 无形资产",
        "key_risks": "政策风险（反腐/限酒）、消费税改革、年轻消费者偏好变化",
        "competition": "高端白酒（茅台/五粮液）寡头格局，次高端竞争激烈"
    },
    "银行": {
        "model": "利差收入为主，通过存贷利差和中间业务获取利润。",
        "moat_type": "牌照 + 规模效应",
        "key_risks": "不良贷款率上升、利率市场化压缩利差、经济周期下行",
        "competition": "国有大行占主导，城商行/农商行差异化竞争"
    },
    "石油加工": {
        "model": "原油加工获取成品油和化工品，收入取决于加工量和炼油价差。",
        "moat_type": "规模 + 成本优势",
        "key_risks": "原油价格波动、环保政策收紧、新能源替代",
        "competition": "中石化/中石油主导，民营炼化产能扩张"
    },
    "半导体": {
        "model": "芯片设计/制造/封测，技术驱动型，研发投入高。",
        "moat_type": "技术壁垒 + 转换成本",
        "key_risks": "技术迭代快、国际贸易限制、周期性波动",
        "competition": "国产替代加速，头部企业抢占市场份额"
    },
    "医药": {
        "model": "药品研发、生产和销售，创新药依赖研发投入。",
        "moat_type": "专利 + 审批壁垒",
        "key_risks": "集采降价、研发失败、政策变化",
        "competition": "创新药企 vs 仿制药企分化加剧"
    },
    "新能源": {
        "model": "光伏/锂电/风电等，受政策补贴和技术进步驱动。",
        "moat_type": "规模 + 成本 + 技术",
        "key_risks": "产能过剩、补贴退坡、海外贸易壁垒",
        "competition": "行业集中度提升，龙头优势明显"
    },
    "互联网": {
        "model": "平台经济，通过用户规模和流量变现。",
        "moat_type": "网络效应 + 规模",
        "key_risks": "监管收紧、反垄断、用户增长见顶",
        "competition": "头部平台生态闭环，新进入者机会有限"
    },
}


def get_industry_knowledge(industry: str) -> Dict:
    """获取行业知识"""
    for key, info in INDUSTRY_KNOWLEDGE.items():
        if key in industry:
            return info
    return {
        "model": f"{industry}行业，具体商业模式需结合公司年报分析。",
        "moat_type": "需具体分析",
        "key_risks": "行业政策变化、竞争加剧、技术替代",
        "competition": "需具体分析行业竞争格局"
    }


# ============================================================
# 报告生成引擎
# ============================================================

class ReportGenerator:
    """4 部分报告生成器"""

    def __init__(self, code: str, name: str, akshare_data: Dict, factor_data: Dict,
                 debate_data: Dict, dcf_data: Dict):
        self.code = code
        self.name = name
        self.akshare = akshare_data
        self.factor = factor_data
        self.debate = debate_data
        self.dcf = dcf_data
        self.date = datetime.now().strftime("%Y-%m-%d")
        self.time = datetime.now().strftime("%Y-%m-%d %H:%M")

    def _shares_display(self) -> float:
        return self.dcf.get("shares_outstanding_billion", 0)

    def generate(self) -> str:
        """生成完整报告"""
        report = []

        # 标题
        report.append(self._header())

        # 第一部分
        report.append(self._part1_qualitative())

        # 第二部分
        report.append(self._part2_quantitative())

        # 第三部分
        report.append(self._part3_valuation())

        # 第四部分
        report.append(self._part4_decision())

        return "\n".join(report)

    def _header(self) -> str:
        basic = self.akshare.get("basic", {})
        industry = basic.get("industry", "未知")
        market_cap = basic.get("market_cap", 0)
        pe = basic.get("pe_ttm", 0)
        pb = basic.get("pb", 0)

        ak_available = self.akshare.get("available", False)
        ak_status = "✅ 已接入 akshare 完整财务数据" if ak_available else "⚠️ akshare 数据不可用，使用因子数据"

        return f"""# 🔬 个股深度分析报告 (Workflow B 增强版)

**股票代码**: {self.code}
**公司名称**: {self.name or basic.get('name', '待确认')}
**行业**: {industry}
**总市值**: {f"{market_cap / 1e8:.1f} 亿元" if market_cap else '暂缺'}
**PE(TTM)**: {f"{pe:.1f}x" if pe else '暂缺'}
**PB**: {f"{pb:.2f}x" if pb else '暂缺'}

**分析日期**: {self.date}
**数据来源**: {ak_status}

---

> **报告结构说明**：
> - 第一部分：定性分析 — 商业模式与经济护城河
> - 第二部分：定量分析 — 财务健康与盈利能力
> - 第三部分：估值分析 — 内在价值与安全边际
> - 第四部分：投资决策建议 — 综合研判与交易计划
"""

    def _part1_qualitative(self) -> str:
        """第一部分：定性分析"""
        basic = self.akshare.get("basic", {})
        industry = basic.get("industry", "未知")
        knowledge = get_industry_knowledge(industry)

        # 商业模式
        business_model = knowledge["model"]
        moat_type = knowledge["moat_type"]

        # 护城河分析
        moat_analysis = self._analyze_moat()

        # 管理层分析
        management_analysis = self._analyze_management()

        # 行业分析
        industry_analysis = self._analyze_industry(knowledge)

        return f"""## 📋 第一部分：定性分析 — 商业模式与经济护城河

### 1.1 商业模式阐释

**行业**: {industry}

{business_model}

{self._describe_business_details()}

### 1.2 经济护城河评估

**主要护城河类型**: {moat_type}

{moat_analysis}

### 1.3 管理层与资本配置

{management_analysis}

### 1.4 行业格局与成长空间

{industry_analysis}

---
"""

    def _describe_business_details(self) -> str:
        """描述业务细节"""
        income = self.akshare.get("income", [])
        if not income:
            return "> 💡 建议结合公司年报和公告获取更详细的商业模式信息。"

        latest = income[0]
        revenue = latest.get("营业总收入") or latest.get("TOTALOPERATEREVE") or 0
        cost = latest.get("营业总成本") or latest.get("TOTALOPERATECOST") or 0
        gross_profit = revenue - cost if revenue and cost else 0

        return f"""**最近报告期**: {latest.get('REPORT_DATE_NAME', '--')}
- 营业收入：{revenue / 1e4:.0f} 万元
- 营业成本：{cost / 1e4:.0f} 万元
- 毛利润：{gross_profit / 1e4:.0f} 万元（毛利率 {gross_profit / revenue * 100:.1f}%）"""

    def _analyze_moat(self) -> str:
        """护城河分析"""
        indicators = self.akshare.get("indicators", [])

        moat_scores = {
            "品牌护城河": 0,
            "网络效应": 0,
            "成本优势": 0,
            "转换成本": 0,
            "无形资产": 0
        }

        evidence = []

        if indicators:
            latest = indicators[0]
            gross_margin = latest.get("销售毛利率(%)")
            roe = latest.get("加权净资产收益率(%)")
            net_margin = latest.get("销售净利率(%)")

            # 品牌护城河
            if gross_margin and gross_margin > 50:
                moat_scores["品牌护城河"] = 4
                evidence.append(f"✅ **品牌护城河**：毛利率 {gross_margin:.1f}%，表明拥有较强品牌溢价能力")
            elif gross_margin and gross_margin > 30:
                moat_scores["品牌护城河"] = 3
                evidence.append(f"🟡 **品牌护城河**：毛利率 {gross_margin:.1f}%，有一定品牌溢价")
            elif gross_margin and gross_margin > 15:
                moat_scores["品牌护城河"] = 2
                evidence.append(f"🟡 **品牌护城河**：毛利率 {gross_margin:.1f}%，品牌溢价一般")

            # 成本优势
            if gross_margin and indicators[-1].get("销售毛利率(%)"):
                old_margin = indicators[-1].get("销售毛利率(%)")
                if gross_margin > old_margin:
                    moat_scores["成本优势"] = 3
                    evidence.append(f"✅ **成本优势**：毛利率呈上升趋势，成本控制能力改善")

            # ROE 持续性
            roe_values = [ind.get("加权净资产收益率(%)") for ind in indicators[:5] if ind.get("加权净资产收益率(%)") is not None]
            if roe_values:
                avg_roe = sum(roe_values) / len(roe_values)
                above_15 = sum(1 for r in roe_values if r > 15)
                if avg_roe > 15 and above_15 >= len(roe_values) * 0.6:
                    evidence.append(f"✅ **盈利能力持续性**：近 {len(roe_values)} 期平均 ROE {avg_roe:.1f}%，{above_15} 期超过 15%，显示竞争优势可持续")
                    moat_scores["转换成本"] = max(moat_scores["转换成本"], 2)

        if not evidence:
            evidence.append("⚠️ 财务数据不足，护城河需结合定性分析判断")

        max_moat = max(moat_scores, key=moat_scores.get)
        max_score = moat_scores[max_moat]

        if max_score >= 3:
            moat_level = "较宽"
        elif max_score >= 2:
            moat_level = "中等"
        else:
            moat_level = "较窄"

        evidence_str = "\n".join(f"- {e}" for e in evidence)

        return f"""**护城河宽度判断**: {moat_level}

{evidence_str}

> 护城河评估基于财务指标间接推断，建议结合公司年报中的竞争格局描述进行定性验证。"""

    def _analyze_management(self) -> str:
        """管理层分析"""
        holders = self.akshare.get("holders", {})
        dividend = self.akshare.get("dividend", [])

        analysis = []

        # 股权集中度
        top_10 = holders.get("top_10", [])
        if top_10:
            total_pct = 0
            for h in top_10[:5]:
                pct = safe_float(h.get("占总股本比例") or h.get("hold_ratio") or 0)
                if pct:
                    total_pct += pct
            if total_pct > 50:
                analysis.append(f"- **股权集中度较高**：前 5 大股东合计持股约 {total_pct:.1f}%，控制权稳定")
            else:
                analysis.append(f"- **股权相对分散**：前 5 大股东合计持股约 {total_pct:.1f}%，制衡机制较好")

        # 分红历史
        if dividend:
            div_count = len(dividend)
            analysis.append(f"- **分红记录**：最近有 {div_count} 次分红记录，表明公司重视股东回报")
        else:
            analysis.append("- **分红记录**：暂无分红数据或公司未进行分红")

        # 资本配置
        indicators = self.akshare.get("indicators", [])
        if indicators:
            latest = indicators[0]
            undistributed = latest.get("每股未分配利润")
            if undistributed and undistributed > 2:
                analysis.append(f"- **未分配利润充裕**：每股未分配利润 {undistributed:.2f} 元，具备分红/回购/再投资空间")

        if not analysis:
            analysis.append("- 数据不足，建议查阅公司年报中的管理层讨论与分析章节")

        return "\n".join(analysis) + "\n\n> 管理层评估基于股权结构和分红行为间接推断，建议结合公司年报、致股东信和管理层访谈进行深度分析。"

    def _analyze_moat_for_audit(self) -> Dict:
        """护城河分析（审计用，返回结构化数据）"""
        indicators = self.akshare.get("indicators", [])
        evidence = []

        if indicators:
            latest = indicators[0]
            gross_margin = latest.get("销售毛利率(%)")
            if gross_margin and gross_margin > 50:
                evidence.append(f"毛利率 {gross_margin:.1f}%，品牌溢价强")
            elif gross_margin and gross_margin > 30:
                evidence.append(f"毛利率 {gross_margin:.1f}%，有一定品牌溢价")

            roe_values = [ind.get("加权净资产收益率(%)") for ind in indicators[:5] if ind.get("加权净资产收益率(%)") is not None]
            if roe_values:
                avg_roe = sum(roe_values) / len(roe_values)
                above_15 = sum(1 for r in roe_values if r > 15)
                if avg_roe > 15 and above_15 >= len(roe_values) * 0.6:
                    evidence.append(f"近 {len(roe_values)} 期平均 ROE {avg_roe:.1f}%，{above_15} 期超过 15%")

        return {
            "evidence": evidence,
            "evidence_count": len(evidence),
        }

    def _analyze_industry(self, knowledge: Dict) -> str:
        """行业分析"""
        indicators = self.akshare.get("indicators", [])
        growth = None

        if indicators:
            rev_first = indicators[0].get("主营业务收入同比增长率(%)")
            if rev_first:
                growth = rev_first

        competition = knowledge["competition"]
        risks = knowledge["key_risks"]

        growth_text = ""
        if growth is not None:
            if growth > 20:
                growth_text = f"公司营收同比增长 {growth:.1f}%，处于高速成长期"
            elif growth > 10:
                growth_text = f"公司营收同比增长 {growth:.1f}%，处于稳健成长期"
            elif growth > 0:
                growth_text = f"公司营收同比增长 {growth:.1f}%，增速放缓"
            else:
                growth_text = f"公司营收同比下降 {abs(growth):.1f}%，面临增长压力"

        return f"""**行业竞争格局**: {competition}

**成长驱动力**: {growth_text if growth_text else '需结合行业趋势分析'}

**波特五力分析**:
- **新进入者威胁**: 取决于行业壁垒（资金/技术/牌照）
- **替代品威胁**: {risks.split('、')[0] if risks else '需具体分析'}
- **供应商议价能力**: 需结合上游集中度分析
- **客户议价能力**: 需结合下游客户集中度分析
- **行业内部竞争**: {competition.split('，')[0] if competition else '需具体分析'}

> 行业分析基于通用行业知识，建议结合最新行业研报和公司公告进行更新。"""

    def _part2_quantitative(self) -> str:
        """第二部分：定量分析"""
        fa = FinancialAnalyzer(self.akshare)
        debt = fa.analyze_debt()
        profit = fa.analyze_profitability()
        growth = fa.analyze_growth()
        cashflow = fa.analyze_cashflow()
        health = fa.analyze_financial_health()

        report = "## 📊 第二部分：定量分析 — 财务健康与盈利能力\n\n"

        # 2.1 财务健康
        report += "### 2.1 财务健康状况\n\n"

        if debt.get("trend"):
            report += "**资产负债率趋势**:\n\n"
            report += "| 报告期 | 总资产（万元） | 总负债（万元） | 资产负债率 |\n"
            report += "|--------|--------------|--------------|----------|\n"
            for t in debt["trend"][:5]:
                report += f"| {t['period']} | {t['total_assets']:,.0f} | {t['total_liab']:,.0f} | {t['debt_ratio']*100:.1f}% |\n"
            report += f"\n**趋势方向**: {debt.get('trend_direction', '--')}\n"
            report += f"\n**评估**: {debt.get('assessment', '--')}\n"

        # 利息保障倍数
        income = self.akshare.get("income", [])
        if income:
            latest = income[0]
            op_profit = latest.get("营业利润") or latest.get("OPERATINGPROFIT") or 0
            interest_exp = latest.get("利息支出") or latest.get("FINANCEEXPENSE") or 0
            if interest_exp and interest_exp > 0:
                interest_coverage = op_profit / interest_exp
                report += f"\n**利息保障倍数**: {interest_coverage:.1f}x"
                if interest_coverage > 5:
                    report += " — 轻松覆盖利息支出，偿债压力小"
                elif interest_coverage > 2:
                    report += " — 可以覆盖利息，但安全边际一般"
                else:
                    report += " — 利息覆盖能力偏弱，需关注"

        # 自由现金流
        if cashflow.get("trend"):
            report += "\n\n**自由现金流趋势**:\n\n"
            report += "| 报告期 | 经营现金流（万元） | 资本支出（万元） | 自由现金流（万元） |\n"
            report += "|--------|------------------|----------------|------------------|\n"
            for t in cashflow["trend"][:5]:
                report += f"| {t['period']} | {t['operating_cf']:,.0f} | {t['capex']:,.0f} | {t['fcf']:,.0f} |\n"
            report += f"\n{cashflow.get('assessment', '')}\n"
            if cashflow.get("fcf_quality"):
                report += f"\n**盈利质量**: {cashflow.get('fcf_quality')}\n"

        if health.get("alerts"):
            report += "\n**⚠️ 财务健康告警**:\n"
            for alert in health["alerts"]:
                report += f"- {alert}\n"

        report += "\n---\n\n"

        # 2.2 盈利能力
        report += "### 2.2 盈利能力与效率\n\n"

        if profit.get("trend"):
            report += "| 报告期 | ROE(%) | 毛利率(%) | 净利率(%) |\n"
            report += "|--------|--------|----------|----------|\n"
            for t in profit["trend"][:6]:
                report += f"| {t['period']} | {t.get('roe', '--')} | {t.get('gross_margin', '--')} | {t.get('net_margin', '--')} |\n"

            avg_roe_val = profit.get('avg_roe')
            avg_roe_str = f'{avg_roe_val:.1f}%' if avg_roe_val else '暂缺'
            report += f"\n**平均 ROE**: {avg_roe_str}\n"
            report += f"**评估**: {profit.get('assessment', '--')}\n"
            if profit.get("margin_trend"):
                report += f"**毛利率趋势**: {profit['margin_trend']}\n"

            # 资产周转率
            metrics = health.get("metrics", {})
            turnover = metrics.get("asset_turnover")
            if turnover:
                report += f"\n**总资产周转率**: {turnover:.2f} 次"
                if turnover > 1:
                    report += " — 资产使用效率良好"
                elif turnover > 0.5:
                    report += " — 资产使用效率一般"
                else:
                    report += " — 资产使用效率偏低，关注资产质量"

        report += "\n---\n\n"

        # 2.3 成长性
        report += "### 2.3 成长性分析\n\n"

        if growth.get("revenue_history"):
            report += "**营业收入趋势**:\n\n"
            report += "| 报告期 | 营业收入（万元） |\n"
            report += "|--------|--------------|\n"
            for r in growth["revenue_history"][:6]:
                report += f"| {r['period']} | {r['value']:,.0f} |\n"

        if growth.get("net_profit_history"):
            report += "\n**净利润趋势**:\n\n"
            report += "| 报告期 | 净利润（万元） |\n"
            report += "|--------|-------------|\n"
            for r in growth["net_profit_history"][:6]:
                report += f"| {r['period']} | {r['value']:,.0f} |\n"

        rev_cagr = growth.get('revenue_cagr')
        if isinstance(rev_cagr, (int, float)):
            rev_cagr_str = f'{rev_cagr * 100:.1f}%'
        else:
            rev_cagr_str = safe_str(rev_cagr)
        profit_cagr = growth.get('profit_cagr')
        if isinstance(profit_cagr, (int, float)):
            profit_cagr_str = f'{profit_cagr * 100:.1f}%'
        else:
            profit_cagr_str = safe_str(profit_cagr)
        report += f"\n**营收 CAGR**: {rev_cagr_str}\n"
        report += f"**净利润 CAGR**: {profit_cagr_str}\n"
        report += f"\n**成长性评估**: {growth.get('assessment', '数据不足')}\n"

        # 财务异常检测
        report += "\n### 2.4 财务异常检测 (红旗信号)\n\n"
        red_flags = self._detect_red_flags()
        if red_flags:
            for flag in red_flags:
                report += f"- {flag}\n"
        else:
            report += "- 🟢 未发现明显财务异常信号\n"

        return report

    def _detect_red_flags(self) -> List[str]:
        """财务异常检测"""
        flags = []
        income = self.akshare.get("income", [])
        indicators = self.akshare.get("indicators", [])
        cashflow = self.akshare.get("cashflow", [])

        # 1. 应收 vs 营收增速
        if len(income) >= 2 and len(indicators) >= 2:
            rev_current = income[0].get("营业总收入") or 0
            rev_prev = income[1].get("营业总收入") or 0
            ar_current = indicators[0].get("应收帐款周转率(次)")
            if ar_current and ar_current < 2:
                flags.append(f"🔴 **应收账款周转率偏低 ({ar_current:.1f} 次)**：回款速度慢，可能存在收入确认激进或客户信用问题")

        # 2. 经营现金流 vs 净利润
        if cashflow and income:
            op_cf = cashflow[0].get("经营活动产生的现金流量净额") or 0
            net_profit = income[0].get("净利润") or 0
            if net_profit > 0 and op_cf < 0:
                flags.append(f"🔴 **经营现金流为负但净利润为正 ({op_cf/1e4:.0f} 万 vs {net_profit/1e4:.0f} 万)**：盈利质量存疑，可能存在大量应收账款或存货积压")
            elif net_profit > 0 and op_cf > 0 and op_cf < net_profit * 0.5:
                flags.append(f"🟡 **经营现金流显著低于净利润 (FCF/净利润 < 0.5)**：盈利质量偏弱")

        # 3. 连续亏损
        if income:
            losses = sum(1 for item in income[:4] if (item.get("净利润") or 0) < 0)
            if losses >= 3:
                flags.append(f"🔴 **近 4 期中 {losses} 期净利润为负**：持续亏损，需关注经营可持续性")
            elif losses == 2:
                flags.append(f"🟡 **近 4 期中 {losses} 期净利润为负**：盈利不稳定")

        # 4. 资产负债率过高
        balance = self.akshare.get("balance", [])
        if balance:
            assets = balance[0].get("资产总计") or 0
            liab = balance[0].get("负债合计") or 0
            if assets > 0 and liab / assets > 0.8:
                flags.append(f"🔴 **资产负债率 {liab/assets*100:.1f}%**：负债水平过高，财务风险大")
            elif assets > 0 and liab / assets > 0.7:
                flags.append(f"🟡 **资产负债率 {liab/assets*100:.1f}%**：负债水平偏高，需关注")

        # 5. 商誉占比
        if balance:
            goodwill = balance[0].get("商誉") or 0
            assets = balance[0].get("资产总计") or 0
            if assets > 0 and goodwill / assets > 0.2:
                flags.append(f"🟡 **商誉占总资产 {goodwill/assets*100:.1f}%**：若收购标的业绩不及预期，存在商誉减值风险")

        return flags

    def _part3_valuation(self) -> str:
        """第三部分：估值分析"""
        basic = self.akshare.get("basic", {})
        indicators = self.akshare.get("indicators", [])
        val_history = self.akshare.get("valuation_history", {})

        report = "## 💰 第三部分：估值分析 — 内在价值与安全边际\n\n"

        # 3.1 估值方法选择
        industry = basic.get("industry", "")
        method = self._suggest_valuation_method(industry)
        report += f"### 3.1 估值方法选择\n\n"
        report += f"**行业**: {industry}\n\n"
        report += f"**推荐估值方法**: {method}\n\n"

        # 3.2 DCF 估值
        report += "### 3.2 三阶段 DCF 模型\n\n"
        if self.dcf.get("available"):
            report += self._render_dcf()
        else:
            reason = self.dcf.get("reason", "数据不足")
            report += f"⚠️ **DCF 估值不可用**: {reason}\n\n"
            report += "> 当公司净利润为正且自由现金流可预测时，DCF 估值更有参考价值。\n\n"

        # 3.3 相对估值
        report += "### 3.3 相对估值\n\n"

        # 当前估值
        current_pe = basic.get("pe_ttm")
        current_pb = basic.get("pb")
        report += "**当前估值指标**:\n\n"
        report += "| 指标 | 当前值 |\n"
        report += "|------|------|\n"
        if current_pe:
            report += f"| PE(TTM) | {current_pe:.1f}x |\n"
        if current_pb:
            report += f"| PB | {current_pb:.2f}x |\n"

        # 历史分位
        report += "\n**历史估值分位**:\n\n"
        if val_history:
            for metric in ["pe_ttm", "pb"]:
                if f"{metric}_percentile" in val_history:
                    pct = val_history[f"{metric}_percentile"]
                    min_val = val_history.get(f"{metric}_min", 0)
                    max_val = val_history.get(f"{metric}_max", 0)
                    med_val = val_history.get(f"{metric}_median", 0)
                    latest = val_history.get(f"{metric}_latest", 0)
                    report += f"| {metric.upper()} | 当前 {latest:.1f} | 最低 {min_val:.1f} | 中位数 {med_val:.1f} | 最高 {max_val:.1f} | 分位 {pct:.0f}% |\n"
        else:
            report += "| 数据暂缺，无法获取历史估值分位 |\n"

        # 历史分位解读
        if val_history.get("pe_ttm_percentile") is not None:
            pe_pct = val_history["pe_ttm_percentile"]
            if pe_pct < 20:
                report += f"\n🟢 PE 处于历史 {pe_pct:.0f}% 分位，属于**历史低估区间**\n"
            elif pe_pct < 50:
                report += f"\n🟡 PE 处于历史 {pe_pct:.0f}% 分位，属于**合理偏低区间**\n"
            elif pe_pct < 80:
                report += f"\n🟡 PE 处于历史 {pe_pct:.0f}% 分位，属于**合理偏高区间**\n"
            else:
                report += f"\n🔴 PE 处于历史 {pe_pct:.0f}% 分位，属于**历史高估区间**\n"

        report += "\n"

        # 3.4 安全边际
        report += "### 3.4 安全边际与理想买入价\n\n"
        if self.dcf.get("available"):
            bear_value = self.dcf["scenarios"]["悲观"]["value_per_share"]
            neutral_value = self.dcf["scenarios"]["中性"]["value_per_share"]
            opt_value = self.dcf["scenarios"]["乐观"]["value_per_share"]
            ideal_buy = self.dcf["ideal_buy_price"]
            current_price = self.dcf["current_price"]
            mos = self.dcf["margin_of_safety"]

            report += "| 估值情景 | 内在价值 | 安全边际买入价 | 当前价格 | 差距 |\n"
            report += "|---------|---------|--------------|---------|------|\n"
            report += f"| 悲观 | {bear_value:.2f} 元 | {bear_value*0.7:.2f} 元 | {current_price:.2f} 元 | {(current_price/bear_value-1)*100:+.1f}% |\n"
            report += f"| 中性 | {neutral_value:.2f} 元 | {neutral_value*0.7:.2f} 元 | {current_price:.2f} 元 | {(current_price/neutral_value-1)*100:+.1f}% |\n"
            report += f"| 乐观 | {opt_value:.2f} 元 | {opt_value*0.7:.2f} 元 | {current_price:.2f} 元 | {(current_price/opt_value-1)*100:+.1f}% |\n"

            report += f"\n**理想买入价 (悲观估值×0.7)**: **{ideal_buy:.2f} 元**\n"
            report += f"**当前安全边际**: {f'{mos:.1f}%' if mos is not None else '无法计算'}\n"

            if mos is not None:
                if mos > 30:
                    report += "\n🟢 当前价格具有充足安全边际\n"
                elif mos > 10:
                    report += "\n🟡 安全边际一般，可小仓位试探\n"
                else:
                    report += "\n🔴 安全边际不足，建议等待更低价格\n"
        else:
            report += "⚠️ DCF 估值不可用，无法计算安全边际。\n"
            report += "\n> 建议关注 PE/PB 历史分位，在低估分位（< 30%）时考虑买入。\n"

        return report

    def _suggest_valuation_method(self, industry: str) -> str:
        """根据行业推荐估值方法"""
        methods = {
            "白酒": "PE + DCF（稳定现金流，适合绝对估值）",
            "银行": "PB + PE（资产驱动型，PB 更有参考意义）",
            "保险": "P/EV + PB（内含价值法最合适）",
            "房地产": "PB + NAV（资产重估法）",
            "半导体": "PS + PE（成长期看 PS，成熟期看 PE）",
            "医药": "PE + PEG（创新药看管线价值，仿制药看 PE）",
            "新能源": "PE + PEG（成长期看增速匹配）",
            "互联网": "PS + PE（用户价值 + 变现能力）",
            "石油加工": "PB + EV/EBITDA（重资产行业，EV/EBITDA 更合适）",
            "零售": "PS + PE（关注同店增长和坪效）",
        }
        for key, method in methods.items():
            if key in industry:
                return method
        return "PE + PB + DCF（综合使用多种方法交叉验证）"

    def _render_dcf(self) -> str:
        """渲染 DCF 结果"""
        report = ""

        base = self.dcf.get("base_earnings", 0)
        growth = self.dcf.get("base_growth_rate", 0)
        report += f"**基础参数**:\n"
        report += f"- 基准盈利（净利润/FCF）: {base:,.0f} 万元\n"
        report += f"- 历史营收 CAGR: {growth:.1%}\n"
        report += f"- 总股本: {self._shares_display():.2f} 亿股\n\n"

        for name in ["悲观", "中性", "乐观"]:
            scenario = self.dcf["scenarios"][name]
            report += f"**{name}情景**:\n\n"
            report += f"- 高增长期: {scenario['stage1_years']} 年，增长率 {scenario['stage1_growth']:.1%}\n"
            report += f"- 过渡期: 3 年，增长率 {scenario['stage2_growth']:.1%}\n"
            report += f"- 永续增长率: {scenario['terminal_growth']:.1%}\n"
            report += f"- 折现率: {scenario['discount_rate']:.1%}\n\n"

            # Stage 1 明细
            report += "Stage 1 高增长期:\n"
            for d in scenario.get("stage1_details", []):
                report += f"  第 {d['year']} 年: 盈利 {d['earnings']:,.0f} 万 → 现值 {d['pv']:,.0f} 万\n"

            # Stage 2 明细
            report += "Stage 2 过渡期:\n"
            for d in scenario.get("stage2_details", []):
                report += f"  第 {d['year']} 年: 盈利 {d['earnings']:,.0f} 万 → 现值 {d['pv']:,.0f} 万\n"

            report += f"  永续价值现值: {scenario['terminal_pv']:,.0f} 万\n"
            report += f"  **企业价值: {scenario['total_value']:,.0f} 万**\n"
            report += f"  **每股内在价值: {scenario['value_per_share']:.2f} 元**\n\n"

        report += "---\n\n"
        return report

    def _part4_decision(self) -> str:
        """第四部分：投资决策建议"""
        report = "## 🎯 第四部分：投资决策建议 — 综合研判与交易计划\n\n"

        # 综合研判
        report += "### 4.1 综合研判\n\n"

        # 核心优势
        strengths = self._identify_strengths()
        report += "**核心优势**:\n\n"
        for i, s in enumerate(strengths, 1):
            report += f"{i}. {s}\n"

        report += "\n"

        # 主要风险
        risks = self._identify_risks()
        report += "**主要风险**:\n\n"
        for i, r in enumerate(risks, 1):
            report += f"{i}. {r}\n"

        report += "\n---\n\n"

        # 4.2 多空辩论摘要
        report += "### 4.2 多空辩论摘要\n\n"
        if self.debate:
            method = self.debate.get("method", "unknown")
            method_label = "完整四角色辩论" if method != "quick_analysis" else "简化规则分析"
            report += f"**辩论方式**: {method_label}\n\n"

            bull = self.debate.get("bull_points", [])
            bear = self.debate.get("bear_points", [])
            rec = self.debate.get("recommendation", "中性")
            conf = self.debate.get("confidence", 50)

            report += "**看多观点**:\n"
            for p in bull:
                report += f"- {p}\n"
            if not bull:
                report += "- (暂无)\n"

            report += "\n**看空观点**:\n"
            for p in bear:
                report += f"- {p}\n"
            if not bear:
                report += "- (暂无)\n"

            report += f"\n**综合推荐**: {rec}（置信度 {conf}%）\n"

        report += "\n---\n\n"

        # 4.3 交易计划
        report += "### 4.3 交易计划建议\n\n"

        recommendation = self._make_final_decision()

        report += f"**最终决策**: 【{recommendation['decision']}】\n\n"
        report += f"**评分**: {recommendation['score']:.1f} / 10\n\n"

        # 仓位建议
        report += f"**仓位类型**: {recommendation['position_type']}\n"
        report += f"**理由**: {recommendation['position_reason']}\n\n"

        # 买入策略
        report += f"**买入策略**: {recommendation['buy_strategy']}\n"
        report += f"**分批买入计划**:\n"
        if recommendation.get("buy_levels"):
            for level in recommendation["buy_levels"]:
                report += f"- {level}\n"

        report += f"\n**卖出纪律**:\n"
        for condition in recommendation.get("sell_conditions", []):
            report += f"- {condition}\n"

        report += f"\n**止损位**: {recommendation.get('stop_loss', '待确认')}\n"
        report += f"**止盈位**: {recommendation.get('take_profit', '待确认')}\n"

        report += "\n---\n\n"

        # 免责声明
        report += """## ⚠️ 免责声明

1. 本报告基于量化数据和算法分析自动生成，**仅供参考，不构成投资建议**
2. DCF 估值对参数假设敏感，实际内在价值可能与计算结果存在较大偏差
3. 市场有风险，投资需谨慎。建议结合独立研究和专业投顾意见做出决策
4. 历史表现不代表未来收益
5. 数据质量和时效性可能影响分析准确性

---

*报告由 Workflow B 增强版自动生成 | {time}*
*数据来源: akshare + DataAggregator + 多空辩论模块*
""".format(time=self.time)

        return report

    def _identify_strengths(self) -> List[str]:
        """识别核心优势"""
        strengths = []
        indicators = self.akshare.get("indicators", [])
        growth_result = FinancialAnalyzer(self.akshare).analyze_growth()

        # ROE
        if indicators:
            avg_roe = None
            roe_values = []
            for ind in indicators[:5]:
                roe = ind.get("加权净资产收益率(%)")
                if roe is not None:
                    roe_values.append(roe)
            if roe_values:
                avg_roe = sum(roe_values) / len(roe_values)
                if avg_roe > 15:
                    strengths.append(f"ROE 持续优秀（近 5 期平均 {avg_roe:.1f}%），具备强盈利能力")
                elif avg_roe > 10:
                    strengths.append(f"ROE 良好（近 5 期平均 {avg_roe:.1f}%），盈利能力稳定")

        # 成长
        cagr = growth_result.get("revenue_cagr")
        if isinstance(cagr, (int, float)) and cagr > 0.15:
            strengths.append(f"营收高速成长（CAGR {cagr:.1%}），处于扩张期")
        elif isinstance(cagr, (int, float)) and cagr > 0.05:
            strengths.append(f"营收稳健成长（CAGR {cagr:.1%}），业务持续扩张")

        # 自由现金流
        cashflow = FinancialAnalyzer(self.akshare).analyze_cashflow()
        if cashflow.get("fcf_positive_years", 0) >= 3:
            strengths.append(f"自由现金流健康（近 {len(cashflow.get('trend', []))} 期中 {cashflow['fcf_positive_years']} 期为正），具备内生增长能力")

        # 负债率
        debt = FinancialAnalyzer(self.akshare).analyze_debt()
        if debt.get("trend"):
            latest_debt = debt["trend"][0]["debt_ratio"]
            if latest_debt < 0.4:
                strengths.append(f"财务结构稳健（资产负债率 {latest_debt:.1%}），抗风险能力强")

        if not strengths:
            strengths.append("需更多数据支撑以识别核心优势")

        return strengths[:3]

    def _identify_risks(self) -> List[str]:
        """识别主要风险"""
        risks = []
        indicators = self.akshare.get("indicators", [])
        income = self.akshare.get("income", [])

        # 连续亏损
        if income:
            losses = sum(1 for item in income[:4] if (item.get("净利润") or 0) < 0)
            if losses >= 3:
                risks.append(f"持续亏损风险（近 4 期中 {losses} 期亏损），经营可持续性存疑")
            elif losses == 2:
                risks.append(f"盈利不稳定（近 4 期中 {losses} 期亏损），需关注盈利拐点")

        # 负债
        balance = self.akshare.get("balance", [])
        if balance:
            assets = balance[0].get("资产总计") or 0
            liab = balance[0].get("负债合计") or 0
            if assets > 0 and liab / assets > 0.7:
                risks.append(f"高负债风险（资产负债率 {liab/assets*100:.1f}%），财务杠杆过高")

        # 行业风险
        basic = self.akshare.get("basic", {})
        industry = basic.get("industry", "")
        knowledge = get_industry_knowledge(industry)
        key_risks = knowledge.get("key_risks", "")
        if key_risks:
            for risk in key_risks.split("、")[:2]:
                risks.append(f"行业风险：{risk}")

        # 财务红旗
        red_flags = self._detect_red_flags()
        red_risks = [f[3:] for f in red_flags if f.startswith("🔴")]
        for r in red_risks[:1]:
            risks.append(f"财务异常：{r}")

        if not risks:
            risks.append("需更多数据识别潜在风险")

        return risks[:3]

    def _make_final_decision(self) -> Dict:
        """综合决策"""
        score = 5.0  # 基础分
        reasons = []

        # 辩论推荐
        debate_rec = self.debate.get("recommendation", "中性")
        debate_conf = self.debate.get("confidence", 50)
        if debate_rec == "看多":
            score += 1.5
            reasons.append("多空辩论偏向看多")
        elif debate_rec == "看空":
            score -= 1.5
            reasons.append("多空辩论偏向看空")

        # 估值水平
        if self.dcf.get("available"):
            mos = self.dcf.get("margin_of_safety")
            if mos and mos > 30:
                score += 1.5
                reasons.append(f"具有充足安全边际 ({mos:.1f}%)")
            elif mos and mos > 0:
                score += 0.5
                reasons.append(f"有一定安全边际 ({mos:.1f}%)")
            elif mos is not None and mos < -20:
                score -= 1.5
                reasons.append(f"当前价格显著高于内在价值 (溢价 {abs(mos):.1f}%)")

        # 盈利质量
        indicators = self.akshare.get("indicators", [])
        if indicators:
            avg_roe = sum(ind.get("加权净资产收益率(%)", 0) or 0 for ind in indicators[:5]) / 5
            if avg_roe > 15:
                score += 1
                reasons.append("ROE 持续优秀")
            elif avg_roe < 5:
                score -= 1
                reasons.append("ROE 持续偏低")

        # 成长性
        growth = FinancialAnalyzer(self.akshare).analyze_growth()
        cagr = growth.get("revenue_cagr")
        if isinstance(cagr, (int, float)):
            if cagr > 0.2:
                score += 1
                reasons.append("高速成长")
            elif cagr < -0.1:
                score -= 1
                reasons.append("营收收缩")

        # 负债
        debt = FinancialAnalyzer(self.akshare).analyze_debt()
        if debt.get("trend"):
            latest_debt = debt["trend"][0]["debt_ratio"]
            if latest_debt > 0.7:
                score -= 1
                reasons.append("负债率偏高")

        # 财务红旗
        red_flags = self._detect_red_flags()
        red_count = sum(1 for f in red_flags if f.startswith("🔴"))
        if red_count >= 2:
            score -= 2
            reasons.append(f"存在 {red_count} 个严重财务红旗信号")
        elif red_count == 1:
            score -= 0.5
            reasons.append("存在 1 个财务红旗信号")

        score = max(1, min(10, score))

        # 决策映射
        if score >= 8:
            decision = "强烈买入"
            position_type = "核心仓位（15-20%）"
            position_reason = "基本面优秀、估值低估、成长性好"
            buy_strategy = "金字塔式买入法，分 3 批建仓"
            buy_levels = [
                f"第 1 批 (40%): 当前价格附近建仓",
                f"第 2 批 (35%): 回调 5-10% 加仓",
                f"第 3 批 (25%): 回调 15-20% 加仓"
            ]
        elif score >= 6.5:
            decision = "买入"
            position_type = "卫星仓位（5-10%）"
            position_reason = "基本面良好，但存在一定不确定性"
            buy_strategy = "分批买入，先小仓位试探"
            buy_levels = [
                f"第 1 批 (50%): 当前价格建仓",
                f"第 2 批 (50%): 回调 8-12% 加仓"
            ]
        elif score >= 5:
            decision = "持有"
            position_type = "暂不新增仓位"
            position_reason = "基本面和估值中性，等待更好时机"
            buy_strategy = "观望，等待回调至理想价位"
            buy_levels = ["当前不建议加仓"]
        elif score >= 3.5:
            decision = "卖出"
            position_type = "减仓"
            position_reason = "基本面或估值存在明显问题"
            buy_strategy = "不建议买入，已有持仓建议减仓"
            buy_levels = []
        else:
            decision = "强烈卖出"
            position_type = "清仓"
            position_reason = "基本面严重恶化或估值极度泡沫"
            buy_strategy = "不建议买入，建议清仓回避"
            buy_levels = []

        # 止损止盈
        basic = self.akshare.get("basic", {})
        current_price = 0
        price_data = self.factor.get("price", {})
        if price_data and price_data.get("price"):
            current_price = price_data["price"]
        elif basic.get("pe_ttm"):
            # 无法获取价格
            current_price = 0

        stop_loss = f"当前价格的 -8%" if current_price else "待确认后设置"
        take_profit = f"当前价格的 +20-30%" if current_price else "待确认后设置"

        sell_conditions = [
            "估值极度高估（PE > 历史 90% 分位）",
            "护城河受损（毛利率/ROE 持续下滑）",
            "发现更好的投资机会",
            "公司基本面发生重大负面变化",
            "止损线触发（-8% 无条件止损）"
        ]

        return {
            "score": score,
            "decision": decision,
            "reasons": reasons,
            "position_type": position_type,
            "position_reason": position_reason,
            "buy_strategy": buy_strategy,
            "buy_levels": buy_levels,
            "sell_conditions": sell_conditions,
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }


# ============================================================
# 主执行流程
# ============================================================

class WorkflowBDeepHandler:
    """Workflow B 增强版主处理器"""

    def __init__(self, code: str, name: str = ''):
        self.code = code
        self.name = name
        self.date = datetime.now().strftime("%Y-%m-%d")

        # 判断市场
        # 支持两种格式: US.HD (前缀) 和 HD.US (后缀)
        code_upper = code.upper().strip()
        self.is_us_stock = code_upper.startswith('US.') or code_upper.endswith('.US')
        self.is_hk_stock = code_upper.startswith('HK.') or code_upper.endswith('.HK')
        self.is_a_stock = not self.is_us_stock and not self.is_hk_stock
        
        # 标准化代码为 Futu 格式 (US.XXX)
        if self.is_us_stock:
            if code_upper.startswith('US.'):
                self.futu_code = code_upper
            else:
                self.futu_code = f"US.{code_upper.replace('.US', '')}"
        elif self.is_hk_stock:
            if code_upper.startswith('HK.'):
                self.futu_code = code_upper
            else:
                self.futu_code = f"HK.{code_upper.replace('.HK', '')}"
        else:
            self.futu_code = code_upper
            # A股自动补全市场前缀
            if code.startswith(('600', '601', '603', '605', '688')):
                self.futu_code = f"SH.{code}"
            elif code.startswith(('000', '002', '300', '301')):
                self.futu_code = f"SZ.{code}"

        # 输出目录
        safe_code = code.replace('.', '_')
        self.output_dir = TRADE_DIR / "data" / "workflow_b" / f"{safe_code}_{self.date}"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 数据容器
        self.akshare_data = {}
        self.factor_data = {}
        self.debate_data = {}
        self.dcf_data = {}

        # 审计上下文
        self._audit_context = {
            "web_search_results": [],
            "has_analyst_reports": False,
            "moat_analysis": {},
            "management_analysis": "",
            "red_flags": [],
            "financial_summary": {},
            "valuation_summary": {},
        }

        # 审计上下文
        self._audit_context = {
            "web_search_results": [],
            "has_analyst_reports": False,
            "moat_analysis": {},
            "management_analysis": "",
            "red_flags": [],
            "financial_summary": {},
            "valuation_summary": {},
        }

    def run(self) -> str:
        """执行完整分析流程"""
        print("=" * 60)
        print("Workflow B 增强版 — 单股深度分析")
        print(f"股票: {self.code} {self.name}")
        print(f"日期: {self.date}")
        print(f"市场: {'A 股' if self.is_a_stock else '美股' if self.is_us_stock else '港股'}")
        print("=" * 60)

        # Step 1: 获取 akshare 数据（仅 A 股）
        if self.is_a_stock:
            self._fetch_akshare()

        # Step 2: 获取因子数据
        self._fetch_factors()

        # Step 3: DCF 估值
        self._calculate_dcf()

        # Step 4: 多空辩论
        self._run_debate()

        # Step 5: 生成报告
        report = self._generate_report()

        # Step 6: 生成审计报告
        audit_report = self._generate_audit()

        # 保存数据（传入审计报告以便持久化）
        self._save_data(audit_report)

        print("\n" + "=" * 60)
        print("分析完成")
        print(f"报告路径: {self.output_dir / 'decision_report.md'}")
        print("=" * 60)

        return report

    def _fetch_akshare(self):
        """获取 akshare 数据"""
        print("\nStep 1: 获取 akshare 财务数据...")
        fetcher = AkshareFetcher()
        if fetcher.is_available():
            self.akshare_data = fetcher.fetch_all(self.code, self.name)
            print(f"  ✅ akshare 数据获取完成")
            print(f"  行业: {self.akshare_data.get('basic', {}).get('industry', '--')}")
        else:
            self.akshare_data = {"available": False, "error": "akshare 未安装"}
            print("  ⚠️ akshare 不可用，将使用因子数据")

    def _fetch_factors(self):
        """获取因子数据"""
        print("\nStep 2: 获取因子数据...")
        loader = FactorDataLoader()
        if loader.is_available():
            symbol = self.futu_code
            self.factor_data = loader.load_all(symbol, self.name)
            print(f"  ✅ 因子数据获取完成")
        else:
            self.factor_data = {"available": False}
            print("  ⚠️ DataAggregator 不可用")

    def _calculate_dcf(self):
        """计算 DCF 估值"""
        print("\nStep 3: 计算 DCF 估值...")
        # 美股/港股：AkShare 不支持，跳过 DCF
        if not self.is_a_stock:
            self.dcf_data = {"available": False, "reason": "非A股，AkShare 不支持，使用因子数据估值"}
            print("  ⚠️ 非A股，跳过 DCF（使用因子数据估值）")
            return
        
        if self.akshare_data.get("available"):
            basic = self.akshare_data.get("basic", {})
            market_cap = basic.get("market_cap") or 0
            pe = basic.get("pe_ttm") or 0  # safe_float can return None

            # 估算当前价格
            current_price = 0

            # 简化：从 akshare basic 获取信息估算
            if market_cap and market_cap > 0:
                # 假设流通股本 ≈ 总股本
                float_shares = basic.get("raw", {}).get("流通股本") if basic.get("raw") else None
                if float_shares:
                    shares_outstanding = safe_float(float_shares)
                else:
                    # 用市值和 PE 反推
                    if pe > 0:
                        shares_outstanding = 1  # 暂时用默认

            # 尝试从价格数据获取
            price_data = self.factor_data.get("price", {})
            if price_data and price_data.get("price"):
                current_price = price_data["price"]
            elif market_cap > 0:
                # 无法获取准确价格，用粗略估算
                current_price = 0

            # 获取股本数据（优先从 indicators 提取）
            total_shares = None
            indicators = self.akshare_data.get("indicators", [])
            if indicators:
                total_shares = indicators[0].get("每股指标汇总", {}).get("总股本(万股)")

                # 如果没有直接总股本数据，用 净资产 / 每股净资产 计算
                if not total_shares:
                    nav = self._extract_indicator_metric(indicators, '股东权益合计(净资产)')
                    nav_per_share = self._extract_indicator_metric(indicators, '每股净资产')
                    if nav > 0 and nav_per_share > 0:
                        # nav 单位是元，nav_per_share 是元/股，结果转为亿股（/1e8）
                        total_shares = (nav / nav_per_share) / 1e8

                # 备选：用 净利润 / 每股收益 计算
                if not total_shares:
                    net_profit = self._extract_indicator_metric(indicators, '归母净利润')
                    eps = self._extract_indicator_metric(indicators, '基本每股收益')
                    if net_profit > 0 and eps > 0:
                        total_shares = (net_profit / eps) / 1e8  # 转为亿股

            shares = safe_float(total_shares) if total_shares else 1  # 单位：亿股

            valuator = DCFValuator(self.akshare_data, current_price, shares)
            self.dcf_data = valuator.calculate()
            # 附加总股本供报告展示
            self.dcf_data["shares_outstanding_billion"] = round(shares, 2)
            print(f"  ✅ DCF 计算完成: {'可用' if self.dcf_data.get('available') else '不可用'}")
        else:
            self.dcf_data = {"available": False, "reason": "无 akshare 财务数据"}
            print("  ⚠️ 无财务数据，跳过 DCF")

    def _extract_indicator_metric(self, indicators: list, metric_name: str) -> float:
        """从 indicators 中提取指标值"""
        if isinstance(indicators, list):
            for item in indicators:
                if isinstance(item, dict) and item.get('指标') == metric_name:
                    for key in item:
                        if key not in ('指标', '选项') and item[key]:
                            try:
                                return float(item[key])
                            except (ValueError, TypeError):
                                pass
        return 0.0

    def _run_debate(self):
        """执行多空辩论"""
        print("\nStep 4: 执行多空辩论...")
        runner = DebateRunner()
        self.debate_data = runner.run(self.futu_code, self.name, self.output_dir, self.akshare_data)
        print(f"  ✅ 辩论完成: {self.debate_data.get('recommendation', '--')}")

    def _generate_report(self) -> str:
        """生成报告"""
        print("\nStep 5: 生成分析报告...")
        generator = ReportGenerator(
            code=self.code,
            name=self.name,
            akshare_data=self.akshare_data,
            factor_data=self.factor_data,
            debate_data=self.debate_data,
            dcf_data=self.dcf_data
        )
        report = generator.generate()

        report_file = self.output_dir / "decision_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        # 收集审计上下文
        self._collect_audit_context(generator)

        print(f"  ✅ 报告已保存: {report_file}")
        return report

    def _collect_audit_context(self, generator):
        """收集审计上下文数据"""
        self._audit_context["moat_analysis"] = generator._analyze_moat_for_audit()
        self._audit_context["management_analysis"] = generator._analyze_management()
        self._audit_context["red_flags"] = generator._detect_red_flags()
        self._audit_context["decision"] = generator._make_final_decision()

        fa = FinancialAnalyzer(self.akshare_data)
        self._audit_context["financial_summary"] = {
            "debt_analysis": fa.analyze_debt(),
            "profitability": fa.analyze_profitability(),
            "growth": fa.analyze_growth(),
            "cashflow": fa.analyze_cashflow(),
        }
        self._audit_context["valuation_summary"] = {
            "has_relative_valuation": True,
            "has_historical_valuation": bool(self.akshare_data.get("valuation_history", {})),
        }

    def _save_data(self, audit_report: Optional[Dict] = None):
        """保存所有数据"""
        with open(self.output_dir / "akshare_data.json", 'w', encoding='utf-8') as f:
            json.dump(self.akshare_data, f, ensure_ascii=False, indent=2, default=str)
        with open(self.output_dir / "factor_data.json", 'w', encoding='utf-8') as f:
            json.dump(self.factor_data, f, ensure_ascii=False, indent=2, default=str)
        with open(self.output_dir / "valuation_data.json", 'w', encoding='utf-8') as f:
            json.dump(self.dcf_data, f, ensure_ascii=False, indent=2, default=str)
        with open(self.output_dir / "debate_data.json", 'w', encoding='utf-8') as f:
            json.dump(self.debate_data, f, ensure_ascii=False, indent=2, default=str)
        if audit_report:
            with open(self.output_dir / "audit_report.json", 'w', encoding='utf-8') as f:
                json.dump(audit_report, f, ensure_ascii=False, indent=2, default=str)

        # 从审计上下文中提取决策和评分
        decision_info = self._audit_context.get("decision", {})
        audit_score = 0
        if audit_report:
            audit_score = audit_report.get("reliability", {}).get("score", 0)

        with open(self.output_dir / "all_data.json", 'w', encoding='utf-8') as f:
            data = {
                "akshare": self.akshare_data,
                "factor": self.factor_data,
                "valuation": self.dcf_data,
                "debate": self.debate_data,
                # Workflow D 依赖的顶层字段
                "decision": decision_info.get("decision", "UNKNOWN") if isinstance(decision_info, dict) else "UNKNOWN",
                "audit_score": audit_score,
            }
            if audit_report:
                data["audit"] = audit_report
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def _generate_audit(self) -> Optional[Dict]:
        """生成审计报告"""
        print("\nStep 6: 生成审计报告...")
        try:
            from workflow_b_audit import WorkflowBAudit, build_audit_context

            ctx = build_audit_context(
                symbol=self.code,
                name=self.name,
                date=self.date,
                akshare_data=self.akshare_data,
                factor_data=self.factor_data,
                debate_data=self.debate_data,
                dcf_data=self.dcf_data,
                financial_summary=self._audit_context.get("financial_summary", {}),
                valuation_summary=self._audit_context.get("valuation_summary", {}),
                decision=self._audit_context.get("decision", {}),
                web_search_results=self._audit_context.get("web_search_results", []),
                has_analyst_reports=self._audit_context.get("has_analyst_reports", False),
                moat_analysis=self._audit_context.get("moat_analysis", {}),
                management_analysis=self._audit_context.get("management_analysis", ""),
                red_flags=self._audit_context.get("red_flags", []),
                output_dir=self.output_dir,
            )

            auditor = WorkflowBAudit(ctx)
            audit_result = auditor.run()
            audit_md = auditor.generate_markdown(audit_result)

            # 保存审计报告
            audit_file = self.output_dir / "audit_report.md"
            with open(audit_file, 'w', encoding='utf-8') as f:
                f.write(audit_md)

            score = audit_result["reliability"]["score"]
            grade = audit_result["reliability"]["grade"]
            alerts = audit_result["summary"]
            print(f"  ✅ 审计完成 — 可靠性 {score:.1f}/100 ({grade})")
            print(f"     告警: 🔴 {alerts['critical_alerts']} | 🟡 {alerts['warning_alerts']} | 🔵 {alerts['info_alerts']}")
            print(f"  📄 审计报告: {audit_file}")

            return audit_result
        except ImportError as e:
            print(f"  ⚠️ 审计模块不可用: {e}")
            return None
        except Exception as e:
            print(f"  ⚠️ 审计生成失败: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description="Workflow B 增强版 — 单股深度分析")
    parser.add_argument("--code", type=str, required=True, help="股票代码（如 600519）")
    parser.add_argument("--name", type=str, default='', help="公司名称（可选）")

    args = parser.parse_args()

    handler = WorkflowBDeepHandler(code=args.code, name=args.name)
    handler.run()


if __name__ == "__main__":
    main()
