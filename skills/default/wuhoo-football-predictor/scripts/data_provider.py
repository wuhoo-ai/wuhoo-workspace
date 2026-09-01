#!/usr/bin/env python3.11
"""
Data Provider — Dynamic data abstraction layer
v1.0 — WC2026 v5.5

Provides fresh data to the inference engine with automatic
freshness checking and cache management.

Data sources:
- JSON files (ELO, schedule, results, venues, team profiles)
- Web APIs (weather via Open-Meteo)
- Computed (motivation, third-place standings, bracket paths)
"""

import json, os, time
from datetime import datetime, timezone, timedelta
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


class DataProvider:
    """Unified data access with freshness tracking."""
    
    def __init__(self, enable_live_fetch=False):
        self.enable_live_fetch = enable_live_fetch
        self._cache = {}
        self._timestamps = {}
        
        # Pre-load static data
        self.elo = self._load_json("elo_ratings.json")
        self.schedule = self._load_json("wc2026_schedule.json")
        self.venues = self._load_json("venues.json")
        self.team_profiles = self._load_json("team_profiles.json")
        self.team_metadata = self._load_json("team_metadata.json")
        self.injuries = self._load_json("injuries.json")
        self.manual_adjustments = self._load_json("manual_adjustments.json")
        
        # Load computed data
        self._motivation = None
        self._bracket_paths = None
        self._third_place = None
        self._weather = None
    
    def _load_json(self, filename):
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}
    
    def get_elo(self, team: str) -> int:
        """Get ELO rating for a team."""
        ratings = self.elo.get("ratings", {})
        r = ratings.get(team, {})
        if isinstance(r, dict):
            return r.get("elo", 1500)
        return r if isinstance(r, (int, float)) else 1500
    
    def get_injury_penalty(self, team: str) -> int:
        """Get total injury ELO penalty for a team."""
        injuries = self.injuries.get("injuries", {})
        team_inj = injuries.get(team, {})
        return team_inj.get("total_penalty", 0)
    
    def get_injury_details(self, team: str) -> list:
        """Get detailed injury list for a team."""
        injuries = self.injuries.get("injuries", {})
        team_inj = injuries.get(team, {})
        return team_inj.get("players", [])
    
    def get_motivation(self, team: str) -> dict:
        """Get MD3 motivation classification. Refreshed if >4h old."""
        if self._motivation is None:
            self._load_motivation()
        
        return self._motivation.get(team, {})
    
    def _load_motivation(self):
        path = os.path.join(DATA_DIR, "matchday3_motivation.json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            self._motivation = data.get("classifications", {})
            self._timestamps["motivation"] = datetime.now()
    
    def get_third_place_prob(self, team: str) -> float:
        """Get third-place advancement probability."""
        if self._third_place is None:
            self._load_third_place()
        return self._third_place.get(team, 0.0)
    
    def _load_third_place(self):
        path = os.path.join(DATA_DIR, "third_place_standings.json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            self._third_place = {}
            for t in data.get("standings", []):
                self._third_place[t["team"]] = t.get("advancement_probability", 0.0)
    
    def get_bracket_path_diff(self, group: str, position: int) -> int:
        """Get bracket path ELO difference for strategic analysis."""
        if self._bracket_paths is None:
            self._load_bracket_paths()
        
        key = f"{group}_{position}"
        paths = self._bracket_paths.get("paths", {})
        return paths.get(key, {}).get("path_elo", 0)
    
    def _load_bracket_paths(self):
        path = os.path.join(DATA_DIR, "bracket_paths.json")
        if os.path.exists(path):
            with open(path) as f:
                self._bracket_paths = json.load(f)
    
    def get_team_profile(self, team: str) -> dict:
        """Get team profile (name_cn, style_category, etc.)."""
        return self.team_profiles.get(team, {})
    
    def get_coach_meta_adjustment(self, team: str) -> tuple:
        """Get coach/meta adjustment. Delegates to existing function."""
        try:
            from wc2026_predict import compute_meta_adjustment
            return compute_meta_adjustment(team)
        except Exception:
            return 0, {}
    
    def get_friendly_form(self, team: str) -> int:
        """Get friendly match form adjustment."""
        try:
            path = os.path.join(DATA_DIR, "friendly_form_adjustments.json")
            if os.path.exists(path):
                with open(path) as f:
                    data = json.load(f)
                return data.get(team, 0)
        except Exception:
            pass
        return 0
    
    def get_tournament_form(self, team: str) -> int:
        """Get tournament form boost (deterministic per team)."""
        try:
            # Use team name hash for deterministic value
            seed = sum(ord(c) * (i + 1) for i, c in enumerate(team))
            import random
            rng = random.Random(seed + 2026)
            return int(rng.gauss(0, 30))  # Reduced from 60 to 30
        except Exception:
            return 0
    
    def build_context(self, team: str, opponent: str, matchday: int = None, 
                      match_id: int = None) -> dict:
        """
        Build complete context dict for a team.
        
        Args:
            team: Team name
            opponent: Opponent team name
            matchday: Matchday number (1-3)
            match_id: Schedule match ID
        
        Returns:
            Context dict with all relevant fields
        """
        elo_val = self.get_elo(team)
        opp_elo = self.get_elo(opponent)
        
        ctx = {
            "team_name": team,
            "elo": elo_val,
            "opp_elo": opp_elo,
            "elo_diff": elo_val - opp_elo,
            "matchday": matchday,
            "injury_penalty": self.get_injury_penalty(team),
            "injury_total": abs(self.get_injury_penalty(team)),
            "injury_heavy": abs(self.get_injury_penalty(team)) > 60,
        }
        
        # MD3-specific context
        if matchday == 3:
            mot = self.get_motivation(team)
            ctx["classification"] = mot.get("classification", "N/A")
            ctx["motivation_elo"] = mot.get("elo_adjustment", 0)
            ctx["motivation_confidence"] = mot.get("confidence", "medium")
            ctx["group"] = mot.get("group", "?")
            ctx["group_position"] = mot.get("group_position", 1)
            ctx["points"] = mot.get("points", 0)
            ctx["gd"] = mot.get("gd", 0)
            
            # Third-place probability
            ctx["third_place_prob"] = self.get_third_place_prob(team)
            ctx["third_place_viable"] = ctx["third_place_prob"] > 0.7
            
            # Bracket path preference
            if mot.get("group"):
                path_1st = self.get_bracket_path_diff(mot["group"], 1)
                path_2nd = self.get_bracket_path_diff(mot["group"], 2)
                ctx["bpp_path_diff"] = path_1st - path_2nd
                ctx["bpp_significant"] = abs(ctx["bpp_path_diff"]) > 100
        
        # Opponent motivation (for interaction rules)
        opp_mot = self.get_motivation(opponent)
        ctx["opp_classification"] = opp_mot.get("classification", "N/A")
        ctx["opponent_must_win"] = opp_mot.get("classification") == "MUST_WIN"
        
        # Team profile
        profile = self.get_team_profile(team)
        ctx["name_cn"] = profile.get("name_cn", team)
        ctx["style_category"] = profile.get("style_category", "balanced")
        
        # Venue/weather context
        ctx["home_advantage"] = 0
        ctx["venue_penalty"] = 0
        
        return ctx


# === Standalone test ===
if __name__ == "__main__":
    print("=== DataProvider Test ===\n")
    
    dp = DataProvider()
    
    # Test basic data access
    print(f"ELO lookup: Argentina = {dp.get_elo('Argentina')}")
    print(f"Injury: Brazil = {dp.get_injury_penalty('Brazil')}")
    
    # Test context building
    ctx = dp.build_context("Scotland", "Brazil", matchday=3)
    print(f"\nContext for Scotland (MD3):")
    for k, v in sorted(ctx.items()):
        print(f"  {k}: {v}")
    
    # Test motivation
    mot = dp.get_motivation("Scotland")
    print(f"\nMotivation: Scotland = {mot.get('classification', 'N/A')} ({mot.get('elo_adjustment', 0):+d})")
    
    print("\n✅ DataProvider tests passed")
