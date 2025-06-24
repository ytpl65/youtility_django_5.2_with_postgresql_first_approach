"""
Tests for People model
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.auth import authenticate
from apps.peoples.models import People
from apps.onboarding.models import Bt


@pytest.mark.django_db
class TestPeopleModel:
    """Test suite for People model"""
    
    def test_people_creation_with_required_fields(self, people_factory):
        """Test creating a people instance with required fields"""
        person = people_factory()
        
        assert person.uuid is not None
        assert person.peoplecode == 'TEST001'
        assert person.peoplename == 'Test Person'
        assert person.loginid == 'testuser'
        assert person.email == 'test@example.com'
        assert person.mobno == '1234567890'
        assert person.isverified is True
        assert person.enable is True
    
    
    def test_people_str_representation(self, people_factory):
        """Test People model string representation"""
        person = people_factory(
            peoplename='John Doe',
            peoplecode='JD001'
        )
        assert str(person) == 'John Doe (JD001)'
    
    
    def test_people_authentication_integration(self, people_factory, test_password):
        """Test People model works with Django authentication"""
        person = people_factory(loginid='authuser')
        person.set_password(test_password)
        person.save()
        
        # Test authentication
        authenticated_user = authenticate(
            username='authuser',
            password=test_password
        )
        assert authenticated_user == person
        assert authenticated_user.is_authenticated
    
    
    def test_people_unique_constraints(self, people_factory, test_client_bt, test_bu_bt):
        """Test People model unique constraints"""
        # Create first person
        people_factory(
            loginid='unique_user',
            peoplecode='UNIQUE001',
            client=test_client_bt,
            bu=test_bu_bt
        )
        
        # Try to create another person with same loginid and bu
        with pytest.raises(IntegrityError):
            people_factory(
                loginid='unique_user',
                peoplecode='UNIQUE002',
                client=test_client_bt,
                bu=test_bu_bt
            )
    
    
    def test_people_gender_choices(self, people_factory):
        """Test People model gender choices"""
        # Test valid gender choices
        for gender_code, gender_name in People.Gender.choices:
            person = people_factory(
                peoplecode=f'GENDER_{gender_code}',
                loginid=f'user_{gender_code.lower()}',
                gender=gender_code
            )
            assert person.gender == gender_code
    
    
    def test_people_admin_flags(self, people_factory):
        """Test People model admin and staff flags"""
        admin_person = people_factory(
            peoplecode='ADMIN001',
            loginid='admin_user',
            isadmin=True,
            is_staff=True
        )
        
        regular_person = people_factory(
            peoplecode='REG001',
            loginid='regular_user',
            isadmin=False,
            is_staff=False
        )
        
        assert admin_person.isadmin is True
        assert admin_person.is_staff is True
        assert regular_person.isadmin is False
        assert regular_person.is_staff is False
    
    
    def test_people_json_extras_field(self, people_factory):
        """Test People model JSON extras field"""
        person = people_factory()
        
        # Test default JSON structure
        assert isinstance(person.people_extras, dict)
        assert 'mobilecapability' in person.people_extras
        assert 'webcapability' in person.people_extras
        assert 'debug' in person.people_extras
        assert person.people_extras['debug'] is False
        
        # Test updating JSON field
        person.people_extras['debug'] = True
        person.people_extras['custom_field'] = 'test_value'
        person.save()
        
        person.refresh_from_db()
        assert person.people_extras['debug'] is True
        assert person.people_extras['custom_field'] == 'test_value'
    
    
    def test_people_reporting_hierarchy(self, people_factory):
        """Test People model reporting hierarchy (self-referential)"""
        manager = people_factory(
            peoplecode='MGR001',
            peoplename='Manager',
            loginid='manager'
        )
        
        employee = people_factory(
            peoplecode='EMP001',
            peoplename='Employee',
            loginid='employee',
            reportto=manager
        )
        
        assert employee.reportto == manager
        assert employee in manager.children.all()
    
    
    def test_people_enable_disable_functionality(self, people_factory):
        """Test People model enable/disable functionality"""
        person = people_factory(enable=True)
        assert person.enable is True
        
        # Disable person
        person.enable = False
        person.save()
        
        person.refresh_from_db()
        assert person.enable is False
    
    
    def test_people_verification_status(self, people_factory):
        """Test People model verification status"""
        verified_person = people_factory(isverified=True)
        unverified_person = people_factory(
            peoplecode='UNVER001',
            loginid='unverified',
            isverified=False
        )
        
        assert verified_person.isverified is True
        assert unverified_person.isverified is False
    
    
    def test_people_foreign_key_relationships(self, people_factory, test_client_bt, test_bu_bt):
        """Test People model foreign key relationships"""
        person = people_factory(client=test_client_bt, bu=test_bu_bt)
        
        # Test relationships exist
        assert person.client == test_client_bt
        assert person.bu == test_bu_bt
        assert person.department is not None
        assert person.designation is not None
        
        # Test reverse relationships
        assert person in test_client_bt.people_clients.all()
        assert person in test_bu_bt.people_bus.all()
    
    
    def test_people_date_fields_validation(self, people_factory):
        """Test People model date fields"""
        from datetime import date
        
        person = people_factory(
            dateofbirth=date(1990, 5, 15),
            dateofjoin=date(2023, 1, 1),
            dateofreport=date(2023, 1, 5)
        )
        
        assert person.dateofbirth == date(1990, 5, 15)
        assert person.dateofjoin == date(2023, 1, 1)
        assert person.dateofreport == date(2023, 1, 5)
    
    
    def test_people_secure_string_fields(self, people_factory):
        """Test People model SecureString fields (email, mobno)"""
        person = people_factory(
            email='secure@example.com',
            mobno='9876543210'
        )
        
        # Test that values are stored (encryption/decryption currently disabled)
        assert person.email == 'secure@example.com'
        assert person.mobno == '9876543210'
    
    
    def test_people_device_id_field(self, people_factory):
        """Test People model device ID field"""
        person = people_factory()
        
        # Test default device ID
        assert person.deviceid == '-1'
        
        # Test updating device ID
        person.deviceid = 'DEVICE123'
        person.save()
        
        person.refresh_from_db()
        assert person.deviceid == 'DEVICE123'
    
    
    def test_people_image_upload_path(self, people_factory):
        """Test People model image upload functionality"""
        person = people_factory()
        
        # Test default image
        assert person.peopleimg.name == 'master/people/blank.png'
    
    
    def test_people_username_field_configuration(self, people_factory):
        """Test People model USERNAME_FIELD configuration"""
        person = people_factory(loginid='username_test')
        
        # Test that USERNAME_FIELD is set correctly
        assert People.USERNAME_FIELD == 'loginid'
        assert person.get_username() == 'username_test'
    
    
    def test_people_required_fields_configuration(self, people_factory):
        """Test People model REQUIRED_FIELDS configuration"""
        expected_required_fields = ['peoplecode', 'peoplename', 'dateofbirth', 'email']
        assert People.REQUIRED_FIELDS == expected_required_fields
    
    
    def test_people_multi_tenant_isolation(self, people_factory):
        """Test People model multi-tenant data isolation"""
        # Create two different clients
        client1 = Bt.objects.create(bucode='CLIENT1', buname='Client 1', enable=True)
        client2 = Bt.objects.create(bucode='CLIENT2', buname='Client 2', enable=True)
        
        # Create people in different clients
        person1 = people_factory(
            peoplecode='TENANT1',
            loginid='tenant1_user',
            client=client1,
            bu=client1
        )
        person2 = people_factory(
            peoplecode='TENANT2',
            loginid='tenant2_user',
            client=client2,
            bu=client2
        )
        
        # Test tenant isolation
        client1_people = People.objects.filter(client=client1)
        client2_people = People.objects.filter(client=client2)
        
        assert person1 in client1_people
        assert person1 not in client2_people
        assert person2 in client2_people
        assert person2 not in client1_people
    
    
    def test_people_base_model_fields(self, people_factory):
        """Test People model inherits BaseModel fields correctly"""
        person = people_factory()
        
        # Test BaseModel fields exist
        assert hasattr(person, 'cdtz')
        assert hasattr(person, 'mdtz')
        assert hasattr(person, 'cuser')
        assert hasattr(person, 'muser')
        assert hasattr(person, 'ctzoffset')
        
        # Test default values
        assert person.cdtz is not None
        assert person.mdtz is not None
        assert person.ctzoffset == -1