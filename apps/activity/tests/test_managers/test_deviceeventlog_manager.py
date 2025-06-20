import pytest
from datetime import datetime, timedelta, timezone
from django.test import RequestFactory
from unittest.mock import patch
from apps.activity.models.deviceevent_log_model import DeviceEventlog
from apps.onboarding.models import Bt  # Make sure this import matches your model location

@pytest.mark.django_db
def test_get_mobileuserlog_returns_expected_result():
    # Create required Bt instance
    bt = Bt.objects.create(bucode='TESTBU', buname='Test BU', enable=True)

    # Setup request with session
    factory = RequestFactory()
    request = factory.get('/')
    request.session = {'bu_id': bt.id}

    # Patch the utility function
    with patch('apps.core.utils.get_qobjs_dir_fields_start_length') as mock_get_qobjs:
        mock_get_qobjs.return_value = (None, '-cdtz', ['cdtz', 'bu_id'], 10, 0)

        # Insert DeviceEventlog entry
        dt = datetime.now(tz=timezone.utc) - timedelta(days=5)
        DeviceEventlog.objects.create(bu=bt, cdtz=dt)

        # Call the manager method
        total, fcount, results = DeviceEventlog.objects.get_mobileuserlog(request)

        assert total == 1
        assert fcount == 1
        assert list(results)[0]['bu_id'] == bt.id
