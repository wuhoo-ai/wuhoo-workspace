#!/usr/bin/env python3.11
"""
report_audit.py — 研究报告数据抽检工具
Adapted from ai-berkshire/tools/report_audit.py

功能：
  extract   从报告中提取15%数据点，生成抽检清单
  verdict   校验抽检结果，输出准出/打回判决
"""

import argparse
import json
import random
import re
import sys
from datetime import datetime
from pathlib import Path

# ── extract ─────────────────────────────────────────────

def extract_data_points(report_text, sample_rate=0.15):
    """
    从报告文本中提取可抽检的数值数据点。
    识别模式：数字后跟单位（亿、万、%、x、倍等）
    
    Returns:
        list of {context, value, unit, line_number}
    """
    patterns = [
        # 数字+单位模式
        (r'(\d+[\d,.]*)\s*(亿|万|%|x|倍|元|港元|美元|港币|人民币)', 'numeric'),
        # PE/PB/ROE 模式
        (r'(PE|PB|ROE|毛利率|净利率|增速|增长率)[：:]\s*([\d.]+%?)', 'ratio'),
        # 市值模式
        (r'市值[：:]\s*(\d+[\d,.]*)\s*(亿|万)', 'market_cap'),
    ]
    
    candidates = []
    for line_no, line in enumerate(report_text.split('\n'), 1):
        for pattern, ptype in patterns:
            matches = re.findall(pattern, line)
            for m in matches:
                if ptype == 'numeric' and len(m) >= 2:
                    candidates.append({
                        'context': line.strip()[:100],
                        'raw_value': m[0],
                        'unit': m[1],
                        'line_number': line_no,
                        'type': ptype
                    })
                elif ptype == 'ratio' and len(m) >= 2:
                    candidates.append({
                        'context': line.strip()[:100],
                        'raw_value': m[1],
                        'unit': '%' if '%' in m[1] else '',
                        'line_number': line_no,
                        'type': ptype,
                        'metric': m[0]
                    })
                elif ptype == 'market_cap' and len(m) >= 2:
                    candidates.append({
                        'context': line.strip()[:100],
                        'raw_value': m[0],
                        'unit': m[1],
                        'line_number': line_no,
                        'type': ptype
                    })
    
    # 15% 随机抽样（至少5个，最多20个）
    sample_size = max(5, min(20, int(len(candidates) * sample_rate)))
    if len(candidates) <= sample_size:
        sampled = candidates
    else:
        random.seed(42)
        sampled = random.sample(candidates, sample_size)
    
    checklist = []
    for item in sampled:
        checklist.append({
            'context': item['context'],
            'reported_value': item['raw_value'],
            'unit': item['unit'],
            'line_number': item['line_number'],
            'type': item.get('type', 'numeric'),
            'metric': item.get('metric', ''),
            'fetched_value': '',       # 待填：从信源获取的值
            'fetched_source': '',      # 待填：数据来源
            'fetched_value2': '',      # 待填：第二来源值
            'fetched_source2': '',     # 待填：第二来源
            'status': 'pending'        # pending / pass / fail
        })
    
    return {
        'extract_time': datetime.now().isoformat(),
        'total_candidates': len(candidates),
        'sample_size': len(checklist),
        'sample_rate_pct': round(sample_size / max(len(candidates), 1) * 100, 1),
        'checklist': checklist
    }


# ── verdict ─────────────────────────────────────────────

def calculate_verdict(checklist, report_name=''):
    """
    计算抽检判决。
    
    偏差 ≤1% → pass
    偏差 1-5% → warn
    偏差 >5% → fail
    
    Returns:
        verdict: '准出' or '打回'
    """
    passed = 0
    warned = 0
    failed = 0
    
    for item in checklist:
        try:
            reported = float(item['reported_value'].replace(',', '').replace('亿', '').replace('万', ''))
            fetched = float(item.get('fetched_value', '0').replace(',', '') or '0')
        except (ValueError, TypeError):
            item['status'] = 'skip'
            item['error'] = '无法解析数值'
            continue
        
        if fetched == 0:
            item['status'] = 'skip'
            item['error'] = '获取值为0或空'
            continue
        
        deviation = abs(reported - fetched) / abs(fetched) * 100 if fetched != 0 else 999
        
        item['deviation_pct'] = round(deviation, 2)
        item['fetched_value'] = str(fetched)
        
        if deviation <= 1:
            item['status'] = 'pass'
            passed += 1
        elif deviation <= 5:
            item['status'] = 'warn'
            warned += 1
        else:
            item['status'] = 'fail'
            failed += 1
    
    total_checked = passed + warned + failed
    if total_checked == 0:
        verdict = 'unchecked'
        verdict_cn = '⚪ 无有效抽检点'
    elif failed == 0:
        verdict = 'pass'
        verdict_cn = '✅ 准出 — 所有抽检点偏差 ≤5%'
    else:
        verdict = 'fail'
        verdict_cn = '❌ 打回 — 存在偏差 >5% 的数据点，需修正后重新抽检'
    
    return {
        'report': report_name,
        'verdict': verdict,
        'verdict_cn': verdict_cn,
        'audit_time': datetime.now().isoformat(),
        'summary': {
            'total_checked': total_checked,
            'passed': passed,
            'warned': warned,
            'failed': failed,
            'pass_rate_pct': round(passed / max(total_checked, 1) * 100, 1)
        },
        'details': checklist
    }


# ── CLI ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='研究报告数据抽检工具')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    p_extract = subparsers.add_parser('extract', help='从报告提取抽检清单')
    p_extract.add_argument('--report', required=True, help='报告文件路径')
    p_extract.add_argument('--output', help='输出 JSON 路径（默认 stdout）')
    p_extract.add_argument('--sample-rate', type=float, default=0.15, 
                           help='抽样比例（默认 0.15）')
    
    p_verdict = subparsers.add_parser('verdict', help='校验抽检结果')
    p_verdict.add_argument('--results', required=True, 
                           help='填好 fetched_value 的 JSON 字符串')
    p_verdict.add_argument('--report', default='', help='报告文件名')
    
    args = parser.parse_args()
    
    if args.command == 'extract':
        report_path = Path(args.report)
        if not report_path.exists():
            print(json.dumps({"error": f"文件不存在: {args.report}"}, ensure_ascii=False))
            sys.exit(1)
        
        with open(report_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        result = extract_data_points(text, args.sample_rate)
        
        output = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).write_text(output, encoding='utf-8')
            print(f"抽检清单已写入: {args.output}")
        else:
            print(output)
    
    elif args.command == 'verdict':
        try:
            checklist = json.loads(args.results)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"JSON 解析失败: {e}"}, ensure_ascii=False))
            sys.exit(1)
        
        if isinstance(checklist, list):
            pass  # raw checklist
        elif isinstance(checklist, dict) and 'checklist' in checklist:
            checklist = checklist['checklist']
        
        result = calculate_verdict(checklist, args.report)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
