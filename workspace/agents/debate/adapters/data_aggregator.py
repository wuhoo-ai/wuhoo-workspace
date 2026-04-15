#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Aggregator - 数据聚合器（真实数据版本）

整合多个数据源，为辩论系统提供统一的数据接口。

数据优先级策略:
- P0: 真实 API 数据 (Tushare/AkShare/Futu)
- P1: 本地缓存数据
- P2: 降级数据 (明确标注，不可用于交易)

更新：2026-03-23 - 确保所有数据真实有效或明确标注降级
更新：2026-04-14 - 删除 QuantaAlpha（负荷太高已移除）+ 增加 Futu K线 → 技术指标计算
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# 加载 .env 文件（如果环境变量未设置）
def _load_env_file():
    """从 ~/.openclaw/.env 加载 API Key 等配置"""
    env_file = Path.home() / '.openclaw' / '.env'
    if not env_file.exists():
        return
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key and value and key not in os.environ:
                    os.environ[key] = value

_load_env_file()

from .trendradar_adapter import TrendRadarAdapter
from .akshare_adapter import AkShareAdapter
from .fundamental_adapter import FundamentalAdapter
from .news_rss_adapter import RSSNewsAdapter

try:
    from .web_search_adapter import WebSearchSentimentAdapter
    _WEB_SEARCH_AVAILABLE = True
except ImportError:
    _WEB_SEARCH_AVAILABLE = False
    WebSearchSentimentAdapter = None


# ============================================================
# 技术指标计算辅助函数（纯 numpy，无外部依赖）
# ============================================================

def _ema(data, period):
    """计算指数移动平均线数组"""
    import numpy as np
    result = np.zeros_like(data, dtype=float)
    multiplier = 2.0 / (period + 1)
    # 用 SMA 初始化第一个 EMA 值
    if len(data) >= period:
        result[period - 1] = np.mean(data[:period])
    else:
        result[0] = np.mean(data)
    for i in range(period if len(data) >= period else 1, len(data)):
        result[i] = (data[i] - result[i-1]) * multiplier + result[i-1]
    # 前 period-1 个值为 0，填充为第一个有效值
    first_valid = result[period - 1] if len(data) >= period else result[0]
    for i in range(period - 1 if len(data) >= period else 0):
        result[i] = first_valid
    return result


def _ema_single(data, period):
    """对一维数组计算 EMA（用于 MACD 的 DEA 线）"""
    import numpy as np
    return _ema(data, period)


class DataAggregator:
    """
    数据聚合器
    
    功能:
    - 统一接口获取所有数据
    - 数据缓存
    - 数据质量检查
    """
    
    def __init__(self):
        """初始化所有适配器"""
        self.trendradar = TrendRadarAdapter()
        self.akshare = AkShareAdapter()
        self.fundamental = FundamentalAdapter()
        self.news_rss = RSSNewsAdapter()

        # WebSearch 可选（需要 requests 等依赖）
        if _WEB_SEARCH_AVAILABLE:
            self.web_search = WebSearchSentimentAdapter()
        else:
            self.web_search = None

        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 300  # 5 分钟缓存

        # 数据质量监控
        self.data_quality_report: Dict[str, str] = {}

        # Futu 技术指标缓存（US/HK 股专用）
        self._futu_technical_cache: Dict[str, Dict] = {}
    
    def get_all_data(self, symbol: str, company_name: Optional[str] = None) -> Dict:
        """
        获取股票的所有数据
        
        Args:
            symbol: 股票代码
            company_name: 公司名称 (可选)
        
        Returns:
            综合数据字典
        """
        cache_key = symbol
        if company_name:
            cache_key = f"{symbol}_{company_name}"
        
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            # 检查缓存是否过期 (5 分钟)
            if self._is_cache_valid(cached):
                return cached["data"]
        
        # 获取各数据源（按优先级）
        # 因子评分：QuantaAlpha 已移除，使用 Futu/基本面数据生成综合评分
        factor_data = {"data_source": "deprecated", "note": "QuantaAlpha 已移除，使用基本面+技术面综合评分"}
        # 获取综合舆情数据（TrendRadar + WebSearch 加权合并）
        sentiment_data = self._get_combined_sentiment(symbol, company_name)

        # AkShare 仅支持 A 股，美股/港股使用 Futu K线计算技术指标
        is_a_share = not (symbol.upper().startswith(('US.', 'HK.')) or '.' in symbol and symbol.upper().split('.')[-1] in ('US', 'HK'))
        if is_a_share:
            technical_data = self.akshare.get_technical_data(symbol)
        else:
            technical_data = self._get_futu_technical_data(symbol)

        # 获取基本面数据（真实数据优先）
        fundamental_data = self._get_fundamental_data(symbol)

        # 获取市场数据
        market_data = self._get_market_data(symbol, technical_data, fundamental_data)

        # 记录数据质量
        self.data_quality_report[symbol] = {
            "factor": factor_data.get('data_source', 'unknown'),
            "technical": technical_data.get('data_source', 'unknown'),
            "fundamental": fundamental_data.get('data_source', 'unknown'),
            "sentiment": sentiment_data.get('source', 'unknown'),
            "sentiment_sources": sentiment_data.get('sources', []),
            "timestamp": datetime.now().isoformat()
        }

        # 数据质量检查 — Futu 真实数据也视为高质量
        tech_source = technical_data.get('data_source', '')
        fund_source = fundamental_data.get('data_source', '')
        data_quality_ok = (
            tech_source in ('tushare_real', 'futu_kline') and
            fund_source in ('real', 'futu', 'tushare', 'akshare') and
            sentiment_data.get('source') != 'none'
        )
        
        # 聚合数据
        aggregated = {
            "factor_data": factor_data,
            "technical_data": technical_data,
            "sentiment_data": sentiment_data,
            "fundamental_data": fundamental_data,
            "market_data": market_data,
            "data_quality": {
                "overall": "good" if data_quality_ok else "degraded",
                "factor": factor_data.get('data_source', 'unknown'),
                "fundamental": fundamental_data.get('data_source', 'unknown'),
                "technical": technical_data.get('data_source', 'unknown'),
                "sentiment": sentiment_data.get('source', 'unknown'),
                "warning": None if data_quality_ok else "⚠️ 部分数据源使用降级数据，决策需谨慎"
            },
            "metadata": {
                "symbol": symbol,
                "company_name": company_name,
                "timestamp": datetime.now().isoformat(),
                "data_sources": {
                    "news_rss": self.news_rss.get_status(),
                    "trendradar": self.trendradar.get_status(),
                    "akshare": self.akshare.get_status(),
                    "web_search": self.web_search.get_status() if self.web_search else {"available": False},
                    "fundamental": self.fundamental.get_status()
                }
            }
        }
        
        # 缓存
        self.cache[cache_key] = {
            "data": aggregated,
            "timestamp": datetime.now()
        }
        
        return aggregated
    
    def _get_combined_sentiment(self, symbol: str, company_name: Optional[str]) -> Dict:
        """
        获取综合舆情数据 (整合多个数据源)

        优先级:
        1. wuhoo-news-rss (企业级关键 skill，RSS 资讯内容，权重最高)
        2. TrendRadar (热搜榜单，市场基准情绪)
        3. Web Search (补充，当 API Key 配置时启用)
        """
        sentiment_sources = []

        # 源 1: wuhoo-news-rss (优先，企业级关键 skill)
        try:
            rss_sentiment = self.news_rss.get_sentiment_data(symbol, company_name)
            if rss_sentiment and rss_sentiment.get("news_count", 0) > 0:
                weight = 0.5  # RSS 资讯权重最高
                sentiment_sources.append({
                    "source": "rss_news",
                    "score": rss_sentiment["sentiment_score"],
                    "weight": weight,
                    "data": rss_sentiment
                })
                print(f"  📰 RSS 舆情: {rss_sentiment['sentiment_label']} ({rss_sentiment['news_count']} 条)")
        except Exception as e:
            print(f"RSS News 舆情获取失败: {e}")

        # 源 2: TrendRadar (热搜榜单，市场基准情绪)
        try:
            tr_sentiment = self.trendradar.get_sentiment_data(symbol, company_name)
            if tr_sentiment and tr_sentiment.get("sentiment_score") is not None:
                weight = 0.3 if sentiment_sources else 0.5
                if tr_sentiment.get("stock_news_count", 0) > 0:
                    weight = 0.4 if sentiment_sources else 0.7

                sentiment_sources.append({
                    "source": "trendradar",
                    "score": tr_sentiment["sentiment_score"],
                    "weight": weight,
                    "data": tr_sentiment
                })
        except Exception as e:
            print(f"TrendRadar 舆情获取失败: {e}")

        # 源 3: Web Search (选择性执行，仅在 API Key 配置时调用)
        if self.web_search is not None and self.web_search.primary_source in ("tavily", "jina"):
            try:
                ws_sentiment = self.web_search.get_sentiment_data(symbol, company_name or "")
                if ws_sentiment and ws_sentiment.get("sentiment_score") is not None:
                    if not sentiment_sources:
                        ws_weight = 1.0
                    else:
                        ws_weight = 0.2

                    sentiment_sources.append({
                        "source": "web_search",
                        "score": ws_sentiment["sentiment_score"],
                        "weight": ws_weight,
                        "data": ws_sentiment
                    })
            except Exception as e:
                print(f"Web Search 舆情获取失败: {e}")
        else:
            print(f"Web Search 未配置 API Key (Tavily/Jina)，跳过")

        # 如果没有有效数据源，返回中性数据
        if not sentiment_sources:
            return {
                "source": "none",
                "sentiment_score": 0.0,
                "sentiment_label": "unavailable",
                "hot_topics": [],
                "news_count": 0,
                "positive_ratio": 0,
                "negative_ratio": 0,
                "neutral_ratio": 1,
                "note": "所有舆情数据源失败或未配置 (RSS/TrendRadar/WebSearch)"
            }

        # 加权平均计算综合评分
        total_weight = sum(s["weight"] for s in sentiment_sources)
        weighted_score = sum(s["score"] * s["weight"] for s in sentiment_sources)
        combined_score = weighted_score / total_weight if total_weight > 0 else 0.0

        # 确定情感标签
        if combined_score > 0.2:
            label = "positive"
        elif combined_score < -0.2:
            label = "negative"
        else:
            label = "neutral"

        # 合并热点话题
        all_topics = []
        for s in sentiment_sources:
            topics = s["data"].get("hot_topics", [])
            if isinstance(topics, list):
                all_topics.extend(topics[:3])

        # 合并新闻数量
        total_news = sum(s["data"].get("news_count", 0) for s in sentiment_sources)

        return {
            "source": "combined",
            "sentiment_score": round(combined_score, 3),
            "sentiment_label": label,
            "positive_ratio": sum(s["data"].get("positive_ratio", 0) * s["weight"] for s in sentiment_sources) / total_weight,
            "negative_ratio": sum(s["data"].get("negative_ratio", 0) * s["weight"] for s in sentiment_sources) / total_weight,
            "news_count": total_news,
            "hot_topics": list(dict.fromkeys(all_topics))[:5],  # 去重保留顺序，前 5
            "sources": [s["source"] for s in sentiment_sources],
            "last_updated": datetime.now().isoformat()
        }
    
    def _safe_get_data(self, fetch_func, *args, default=None, **kwargs):
        """
        安全获取数据 (带降级处理)
        
        Args:
            fetch_func: 数据获取函数
            *args: 函数参数
            default: 默认值 (失败时返回)
            **kwargs: 关键字参数
        
        Returns:
            数据或默认值
        """
        try:
            result = fetch_func(*args, **kwargs)
            if result is None:
                return default if default is not None else {}
            return result
        except Exception as e:
            print(f"{fetch_func.__name__} 获取失败：{e}")
            return default if default is not None else {}
    
    def _is_cache_valid(self, cached: Dict, max_age_seconds: int = 300) -> bool:
        """检查缓存是否有效"""
        if "timestamp" not in cached:
            return False

        age = (datetime.now() - cached["timestamp"]).total_seconds()
        return age < max_age_seconds

    def _get_futu_technical_data(self, symbol: str) -> Dict:
        """
        通过 Futu K线数据计算技术指标（US/HK 股专用）

        替代 AkShare（不支持 US/HK），使用 Futu OpenAPI 获取日 K 线，
        计算 MACD、RSI、KDJ、均线、布林带等技术指标。

        Args:
            symbol: 股票代码 (如 US.NVDA, HK.00700)

        Returns:
            技术面数据字典，与 AkShare 格式兼容
        """
        # 检查缓存
        if symbol in self._futu_technical_cache:
            cached = self._futu_technical_cache[symbol]
            age = (datetime.now() - cached["timestamp"]).total_seconds()
            if age < 300:  # 5 分钟缓存
                return cached["data"]

        try:
            from futu import OpenQuoteContext, KLType, AuType, SubType
            import numpy as np

            # 统一股票代码格式: "00012.HK" -> "HK.00012"
            if '.' in symbol:
                parts = symbol.split('.')
                if parts[1].upper() in ('HK', 'US', 'SH', 'SZ'):
                    symbol = f"{parts[1].upper()}.{parts[0]}"

            host = os.environ.get('FUTU_HOST', '127.0.0.1')
            port = int(os.environ.get('FUTU_PORT', '11111'))

            quote_ctx = OpenQuoteContext(host=host, port=port)

            # 先订阅 K 线数据 (OpenD 10.2+ 要求先订阅才能获取数据)
            ret_sub, _ = quote_ctx.subscribe(symbol, [SubType.K_DAY])
            if ret_sub != 0:
                quote_ctx.close()
                return self._technical_degraded(symbol, "K 线数据订阅失败")

            # 获取最近 120 根日 K 线（OpenD 10.2+ 返回 2 个值：ret, data）
            result = quote_ctx.get_cur_kline(symbol, 120, KLType.K_DAY, AuType.QFQ)
            ret, data = result[0], result[1]
            quote_ctx.close()

            if ret != 0 or data is None or len(data) < 30:
                return self._technical_degraded(symbol, f"K 线数据不足 (ret={ret}, len={len(data) if data is not None else 0})")

            closes = data['close'].values.astype(float)
            highs = data['high'].values.astype(float)
            lows = data['low'].values.astype(float)
            volumes = data['volume'].values.astype(float)
            turnovers = data['turnover'].values.astype(float) if 'turnover' in data.columns else np.zeros(len(closes))

            current_price = closes[-1]
            prev_price = closes[-2] if len(closes) >= 2 else current_price
            change_pct = ((current_price - prev_price) / prev_price * 100) if prev_price > 0 else 0

            # === MACD (12, 26, 9) ===
            macd, signal, histogram = self._calc_macd(closes, 12, 26, 9)

            # === RSI (14 日) ===
            rsi = self._calc_rsi(closes, 14)

            # === KDJ (9, 3, 3) ===
            k, d, j = self._calc_kdj(highs, lows, closes, 9, 3, 3)

            # === 均线 ===
            ma5 = self._calc_ma(closes, 5)
            ma10 = self._calc_ma(closes, 10)
            ma20 = self._calc_ma(closes, 20)
            ma60 = self._calc_ma(closes, 60) if len(closes) >= 60 else 0

            # === 布林带 (20, 2) ===
            boll_mid, boll_upper, boll_lower = self._calc_bollinger(closes, 20, 2)

            # === 趋势判断 ===
            if ma5 > ma10 > ma20:
                trend = "uptrend"
            elif ma5 < ma10 < ma20:
                trend = "downtrend"
            else:
                trend = "sideways"

            # === 综合信号 ===
            buy_signals = 0
            sell_signals = 0

            # MACD 金叉/死叉
            if macd > signal:
                buy_signals += 1
            else:
                sell_signals += 1

            # RSI 超买/超卖
            if rsi < 30:
                buy_signals += 1  # 超卖反弹
            elif rsi > 70:
                sell_signals += 1  # 超买回调

            # KDJ 金叉
            if k > d and j > 50:
                buy_signals += 1
            elif k < d and j < 50:
                sell_signals += 1

            # 均线排列
            if ma5 > ma10 and ma10 > ma20:
                buy_signals += 1
            elif ma5 < ma10 and ma10 < ma20:
                sell_signals += 1

            if buy_signals > sell_signals + 1:
                signal_label = "buy"
            elif sell_signals > buy_signals + 1:
                signal_label = "sell"
            else:
                signal_label = "neutral"

            # 量比（当日成交量 / 5 日均量）
            avg_vol_5 = np.mean(volumes[-5:]) if len(volumes) >= 5 else np.mean(volumes)
            volume_ratio = volumes[-1] / avg_vol_5 if avg_vol_5 > 0 else 1.0

            # 换手率
            turnover_rate = data['turnover_rate'].iloc[-1] / 100 if 'turnover_rate' in data.columns and data['turnover_rate'].iloc[-1] not in [None, 0, ''] else 0.03

            result = {
                "macd": "golden_cross" if macd > signal else "death_cross",
                "macd_value": round(float(macd), 4),
                "signal_value": round(float(signal), 4),
                "macd_histogram": round(float(histogram), 4),
                "rsi": round(float(rsi), 1),
                "kdj": {
                    "k": round(float(k), 1),
                    "d": round(float(d), 1),
                    "j": round(float(j), 1),
                },
                "trend": trend,
                "signal": signal_label,
                "ma5": round(float(ma5), 2),
                "ma10": round(float(ma10), 2),
                "ma20": round(float(ma20), 2),
                "boll_upper": round(float(boll_upper), 2),
                "boll_lower": round(float(boll_lower), 2),
                "boll_position": round(float((current_price - boll_lower) / (boll_upper - boll_lower) * 100), 1) if (boll_upper - boll_lower) > 0 else 50,
                "support": round(float(ma20), 2),
                "resistance": round(float(boll_upper), 2),
                "volume_ratio": round(float(volume_ratio), 2),
                "turnover_rate": round(float(turnover_rate), 4),
                "price": round(float(current_price), 2),
                "change_pct": round(float(change_pct), 2),
                "volume": int(volumes[-1]),
                "data_quality": "real",
                "data_source": "futu_kline",
                "trade_days": len(closes),
                "last_updated": datetime.now().isoformat(),
            }

            self._futu_technical_cache[symbol] = {
                "data": result,
                "timestamp": datetime.now()
            }
            return result

        except ImportError:
            return self._technical_degraded(symbol, "futu 库未安装")
        except Exception as e:
            return self._technical_degraded(symbol, f"Futu K 线获取失败: {e}")

    @staticmethod
    def _calc_macd(closes, fast=12, slow=26, signal_period=9):
        """计算 MACD"""
        import numpy as np
        ema_fast = _ema(closes, fast)
        ema_slow = _ema(closes, slow)
        dif = ema_fast - ema_slow
        dea = _ema_single(dif, signal_period)
        histogram = 2 * (dif - dea)
        return dif[-1], dea[-1], histogram[-1]

    @staticmethod
    def _calc_rsi(closes, period=14):
        """计算 RSI"""
        import numpy as np
        if len(closes) < period + 1:
            return 50.0
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _calc_kdj(highs, lows, closes, n=9, m1=3, m2=3):
        """计算 KDJ"""
        import numpy as np
        if len(closes) < n:
            return 50.0, 50.0, 50.0
        low_list = np.array([np.min(lows[max(0, i-n+1):i+1]) for i in range(len(closes))])
        high_list = np.array([np.max(highs[max(0, i-n+1):i+1]) for i in range(len(closes))])
        rsv = np.where(high_list != low_list, (closes - low_list) / (high_list - low_list) * 100, 50.0)
        k = 50.0
        d = 50.0
        for rsv_val in rsv:
            k = k * (m1 - 1) / m1 + rsv_val / m1
            d = d * (m2 - 1) / m2 + k / m2
        j = 3 * k - 2 * d
        return k, d, j

    @staticmethod
    def _calc_ma(closes, period):
        """计算移动平均"""
        if len(closes) < period:
            return 0.0
        return float(closes[-period:].mean())

    @staticmethod
    def _calc_bollinger(closes, period=20, std_dev=2):
        """计算布林带"""
        import numpy as np
        if len(closes) < period:
            mid = np.mean(closes)
            std = np.std(closes)
        else:
            mid = np.mean(closes[-period:])
            std = np.std(closes[-period:])
        return mid, mid + std_dev * std, mid - std_dev * std

    def _technical_degraded(self, symbol: str, reason: str) -> Dict:
        """技术面降级数据（当 Futu 不可用时）"""
        return {
            "macd": "neutral",
            "macd_value": 0,
            "signal_value": 0,
            "macd_histogram": 0,
            "rsi": 50,
            "kdj": {"k": 50, "d": 50, "j": 50},
            "trend": "sideways",
            "signal": "neutral",
            "ma5": 0,
            "ma10": 0,
            "ma20": 0,
            "boll_upper": 0,
            "boll_lower": 0,
            "boll_position": 50,
            "support": 0,
            "resistance": 0,
            "volume_ratio": 1.0,
            "turnover_rate": 0.03,
            "price": 0,
            "change_pct": 0,
            "volume": 0,
            "data_quality": "degraded",
            "data_source": "degraded",
            "trade_days": 0,
            "last_updated": datetime.now().isoformat(),
            "warning": f"⚠️ 技术面降级 — {reason}",
        }

    def _get_fundamental_data(self, symbol: str) -> Dict:
        """
        获取基本面数据（真实数据优先）
        
        使用 FundamentalAdapter 按优先级获取:
        1. Tushare Pro API
        2. AkShare
        3. Qlib 本地数据
        4. 降级数据 (明确标注)
        """
        return self.fundamental.get_fundamental_data(symbol)
    
    def _get_market_data(self, symbol: str, technical_data: Dict, fundamental_data: Optional[Dict] = None) -> Dict:
        """
        获取市场数据
        
        优先级:
        1. 从 technical_data 获取真实数据
        2. 从 fundamental_data 补充
        3. 降级计算 (明确标注)
        """
        # 检查数据质量
        tech_quality = technical_data.get('data_quality', 'unknown')
        fund_quality = fundamental_data.get('data_quality', 'unknown') if fundamental_data else 'unknown'
        
        # 计算市场数据
        price = technical_data.get("price", fundamental_data.get("price", 100) if fundamental_data else 100)
        volume = technical_data.get("volume", 1000000)
        turnover_rate = technical_data.get("turnover_rate", 0.03)
        
        # 市值计算（优先使用真实数据）
        if fundamental_data and fundamental_data.get('market_cap'):
            market_cap = fundamental_data['market_cap']
        elif technical_data.get('market_cap'):
            market_cap = technical_data['market_cap']
        else:
            # 降级计算
            market_cap = price * 100000000  # 假设股本 1 亿股
        
        return {
            "volatility": turnover_rate * 10 if turnover_rate else 0.3,
            "daily_turnover": volume * price if volume and price else 0,
            "market_cap": market_cap,
            "earnings_soon": False,  # TODO: 检查财报日期
            "price": price,
            "data_quality": max(tech_quality, fund_quality) if tech_quality == fund_quality else 'mixed',
            "last_updated": datetime.now().isoformat()
        }
    
    def get_data_summary(self, symbol: str) -> Dict:
        """
        获取数据摘要 (用于快速预览)
        
        Args:
            symbol: 股票代码
        
        Returns:
            数据摘要
        """
        data = self.get_all_data(symbol)
        
        return {
            "symbol": symbol,
            "factor_score": data["factor_data"].get("momentum_score", 0),
            "sentiment_score": data["sentiment_data"].get("sentiment_score", 0),
            "technical_signal": data["technical_data"].get("signal", "unknown"),
            "trend": data["technical_data"].get("trend", "unknown"),
            "pe": data["fundamental_data"].get("pe", 0),
            "roe": data["fundamental_data"].get("roe", 0),
            "timestamp": data["metadata"]["timestamp"]
        }
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
    
    def get_status(self) -> Dict:
        """获取聚合器状态"""
        return {
            "cache_size": len(self.cache),
            "data_sources": {
                "trendradar": self.trendradar.get_status(),
                "akshare": self.akshare.get_status(),
                "futu_technical": "enabled_for_us_hk"
            }
        }


# 使用示例
if __name__ == "__main__":
    aggregator = DataAggregator()
    
    print("数据聚合器状态:")
    print(json.dumps(aggregator.get_status(), indent=2, ensure_ascii=False))
    
    print("\n获取 600519.SH 数据...")
    data = aggregator.get_all_data("600519.SH", "贵州茅台")
    
    print("\n数据摘要:")
    summary = aggregator.get_data_summary("600519.SH")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    print("\n因子数据:")
    print(json.dumps(data["factor_data"], indent=2, ensure_ascii=False))
    
    print("\n舆情数据:")
    print(json.dumps(data["sentiment_data"], indent=2, ensure_ascii=False))

