"""
Generate the URL-categorizer ground-truth corpus from dev-DB AdCopy records.

Each AdCopy points its `link` at a product page and is tagged with the product
via `keyword_group`. Because `keyword_group.keyword` is the SAME vocabulary that
`categorize_url` emits (its `guessed_category` values are KG keywords), the link
-> keyword_group pair is apples-to-apples ground truth with no alias map needed.

We keep only "real product" pages:
  - link present and http/relative,
  - keyword_group set AND is_core_product=True (drops geo/segment KGs like
    'otsego county', 'membership', 'refer a friend'),
  - NOT an apply/open/funnel link and NOT a known LOS / online-banking host
    (those are opaque application URLs, not product landing pages).

Output: tests/getads/fixtures/url_categorizer_corpus.jsonl
  one row: {"url", "expected_category", "is_biz", "company_code", "source"}

Run:
    python tests/getads/build_url_corpus.py
"""

import os
import sys
import json
from collections import Counter

sys.path.append(r'C:\Source\ga')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ga.settings')
import django  # noqa: E402
django.setup()

from app.models import AdCopy  # noqa: E402
from google_tools import predict_url_category  # noqa: E402

DB = 'dev'

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'url_categorizer_corpus.jsonl')

# apply/open/funnel tokens and known LOS / online-banking hosts to exclude
APPLY_TOKENS = ['apply', '/open', 'open-', 'openaccount', 'enroll', 'login', 'logout',
                'onlineserv', 'account-open', 'funnel', 'oao', '/olb']
LOS_HOSTS = ['loanspq.com', 'mortgagewebcenter', 'mortgage-application', 'meridianlink',
             'app.loanspq', 'banno', 'narmi', 'q2online', 'digitalbanking', 'secure.']


def is_excluded(url):
    u = (url or '').lower()
    return any(t in u for t in APPLY_TOKENS) or any(h in u for h in LOS_HOSTS)


def build_rows():
    qs = (AdCopy.objects.using(DB)
          .exclude(link__isnull=True).exclude(link='')
          .exclude(keyword_group__isnull=True)
          .filter(keyword_group__is_core_product=True)
          .select_related('keyword_group', 'company'))

    seen = {}
    excluded = 0
    for a in qs.iterator():
        link = (a.link or '').strip()
        if not (link.lower().startswith('http') or link.startswith('/')):
            continue
        if is_excluded(link):
            excluded += 1
            continue
        gold = (a.keyword_group.keyword or '').strip().lower()
        if not gold:
            continue
        if link not in seen:
            seen[link] = {
                'url': link,
                'expected_category': gold,
                'is_biz': bool(a.is_biz),
                'company_code': a.company.code if a.company else None,
                'source': 'adcopy',
            }
    return list(seen.values()), excluded


def report(rows):
    n = len(rows)
    dist = Counter(r['expected_category'] for r in rows)
    biz = sum(1 for r in rows if r['is_biz'])
    print(f"\ncorpus rows: {n}  (is_biz: {biz})")
    print(f"distinct categories: {len(dist)}")
    print(f"top categories: {dist.most_common(30)}")

    # baseline accuracy (co=None) on non-biz rows, granularity tolerant
    n2 = cat_hit = tol_hit = made = 0
    per_total = Counter(); per_hit = Counter()
    for r in rows:
        if r['is_biz']:
            continue
        n2 += 1
        d = predict_url_category(r['url'], co=None)
        pred = (d.get('guessed_category') or '').strip().lower()
        sub = (d.get('guessed_subcategory') or '').strip().lower()
        gold = r['expected_category']
        per_total[gold] += 1
        if pred:
            made += 1
        hit = (pred == gold or sub == gold)
        if pred == gold:
            cat_hit += 1
        if hit:
            tol_hit += 1
            per_hit[gold] += 1
    print(f"\n--- baseline (non-biz, co=None, n={n2}) ---")
    print(f"  category-exact accuracy:        {cat_hit/n2:.3f} ({cat_hit}/{n2})")
    print(f"  granularity-tolerant accuracy:  {tol_hit/n2:.3f} ({tol_hit}/{n2})")
    print(f"  coverage (predictions made):    {made/n2:.3f} ({made}/{n2})")
    print(f"  precision (of predictions):     {tol_hit/made:.3f} ({tol_hit}/{made})")
    print("  per-category recall (>=5 rows):")
    for cat, tot in per_total.most_common():
        if tot >= 5:
            print(f"     {cat:28s} {per_hit[cat]/tot:.2f} ({per_hit[cat]}/{tot})")


def main():
    rows, excluded = build_rows()
    print(f"excluded apply/open/LOS links: {excluded}")
    report(rows)
    os.makedirs(os.path.dirname(FIXTURE), exist_ok=True)
    # deterministic order for a stable committed fixture
    rows.sort(key=lambda r: (r['expected_category'], r['url']))
    with open(FIXTURE, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f"\nwrote {len(rows)} rows -> {FIXTURE}")


if __name__ == '__main__':
    main()
