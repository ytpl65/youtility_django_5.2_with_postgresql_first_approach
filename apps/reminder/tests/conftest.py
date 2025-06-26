import pytest
from django.utils import timezone
from datetime import timedelta

from apps.reminder.models import Reminder
from apps.peoples.models import People, Pgroup
from apps.activity.models.asset_model import Asset 
from apps.activity.models.job_model import Job, Jobneed 
from apps.activity.models.question_model import QuestionSet
from apps.onboarding.models import Bt


@pytest.fixture
def sample_people():
    return People.objects.create(
        peoplecode="TEST001",
        peoplename="Test Person",
        email="test@example.com",
        dateofbirth="1990-01-01"
    )

@pytest.fixture
def sample_group():
    return Pgroup.objects.create(
        groupname="Test Group"
    )

@pytest.fixture
def sample_bt():
    return Bt.objects.create(
        bucode="TESTBU001",
        buname="Test BU"
    )

@pytest.fixture
def sample_asset():
    return Asset.objects.create(
        assetcode="TESTASSET001",
        assetname="Test Asset",
        iscritical=False
    )

@pytest.fixture
def sample_job():
    return Job.objects.create(
        jobname="Test Job",
        jobdesc="Test Job Description",
        fromdate=timezone.now(),
        uptodate=timezone.now() + timedelta(days=30),
        planduration=60,
        gracetime=15,
        expirytime=120,
        priority=Job.Priority.MEDIUM,
        seqno=1,
        scantype=Job.Scantype.SKIP
    )

@pytest.fixture
def sample_jobneed():
    return Jobneed.objects.create(
        jobdesc="Test Jobneed",
        gracetime=30,
        priority=Jobneed.Priority.MEDIUM,
        seqno=1
    )

@pytest.fixture
def sample_questionset():
    return QuestionSet.objects.create(
        qsetname="Test Questionset"
    )

@pytest.fixture
def complete_reminder_data(sample_people, sample_group, sample_bt, sample_asset,
                          sample_job, sample_jobneed, sample_questionset):
    return {
        'description': 'Test reminder description',
        'bu': sample_bt,
        'asset': sample_asset,
        'qset': sample_questionset,
        'people': sample_people,
        'group': sample_group,
        'priority': Reminder.Priority.HIGH,
        'reminderdate': timezone.now() + timedelta(days=1),
        'reminderin': Reminder.Frequency.DAILY,
        'reminderbefore': 30,
        'job': sample_job,
        'jobneed': sample_jobneed,
        'plandatetime': timezone.now() + timedelta(days=2),
        'mailids': 'test@example.com,test2@example.com',
        'status': Reminder.StatusChoices.SUCCESS
    }

@pytest.fixture
def minimal_reminder_data():
    return {
        'description': 'Minimal reminder',
        'priority': Reminder.Priority.LOW,
        'reminderin': Reminder.Frequency.NONE,
        'reminderbefore': 0,
        'mailids': 'test@example.com',
        'status': Reminder.StatusChoices.FAILED
    }

@pytest.fixture
def future_reminder(complete_reminder_data):
    return Reminder.objects.create(**complete_reminder_data)

@pytest.fixture
def past_reminder(complete_reminder_data):
    data = complete_reminder_data.copy()
    data['reminderdate'] = timezone.now() - timedelta(days=1)
    data['plandatetime'] = timezone.now() - timedelta(hours=1)
    return Reminder.objects.create(**data)

@pytest.fixture
def success_reminder(complete_reminder_data):
    data = complete_reminder_data.copy()
    data['status'] = Reminder.StatusChoices.SUCCESS
    return Reminder.objects.create(**data)

@pytest.fixture
def failed_reminder(complete_reminder_data):
    data = complete_reminder_data.copy()
    data['status'] = Reminder.StatusChoices.FAILED
    return Reminder.objects.create(**data)