#!/usr/bin/env python3
import json
import sys
from pathlib import Path

KNOWN_TARGETS = Path.home() / ".openclaw" / "qqbot" / "data" / "known-targets.json"


def norm(s: str) -> str:
    return (s or "").strip().casefold()


def load_targets(account_id: str | None = None):
    if not KNOWN_TARGETS.exists():
        return []
    with KNOWN_TARGETS.open("r", encoding="utf-8") as f:
        data = json.load(f)
    items = data if isinstance(data, list) else []
    if account_id:
        account_norm = norm(account_id)
        items = [item for item in items if norm(str(item.get("accountId", ""))) == account_norm]
    return items


def score(entry, query: str):
    q = norm(query)
    name = norm(entry.get("displayName", ""))
    target = norm(entry.get("target", ""))
    if not q:
        return -1
    if name == q:
        return 300
    if target == q:
        return 290
    if q in name and name:
        return 200 - (len(name) - len(q))
    if q in target and target:
        return 180 - (len(target) - len(q))
    return -1


def main():
    if len(sys.argv) < 2:
        print("Usage: resolve_known_target.py <query> [--account-id <id>]", file=sys.stderr)
        sys.exit(2)

    query = sys.argv[1]
    account_id = None
    if len(sys.argv) >= 4 and sys.argv[2] == "--account-id":
        account_id = sys.argv[3]
    items = load_targets(account_id)
    ranked = []
    for item in items:
        s = score(item, query)
        if s >= 0:
            ranked.append((s, int(item.get("lastSeenAt", 0) or 0), item))

    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    out = []
    for s, _, item in ranked:
        out.append({
            "score": s,
            "displayName": item.get("displayName"),
            "target": item.get("target"),
            "accountId": item.get("accountId"),
            "kind": item.get("kind"),
            "lastSeenAt": item.get("lastSeenAt"),
            "sourceChatType": item.get("sourceChatType"),
        })
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
