"""wuhoo-news-intel 测试套件 — 路径注入"""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR / "src"))
sys.path.insert(0, str(SKILL_DIR / "scripts"))
