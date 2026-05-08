#!/usr/bin/env python3.11
"""
查看每日定时任务执行结果
用法:
  python3.11 cron_view.py          # 今天的结果
  python3.11 cron_view.py 2026-05-03  # 指定日期
  python3.11 cron_view.py --latest    # 只看每个任务最新一次
"""
import sys, os, json, re
from pathlib import Path
from datetime import date, datetime

CRON_DIR = Path.home() / ".hermes/cron"
OUTPUT_DIR = CRON_DIR / "output"
JOBS_FILE = CRON_DIR / "jobs.json"

# Load job name mapping
job_names = {}
if JOBS_FILE.exists():
    with open(JOBS_FILE) as f:
        data = json.load(f)
        jobs = data.get("jobs", data) if isinstance(data, dict) else data
        for j in jobs:
            job_names[j.get("id", j.get("job_id"))] = j.get("name", j.get("id", "")[:8])

def main():
    target_date = str(date.today())
    latest_only = False
    
    if "--latest" in sys.argv:
        latest_only = True
    for arg in sys.argv[1:]:
        if re.match(r'\d{4}-\d{2}-\d{2}', arg):
            target_date = arg
    
    if not OUTPUT_DIR.exists():
        print("📭 暂无定时任务输出")
        return
    
    results = []
    for job_dir in sorted(OUTPUT_DIR.iterdir()):
        if not job_dir.is_dir():
            continue
        job_id = job_dir.name
        name = job_names.get(job_id, job_id[:8])
        
        files = sorted(job_dir.glob(f"{target_date}*.md"))
        if not files and latest_only:
            # For latest mode, find most recent file
            all_files = sorted(job_dir.glob("*.md"))
            if all_files:
                files = [all_files[-1]]
        
        for f in files:
            stat = f.stat()
            size_kb = stat.st_size / 1024
            lines = f.read_text(encoding='utf-8').count('\n')
            results.append({
                'name': name,
                'job_id': job_id,
                'path': str(f),
                'time': f.name.replace('.md', ''),
                'size_kb': size_kb,
                'lines': lines
            })
    
    if not results:
        print(f"📭 {target_date} 无常任务执行记录")
        print(f"   （检查目录：{OUTPUT_DIR}）")
        return
    
    print(f"📋 定时任务执行记录 — {target_date}")
    print("=" * 65)
    print(f"{'任务名称':<22} {'时间':<20} {'大小':>6} {'行数':>5}")
    print("-" * 65)
    
    for r in sorted(results, key=lambda x: x['time']):
        print(f"{r['name']:<22} {r['time']:<20} {r['size_kb']:>5.1f}K {r['lines']:>5}行")
    
    print("-" * 65)
    print(f"共 {len(results)} 条记录")
    print(f"\n💡 查看内容: less {results[0]['path']}" if results else "")

if __name__ == "__main__":
    main()
