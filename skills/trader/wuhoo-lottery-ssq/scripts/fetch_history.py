#!/usr/bin/env python3.11
"""
双色球历史开奖数据抓取模块

数据源：500.com (datachart.500.com)
解析 HTML 表格获取历史开奖数据

输出格式：CSV (期号,日期,红1,红2,红3,红4,红5,红6,蓝球,销售额,奖池)
"""

import csv
import os
import sys
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent.parent / "data"
CSV_FILE = DATA_DIR / "ssq_history.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://datachart.500.com/ssq/"
}


def fetch_500com(start: str = "03001", end: str = "26999") -> list[dict]:
    """从 500.com 抓取双色球历史数据
    
    Args:
        start: 起始期号（如 '03001' 表示 2003001 期）
        end: 结束期号
    
    Returns:
        开奖记录列表
    """
    url = "https://datachart.500.com/ssq/history/newinc/history.php"
    params = {"start": start, "end": end}
    
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        tbody = soup.find("tbody", id="tdata")
        if not tbody:
            tbody = soup.find("tbody")
        
        if not tbody:
            print("[ERROR] 未找到数据表格")
            return []
        
        rows = tbody.find_all("tr")
        results = []
        
        for row in rows:
            tds = row.find_all("td")
            if len(tds) < 16:
                continue
            
            try:
                code = tds[0].text.strip()
                red1 = int(tds[1].text.strip())
                red2 = int(tds[2].text.strip())
                red3 = int(tds[3].text.strip())
                red4 = int(tds[4].text.strip())
                red5 = int(tds[5].text.strip())
                red6 = int(tds[6].text.strip())
                blue = int(tds[7].text.strip())
                sales = tds[9].text.strip().replace(",", "")
                pool = tds[14].text.strip().replace(",", "")
                date = tds[15].text.strip()
                
                # 验证数据有效性
                if not (1 <= red1 < red2 < red3 < red4 < red5 < red6 <= 33):
                    continue
                if not (1 <= blue <= 16):
                    continue
                
                results.append({
                    "期号": code,
                    "日期": date,
                    "红1": red1,
                    "红2": red2,
                    "红3": red3,
                    "红4": red4,
                    "红5": red5,
                    "红6": red6,
                    "蓝球": blue,
                    "销售额": sales,
                    "奖池": pool,
                })
            except (ValueError, IndexError):
                continue
        
        return results
    
    except Exception as e:
        print(f"[ERROR] 500.com 抓取失败: {e}")
        return []


def load_existing_codes() -> set[str]:
    """加载已存在的期号集合"""
    codes = set()
    if CSV_FILE.exists():
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                codes.add(row["期号"])
    return codes


def save_data(records: list[dict], verbose: bool = True) -> str:
    """保存数据到 CSV，按期号降序排列
    
    Args:
        records: 开奖记录列表
        verbose: 是否打印详细信息
    
    Returns:
        文件路径
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 合并已有数据（增量更新）
    existing_codes = load_existing_codes()
    existing_records = []
    
    if CSV_FILE.exists():
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_records.append(row)
    
    # 合并新数据（去重）
    existing_code_set = set(r["期号"] for r in existing_records)
    new_count = 0
    
    for rec in records:
        if rec["期号"] not in existing_code_set:
            existing_records.append(rec)
            new_count += 1
    
    # 按期号排序（降序）
    existing_records.sort(key=lambda x: x["期号"], reverse=True)
    
    # 写入 CSV
    fieldnames = ["期号", "日期", "红1", "红2", "红3", "红4", "红5", "红6", "蓝球", "销售额", "奖池"]
    with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_records)
    
    if verbose:
        print(f"✅ 保存完成: {len(existing_records)} 条记录 (新增 {new_count} 条)")
        if existing_records:
            print(f"   最新期号: {existing_records[0]['期号']} ({existing_records[0]['日期']})")
            print(f"   最早期号: {existing_records[-1]['期号']} ({existing_records[-1]['日期']})")
        print(f"📁 数据文件: {CSV_FILE}")
    
    return str(CSV_FILE)


def fetch_history(start: str = "03001", end: str = "26999", verbose: bool = True) -> str:
    """完整抓取流程
    
    Args:
        start: 起始期号
        end: 结束期号
        verbose: 是否打印日志
    
    Returns:
        CSV 文件路径
    """
    if verbose:
        print("🔄 开始抓取双色球历史数据...")
        print(f"📡 数据源: 500.com (datachart)")
    
    records = fetch_500com(start, end)
    
    if verbose:
        print(f"✅ 抓取完成: {len(records)} 条有效记录")
    
    return save_data(records, verbose=verbose)


def get_latest_code() -> str:
    """获取最新期号"""
    if not CSV_FILE.exists():
        return ""
    
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            return row["期号"]
    return ""


def incremental_update(verbose: bool = True) -> str:
    """增量更新：只获取最新数据"""
    latest = get_latest_code()
    if not latest:
        if verbose:
            print("📥 无历史数据，开始全量抓取...")
        return fetch_history(verbose=verbose)
    
    # 从最新期号的下一期开始抓取
    # 期号格式: YYNNN (年份后2位 + 期数)
    year_part = int(latest[:2])
    seq_part = int(latest[2:])
    next_seq = seq_part + 1
    
    # 构建下期期号
    if next_seq > 154:  # 一年最多约 154 期
        next_year = year_part + 1
        next_seq = 1
    else:
        next_year = year_part
    
    start_code = f"{next_year:02d}{next_seq:03d}"
    end_code = "26999"
    
    if verbose:
        print(f"🔄 增量更新 (从 {start_code} 开始)...")
    
    records = fetch_500com(start_code, end_code)
    
    if verbose:
        if records:
            print(f"✅ 新增 {len(records)} 条记录")
        else:
            print("✅ 数据已是最新")
    
    return save_data(records, verbose=verbose)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="双色球历史数据抓取")
    parser.add_argument("--start", default="03001", help="起始期号")
    parser.add_argument("--end", default="26999", help="结束期号")
    parser.add_argument("--incremental", action="store_true", help="增量更新模式")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    
    args = parser.parse_args()
    
    if args.incremental:
        incremental_update(verbose=not args.quiet)
    else:
        fetch_history(args.start, args.end, verbose=not args.quiet)
