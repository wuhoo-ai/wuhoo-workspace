#!/home/admin/.openclaw/workspace/agents/trade/venv-futu/bin/python3
# -*- coding: utf-8 -*-
"""
A 股多维度分析脚本 - 对选股结果进行深度分析

分析维度:
1. 因子分析 (残差波动率、换手率、动量、Beta)
2. 技术面分析 (支撑位、压力位、RSI、MACD)
3. 基本面分析 (PE、PB、ROE、营收增长)
4. 多空辩论总结
5. 投资建议生成
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# 加载环境变量
env_file = Path.home() / '.openclaw' / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key.strip() and value.strip():
                    os.environ[key.strip()] = value.strip()

# 添加路径
sys.path.insert(0, '/home/admin/.openclaw/workspace/agents/main/skills/stock-pick/venv/lib/python3.11/site-packages')

import tushare as ts

# 初始化 Tushare
token = os.environ.get('TUSHARE_TOKEN')
if token:
    ts.set_token(token)
    pro = ts.pro_api()
else:
    print("警告：TUSHARE_TOKEN 未设置")
    pro = None


def get_basic_info(ts_code):
    """获取股票基本信息"""
    try:
        df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,market,list_date')
        info = df[df['ts_code'] == ts_code]
        if len(info) > 0:
            return info.iloc[0].to_dict()
    except Exception as e:
        print(f"获取基本信息失败：{e}")
    return {}


def get_daily_basic(ts_code, start_date, end_date):
    """获取每日基本指标"""
    try:
        df = pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date,
                            fields='ts_code,trade_date,close,turnover_rate,pe,pe_ttm,pb')
        if len(df) > 0:
            latest = df.iloc[-1].to_dict()
            return {
                'close': latest.get('close', 0),
                'turnover_rate': latest.get('turnover_rate', 0),
                'pe_ttm': latest.get('pe_ttm', 0),
                'pb': latest.get('pb', 0)
            }
    except Exception as e:
        print(f"获取每日基本指标失败：{e}")
    return {}


def get_income_data(ts_code):
    """获取营收数据"""
    try:
        df = pro.income(ts_code=ts_code, start_date='20240101', end_date='20251231',
                       fields='ts_code,end_date,total_revenue,net_profit')
        if len(df) > 0:
            # 按报告期分组
            data = df.groupby('end_date')[['total_revenue', 'net_profit']].last().reset_index()
            if len(data) >= 2:
                latest = data.iloc[-1]
                prev = data.iloc[-2]
                revenue_growth = ((latest['total_revenue'] - prev['total_revenue']) / prev['total_revenue'] * 100) if prev['total_revenue'] > 0 else 0
                return {
                    'revenue': latest['total_revenue'] if 'total_revenue' in latest else 0,
                    'net_profit': latest['net_profit'] if 'net_profit' in latest else 0,
                    'revenue_growth': revenue_growth
                }
    except Exception as e:
        print(f"获取营收数据失败：{e}")
    return {}


def get_technical_indicators(ts_code, start_date, end_date):
    """计算技术指标"""
    try:
        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if len(df) < 60:
            return {}

        df = df.sort_values('trade_date').reset_index(drop=True)
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df['vol'].values

        # RSI (14 日)
        delta = np.diff(close)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = pd.Series(gain).rolling(14).mean().iloc[-1]
        avg_loss = pd.Series(loss).rolling(14).mean().iloc[-1]
        rs = avg_gain / avg_loss if avg_loss > 0 else 0
        rsi = 100 - (100 / (1 + rs))

        # MACD
        exp1 = pd.Series(close).ewm(span=12, adjust=False).mean()
        exp2 = pd.Series(close).ewm(span=26, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd = macd_line.iloc[-1]
        signal = signal_line.iloc[-1]
        macd_hist = macd - signal

        # 布林带
        sma = pd.Series(close).rolling(20).mean()
        std = pd.Series(close).rolling(20).std()
        upper = sma + 2 * std
        lower = sma - 2 * std
        current_price = close[-1]
        boll_position = (current_price - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1]) * 100 if upper.iloc[-1] > lower.iloc[-1] else 50

        # 支撑位和压力位 (最近 20 日)
        support = np.min(low[-20:])
        resistance = np.max(high[-20:])

        return {
            'rsi': round(rsi, 2),
            'macd': round(macd, 4),
            'signal': round(signal, 4),
            'macd_hist': round(macd_hist, 4),
            'boll_position': round(boll_position, 2),
            'support': round(support, 2),
            'resistance': round(resistance, 2),
            'current_price': round(current_price, 2)
        }
    except Exception as e:
        print(f"计算技术指标失败：{e}")
    return {}


def analyze_stock(stock_data, start_date, end_date):
    """单只股票完整分析"""
    ts_code = stock_data.get('ts_code', '')
    name = stock_data.get('name', '')

    print(f"\n分析：{ts_code} {name}")

    # 1. 因子数据 (来自选股结果)
    factors = {
        'residual_vol': stock_data.get('residual_vol', 0),
        'turnover_5d': stock_data.get('turnover_5d', 0),
        'momentum_5d': stock_data.get('momentum_5d', 0),
        'beta_20d': stock_data.get('beta_20d', 0),
        'momentum_10d': stock_data.get('momentum_10d', 0)
    }

    # 2. 基本面数据
    basic_info = get_basic_info(ts_code)
    daily_basic = get_daily_basic(ts_code, start_date.replace('-', ''), end_date.replace('-', ''))
    income_data = get_income_data(ts_code)

    fundamentals = {
        'industry': basic_info.get('industry', ''),
        'market': basic_info.get('market', ''),
        'pe_ttm': daily_basic.get('pe_ttm', 0),
        'pb': daily_basic.get('pb', 0),
        'revenue_growth': income_data.get('revenue_growth', 0),
        'net_profit': income_data.get('net_profit', 0)
    }

    # 3. 技术面数据
    technicals = get_technical_indicators(ts_code, start_date.replace('-', ''), end_date.replace('-', ''))

    # 4. 综合评分
    score = 5.0
    reasons = []

    # 因子评分
    if factors['residual_vol'] < 30:
        score += 1
        reasons.append("残差波动率低 (风险小)")
    if factors['turnover_5d'] > 3:
        score += 0.5
        reasons.append("换手率高 (流动性好)")
    if factors['momentum_5d'] > -5:
        score += 0.5
        reasons.append("短期动量尚可")
    if 0.8 <= factors['beta_20d'] <= 1.2:
        score += 0.5
        reasons.append("Beta 适中")

    # 技术面评分
    if technicals.get('rsi', 50) < 30:
        score += 1
        reasons.append("RSI 超卖 (可能反弹)")
    elif technicals.get('rsi', 50) > 70:
        score -= 1
        reasons.append("RSI 超买 (可能回调)")

    if technicals.get('macd_hist', 0) > 0:
        score += 0.5
        reasons.append("MACD 金叉")
    else:
        score -= 0.5
        reasons.append("MACD 死叉")

    # 基本面评分
    pe_ttm = fundamentals.get('pe_ttm')
    if pe_ttm is not None and pe_ttm > 0 and pe_ttm < 20:
        score += 1
        reasons.append("PE 估值较低")
    elif pe_ttm is not None and pe_ttm > 50:
        score -= 1
        reasons.append("PE 估值较高")

    revenue_growth = fundamentals.get('revenue_growth', 0)
    if revenue_growth and revenue_growth > 10:
        score += 1
        reasons.append("营收增长良好")
    elif revenue_growth and revenue_growth < 0:
        score -= 0.5
        reasons.append("营收下滑")

    score = min(max(score, 0), 10)

    # 投资建议
    if score >= 8:
        recommendation = "强烈推荐买入"
        action = "STRONG_BUY"
    elif score >= 7:
        recommendation = "建议买入"
        action = "BUY"
    elif score >= 5:
        recommendation = "持有观望"
        action = "HOLD"
    elif score >= 3:
        recommendation = "建议减持"
        action = "REDUCE"
    else:
        recommendation = "强烈建议卖出"
        action = "SELL"

    return {
        'ts_code': ts_code,
        'name': name,
        'factors': factors,
        'fundamentals': fundamentals,
        'technicals': technicals,
        'score': round(score, 2),
        'recommendation': recommendation,
        'action': action,
        'reasons': reasons,
        'timestamp': datetime.now().isoformat()
    }


def generate_debate_summary(analysis_results):
    """生成多空辩论总结"""
    print("\n" + "=" * 60)
    print("多空辩论总结")
    print("=" * 60)

    for result in analysis_results:
        print(f"\n{result['ts_code']} {result['name']}:")
        print(f"  综合评分：{result['score']}/10")
        print(f"  投资建议：{result['recommendation']}")
        print(f"  看多理由:")
        for reason in result['reasons'][:5]:
            print(f"    + {reason}")
        print(f"  关键指标:")
        print(f"    - 残差波动率：{result['factors']['residual_vol']:.2f}%")
        print(f"    - 5 日换手率：{result['factors']['turnover_5d']:.2f}%")
        print(f"    - 10 日动量：{result['factors']['momentum_10d']:.2f}%")
        if result['technicals']:
            print(f"    - RSI: {result['technicals'].get('rsi', 'N/A')}")
            print(f"    - 支撑位：{result['technicals'].get('support', 'N/A')}")
            print(f"    - 压力位：{result['technicals'].get('resistance', 'N/A')}")


def main():
    # 读取选股结果
    result_file = Path('/home/admin/.openclaw/workspace/agents/main/data/stock-pick/factors/result_cn_20260401.csv')
    if not result_file.exists():
        print("选股结果文件不存在")
        return

    df = pd.read_csv(result_file)
    stocks = df.to_dict('records')

    print("=" * 60)
    print("A 股多维度分析")
    print("=" * 60)
    print(f"分析股票数量：{len(stocks)}")

    # 分析每只股票
    analysis_results = []
    start_date = '2026-03-01'
    end_date = '2026-04-01'

    for stock in stocks:
        result = analyze_stock(stock, start_date, end_date)
        analysis_results.append(result)

    # 生成辩论总结
    generate_debate_summary(analysis_results)

    # 保存结果
    output_dir = Path('/home/admin/.openclaw/workspace/agents/trade/data/workflow_c/CN_2026-04-01')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存分析结果
    with open(output_dir / '02_analysis_results.json', 'w', encoding='utf-8') as f:
        json.dump({'analysis_results': analysis_results, 'date': '2026-04-01', 'market': 'CN'}, f, ensure_ascii=False, indent=2)

    # 生成投资建议
    recommendations = []
    for result in analysis_results:
        if result['action'] in ['BUY', 'STRONG_BUY']:
            rec = {
                'code': result['ts_code'],
                'name': result['name'],
                'action': 'BUY',
                'confidence': result['score'] / 10,
                'reason': ', '.join(result['reasons'][:3]),
                'score': result['score'],
                'timestamp': datetime.now().isoformat()
            }
            recommendations.append(rec)

    with open(output_dir / '04_recommendations.json', 'w', encoding='utf-8') as f:
        json.dump({'recommendations': recommendations, 'count': len(recommendations)}, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("分析完成")
    print("=" * 60)
    print(f"结果已保存到：{output_dir}")
    print(f"推荐买入数量：{len(recommendations)}")

    for rec in recommendations:
        print(f"  - {rec['code']} {rec['name']} (评分：{rec['score']})")


if __name__ == '__main__':
    main()
