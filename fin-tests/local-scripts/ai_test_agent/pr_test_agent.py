"""
AI Test Agent - Analyzes GitHub PRs and Decides What to Test

This agent:
1. Reads code changes from a GitHub PR (public or private)
2. Analyzes what was changed
3. Decides which tests to run based on the changes
4. Optionally executes those tests

Requirements:
- GitHub CLI (gh) authenticated: `gh auth login`
- Or set GITHUB_TOKEN environment variable
"""

import os
import subprocess
import json
import re
from typing import Optional
from dataclasses import dataclass

# Try to import anthropic for AI analysis
try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("Warning: anthropic package not installed. AI analysis disabled.")


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
    """A recommended test based on PR changes."""
    test_file: str
    reason: str
    priority: str  # high, medium, low
    related_changes: list


def run_gh_command(command: str) -> tuple[bool, str]:
    """Run a GitHub CLI command and return success status and output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def get_github_token() -> Optional[str]:
    """Get GitHub token from environment or prompt user."""
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if token:
        return token

    # Check for .env file
    env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('GITHUB_TOKEN='):
                    return line.split('=', 1)[1].strip().strip('"\'')

    return None


def fetch_pr_via_api(owner: str, repo: str, pr_number: int, token: str = None) -> Optional[dict]:
    """Fetch PR information using GitHub REST API."""
    import requests

    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'AI-Test-Agent'
    }
    if token:
        headers['Authorization'] = f'token {token}'

    base_url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}'

    # Fetch PR details
    response = requests.get(base_url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching PR: {response.status_code} - {response.text[:200]}")
        return None

    pr_data = response.json()

    # Fetch files changed
    files_response = requests.get(f'{base_url}/files', headers=headers)
    files = files_response.json() if files_response.status_code == 200 else []

    # Fetch diff
    diff_headers = headers.copy()
    diff_headers['Accept'] = 'application/vnd.github.v3.diff'
    diff_response = requests.get(base_url, headers=diff_headers)
    diff = diff_response.text if diff_response.status_code == 200 else ""

    return {
        'title': pr_data.get('title', ''),
        'body': pr_data.get('body', ''),
        'baseRefName': pr_data.get('base', {}).get('ref', 'main'),
        'headRefName': pr_data.get('head', {}).get('ref', ''),
        'files': [
            {
                'path': f.get('filename', ''),
                'additions': f.get('additions', 0),
                'deletions': f.get('deletions', 0),
                'status': f.get('status', ''),
            }
            for f in files
        ],
        'diff': diff
    }


def parse_pr_url(pr_url: str) -> tuple[str, str, int]:
    """Parse a GitHub PR URL into owner, repo, and PR number."""
    # Handle formats:
    # https://github.com/owner/repo/pull/123
    # owner/repo#123
    # owner/repo/pull/123

    patterns = [
        r'github\.com/([^/]+)/([^/]+)/pull/(\d+)',  # Full URL
        r'^([^/]+)/([^/]+)#(\d+)$',                  # owner/repo#123
        r'^([^/]+)/([^/]+)/pull/(\d+)$',            # owner/repo/pull/123
    ]

    for pattern in patterns:
        match = re.search(pattern, pr_url)
        if match:
            return match.group(1), match.group(2), int(match.group(3))

    raise ValueError(f"Could not parse PR URL: {pr_url}")


def get_pr_info(pr_url: str) -> Optional[PRInfo]:
    """Fetch PR information from GitHub using API or gh CLI."""

    owner, repo, pr_number = parse_pr_url(pr_url)
    full_repo = f"{owner}/{repo}"

    print(f"\nFetching PR #{pr_number} from {full_repo}...")

    # Try using GitHub API first (works without gh CLI)
    token = get_github_token()
    if not token:
        print("Note: No GITHUB_TOKEN found. For private repos, set GITHUB_TOKEN environment variable.")

    pr_data = fetch_pr_via_api(owner, repo, pr_number, token)

    if pr_data is None:
        # Fallback to gh CLI if API fails
        print("API fetch failed, trying gh CLI...")
        success, pr_json = run_gh_command(
            f'gh pr view {pr_number} --repo {full_repo} --json title,body,baseRefName,headRefName,files'
        )

        if not success:
            print(f"Error fetching PR: {pr_json}")
            return None

        pr_data = json.loads(pr_json)

        # Get the diff via CLI
        success, diff = run_gh_command(
            f'gh pr diff {pr_number} --repo {full_repo}'
        )
        pr_data['diff'] = diff if success else ""

    # Extract changed files
    changed_files = []
    if 'files' in pr_data:
        for f in pr_data['files']:
            changed_files.append({
                'path': f.get('path', f.get('filename', '')),
                'additions': f.get('additions', 0),
                'deletions': f.get('deletions', 0),
            })

    return PRInfo(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        title=pr_data.get('title', ''),
        description=pr_data.get('body', '') or '',
        changed_files=changed_files,
        diff=pr_data.get('diff', '')[:50000],  # Limit diff size
        base_branch=pr_data.get('baseRefName', 'main'),
        head_branch=pr_data.get('headRefName', ''),
    )


def analyze_changes_with_ai(pr_info: PRInfo, available_tests: list[str]) -> list[TestRecommendation]:
    """Use AI to analyze PR changes and recommend tests."""

    if not HAS_ANTHROPIC:
        print("AI analysis not available - returning all tests")
        return [TestRecommendation(t, "AI unavailable", "medium", []) for t in available_tests]

    client = Anthropic()

    # Build context about the changes
    files_summary = "\n".join([
        f"  - {f['path']} (+{f['additions']}/-{f['deletions']})"
        for f in pr_info.changed_files
    ])

    prompt = f"""Analyze this Pull Request and recommend which tests should be run.

## PR Information
- **Title**: {pr_info.title}
- **Description**: {pr_info.description[:2000] if pr_info.description else 'No description'}
- **Branch**: {pr_info.head_branch} → {pr_info.base_branch}

## Changed Files
{files_summary}

## Diff (truncated)
```
{pr_info.diff[:15000]}
```

## Available Test Files
{json.dumps(available_tests, indent=2)}

## Your Task
Based on the code changes, determine which tests should be run. Consider:
1. Direct changes to test files (must run those tests)
2. Changes to source files that tests cover
3. Changes to shared utilities or configurations
4. Changes that might affect specific features (card ads, login, CTAs, etc.)

Respond with a JSON array of test recommendations:
```json
[
  {{
    "test_file": "path/to/test.py",
    "reason": "Why this test should run",
    "priority": "high|medium|low",
    "related_changes": ["file1.py", "file2.py"]
  }}
]
```

Only recommend tests from the available tests list. If no tests are relevant, return an empty array.
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    # Extract JSON from response
    response_text = response.content[0].text

    # Find JSON array in response
    json_match = re.search(r'\[[\s\S]*\]', response_text)
    if not json_match:
        print("Warning: Could not parse AI response")
        return []

    try:
        recommendations = json.loads(json_match.group())
        return [
            TestRecommendation(
                test_file=r['test_file'],
                reason=r['reason'],
                priority=r['priority'],
                related_changes=r.get('related_changes', [])
            )
            for r in recommendations
        ]
    except json.JSONDecodeError as e:
        print(f"Warning: JSON parse error: {e}")
        return []


def discover_available_tests(test_dirs: list[str] = None) -> list[str]:
    """Discover available test files in the project."""

    if test_dirs is None:
        test_dirs = ['.', 'tests', 'fin-tests', 'pytests']

    test_files = []

    for test_dir in test_dirs:
        if not os.path.exists(test_dir):
            continue

        for root, dirs, files in os.walk(test_dir):
            # Skip hidden directories and common non-test directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv']]

            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(os.path.join(root, file))

    return test_files


def run_tests(test_files: list[str], dry_run: bool = True) -> dict:
    """Run the recommended tests."""

    results = {}

    for test_file in test_files:
        if dry_run:
            print(f"  [DRY RUN] Would run: pytest {test_file}")
            results[test_file] = "dry_run"
        else:
            print(f"  Running: pytest {test_file}")
            success, output = run_gh_command(f'pytest {test_file} -v')
            results[test_file] = "passed" if success else "failed"
            if not success:
                print(f"    FAILED: {output[:500]}")

    return results


def analyze_pr_and_recommend_tests(
    pr_url: str,
    test_dirs: list[str] = None,
    run_tests_flag: bool = False,
    dry_run: bool = True
) -> dict:
    """
    Main function: Analyze a PR and recommend/run tests.

    Args:
        pr_url: GitHub PR URL or owner/repo#number format
        test_dirs: Directories to search for tests
        run_tests_flag: Whether to actually run the tests
        dry_run: If running tests, whether to do a dry run

    Returns:
        Dictionary with analysis results
    """

    print("\n" + "="*70)
    print("AI TEST AGENT - PR Analysis")
    print("="*70)

    # Step 1: Fetch PR information
    pr_info = get_pr_info(pr_url)
    if not pr_info:
        return {"error": "Could not fetch PR information"}

    print(f"\n✓ PR #{pr_info.pr_number}: {pr_info.title}")
    print(f"  Branch: {pr_info.head_branch} → {pr_info.base_branch}")
    print(f"  Changed files: {len(pr_info.changed_files)}")

    # Step 2: Discover available tests
    available_tests = discover_available_tests(test_dirs)
    print(f"\n✓ Found {len(available_tests)} test files")

    if not available_tests:
        return {"error": "No test files found", "pr": pr_info}

    # Step 3: Analyze changes and recommend tests
    print("\n⏳ Analyzing changes with AI...")
    recommendations = analyze_changes_with_ai(pr_info, available_tests)

    print(f"\n✓ AI recommended {len(recommendations)} tests to run:")

    # Group by priority
    high_priority = [r for r in recommendations if r.priority == 'high']
    medium_priority = [r for r in recommendations if r.priority == 'medium']
    low_priority = [r for r in recommendations if r.priority == 'low']

    for priority_name, tests in [('HIGH', high_priority), ('MEDIUM', medium_priority), ('LOW', low_priority)]:
        if tests:
            print(f"\n  [{priority_name} PRIORITY]")
            for rec in tests:
                print(f"    • {rec.test_file}")
                print(f"      Reason: {rec.reason}")
                if rec.related_changes:
                    print(f"      Related: {', '.join(rec.related_changes[:3])}")

    # Step 4: Optionally run tests
    test_results = {}
    if run_tests_flag and recommendations:
        print("\n" + "-"*70)
        print("RUNNING TESTS" + (" (DRY RUN)" if dry_run else ""))
        print("-"*70)

        # Run high priority first, then medium, then low
        for rec in high_priority + medium_priority + low_priority:
            test_results[rec.test_file] = run_tests([rec.test_file], dry_run)

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"PR: {pr_info.owner}/{pr_info.repo}#{pr_info.pr_number}")
    print(f"Files changed: {len(pr_info.changed_files)}")
    print(f"Tests recommended: {len(recommendations)}")
    print(f"  - High priority: {len(high_priority)}")
    print(f"  - Medium priority: {len(medium_priority)}")
    print(f"  - Low priority: {len(low_priority)}")

    return {
        "pr": {
            "owner": pr_info.owner,
            "repo": pr_info.repo,
            "number": pr_info.pr_number,
            "title": pr_info.title,
            "changed_files": len(pr_info.changed_files),
        },
        "recommendations": [
            {
                "test_file": r.test_file,
                "reason": r.reason,
                "priority": r.priority,
            }
            for r in recommendations
        ],
        "test_results": test_results,
    }


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="AI Test Agent - Analyze PRs and recommend tests"
    )
    parser.add_argument(
        "pr_url",
        help="GitHub PR URL (e.g., https://github.com/owner/repo/pull/123 or owner/repo#123)"
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Actually run the recommended tests"
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Execute tests for real (default is dry run)"
    )
    parser.add_argument(
        "--test-dirs",
        nargs="+",
        default=None,
        help="Directories to search for tests"
    )

    args = parser.parse_args()

    result = analyze_pr_and_recommend_tests(
        pr_url=args.pr_url,
        test_dirs=args.test_dirs,
        run_tests_flag=args.run,
        dry_run=not args.no_dry_run
    )

    # Print result as JSON for programmatic use
    print("\n" + "-"*70)
    print("JSON OUTPUT:")
    print(json.dumps(result, indent=2))
