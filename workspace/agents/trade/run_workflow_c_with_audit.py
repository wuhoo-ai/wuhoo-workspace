#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow C Runner - 执行分析 + 推送钉钉

功能:
1. 执行 Workflow C 全链路分析 (选股 → 多维度 → 辩论 → 推荐 → 审计)
2. 生成审计报告
3. 推送摘要到钉钉
4. 推送审计文件和报告作为附件
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

# 路径
DEBATE_DIR = Path('/home/admin/.openclaw/workspace/agents/debate')
TRADE_DIR = Path('/home/admin/.openclaw/workspace/agents/trade')
WORKFLOW_C_DIR = TRADE_DIR / 'data' / 'workflow_c' / 'CN_2026-04-07'
NOTIFY_SCRIPT = Path.home() / '.openclaw' / 'scripts' / 'notify.py'

DINGTALK_USER_ID = "01443329476136537748"

# 确保路径
sys.path.insert(0, str(DEBATE_DIR))
sys.path.insert(0, str(TRADE_DIR))


def send_dingtalk_text(message: str) -> bool:
    """发送文本消息到钉钉"""
    try:
        result = subprocess.run(
            ["python3", str(NOTIFY_SCRIPT), message],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"钉钉发送失败: {e}")
        return False


def send_dingtalk_file(file_path: str, caption: str = "") -> bool:
    """发送文件到钉钉 (作为 document media)"""
    try:
        cmd = [
            "openclaw", "message", "send",
            "--channel", "dingtalk",
            "--target", DINGTALK_USER_ID,
            "--media", file_path,
        ]
        if caption:
            cmd.extend(["--message", caption])
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        return result.returncode == 0
    except Exception as e:
        print(f"文件发送失败: {e}")
        return False


def main():
    start_time = time.time()
    print(f"\n{'='*70}")
    print(f" Workflow C Runner - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")

    # ── Step 1: 执行 Workflow C ──
    print("\n[1/3] 执行 Workflow C 全链路分析...")
    WORKFLOW_C_DIR.mkdir(parents=True, exist_ok=True)

    # 导入并执行
    os.chdir(str(TRADE_DIR))
    from workflow_c_cn_analysis import run_full_workflow
    run_full_workflow()

    elapsed = time.time() - start_time
    print(f"\nWorkflow C 执行完成，耗时 {elapsed:.0f}s")

    # ── Step 2: 加载审计结果 ──
    print("\n[2/3] 加载审计结果...")
    audit_json_path = WORKFLOW_C_DIR / '05_audit_report.json'
    report_md_path = WORKFLOW_C_DIR / 'workflow_analysis_report.md'

    if not audit_json_path.exists():
        print("  审计报告未生成")
        send_dingtalk_text("⚠️ Workflow C 审计报告未生成")
        return

    with open(audit_json_path, 'r', encoding='utf-8') as f:
        audit_data = json.load(f)

    meta = audit_data['audit_meta']
    summary = audit_data['summary']
    stocks = audit_data['stock_audits']

    # ── Step 3: 推送钉钉 ──
    print("\n[3/3] 推送钉钉通知...")

    # 构建摘要消息
    status_icon = "✅" if summary['critical_alerts'] == 0 else "⚠️"
    reliability_level = "高" if summary['avg_reliability'] >= 80 else ("中" if summary['avg_reliability'] >= 60 else "低")

    msg_lines = [
        f"📊 Workflow C 分析报告 ({meta['date']})",
        f"",
        f"{status_icon} 总体可靠性: {summary['avg_reliability']:.1f}/100 ({reliability_level})",
        f"",
        f"📈 统计摘要:",
        f"  • 候选股票: {summary['total_stocks']} 只",
        f"  • 可靠: {summary['reliable_count']} | 不可靠: {summary['unreliable_count']}",
        f"  • CRITICAL: {summary['critical_alerts']} | WARNING: {summary['warning_alerts']}",
        f"",
        f"📋 逐股审计:",
    ]

    for s in stocks:
        icon = "✅" if s['is_reliable'] else "❌"
        alert_count = len(s['alerts'])
        alert_info = f" ({alert_count}条告警)" if alert_count > 0 else ""
        msg_lines.append(f"  {icon} {s['code']} {s['name']}: {s['reliability']:.1f}{alert_info}")

    msg_lines.extend([
        f"",
        f"⏱️ 执行耗时: {elapsed:.0f}s",
        f"",
        f"📎 详细报告: audit_report.md",
        f"📎 完整分析: workflow_analysis_report.md",
        f"📎 审计数据: 05_audit_report.json",
    ])

    message = "\n".join(msg_lines)
    print(f"\n钉钉消息预览:\n{message}")

    # 发送文本摘要
    success = send_dingtalk_text(message)
    if success:
        print("✅ 文本摘要已发送到钉钉")
    else:
        print("❌ 文本摘要发送失败")

    # 发送审计报告文件
    audit_md_path = WORKFLOW_C_DIR / 'audit_report.md'
    if audit_md_path.exists():
        success = send_dingtalk_file(str(audit_md_path), "📋 Workflow C 审计报告")
        if success:
            print("✅ 审计报告已发送到钉钉")
        else:
            print("⚠️ 审计报告发送失败（尝试文本模式）")
            # 如果文件发送失败，发送内容摘要
            with open(audit_md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            # 截取前 2000 字符发送
            truncated = md_content[:2000] + "\n\n...(文件过长，请查看完整报告)"
            send_dingtalk_text(truncated)

    print(f"\n{'='*70}")
    print(f" Workflow C Runner 完成")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
