#!/usr/bin/env python3.11
"""同步 skills/ 到 ~/.hermes/skills/"""
import os, shutil, subprocess

WS_SKILLS = os.path.expanduser("~/wuhoo-workspace/skills")
HERMES_SKILLS = os.path.expanduser("~/.hermes/skills")

def sync():
    """尝试 skills tap add，失败则手动复制"""
    # Try skills tap add first
    r = subprocess.run("hermes skills tap add ~/wuhoo-workspace 2>&1", shell=True, capture_output=True, text=True)
    if r.returncode == 0 and ("added" in r.stdout.lower() or "added" in r.stderr.lower()):
        print("Skills tap registered successfully")
        return
    
    # Fallback: manual copy
    print("Tap add not available, using manual sync...")
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
