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
        """fetcher 模块可导入 (函数式架构: fetch_all/main 为入口)"""
        # feedparser可能未安装，测试模块结构
        try:
            from fetcher import fetch_all, main
            assert callable(fetch_all) and callable(main)
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


class TestInsertArticleCounting20260910:
    """2026-09-10 修复: insert_article 用 conn.total_changes > 0 判断新文章,
    但该值是连接累计值 — 首条插入后所有重复也返回 True, fetch 统计虚高
    (实测某次 fetch 报 '新增 1407' 而实际插入仅 26)。修复: before/after 快照对比。"""

    def _article(self, h, title='T'):
        return {'feed_name': 'X', 'source_url': 'u', 'title': title, 'summary': '', 'content': '',
                'link': 'l-' + h, 'author': '', 'pub_date': None, 'category': 'c', 'tags': [],
                'hash': h, 'hot_score': 0, 'is_alert': 0, 'alert_keywords': ''}

    def test_dup_after_first_insert_counts_false(self, tmp_path):
        from fetcher import init_db, insert_article
        conn = init_db(str(tmp_path / 't.db'))
        try:
            assert insert_article(conn, self._article('h1')) is True   # 首条新文章
            assert insert_article(conn, self._article('h1')) is False  # 同 hash 重复 (修复前误报 True)
            assert insert_article(conn, self._article('h2')) is True   # 另一条新文章
            assert insert_article(conn, self._article('h2')) is False  # 再次重复
        finally:
            conn.close()
