#!/usr/bin/env python3.11
"""
value_debate.py — 四大师价值投资辩论（独立运行，方案C）
基于 ai-berkshire investment-team skill 改编

4 角色独立辩论:
  - 段永平 Agent: 生意本质 + 商业模式
  - 巴菲特 Agent: 护城河 + 财务估值
  - 芒格 Agent: 逆向思考 + 风险识别
  - 李录 Agent: 长期确定性 + 文明趋势

每位 Agent 独立搜索、独立评分 (1-5)，最后综合。
与现有 wuhoo-debate (量化Bull/Bear) 并行，Trader 综合两者。

用法:
  python3.11 value_debate.py --code 600519 --market cn --name 贵州茅台
  python3.11 value_debate.py --from-quality quality_pass_us_20260629.csv
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

HOME = Path.home()
WS = HOME / "wuhoo-workspace"
DATA_DIR = WS / "data" / "value-investing"
SKILL_DIR = Path(__file__).parent
PROMPTS_DIR = SKILL_DIR / "prompts"

DATA_DIR.mkdir(parents=True, exist_ok=True)
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Master Prompts ──────────────────────────────────────

DUAN_PROMPT = """你是段永平，中国最成功的价值投资者之一。你的投资哲学核心是"对的生意、对的人、对的价格"。

请从生意本质角度分析 {name}({code})，包括：

1. **一句话定义生意本质**：这家公司到底做什么生意？靠什么赚钱？
2. **收入结构拆解**：各业务线占比和趋势
3. **商业模式可持续性**：这门生意10年后还在吗？关键变量是什么？
4. **"本分"检验**：管理层是否在做对的事情？有没有偏离主业？
5. **打分**：1-5星

输出 JSON 格式：
{{"score": 3.5, "confidence": 0.7, "recommendation": "BUY/HOLD/AVOID", 
 "key_points": ["要点1", "要点2"], "critical_question": "段永平式追问", 
 "summary": "一句话总结"}}
"""

BUFFETT_PROMPT = """你是沃伦·巴菲特，伯克希尔·哈撒韦的CEO。你的投资哲学核心是"护城河、安全边际、长期持有"。

请从护城河和估值角度分析 {name}({code})，包括：

1. **护城河逐类验证**：品牌/转换成本/网络效应/规模优势/技术壁垒
2. **护城河趋势**：过去5年变宽还是变窄？未来5年预判
3. **财务质量**：ROE、毛利率、FCF、负债水平
4. **估值判断**：当前估值相对内在价值是否有安全边际？
5. **打分**：1-5星

输出 JSON 格式：
{{"score": 3.5, "confidence": 0.7, "recommendation": "BUY/HOLD/AVOID",
 "key_points": ["要点1", "要点2"], "critical_question": "巴菲特式追问",
 "summary": "一句话总结", "moat_types": {{"brand": 0-5, "switching_cost": 0-5, 
 "network_effect": 0-5, "scale": 0-5, "tech_moat": 0-5}}}}
"""

MUNGER_PROMPT = """你是查理·芒格，巴菲特的终身搭档。你的投资哲学核心是"反过来想、总是反过来想"。

请从逆向思维角度分析 {name}({code})，包括：

1. **失败路径枚举**：列出所有可能导致这笔投资失败的情景（至少5条）
2. **每条路径概率+影响**：用概率×影响评估严重性
3. **空方核心论点**：聪明人为什么不做多/在做空？
4. **历史类比**：相似位置的公司结局如何？
5. **偏误自查**：对这家公司，我们最容易犯什么认知偏误？
6. **打分**：1-5星

输出 JSON 格式：
{{"score": 3.5, "confidence": 0.7, "recommendation": "BUY/HOLD/AVOID",
 "key_points": ["要点1", "要点2"], "failure_paths": [{{"path": "描述", "probability": "%", "impact": "高/中/低"}}],
 "worst_case_value": "最坏情景估值", "summary": "一句话总结"}}
"""

LI_LU_PROMPT = """你是李录，喜马拉雅资本的创始人。你的投资哲学核心是"长期确定性、文明演进框架"。

请从长期确定性和文明趋势角度分析 {name}({code})，包括：

1. **文明级判断**：这个赛道是"文明级范式转移"还是"阶段性热潮"？
2. **技术革命类比**：历史上最接近的技术革命类比是什么？
3. **10-20年终局**：10-20年后这家公司的终局是什么？
4. **赢家通吃判断**：这个市场是不是赢家通吃？为什么？
5. **管理层文化**：管理层和公司文化是否有长期竞争优势？
6. **打分**：1-5星

输出 JSON 格式：
{{"score": 3.5, "confidence": 0.7, "recommendation": "BUY/HOLD/AVOID",
 "key_points": ["要点1", "要点2"], "civilization_verdict": "范式转移/阶段性热潮",
 "endgame": "终局判断", "summary": "一句话总结"}}
"""


# ── Data Preparation ────────────────────────────────────

def prepare_stock_context(market, code, name):
    """Prepare data context for LLM agents."""
    context = {
        "market": market,
        "code": code,
        "name": name,
        "financial_data": {},
        "sources": []
    }
    
    if market in ('us', 'hk'):
        try:
            import yfinance as yf
            ticker = code if market == 'us' else (code[3:] + '.HK' if code.startswith('HK.') else code + '.HK')
            stock = yf.Ticker(ticker)
            info = stock.info
            
            context["financial_data"] = {
                "price": info.get('currentPrice'),
                "pe": info.get('trailingPE'),
                "forward_pe": info.get('forwardPE'),
                "pb": info.get('priceToBook'),
                "market_cap_b": round(info.get('marketCap', 0) / 1e9, 1) if info.get('marketCap') else None,
                "roe_pct": round((info.get('returnOnEquity') or 0) * 100, 1),
                "gross_margin_pct": round((info.get('grossMargins') or 0) * 100, 1),
                "net_margin_pct": round((info.get('profitMargins') or 0) * 100, 1),
                "revenue_b": round(info.get('totalRevenue', 0) / 1e9, 1) if info.get('totalRevenue') else None,
                "fcf_b": round(info.get('freeCashflow', 0) / 1e9, 1) if info.get('freeCashflow') else None,
                "debt_to_equity": info.get('debtToEquity'),
                "dividend_yield_pct": round((info.get('dividendYield') or 0) * 100, 2),
                "beta": info.get('beta'),
                "sector": info.get('sector', ''),
                "industry": info.get('industry', ''),
                "description": (info.get('longBusinessSummary') or '')[:500],
                "employees": info.get('fullTimeEmployees')
            }
            context["sources"].append("yfinance")
        except Exception as e:
            context["yfinance_error"] = str(e)
    
    return context


# ── LLM Call ────────────────────────────────────────────

def call_llm(prompt, system_prompt="", max_tokens=4000):
    """Call DeepSeek API."""
    api_key = os.environ.get('DEEPSEEK_API_KEY', '')
    if not api_key:
        return {"error": "DEEPSEEK_API_KEY not set"}
    
    import urllib.request
    
    api_base = os.environ.get('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')
    url = f"{api_base.rstrip('/')}/chat/completions"
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = json.dumps({
        "model": "deepseek-v4-pro",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    })
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            content = result['choices'][0]['message']['content']
            return {"content": content, "status": "ok"}
    except Exception as e:
        return {"error": str(e)}


def parse_json_output(content):
    """Parse JSON from LLM output, handling markdown fences."""
    # Try direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Try to extract from markdown code block
    import re
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    
    # Try to find JSON-like structure
    match = re.search(r'\{[\s\S]*\}', content)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    
    return {"error": "failed_to_parse", "raw": content[:500]}


# ── Debate Execution ────────────────────────────────────

def run_value_debate(market, code, name, context):
    """Run 4-master debate for one stock."""
    
    financial_summary = ""
    fd = context.get("financial_data", {})
    if fd:
        financial_summary = f"""
当前数据:
- 股价: {fd.get('price', 'N/A')}
- PE: {fd.get('pe', 'N/A')} (Forward: {fd.get('forward_pe', 'N/A')})
- PB: {fd.get('pb', 'N/A')}
- 市值: {fd.get('market_cap_b', 'N/A')}B
- ROE: {fd.get('roe_pct', 'N/A')}%
- 毛利率: {fd.get('gross_margin_pct', 'N/A')}%
- 净利率: {fd.get('net_margin_pct', 'N/A')}%
- 营收: {fd.get('revenue_b', 'N/A')}B
- FCF: {fd.get('fcf_b', 'N/A')}B
- 行业: {fd.get('sector', '')} / {fd.get('industry', '')}
- 业务: {fd.get('description', '')[:300]}
"""
    
    system_header = "你是一位投资大师。请基于你的投资哲学框架进行分析。只输出 JSON，不要其他内容。"
    
    # Run all 4 agents (sequentially for now)
    agents = [
        ("duan", "段永平", DUAN_PROMPT.format(name=name, code=code) + financial_summary),
        ("buffett", "巴菲特", BUFFETT_PROMPT.format(name=name, code=code) + financial_summary),
        ("munger", "芒格", MUNGER_PROMPT.format(name=name, code=code) + financial_summary),
        ("lilu", "李录", LI_LU_PROMPT.format(name=name, code=code) + financial_summary),
    ]
    
    results = {}
    for agent_key, master_name, prompt in agents:
        print(f"  🤔 {master_name} 分析中...")
        llm_result = call_llm(prompt, system_header + f"\n你是{master_name}。")
        
        if "error" in llm_result:
            results[agent_key] = {"error": llm_result["error"], "master": master_name}
            print(f"    ❌ {llm_result['error']}")
            continue
        
        parsed = parse_json_output(llm_result["content"])
        parsed["master"] = master_name
        results[agent_key] = parsed
        print(f"    ✅ {master_name}: score={parsed.get('score', '?')}, {parsed.get('recommendation', '?')}")
        
        time.sleep(1)  # Rate limit
    
    # Synthesize
    scores = []
    recommendations = []
    for agent_key, r in results.items():
        if 'score' in r and isinstance(r['score'], (int, float)):
            scores.append(float(r['score']))
        if 'recommendation' in r:
            recommendations.append(r['recommendation'])
    
    avg_score = sum(scores) / len(scores) if scores else 0
    
    # Consensus
    buy_count = recommendations.count('BUY')
    hold_count = recommendations.count('HOLD')
    avoid_count = recommendations.count('AVOID')
    
    if buy_count >= 3:
        consensus = "强烈推荐 (≥3位大师BUY)"
    elif buy_count >= 2:
        consensus = "推荐 (2位大师BUY)"
    elif hold_count >= 2:
        consensus = "中性 (多数HOLD)"
    elif avoid_count >= 3:
        consensus = "回避 (≥3位大师AVOID)"
    else:
        consensus = "分歧 (大师观点不一致)"
    
    return {
        "symbol": code,
        "name": name,
        "market": market,
        "timestamp": datetime.now().isoformat(),
        "masters": results,
        "consensus": {
            "avg_score": round(avg_score, 2),
            "buy_votes": buy_count,
            "hold_votes": hold_count,
            "avoid_votes": avoid_count,
            "verdict": consensus
        }
    }


# ── CLI ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='四大师价值投资辩论')
    parser.add_argument('--code', help='股票代码')
    parser.add_argument('--market', required=True, choices=['cn', 'hk', 'us'], help='市场')
    parser.add_argument('--name', help='股票名称')
    parser.add_argument('--from-quality', help='从质量筛选结果批量运行')
    parser.add_argument('--output-dir', help='输出目录')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir) if args.output_dir else (DATA_DIR / "debates")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    stocks = []
    
    if args.from_quality:
        csv_path = Path(args.from_quality)
        if csv_path.exists():
            import pandas as pd
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                stocks.append((row.get('market', args.market), row['code'], row.get('name', row['code'])))
    elif args.code:
        stocks.append((args.market, args.code, args.name or args.code))
    
    if not stocks:
        parser.print_help()
        sys.exit(1)
    
    all_results = []
    for market, code, name in stocks:
        print(f"\n🏛️ 价值辩论: {name} ({code}) [{market.upper()}]")
        
        context = prepare_stock_context(market, code, name)
        result = run_value_debate(market, code, name, context)
        all_results.append(result)
        
        # Save individual result
        safe_code = code.replace('.', '_').replace('/', '_')
        result_path = output_dir / f"value_debate_{market}_{safe_code}.json"
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  💾 {result_path}")
        print(f"  📊 综合: {result['consensus']['verdict']} (avg={result['consensus']['avg_score']})")
    
    # Save summary
    if len(all_results) > 1:
        summary_path = output_dir / f"value_debate_summary_{datetime.now().strftime('%Y%m%d')}.json"
        summary = {
            "date": datetime.now().strftime('%Y-%m-%d'),
            "total": len(all_results),
            "results": [{
                "symbol": r["symbol"],
                "name": r["name"],
                "consensus": r["consensus"],
                "scores": {
                    k: v.get("score", "?") for k, v in r["masters"].items() if "score" in v
                }
            } for r in all_results]
        }
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"\n📋 汇总: {summary_path}")


if __name__ == '__main__':
    main()
