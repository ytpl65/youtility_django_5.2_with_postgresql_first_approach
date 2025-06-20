import pytest
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from apps.activity.models.asset_model import Asset
from apps.onboarding.models import Bt, TypeAssist
from apps.activity.managers.asset_manager import AssetLogManager
import json
from unittest.mock import patch

from datetime import datetime
from django.utils import timezone

@pytest.fixture
def session_request(rf, client_bt, bu_bt):
    request = rf.get('/')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    request.session['client_id'] = client_bt.id
    request.session['bu_id'] = bu_bt.id
    request.session['assignedsites'] = [bu_bt.id]
    return request


def test_get_assetdetails_returns_queryset(asset_factory):
    bt = Bt.objects.create(bucode='T1', buname='Test', enable=True)
    aware_mdtz = timezone.make_aware(datetime(2024,12,1,10,00,00))
    asset_factory(mdtz=aware_mdtz, bu=bt)  # adjust date + bu
    results = Asset.objects.get_assetdetails("2024-01-01 00:00:00", site_id=bt.id)
    assert results.exists()



@pytest.mark.django_db
def test_get_assetlistview_valid(session_request, client_bt):
    from apps.activity.models.asset_model import Asset

    # Set up session
    session_request.session['client_id'] = client_bt.id
    session_request.session['bu_id'] = client_bt.id
    session_request.session.save()
    session_request.GET = {'params': json.dumps({'status': 'WORKING'})}

    # Create a matching asset
    Asset.objects.create(
        assetcode='AS001',
        assetname='Pump',
        runningstatus='WORKING',
        client=client_bt,
        bu=client_bt,
        enable=True,
        identifier='ASSET',
        gpslocation='POINT(12.9716 77.5946)',
        iscritical=True
    )

    # Fields and related
    fields = ['assetname', 'runningstatus']
    related = []

    result = Asset.objects.get_assetlistview(related, fields, session_request)
    
    # This should now pass
    assert result.exists()


def test_get_assetchart_data(session_request):
    series, total = Asset.objects.get_assetchart_data(session_request)
    assert isinstance(series, list)
    assert isinstance(total, int)


@patch('apps.core.utils.runrawsql')
@patch('apps.core.utils.format_timedelta', return_value="1 hour")
def test_get_period_of_assetstatus(mock_format, mock_run):
    mock_run.return_value = [{'total_duration': 3600}]
    result = Asset.objects.get_period_of_assetstatus(assetid=1, status='WORKING')
    assert result == "1 hour"


@pytest.mark.django_db
def test_asset_type_choices_for_report_with_missing_session():
    rf = RequestFactory()
    request = rf.get('/')

    # Apply session middleware FIRST
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()

    # Now set session keys
    request.session['client_id'] = 1
    request.session['bu_id'] = 1
    request.session['assignedsites'] = [1]

    result = Asset.objects.asset_type_choices_for_report(request)

    # Ensure it runs and returns either empty queryset or correct result structure
    assert isinstance(result, list) or hasattr(result, '__iter__')


