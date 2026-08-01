"""
Comprehensive regression test for the URL auto-categorizer
(`google_tools.predict_url_category` -> `segment_url` + `categorize_url`).

The corpus is real client AdCopy links from the dev DB, each labeled with the
product the AdCopy is tagged with (`keyword_group.keyword`). That label is the
SAME vocabulary `categorize_url` emits, so comparison is apples-to-apples with no
alias map. Regenerate with:

    python tests/getads/build_url_corpus.py

Baselines anchored to the corpus as of 2026-06-03 (303 rows, non-biz n=290):
accuracy 0.666, coverage 0.745, precision 0.894. Floors are set a few points
under baseline to catch real regressions without false alarms from minor drift.

The dominant failure mode of this categorizer is COVERAGE (URLs with no product
tokens -> no category), not PRECISION (when it predicts, it is ~89% right), so we
assert the two separately; precision is the primary anti-regression guard.

heloc vs home equity loan are scored as DISTINCT products (no alias) per product
guidance -- the correct per-URL gold is verified against the live client page
during tuning, not blanket-aliased here.

Run:
    pytest tests/getads/test_url_categorizer_corpus.py -m unit -v
"""

import json
import os
from collections import Counter

import pytest

from google_tools import predict_url_category

pytestmark = pytest.mark.unit

CORPUS_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'url_categorizer_corpus.jsonl')

# Floors (~3-5 pts under the 2026-06-03 baseline)
OVERALL_ACCURACY_FLOOR = 0.62     # baseline 0.666
COVERAGE_FLOOR = 0.68             # baseline 0.745
PRECISION_FLOOR = 0.84            # baseline 0.894
# no category with >= this many rows may collapse below this recall
NO_COLLAPSE_MIN_ROWS = 10
NO_COLLAPSE_RECALL_FLOOR = 0.40   # lowest big-category baseline (home equity loan) is 0.54


@pytest.fixture(scope='module')
def corpus():
    if not os.path.exists(CORPUS_PATH):
        pytest.skip(
            f'Corpus not found at {CORPUS_PATH}. '
            f'Generate with: python tests/getads/build_url_corpus.py'
        )
    with open(CORPUS_PATH, encoding='utf-8') as f:
        rows = [json.loads(line) for line in f if line.strip()]
    # unit test scores with co=None, so the biz path can't fire -- exclude biz rows
    return [r for r in rows if not r.get('is_biz')]


@pytest.fixture(scope='module')
def scored(corpus):
    """Categorize every corpus URL once; reuse across tests.

    Returns list of (row, predicted_category, predicted_subcategory, is_hit).
    Match is granularity-tolerant: gold may be a category or a subcategory.
    """
    results = []
    for r in corpus:
        d = predict_url_category(r['url'], co=None)
        pred = (d.get('guessed_category') or '').strip().lower()
        sub = (d.get('guessed_subcategory') or '').strip().lower()
        gold = r['expected_category']
        is_hit = (pred == gold) or (sub == gold)
        results.append((r, pred, sub, is_hit))
    return results


class TestCorpusOverall:
    def test_corpus_has_volume(self, corpus):
        assert len(corpus) >= 200, f'Corpus too small: {len(corpus)} rows'

    def test_never_raises(self, scored):
        # If predict_url_category threw on any URL the `scored` fixture would have
        # errored building; reaching here means every URL categorized cleanly.
        assert len(scored) > 0

    def test_overall_accuracy_above_floor(self, scored):
        n = len(scored)
        correct = sum(1 for *_, hit in scored if hit)
        rate = correct / n
        assert rate >= OVERALL_ACCURACY_FLOOR, (
            f'Accuracy {rate:.3f} below floor {OVERALL_ACCURACY_FLOOR} ({correct}/{n})'
        )

    def test_coverage_above_floor(self, scored):
        n = len(scored)
        made = sum(1 for _, pred, *_ in scored if pred)
        rate = made / n
        assert rate >= COVERAGE_FLOOR, (
            f'Coverage {rate:.3f} below floor {COVERAGE_FLOOR} ({made}/{n})'
        )

    def test_precision_above_floor(self, scored):
        """Of the predictions actually made, how many are right. This is the
        primary guard: the categorizer must not start mislabeling products."""
        made = [(r, pred, sub, hit) for (r, pred, sub, hit) in scored if pred]
        if not made:
            pytest.fail('No predictions made at all')
        correct = sum(1 for *_, hit in made if hit)
        rate = correct / len(made)
        assert rate >= PRECISION_FLOOR, (
            f'Precision {rate:.3f} below floor {PRECISION_FLOOR} '
            f'({correct}/{len(made)})'
        )


class TestCorpusPerCategory:
    def test_no_category_collapses(self, scored):
        """No well-represented product category may drop below the recall floor.
        Catches the 'one product broke' case overall accuracy would mask."""
        total = Counter()
        hit = Counter()
        for r, _pred, _sub, is_hit in scored:
            cat = r['expected_category']
            total[cat] += 1
            if is_hit:
                hit[cat] += 1

        weak = []
        for cat, tot in total.items():
            if tot >= NO_COLLAPSE_MIN_ROWS:
                recall = hit[cat] / tot
                if recall < NO_COLLAPSE_RECALL_FLOOR:
                    weak.append((cat, recall, hit[cat], tot))

        assert not weak, (
            f'Categories below recall floor {NO_COLLAPSE_RECALL_FLOOR}:\n  '
            + '\n  '.join(f'{c}: {r:.3f} ({h}/{t})' for c, r, h, t in weak)
        )

    @pytest.mark.parametrize('category,floor', [
        ('cd',               0.70),   # baseline 0.79
        ('savings account',  0.72),   # baseline 0.85
        ('boat loan',        0.60),   # baseline 0.73
        ('credit card',      0.62),   # baseline 0.73
        ('mortgage',         0.58),   # baseline 0.70
        ('car loan',         0.50),   # baseline 0.61
    ])
    def test_category_specific_recall(self, scored, category, floor):
        total = correct = 0
        for r, _pred, _sub, is_hit in scored:
            if r['expected_category'] == category:
                total += 1
                if is_hit:
                    correct += 1
        if total == 0:
            pytest.skip(f'No rows for category {category}')
        recall = correct / total
        assert recall >= floor, (
            f'{category} recall {recall:.3f} below floor {floor} ({correct}/{total})'
        )


class TestCorpusShape:
    def test_required_fields_present(self, corpus):
        required = {'url', 'expected_category', 'is_biz', 'source'}
        missing = required - set(corpus[0].keys())
        assert not missing, f'Corpus missing fields: {missing}'

    def test_urls_nonempty(self, corpus):
        bad = [r for r in corpus if not (r['url'] or '').strip()]
        assert not bad, f'{len(bad)} rows with empty url'

    def test_labels_lowercased(self, corpus):
        bad = [r for r in corpus if r['expected_category'] != r['expected_category'].lower()]
        assert not bad, f'{len(bad)} labels not normalized to lowercase'


class TestKnownCases:
    """Hand-picked URLs guarding specific categorizer fixes that the AdCopy
    corpus doesn't cover (funnel-excluded links or products absent from ad
    inventory). subcategory is only asserted when an expected value is given."""

    @pytest.mark.parametrize('url,expected_category,expected_subcategory', [
        # ECGC-3167: student/youth deposit pages. 'checking' can sit in a
        # non-last path segment, and youth savings now maps to the real KG.
        ('https://www.georgiasown.org/checking/student-access', 'student checking account', None),
        ('https://www.georgiasown.org/checking/student', 'student checking account', None),
        ('https://example.org/student-checking', 'student checking account', None),
        ('https://example.org/savings/youth', 'student savings account', None),
        ('https://example.org/youth-savings', 'student savings account', None),

        # investment-property loan/mortgage -> mortgage / investment property mortgage
        ('https://www.globalcu.org/home-loans/mortgages/portfolio-loans/investment-properties',
         'mortgage', 'investment property mortgage'),
        ('https://example.org/loans/investment-property-loan', 'mortgage', 'investment property mortgage'),
        ('https://example.org/mortgages/investment-property', 'mortgage', 'investment property mortgage'),
        # false-positive guard: a plain investment loan is NOT a property mortgage
        ('https://example.org/investment-loan', 'investment', None),

        # plain deposit regressions
        ('https://example.org/personal-checking', 'checking account', None),
        ('https://example.org/savings-accounts', 'savings account', None),
    ])
    def test_known_url_category(self, url, expected_category, expected_subcategory):
        d = predict_url_category(url, co=None)
        cat = d.get('guessed_category') or None
        sub = d.get('guessed_subcategory') or None
        assert cat == expected_category, f'{url}: category {cat!r} != {expected_category!r}'
        if expected_subcategory is not None:
            assert sub == expected_subcategory, (
                f'{url}: subcategory {sub!r} != {expected_subcategory!r}'
            )
