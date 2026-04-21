#!/usr/bin/env python3.11
"""学习循环审查 - 每日自动执行"""
import os, json, subprocess
from datetime import datetime, timedelta

WS = os.path.expanduser("~/wuhoo-workspace")
HERMES = os.path.expanduser("~/.hermes")
LEARNING = os.path.join(WS, "learning")

def analyze_sessions():
    """分析最近的session"""
    sessions_dir = os.path.join(HERMES, "sessions")
    if not os.path.exists(sessions_dir):
        return {"total": 0, "errors": 0}
    
    # Simple stat: count session files modified in last 24h
    cutoff = datetime.now() - timedelta(hours=24)
    recent = 0
    errors = 0
    for f in os.listdir(sessions_dir):
        fp = os.path.join(sessions_dir, f)
        mtime = datetime.fromtimestamp(os.path.getmtime(fp))
        if mtime > cutoff:
            recent += 1
            with open(fp, errors='ignore') as fh:
                content = fh.read()
                if "error" in content.lower() or "failed" in content.lower():
                    errors += 1
    return {"total": recent, "errors": errors}

def check_memory():
    """检查memory使用率"""
    mem_files = [
        os.path.join(HERMES, "memories", "MEMORY.md"),
        os.path.join(HERMES, "memories", "USER.md"),
    ]
    total_chars = 0
    file_details = {}
    for mf in mem_files:
        name = os.path.basename(mf)
        if os.path.exists(mf):
            with open(mf) as f:
                content = f.read()
                sz = len(content)
                total_chars += sz
                file_details[name] = sz
        else:
            file_details[name] = 0
    # Each entry has ~2200 char limit; total ~8000 char practical limit
    return {"chars": total_chars, "limit": 8000, "files": file_details}

def generate_report():
    sessions = analyze_sessions()
    memory = check_memory()
    now = datetime.now().isoformat()
    
    report = f"# 学习循环报告\n\n生成时间: {now}\n\n"
    report += f"## 24小时统计\n\n- 活跃session: {sessions['total']}\n- 含错误的session: {sessions['errors']}\n\n"
    report += f"## 记忆状态\n\n- 当前大小: {memory['chars']} chars\n- 上限: {memory['limit']} chars\n- 使用率: {memory['chars']/memory['limit']*100:.1f}%\n\n"
    
    if memory['chars'] > memory['limit'] * 0.8:
        report += "**警告**: 记忆接近上限，建议清理\n\n"
    
    # Log execution
    log_entry = {"timestamp": now, "sessions": sessions, "memory": memory, "report_path": f"learning/retrospective/{now[:10]}.md"}
    with open(os.path.join(LEARNING, "execution_log.jsonl"), "a") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    # Save report
    report_path = os.path.join(LEARNING, "retrospective", f"{now[:10]}.md")
    with open(report_path, "w") as f:
        f.write(report)
    
    print(f"Report saved to {report_path}")
    return report

if __name__ == "__main__":
    generate_report()
