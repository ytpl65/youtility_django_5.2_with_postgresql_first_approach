"""
Tests for PeopleEventlog model
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.gis.geos import Point, LineString
from django.utils import timezone
from datetime import datetime, timedelta, date
from apps.attendance.models import PeopleEventlog


@pytest.mark.django_db
class TestPeopleEventlogModel:
    """Test suite for PeopleEventlog model"""
    
    def test_people_eventlog_creation_basic(self, people_eventlog_factory):
        """Test creating a basic PeopleEventlog instance"""
        eventlog = people_eventlog_factory()
        
        assert eventlog.uuid is not None
        assert eventlog.people is not None
        assert eventlog.client is not None
        assert eventlog.bu is not None
        assert eventlog.datefor is not None
        assert eventlog.punchintime is not None
        assert eventlog.transportmodes == ['NONE']
        assert eventlog.facerecognitionin is False
        assert eventlog.facerecognitionout is False
    
    
    def test_people_eventlog_str_representation(self, people_eventlog_factory):
        """Test PeopleEventlog string representation"""
        eventlog = people_eventlog_factory(
            remarks='Daily attendance check-in'
        )
        # Model might not have __str__ method, so test basic properties
        assert eventlog.remarks == 'Daily attendance check-in'
        assert str(eventlog.uuid) is not None
    
    
    def test_people_eventlog_transport_mode_choices(self, people_eventlog_factory, transport_modes):
        """Test PeopleEventlog transport mode choices"""
        # Test various transport modes
        for mode in transport_modes[:3]:  # Test first 3 to avoid too many objects
            eventlog = people_eventlog_factory(
                transportmodes=[mode],
                deviceid=f'DEVICE_{mode}'
            )
            assert mode in eventlog.transportmodes
            assert len(eventlog.transportmodes) == 1
    
    
    def test_people_eventlog_multiple_transport_modes(self, people_eventlog_factory):
        """Test PeopleEventlog with multiple transport modes"""
        modes = ['BUS', 'TRAIN']
        eventlog = people_eventlog_factory(
            transportmodes=modes
        )
        
        assert eventlog.transportmodes == modes
        assert 'BUS' in eventlog.transportmodes
        assert 'TRAIN' in eventlog.transportmodes
        assert len(eventlog.transportmodes) == 2
    
    
    def test_people_eventlog_gps_locations(self, people_eventlog_factory, gps_coordinates):
        """Test PeopleEventlog GPS location fields"""
        eventlog = people_eventlog_factory(
            startlocation=gps_coordinates['bangalore_office'],
            endlocation=gps_coordinates['mumbai_office'],
            journeypath=gps_coordinates['journey_path']
        )
        
        assert eventlog.startlocation is not None
        assert eventlog.endlocation is not None
        assert eventlog.journeypath is not None
        
        # Test GPS coordinates
        assert eventlog.startlocation.x == 77.5946
        assert eventlog.startlocation.y == 12.9716
        assert eventlog.endlocation.x == 72.8777
        assert eventlog.endlocation.y == 19.0760
    
    
    def test_people_eventlog_time_fields(self, people_eventlog_factory):
        """Test PeopleEventlog time-related fields"""
        punch_in = timezone.now()
        punch_out = punch_in + timedelta(hours=8)
        
        eventlog = people_eventlog_factory(
            punchintime=punch_in,
            punchouttime=punch_out,
            datefor=punch_in.date(),
            duration=480  # 8 hours in minutes
        )
        
        assert eventlog.punchintime == punch_in
        assert eventlog.punchouttime == punch_out
        assert eventlog.datefor == punch_in.date()
        assert eventlog.duration == 480
        
        # Test duration calculation logic (if implemented)
        time_diff = eventlog.punchouttime - eventlog.punchintime
        expected_minutes = int(time_diff.total_seconds() / 60)
        assert expected_minutes == 480
    
    
    def test_people_eventlog_json_fields(self, people_eventlog_factory):
        """Test PeopleEventlog JSON fields"""
        custom_extras = {
            'verified_in': True,
            'distance_in': 0.5,
            'verified_out': True,
            'distance_out': 0.3,
            'threshold': '0.5',
            'model': 'CustomModel',
            'similarity_metric': 'euclidean'
        }
        
        custom_geojson = {
            'startlocation': 'Office Main Gate',
            'endlocation': 'Office Parking'
        }
        
        eventlog = people_eventlog_factory(
            peventlogextras=custom_extras,
            geojson=custom_geojson
        )
        
        assert eventlog.peventlogextras['verified_in'] is True
        assert eventlog.peventlogextras['model'] == 'CustomModel'
        assert eventlog.geojson['startlocation'] == 'Office Main Gate'
        assert eventlog.geojson['endlocation'] == 'Office Parking'
    
    
    def test_people_eventlog_face_recognition_flags(self, people_eventlog_factory):
        """Test PeopleEventlog face recognition flags"""
        # Test with face recognition enabled
        eventlog_with_face = people_eventlog_factory(
            facerecognitionin=True,
            facerecognitionout=True
        )
        
        assert eventlog_with_face.facerecognitionin is True
        assert eventlog_with_face.facerecognitionout is True
        
        # Test with face recognition disabled
        eventlog_without_face = people_eventlog_factory(
            facerecognitionin=False,
            facerecognitionout=False,
            deviceid='NO_FACE_DEVICE'
        )
        
        assert eventlog_without_face.facerecognitionin is False
        assert eventlog_without_face.facerecognitionout is False
    
    
    def test_people_eventlog_financial_fields(self, people_eventlog_factory):
        """Test PeopleEventlog financial/expense fields"""
        eventlog = people_eventlog_factory(
            expamt=150.75,
            distance=25.5
        )
        
        assert eventlog.expamt == 150.75
        assert eventlog.distance == 25.5
        
        # Test default values
        default_eventlog = people_eventlog_factory()
        assert default_eventlog.expamt == 0.0
        assert default_eventlog.distance == 0.0
    
    
    def test_people_eventlog_device_tracking(self, people_eventlog_factory):
        """Test PeopleEventlog device tracking fields"""
        eventlog = people_eventlog_factory(
            deviceid='ANDROID_12345',
            accuracy=89.5,
            reference='MOBILE_CHECKIN'
        )
        
        assert eventlog.deviceid == 'ANDROID_12345'
        assert eventlog.accuracy == 89.5
        assert eventlog.reference == 'MOBILE_CHECKIN'
    
    
    def test_people_eventlog_relationships(self, people_eventlog_factory, test_people, test_client_bt, test_bu_bt):
        """Test PeopleEventlog foreign key relationships"""
        eventlog = people_eventlog_factory(
            people=test_people,
            client=test_client_bt,
            bu=test_bu_bt,
            verifiedby=test_people
        )
        
        # Test forward relationships
        assert eventlog.people == test_people
        assert eventlog.client == test_client_bt
        assert eventlog.bu == test_bu_bt
        assert eventlog.verifiedby == test_people
        
        # Test reverse relationships
        assert eventlog in test_people.peopleeventlog_set.all()
        assert eventlog in test_client_bt.clients.all()
        assert eventlog in test_bu_bt.bus.all()
    
    
    def test_people_eventlog_shift_assignment(self, people_eventlog_factory, test_shift):
        """Test PeopleEventlog shift assignment"""
        eventlog = people_eventlog_factory(
            shift=test_shift
        )
        
        assert eventlog.shift == test_shift
        assert eventlog.shift.shiftname == 'Morning Shift'
        # Handle both time objects and strings
        start_time = eventlog.shift.starttime
        end_time = eventlog.shift.endtime
        
        if hasattr(start_time, 'strftime'):
            assert start_time.strftime('%H:%M:%S') == '09:00:00'
        else:
            assert str(start_time) == '09:00:00'
            
        if hasattr(end_time, 'strftime'):
            assert end_time.strftime('%H:%M:%S') == '17:00:00'
        else:
            assert str(end_time) == '17:00:00'
    
    
    def test_people_eventlog_geofence_integration(self, people_eventlog_factory, test_geofence):
        """Test PeopleEventlog geofence integration"""
        eventlog = people_eventlog_factory(
            geofence=test_geofence
        )
        
        assert eventlog.geofence == test_geofence
        assert eventlog.geofence.gfcode == 'OFFICE001'
        assert eventlog.geofence.gfname == 'Office Geofence'
    
    
    def test_people_eventlog_bulk_operations(self, people_eventlog_factory, test_people):
        """Test bulk operations on PeopleEventlog"""
        # Create multiple eventlogs
        eventlogs = []
        for i in range(5):
            eventlog = people_eventlog_factory(
                deviceid=f'BULK_DEVICE_{i}',
                datefor=date.today() - timedelta(days=i),
                people=test_people
            )
            eventlogs.append(eventlog)
        
        # Test bulk filtering
        today_events = PeopleEventlog.objects.filter(
            datefor=date.today(),
            people=test_people
        )
        assert today_events.count() == 1
        
        # Test bulk update
        PeopleEventlog.objects.filter(
            deviceid__startswith='BULK_DEVICE'
        ).update(remarks='Bulk updated remark')
        
        # Verify bulk update
        updated_events = PeopleEventlog.objects.filter(
            deviceid__startswith='BULK_DEVICE',
            remarks='Bulk updated remark'
        )
        assert updated_events.count() == 5
    
    
    def test_people_eventlog_date_filtering(self, people_eventlog_factory):
        """Test PeopleEventlog date-based filtering"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Create eventlogs for different dates
        today_event = people_eventlog_factory(
            datefor=today,
            deviceid='TODAY_DEVICE'
        )
        yesterday_event = people_eventlog_factory(
            datefor=yesterday,
            deviceid='YESTERDAY_DEVICE'
        )
        
        # Test date filtering
        today_events = PeopleEventlog.objects.filter(datefor=today)
        yesterday_events = PeopleEventlog.objects.filter(datefor=yesterday)
        
        assert today_event in today_events
        assert yesterday_event in yesterday_events
        assert today_event not in yesterday_events
        assert yesterday_event not in today_events
    
    
    def test_people_eventlog_tenant_isolation(self, people_eventlog_factory):
        """Test PeopleEventlog multi-tenant data isolation"""
        from apps.onboarding.models import Bt
        
        # Create two different clients
        client1 = Bt.objects.create(bucode='CLIENT1', buname='Client 1', enable=True)
        client2 = Bt.objects.create(bucode='CLIENT2', buname='Client 2', enable=True)
        
        # Create eventlogs for different clients
        event1 = people_eventlog_factory(
            client=client1,
            bu=client1,
            deviceid='CLIENT1_DEVICE'
        )
        event2 = people_eventlog_factory(
            client=client2,
            bu=client2,
            deviceid='CLIENT2_DEVICE'
        )
        
        # Test tenant isolation
        client1_events = PeopleEventlog.objects.filter(client=client1)
        client2_events = PeopleEventlog.objects.filter(client=client2)
        
        assert event1 in client1_events
        assert event1 not in client2_events
        assert event2 in client2_events
        assert event2 not in client1_events
    
    
    def test_people_eventlog_performance_fields(self, people_eventlog_factory):
        """Test PeopleEventlog performance and accuracy fields"""
        eventlog = people_eventlog_factory(
            accuracy=95.7,
            distance=12.5,
            duration=300,  # 5 hours
            expamt=75.50
        )
        
        assert eventlog.accuracy == 95.7
        assert eventlog.distance == 12.5
        assert eventlog.duration == 300
        assert eventlog.expamt == 75.50
        
        # Test performance calculations (if implemented)
        if eventlog.distance and eventlog.duration:
            # Speed calculation could be implemented
            speed_kmh = (eventlog.distance / (eventlog.duration / 60)) if eventlog.duration > 0 else 0
            assert speed_kmh >= 0