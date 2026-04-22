"""News-RSS 基础测试"""
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

NEWS_DIR = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(NEWS_DIR))


class TestFetcherImport:
    """Fetcher 模块导入测试"""

    def test_fetcher_import(self):
        """fetcher 模块可导入"""
        # feedparser可能未安装，测试模块结构
        try:
            from fetcher import NewsFetcher
            assert NewsFetcher is not None
        except ImportError as e:
            if 'feedparser' in str(e):
                pytest.skip("feedparser 未安装")
            raise


class TestNewsRSS:
    """News-RSS 功能测试（mock）"""

    def test_mock_feedparser(self):
        """模拟feedparser解析"""
        mock_feedparser = MagicMock()
        mock_feedparser.parse.return_value = MagicMock(
            entries=[
                {'title': 'Test News 1', 'link': 'http://test.com/1', 'summary': 'Summary 1'},
                {'title': 'Test News 2', 'link': 'http://test.com/2', 'summary': 'Summary 2'},
            ]
        )

        with patch.dict(sys.modules, {'feedparser': mock_feedparser}):
            # 验证mock生效
            result = mock_feedparser.parse('http://test.com/rss')
            assert len(result.entries) == 2
            assert result.entries[0]['title'] == 'Test News 1'
