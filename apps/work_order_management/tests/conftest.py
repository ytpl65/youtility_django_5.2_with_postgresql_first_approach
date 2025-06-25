"""
Fixtures for work_order_management app testing
"""
import pytest
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils import timezone
from django.contrib.gis.geos import Point
from datetime import datetime, timedelta, date
from apps.work_order_management.models import Wom, Vendor, WomDetails, Approver
from apps.onboarding.models import Bt, TypeAssist
from apps.peoples.models import People
from apps.activity.models.asset_model import Asset
from apps.activity.models.location_model import Location 
from apps.activity.models.question_model import QuestionSet 
from apps.activity.models.question_model import  Question


@pytest.fixture
def rf():
    """Request factory"""
    return RequestFactory()


@pytest.fixture
def test_client_wom():
    """Create test client for work order management"""
    return Bt.objects.create(
        bucode='WOMCLIENT',
        buname='Work Order Management Client',
        enable=True
    )


@pytest.fixture
def test_bu_wom(test_client_wom):
    """Create test business unit for work order management"""
    return Bt.objects.create(
        bucode='WOMBU',
        buname='Work Order Management BU',
        parent=test_client_wom,
        enable=True,
        gpslocation=Point(77.5946, 12.9716)
    )


@pytest.fixture
def test_people_wom(test_client_wom, test_bu_wom):
    """Create test people for work order management"""
    return People.objects.create(
        peoplecode='WOMUSER001',
        peoplename='Work Order Manager',
        loginid='womuser',
        email='womuser@example.com',
        mobno='9876543210',
        dateofbirth='1990-01-01',
        dateofjoin='2023-01-01',
        client=test_client_wom,
        bu=test_bu_wom,
        isverified=True,
        enable=True
    )


@pytest.fixture
def test_vendor_type():
    """Create vendor type TypeAssist"""
    return TypeAssist.objects.create(
        tacode='ELECTRICAL',
        taname='Electrical Contractor',
        enable=True
    )


@pytest.fixture
def test_ticket_category():
    """Create ticket category TypeAssist"""
    return TypeAssist.objects.create(
        tacode='MAINTENANCE',
        taname='Maintenance Request',
        enable=True
    )


@pytest.fixture
def test_asset(test_client_wom, test_bu_wom):
    """Create test asset"""
    return Asset.objects.create(
        assetcode='PUMP001',
        assetname='Water Pump Unit 1',
        client=test_client_wom,
        bu=test_bu_wom,
        enable=True,
        iscritical=True
    )


@pytest.fixture
def test_location(test_client_wom, test_bu_wom):
    """Create test location"""
    return Location.objects.create(
        loccode='BASEMENT',
        locname='Basement Level',
        client=test_client_wom,
        bu=test_bu_wom,
        enable=True,
        iscritical=False,
        locstatus=Location.LocationStatus.WORKING
    )


@pytest.fixture
def test_question():
    """Create test question"""
    return Question.objects.create(
        quesname='What is the issue?',
        enable=True
    )


@pytest.fixture
def test_questionset(test_client_wom, test_bu_wom):
    """Create test question set"""
    return QuestionSet.objects.create(
        qsetname='Maintenance Checklist',
        client=test_client_wom,
        bu=test_bu_wom,
        enable=True
    )


@pytest.fixture
def test_vendor(test_client_wom, test_bu_wom, test_vendor_type):
    """Create test vendor"""
    return Vendor.objects.create(
        code='ELEC001',
        name='ABC Electrical Services',
        type=test_vendor_type,
        address='123 Industrial Area, Bangalore',
        gpslocation=Point(77.5946, 12.9716),
        enable=True,
        mobno='9876543210',
        email='contact@abcelectrical.com',
        client=test_client_wom,
        bu=test_bu_wom,
        description='Professional electrical maintenance services'
    )


@pytest.fixture
def wom_factory(test_client_wom, test_bu_wom, test_people_wom, test_vendor, test_questionset, test_asset, test_location, test_ticket_category):
    """Factory for creating Wom instances"""
    counter = [0]  # Use list to maintain counter state
    
    def _create_wom(
        description=None,
        workstatus=None,
        workpermit=None,
        priority=None,
        vendor=None,
        **kwargs
    ):
        counter[0] += 1
        unique_id = f"{timezone.now().timestamp():.6f}_{counter[0]}"
        
        defaults = {
            'description': description or f'Work Order {unique_id}',
            'plandatetime': kwargs.get('plandatetime', timezone.now() + timedelta(hours=1)),
            'expirydatetime': kwargs.get('expirydatetime', timezone.now() + timedelta(hours=8)),
            'gpslocation': kwargs.get('gpslocation', Point(77.5946, 12.9716)),
            'asset': kwargs.get('asset', test_asset),
            'location': kwargs.get('location', test_location),
            'workstatus': workstatus or Wom.Workstatus.ASSIGNED,
            'seqno': kwargs.get('seqno', counter[0]),
            'workpermit': workpermit or Wom.WorkPermitStatus.NOTNEED,
            'verifiers_status': kwargs.get('verifiers_status', Wom.WorkPermitVerifierStatus.PENDING),
            'priority': priority or Wom.Priority.MEDIUM,
            'qset': kwargs.get('qset', test_questionset),
            'vendor': vendor or test_vendor,
            'performedby': kwargs.get('performedby', f'Test Performer {counter[0]}'),
            'alerts': kwargs.get('alerts', False),
            'client': kwargs.get('client', test_client_wom),
            'bu': kwargs.get('bu', test_bu_wom),
            'ticketcategory': kwargs.get('ticketcategory', test_ticket_category),
            'ismailsent': kwargs.get('ismailsent', False),
            'isdenied': kwargs.get('isdenied', False),
            'attachmentcount': kwargs.get('attachmentcount', 0),
            'categories': kwargs.get('categories', ['MAINTENANCE']),
            'identifier': kwargs.get('identifier', Wom.Identifier.WO),
            'cuser': kwargs.get('cuser', test_people_wom),
            'muser': kwargs.get('muser', test_people_wom),
        }
        defaults.update(kwargs)
        return Wom.objects.create(**defaults)
    
    return _create_wom


@pytest.fixture
def vendor_factory(test_client_wom, test_bu_wom, test_vendor_type):
    """Factory for creating Vendor instances"""
    counter = [0]  # Use list to maintain counter state
    
    def _create_vendor(
        code=None,
        name=None,
        vendor_type=None,
        client=None,
        bu=None,
        **kwargs
    ):
        counter[0] += 1
        unique_id = f"{timezone.now().timestamp():.6f}_{counter[0]}"
        
        defaults = {
            'code': code or f'VEN_{unique_id}',
            'name': name or f'Test Vendor Company {counter[0]}',
            'type': vendor_type or test_vendor_type,
            'address': kwargs.get('address', f'Test Address {counter[0]}, City'),
            'gpslocation': kwargs.get('gpslocation', Point(77.5946, 12.9716)),
            'enable': kwargs.get('enable', True),
            'mobno': kwargs.get('mobno', f'987654{counter[0] % 10000:04d}'),
            'email': kwargs.get('email', f'test{counter[0]}@vendor.com'),
            'client': client or test_client_wom,
            'bu': bu or test_bu_wom,
            'show_to_all_sites': kwargs.get('show_to_all_sites', False),
            'description': kwargs.get('description', f'Test vendor description {counter[0]}'),
        }
        defaults.update(kwargs)
        return Vendor.objects.create(**defaults)
    
    return _create_vendor


@pytest.fixture
def womdetails_factory(test_question):
    """Factory for creating WomDetails instances"""
    counter = [0]  # Use list to maintain counter state
    
    def _create_womdetails(
        wom=None,
        question=None,
        qset=None,
        **kwargs
    ):
        counter[0] += 1
        
        # Create unique question if not provided
        if question is None:
            unique_id = f"{timezone.now().timestamp():.6f}_{counter[0]}"
            question = Question.objects.create(
                quesname=f'Question {unique_id}',
                enable=True
            )
        
        defaults = {
            'seqno': kwargs.get('seqno', counter[0]),
            'question': question,
            'answertype': kwargs.get('answertype', WomDetails.AnswerType.SINGLELINE),
            'qset': qset,
            'answer': kwargs.get('answer', f'Test answer {counter[0]}'),
            'isavpt': kwargs.get('isavpt', False),
            'avpttype': kwargs.get('avpttype', WomDetails.AvptType.NONE),
            'options': kwargs.get('options', ''),
            'min': kwargs.get('min', None),
            'max': kwargs.get('max', None),
            'alerton': kwargs.get('alerton', ''),
            'ismandatory': kwargs.get('ismandatory', True),
            'wom': wom,
            'alerts': kwargs.get('alerts', False),
            'attachmentcount': kwargs.get('attachmentcount', 0),
        }
        defaults.update(kwargs)
        return WomDetails.objects.create(**defaults)
    
    return _create_womdetails


@pytest.fixture
def approver_factory(test_client_wom, test_bu_wom):
    """Factory for creating Approver instances"""
    counter = [0]  # Use list to maintain counter state
    
    def _create_approver(
        people=None,
        client=None,
        bu=None,
        identifier=None,
        **kwargs
    ):
        # Create unique person if not provided
        if people is None:
            from apps.peoples.models import People
            counter[0] += 1
            unique_id = f"{timezone.now().timestamp():.6f}_{counter[0]}"
            people = People.objects.create(
                peoplecode=f'APP_{unique_id}',
                peoplename=f'Approver {unique_id}',
                loginid=f'approver_{unique_id}',
                email=f'approver_{unique_id}@example.com',
                mobno=f'98765{(int(timezone.now().timestamp()) + counter[0]) % 100000:05d}',
                dateofbirth='1990-01-01',
                dateofjoin='2023-01-01',
                client=client or test_client_wom,
                bu=bu or test_bu_wom,
                enable=True
            )
        
        defaults = {
            'approverfor': kwargs.get('approverfor', ['WORKORDER']),
            'sites': kwargs.get('sites', []),
            'forallsites': kwargs.get('forallsites', True),
            'people': people,
            'bu': bu or test_bu_wom,
            'client': client or test_client_wom,
            'identifier': identifier or Approver.Identifier.APPROVER,
        }
        defaults.update(kwargs)
        return Approver.objects.create(**defaults)
    
    return _create_approver


@pytest.fixture
def authenticated_wom_request(rf, test_people_wom, test_client_wom, test_bu_wom):
    """Create an authenticated request with session for work order management testing"""
    request = rf.get('/')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    
    # Set session data for work order management
    request.session['client_id'] = test_client_wom.id
    request.session['bu_id'] = test_bu_wom.id
    request.session['assignedsites'] = [test_bu_wom.id]
    request.session['user_id'] = test_people_wom.id
    request.session['people_id'] = test_people_wom.id
    request.session['is_superadmin'] = False
    request.session['client_webcaps'] = []
    request.session['client_mobcaps'] = []
    request.session['client_portletcaps'] = []
    request.session['client_reportcaps'] = []
    request.session['client_noccaps'] = []
    request.session['sitecode'] = test_bu_wom.bucode
    request.session['sitename'] = test_bu_wom.buname
    request.session['clientcode'] = test_client_wom.bucode
    request.session['ctzoffset'] = 330  # IST timezone offset
    request.user = test_people_wom
    
    return request


@pytest.fixture
def sample_wom_data():
    """Sample data for work order forms"""
    return {
        'description': 'Fix water pump in basement',
        'priority': 'HIGH',
        'workstatus': 'ASSIGNED',
        'workpermit': 'NOT_REQUIRED',
        'performedby': 'Maintenance Team',
        'categories': ['ELECTRICAL', 'PLUMBING'],
        'alerts': True,
        'ismailsent': False,
        'isdenied': False
    }


@pytest.fixture
def work_order_statuses():
    """All work order status choices"""
    return [
        Wom.Workstatus.ASSIGNED,
        Wom.Workstatus.REASSIGNED,
        Wom.Workstatus.COMPLETED,
        Wom.Workstatus.INPROGRESS,
        Wom.Workstatus.CANCELLED,
        Wom.Workstatus.CLOSED
    ]


@pytest.fixture
def work_permit_statuses():
    """All work permit status choices"""
    return [
        Wom.WorkPermitStatus.NOTNEED,
        Wom.WorkPermitStatus.APPROVED,
        Wom.WorkPermitStatus.REJECTED,
        Wom.WorkPermitStatus.PENDING
    ]


@pytest.fixture
def priority_levels():
    """All priority level choices"""
    return [
        Wom.Priority.HIGH,
        Wom.Priority.LOW,
        Wom.Priority.MEDIUM
    ]


@pytest.fixture
def answer_types():
    """All answer type choices for WomDetails"""
    return [
        WomDetails.AnswerType.CHECKBOX,
        WomDetails.AnswerType.DATE,
        WomDetails.AnswerType.DROPDOWN,
        WomDetails.AnswerType.EMAILID,
        WomDetails.AnswerType.MULTILINE,
        WomDetails.AnswerType.NUMERIC,
        WomDetails.AnswerType.SIGNATURE,
        WomDetails.AnswerType.SINGLELINE,
        WomDetails.AnswerType.TIME,
        WomDetails.AnswerType.RATING,
        WomDetails.AnswerType.BACKCAMERA,
        WomDetails.AnswerType.FRONTCAMERA,
        WomDetails.AnswerType.PEOPLELIST,
        WomDetails.AnswerType.SITELIST,
        WomDetails.AnswerType.NONE,
        WomDetails.AnswerType.MULTISELECT
    ]


@pytest.fixture
def attachment_types():
    """All attachment type choices for WomDetails"""
    return [
        WomDetails.AvptType.BACKCAMPIC,
        WomDetails.AvptType.FRONTCAMPIC,
        WomDetails.AvptType.AUDIO,
        WomDetails.AvptType.VIDEO,
        WomDetails.AvptType.NONE
    ]


@pytest.fixture
def gps_coordinates_wom():
    """Sample GPS coordinates for work order management testing"""
    return {
        'office_location': Point(77.5946, 12.9716),
        'site_location': Point(77.6000, 12.9800),
        'vendor_location': Point(77.5800, 12.9600),
        'asset_location': Point(77.5950, 12.9720)
    }


@pytest.fixture
def sample_other_data():
    """Sample other_data JSON for Wom model"""
    return {
        'token': 'abc123token',
        'created_at': '2024-01-01T10:00:00Z',
        'token_expiration': 60,
        'reply_from_vendor': 'Work completed successfully',
        'wp_seqno': 1001,
        'wp_approvers': [
            {
                'people_id': 1,
                'name': 'John Approver',
                'status': 'APPROVED',
                'timestamp': '2024-01-01T11:00:00Z'
            }
        ],
        'wp_verifiers': [
            {
                'people_id': 2,
                'name': 'Jane Verifier',
                'status': 'VERIFIED',
                'timestamp': '2024-01-01T11:30:00Z'
            }
        ],
        'section_weightage': 0.8,
        'overall_score': 85.5,
        'remarks': 'Work completed within schedule',
        'uptime_score': 95.0
    }


@pytest.fixture
def sample_wo_history():
    """Sample wo_history JSON for Wom model"""
    return {
        'wo_history': [
            {
                'id': 1,
                'description': 'Initial work order',
                'workstatus': 'ASSIGNED',
                'timestamp': '2024-01-01T09:00:00Z'
            },
            {
                'id': 1,
                'description': 'Updated work order',
                'workstatus': 'INPROGRESS',
                'timestamp': '2024-01-01T10:00:00Z'
            }
        ],
        'wp_history': [
            {
                'wp_seqno': 1001,
                'status': 'APPROVED',
                'timestamp': '2024-01-01T11:00:00Z'
            }
        ]
    }


@pytest.fixture
def vendor_types():
    """Common vendor types for testing"""
    types = []
    vendor_type_names = [
        ('ELECTRICAL', 'Electrical Contractor'),
        ('PLUMBING', 'Plumbing Services'),
        ('HVAC', 'HVAC Maintenance'),
        ('CLEANING', 'Cleaning Services'),
        ('SECURITY', 'Security Services'),
        ('CATERING', 'Catering Services')
    ]
    
    for code, name in vendor_type_names:
        vendor_type = TypeAssist.objects.create(
            tacode=code,
            taname=name,
            enable=True
        )
        types.append(vendor_type)
    
    return types