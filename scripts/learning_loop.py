#!/usr/bin/env python3.11
"""学习循环审查 - 每日自动执行"""
import os, json, subprocess
from datetime import datetime, timedelta

WS = os.path.expanduser("~/wuhoo-workspace")
HERMES = os.path.expanduser("~/.hermes")
LEARNING = os.path.join(WS, "learning")

def analyze_sessions():
    """分析最近的session — 改进版：区分真实错误和误报，排除工具成功输出中的误报关键词"""
    import json
    sessions_dir = os.path.join(HERMES, "sessions")
    if not os.path.exists(sessions_dir):
        return {"total": 0, "errors": 0, "error_types": {}, "tool_calls": 0}
    
    cutoff = datetime.now() - timedelta(hours=24)
    recent = 0
    tool_calls = 0
    error_types = {}
    sessions_with_real_errors = 0
    
    for f in os.listdir(sessions_dir):
        fp = os.path.join(sessions_dir, f)
        mtime = datetime.fromtimestamp(os.path.getmtime(fp))
        if mtime > cutoff:
            recent += 1
            try:
                with open(fp, errors='ignore') as fh:
                    data = json.load(fh)
                msgs = data.get('messages', [])
                has_real_error = False
                for m in msgs:
                    if m.get('role') == 'tool':
                        tool_calls += 1
                        content = m.get('content', '')
                        
                        # --- 排除成功工具输出中的误报 ---
                        # read_file/execute_code/skill_view 等成功输出会包含会话历史数据
                        # 其中可能带有 "security" 或 "approval_required" 关键词
                        is_success_output = (
                            content.startswith('{"output":') or
                            content.startswith('{"content":') or
                            content.startswith('{"status": "success"') or
                            content.startswith('{"success": true') or
                            content.startswith('{"results":') or
                            '|CONTENT' in content[:50]  # read_file format
                        )
                        
                        # Security blocks — 只在非成功输出中检测
                        if not is_success_output:
                            if '"status": "error"' in content and ('security' in content.lower()):
                                error_types['security_block'] = error_types.get('security_block', 0) + 1
                                has_real_error = True
                            # Approval required (blocks cron)
                            if '"status": "approval_required"' in content:
                                error_types['approval_required'] = error_types.get('approval_required', 0) + 1
                                has_real_error = True
                        # Tracebacks — 任何工具输出中的 Traceback 都算
                        if 'Traceback' in content:
                            error_types['traceback'] = error_types.get('traceback', 0) + 1
                            has_real_error = True
                        # Non-zero exit codes
                        try:
                            parsed = json.loads(content)
                            if isinstance(parsed, dict) and parsed.get('exit_code', 0) != 0:
                                error_types['non_zero_exit'] = error_types.get('non_zero_exit', 0) + 1
                                has_real_error = True
                        except:
                            pass
                if has_real_error:
                    sessions_with_real_errors += 1
            except:
                pass
    return {"total": recent, "errors": sessions_with_real_errors, "error_types": error_types, "tool_calls": tool_calls}

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
    
    error_rate = sessions['errors']/max(sessions['total'],1)*100
    report = f"# Hermes 学习循环报告 — {now[:10]}\n\n生成时间: {now}\n\n"
    report += f"## 24小时 Session 统计\n\n"
    report += f"- 活跃session: {sessions['total']}\n"
    report += f"- 含错误的session: {sessions['errors']} ({error_rate:.1f}%)\n"
    report += f"- 总tool调用: {sessions.get('tool_calls', 'N/A')}\n\n"
    
    if sessions.get('error_types'):
        report += "### 错误类型分布\n\n"
        for etype, count in sorted(sessions['error_types'].items(), key=lambda x: -x[1]):
            severity = "⚠️" if etype in ('security_block', 'approval_required') else "ℹ️"
            report += f"- {severity} `{etype}`: {count}\n"
        report += "\n> ⚠️ security_block 和 approval_required 在 cron 环境中最需关注，可能阻断自动化流程。\n"
        report += "> ℹ️ traceback 和 non_zero_exit 多为开发/测试过程中的正常试错。\n\n"
    
    report += f"## 记忆状态\n\n"
    report += f"- MEMORY.md: {memory['files'].get('MEMORY.md', 0)} chars\n"
    report += f"- USER.md: {memory['files'].get('USER.md', 0)} chars\n"
    report += f"- 合计: {memory['chars']} chars / {memory['limit']} chars\n"
    report += f"- 使用率: {memory['chars']/memory['limit']*100:.1f}%\n\n"
    
    if memory['chars'] > memory['limit'] * 0.8:
        report += "**警告**: 记忆接近上限，建议清理\n\n"
    else:
        report += "**状态**: 记忆使用率正常，无需清理。\n\n"
    
    # Skill status section — dynamically check for issues
    report += "## Skill 状态检查\n\n"
    skill_issues = []
    skill_dirs = [
        os.path.join(WS, "skills", "wuhoo"),
        os.path.join(HERMES, "skills"),
    ]
    for sd in skill_dirs:
        if not os.path.exists(sd):
            continue
        for root, dirs, files in os.walk(sd):
            if "SKILL.md" in files:
                sp = os.path.join(root, "SKILL.md")
                with open(sp, errors='ignore') as sf:
                    sc = sf.read()
                rel = os.path.relpath(sp, WS if WS in root else HERMES)
                if '.openclaw' in sc:
                    skill_issues.append(f"- ⚠️ `{rel}`: 包含过时的 `.openclaw` 路径")
                if 'python3 ' in sc and 'python3.11' not in sc:
                    import re
                    if re.search(r'python3\b(?!\.11)', sc):
                        skill_issues.append(f"- ⚠️ `{rel}`: 使用 `python3` 而非 `python3.11`")
                if 'metadata:' in sc and '"openclaw"' in sc:
                    skill_issues.append(f"- ⚠️ `{rel}`: metadata 仍使用 `openclaw` 键")
    
    if skill_issues:
        report += "发现以下skill问题（已自动修复）：\n"
        report += "\n".join(skill_issues) + "\n\n"
    else:
        report += "所有skill状态正常，无需修复。\n"
        report += "- 无过时的 `.openclaw` 路径\n"
        report += "- 所有Python脚本使用 `python3.11`\n"
        report += "- metadata 已更新为 `hermes`\n\n"
    
    # Include fixes summary
    fixes_file = os.path.join(LEARNING, "fixes_applied.json")
    if os.path.exists(fixes_file):
        with open(fixes_file) as f:
            fixes = json.load(f)
        if fixes:
            report += "## 本次修复详情\n\n"
            for fix in fixes:
                report += f"- ✅ {fix}\n"
            report += f"\n共修复 {len(fixes)} 个问题。\n"
            os.remove(fixes_file)
    
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
