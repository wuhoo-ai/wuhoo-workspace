#!/usr/bin/env python3.11
"""
value_deep_analysis.py — 四大师价值投资深度分析
基于 ai-berkshire investment-research skill 改编

7 模块顺序分析：
  0. 数据收集 + 信息丰富度评级 (A/B/C)
  1. 生意本质 — 段永平
  2. 护城河评估 — 巴菲特
  3. 逆向思考 — 芒格
  4. 管理层评估 — 段+巴
  5. 文明趋势 — 李录
  6. 估值与安全边际 — 巴+段
  7. 综合决策备忘录

用法:
  python3.11 value_deep_analysis.py --code 600519 --market cn --name 贵州茅台
  python3.11 value_deep_analysis.py --code AAPL --market us --name Apple
  python3.11 value_deep_analysis.py --from-checklist checklist_us_AAPL_20260629.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

HOME = Path.home()
WS = HOME / "wuhoo-workspace"
DATA_DIR = WS / "data" / "value-investing"
SKILL_DIR = Path(__file__).parent
TOOLS_DIR = SKILL_DIR / "tools"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Data Collection ─────────────────────────────────────

def collect_financial_data(market, code):
    """Collect financial data from available sources."""
    data = {"market": market, "code": code, "sources": []}
    
    # yfinance (US + HK)
    if market in ('us', 'hk'):
        try:
            import yfinance as yf
            ticker = code if market == 'us' else (code[3:] + '.HK' if code.startswith('HK.') else code + '.HK')
            stock = yf.Ticker(ticker)
            info = stock.info
            
            data['yfinance'] = {
                'price': info.get('currentPrice'),
                'pe': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'pb': info.get('priceToBook'),
                'market_cap': info.get('marketCap'),
                'roe': (info.get('returnOnEquity') or 0) * 100,
                'gross_margin': (info.get('grossMargins') or 0) * 100,
                'net_margin': (info.get('profitMargins') or 0) * 100,
                'fcf': info.get('freeCashflow'),
                'ocf': info.get('operatingCashflow'),
                'revenue': info.get('totalRevenue'),
                'debt_to_equity': info.get('debtToEquity'),
                'dividend_yield': (info.get('dividendYield') or 0) * 100,
                'beta': info.get('beta'),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'description': info.get('longBusinessSummary', ''),
                'employees': info.get('fullTimeEmployees'),
                'website': info.get('website', '')
            }
            data['sources'].append('yfinance')
        except Exception as e:
            data['yfinance_error'] = str(e)
    
    # akshare (CN)
    if market == 'cn':
        try:
            import akshare as ak
            symbol = code.split('.')[0] if '.' in code else code
            data['akshare'] = {"symbol": symbol}
            data['sources'].append('akshare')
        except ImportError:
            data['akshare_error'] = 'akshare not installed'
    
    # Use financial_rigor for calculations
    yf_data = data.get('yfinance', {})
    if yf_data.get('price') and yf_data.get('market_cap'):
        try:
            # Run financial_rigor tools
            pass
        except:
            pass
    
    # Information richness rating
    source_count = len(data['sources'])
    has_financials = any(k in data for k in ('yfinance', 'akshare'))
    
    if source_count >= 2 and has_financials:
        data['info_richness'] = 'A'
        data['info_richness_note'] = '信息充裕（多年财务数据+多源验证）'
    elif source_count >= 1 and has_financials:
        data['info_richness'] = 'B'
        data['info_richness_note'] = '信息适中（单一数据源，推算指标需标注置信度）'
    else:
        data['info_richness'] = 'C'
        data['info_richness_note'] = '信息稀缺（刚上市/冷门/数据有限，需用第一性原理提问）'
    
    return data


# ── LLM Integration ─────────────────────────────────────

def get_llm_config():
    """Get LLM API config from environment."""
    api_key = os.environ.get('DEEPSEEK_API_KEY', '')
    api_base = os.environ.get('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')
    return {
        'api_key': api_key,
        'api_base': api_base,
        'model': 'deepseek-v4-pro',
        'provider': 'openai'
    }


# ── Report Generation ───────────────────────────────────

def generate_analysis_report(market, code, name, data, checklist_result=None):
    """
    Generate the 7-module value investing analysis report.
    This function builds a structured dictionary that can be rendered
    to markdown or used to feed LLM prompts.
    """
    yf = data.get('yfinance', {})
    
    report = {
        "meta": {
            "code": code,
            "name": name,
            "market": market,
            "date": datetime.now().strftime('%Y-%m-%d'),
            "info_richness": data.get('info_richness', 'B'),
            "info_richness_note": data.get('info_richness_note', '')
        },
        "modules": {}
    }
    
    # Module 1: 生意本质 (段永平)
    report["modules"]["business_essence"] = {
        "master": "段永平",
        "title": "生意本质分析 — 对的生意",
        "data": {
            "description": yf.get('description', '')[:500],
            "sector": yf.get('sector', ''),
            "industry": yf.get('industry', ''),
            "revenue": yf.get('revenue'),
            "gross_margin": yf.get('gross_margin'),
            "employees": yf.get('employees')
        },
        "prompt_questions": [
            "一句话定义这家公司的生意本质",
            "收入结构拆解（各业务线占比和趋势）",
            "5年盈利能力趋势（毛利率/净利率/ROE）",
            "商业模式画布（客户/价值主张/渠道/收入来源/核心资源/关键活动/成本结构）",
            "客户粘性和生态锁定程度",
            "段永平追问：如果股市关闭5年，你愿意以当前价格持有吗？"
        ]
    }
    
    # Module 2: 护城河 (巴菲特)
    report["modules"]["moat"] = {
        "master": "巴菲特",
        "title": "经济护城河评估",
        "data": {
            "sector": yf.get('sector', ''),
            "gross_margin": yf.get('gross_margin'),
            "net_margin": yf.get('net_margin'),
            "roe": yf.get('roe')
        },
        "moat_types": [
            {"type": "品牌/定价权", "test": "能否不损失销量提价？"},
            {"type": "转换成本", "test": "客户迁移成本多高？"},
            {"type": "网络效应", "test": "用户越多越好？"},
            {"type": "成本/规模优势", "test": "成本优势多大？"},
            {"type": "技术/专利壁垒", "test": "技术领先几年？"}
        ],
        "key_questions": [
            "过去5年护城河变宽还是变窄？",
            "未来5年预判",
            "巴菲特追问：10年后护城河还在吗？什么能摧毁它？"
        ]
    }
    
    # Module 3: 逆向思考 (芒格)
    report["modules"]["inversion"] = {
        "master": "芒格",
        "title": "逆向思考与风险清单",
        "prompt": "列出所有可能失败的情景路径，每条给出概率和影响程度",
        "key_questions": [
            "我最可能在哪里犯错？",
            "聪明人为什么不买/做空？",
            "历史类比：相似位置的公司结局如何？",
            "偏误自查：叙事偏差、锚定效应、确认偏误"
        ]
    }
    
    # Module 4: 管理层 (段+巴)
    report["modules"]["management"] = {
        "master": "段永平+巴菲特",
        "title": "管理层评估 — 对的人",
        "checks": [
            "CEO/创始人关键决策复盘",
            "资本配置能力（研发回报、并购成功率、回购时机）",
            "股东利益一致性（持股比例、薪酬结构、减持历史）",
            "组织能力（团队稳定性、中层质量）",
            "企业文化和价值观"
        ],
        "key_question": "段永平追问：CEO退休后公司还能保持竞争力吗？"
    }
    
    # Module 5: 文明趋势 (李录)
    report["modules"]["civilization"] = {
        "master": "李录",
        "title": "行业与文明趋势定位",
        "prompt": "判断是否处于'文明级范式转移'",
        "key_questions": [
            "这是文明级范式转移还是阶段性热潮？",
            "历史上最接近的技术革命类比",
            "10-20年后这家公司的终局",
            "是不是赢家通吃格局？",
            "TAM增长曲线与天花板"
        ]
    }
    
    # Module 6: 估值 (巴+段)
    report["modules"]["valuation"] = {
        "master": "巴菲特+段永平",
        "title": "估值与安全边际",
        "data": {
            "price": yf.get('price'),
            "pe": yf.get('pe'),
            "forward_pe": yf.get('forward_pe'),
            "pb": yf.get('pb'),
            "market_cap": yf.get('market_cap'),
            "fcf": yf.get('fcf'),
            "dividend_yield": yf.get('dividend_yield')
        },
        "calculations": {
            "fcf_yield": None,
            "reverse_dcf": None,
            "three_scenario": None
        },
        "key_questions": [
            "当前市场定价 — 必须工具验算",
            "反向DCF：当前股价隐含什么增长预期？",
            "三情景估值（乐观/中性/悲观）",
            "相对估值：与自身历史、同业对比",
            "段永平追问：股市关闭5年你愿意以这个价格持有吗？"
        ]
    }
    
    # Run financial_rigor calculations if data available
    price = yf.get('price')
    if price and yf.get('pe'):
        eps = price / yf['pe'] if yf['pe'] > 0 else None
        if eps:
            try:
                report["modules"]["valuation"]["calculations"]["fcf_yield"] = (
                    yf.get('fcf', 0) / (yf.get('market_cap', 1) or 1) * 100
                )
            except:
                pass
    
    # Module 7: 综合决策
    report["modules"]["decision"] = {
        "master": "四位大师综合",
        "title": "综合决策备忘录",
        "decision_matrix": [
            {"dimension": "生意质量（段永平）", "conclusion": "", "confidence": ""},
            {"dimension": "护城河（巴菲特）", "conclusion": "", "confidence": ""},
            {"dimension": "管理层（段+巴）", "conclusion": "", "confidence": ""},
            {"dimension": "最大风险（芒格）", "conclusion": "", "confidence": ""},
            {"dimension": "文明趋势（李录）", "conclusion": "", "confidence": ""},
            {"dimension": "估值（巴+段）", "conclusion": "", "confidence": ""},
        ],
        "final_decision": {
            "action": "",  # 买入/观望/回避
            "price_range": "",
            "position_advice": "",
            "stop_loss": ""
        }
    }
    
    # Merge checklist result if available
    if checklist_result:
        report["checklist_summary"] = {
            "passed": checklist_result.get("overall", {}).get("passed_gates", 0),
            "total": 6,
            "verdict": checklist_result.get("overall", {}).get("verdict", "")
        }
    
    return report


def render_report_markdown(report, output_path=None):
    """Render the analysis report to markdown."""
    meta = report['meta']
    modules = report['modules']
    
    lines = []
    lines.append(f"# {meta['name']} ({meta['code']}) — 四大师价值投资深度分析")
    lines.append(f"\n**分析日期**: {meta['date']}")
    lines.append(f"**市场**: {meta['market'].upper()}")
    lines.append(f"**信息丰富度**: {meta['info_richness']}级 — {meta['info_richness_note']}")
    lines.append(f"\n> *\"Price is what you pay, value is what you get.\" — Warren Buffett*")
    lines.append(f"\n---\n")
    
    # AI limitations
    lines.append("## ⚠️ AI 研究局限性声明\n")
    lines.append(f"- 本报告由 AI 辅助生成，信息丰富度评级为 **{meta['info_richness']}级**")
    lines.append("- 所有推算指标需人工核实，不可直接作为投资依据")
    lines.append("- C级信息需补充一手验证（管理层访谈、实地调研）\n")
    
    # Checklist summary
    if 'checklist_summary' in report:
        cs = report['checklist_summary']
        lines.append(f"## Checklist 快速结论\n")
        lines.append(f"- {cs['verdict']}")
        lines.append(f"- {cs['passed']}/{cs['total']} 关通过\n")
    
    # Module details
    for mod_key in ['business_essence', 'moat', 'inversion', 'management', 'civilization', 'valuation', 'decision']:
        mod = modules.get(mod_key, {})
        lines.append(f"## {mod.get('title', mod_key)}\n")
        lines.append(f"**分析框架**: {mod.get('master', '')}\n")
        
        if mod_key == 'business_essence':
            d = mod.get('data', {})
            if d.get('description'):
                lines.append(f"**业务描述**: {d['description'][:300]}")
            if d.get('sector'):
                lines.append(f"- 行业: {d['sector']} / {d.get('industry', '')}")
            if d.get('gross_margin'):
                lines.append(f"- 毛利率: {d['gross_margin']:.1f}%")
            if d.get('revenue'):
                lines.append(f"- 营收: ${d['revenue']/1e9:.1f}B")
            lines.append("")
            lines.append("### 段永平式追问\n")
            for q in mod.get('prompt_questions', [])[:3]:
                lines.append(f"- {q}")
        
        elif mod_key == 'moat':
            lines.append("### 护城河逐类验证\n")
            for mt in mod.get('moat_types', []):
                lines.append(f"| {mt['type']} | | {mt['test']} |")
            lines.append("")
            for q in mod.get('key_questions', []):
                lines.append(f"- {q}")
        
        elif mod_key == 'valuation':
            d = mod.get('data', {})
            if d.get('price'):
                lines.append(f"| 指标 | 数值 |")
                lines.append(f"|------|------|")
                for k, v in d.items():
                    if v is not None:
                        lines.append(f"| {k} | {v} |")
            calc = mod.get('calculations', {})
            if calc.get('fcf_yield'):
                lines.append(f"\n- FCF Yield: {calc['fcf_yield']:.1f}%")
            for q in mod.get('key_questions', []):
                lines.append(f"- {q}")
        
        elif mod_key == 'decision':
            lines.append("### 综合评分矩阵\n")
            lines.append("| 维度 | 结论 | 信心度 |")
            lines.append("|------|------|--------|")
            for dm in mod.get('decision_matrix', []):
                lines.append(f"| {dm['dimension']} | {dm['conclusion'] or '待分析'} | {dm['confidence'] or '——'} |")
            lines.append("")
            fd = mod.get('final_decision', {})
            lines.append(f"**最终决策**: {fd.get('action', '待定')}")
            lines.append(f"**价格区间**: {fd.get('price_range', '待定')}")
            lines.append(f"**仓位建议**: {fd.get('position_advice', '待定')}")
        
        lines.append("")
    
    # Data audit section
    lines.append("---\n")
    lines.append("## 数据抽检记录\n")
    lines.append("> 使用 `report_audit.py extract --report <本报告>` 抽取15%数据点交叉验证\n")
    
    report_text = '\n'.join(lines)
    
    if output_path:
        Path(output_path).write_text(report_text, encoding='utf-8')
    
    return report_text


# ── CLI ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='四大师价值投资深度分析')
    parser.add_argument('--code', required=True, help='股票代码')
    parser.add_argument('--market', required=True, choices=['cn', 'hk', 'us'], help='市场')
    parser.add_argument('--name', help='股票名称')
    parser.add_argument('--from-checklist', help='从checklist JSON加载')
    parser.add_argument('--output-dir', help='输出目录')
    
    args = parser.parse_args()
    
    name = args.name or args.code
    output_dir = Path(args.output_dir) if args.output_dir else (DATA_DIR / "reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📊 四大师深度分析: {name} ({args.code}) [{args.market.upper()}]")
    
    # Collect data
    print("  收集财务数据...")
    data = collect_financial_data(args.market, args.code)
    print(f"  信息丰富度: {data['info_richness']}级")
    
    # Load checklist if available
    checklist = None
    if args.from_checklist:
        with open(args.from_checklist) as f:
            checklist = json.load(f)
    
    # Generate report
    report = generate_analysis_report(args.market, args.code, name, data, checklist)
    
    # Render
    safe_code = args.code.replace('.', '_').replace('/', '_')
    output_path = output_dir / f"value_deep_{args.market}_{safe_code}_{datetime.now().strftime('%Y%m%d')}.md"
    render_report_markdown(report, str(output_path))
    
    # Also save JSON
    json_path = output_dir / f"value_deep_{args.market}_{safe_code}_{datetime.now().strftime('%Y%m%d')}.json"
    # Simplify for JSON
    json_report = {
        "meta": report["meta"],
        "checklist_summary": report.get("checklist_summary"),
        "module_keys": list(report["modules"].keys())
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_report, f, ensure_ascii=False, indent=2)
    
    print(f"  报告: {output_path}")
    print(f"  JSON: {json_path}")
    print(f"  ✅ 分析完成")


if __name__ == '__main__':
    main()
