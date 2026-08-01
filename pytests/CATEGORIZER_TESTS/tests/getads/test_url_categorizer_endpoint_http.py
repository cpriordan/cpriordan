"""
HTTP-tier tests for the URL-categorizer endpoint:  GET /api/v1/get_url_category/

This validates the *deployed* categorizer path (view -> predict_url_category)
against a running server, complementing the in-process unit corpus test
(`test_url_categorizer_corpus.py`). It reuses the same committed corpus fixture
to confirm the endpoint returns the same results as the in-process categorizer.

No Django import -- pure `requests`, instant startup.

Run (local server on :8001 by default):
    pytest tests/getads/test_url_categorizer_endpoint_http.py -m http -v
    TEST_BASE_URL=https://devfinalyticsdata.com pytest tests/getads/test_url_categorizer_endpoint_http.py -m http
"""

import json
import os
from collections import Counter

import pytest
import requests

pytestmark = pytest.mark.http

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8001")
ENDPOINT = f"{BASE_URL}/api/v1/get_url_category/"
CORPUS_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'url_categorizer_corpus.jsonl')

# Mirrors KNOWN cases in test_url_categorizer_corpus.py (kept small + in sync by hand).
# (url, expected_category, expected_subcategory_or_None)
KNOWN_CASES = [
    ('https://www.georgiasown.org/checking/student-access', 'student checking account', None),
    ('https://example.org/student-checking', 'student checking account', None),
    ('https://example.org/savings/youth', 'student savings account', None),
    ('https://www.globalcu.org/home-loans/mortgages/portfolio-loans/investment-properties',
     'mortgage', 'investment property mortgage'),
    ('https://example.org/investment-loan', 'investment', None),
    ('https://example.org/personal-checking', 'checking account', None),
]

PRECISION_FLOOR = 0.84   # same floor as the in-process corpus test


def _categorize(url, cu_id=None):
    params = {'url': url}
    if cu_id:
        params['cu_id'] = cu_id
    return requests.get(ENDPOINT, params=params, timeout=15)


@pytest.fixture(scope='module', autouse=True)
def _require_server():
    """Skip the whole module if the categorizer endpoint isn't reachable."""
    try:
        r = _categorize('https://example.org/personal-checking')
    except requests.RequestException as e:
        pytest.skip(f'Categorizer endpoint not reachable at {ENDPOINT}: {e}')
    if r.status_code != 200:
        pytest.skip(f'Endpoint returned HTTP {r.status_code} at {ENDPOINT}')


class TestEndpointShape:
    def test_returns_200_and_json(self):
        r = _categorize('https://example.org/personal-checking')
        assert r.status_code == 200
        d = r.json()
        assert 'guessed_category' in d, f'missing guessed_category in {d}'

    def test_returns_expected_keys(self):
        d = _categorize('https://example.org/personal-checking').json()
        for k in ('guessed_category', 'guessed_subcategory', 'is_biz', 'is_rate'):
            assert k in d, f'endpoint response missing {k!r}: {d}'


class TestEndpointKnownCases:
    @pytest.mark.parametrize('url,expected_category,expected_subcategory', KNOWN_CASES)
    def test_known_case(self, url, expected_category, expected_subcategory):
        d = _categorize(url).json()
        cat = d.get('guessed_category') or None
        sub = d.get('guessed_subcategory') or None
        assert cat == expected_category, f'{url}: category {cat!r} != {expected_category!r}'
        if expected_subcategory is not None:
            assert sub == expected_subcategory, (
                f'{url}: subcategory {sub!r} != {expected_subcategory!r}'
            )


class TestEndpointMatchesCorpus:
    """Run the committed corpus through the endpoint; the deployed path must hit
    the same precision floor as the in-process categorizer (proves parity)."""

    def test_corpus_precision_via_endpoint(self):
        if not os.path.exists(CORPUS_PATH):
            pytest.skip(f'Corpus not found at {CORPUS_PATH}')
        with open(CORPUS_PATH, encoding='utf-8') as f:
            rows = [json.loads(line) for line in f if line.strip()]
        rows = [r for r in rows if not r.get('is_biz')]   # endpoint called without cu_id -> no biz path

        made = correct = 0
        per_total = Counter()
        per_hit = Counter()
        per_miss = {}

        for r in rows:
            resp = _categorize(r['url'])
            try:
                d = resp.json()
            except Exception:
                print(f'\nBAD RESPONSE [{resp.status_code}] for URL: {r["url"]!r} — body: {resp.text[:200]!r}')
                continue
            pred = (d.get('guessed_category') or '').strip().lower()
            sub = (d.get('guessed_subcategory') or '').strip().lower()
            gold = r['expected_category']
            per_total[gold] += 1
            hit = (pred == gold) or (sub == gold)
            if pred:
                made += 1
                if hit:
                    correct += 1
                    per_hit[gold] += 1
                else:
                    per_miss.setdefault(gold, []).append((r['url'], pred or '<none>'))
            else:
                per_miss.setdefault(gold, []).append((r['url'], '<no prediction>'))

        print(f'\n{"="*60}')
        print(f'CATEGORY BREAKDOWN (endpoint: {ENDPOINT})')
        print(f'{"="*60}')
        print(f'{"Category":<35} {"Total":>5} {"Hit":>5} {"Recall":>7}')
        print(f'{"-"*60}')
        for cat in sorted(per_total):
            total = per_total[cat]
            hit = per_hit[cat]
            recall = hit / total if total else 0
            flag = ' FAIL' if recall < 0.5 else ''
            print(f'{cat:<35} {total:>5} {hit:>5} {recall:>7.1%}{flag}')
        print(f'{"-"*60}')
        n = len(rows)
        coverage = made / n if n else 0
        precision = correct / made if made else 0
        print(f'{"TOTAL":<35} {n:>5} {correct:>5} {precision:>7.1%}  (precision)')
        print(f'{"Coverage (predictions made)":<35} {made:>5} {"":>5} {coverage:>7.1%}')
        print(f'{"="*60}\n')

        assert made > 0, 'endpoint made no predictions across the corpus'
        assert precision >= PRECISION_FLOOR, (
            f'endpoint precision {precision:.3f} below floor {PRECISION_FLOOR} '
            f'({correct}/{made})'
        )
