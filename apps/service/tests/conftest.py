import pytest
import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "intelliwiz_config.settings")
django.setup()

from django.contrib.auth import get_user_model
from apps.onboarding.models import Bt


@pytest.fixture
def bt_factory(db):
    def _create(**kwargs):
        defaults = {
            "bucode": "TSTBU",
            "buname": "Test BU",
            "enable": True,
        }
        defaults.update(kwargs)
        return Bt.objects.create(**defaults)
    return _create

@pytest.fixture
def people_factory(db, bt_factory):
    def _create(**kwargs):
        bt = bt_factory()
        defaults = {
            "peoplecode": "P001",
            "peoplename": "Test User",
            "loginid": "testuser",
            "email": "user@example.com",
            "dateofbirth": "1990-01-01",
            "client": bt,
            "bu": bt,
        }
        defaults.update(kwargs)
        return get_user_model().objects.create(**defaults)
    return _create

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()
