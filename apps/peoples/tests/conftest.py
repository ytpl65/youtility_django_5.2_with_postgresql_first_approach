"""
Fixtures for peoples app testing
"""
import pytest
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django.contrib.gis.geos import Point
from datetime import datetime, timedelta
from apps.peoples.models import People, Pgroup, Pgbelonging, Capability, BaseModel
from apps.onboarding.models import Bt, TypeAssist


@pytest.fixture
def rf():
    """Request factory"""
    return RequestFactory()


@pytest.fixture
def test_password():
    """Standard test password"""
    return 'test_password_123'


@pytest.fixture
def test_client_bt():
    """Create test client BT"""
    return Bt.objects.create(
        bucode='TESTCLIENT',
        buname='Test Client',
        enable=True
    )


@pytest.fixture
def test_bu_bt():
    """Create test BU"""
    return Bt.objects.create(
        bucode='TESTBU',
        buname='Test BU',
        enable=True
    )


@pytest.fixture
def test_typeassist_department(test_client_bt, test_bu_bt):
    """Create test department TypeAssist"""
    return TypeAssist.objects.create(
        tacode='DEPT001',
        taname='Test Department',
        client=test_client_bt,
        bu=test_bu_bt,
        enable=True
    )


@pytest.fixture
def test_typeassist_designation(test_client_bt, test_bu_bt):
    """Create test designation TypeAssist"""
    return TypeAssist.objects.create(
        tacode='DESIG001',
        taname='Test Designation',
        client=test_client_bt,
        bu=test_bu_bt,
        enable=True
    )


@pytest.fixture
def people_factory(test_client_bt, test_bu_bt, test_typeassist_department, test_typeassist_designation):
    """Factory for creating People instances"""
    def _create_people(
        peoplecode='TEST001',
        peoplename='Test Person',
        loginid='testuser',
        email='test@example.com',
        mobno='1234567890',
        client=None,
        bu=None,
        department=None,
        designation=None,
        **kwargs
    ):
        defaults = {
            'peoplecode': peoplecode,
            'peoplename': peoplename,
            'loginid': loginid,
            'email': email,
            'mobno': mobno,
            'client': client or test_client_bt,
            'bu': bu or test_bu_bt,
            'department': department or test_typeassist_department,
            'designation': designation or test_typeassist_designation,
            'dateofbirth': kwargs.get('dateofbirth', '1990-01-01'),
            'dateofjoin': kwargs.get('dateofjoin', '2023-01-01'),
            'dateofreport': kwargs.get('dateofreport', '2023-01-01'),
            'isverified': kwargs.get('isverified', True),
            'enable': kwargs.get('enable', True),
            'gender': kwargs.get('gender', 'M'),
        }
        defaults.update(kwargs)
        return People.objects.create(**defaults)
    
    return _create_people


@pytest.fixture
def pgroup_factory(test_client_bt, test_bu_bt):
    """Factory for creating Pgroup instances"""
    def _create_pgroup(
        groupname='Test Group',
        client=None,
        bu=None,
        **kwargs
    ):
        defaults = {
            'groupname': groupname,
            'client': client or test_client_bt,
            'bu': bu or test_bu_bt,
            'enable': kwargs.get('enable', True),
        }
        defaults.update(kwargs)
        return Pgroup.objects.create(**defaults)
    
    return _create_pgroup


@pytest.fixture
def capability_factory():
    """Factory for creating Capability instances"""
    def _create_capability(
        capname='test_capability',
        capdesc='Test Capability Description',
        **kwargs
    ):
        defaults = {
            'capname': capname,
            'capdesc': capdesc,
            'enable': kwargs.get('enable', True),
        }
        defaults.update(kwargs)
        return Capability.objects.create(**defaults)
    
    return _create_capability


@pytest.fixture
def authenticated_request(rf, people_factory):
    """Create an authenticated request with session"""
    request = rf.get('/')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    
    # Create test user
    user = people_factory(loginid='testuser', peoplecode='TESTUSER')
    
    # Set session data with all required fields
    request.session['client_id'] = user.client.id
    request.session['bu_id'] = user.bu.id
    request.session['assignedsites'] = [user.bu.id]
    request.session['user_id'] = user.id
    request.session['is_superadmin'] = False
    request.session['client_webcaps'] = []
    request.session['client_mobcaps'] = []
    request.session['client_portletcaps'] = []
    request.session['client_reportcaps'] = []
    request.session['client_noccaps'] = []
    request.user = user
    
    return request


@pytest.fixture
def admin_user(people_factory):
    """Create admin user"""
    return people_factory(
        peoplecode='ADMIN001',
        peoplename='Admin User',
        loginid='admin',
        email='admin@example.com',
        isadmin=True,
        is_staff=True
    )


@pytest.fixture
def regular_user(people_factory):
    """Create regular user"""
    return people_factory(
        peoplecode='USER001',
        peoplename='Regular User',
        loginid='user',
        email='user@example.com',
        isadmin=False,
        is_staff=False
    )


@pytest.fixture
def fresh_client():
    """Create a fresh Django test client for each test"""
    from django.test import Client
    return Client()