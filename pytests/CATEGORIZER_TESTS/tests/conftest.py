"""
Pytest configuration and shared fixtures.

Test tiers (use with: pytest -m "marker"):
  unit         - Pure logic, no Django ORM or database. Starts instantly.
  integration  - Django ORM / database tests.
  e2e          - Browser / Playwright tests.
  http         - Pure HTTP tests against a running server (no Django import).
  slow         - Any test over ~5s.
"""

import os

import django
import pytest
from django.conf import settings
from django.test.utils import setup_test_environment, teardown_test_environment


# ---------------------------------------------------------------------------
# Django bootstrap
# ---------------------------------------------------------------------------

def pytest_addoption(parser):
    """Add custom CLI options for browser E2E tests."""
    parser.addoption('--env', action='store', default='local', help='Target environment: local, dev, stg, prod')
    parser.addoption('--company', action='store', default='glbl', help='Company code for test scenarios')


def pytest_configure(config):
    """Configure Django for pytest."""
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ga.settings')
        django.setup()
        setup_test_environment()


def pytest_unconfigure(config):
    """Clean up Django after pytest."""
    teardown_test_environment()


# ---------------------------------------------------------------------------
# Auto-apply markers based on test class / file conventions
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(config, items):
    """Auto-apply markers so existing tests work without manual decoration."""
    for item in items:
        # Auto-mark Playwright / E2E tests
        if "playwright" in item.keywords or "StaticLiveServerTestCase" in str(getattr(item.cls, '__bases__', [])):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)

        # Auto-mark pure HTTP tests (files that contain 'http' marker or live in tests/http/)
        if "http" in item.keywords:
            item.add_marker(pytest.mark.http)


# ---------------------------------------------------------------------------
# Database fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def django_db_setup():
    """Set up test database for the session."""
    from django.core.management import call_command

    call_command('migrate', '--run-syncdb', verbosity=0, interactive=False)

    yield


# ---------------------------------------------------------------------------
# Playwright fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def playwright():
    """Playwright fixture for the session."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="function")
def browser(playwright):
    """Browser fixture for each test function."""
    browser = playwright.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def page(browser):
    """Page fixture for each test function."""
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


# ---------------------------------------------------------------------------
# HTTP test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_url():
    """Base URL for pure HTTP tests against a running server."""
    return os.environ.get("TEST_BASE_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Admin-page E2E fixtures
#
# Why these exist: hitting any /scenarios/ admin page over Playwright requires
# clearing five gates (auth session, MFA predicate, fin-employee perms,
# company resolution via cu_id, Ad pre_save signals). The helpers below
# encode each gate; see .claude/skills/admin-e2e-test/SKILL.md for what each
# one is for and how to debug a regression.
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_e2e_company():
    """Test Company that resolves through Company().get_company() and is owned
    by the admin test user. company_type='credit_union' is required because
    check_company filters by it for fin-employee users."""
    from app.models import Company

    co = Company.objects.filter(code='admin_e2e').first()
    if not co:
        co = Company.objects.create(
            name='Admin E2E', code='admin_e2e', number='99099',
            is_active=True, is_subscriber=True, company_type='credit_union',
        )
    elif co.company_type != 'credit_union':
        co.company_type = 'credit_union'
        co.save()
    return co


@pytest.fixture
def admin_e2e_user(admin_e2e_company):
    """Staff user in personalization_admin group with MFA already 'set up'.

    Satisfies three gates simultaneously:
      - check_perms: is_staff + fin-employee group membership
      - check_company: userprofile.company resolves to admin_e2e_company
      - is_mfa_setup_invalid: mfa_setup_complete + a TOTPDevice exist
    """
    from django.contrib.auth.models import Group, User
    from django.db.models.signals import pre_save
    from django_otp.plugins.otp_totp.models import TOTPDevice

    from app.models import UserProfile
    from app.signals.handlers import user_presave

    pre_save.disconnect(user_presave, sender=User)
    Group.objects.get_or_create(name='personalization_admin')
    admin_grp = Group.objects.get(name='personalization_admin')

    user = User.objects.filter(username='admin_e2e@finalytics.ai').first()
    if not user:
        user = User.objects.create_user(
            username='admin_e2e@finalytics.ai',
            email='admin_e2e@finalytics.ai',
            password='unused-session-auth-only',
        )
    up, _ = UserProfile.objects.get_or_create(
        user=user, defaults={'company': admin_e2e_company}
    )
    if not up.company:
        up.company = admin_e2e_company
        up.save()
    user.groups.add(admin_grp)
    user.is_staff = True
    user.save()

    up.mfa_setup_complete = True
    up.save()
    TOTPDevice.objects.get_or_create(
        user=user, name='e2e', defaults={'confirmed': True}
    )
    yield user
    pre_save.connect(user_presave, sender=User)


@pytest.fixture
def admin_e2e_session_cookie(admin_e2e_user, admin_e2e_company):
    """Builds a Django session for the admin user and returns a cookie dict
    ready to hand to Playwright's context.add_cookies().

    This is the same shape django.contrib.auth.login() writes — see
    django/contrib/auth/__init__.py login(). The session row lands in the
    runserver's database, so cross-process cookie handoff just works on local.
    """
    from django.conf import settings as dj_settings
    from django.contrib.sessions.backends.db import SessionStore

    session = SessionStore()
    session['_auth_user_id'] = str(admin_e2e_user.id)
    session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
    session['_auth_user_hash'] = admin_e2e_user.get_session_auth_hash()
    session['cu_id'] = admin_e2e_company.code
    session.create()

    base = os.environ.get('TEST_BASE_URL', 'http://127.0.0.1:8001')
    return {
        'name': dj_settings.SESSION_COOKIE_NAME,
        'value': session.session_key,
        'url': base,
    }


@pytest.fixture
def disconnect_ad_pre_save_signals():
    """Disconnects every pre_save handler registered for Ad in
    app/signals/handlers.py. They assume realistic ad_html/template state and
    will explode on minimal test fixtures. Reconnects on teardown.

    To verify the list is current: `Grep pre_save\\.connect.*sender=Ad`.
    """
    from django.db.models.signals import pre_save

    from app.models import Ad
    from app.signals.handlers import (
        campaign_presave, create_ad, prevent_calculator_activation,
        track_revision_pre_save, use_ad_config,
    )

    handlers = (
        prevent_calculator_activation, campaign_presave, create_ad,
        track_revision_pre_save, use_ad_config,
    )
    for h in handlers:
        pre_save.disconnect(h, sender=Ad)
    yield
    for h in handlers:
        pre_save.connect(h, sender=Ad)


@pytest.fixture
def admin_authed_context(playwright, admin_e2e_session_cookie):
    """Playwright context that's already authed against the local runserver.

    Usage:
        def test_something(admin_authed_context):
            ctx = admin_authed_context
            page = ctx.new_page()
            page.goto('http://127.0.0.1:8001/scenarios/...')
    """
    browser = playwright.chromium.launch(headless=True)
    ctx = browser.new_context()
    ctx.add_cookies([admin_e2e_session_cookie])
    yield ctx
    browser.close()
