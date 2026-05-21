#!/usr/bin/env python3
"""
ELO 自动采集管线 v2.0 — Multi-source cascade with maintained static fallback

Data sources (priority order):
  1. international-football.net (HTTP, subject to rate limiting)
  2. eloratings.net main page (JS-rendered; Agent uses web_search to fetch)
  3. Static fallback (this file, updated 2026-05-21 via web_extract)

Usage:
  python3.11 scripts/fetch_elo.py                          # → data/elo_ratings.json
  python3.11 scripts/fetch_elo.py --output /path/to/out    # custom output
  python3.11 scripts/fetch_elo.py --diff                   # show changes vs current
  python3.11 scripts/fetch_elo.py --update-static          # Agent: update fallback from stdin JSON
  python3.11 scripts/fetch_elo.py --source                 # show data sources

Architecture:
  The script maintains a hardcoded STATIC_ELO dict as the authoritative fallback.
  Periodically, the Hermes Agent updates STATIC_ELO by running:
    web_extract(on international-football.net) → parse → pipe to --update-static
  The script also tries HTTP sources (international-football.net) on each run.
"""

import json
import sys
import os
import subprocess
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple, List

# ============================================================================
# STATIC FALLBACK — Authoritative snapshot
# Source: international-football.net + eloratings.net (2026-05-21)
# Updated by: Hermes Agent via --update-static
# ============================================================================
STATIC_ELO: Dict[str, int] = {
    # ── Top 20 ──────────────────────────────────────────────────────
    'Spain':             2165,   # 1
    'Argentina':         2113,   # 2
    'France':            2082,   # 3
    'England':           2020,   # 4
    'Brazil':            1984,   # 5 (tied with Portugal)
    'Portugal':          1984,   # 5
    'Colombia':          1975,   # 7
    'Netherlands':       1961,   # 8
    'Ecuador':           1933,   # 9
    'Croatia':           1930,   # 10
    'Germany':           1923,   # 11
    'Norway':            1912,   # 12
    'Japan':             1904,   # 13
    'Turkey':            1902,   # 14
    'Uruguay':           1892,   # 15
    'Switzerland':       1889,   # 16
    'Senegal':           1879,   # 17
    'Denmark':           1870,   # 18
    'Belgium':           1866,   # 19
    'Mexico':            1858,   # 20

    # ── 21-40 ──────────────────────────────────────────────────────
    'Italy':             1856,   # 21
    'Paraguay':          1833,   # 22
    'Austria':           1827,   # 23
    'Morocco':           1821,   # 24
    'Canada':            1784,   # 25
    'Australia':         1783,   # 26
    'Serbia':            1769,   # 28
    'Ukraine':           1767,   # 29 (tied with Scotland)
    'Scotland':          1767,   # 29
    'Iran':              1760,   # 31
    'South Korea':       1752,   # 32 (tied: Greece, Nigeria)
    'Nigeria':           1752,   # 32
    'Algeria':           1743,   # 35
    'Panama':            1737,   # 36
    'Poland':            1729,   # 37
    'Uzbekistan':        1727,   # 38
    'Czech Republic':    1726,   # 40
    'United States':     1721,   # 41
    'Sweden':            1719,   # 43
    'Greece':            1752,   # 32 (tied)

    # ── 41-60 ──────────────────────────────────────────────────────
    'Peru':              1695,   # 47
    'Ireland':           1691,   # 49
    'Jordan':            1690,   # 50
    'Egypt':             1689,   # 51
    'Ivory Coast':       1676,   # 52
    'DR Congo':          1655,   # 54
    'Tunisia':           1636,   # 58
    'Cameroon':          1614,   # 61
    'Iraq':              1607,   # 63
    'Bosnia and Herzegovina': 1594,  # from eloratings.net "Latest Results"
    'New Zealand':       1585,   # 66 (from eloratings.net WC 2026 page)
    'Chile':             1710,   # 44
    'Hungary':           1703,   # 45
    'Wales':             1698,   # 46
    'Slovenia':          1694,   # 48

    # ── 60+ WC teams ──────────────────────────────────────────────
    'Saudi Arabia':      1568,   # 76 (from eloratings.net WC 2026 page)
    'Cape Verde':        1549,   # 72 (from eloratings.net WC 2026 page)
    'South Africa':      1524,   # ~80 (from eloratings.net WC 2026 page)
    'Haiti':             1532,   # 77
    'Ghana':             1505,   # 82
    'Curacao':           1436,   # 90
    'Qatar':             1427,   # 95(from international-football.net)
    'Costa Rica':        1613,   # 62
    'Venezuela':         1727,   # 38 (tied with Uzbekistan)
}

# ============================================================================
# TEAM NAME ALIASES — maps alternate spellings to canonical STATIC_ELO keys
# ============================================================================
TEAM_ALIASES: Dict[str, Optional[str]] = {
    'usa': 'United States',
    'us': 'United States',
    'korea republic': 'South Korea',
    'south korea': 'South Korea',
    'korea': 'South Korea',
    'bosnia': 'Bosnia and Herzegovina',
    'bosnia herzegovina': 'Bosnia and Herzegovina',
    'bosnia/herzeg': 'Bosnia and Herzegovina',
    'czechia': 'Czech Republic',
    'czech': 'Czech Republic',
    'dr congo': 'DR Congo',
    'dem. rep. of congo': 'DR Congo',
    'dem rep of congo': 'DR Congo',
    'congo dr': 'DR Congo',
    'ivory coast': 'Ivory Coast',
    "cote d'ivoire": 'Ivory Coast',
    'cape verde': 'Cape Verde',
    'new zealand': 'New Zealand',
    'saudi arabia': 'Saudi Arabia',
    'south africa': 'South Africa',
    'united states of america': 'United States',
    'curacao': 'Curacao',
    'curaçao': 'Curacao',
    'north korea': None,  # not in our dataset
}

# ============================================================================
# Core logic
# ============================================================================

def _canonical_name(name: str) -> Optional[str]:
    """Map a name to its canonical STATIC_ELO key, or None if unmapped."""
    name = name.strip()
    if name in STATIC_ELO:
        return name
    lower = name.lower()
    if lower in TEAM_ALIASES:
        return TEAM_ALIASES[lower]
    # Try case-insensitive match against STATIC_ELO keys
    for key in STATIC_ELO:
        if key.lower() == lower:
            return key
    return None


def fetch_http_international_football() -> Optional[Dict[str, int]]:
    """
    Try to fetch from international-football.net via HTTP.
    Subject to 429 rate limiting — returns None on failure.
    """
    url = "https://www.international-football.net/elo-ratings-table"
    try:
        result = subprocess.run(
            ['curl', '-sL', '--connect-timeout', '15', '--max-time', '30',
             '-H', 'User-Agent: Mozilla/5.0 (compatible; EloBot/2.0)',
             url],
            capture_output=True, text=True, timeout=35
        )
        if result.returncode != 0 or 'Too Many Requests' in result.stdout:
            return None

        # Parse HTML table rows for "Rank | Team | Elo Rating" pattern
        elo_data: Dict[str, int] = {}
        # Look for table rows: <tr>...<td>RANK</td><td>TEAM</td><td>ELO</td>...</tr>
        row_pattern = re.compile(
            r'<tr[^>]*>\s*<td[^>]*>\s*(\d+)\s*</td>\s*'
            r'<td[^>]*>\s*(.*?)\s*</td>\s*'
            r'<td[^>]*>\s*(\d+)\s*</td>',
            re.IGNORECASE
        )
        for match in row_pattern.finditer(result.stdout):
            rank = int(match.group(1))
            team = match.group(2).strip()
            elo = int(match.group(3))
            # Strip HTML tags from team name
            team = re.sub(r'<[^>]+>', '', team)
            canonical = _canonical_name(team)
            if canonical:
                elo_data[canonical] = elo

        return elo_data if len(elo_data) > 20 else None
    except Exception:
        return None


def parse_eloratings_snippet(text: str) -> Dict[str, int]:
    """
    Parse eloratings.net search result snippet.
    Format: "N. Country. ELO ; N+1. Country. ELO ; ..."
    Also handles: "1. global_rank. Country" (confederation pages, no ELO)
    """
    result: Dict[str, int] = {}
    # Pattern: "N. Country Name. ELO" where ELO is 3-4 digits
    # Handles multi-word country names
    pattern = re.compile(
        r'(?:^|[;,])\s*(\d+)\.\s+([A-Za-zÀ-ÖØ-öø-ÿ\s\-]+?)(?:\.\s+(\d{3,4}))?(?=\s*[;,]|\s*$)'
    )
    for match in pattern.finditer(text):
        rank = int(match.group(1))
        team = match.group(2).strip()
        elo_str = match.group(3)
        if elo_str:
            canonical = _canonical_name(team)
            if canonical:
                result[canonical] = int(elo_str)
    return result


def load_existing(path: str) -> Dict[str, int]:
    """Load existing elo_ratings.json, return {team: elo}."""
    try:
        with open(path) as f:
            data = json.load(f)
        return {team: info['elo'] for team, info in data.get('ratings', {}).items()}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return {}


def compute_ranks(elo_dict: Dict[str, int]) -> List[Tuple[int, str, int]]:
    """Return sorted list of (rank, team, elo). Ties get same rank."""
    sorted_teams = sorted(elo_dict.items(), key=lambda x: -x[1])
    ranked = []
    prev_elo = None
    prev_rank = 0
    for i, (team, elo) in enumerate(sorted_teams, 1):
        if elo == prev_elo:
            rank = prev_rank  # tie
        else:
            rank = i
        ranked.append((rank, team, elo))
        prev_elo = elo
        prev_rank = rank
    return ranked


def save_ratings(elo_dict: Dict[str, int], output_path: str, source: str):
    """Save ELO data in standard format compatible with wc2026_predict.py."""
    ranked = compute_ranks(elo_dict)
    ratings = {}
    for rank, team, elo in ranked:
        ratings[team] = {'elo': elo, 'rank': rank, 'country': team}

    meta = {
        'last_update': datetime.now(timezone.utc).isoformat(),
        'source': source,
        'team_count': len(ratings),
        'ratings': ratings,
    }

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    return meta


def diff_ratings(old: Dict[str, int], new: Dict[str, int]) -> List[str]:
    """Return human-readable diff lines between old and new ratings."""
    lines = []
    all_teams = set(old.keys()) | set(new.keys())

    for team in sorted(all_teams):
        old_e = old.get(team)
        new_e = new.get(team)
        if old_e is None:
            lines.append(f"  + {team}: {new_e} (NEW)")
        elif new_e is None:
            lines.append(f"  - {team}: {old_e} (REMOVED)")
        elif old_e != new_e:
            delta = new_e - old_e
            sign = '+' if delta > 0 else ''
            arrow = '↑' if delta > 0 else '↓'
            lines.append(f"  {arrow} {team}: {old_e} → {new_e} ({sign}{delta})")

    return lines


def update_static_fallback(json_input: str) -> int:
    """
    Update STATIC_ELO in this script file from stdin JSON.
    JSON format: {"Spain": 2165, "Argentina": 2113, ...}
    Returns number of teams updated.
    """
    try:
        incoming = json.loads(json_input)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        return 0

    if not isinstance(incoming, dict):
        print("❌ JSON must be a dict of {team: elo}", file=sys.stderr)
        return 0

    # Validate and canonicalize
    validated: Dict[str, int] = {}
    for team, elo in incoming.items():
        if not isinstance(elo, (int, float)):
            print(f"⚠️  Skipping {team}: non-numeric ELO {elo}", file=sys.stderr)
            continue
        canonical = _canonical_name(team)
        if canonical is None:
            print(f"⚠️  Skipping {team}: not in known teams list", file=sys.stderr)
            continue
        validated[canonical] = int(elo)

    if not validated:
        print("❌ No valid teams found in input", file=sys.stderr)
        return 0

    # Update this file's STATIC_ELO section
    script_path = Path(__file__)
    content = script_path.read_text()

    # Find the STATIC_ELO block
    start_marker = 'STATIC_ELO: Dict[str, int] = {'
    end_marker = '\n}'

    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("❌ Could not find STATIC_ELO in script", file=sys.stderr)
        return 0

    # Find the closing brace of STATIC_ELO
    brace_start = start_idx + len(start_marker)
    depth = 1
    end_idx = brace_start
    for i in range(brace_start, len(content)):
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
            if depth == 0:
                end_idx = i
                break

    if depth != 0:
        print("❌ Could not find end of STATIC_ELO", file=sys.stderr)
        return 0

    # Build new STATIC_ELO section
    ranked = sorted(validated.items(), key=lambda x: -x[1])
    new_lines = ['STATIC_ELO: Dict[str, int] = {']
    # Group by tiers
    current_tier = 'top'
    for rank, (team, elo) in enumerate(ranked, 1):
        comment = f"  #{rank}"
        new_lines.append(f"    '{team}': {elo:>16},  {comment if rank <= 30 else ''}")
    new_lines.append('}')

    new_section = '\n'.join(new_lines)

    # Patch the file
    new_content = content[:start_idx] + new_section + content[end_idx + 1:]
    script_path.write_text(new_content)

    print(f"✅ Updated STATIC_ELO: {len(validated)} teams (was {len(STATIC_ELO)})")
    return len(validated)


# ============================================================================
# Main
# ============================================================================

def main():
    output = 'data/elo_ratings.json'
    show_diff = False
    update_static = False

    args = sys.argv[1:]
    for arg in args:
        if arg.startswith('--output='):
            output = arg.split('=', 1)[1]
        elif arg == '--diff':
            show_diff = True
        elif arg == '--update-static':
            update_static = True
        elif arg == '--source':
            print("Static fallback source: international-football.net + eloratings.net (2026-05-21)")
            print(f"Teams: {len(STATIC_ELO)}")
            return

    # ── Mode: update static fallback from stdin ──
    if update_static:
        json_input = sys.stdin.read()
        updated = update_static_fallback(json_input)
        sys.exit(0 if updated > 0 else 1)

    # ── Mode: fetch and save ──
    elo_new: Dict[str, int] = {}
    source = 'static fallback'

    # Tier 1: HTTP fetch
    print("🔍 Trying international-football.net ...")
    http_data = fetch_http_international_football()
    if http_data and len(http_data) >= 30:
        elo_new = http_data
        source = 'international-football.net (HTTP)'
        print(f"   ✅ Got {len(http_data)} teams via HTTP")
    else:
        print("   ⚠️  HTTP unavailable (429 or no data)")

    # Tier 2: Merge with existing file (preserve any manually curated data)
    existing = load_existing(output)

    # Tier 3: Fall back to STATIC_ELO for any missing teams
    if not elo_new:
        elo_new = dict(STATIC_ELO)
        source = 'static fallback (2026-05-21)'

    # Merge: STATIC_ELO fills gaps in HTTP data
    for team, elo in STATIC_ELO.items():
        if team not in elo_new:
            elo_new[team] = elo

    # Build set of canonical names already covered
    covered_canonical = set()
    for team in list(elo_new.keys()):
        canonical = _canonical_name(team)
        if canonical:
            covered_canonical.add(canonical)

    # Preserve existing teams not already covered (handle alias normalization)
    for team, elo in existing.items():
        canonical = _canonical_name(team)
        if canonical is None:
            # Team not in our known list — keep as-is if unique
            if team not in elo_new and team.lower() not in {t.lower() for t in elo_new}:
                elo_new[team] = elo
        elif canonical not in covered_canonical:
            elo_new[canonical] = elo
            covered_canonical.add(canonical)

    # ── Diff ──
    if show_diff:
        old = existing if existing else {}
        changes = diff_ratings(old, elo_new)
        if changes:
            print(f"\n📊 Changes vs existing ({len(changes)} teams):")
            for line in changes:
                print(line)
        else:
            print("\n📊 No changes vs existing.")

    # ── Save ──
    meta = save_ratings(elo_new, output, source)
    print(f"\n💾 Saved to {output}")
    print(f"   Teams: {meta['team_count']} | Source: {source}")
    print(f"   Updated: {meta['last_update'][:19]}")

    # Quick summary of top 10
    ranked = compute_ranks(elo_new)
    print("\n   Top 10:")
    for rank, team, elo in ranked[:10]:
        print(f"   {rank:>2}. {team:<24} {elo}")


if __name__ == '__main__':
    main()