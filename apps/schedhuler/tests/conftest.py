import pytest
from django.utils import timezone
from datetime import timedelta, datetime
from unittest.mock import Mock

from apps.schedhuler.models import *
from apps.peoples.models import People, Pgroup
from apps.activity.models.asset_model import Asset
from apps.activity.models.job_model import Job, Jobneed
from apps.activity.models.question_model import QuestionSet
from apps.onboarding.models import Bt


@pytest.fixture
def sample_people():
    return People.objects.create(
        peoplename="Test Person",
        peopleemail="test@example.com",
        peoplecode="TEST001"
    )

@pytest.fixture
def sample_group():
    return Pgroup.objects.create(
        groupname="Test Group"
    )

@pytest.fixture
def sample_bt():
    return Bt.objects.create(
        buname="Test BU",
        buadd="Test Address"
    )

@pytest.fixture
def sample_asset():
    return Asset.objects.create(
        assetname="Test Asset",
        assetdesc="Test Asset Description"
    )

@pytest.fixture
def sample_questionset():
    return QuestionSet.objects.create(
        qsetname="Test Questionset"
    )

@pytest.fixture
def sample_job(sample_people, sample_asset, sample_questionset):
    return Job.objects.create(
        jobname="Test Job",
        jobdesc="Test Job Description",
        people=sample_people,
        asset=sample_asset,
        qset=sample_questionset
    )

@pytest.fixture
def sample_jobneed(sample_job, sample_people, sample_asset, sample_questionset):
    return Jobneed.objects.create(
        jobdesc="Test Jobneed",
        job=sample_job,
        people=sample_people,
        asset=sample_asset,
        qset=sample_questionset
    )

@pytest.fixture
def job_data():
    return {
        'id': 1,
        'jobname': 'Test Job',
        'cron': '0 8 * * *',
        'identifier': 'TASK',
        'ctzoffset': 330,
        'cdtz': timezone.now(),
        'mdtz': timezone.now(),
        'fromdate': timezone.now(),
        'uptodate': timezone.now() + timedelta(days=30),
        'lastgeneratedon': timezone.now() - timedelta(days=1),
        'asset_id': 1,
        'people_id': 1,
        'pgroup_id': 1,
        'qset_id': 1,
        'gracetime': 5,
        'planduration': 60,
        'expirytime': 10,
        'sgroup__groupname': 'Test Site Group',
        'sgroup_id': 1,
        'client_id': 1,
        'cuser_id': 1,
        'muser_id': 1,
        'ticketcategory_id': 1,
        'frequency': 'NONE',
        'bu_id': 1,
        'scantype': 'QR',
        'priority': 'HIGH'
    }

@pytest.fixture
def checkpoint_data():
    return {
        'expirytime': 10,
        'qsetname': 'Test QSet',
        'qsetid': 1,
        'assetid': 1,
        'seqno': 1,
        'starttime': '08:00',
        'endtime': '17:00'
    }

@pytest.fixture
def external_checkpoint_data():
    return {
        'expirytime': 10,
        'qsetname': 'Test QSet',
        'qsetid': 1,
        'assetid': 1,
        'seqno': 1,
        'starttime': '08:00',
        'endtime': '17:00',
        'bu__buname': 'Test Site',
        'distance': 5.5,
        'breaktime': 15
    }

@pytest.fixture
def mock_asset():
    asset = Mock()
    asset.id = 1
    asset.asset_json = {'multifactor': 1}
    return asset

@pytest.fixture
def mock_jobneed():
    jobneed = Mock()
    jobneed.id = 1
    jobneed.other_info = {}
    return jobneed