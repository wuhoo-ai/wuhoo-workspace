#!/usr/bin/env python3.11
"""
industry_funnel.py — 行业漏斗筛选
基于 ai-berkshire industry-funnel skill 改编

5 层漏斗：
  1. 全市场扫描 (30-60家) — 活跃度+涨幅+市值锚定
  2. 价值投资5条硬指标粗筛 (≤10家)
  3. 精细分析 (≤10家，每家300-500字)
  4. 四大师深度分析 (3家，每家800-1200字)
  5. 综合输出（组合表+ETF替代+行业位置+信息自评）

用法:
  python3.11 industry_funnel.py --industry "AI算力" --market us
  python3.11 industry_funnel.py --industry "新能源汽车" --market all
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

HOME = Path.home()
WS = HOME / "wuhoo-workspace"
DATA_DIR = WS / "data" / "value-investing"
SKILL_DIR = Path(__file__).parent

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Market Scanner ──────────────────────────────────────

def scan_industry(industry_name, market='us'):
    """
    Layer 1: Full market scan.
    Returns list of candidate stocks in the industry.
    
    For now: uses web_search via LLM context.
    In production: integrates with yfinance sector data.
    """
    # This is designed to be called from an LLM agent context
    # where web_search is available as a tool
    scan_plan = {
        "industry": industry_name,
        "market": market,
        "scan_criteria": {
            "A_active": f"{market.upper()} 市场近30天成交额前列",
            "B_momentum": "近30天涨幅前20 + 近90天涨幅前20的并集",
            "C_market_cap": "行业内市值前30"
        },
        "must_check_markets": [],
        "output_format": {
            "columns": ["公司名", "代码", "市场", "市值", "一句话主业", "行业占比", "入选类别(A/B/C)"]
        }
    }
    
    if market in ('all', 'us'):
        scan_plan["must_check_markets"].append("美股")
    if market in ('all', 'hk'):
        scan_plan["must_check_markets"].append("港股")
    if market in ('all', 'cn'):
        scan_plan["must_check_markets"].append("A股")
    scan_plan["must_check_markets"].append("国际市场（日韩台欧）")
    
    return scan_plan


# ── Coarse Screen ───────────────────────────────────────

def coarse_screen(candidates):
    """
    Layer 2: Apply 5 hard indicators to narrow to ≤10.
    
    Indicators:
    1. PE合理（与历史/同业对比）
    2. ROE > 15%
    3. 经营现金流为正且占净利润>70%
    4. 资产负债率 < 60%
    5. 护城河快评 ★★★ 以上
    """
    screen_config = {
        "indicators": [
            {"id": 1, "name": "PE估值合理", "standard": "与历史/同业对比合理"},
            {"id": 2, "name": "ROE", "standard": "> 15% 或近3年趋势改善"},
            {"id": 3, "name": "经营现金流", "standard": "为正且占净利润 > 70%"},
            {"id": 4, "name": "资产负债率", "standard": "< 60%（公用事业放宽至70%）"},
            {"id": 5, "name": "护城河快评", "standard": "★★★ 以上"}
        ],
        "retention_rules": {
            "5_pass": "直接保留",
            "4_pass_1_near": "保留但标黄",
            "below_4": "淘汰，注明理由"
        },
        "overflow_rule": "若保留超过12家，将护城河标准提高至 ★★★★ 再筛一次"
    }
    return screen_config


# ── Fine Analysis ───────────────────────────────────────

def fine_analysis_template():
    """Layer 3: Fine analysis template (300-500 words per stock)."""
    return {
        "template": {
            "一句话商业模式": "卖什么、卖给谁、怎么收钱",
            "财务质量": "收入/利润增速、毛利率、ROE、现金流",
            "护城河深度": "主要类型 + 具体证据 + 5年后判断",
            "主要风险(前3)": [],
            "估值快评": "当前PE/PS/EV-EBITDA、历史分位、同业对比、一句话结论",
            "进入终选3家？": "是/否 + 理由"
        },
        "selection_criteria": "不是打分排序，而是按'投资组合互补性'选择",
        "portfolio_types": [
            "高确定性低弹性（巴菲特型）— 至少1家",
            "中等确定性中等弹性（成长型）— 至少1家",
            "高弹性高风险（期权型）— 可选1家"
        ],
        "quality_rule": "找不到3家足够好的，宁可'终选2家+1家观察'，不凑数"
    }


# ── Master Deep Dive ────────────────────────────────────

def master_deep_dive_template():
    """Layer 4: Four-master deep dive template (800-1200 words per stock)."""
    return {
        "perspectives": [
            {
                "master": "段永平",
                "focus": "生意本质",
                "questions": [
                    "定义公司做什么生意",
                    "这是好生意吗？为什么？",
                    "公司的'本分'是什么？管理层是否偏离？",
                    "商业模式的'持续性'在哪？"
                ]
            },
            {
                "master": "巴菲特",
                "focus": "护城河深度",
                "questions": [
                    "五类护城河打分（1-5星），列具体证据",
                    "10年后护城河是否还在？",
                    "现在的'安全边际'在哪？"
                ]
            },
            {
                "master": "芒格",
                "focus": "风险与失败模式",
                "questions": [
                    "公司最可能怎么失败？（前3路径）",
                    "最坏情景下值多少钱？",
                    "聪明人为什么不买？",
                    "是否存在道德/合规/管理层风险？"
                ]
            },
            {
                "master": "李录",
                "focus": "文明级趋势定位",
                "questions": [
                    "赛道是'文明级范式转移'还是'阶段性热潮'？",
                    "历史上最接近的技术革命类比",
                    "10-20年后终局",
                    "是不是赢家通吃格局？"
                ]
            }
        ],
        "recommendation_format": {
            "stars": "★★★★☆",
            "type": "核心 / 卫星 / 期权 / 观察",
            "buy_range": "当前价 / 回调N% / 等待",
            "position_pct": "占该主题仓位X%",
            "monitor": "逻辑一旦反转的信号"
        }
    }


# ── Output Generation ───────────────────────────────────

def generate_funnel_report(industry_name, market, results):
    """Layer 5: Generate comprehensive funnel report."""
    lines = []
    lines.append(f"# 行业漏斗筛选: {industry_name}")
    lines.append(f"\n**筛选日期**: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"**市场范围**: {market.upper()}")
    lines.append(f"\n---\n")
    
    lines.append("## 漏斗流程\n")
    lines.append("```")
    lines.append("全市场扫描 30-60家 → 5条硬指标粗筛 ≤10家 → 精细分析 → 四大师深度 3家 → 输出")
    lines.append("```\n")
    
    lines.append("## 终选3家组合表\n")
    lines.append("| 公司 | 类型 | 推荐度 | 建议仓位 | 核心逻辑 | 关键风险 |")
    lines.append("|------|------|--------|----------|----------|----------|")
    lines.append("| 待LLM填充 | | | | | |")
    lines.append("")
    
    lines.append("## 行业级ETF替代\n")
    lines.append("| ETF | 费率 | 覆盖范围 | 备注 |")
    lines.append("|-----|------|----------|------|")
    lines.append("| 待搜索 | | | |")
    lines.append("")
    
    lines.append("## 行业位置判断\n")
    lines.append("- PE/PB 历史分位: 待分析")
    lines.append("- 行业所处阶段: 待判断（早期/扩张/成熟/衰退）")
    lines.append("")
    
    lines.append("## 信息充分度自评\n")
    lines.append("| 维度 | 评级 | 说明 |")
    lines.append("|------|------|------|")
    lines.append("| 公司财务数据 | | |")
    lines.append("| 估值数据时效性 | | |")
    lines.append("| 行业格局判断 | | |")
    lines.append("| 管理层信息 | | |")
    lines.append("")
    
    lines.append("## AI研究偏见自觉\n")
    lines.append("| 偏见 | 检查 |")
    lines.append("|------|------|")
    lines.append("| 龙头偏好 | 是否因大市值而忽略小公司？ |")
    lines.append("| 英文偏好 | 是否遗漏A/H股好公司？ |")
    lines.append("| 故事偏好 | 是否区分'AI收入占比' vs 'AI故事占比'？ |")
    lines.append("| 当下偏好 | 是否错过转型黑马？ |")
    lines.append("")
    
    lines.append("---\n")
    lines.append("*本报告由 AI 辅助生成，需结合人工判断使用。*\n")
    
    return '\n'.join(lines)


# ── CLI ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='行业漏斗筛选')
    parser.add_argument('--industry', required=True, help='行业/主题名称')
    parser.add_argument('--market', default='us', choices=['cn', 'hk', 'us', 'all'],
                       help='市场范围')
    parser.add_argument('--output-dir', help='输出目录')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir) if args.output_dir else (DATA_DIR / "reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔍 行业漏斗: {args.industry} [{args.market.upper()}]")
    
    # Generate scan plan
    scan_plan = scan_industry(args.industry, args.market)
    
    # Generate report template
    report = generate_funnel_report(args.industry, args.market, {})
    
    safe_name = args.industry.replace(' ', '_').replace('/', '_')
    output_path = output_dir / f"funnel_{safe_name}_{datetime.now().strftime('%Y%m%d')}.md"
    output_path.write_text(report, encoding='utf-8')
    
    print(f"  📄 漏斗报告: {output_path}")
    print(f"  📋 扫描计划已生成 — 需LLM执行扫描+筛选")
    
    # Output scan plan for LLM
    plan_path = output_dir / f"funnel_plan_{safe_name}_{datetime.now().strftime('%Y%m%d')}.json"
    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump({
            "industry": args.industry,
            "market": args.market,
            "scan_plan": scan_plan,
            "coarse_screen": coarse_screen([]),
            "fine_analysis": fine_analysis_template(),
            "deep_dive": master_deep_dive_template()
        }, f, ensure_ascii=False, indent=2)
    
    print(f"  📋 执行计划: {plan_path}")
    print(f"  ✅ 模板已生成 — 由 LLM Agent 执行漏斗筛选")


if __name__ == '__main__':
    main()
