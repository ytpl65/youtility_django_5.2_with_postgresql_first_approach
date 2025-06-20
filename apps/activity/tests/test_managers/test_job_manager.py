from urllib import request
import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from apps.activity.models.job_model import Job
from apps.activity.models.asset_model import Asset
from unittest.mock import patch
from datetime import timedelta
from apps.peoples.models import People
from apps.onboarding.models import Bt


@pytest.fixture
def session_request(rf, django_user_model):
    request = rf.get("/")
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    bt = Bt.objects.create(bucode='TESTBU', buname='Test BU', enable=True)
    request.session.save()
    request.session['client_id'] = bt.id
    request.session['bu_id'] = bt.id
    request.session['assignedsites'] = [bt.id]
    request.user = People.objects.create(
        peoplename="Tester", email="test@example.com", client=bt, bu=bt,
        dateofbirth="2023-05-22", dateofjoin="2023-05-22",dateofreport="2023-05-22"
        )
    return request


@pytest.mark.django_db
def test_get_scheduled_internal_tours(session_request):
    job = Job.objects.create(
        jobname="Routine", identifier="INTERNALTOUR",
        bu_id=1, client_id=1, parent_id=1, enable=True,
        fromdate="2023-05-22 09:30:00+00", uptodate="2023-05-22 09:30:00+00",
        planduration=10, gracetime=5, expirytime=10, priority="LOW", scantype="SKIP", seqno=1    )
    session_request.session['assignedsites'] = [1]
    session_request.session['client_id'] = 1

    fields = ['id', 'jobname']
    related = []
    result = Job.objects.get_scheduled_internal_tours(session_request, related, fields)

    assert any([j['jobname'] == "Routine" for j in result])


@pytest.mark.django_db
def test_get_jobppm_listview(session_request):
    Job.objects.create(
        jobname='PPM Task',
        identifier='PPM',
        enable=True,
        bu_id=session_request.session['bu_id'],
        client_id=session_request.session['client_id'],
        fromdate="2024-01-01 09:00:00+00",
        uptodate="2024-01-31 18:00:00+00",
        planduration=30,
        gracetime=10,
        expirytime=15,
        priority="LOW",
        scantype="SKIP",
        seqno=1
    )
    session_request.GET = {}
    result = Job.objects.get_jobppm_listview(session_request)
    assert result.exists()

from django.http import QueryDict

data = QueryDict('', mutable=True)
data.update({
    'action': 'create',
    'parentid': 1,
    'qset_id': 1,
    'asset_id': 1,
    'seqno': 1,
    'expirytime': 5,
    'qsetname': 'Test Qset',
    'ctzoffset': 0,
})
request.POST = data


@patch('apps.core.utils.runrawsql', return_value=[{'total_duration': timedelta(seconds=3600)}])
def test_get_period_of_assetstatus(mock_runrawsql):
    result = Asset.objects.get_period_of_assetstatus(assetid=1, status='MAINTENANCE')
    assert result == "1 hour"

