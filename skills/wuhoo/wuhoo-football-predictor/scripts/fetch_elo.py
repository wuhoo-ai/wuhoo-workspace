#!/usr/bin/env python3
"""
从 clubelo.com 获取最新国家队 Elo 评分
Usage: python3.11 scripts/fetch_elo.py [--output data/elo_ratings.json]
"""
import json
import sys
import subprocess
from datetime import datetime

def fetch_elo_from_clubelo():
    """Fetch national team Elo from clubelo.com"""
    try:
        result = subprocess.run(
            ['curl', '-s', 'http://api.clubelo.com/'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None
        
        lines = result.stdout.strip().split('\n')
        if not lines:
            return None
        
        # Parse CSV
        headers = lines[0].split(',')
        elo_data = {}
        
        for line in lines[1:]:
            parts = line.split(',')
            if len(parts) < 5:
                continue
            
            row = dict(zip(headers, parts))
            team = row.get('Club', row.get('Team', ''))
            elo = row.get('Elo', '')
            
            if team and elo:
                try:
                    elo_val = float(elo)
                    # Only national teams (clubelo uses country codes)
                    if len(team) <= 25 and elo_val > 1000:
                        elo_data[team] = int(round(elo_val))
                except ValueError:
                    continue
        
        return elo_data
    except Exception:
        return None

def fetch_elo_fallback():
    """Fallback Elo ratings (updated 2026-04-23)"""
    return {
        'Argentina': 2114, 'France': 2075, 'Brazil': 2061, 'England': 2022,
        'Spain': 2013, 'Portugal': 1998, 'Netherlands': 1985, 'Belgium': 1982,
        'Germany': 1978, 'Italy': 1968, 'Uruguay': 1963, 'Colombia': 1950,
        'Croatia': 1940, 'Morocco': 1933, 'USA': 1920, 'Mexico': 1910,
        'Japan': 1905, 'Senegal': 1898, 'Switzerland': 1890, 'Denmark': 1885,
        'Austria': 1878, 'Turkey': 1870, 'Ecuador': 1865, 'Nigeria': 1860,
        'South Korea': 1855, 'Iran': 1850, 'Egypt': 1845, 'Australia': 1840,
        'Serbia': 1835, 'Poland': 1830, 'Ukraine': 1825, 'Sweden': 1820,
        'Algeria': 1805, 'Tunisia': 1800, 'Ghana': 1795, 'Cameroon': 1790,
        'Canada': 1775, 'Czech Republic': 1770, 'Scotland': 1765, 'Norway': 1760,
        'Paraguay': 1755, 'Saudi Arabia': 1750, 'Bosnia and Herzegovina': 1745,
        'Iraq': 1740, 'Uzbekistan': 1735, 'DR Congo': 1730, 'Cape Verde': 1725,
        'Ivory Coast': 1720, 'Panama': 1715, 'New Zealand': 1710, 'Qatar': 1705,
        'Jordan': 1700, 'Haiti': 1695, 'Curacao': 1690,
    }

if __name__ == '__main__':
    output = 'data/elo_ratings.json'
    for arg in sys.argv[1:]:
        if arg.startswith('--output='):
            output = arg.split('=', 1)[1]
    
    elo = fetch_elo_from_clubelo()
    if elo:
        print(f"✅ Fetched {len(elo)} teams from clubelo.com")
    else:
        print("⚠️ clubelo.com unavailable, using fallback data")
        elo = fetch_elo_fallback()
    
    # Convert to dict format compatible with fetch_data.py
    ratings_dict = {}
    for rank, (team, elo_val) in enumerate(elo.items(), 1):
        ratings_dict[team] = {
            'elo': elo_val,
            'rank': rank,
            'country': team
        }
    
    meta = {
        'last_update': datetime.now().isoformat(),
        'source': 'clubelo.com' if len(elo) > 50 else 'fallback',
        'ratings': ratings_dict
    }
    
    with open(output, 'w') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved to {output} ({len(elo)} teams)")
