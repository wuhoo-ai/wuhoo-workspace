#!/usr/bin/env python3.11
"""同步 skills/ 到 ~/.hermes/skills/"""
import os, shutil, subprocess

WS_SKILLS = os.path.expanduser("~/wuhoo-workspace/skills")
HERMES_SKILLS = os.path.expanduser("~/.hermes/skills")

def sync():
    """Use skills tap add to link workspace skills"""
    for skill_dir in os.listdir(WS_SKILLS):
        skill_path = os.path.join(WS_SKILLS, skill_dir)
        if os.path.isdir(skill_path) and os.path.exists(os.path.join(skill_path, "SKILL.md")):
            print(f"  Syncing {skill_dir}...")
            dest = os.path.join(HERMES_SKILLS, f"wuhoo-{skill_dir}")
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(skill_path, dest,
                          ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', 'venv', 'venv-futu', '*.pyc'))
    print("Sync complete. Run 'hermes skills list' to verify.")

if __name__ == "__main__":
    sync()
