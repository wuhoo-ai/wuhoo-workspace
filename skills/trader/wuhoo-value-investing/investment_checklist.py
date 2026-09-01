#!/usr/bin/env python3.11
"""
investment_checklist.py — 巴菲特价值投资买入前 Checklist
基于 ai-berkshire investment-checklist skill 改编

对单只或多只股票执行6关Checklist + 镜子测试 + 快速否决清单。
输出结构化 Markdown 报告。

用法:
  python3.11 investment_checklist.py --code 600519 --market cn --name 贵州茅台
  python3.11 investment_checklist.py --code AAPL --market us --name Apple
  python3.11 investment_checklist.py --from-result result_us_20260629.csv
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

HOME = Path.home()
WS = HOME / "wuhoo-workspace"
DATA_DIR = WS / "data" / "value-investing"
SKILL_DIR = Path(__file__).parent
STOCK_PICK_DATA = WS / "data" / "stock-pick"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Gate Definitions ────────────────────────────────────

GATES = {
    1: {
        "name": "能力圈 — 我能理解这门生意吗",
        "master": "巴菲特+段永平",
        "questions": [
            "能用一句话说清楚这家公司靠什么赚钱吗？",
            "10年后大概率还在做什么生意？",
            "哪些关键变量决定成败？",
            "对这个行业的认知是来自深度研究还是道听途说？"
        ],
        "scoring": "★★★★★: 极其简单清晰 | ★★★★☆: 清楚但需专业知识 | ★★★☆☆: 可理解但10年确定性低 | ★★☆☆☆: 业务复杂或剧变中 | ★☆☆☆☆: 完全不在能力圈",
        "hard_veto": "说不清怎么赚钱 → 直接否决"
    },
    2: {
        "name": "好生意 — 经济特征",
        "master": "巴菲特",
        "metrics": [
            ("ROE (5年均值)", ">15%优秀, >20%卓越"),
            ("毛利率", ">40%暗示定价权"),
            ("自由现金流", "持续为正、≈净利润"),
            ("资本开支强度", "轻资产优于重资产"),
            ("负债水平", "有息负债/净利润<3年")
        ],
        "scoring": "★★★★★: 全部达标 | ★★★★☆: 4项达标 | ★★★☆☆: 3项达标 | ★★☆☆☆: 2项或恶化 | ★☆☆☆☆: 多数不达标"
    },
    3: {
        "name": "护城河 — 竞争优势",
        "master": "巴菲特",
        "types": [
            "品牌/定价权（能否不损失销量提价？）",
            "转换成本（客户迁移成本多高？）",
            "网络效应（用户越多越好？）",
            "成本/规模优势（成本优势多大？）",
            "技术/专利壁垒（技术领先几年？）"
        ],
        "key_question": "如果给竞争对手100亿，能否复制这门生意？",
        "scoring": "★★★★★: 多重护城河叠加且在变宽 | ★★★★☆: 至少一条强护城河 | ★★★☆☆: 有但不够深 | ★★☆☆☆: 正在被侵蚀 | ★☆☆☆☆: 无明显护城河"
    },
    4: {
        "name": "管理层 — 人的因素",
        "master": "段永平+巴菲特",
        "checks": [
            "诚实度（承诺 vs 交付）",
            "资本配置能力（回购/分红/并购记录）",
            "股东利益导向（持股、薪酬）",
            "所有者心态（创始人 vs 职业经理人）",
            "公司治理（关联交易、商誉、审计）",
            "CEO离开后能否照常运转？"
        ],
        "scoring": "★★★★★: 创始人掌舵、配置卓越 | ★★★★☆: 优秀但有小瑕疵 | ★★★☆☆: 合格但有治理隐患 | ★★☆☆☆: 有诚信或治理问题 | ★☆☆☆☆: 严重诚信问题→硬性否决"
    },
    5: {
        "name": "安全边际 — 价格是否足够便宜",
        "master": "巴菲特+段永平",
        "metrics": [
            ("PE (TTM)", "历史分位"),
            ("前瞻PE", ""),
            ("PB", ""),
            ("股息率", ""),
            ("FCF Yield", "")
        ],
        "key_questions": [
            "三情景估值（乐观/中性/悲观）",
            "如果判断有误，在当前价格买入最多亏多少？",
            "股价腰斩你敢加仓吗？"
        ],
        "scoring": "★★★★★: 内在价值打5折以下 | ★★★★☆: 打7折 | ★★★☆☆: 合理估值 | ★★☆☆☆: 偏贵 | ★☆☆☆☆: 严重高估"
    },
    6: {
        "name": "仓位与决策纪律",
        "master": "巴菲特",
        "questions": [
            "是否因为FOMO想买？",
            "是否因为别人推荐才想买？",
            "如果停牌5年你能接受吗？",
            "买入论述能否用200字以内写清楚？"
        ]
    }
}

VETO_LIST = [
    "说不清楚这家公司怎么赚钱",
    "连续3年自由现金流为负且看不到改善",
    "管理层有诚信污点",
    "竞争优势正在被不可逆侵蚀",
    "需要靠'下一个接盘者出更高价'来赚钱（博傻）",
    "无法承受这笔投资归零的后果",
    "买入理由主要是'别人都在买'或'最近涨得好'",
    "无法用200字以内写清楚买入理由"
]


# ── Data Fetching ───────────────────────────────────────

def fetch_stock_data(market, code, name):
    """Fetch financial data for checklist."""
    try:
        import yfinance as yf
    except ImportError:
        return {"error": "yfinance not installed", "source": "none"}
    
    if market == 'cn':
        # A-share: try akshare
        try:
            import akshare as ak
            symbol = code.split('.')[0] if '.' in code else code
            info = ak.stock_individual_info_em(symbol=symbol)
            indicators = ak.stock_financial_abstract(symbol=symbol)
            # Extract key metrics
            return {
                "source": "akshare",
                "name": name,
                "market": "cn",
                "code": code,
                "raw_info": str(info)[:500] if info is not None else "N/A",
                "raw_indicators": str(indicators)[:1000] if indicators is not None else "N/A"
            }
        except ImportError:
            pass
        except Exception as e:
            pass
    
    # US/HK: yfinance
    if market == 'us':
        ticker = code
    elif market == 'hk':
        ticker = code[3:] + '.HK' if code.startswith('HK.') else code + '.HK'
    else:
        ticker = code
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            "source": "yfinance",
            "name": name,
            "market": market,
            "code": code,
            "ticker": ticker,
            "price": info.get('currentPrice') or info.get('regularMarketPrice'),
            "pe": info.get('trailingPE'),
            "forward_pe": info.get('forwardPE'),
            "pb": info.get('priceToBook'),
            "roe": (info.get('returnOnEquity') or 0) * 100,
            "gross_margin": (info.get('grossMargins') or 0) * 100,
            "net_margin": (info.get('profitMargins') or 0) * 100,
            "market_cap": info.get('marketCap'),
            "dividend_yield": (info.get('dividendYield') or 0) * 100,
            "debt_to_equity": info.get('debtToEquity'),
            "free_cashflow": info.get('freeCashflow'),
            "operating_cashflow": info.get('operatingCashflow'),
            "sector": info.get('sector', ''),
            "industry": info.get('industry', ''),
            "description": (info.get('longBusinessSummary') or '')[:500]
        }
    except Exception as e:
        return {"error": str(e), "source": "yfinance"}


# ── Checklist Execution ─────────────────────────────────

def run_checklist(market, code, name, stock_data, llm_enabled=False):
    """
    Execute 6-gate checklist.
    
    Returns structured dict for report generation.
    """
    gates_result = {}
    total_score = 0
    passed_gates = 0
    
    for gate_id in range(1, 7):
        gate_info = GATES[gate_id].copy()
        gate_result = {
            "gate_id": gate_id,
            "name": gate_info["name"],
            "master": gate_info["master"],
            "status": "pending",
            "score": 0,
            "stars": "",
            "notes": []
        }
        
        if gate_id == 1:  # 能力圈
            if stock_data.get('description'):
                gate_result["notes"].append(f"业务: {stock_data['description'][:200]}")
            gate_result["status"] = "qualitative"
            gate_result["score"] = 0
            gate_result["needs_llm"] = True
            
        elif gate_id == 2:  # 好生意
            roe = stock_data.get('roe')
            gm = stock_data.get('gross_margin')
            fcf = stock_data.get('free_cashflow')
            ocf = stock_data.get('operating_cashflow')
            dte = stock_data.get('debt_to_equity')
            
            metrics_passed = 0
            if roe and roe > 15:
                metrics_passed += 1
                gate_result["notes"].append(f"✅ ROE={roe:.1f}% (>15%)")
            elif roe:
                gate_result["notes"].append(f"❌ ROE={roe:.1f}%")
            else:
                gate_result["notes"].append("⚠️ ROE 数据缺失")
            
            if gm and gm > 40:
                metrics_passed += 1
                gate_result["notes"].append(f"✅ 毛利率={gm:.1f}% (>40%)")
            elif gm:
                gate_result["notes"].append(f"⚠️ 毛利率={gm:.1f}%")
            
            if fcf and fcf > 0:
                metrics_passed += 1
                gate_result["notes"].append(f"✅ FCF={fcf/1e9:.1f}B (正)")
            elif fcf is not None:
                gate_result["notes"].append(f"❌ FCF={fcf/1e9:.1f}B (负)")
            
            if ocf and ocf > 0:
                metrics_passed += 1
                gate_result["notes"].append(f"✅ OCF={ocf/1e9:.1f}B (正)")
            
            if dte is not None and dte < 200:
                metrics_passed += 1
                gate_result["notes"].append(f"✅ D/E={dte:.1f}%")
            elif dte is not None:
                gate_result["notes"].append(f"⚠️ D/E={dte:.1f}%")
            
            score_map = {5: 5, 4: 4, 3: 3, 2: 2, 1: 2, 0: 1}
            gate_result["score"] = score_map.get(metrics_passed, 2)
            gate_result["status"] = "scored"
            
        elif gate_id == 3:  # 护城河
            gate_result["status"] = "qualitative"
            gate_result["score"] = 0
            gate_result["needs_llm"] = True
            
        elif gate_id == 4:  # 管理层
            gate_result["status"] = "qualitative"
            gate_result["score"] = 0
            gate_result["needs_llm"] = True
            
        elif gate_id == 5:  # 安全边际
            pe = stock_data.get('pe')
            fwd_pe = stock_data.get('forward_pe')
            pb = stock_data.get('pb')
            div_yield = stock_data.get('dividend_yield')
            
            if pe:
                gate_result["notes"].append(f"PE(TTM)={pe:.1f}")
                if pe < 15:
                    gate_result["score"] = 5
                    gate_result["notes"].append("低估值区间")
                elif pe < 25:
                    gate_result["score"] = 4
                elif pe < 40:
                    gate_result["score"] = 3
                else:
                    gate_result["score"] = 2
            else:
                gate_result["score"] = 2
            gate_result["status"] = "scored"
            
        elif gate_id == 6:  # 纪律
            gate_result["status"] = "qualitative"
            gate_result["score"] = 0
            gate_result["needs_llm"] = True
        
        # Stars
        stars_map = {5: "★★★★★", 4: "★★★★☆", 3: "★★★☆☆", 2: "★★☆☆☆", 1: "★☆☆☆☆", 0: "——"}
        gate_result["stars"] = stars_map.get(gate_result["score"], "——")
        
        if gate_result["score"] >= 3:
            passed_gates += 1
        total_score += gate_result["score"]
        
        gates_result[gate_id] = gate_result
    
    # Mirror test template
    mirror_test = f"""
> "我以 __元 买入 {name}({code})，因为：
> 1. 这门生意的本质是___，我理解它；
> 2. 它的护城河是___，而且在变宽/变窄；
> 3. 管理层___，值得/不值得信赖；
> 4. 当前价格相当于内在价值的___折，有/无足够安全边际；
> 5. 即使我错了，下行风险可控/不可控，因为___。"
"""
    
    # Overall
    overall = {
        "passed_gates": passed_gates,
        "total_gates": 6,
        "total_score": total_score,
        "max_score": 30,
        "pass_pct": passed_gates / 6 * 100,
        "score_pct": total_score / 30 * 100 if total_score > 0 else 0
    }
    
    if passed_gates >= 5:
        overall["verdict"] = "✅ 通过 Checklist — 可以进入深度研究阶段"
    elif passed_gates >= 3:
        overall["verdict"] = "⚠️ 部分通过 — 存在关键争议点，需投资者自行判断"
    elif passed_gates >= 1:
        overall["verdict"] = "❌ 未通过 Checklist — 多数关卡未达标"
    else:
        overall["verdict"] = "🔴 严重不通过 — 建议回避"
    
    return {
        "stock": {"code": code, "name": name, "market": market},
        "gates": gates_result,
        "mirror_test": mirror_test,
        "veto_list": VETO_LIST,
        "overall": overall,
        "stock_data_summary": {
            "price": stock_data.get('price'),
            "pe": stock_data.get('pe'),
            "pb": stock_data.get('pb'),
            "roe": stock_data.get('roe'),
            "gross_margin": stock_data.get('gross_margin'),
            "source": stock_data.get('source')
        }
    }


# ── Report Generation ───────────────────────────────────

def generate_report(result, output_path=None):
    """Generate Markdown checklist report."""
    stock = result['stock']
    overall = result['overall']
    
    lines = []
    lines.append(f"# 巴菲特买入前 Checklist: {stock['name']} ({stock['code']})")
    lines.append(f"\n**检查日期**: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"**市场**: {stock['market'].upper()}")
    lines.append(f"\n---\n")
    
    # Data summary
    sd = result['stock_data_summary']
    lines.append("## 数据摘要\n")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    for k, v in sd.items():
        if v is not None:
            lines.append(f"| {k} | {v} |")
    lines.append("")
    
    # Gates
    lines.append(f"## 六关总览\n")
    lines.append(f"| 关卡 | 评分 | 状态 |")
    lines.append(f"|------|------|------|")
    for gate_id in range(1, 7):
        g = result['gates'][gate_id]
        status_icon = "✅" if g['score'] >= 3 else ("⚠️" if g['score'] >= 2 else "❌")
        lines.append(f"| {gate_id}. {g['name'][:20]} | {g['stars']} | {status_icon} |")
    lines.append("")
    
    # Detail per gate
    for gate_id in range(1, 7):
        g = result['gates'][gate_id]
        lines.append(f"### 第{gate_id}关: {g['name']}")
        lines.append(f"**大师**: {g['master']}")
        lines.append(f"**评分**: {g['stars']}")
        if g['notes']:
            for note in g['notes']:
                lines.append(f"- {note}")
        if g.get('needs_llm'):
            lines.append(f"  ⚠️ 此关需LLM定性分析（护城河/管理层/能力圈评估）")
        lines.append("")
    
    # Mirror test
    lines.append(f"## 镜子测试\n")
    lines.append(result['mirror_test'])
    lines.append(f"\n**5句话说不完整 = 不买。**\n")
    
    # Veto list
    lines.append(f"## 快速否决清单\n")
    for i, item in enumerate(result['veto_list'], 1):
        lines.append(f"- [ ] {item}")
    lines.append("")
    
    # Overall
    lines.append(f"## 综合结论\n")
    lines.append(f"**通过率**: {overall['passed_gates']}/{overall['total_gates']} 关")
    lines.append(f"**总分**: {overall['total_score']}/{overall['max_score']}")
    lines.append(f"\n**{overall['verdict']}**\n")
    
    report = '\n'.join(lines)
    
    if output_path:
        Path(output_path).write_text(report, encoding='utf-8')
    
    return report


# ── CLI ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='巴菲特价值投资买入前 Checklist')
    parser.add_argument('--code', help='股票代码')
    parser.add_argument('--market', choices=['cn', 'hk', 'us'], help='市场')
    parser.add_argument('--name', help='股票名称')
    parser.add_argument('--from-result', help='从选股结果CSV批量运行')
    parser.add_argument('--output-dir', help='输出目录')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir) if args.output_dir else DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    stocks = []
    
    if args.from_result:
        csv_path = Path(args.from_result)
        if not csv_path.is_absolute():
            csv_path = STOCK_PICK_DATA / "factors" / args.from_result
        if csv_path.exists():
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            for _, row in df.iterrows():
                market = args.market or 'cn'
                code = row.get('ts_code', row.get('code', ''))
                name = row.get('name', code)
                stocks.append((market, code, name))
    
    elif args.code:
        stocks.append((args.market or 'cn', args.code, args.name or args.code))
    
    if not stocks:
        parser.print_help()
        sys.exit(1)
    
    for market, code, name in stocks:
        print(f"\n🔍 检查: {name} ({code}) [{market.upper()}]")
        stock_data = fetch_stock_data(market, code, name)
        
        if 'error' in stock_data:
            print(f"  ❌ 数据获取失败: {stock_data['error']}")
            continue
        
        result = run_checklist(market, code, name, stock_data)
        
        safe_code = code.replace('.', '_').replace('/', '_')
        output_path = output_dir / f"checklist_{market}_{safe_code}_{datetime.now().strftime('%Y%m%d')}.md"
        report = generate_report(result, str(output_path))
        
        print(f"  {result['overall']['verdict']}")
        print(f"  报告: {output_path}")


if __name__ == '__main__':
    main()
