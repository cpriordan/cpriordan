"""
Score the committed URL-categorizer corpus with the CURRENT categorizer and
append the key stats to a history file, so categorizer accuracy can be tracked
over time and compared run-to-run.

This is the longitudinal tracker (not a pass/fail gate -- that's
`test_url_categorizer_corpus.py`). Run it after changing `categorize_url` or
regenerating the corpus to record where things stand:

    python tests/getads/score_url_corpus.py

History (append-only, committed): tests/getads/results/url_categorizer_history.jsonl
Each line:
  {date, branch, commit, corpus_rows, accuracy, coverage, precision,
   per_category_recall:{cat: recall}}
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from collections import Counter

sys.path.append(r'C:\Source\ga')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ga.settings')
import django  # noqa: E402
django.setup()

from google_tools import predict_url_category  # noqa: E402

HERE = os.path.dirname(__file__)
CORPUS_PATH = os.path.join(HERE, 'fixtures', 'url_categorizer_corpus.jsonl')
HISTORY_PATH = os.path.join(HERE, 'results', 'url_categorizer_history.jsonl')

PER_CATEGORY_MIN_ROWS = 5   # only record recall for reasonably-represented categories


def git(*args):
    try:
        return subprocess.check_output(['git', *args], cwd=r'C:\Source\ga',
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def load_corpus():
    with open(CORPUS_PATH, encoding='utf-8') as f:
        rows = [json.loads(line) for line in f if line.strip()]
    # score with co=None, so the biz path can't fire -- non-biz rows only
    return [r for r in rows if not r.get('is_biz')]


def score(rows):
    n = len(rows)
    correct = made = 0
    per_total = Counter()
    per_hit = Counter()
    for r in rows:
        d = predict_url_category(r['url'], co=None)
        pred = (d.get('guessed_category') or '').strip().lower()
        sub = (d.get('guessed_subcategory') or '').strip().lower()
        gold = r['expected_category']
        per_total[gold] += 1
        if pred:
            made += 1
        if pred == gold or sub == gold:
            correct += 1
            per_hit[gold] += 1
    per_recall = {
        cat: round(per_hit[cat] / tot, 4)
        for cat, tot in per_total.items() if tot >= PER_CATEGORY_MIN_ROWS
    }
    return {
        'corpus_rows': n,
        'accuracy': round(correct / n, 4) if n else 0.0,
        'coverage': round(made / n, 4) if n else 0.0,
        'precision': round(correct / made, 4) if made else 0.0,
        'per_category_recall': dict(sorted(per_recall.items())),
    }


def previous_record():
    if not os.path.exists(HISTORY_PATH):
        return None
    prev = None
    with open(HISTORY_PATH, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                prev = json.loads(line)
    return prev


def fmt_delta(cur, prev, key):
    c = cur.get(key)
    if prev is None or prev.get(key) is None:
        return f"{c:.4f}  (no prior)"
    d = c - prev[key]
    arrow = '▲' if d > 0 else ('▼' if d < 0 else '=')
    return f"{c:.4f}  ({arrow}{d:+.4f} vs {prev[key]:.4f})"


def main():
    rows = load_corpus()
    metrics = score(rows)
    record = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'branch': git('rev-parse', '--abbrev-ref', 'HEAD'),
        'commit': git('rev-parse', '--short', 'HEAD'),
        **metrics,
    }

    prev = previous_record()
    print(f"=== URL categorizer score ({record['date']} {record['branch']}@{record['commit']}) ===")
    print(f"  corpus rows (non-biz): {record['corpus_rows']}")
    for key in ('accuracy', 'coverage', 'precision'):
        print(f"  {key:10s} {fmt_delta(record, prev, key)}")

    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    print(f"\nappended record -> {HISTORY_PATH}")


if __name__ == '__main__':
    main()
