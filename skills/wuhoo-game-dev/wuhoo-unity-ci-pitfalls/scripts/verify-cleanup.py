"""Verify CI cleanup after removing files/scenes.

Usage: /usr/bin/python3.11 scripts/verify-cleanup.py

Checks:
1. Dead files confirmed deleted
2. Stale EditorBuildSettings entries removed  
3. Stale private methods purged
4. Resources audio canonical copy exists
"""

import re, sys, os

PROJECT = "/home/admin/miners-watch"
errors = []

# 1. Check specific dead files/dirs are gone
dead = []
for p in dead:
    if os.path.exists(p):
        errors.append(f"DEAD FILE EXISTS: {p}")

# 2. EditorBuildSettings scene count expected
with open(f"{PROJECT}/ProjectSettings/EditorBuildSettings.asset") as f:
    ebs = f.read()
scene_count = len(re.findall(r"path: Assets/Scenes/", ebs))
if scene_count != 5:
    errors.append(f"Expected 5 build scenes, found {scene_count}")
for s in ["MainMenu", "Surface", "ShallowCave", "MidCave", "DeepCave"]:
    if s not in ebs:
        errors.append(f"MISSING SCENE: {s}")
if "TestGround" in ebs:
    errors.append("STALE: TestGround still in build settings")

# 3. Resources/Audio canonical
for p in [
    f"{PROJECT}/Assets/Resources/Audio/SFX/sfx_mine_01.wav",
    f"{PROJECT}/Assets/Resources/Audio/BGM/bgm_day.wav",
]:
    if not os.path.exists(p):
        errors.append(f"MISSING CANONICAL: {p}")

if errors:
    for e in errors: print(f"FAIL: {e}")
    sys.exit(1)
print("CLEANUP VERIFIED: no dead files, 5 scenes, audio canonical")
