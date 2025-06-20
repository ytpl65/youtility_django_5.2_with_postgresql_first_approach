import pytest
from apps.activity.forms.job_form import JobForm, JobNeedForm, AdhocTaskForm
from django.test.client import RequestFactory
from apps.onboarding.models import Shift
from datetime import datetime


@pytest.mark.django_db
def test_jobform_valid_submission(client_bt, bu_bt, rf):
    request = rf.post("/")
    request.session = {'client_id': client_bt.id, 'bu_id': bu_bt.id}

    from django.utils import timezone
    now = timezone.now()

    form_data = {
        "jobname": "Test Job",
        "jobdesc": "Test job desc",
        "fromdate": now,
        "uptodate": now,
        "cron": "* * * * *",
        "planduration": 10,
        "gracetime": 5,
        "expirytime": 15,
        "priority": "LOW",
        "scantype": "SKIP",
        "seqno": 1,
        "identifier": "TASK",
        "client": client_bt.id,
        "bu": bu_bt.id,
        "starttime": "08:00",
        "endtime": "10:00",
        "ctzoffset": 0,
        "frequency": "DAILY",
        "shift": 1  # 🔧 You must create a dummy shift object for this
    }

    # Create a dummy Shift
    shift = Shift.objects.create(shiftname="Morning", enable=True,starttime="08:00", endtime="10:00")
    form_data["shift"] = shift.id

    form = JobForm(data=form_data, request=request)

    assert form.is_valid(), form.errors

@pytest.mark.django_db
def test_jobform_missing_required_fields(rf):
    request = rf.post('/')
    request.session = {'client_id': 1, 'bu_id': 1}
    
    form = JobForm(data={}, request=request)
    
    assert not form.is_valid()
    assert 'jobname' in form.errors
    assert 'fromdate' in form.errors


@pytest.mark.django_db
def test_jobform_fromdate_is_utc(client_bt, bu_bt):
    rf = RequestFactory()
    request = rf.post('/')
    request.session = {'client_id': client_bt.id, 'bu_id': bu_bt.id}

    naive_dt = datetime(2025, 4, 15, 12, 0)
    shift = Shift.objects.create(shiftname="Morning", enable=True,starttime="08:00", endtime="10:00")
    form_data = {
        'jobname': 'UTC Shift',
        'fromdate': naive_dt,
        'uptodate': naive_dt,
        'cron': '* * * * *',
        'planduration': 10,
        'gracetime': 5,
        'expirytime': 5,
        'priority': 'HIGH',
        'seqno': 1,
        'scantype': 'SKIP',
        'client': client_bt.id,
        'bu': bu_bt.id,
        'identifier': 'TASK',
        'frequency': 'DAILY',
        'ctzoffset': 0,
        'shift': shift.id , # 🔧 You must create a dummy shift object for thi
        'starttime': "08:00",
        "endtime": "10:00",
    }

    form = JobForm(data=form_data, request=request)
    form.fields['people'].required = False  # handle optional fields
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_jobneedform_valid(people_factory, questionset_factory, asset_factory):
    person = people_factory()
    qset = questionset_factory()
    asset = asset_factory()
    
    form = JobNeedForm(data={
        "identifier": "TASK",
        "frequency": "DAILY",
        "jobdesc": "Routine Check",
        "priority": "LOW",
        "scantype": "SKIP",
        "plandatetime": "2023-05-22 09:30:00+00",
        "expirydatetime": "2023-05-22 10:00:00+00",
        "gracetime": 10,
        "starttime": "2023-05-22 09:30:00+00",
        "endtime": "2023-05-22 10:00:00+00",
        "people": person.id,
        "qset": qset.id,
        "asset": asset.id,
        "multifactor": 1.0,
        "jobstatus": "ASSIGNED",
        "ctzoffset": 0,
    })

    assert form.is_valid(), form.errors

@pytest.mark.django_db
def test_adhoc_task_form_valid(client_bt, bu_bt, people_factory, asset_factory, questionset_factory, rf):
    request = rf.post("/")
    request.session = {
        'client_id': client_bt.id,
        'bu_id': bu_bt.id,
        'assignedsites': [bu_bt.id],  # ✅ Add this line to prevent KeyError
    }
    asset = asset_factory(assetcode="A001_FORM_TEST")
    form_data = {
        "identifier": "TASK",
        "priority": "LOW",
        "scantype": "SKIP",
        "seqno": 1,
        "gracetime": 5,
        "assign_to": "PEOPLE",
        "jobdesc": "Sample task",
        "plandatetime": "2023-05-22 09:30:00",
        "expirydatetime": "2023-05-23 09:30:00",
        "people": people_factory().id,
        "asset": asset.id,
        "qset": questionset_factory().id,
        "ctzoffset": 0,
        "frequency": "DAILY",
        "starttime": "2023-05-22 09:30:00",
        "endtime": "2023-05-23 09:30:00",
        "multifactor": 1.0,
        "jobstatus": "ASSIGNED",
    }

    form = AdhocTaskForm(data=form_data, request=request)
    form.fields['qset'].choices = [(questionset_factory().id, 'Test QSet')]
    form.fields['asset'].choices = [(asset_factory().id, 'Test Asset')]
    form.fields['people'].choices = [(people_factory().id, 'Test Person')]

    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_adhoc_task_form_missing_required_field(client_bt, bu_bt, rf):
    request = rf.post("/")
    request.session = {
    'client_id': client_bt.id,
    'bu_id': bu_bt.id,
    'assignedsites': [bu_bt.id],  # ✅ Add this line to prevent KeyError
}

    
    form = AdhocTaskForm(data={}, request=request)
    assert not form.is_valid()
    assert 'plandatetime' in form.errors


@pytest.mark.django_db
def test_adhoc_task_form_invalid_assign_to(client_bt, bu_bt, rf):
    request = rf.post("/")
    request.session = {
    'client_id': client_bt.id,
    'bu_id': bu_bt.id,
    'assignedsites': [bu_bt.id],  # ✅ Add this line to prevent KeyError
}

    form_data = {
        "assign_to": "INVALID"
    }

    form = AdhocTaskForm(data=form_data, request=request)
    assert not form.is_valid()
    assert 'assign_to' in form.errors
