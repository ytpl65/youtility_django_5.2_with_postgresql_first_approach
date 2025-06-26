import pytest
from django.test import override_settings
from unittest.mock import MagicMock

# Configure test settings
TEST_DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Mock Celery app for testing
@pytest.fixture
def mock_celery_app():
    """Mock Celery app for testing"""
    app = MagicMock()
    app.task = MagicMock()
    return app

@pytest.fixture
def mock_email_settings():
    """Override email settings for testing"""
    with override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        EMAIL_HOST_USER='test@example.com',
        DEFAULT_FROM_EMAIL='test@example.com'
    ):
        yield

@pytest.fixture
def sample_job_data():
    """Sample job data for testing"""
    return {
        'id': 1,
        'identifier': 'JOB001',
        'jobdesc': 'Test Job Description',
        'bu_id': 1,
        'client_id': 1,
        'cuser_id': 1,
        'assignedto': 'test@example.com',
        'plandatetime': '2024-01-15 10:00:00',
        'expirydatetime': '2024-01-16 10:00:00',
        'ticketcategory__tacode': 'AUTOCLOSENOTIFY'
    }

@pytest.fixture
def sample_report_data():
    """Sample report data for testing"""
    return {
        'id': 1,
        'report_id': 'RPT001',
        'enable': True,
        'cron': '0 9 * * *',
        'email_to': 'report@example.com',
        'email_subject': 'Daily Report',
        'email_body': 'Please find attached report',
        'parameters': {}
    }

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with Django settings"""
    import django
    from django.conf import settings
    
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES=TEST_DATABASES,
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
                'django.contrib.sessions',
                'django.contrib.messages',
                'apps.core',
                'apps.reports',
                'apps.activity',
                'background_tasks',
            ],
            MIDDLEWARE=[],
            ROOT_URLCONF='',
            SECRET_KEY='test-secret-key',
            USE_TZ=True,
        )
        django.setup()