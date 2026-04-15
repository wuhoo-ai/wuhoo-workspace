#!/usr/bin/env python3
import json
import sys
from pathlib import Path

KNOWN_TARGETS = Path.home() / '.openclaw' / 'qqbot' / 'data' / 'known-targets.json'


def norm(s: str) -> str:
    return (s or '').strip().casefold()


def load_targets(account_id: str | None = None):
    if not KNOWN_TARGETS.exists():
        return []
    with KNOWN_TARGETS.open('r', encoding='utf-8') as f:
        data = json.load(f)
    items = data if isinstance(data, list) else []
    if account_id:
        account_norm = norm(account_id)
        items = [item for item in items if norm(str(item.get('accountId', ''))) == account_norm]
    return items


def score(entry, query: str):
    q = norm(query)
    name = norm(entry.get('displayName', ''))
    target = norm(entry.get('target', ''))
    if not q:
        return -1
    if name == q:
        return 300
    if target == q:
        return 290
    if q in name and name:
        return 200 - max(0, len(name) - len(q))
    if q in target and target:
        return 180 - max(0, len(target) - len(q))
    return -1


def ranked_matches(query: str, account_id: str | None = None):
    items = load_targets(account_id)
    ranked = []
    for item in items:
        s = score(item, query)
        if s >= 0:
            ranked.append((s, int(item.get('lastSeenAt', 0) or 0), item))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    out = []
    for s, _, item in ranked:
        out.append({
            'score': s,
            'displayName': item.get('displayName'),
            'target': item.get('target'),
            'accountId': item.get('accountId'),
            'kind': item.get('kind'),
            'lastSeenAt': item.get('lastSeenAt'),
            'sourceChatType': item.get('sourceChatType'),
        })
    return out


def usage():
    print('Usage:', file=sys.stderr)
    print('  prepare_send.py <recipient> [--account-id <id>] --file <path> [--caption <text>]', file=sys.stderr)
    print('  prepare_send.py <recipient> [--account-id <id>] --text <message>', file=sys.stderr)


def main():
    if len(sys.argv) < 4:
        usage()
        sys.exit(2)

    recipient = sys.argv[1]
    args = sys.argv[2:]
    file_path = None
    caption = None
    text = None
    account_id = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == '--account-id' and i + 1 < len(args):
            account_id = args[i + 1]
            i += 2
        elif a == '--file' and i + 1 < len(args):
            file_path = args[i + 1]
            i += 2
        elif a == '--caption' and i + 1 < len(args):
            caption = args[i + 1]
            i += 2
        elif a == '--text' and i + 1 < len(args):
            text = args[i + 1]
            i += 2
        else:
            usage()
            sys.exit(2)

    if bool(file_path) == bool(text):
        print(json.dumps({'error': 'Provide exactly one of --file or --text'}, ensure_ascii=False, indent=2))
        sys.exit(2)

    matches = ranked_matches(recipient, account_id)
    if not matches:
        print(json.dumps({'status': 'no_match', 'recipient': recipient, 'matches': []}, ensure_ascii=False, indent=2))
        sys.exit(1)

    top = matches[0]
    ambiguous = len(matches) > 1 and matches[1]['score'] == top['score']

    payload = {
        'channel': 'qqbot',
        'target': top['target'],
        'accountId': top['accountId'],
    }
    if file_path:
        p = Path(file_path)
        payload['path'] = str(p)
        payload['pathExists'] = p.exists()
        if caption:
            payload['caption'] = caption
    else:
        payload['message'] = text

    result = {
        'status': 'ambiguous' if ambiguous else 'ok',
        'recipient': recipient,
        'accountScope': account_id,
        'resolved': top,
        'matches': matches[:5],
        'messageToolPayload': payload,
        'note': 'Use message(action=send, ...messageToolPayload) for actual delivery.'
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(3 if ambiguous else 0)


if __name__ == '__main__':
    main()
