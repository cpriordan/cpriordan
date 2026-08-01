"""
AI Test Agent v2 - Analyzes GitHub PRs, Recommends Tests & Suggests New Tests

This agent:
1. Reads code changes from a GitHub PR
2. Analyzes changes using Claude AI
3. Recommends which existing tests to run
4. Suggests new tests that should be written

Requirements:
- GITHUB_TOKEN: GitHub Personal Access Token
- ANTHROPIC_API_KEY: Anthropic API key for Claude
"""

import os
import json
import re
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

# Import required packages
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("ERROR: requests package not installed. Run: pip install requests")

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("ERROR: anthropic package not installed. Run: pip install anthropic")


@dataclass
class PRInfo:
    """Information about a Pull Request."""
    owner: str
    repo: str
    pr_number: int
    title: str
    description: str
    changed_files: list
    diff: str
    base_branch: str
    head_branch: str


@dataclass
class TestRecommendation:
    """An existing test recommended to run."""
    test_file: str
    reason: str
    priority: str  # high, medium, low
    related_changes: list


@dataclass
class TestSuggestion:
    """A new test that should be written."""
    description: str
    test_type: str  # unit, integration, e2e
    file_to_test: str
    scenarios: list
    priority: str
    sample_code: str = ""


def load_env():
    """Load environment variables from .env file."""
    env_paths = [
        os.path.join(os.path.dirname(__file__), '.env'),
        os.path.join(os.path.dirname(__file__), '..', '.env'),
    ]

    for env_file in env_paths:
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip().strip('"\'')
                        if key not in os.environ:
                            os.environ[key] = value
            break


def get_token(name: str) -> Optional[str]:
    """Get token from environment."""
    load_env()
    return os.environ.get(name)


def parse_pr_url(pr_url: str) -> tuple:
    """Parse GitHub PR URL into owner, repo, pr_number."""
    patterns = [
        r'github\.com/([^/]+)/([^/]+)/pull/(\d+)',
        r'^([^/]+)/([^/]+)#(\d+)$',
        r'^([^/]+)/([^/]+)/pull/(\d+)$',
    ]

    for pattern in patterns:
        match = re.search(pattern, pr_url)
        if match:
            return match.group(1), match.group(2), int(match.group(3))

    raise ValueError(f"Could not parse PR URL: {pr_url}")


def fetch_pr(owner: str, repo: str, pr_number: int) -> Optional[PRInfo]:
    """Fetch PR information from GitHub API."""
    if not HAS_REQUESTS:
        return None

    token = get_token('GITHUB_TOKEN') or get_token('GH_TOKEN')

    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'AI-Test-Agent'
    }
    if token:
        headers['Authorization'] = f'token {token}'
    else:
        print("WARNING: No GITHUB_TOKEN found. Private repos will fail.")

    base_url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}'

    # Fetch PR details
    response = requests.get(base_url, headers=headers)
    if response.status_code != 200:
        print(f"ERROR: Failed to fetch PR: {response.status_code}")
        print(f"  {response.text[:200]}")
        return None

    pr_data = response.json()

    # Fetch changed files
    files_response = requests.get(f'{base_url}/files', headers=headers)
    files = files_response.json() if files_response.status_code == 200 else []

    # Fetch diff
    diff_headers = headers.copy()
    diff_headers['Accept'] = 'application/vnd.github.v3.diff'
    diff_response = requests.get(base_url, headers=diff_headers)
    diff = diff_response.text if diff_response.status_code == 200 else ""

    changed_files = [
        {
            'path': f.get('filename', ''),
            'additions': f.get('additions', 0),
            'deletions': f.get('deletions', 0),
            'status': f.get('status', 'modified'),
        }
        for f in files
    ]

    return PRInfo(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        title=pr_data.get('title', ''),
        description=pr_data.get('body', '') or '',
        changed_files=changed_files,
        diff=diff[:50000],
        base_branch=pr_data.get('base', {}).get('ref', 'main'),
        head_branch=pr_data.get('head', {}).get('ref', ''),
    )


def discover_tests(test_dirs: list = None) -> list:
    """Find all test files in the project."""
    if test_dirs is None:
        test_dirs = ['.', 'tests', 'fin-tests', 'pytests', '__tests__', 'test']

    test_files = []

    for test_dir in test_dirs:
        if not os.path.exists(test_dir):
            continue

        for root, dirs, files in os.walk(test_dir):
            # Skip unwanted directories
            dirs[:] = [d for d in dirs if not d.startswith('.')
                      and d not in ['__pycache__', 'node_modules', 'venv', '.git']]

            for file in files:
                # Python tests
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(os.path.join(root, file))
                # JS tests
                elif file.endswith('.test.js') or file.endswith('.spec.js'):
                    test_files.append(os.path.join(root, file))
                elif file.endswith('.test.ts') or file.endswith('.spec.ts'):
                    test_files.append(os.path.join(root, file))

    return test_files


def analyze_with_ai(pr_info: PRInfo, available_tests: list) -> tuple:
    """Use Claude to analyze PR and provide recommendations."""
    if not HAS_ANTHROPIC:
        print("ERROR: anthropic package required")
        return [], []

    client = Anthropic()

    files_summary = "\n".join([
        f"  - {f['path']} (+{f['additions']}/-{f['deletions']}) [{f['status']}]"
        for f in pr_info.changed_files
    ])

    prompt = f"""Analyze this Pull Request and provide test recommendations.

## PR Information
- **Title**: {pr_info.title}
- **Description**: {pr_info.description[:2000] if pr_info.description else 'No description'}
- **Branch**: {pr_info.head_branch} → {pr_info.base_branch}

## Changed Files
{files_summary}

## Code Diff
```
{pr_info.diff[:25000]}
```

## Available Test Files in This Project
{json.dumps(available_tests[:100], indent=2)}

## Your Task

Provide TWO types of recommendations:

### 1. EXISTING TESTS TO RUN
Which tests from the available list should run for this PR? Consider:
- Tests that directly test the changed files
- Tests for features affected by the changes
- Integration tests that might catch regressions

**IMPORTANT - Environment Consideration:**
- PRs are deployed to STAGING first, NOT production
- Only recommend STAGING tests (files without "PROD" in the name) for validating PR changes
- DO NOT recommend production tests (files with "PROD" in the name) because the PR code is not deployed to production yet
- If a staging version of a test doesn't exist but would be useful, suggest it as a new test to write

### 2. NEW TESTS TO WRITE
What new tests should be written to properly test these changes? Consider:
- Untested functionality introduced by this PR
- Edge cases not covered by existing tests
- Integration scenarios between changed components
- Staging versions of tests if only PROD versions exist

Respond with this exact JSON format:
```json
{{
  "existing_tests_to_run": [
    {{
      "test_file": "path/to/test.py",
      "reason": "Why run this test",
      "priority": "high|medium|low",
      "related_changes": ["file1.js"]
    }}
  ],
  "new_tests_to_write": [
    {{
      "description": "What the test should verify",
      "test_type": "unit|integration|e2e",
      "file_to_test": "path/to/source.js",
      "scenarios": ["Scenario 1", "Scenario 2"],
      "priority": "high|medium|low",
      "sample_code": "Optional: brief pseudocode or test structure"
    }}
  ],
  "summary": "Brief summary of testing recommendations"
}}
```

Be specific and actionable. Only recommend existing tests from the provided list.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text

        # Extract JSON
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if not json_match:
            print("WARNING: Could not parse AI response")
            return [], []

        result = json.loads(json_match.group())

        recommendations = [
            TestRecommendation(
                test_file=r['test_file'],
                reason=r['reason'],
                priority=r['priority'],
                related_changes=r.get('related_changes', [])
            )
            for r in result.get('existing_tests_to_run', [])
        ]

        suggestions = [
            TestSuggestion(
                description=s['description'],
                test_type=s['test_type'],
                file_to_test=s['file_to_test'],
                scenarios=s.get('scenarios', []),
                priority=s['priority'],
                sample_code=s.get('sample_code', '')
            )
            for s in result.get('new_tests_to_write', [])
        ]

        if 'summary' in result:
            print(f"\n  Summary: {result['summary']}")

        return recommendations, suggestions

    except json.JSONDecodeError as e:
        print(f"ERROR: JSON parse error: {e}")
        return [], []
    except Exception as e:
        print(f"ERROR: AI analysis failed: {e}")
        return [], []


def analyze_pr(pr_url: str, test_dirs: list = None) -> dict:
    """
    Main function: Analyze a PR and provide test recommendations.

    Args:
        pr_url: GitHub PR URL
        test_dirs: Directories to search for tests

    Returns:
        Dictionary with analysis results
    """
    print("\n" + "="*70)
    print("AI TEST AGENT v2")
    print("Analyzes PRs | Recommends Tests | Suggests New Tests")
    print("="*70)

    # Parse and fetch PR
    owner, repo, pr_number = parse_pr_url(pr_url)
    print(f"\nFetching PR #{pr_number} from {owner}/{repo}...")

    pr_info = fetch_pr(owner, repo, pr_number)
    if not pr_info:
        return {"error": "Failed to fetch PR"}

    print(f"\n[OK] PR: {pr_info.title}")
    print(f"     Branch: {pr_info.head_branch} -> {pr_info.base_branch}")
    print(f"     Files changed: {len(pr_info.changed_files)}")

    print("\n     Changed files:")
    for f in pr_info.changed_files[:15]:
        print(f"       - {f['path']} (+{f['additions']}/-{f['deletions']})")
    if len(pr_info.changed_files) > 15:
        print(f"       ... and {len(pr_info.changed_files) - 15} more")

    # Discover tests
    available_tests = discover_tests(test_dirs)
    print(f"\n[OK] Found {len(available_tests)} test files in project")

    # AI Analysis
    print("\n[..] Analyzing with AI...")
    recommendations, suggestions = analyze_with_ai(pr_info, available_tests)

    # Print Results
    print("\n" + "="*70)
    print("EXISTING TESTS TO RUN")
    print("="*70)

    if recommendations:
        for priority in ['high', 'medium', 'low']:
            tests = [r for r in recommendations if r.priority == priority]
            if tests:
                icon = {'high': '[!!!]', 'medium': '[!!]', 'low': '[!]'}[priority]
                print(f"\n{icon} {priority.upper()} PRIORITY:")
                for rec in tests:
                    print(f"\n    {rec.test_file}")
                    print(f"    Reason: {rec.reason}")
                    if rec.related_changes:
                        print(f"    Related: {', '.join(rec.related_changes[:3])}")
    else:
        print("\n  No existing tests recommended.")

    print("\n" + "="*70)
    print("NEW TESTS TO WRITE")
    print("="*70)

    if suggestions:
        for i, sug in enumerate(suggestions, 1):
            icon = {'high': '[!!!]', 'medium': '[!!]', 'low': '[!]'}[sug.priority]
            print(f"\n{icon} Suggestion #{i}: {sug.description}")
            print(f"    Type: {sug.test_type}")
            print(f"    For: {sug.file_to_test}")
            if sug.scenarios:
                print("    Test scenarios:")
                for scenario in sug.scenarios[:5]:
                    print(f"      - {scenario}")
            if sug.sample_code:
                print(f"    Sample code:\n      {sug.sample_code[:200]}")
    else:
        print("\n  No new tests suggested - existing coverage may be sufficient.")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"PR: {owner}/{repo}#{pr_number}")
    print(f"Files changed: {len(pr_info.changed_files)}")
    print(f"Existing tests to run: {len(recommendations)}")
    high = len([r for r in recommendations if r.priority == 'high'])
    med = len([r for r in recommendations if r.priority == 'medium'])
    low = len([r for r in recommendations if r.priority == 'low'])
    print(f"  - High: {high}, Medium: {med}, Low: {low}")
    print(f"New tests suggested: {len(suggestions)}")

    return {
        "pr": {
            "owner": owner,
            "repo": repo,
            "number": pr_number,
            "title": pr_info.title,
            "files_changed": len(pr_info.changed_files),
        },
        "existing_tests_to_run": [
            {"file": r.test_file, "reason": r.reason, "priority": r.priority}
            for r in recommendations
        ],
        "new_tests_to_write": [
            {"description": s.description, "type": s.test_type, "for": s.file_to_test, "priority": s.priority}
            for s in suggestions
        ],
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="AI Test Agent - Analyze PRs and recommend tests"
    )
    parser.add_argument(
        "pr_url",
        help="GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)"
    )
    parser.add_argument(
        "--test-dirs",
        nargs="+",
        default=None,
        help="Directories to search for tests"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    result = analyze_pr(args.pr_url, args.test_dirs)

    if args.json:
        print("\n" + json.dumps(result, indent=2))
