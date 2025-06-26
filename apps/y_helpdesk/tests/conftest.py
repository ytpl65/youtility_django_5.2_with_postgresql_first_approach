import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import uuid

from apps.y_helpdesk.models import Ticket, EscalationMatrix
from apps.peoples.models import People, Pgroup
from apps.activity.models.asset_model import Asset 
from apps.activity.models.job_model import Job, QuestionSet 
from apps.activity.models.location_model import Location
from apps.onboarding.models import Bt, TypeAssist

User = get_user_model()


@pytest.fixture
def sample_user():
    return User.objects.create_user(
        loginid='testuser',
        password='testpass123',
        peoplecode='TEST001',
        peoplename='Test User',
        dateofbirth='1990-01-01',
        email='testuser@example.com'
    )

@pytest.fixture
def sample_people():
    return People.objects.create(
        peoplename="Test Person",
        email="test@example.com",
        peoplecode="TEST002",
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
def sample_questionset():
    return QuestionSet.objects.create(
        qsetname="Test Questionset"
    )

@pytest.fixture
def sample_location():
    return Location.objects.create(
        loccode="TESTLOC001",
        locname="Test Location",
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
def sample_ticket_data(sample_people, sample_group, sample_bt, sample_asset, 
                      sample_questionset, sample_location):
    return {
        'ticketdesc': 'Test ticket description',
        'assignedtopeople': sample_people,
        'assignedtogroup': sample_group,
        'comments': 'Test comments',
        'bu': sample_bt,
        'client': sample_bt,
        'priority': Ticket.Priority.HIGH,
        'asset': sample_asset,
        'qset': sample_questionset,
        'location': sample_location,
        'status': Ticket.Status.NEW,
        'performedby': sample_people,
        'ticketsource': Ticket.TicketSource.USERDEFINED
    }

@pytest.fixture
def sample_ticket(sample_ticket_data):
    return Ticket.objects.create(**sample_ticket_data)

@pytest.fixture
def sample_escalation_data(sample_user, sample_people, sample_group, sample_bt, sample_job):
    return {
        'body': 'Escalation body text',
        'job': sample_job,
        'level': 1,
        'frequency': EscalationMatrix.Frequency.HOUR,
        'frequencyvalue': 2,
        'assignedfor': 'test assignment',
        'assignedperson': sample_user,
        'assignedgroup': sample_group,
        'bu': sample_bt,
        'notify': 'test@example.com',
        'client': sample_bt
    }

@pytest.fixture
def sample_escalation_matrix(sample_escalation_data):
    return EscalationMatrix.objects.create(**sample_escalation_data)

@pytest.fixture
def ticket_priorities():
    return ['LOW', 'MEDIUM', 'HIGH']

@pytest.fixture
def ticket_statuses():
    return ['NEW', 'CANCELLED', 'RESOLVED', 'OPEN', 'ONHOLD', 'CLOSED']

@pytest.fixture
def escalation_frequencies():
    return ['MINUTE', 'HOUR', 'DAY', 'WEEK']

@pytest.fixture
def multiple_tickets(sample_people, sample_bt):
    tickets = []
    for i in range(3):
        ticket = Ticket.objects.create(
            ticketdesc=f'Test ticket {i+1}',
            assignedtopeople=sample_people,
            bu=sample_bt,
            client=sample_bt,
            status=Ticket.Status.NEW if i % 2 == 0 else Ticket.Status.OPEN,
            ticketsource=Ticket.TicketSource.USERDEFINED
        )
        tickets.append(ticket)
    return tickets

@pytest.fixture
def future_ticket(sample_ticket_data):
    data = sample_ticket_data.copy()
    data['modifieddatetime'] = timezone.now() + timedelta(days=1)
    return Ticket.objects.create(**data)

@pytest.fixture
def past_ticket(sample_ticket_data):
    data = sample_ticket_data.copy()
    data['modifieddatetime'] = timezone.now() - timedelta(days=1)
    return Ticket.objects.create(**data)