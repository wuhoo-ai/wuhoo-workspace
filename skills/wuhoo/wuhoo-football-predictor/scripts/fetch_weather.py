#!/usr/bin/env python3
"""
WC2026 比赛日天气采集 — Open-Meteo Forecast API

数据源: https://api.open-meteo.com/v1/forecast (免费, 无需 API key)
三重降级: Open-Meteo → venues.json 静态均值 → 零值

Usage:
  python3.11 scripts/fetch_weather.py --date 2026-06-24   # 指定日期
  python3.11 scripts/fetch_weather.py --tomorrow            # 明天
  python3.11 scripts/fetch_weather.py --date 2026-06-24 --dry-run  # 仅打印不保存

Output:
  data/match_weather.json  — 按 match_id 索引，含天气数据 + 计算好的 penalty
"""

import sys
import os
import json
import argparse
import time
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, SCRIPT_DIR)

DATA_DIR = os.path.join(PROJECT_DIR, 'data')

# WMO Weather Code → condition category + rain bucket
# https://www.nodc.noaa.gov/archive/arc0021/0002199/1.1/data/0-data/HTML/WMO-CODE/WMO4677.HTM
WMO_CODE_MAP = {
    0:  ("clear", "none"),
    1:  ("mainly_clear", "none"),
    2:  ("partly_cloudy", "none"),
    3:  ("overcast", "none"),
    # Rain / Drizzle
    45: ("fog", "none"),
    48: ("fog", "none"),
    51: ("light_drizzle", "light"),
    53: ("moderate_drizzle", "moderate"),
    55: ("dense_drizzle", "moderate"),
    56: ("freezing_drizzle", "light"),
    57: ("freezing_drizzle", "moderate"),
    61: ("slight_rain", "light"),
    63: ("moderate_rain", "moderate"),
    65: ("heavy_rain", "heavy"),
    66: ("freezing_rain", "light"),
    67: ("freezing_rain", "moderate"),
    # Snow (unlikely in June WC, but handle)
    71: ("slight_snow", "light"),
    73: ("moderate_snow", "moderate"),
    75: ("heavy_snow", "heavy"),
    77: ("snow_grains", "light"),
    # Showers
    80: ("slight_rain_showers", "light"),
    81: ("moderate_rain_showers", "moderate"),
    82: ("violent_rain_showers", "heavy"),
    # Thunderstorm
    85: ("slight_thunderstorm", "moderate"),
    86: ("heavy_thunderstorm", "heavy"),
    95: ("thunderstorm", "moderate"),
    96: ("thunderstorm_with_hail", "heavy"),
    99: ("heavy_thunderstorm_with_hail", "heavy"),
}

RAIN_CATEGORY_PENALTY = {
    "none": 0,
    "light": -5,
    "moderate": -15,
    "heavy": -30,
}

WIND_CATEGORY_MAP = {
    (0, 15): ("calm", 0),
    (15, 30): ("breezy", -8),
    (30, 100): ("windy", -15),
}


def load_json(path):
    with open(path) as f:
        return json.load(f)


def get_match_local_time(match, venue):
    """Estimate match local time from Beijing time and venue timezone offset."""
    tz_map = {
        "MEX": -6,   # Mexico City (CST) — UTC-6
        "USA": -4,   # US East (EDT in June) — UTC-4
        "CAN": -4,   # Toronto/Vancouver (EDT/PDT) — use -4 as approx
    }
    tz_offset = tz_map.get(venue.get("country", "USA"), -4)
    # Beijing is UTC+8, so Beijing - venue_tz = hour offset
    # For simplicity: match is played at local evening ~19:00-21:00
    # Use daily max temp (daytime) + min temp (night) average for match temp
    return None  # Use daily values directly


def fetch_venue_weather(venue_name, venue_data, target_date_str):
    """Fetch weather for one venue from Open-Meteo."""
    coords = venue_data.get("coordinates")
    if not coords:
        return None, "no coordinates"

    lat = coords["lat"]
    lon = coords["lon"]

    # Open-Meteo forecast API
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code,wind_speed_10m_max"
        f"&timezone=auto&forecast_days=7"
    )

    try:
        req = Request(url, headers={"User-Agent": "WC2026-Predictor/5.2"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        daily = data.get("daily", {})
        times = daily.get("time", [])
        if target_date_str not in times:
            # Find closest date
            return None, f"date {target_date_str} not in forecast range"

        idx = times.index(target_date_str)
        tmax = daily["temperature_2m_max"][idx]
        tmin = daily["temperature_2m_min"][idx]
        precip = daily["precipitation_sum"][idx]
        wcode = daily["weather_code"][idx]
        wind = daily["wind_speed_10m_max"][idx]

        temp_avg = (tmax + tmin) / 2

        # WMO code → categories
        condition, precip_cat = WMO_CODE_MAP.get(wcode, (f"code_{wcode}", "none"))

        # Wind category
        wind_cat, wind_penalty = "calm", 0
        for (lo, hi), (cat, pen) in WIND_CATEGORY_MAP.items():
            if lo <= wind < hi:
                wind_cat, wind_penalty = cat, pen
                break

        # Indoor exemption for wind
        if venue_data.get("indoor", False):
            wind_penalty = 0
            wind_cat = "indoor"

        # Rain penalty
        rain_penalty = RAIN_CATEGORY_PENALTY.get(precip_cat, 0)

        # Heat penalty (recomputed with real temp)
        heat_penalty = 0
        if temp_avg > 28:  # threshold_c
            heat_penalty = int((temp_avg - 28) / 5 * 10)  # penalty_per_5c_above
            if venue_data.get("indoor", False):
                heat_penalty = int(heat_penalty * 0.5)

        return {
            "venue": venue_name,
            "city": venue_data.get("city", "?"),
            "temp_c_max": round(tmax, 1),
            "temp_c_min": round(tmin, 1),
            "temp_c_avg": round(temp_avg, 1),
            "weather_code": wcode,
            "condition": condition,
            "precip_mm": round(precip, 1),
            "precip_category": precip_cat,
            "wind_kph": round(wind, 1),
            "wind_category": wind_cat,
            "rain_penalty": rain_penalty,
            "wind_penalty": wind_penalty,
            "heat_penalty_actual": heat_penalty,
            "indoor": venue_data.get("indoor", False),
        }, None

    except URLError as e:
        return None, f"API error: {e}"
    except Exception as e:
        return None, f"Parse error: {e}"


def fallback_weather(venue_name, venue_data):
    """Fallback: use venues.json static averages."""
    return {
        "venue": venue_name,
        "city": venue_data.get("city", "?"),
        "temp_c_avg": venue_data.get("temp_c_jun_jul_avg", 20),
        "condition": "static_average",
        "precip_mm": 0,
        "precip_category": "none",
        "wind_kph": 0,
        "wind_category": "unknown",
        "rain_penalty": 0,
        "wind_penalty": 0,
        "heat_penalty_actual": venue_data.get("heat_elo_penalty", 0),
        "indoor": venue_data.get("indoor", False),
        "_fallback": True,
    }


def main():
    parser = argparse.ArgumentParser(description="WC2026 Match Weather Fetcher")
    parser.add_argument("--date", help="Target Beijing date (YYYY-MM-DD)")
    parser.add_argument("--tomorrow", action="store_true", help="Target = tomorrow")
    parser.add_argument("--dry-run", action="store_true", help="Print only, don't save")
    args = parser.parse_args()

    beijing_tz = timezone(timedelta(hours=8))
    now = datetime.now(beijing_tz)

    if args.tomorrow:
        target_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    elif args.date:
        target_date = args.date
    else:
        target_date = now.strftime("%Y-%m-%d")

    print(f"🌤️  Fetching weather for {target_date}...")

    # Load data
    schedule = load_json(os.path.join(DATA_DIR, "wc2026_schedule.json"))
    venues = load_json(os.path.join(DATA_DIR, "venues.json"))

    # Find matches on target date
    matches = [m for m in schedule["matches"] if m.get("date_beijing") == target_date]
    if not matches:
        print(f"✅ {target_date}: No matches scheduled")
        return

    print(f"   {len(matches)} matches, fetching venue weather...")

    # Collect unique venues
    unique_venues = set()
    for m in matches:
        venue_name = m.get("venue")
        if venue_name:
            unique_venues.add(venue_name)

    # Fetch weather per venue
    venue_weather = {}
    api_errors = 0
    for vname in sorted(unique_venues):
        vdata = venues.get("venues", {}).get(vname, {})
        result, error = fetch_venue_weather(vname, vdata, target_date)
        if error:
            print(f"   ⚠️ {vname}: {error} → fallback to static")
            result = fallback_weather(vname, vdata)
            api_errors += 1
        else:
            status = result["condition"]
            print(f"   ✅ {vname}: {status} | {result['temp_c_avg']}°C | rain {result['precip_mm']}mm | wind {result['wind_kph']}km/h")
        venue_weather[vname] = result
        time.sleep(0.1)  # polite rate limit

    # Build per-match forecasts
    forecasts = {}
    for m in matches:
        mid = str(m["match_id"])
        venue_name = m.get("venue", "")
        vw = venue_weather.get(venue_name, {})

        forecasts[mid] = {
            "match_id": m["match_id"],
            "team_a": m["team_a"],
            "team_b": m["team_b"],
            "venue": venue_name,
            "date_beijing": target_date,
            "time_beijing": m.get("time_beijing", "?"),
            "group": m.get("group", "?"),
            "matchday": m.get("matchday", "?"),
            **vw,
        }

    output = {
        "generated": datetime.now().isoformat(),
        "source": "open-meteo.com",
        "target_date": target_date,
        "total_matches": len(matches),
        "api_errors": api_errors,
        "forecasts": forecasts,
    }

    if args.dry_run:
        print(f"\n📋 Dry run — not saving:")
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    # Save
    out_path = os.path.join(DATA_DIR, "match_weather.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Saved to match_weather.json ({len(forecasts)} matches, {api_errors} fallbacks)")


if __name__ == "__main__":
    main()
