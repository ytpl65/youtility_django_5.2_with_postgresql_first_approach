"""
Fixtures for onboarding app testing
"""
import pytest
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils import timezone
from django.contrib.gis.geos import Point, Polygon
from datetime import datetime, timedelta, date, time
from apps.onboarding.models import Bt, TypeAssist, Shift, GeofenceMaster, Device, Subscription, DownTimeHistory
from apps.peoples.models import People


@pytest.fixture
def rf():
    """Request factory"""
    return RequestFactory()


@pytest.fixture
def test_root_client():
    """Create root client BT for testing"""
    return Bt.objects.create(
        bucode='ROOTCLIENT',
        buname='Root Test Client',
        enable=True
    )


@pytest.fixture
def test_client_bt():
    """Create test client BT"""
    return Bt.objects.create(
        bucode='TESTCLIENT',
        buname='Test Client Organization',
        enable=True
    )


@pytest.fixture
def test_bu_bt(test_client_bt):
    """Create test business unit"""
    return Bt.objects.create(
        bucode='TESTBU',
        buname='Test Business Unit',
        parent=test_client_bt,
        enable=True
    )


@pytest.fixture
def test_site_bt(test_bu_bt, test_client_bt):
    """Create test site"""
    return Bt.objects.create(
        bucode='TESTSITE',
        buname='Test Site Location',
        parent=test_bu_bt,
        enable=True,
        gpslocation=Point(77.5946, 12.9716),
        pdist=100.0
    )


@pytest.fixture
def test_identifier_client():
    """Create CLIENT identifier TypeAssist"""
    return TypeAssist.objects.create(
        tacode='CLIENT',
        taname='Client',
        enable=True
    )


@pytest.fixture
def test_identifier_site():
    """Create SITE identifier TypeAssist"""
    return TypeAssist.objects.create(
        tacode='SITE',
        taname='Site',
        enable=True
    )


@pytest.fixture
def test_bu_type():
    """Create BU type TypeAssist"""
    return TypeAssist.objects.create(
        tacode='BUTYPE',
        taname='Business Unit Type',
        enable=True
    )


@pytest.fixture
def test_designation_type():
    """Create designation TypeAssist"""
    return TypeAssist.objects.create(
        tacode='SECURITY_GUARD',
        taname='Security Guard',
        enable=True
    )


@pytest.fixture
def test_shift(test_client_bt, test_bu_bt, test_designation_type):
    """Create test shift"""
    return Shift.objects.create(
        shiftname='Morning Shift',
        starttime=time(9, 0, 0),
        endtime=time(17, 0, 0),
        shiftduration=8,
        peoplecount=10,
        designation=test_designation_type,
        client=test_client_bt,
        bu=test_bu_bt,
        enable=True,
        shift_data={'SECURITY_GUARD': {'count': 10}}
    )


@pytest.fixture
def test_geofence(test_client_bt, test_bu_bt):
    """Create test geofence"""
    # Create a simple rectangular polygon around Bangalore coordinates
    polygon_coords = [
        (77.590, 12.970),  # Southwest
        (77.600, 12.970),  # Southeast  
        (77.600, 12.980),  # Northeast
        (77.590, 12.980),  # Northwest
        (77.590, 12.970)   # Close the polygon
    ]
    
    return GeofenceMaster.objects.create(
        gfcode='OFFICE001',
        gfname='Office Geofence',
        alerttext='You are entering office premises',
        geofence=Polygon(polygon_coords),
        client=test_client_bt,
        bu=test_bu_bt,
        enable=True
    )


@pytest.fixture
def test_device(test_client_bt):
    """Create test device"""
    return Device.objects.create(
        handsetname='Test Mobile Device',
        modelname='Samsung Galaxy S21',
        dateregistered=date.today(),
        lastcommunication=timezone.now(),
        imeino='123456789012345',
        phoneno='9876543210',
        isdeviceon=True,
        client=test_client_bt
    )


@pytest.fixture
def test_subscription(test_client_bt, test_device):
    """Create test subscription"""
    return Subscription.objects.create(
        startdate=date.today(),
        enddate=date.today() + timedelta(days=365),
        status=Subscription.StatusChoices.A.value,
        assignedhandset=test_device,
        client=test_client_bt,
        istemporary=False
    )


@pytest.fixture
def test_people_onboarding(test_client_bt, test_bu_bt):
    """Create test people for onboarding tests"""
    return People.objects.create(
        peoplecode='ONBOARD001',
        peoplename='Test Onboarding User',
        loginid='onboarduser',
        email='onboard@example.com',
        mobno='9876543210',
        dateofbirth='1990-01-01',
        dateofjoin='2023-01-01',
        client=test_client_bt,
        bu=test_bu_bt,
        isverified=True,
        enable=True
    )


@pytest.fixture
def bt_factory():
    """Factory for creating Bt instances"""
    def _create_bt(
        bucode=None,
        buname=None,
        parent=None,
        identifier=None,
        **kwargs
    ):
        defaults = {
            'bucode': bucode or f'BT_{timezone.now().timestamp()}',
            'buname': buname or 'Test Business Unit',
            'enable': kwargs.get('enable', True),
            'iswarehouse': kwargs.get('iswarehouse', False),
            'gpsenable': kwargs.get('gpsenable', False),
            'deviceevent': kwargs.get('deviceevent', False),
            'pdist': kwargs.get('pdist', 0.0),
            'isvendor': kwargs.get('isvendor', False),
            'isserviceprovider': kwargs.get('isserviceprovider', False),
        }
        if parent:
            defaults['parent'] = parent
        if identifier:
            defaults['identifier'] = identifier
            
        defaults.update(kwargs)
        return Bt.objects.create(**defaults)
    
    return _create_bt


@pytest.fixture
def typeassist_factory():
    """Factory for creating TypeAssist instances"""
    def _create_typeassist(
        tacode=None,
        taname=None,
        tatype=None,
        client=None,
        bu=None,
        **kwargs
    ):
        defaults = {
            'tacode': tacode or f'TA_{timezone.now().timestamp()}',
            'taname': taname or 'Test Type Assist',
            'enable': kwargs.get('enable', True),
        }
        if tatype:
            defaults['tatype'] = tatype
        if client:
            defaults['client'] = client
        if bu:
            defaults['bu'] = bu
            
        defaults.update(kwargs)
        return TypeAssist.objects.create(**defaults)
    
    return _create_typeassist


@pytest.fixture
def shift_factory(test_client_bt, test_bu_bt):
    """Factory for creating Shift instances"""
    def _create_shift(
        shiftname=None,
        client=None,
        bu=None,
        designation=None,
        **kwargs
    ):
        defaults = {
            'shiftname': shiftname or f'Shift_{timezone.now().timestamp()}',
            'starttime': kwargs.get('starttime', time(9, 0, 0)),
            'endtime': kwargs.get('endtime', time(17, 0, 0)),
            'shiftduration': kwargs.get('shiftduration', 8),
            'peoplecount': kwargs.get('peoplecount', 5),
            'client': client or test_client_bt,
            'bu': bu or test_bu_bt,
            'enable': kwargs.get('enable', True),
            'nightshiftappicable': kwargs.get('nightshiftappicable', True),
            'captchafreq': kwargs.get('captchafreq', 10),
            'shift_data': kwargs.get('shift_data', {}),
        }
        if designation:
            defaults['designation'] = designation
            
        defaults.update(kwargs)
        return Shift.objects.create(**defaults)
    
    return _create_shift


@pytest.fixture
def geofence_factory(test_client_bt, test_bu_bt):
    """Factory for creating GeofenceMaster instances"""
    def _create_geofence(
        gfcode=None,
        gfname=None,
        client=None,
        bu=None,
        **kwargs
    ):
        # Default polygon coordinates around Bangalore
        default_coords = [
            (77.590, 12.970),
            (77.600, 12.970),
            (77.600, 12.980),
            (77.590, 12.980),
            (77.590, 12.970)
        ]
        
        defaults = {
            'gfcode': gfcode or f'GF_{timezone.now().timestamp()}',
            'gfname': gfname or 'Test Geofence',
            'alerttext': kwargs.get('alerttext', 'Test alert'),
            'geofence': kwargs.get('geofence', Polygon(default_coords)),
            'client': client or test_client_bt,
            'bu': bu or test_bu_bt,
            'enable': kwargs.get('enable', True),
        }
        defaults.update(kwargs)
        return GeofenceMaster.objects.create(**defaults)
    
    return _create_geofence


@pytest.fixture
def device_factory(test_client_bt):
    """Factory for creating Device instances"""
    def _create_device(
        handsetname=None,
        client=None,
        **kwargs
    ):
        defaults = {
            'handsetname': handsetname or f'Device_{timezone.now().timestamp()}',
            'modelname': kwargs.get('modelname', 'Test Model'),
            'dateregistered': kwargs.get('dateregistered', date.today()),
            'lastcommunication': kwargs.get('lastcommunication', timezone.now()),
            'imeino': kwargs.get('imeino', f'{int(timezone.now().timestamp())}'),
            'phoneno': kwargs.get('phoneno', '9876543210'),
            'isdeviceon': kwargs.get('isdeviceon', True),
            'client': client or test_client_bt,
        }
        defaults.update(kwargs)
        return Device.objects.create(**defaults)
    
    return _create_device


@pytest.fixture
def subscription_factory(test_client_bt):
    """Factory for creating Subscription instances"""
    def _create_subscription(
        client=None,
        assignedhandset=None,
        **kwargs
    ):
        defaults = {
            'startdate': kwargs.get('startdate', date.today()),
            'enddate': kwargs.get('enddate', date.today() + timedelta(days=365)),
            'status': kwargs.get('status', Subscription.StatusChoices.A.value),
            'client': client or test_client_bt,
            'istemporary': kwargs.get('istemporary', False),
        }
        if assignedhandset:
            defaults['assignedhandset'] = assignedhandset
            
        defaults.update(kwargs)
        return Subscription.objects.create(**defaults)
    
    return _create_subscription


@pytest.fixture
def authenticated_onboarding_request(rf, test_people_onboarding, test_client_bt, test_bu_bt):
    """Create an authenticated request with session for onboarding testing"""
    request = rf.get('/')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    
    # Set session data for onboarding
    request.session['client_id'] = test_client_bt.id
    request.session['bu_id'] = test_bu_bt.id
    request.session['assignedsites'] = [test_bu_bt.id]
    request.session['user_id'] = test_people_onboarding.id
    request.session['is_superadmin'] = False
    request.session['client_webcaps'] = []
    request.session['client_mobcaps'] = []
    request.session['client_portletcaps'] = []
    request.session['client_reportcaps'] = []
    request.session['client_noccaps'] = []
    request.session['sitecode'] = test_bu_bt.bucode
    request.session['sitename'] = test_bu_bt.buname
    request.session['clientcode'] = test_client_bt.bucode
    request.session['ctzoffset'] = 330  # IST timezone offset
    request.user = test_people_onboarding
    
    return request


@pytest.fixture
def sample_onboarding_data():
    """Sample data for onboarding forms"""
    return {
        'bucode': 'SAMPLEBU',
        'buname': 'Sample Business Unit',
        'enable': True,
        'gpsenable': False,
        'deviceevent': False,
        'pdist': 50.0,
        'iswarehouse': False,
        'isvendor': False,
        'isserviceprovider': False,
        'ctzoffset': 330
    }


@pytest.fixture
def gps_coordinates():
    """Sample GPS coordinates for testing"""
    return {
        'bangalore_office': Point(77.5946, 12.9716),
        'mumbai_office': Point(72.8777, 19.0760),
        'delhi_office': Point(77.1025, 28.7041),
        'chennai_office': Point(80.2707, 13.0827),
        'office_polygon': Polygon([
            (77.590, 12.970),
            (77.600, 12.970), 
            (77.600, 12.980),
            (77.590, 12.980),
            (77.590, 12.970)
        ])
    }


@pytest.fixture
def shift_times():
    """Common shift time configurations"""
    return {
        'morning': {'start': time(9, 0, 0), 'end': time(17, 0, 0)},
        'evening': {'start': time(17, 0, 0), 'end': time(1, 0, 0)},
        'night': {'start': time(22, 0, 0), 'end': time(6, 0, 0)},
        'full_day': {'start': time(0, 0, 0), 'end': time(23, 59, 59)}
    }


@pytest.fixture
def bu_preference_data():
    """Sample BU preference data"""
    return {
        "mobilecapability": ["ATTENDANCE", "TRACKING"],
        "webcapability": ["DASHBOARD", "REPORTS"],
        "portletcapability": ["ALERTS", "NOTIFICATIONS"],
        "reportcapability": ["DAILY", "WEEKLY"],
        "maxadmins": 5,
        "address": "Test Address, Bangalore",
        "permissibledistance": 100,
        "no_of_devices_allowed": 50,
        "no_of_users_allowed_web": 25,
        "no_of_users_allowed_mob": 100,
        "no_of_users_allowed_both": 75,
        "total_people_count": 50,
        "clienttimezone": "Asia/Kolkata",
        "billingtype": "MONTHLY"
    }