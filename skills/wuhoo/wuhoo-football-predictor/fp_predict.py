#!/usr/bin/env python3.11
"""
足球赛事预测系统 CLI 入口
Usage:
    python3.11 fp_predict.py --update --tournament worldcup
    python3.11 fp_predict.py --analyze --tournament worldcup
    python3.11 fp_predict.py --predict "Brazil" "Germany" --tournament worldcup
    python3.11 fp_predict.py --backtest --tournament worldcup --year 2022
    python3.11 fp_predict.py --backtest --tournament euro --year 2024
    python3.11 fp_predict.py --full --tournament worldcup --budget 100
    python3.11 fp_predict.py --list-tournaments
"""

import argparse
import sys
import json
from pathlib import Path

# 添加脚本路径
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from fetch_data import DataFetcher
from prediction_models import predict_match
from sentiment_analyzer import SentimentAnalyzer, mock_news_for_team
from backtest import Backtester


def main():
    parser = argparse.ArgumentParser(description="🏆 足球赛事预测系统")
    
    # 操作参数
    parser.add_argument("--update", action="store_true", help="更新赛事数据")
    parser.add_argument("--analyze", action="store_true", help="分析即将进行的比赛")
    parser.add_argument("--predict", nargs=2, metavar=("TEAM_A", "TEAM_B"), help="预测指定比赛")
    parser.add_argument("--backtest", action="store_true", help="回测历史赛事")
    parser.add_argument("--full", action="store_true", help="完整流程（更新+分析+预测）")
    parser.add_argument("--list-tournaments", action="store_true", help="列出支持的赛事")
    parser.add_argument("--news", type=str, metavar="TEAM", help="查看球队新闻情绪")
    
    # 通用参数
    parser.add_argument("--tournament", type=str, default="worldcup", 
                       choices=["worldcup", "euro", "copa", "asiancup"],
                       help="赛事代码 (默认: worldcup)")
    parser.add_argument("--year", type=int, default=None, help="赛事年份")
    parser.add_argument("--model", type=str, default="ensemble",
                       choices=["poisson", "elo", "factor", "ensemble"],
                       help="预测模型 (默认: ensemble)")
    parser.add_argument("--budget", type=float, default=100, help="预算金额")
    parser.add_argument("--data-dir", type=str, default=None, help="数据目录")
    
    args = parser.parse_args()
    
    # 初始化
    data_dir = args.data_dir or str(Path(__file__).parent / "data")
    fetcher = DataFetcher(data_dir)
    backtester = Backtester(data_dir)
    
    # 列出赛事
    if args.list_tournaments:
        _list_tournaments()
        return
    
    # 更新数据
    if args.update or args.full:
        _update_data(args.tournament, fetcher)
    
    # 回测
    if args.backtest:
        year = args.year or _get_default_year(args.tournament)
        backtester.backtest_tournament(args.tournament, year, args.model)
        return
    
    # 新闻情绪
    if args.news:
        _show_news(args.news)
        return
    
    # 预测指定比赛
    if args.predict:
        team_a, team_b = args.predict
        _predict_match(team_a, team_b, args.tournament, fetcher, args.model)
        return
    
    # 分析
    if args.analyze or args.full:
        _analyze_tournament(args.tournament, fetcher)
    
    # 如果没有执行任何操作
    if not any([args.update, args.analyze, args.predict, args.backtest, 
                args.full, args.list_tournaments, args.news]):
        parser.print_help()


def _list_tournaments():
    """列出支持的赛事"""
    config_path = Path(__file__).parent / "configs" / "tournaments.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print("\n🏆 支持的赛事:")
    print("=" * 60)
    for code, info in config['tournaments'].items():
        print(f"  {code:12} | {info['name_cn']:8} | {info['name']}")
        print(f"             | 最近: {info.get('latest_year', '?')}   | 下届: {info.get('next_year', '?')}")
        print("-" * 60)
    print()


def _update_data(tournament: str, fetcher: DataFetcher):
    """更新赛事数据"""
    print(f"\n📥 更新 {tournament} 数据...")
    
    if tournament == 'worldcup':
        fetcher.fetch_worldcup_history()
    elif tournament == 'euro':
        fetcher.fetch_euro_history()
    
    # 更新 Elo
    fetcher.fetch_elo_ratings()
    
    print("✅ 数据更新完成\n")


def _predict_match(team_a: str, team_b: str, tournament: str, 
                  fetcher: DataFetcher, model: str):
    """预测指定比赛"""
    print(f"\n🏆 预测: {team_a} vs {team_b}")
    print("=" * 50)
    
    # 获取 Elo
    elo_ratings = fetcher.fetch_elo_ratings()
    elo_a = elo_ratings.get(team_a, {}).get('elo', 1500)
    elo_b = elo_ratings.get(team_b, {}).get('elo', 1500)
    
    # 计算平均进球
    elo_diff = elo_a - elo_b
    goals_a = max(0.5, 1.5 + elo_diff / 200)
    goals_b = max(0.5, 1.5 - elo_diff / 200)
    
    # 新闻情绪
    analyzer = SentimentAnalyzer()
    news_a = mock_news_for_team(team_a)
    news_b = mock_news_for_team(team_b)
    sentiment_a = analyzer.analyze_news_batch(news_a)
    sentiment_b = analyzer.analyze_news_batch(news_b)
    
    # 因子
    factors = {
        'recent_form': elo_diff / 400,
        'team_strength': elo_diff / 500,
        'head_to_head': 0,
        'tournament_context': 0,
        'news_sentiment': sentiment_a['sentiment_score'] - sentiment_b['sentiment_score']
    }
    
    # 预测
    result = predict_match(team_a, team_b, elo_a, elo_b, goals_a, goals_b, factors)
    
    # 输出
    print(f"\n📊 Elo 评分:")
    print(f"  {team_a}: {elo_a}")
    print(f"  {team_b}: {elo_b}")
    print(f"  差值: {elo_diff:+.0f}")
    
    print(f"\n📰 新闻情绪:")
    print(f"  {team_a}: {sentiment_a['trend']} ({sentiment_a['sentiment_score']:+.2f})")
    print(f"  {team_b}: {sentiment_b['trend']} ({sentiment_b['sentiment_score']:+.2f})")
    
    print(f"\n🎯 预测结果 ({model.upper()}):")
    pred = result['predictions'].get(model, result['predictions']['ensemble'])
    print(f"  {team_a} 胜: {pred['win_a']:.1%}")
    print(f"  平局: {pred['draw']:.1%}")
    print(f"  {team_b} 胜: {pred['win_b']:.1%}")
    
    print(f"\n{result['recommendation']}")
    
    # 免责声明
    print("\n⚠️ 免责声明: 结果仅供娱乐参考，不保证盈利。")
    print("   足球比赛具有高度不确定性，请理性对待。\n")


def _analyze_tournament(tournament: str, fetcher: DataFetcher):
    """分析赛事"""
    print(f"\n📊 分析 {tournament}...")
    
    # 加载数据
    if tournament == 'worldcup':
        df = fetcher.fetch_worldcup_history()
    elif tournament == 'euro':
        df = fetcher.fetch_euro_history()
    
    if df.empty:
        print("❌ 未找到数据，请先运行 --update")
        return
    
    print(f"✅ 共 {len(df)} 场比赛数据")
    print("📊 使用 --predict 预测具体比赛")
    print("📊 使用 --backtest 回测历史表现")


def _show_news(team: str):
    """显示球队新闻情绪"""
    analyzer = SentimentAnalyzer()
    news = mock_news_for_team(team)
    result = analyzer.analyze_news_batch(news)
    
    print(f"\n📰 {team} 新闻情绪:")
    print("=" * 50)
    print(f"  情感得分: {result['sentiment_score']:+.2f}")
    print(f"  新闻数量: {result['num_news']}")
    print(f"  趋势: {result['trend']}")
    
    if result['injury_alerts']:
        print(f"\n⚠️ 伤停警报:")
        for alert in result['injury_alerts']:
            print(f"  - {alert}")
    
    print()


def _get_default_year(tournament: str) -> int:
    """获取默认年份"""
    if tournament == 'worldcup':
        return 2022
    elif tournament == 'euro':
        return 2024
    return 2022


if __name__ == "__main__":
    main()
