"""
Fixtures for attendance app testing
"""
import pytest
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils import timezone
from django.contrib.gis.geos import Point, LineString
from datetime import datetime, timedelta, date
from apps.attendance.models import PeopleEventlog, Tracking
from apps.peoples.models import People
from apps.onboarding.models import Bt, TypeAssist, Shift, GeofenceMaster


@pytest.fixture
def rf():
    """Request factory"""
    return RequestFactory()


@pytest.fixture
def test_client_bt():
    """Create test client BT"""
    return Bt.objects.create(
        bucode='ATTCLIENT',
        buname='Attendance Test Client',
        enable=True
    )


@pytest.fixture
def test_bu_bt():
    """Create test BU"""
    return Bt.objects.create(
        bucode='ATTBU',
        buname='Attendance Test BU',
        enable=True
    )


@pytest.fixture
def test_peventtype(test_client_bt, test_bu_bt):
    """Create test event type TypeAssist"""
    return TypeAssist.objects.create(
        tacode='CHECKIN',
        taname='Check In',
        client=test_client_bt,
        bu=test_bu_bt,
        enable=True
    )


@pytest.fixture
def test_shift(test_client_bt, test_bu_bt):
    """Create test shift"""
    return Shift.objects.create(
        shiftname='Morning Shift',
        starttime='09:00:00',
        endtime='17:00:00',
        shiftduration=8,
        peoplecount=10,
        client=test_client_bt,
        bu=test_bu_bt,
        enable=True
    )


@pytest.fixture
def test_geofence(test_client_bt, test_bu_bt):
    """Create test geofence"""
    return GeofenceMaster.objects.create(
        gfcode='OFFICE001',
        gfname='Office Geofence',
        alerttext='Office area alert',
        client=test_client_bt,
        bu=test_bu_bt,
        enable=True
    )


@pytest.fixture
def test_people(test_client_bt, test_bu_bt):
    """Create test people for attendance"""
    return People.objects.create(
        peoplecode='ATTENDEE001',
        peoplename='Test Attendee',
        loginid='attendee',
        email='attendee@example.com',
        mobno='1234567890',
        dateofbirth='1990-01-01',
        dateofjoin='2023-01-01',
        client=test_client_bt,
        bu=test_bu_bt,
        isverified=True,
        enable=True
    )


@pytest.fixture
def people_eventlog_factory(test_people, test_client_bt, test_bu_bt, test_peventtype, test_shift, test_geofence):
    """Factory for creating PeopleEventlog instances"""
    def _create_eventlog(
        people=None,
        client=None,
        bu=None,
        peventtype=None,
        shift=None,
        geofence=None,
        **kwargs
    ):
        defaults = {
            'people': people or test_people,
            'client': client or test_client_bt,
            'bu': bu or test_bu_bt,
            'peventtype': peventtype or test_peventtype,
            'shift': shift or test_shift,
            'geofence': geofence or test_geofence,
            'verifiedby': people or test_people,
            'transportmodes': kwargs.get('transportmodes', ['NONE']),
            'punchintime': kwargs.get('punchintime', timezone.now()),
            'datefor': kwargs.get('datefor', date.today()),
            'distance': kwargs.get('distance', 0.0),
            'duration': kwargs.get('duration', 0),
            'expamt': kwargs.get('expamt', 0.0),
            'accuracy': kwargs.get('accuracy', 95.0),
            'deviceid': kwargs.get('deviceid', 'TEST_DEVICE_001'),
            'startlocation': kwargs.get('startlocation', Point(77.5946, 12.9716)),
            'remarks': kwargs.get('remarks', 'Test attendance record'),
            'facerecognitionin': kwargs.get('facerecognitionin', False),
            'facerecognitionout': kwargs.get('facerecognitionout', False),
            'otherlocation': kwargs.get('otherlocation', 'Test Location'),
            'reference': kwargs.get('reference', 'TEST_REF'),
        }
        defaults.update(kwargs)
        return PeopleEventlog.objects.create(**defaults)
    
    return _create_eventlog


@pytest.fixture
def tracking_factory(test_people):
    """Factory for creating Tracking instances"""
    def _create_tracking(
        people=None,
        **kwargs
    ):
        defaults = {
            'people': people or test_people,
            'deviceid': kwargs.get('deviceid', 'TEST_TRACK_001'),
            'gpslocation': kwargs.get('gpslocation', Point(77.5946, 12.9716)),
            'receiveddate': kwargs.get('receiveddate', timezone.now()),
            'transportmode': kwargs.get('transportmode', 'NONE'),
            'reference': kwargs.get('reference', 'TEST_TRACK_REF'),
            'identifier': kwargs.get('identifier', 'TRACKING'),
        }
        defaults.update(kwargs)
        return Tracking.objects.create(**defaults)
    
    return _create_tracking


@pytest.fixture
def authenticated_attendance_request(rf, test_people, test_client_bt, test_bu_bt):
    """Create an authenticated request with session for attendance testing"""
    request = rf.get('/')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    
    # Set session data with all required fields for attendance
    request.session['client_id'] = test_client_bt.id
    request.session['bu_id'] = test_bu_bt.id
    request.session['assignedsites'] = [test_bu_bt.id]
    request.session['user_id'] = test_people.id
    request.session['is_superadmin'] = False
    request.session['client_webcaps'] = []
    request.session['client_mobcaps'] = []
    request.session['client_portletcaps'] = []
    request.session['client_reportcaps'] = []
    request.session['client_noccaps'] = []
    request.session['sitecode'] = test_bu_bt.bucode
    request.session['sitename'] = test_bu_bt.buname
    request.session['clientcode'] = test_client_bt.bucode
    request.user = test_people
    
    return request


@pytest.fixture
def sample_attendance_data():
    """Sample data for attendance forms"""
    return {
        'people': 1,
        'datefor': date.today().strftime('%d-%b-%Y'),
        'peventtype': 1,
        'verifiedby': 1,
        'punchintime': timezone.now().strftime('%d-%b-%Y %H:%M:%S'),
        'punchouttime': (timezone.now() + timedelta(hours=8)).strftime('%d-%b-%Y %H:%M:%S'),
        'remarks': 'Test attendance entry',
        'ctzoffset': 330,
        'transportmodes': ['NONE'],
        'distance': 0.0,
        'duration': 480,  # 8 hours in minutes
        'expamt': 0.0,
        'accuracy': 95.0,
        'deviceid': 'TEST_DEVICE',
        'facerecognitionin': False,
        'facerecognitionout': False,
        'otherlocation': 'Office',
        'reference': 'ATTENDANCE_TEST'
    }


@pytest.fixture
def gps_coordinates():
    """Sample GPS coordinates for testing"""
    return {
        'bangalore_office': Point(77.5946, 12.9716),
        'mumbai_office': Point(72.8777, 19.0760),
        'delhi_office': Point(77.1025, 28.7041),
        'chennai_office': Point(80.2707, 13.0827),
        'journey_path': LineString([
            (77.5946, 12.9716),  # Start
            (77.5950, 12.9720),  # Waypoint 1
            (77.5955, 12.9725),  # Waypoint 2
            (77.5960, 12.9730),  # End
        ])
    }


@pytest.fixture
def transport_modes():
    """Available transport modes for testing"""
    return [
        'BIKE', 'RICKSHAW', 'BUS', 'TRAIN', 'TRAM', 
        'PLANE', 'FERRY', 'NONE', 'CAR', 'TAXI', 'OLA_UBER'
    ]