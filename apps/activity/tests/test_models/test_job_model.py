import pytest 
from apps.activity.models.job_model import Jobneed,JobneedDetails
from django.utils import timezone
from django.core.exceptions import ValidationError

@pytest.mark.django_db
def test_job_model(job_factory):
    job = job_factory()
    assert str(job) == "Test Job"


@pytest.mark.django_db
def test_create_minimal_jobneed(client_bt, bu_bt):
    jobneed = Jobneed.objects.create(
        jobdesc="Night Tour",
        gracetime=5,
        receivedonserver=timezone.now(),
        priority="LOW",
        scantype="SKIP",
        seqno=1,
        client=client_bt,
        bu=bu_bt
    )

    assert jobneed.uuid is not None
    assert jobneed.multifactor == 1
    assert jobneed.ismailsent is False


@pytest.mark.django_db
def test_invalid_priority_raises():
    jobneed = Jobneed(
        jobdesc="Bad Priority",
        gracetime=1,
        receivedonserver=timezone.now(),
        priority="INVALID",
        scantype="SKIP",
        seqno=1
    )
    with pytest.raises(ValidationError):
        jobneed.full_clean()



@pytest.mark.django_db
def test_create_minimal_jobneeddetails(jobneed_factory):
    jobneed = jobneed_factory()
    details = JobneedDetails.objects.create(
        seqno=1,
        jobneed=jobneed,
    )
    assert details.uuid is not None
    assert details.ismandatory is True
    assert details.alerts is False
    assert details.attachmentcount == 0


from django.core.exceptions import ValidationError

@pytest.mark.django_db
def test_invalid_answertype_fails(jobneed_factory):
    jobneed = jobneed_factory()
    details = JobneedDetails(
        seqno=1,
        jobneed=jobneed,
        answertype="INVALID"
    )
    with pytest.raises(ValidationError):
        details.full_clean()


@pytest.mark.django_db
def test_min_max_decimal_precision(jobneed_factory):
    jobneed = jobneed_factory()
    details = JobneedDetails.objects.create(
        seqno=1,
        jobneed=jobneed,
        min=1.1234,
        max=9.8765
    )
    assert float(details.min) == 1.1234
    assert float(details.max) == 9.8765
