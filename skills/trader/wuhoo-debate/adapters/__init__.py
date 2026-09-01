# Data Adapters
# 数据适配器层

from .trendradar_adapter import TrendRadarAdapter
from .akshare_adapter import AkShareAdapter
from .fundamental_adapter import FundamentalAdapter
from .news_rss_adapter import RSSNewsAdapter
from .data_aggregator import DataAggregator

# 延迟导入（需要 requests 等额外依赖）
_web_search_available = True
try:
    from .web_search_adapter import WebSearchSentimentAdapter
except ImportError:
    _web_search_available = False
    WebSearchSentimentAdapter = None

__all__ = [
    'TrendRadarAdapter',
    'AkShareAdapter',
    'FundamentalAdapter',
    'RSSNewsAdapter',
    'DataAggregator',
    'WebSearchSentimentAdapter',
]
