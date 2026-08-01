# URL Auto-Categorizer — Test Suite & Accuracy Tracking

**Targets:** `google_tools.py` → `predict_url_category()` → `segment_url()` + `categorize_url()` (+ `biz_categorizer`, `override_categorizer`)
**Test suite:** `tests/getads/test_url_categorizer_corpus.py` · **Corpus generator:** `build_url_corpus.py` · **Accuracy tracker:** `score_url_corpus.py`
**Status:** Implemented v1 — 2026-06-03 (see "Implemented" below). The sections above record the findings and design decisions behind it.

## What exists today (the "old code")

There is **no actual test** for the URL categorizer. What exists:

- **`app/management/commands/categorize_urls.py`** — runs `categorize_url` over every
  `UrlSegment`/`Page` and saves the result. Not a test (no assertions).
- **Labeled CSVs** in `app/data/keywords/`:
  | file | rows | columns |
  |---|---|---|
  | `initial_run_manual_edits_new_keywords.csv` | 601 | `url, cat` |
  | `url-to-product-name-mapping.csv` | 111 | `url, product_name` |
  | `temp_initial_run_manual_edits.csv` | 640 | `…cat, success, fix, detailed_product…` (has subcategory) |
  | `is_product.csv` | 2551 | `url, is_product` (a *different* classifier) |
- **Dev DB**: `Page` = 8,248 rows (857 `is_reviewed=True`, 2,290 with `category`, only 30
  with `subcategory`); `UrlSegment` = **empty**.

## ⭐ Primary ground-truth source: `AdCopy.link` → `AdCopy.keyword_group` (dev DB)

(Per the idea to test non-apply/open ad links against the product the AdCopy is tagged
with.) This is the **best** corpus because the gold label is `keyword_group.keyword`,
which is the **same vocabulary `categorize_url` emits** (its `guessed_category` values are
KG keywords) — so **no alias/normalization map is needed**, and the labels are
team-curated, not hand-annotated for this test.

**Selection (validated on dev):** `AdCopy` with `link` set, `keyword_group` set and
`keyword_group.is_core_product=True` (scopes to real products, drops geo/segment KGs like
`otsego county`, `membership`, `refer a friend`), excluding apply/open + LOS/app-host
links (`apply`, `open`, `enroll`, `login`, `onlineserv`, `loanspq.com`, `meridianlink`,
`banno`, `narmi`, `q2online`, …). Dedupe by link.

**Measured today (this branch, `co=None`, 362 distinct links):**

| metric | value | notes |
|---|---|---|
| category-exact accuracy | **62.4%** (226/362) | |
| non-biz only | **64.6%** (223/345) | biz needs a `co` |
| coverage (non-`<none>` predictions) | **71.5%** (259/362) | |
| precision of predictions made | **~87%** (226/259) | when it predicts, it's usually right |

**Key insight:** the dominant failure is **coverage, not precision** — 103 of 136 misses
are `<none>` (no product tokens found), and almost no misses are "predicted X but gold was
a different product Y." The few real category disagreements are `heloc` ⇄
`home equity loan` (alias candidate) and biz pages (need `co`). So the test must track
**coverage and precision separately**, not just blended accuracy.

## Secondary sources

- **Labeled CSVs** (above) add domain breadth but use a *different* vocabulary than the
  categorizer output, so they need a canonical alias map (see below). Current measured
  accuracy: ~52% strict / ~66% with partial normalization. Use as a supplementary corpus.
- **Dev `Page.is_reviewed=True`** (857): messy (mixed category/subcategory granularity,
  pattern-only labels like `search`/`login`, biz). Lowest priority.

## Proposed design (mirror `tests/transactions/test_categorizer_corpus.py`)

### 1. Generator → committed fixture (deterministic, no DB at test time)

`tests/getads/build_url_corpus.py` exports the dev AdCopy corpus to
`tests/getads/fixtures/url_categorizer_corpus.jsonl`, one row per link:
`{url, expected_category, is_biz, source:"adcopy"}`. Run on-demand (like
`generate_synthetic_corpus.py`); regenerate as ad inventory grows. Optionally append the
normalized CSV rows behind a flag (`source:"csv"`). Commit the fixture so the test is
reproducible and needs no dev access.

### 2. Canonical alias map (only for the CSV/Page sources)

`tests/getads/url_category_aliases.py` — maps CSV label vocab → KG vocab
(`checking`→`checking account`, `credit cards`→`credit card`, `vehicle loan`→`car loan`,
`investments`→`investment`, …) and an out-of-scope set (`search`, `login`, `banking`,
generic `loan`). The AdCopy corpus bypasses this (already KG vocab); the single arguable
in-vocab alias is `heloc` ⇄ `home equity loan` — decide whether to treat as equal.

### 3. Tests — `tests/getads/test_url_categorizer_corpus.py` (`@pytest.mark.unit`)

Score once in a module fixture via `predict_url_category(url, co=None)` over non-biz rows;
match is granularity-tolerant (canonical `guessed_category` == gold **or**
`guessed_subcategory` == gold). Assertions, with floors anchored ~3 pts under the
re-measured baseline:

- `test_precision_above_floor` — of predictions actually made, ≥ floor (baseline ~87%).
  *This is the anti-regression guard that matters most* — it must not start mislabeling.
- `test_coverage_above_floor` — fraction getting a non-null category ≥ floor (~0.68).
- `test_overall_accuracy_above_floor` — blended (~0.60).
- `test_no_category_collapse` + parametrized per-category recall floors (car loan, cd,
  mortgage, credit card, checking account, …) — catches "one product broke."
- `test_never_raises` — every URL in the corpus categorizes without throwing.

### 4. Biz path — separate `@pytest.mark.integration` test

For `is_biz` rows, pass a `biz_enabled` `co` so `biz_categorizer` runs; assert the biz
categories (`business loan`, `merchant services`, `cash management`, …) resolve. Kept out
of the fast unit corpus.

### 5. Investment-property coverage

The `categorize-url-investment-property.md` change is exercised by corpus rows whose links
point at investment-property loan/mortgage pages → `mortgage` /
`investment property mortgage`; if none exist in the AdCopy set, add a small hand-built
parametrized case so that fix stays regression-guarded. (Replaces the standalone test.)

## Open decisions (need input)

1. **Scope of v1** — ship the **AdCopy corpus only** (clean, no alias map, ~360 rows
   growing) and add the CSV breadth later? Recommended.
2. **`heloc` vs `home equity loan`** — treat as equal in scoring, or keep distinct?
3. **Fixture vs live** — commit a generated JSONL (deterministic, recommended) vs query
   dev at test time (always-current but non-deterministic, needs dev access).

## Tests (this plan's deliverable)

Acceptance: `pytest tests/getads/test_url_categorizer_corpus.py -m unit -v` passes with
precision/coverage/accuracy floors + per-category recall; biz integration test passes;
fixture regenerable via `build_url_corpus.py`.

## Implemented (2026-06-03) — v1 (AdCopy corpus)

Decisions taken: AdCopy corpus only; committed JSONL fixture; `heloc` vs
`home equity loan` kept **distinct** (no alias — correct per-URL gold to be verified
against the live client page during tuning).

- `tests/getads/build_url_corpus.py` — generator; queries dev `AdCopy`
  (`is_core_product` KGs, non-apply/open, non-LOS), dedupes by link →
  `tests/getads/fixtures/url_categorizer_corpus.jsonl` (**303 rows, 33 categories**).
- `tests/getads/test_url_categorizer_corpus.py` — `@pytest.mark.unit`, in-process tests
  (corpus floors + `TestKnownCases` hand-picked regressions). Floors anchored under the
  2026-06-03 baseline (accuracy 0.666, coverage 0.745, precision 0.894): accuracy ≥0.62,
  coverage ≥0.68, precision ≥0.84, no >=10-row category below 0.40 recall, + per-category
  floors.
- `tests/getads/test_url_categorizer_endpoint_http.py` — `@pytest.mark.http`, exercises the
  deployed endpoint `GET /api/v1/get_url_category/` (no-auth GET, params `url` + optional
  `cu_id`). Runs the same known cases and the full corpus through the endpoint and asserts
  parity with the in-process precision floor. Skips if no server is reachable. Defaults to
  `http://localhost:8001`; override with `TEST_BASE_URL` (e.g. a dev/stg data site).
- `tests/getads/score_url_corpus.py` — longitudinal tracker; scores the committed corpus
  with the current categorizer and **appends key stats over time** to
  `tests/getads/results/url_categorizer_history.jsonl` (date, branch, commit, corpus_rows,
  accuracy, coverage, precision, per-category recall) with run-to-run deltas printed.

**Deferred:** biz-path integration test (pass a `biz_enabled` co for `is_biz` rows);
optional CSV-breadth corpus behind an alias map; investment-property explicit cases if not
already represented by AdCopy links.

## Running the tests

```bash
# In-process unit tests (no server needed): corpus floors + known-case regressions
pytest tests/getads/test_url_categorizer_corpus.py -m unit -v

# Endpoint (HTTP) tests against a running server — defaults to http://localhost:8001
TEST_BASE_URL=http://127.0.0.1:8001 pytest tests/getads/test_url_categorizer_endpoint_http.py -m http -v
#   point at a deployed env instead:
TEST_BASE_URL=https://stgfinalyticsdata.com pytest tests/getads/test_url_categorizer_endpoint_http.py -m http -v

# Both together (server up)
TEST_BASE_URL=http://127.0.0.1:8001 pytest tests/getads/test_url_categorizer_corpus.py tests/getads/test_url_categorizer_endpoint_http.py -q

# Regenerate the corpus fixture from dev AdCopy (after ad inventory changes)
python tests/getads/build_url_corpus.py

# Record a stats-over-time data point (run after a categorizer change / commit)
python tests/getads/score_url_corpus.py
```

As of 2026-06-03: **26 unit + 9 http tests passing**.

## Endpoint under test

`GET /api/v1/get_url_category/` ({{app/views.py}} `get_url_category`) — no auth, query
params `url` (required) and optional `cu_id` (resolves a Company for the biz path). Returns
the `predict_url_category` dict (`guessed_category`, `guessed_subcategory`, `is_biz`,
`is_rate`, `is_calculator`, `audience`). A batch sibling `get_url_categories`
(`POST /api/v1/...`, auth required) takes `{urls: [...]}`.

## Related fixes captured by this suite

- **Investment property** (`categorize_url`): `investment property` loan/mortgage URLs →
  `mortgage` / subcat `investment property mortgage`, guarded so a plain `investment loan`
  stays `investment`.
- **Student/youth deposits (ECGC-3167)**: `student checking account` now detected when
  `checking` is in a non-last URL segment; youth-savings emits `student savings account`
  (a real KG) instead of the orphan `youth savings account`.
- **Taxonomy**: new `student savings account` KeywordGroup (local; pending dev/stg/prod);
  Confluence "Vocabulary" page updated to add `investment property mortgage` +
  `student savings account` and remove `youth savings account`.
