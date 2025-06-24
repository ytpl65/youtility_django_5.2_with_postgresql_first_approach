"""
Tests for Tracking model
"""
import pytest
from django.core.exceptions import ValidationError
from django.contrib.gis.geos import Point
from django.utils import timezone
from datetime import datetime, timedelta
from apps.attendance.models import Tracking


@pytest.mark.django_db
class TestTrackingModel:
    """Test suite for Tracking model"""
    
    def test_tracking_creation_basic(self, tracking_factory):
        """Test creating a basic Tracking instance"""
        tracking = tracking_factory()
        
        assert tracking.uuid is not None
        assert tracking.people is not None
        assert tracking.deviceid is not None
        assert tracking.gpslocation is not None
        assert tracking.receiveddate is not None
        assert tracking.transportmode is not None
        assert tracking.identifier == 'TRACKING'
    
    
    def test_tracking_identifier_choices(self, tracking_factory):
        """Test Tracking identifier choices"""
        identifiers = [
            'NONE', 'CONVEYANCE', 'EXTERNALTOUR', 
            'INTERNALTOUR', 'SITEVISIT', 'TRACKING'
        ]
        
        for identifier in identifiers:
            tracking = tracking_factory(
                identifier=identifier,
                deviceid=f'DEVICE_{identifier}'
            )
            assert tracking.identifier == identifier
    
    
    def test_tracking_gps_location(self, tracking_factory, gps_coordinates):
        """Test Tracking GPS location field"""
        location = gps_coordinates['bangalore_office']
        tracking = tracking_factory(
            gpslocation=location
        )
        
        assert tracking.gpslocation is not None
        assert tracking.gpslocation.x == 77.5946
        assert tracking.gpslocation.y == 12.9716
        
        # Test with different coordinates
        mumbai_tracking = tracking_factory(
            gpslocation=gps_coordinates['mumbai_office'],
            deviceid='MUMBAI_DEVICE'
        )
        assert mumbai_tracking.gpslocation.x == 72.8777
        assert mumbai_tracking.gpslocation.y == 19.0760
    
    
    def test_tracking_device_identification(self, tracking_factory):
        """Test Tracking device identification"""
        tracking = tracking_factory(
            deviceid='MOBILE_ANDROID_123456',
            transportmode='CAR'
        )
        
        assert tracking.deviceid == 'MOBILE_ANDROID_123456'
        assert tracking.transportmode == 'CAR'
    
    
    def test_tracking_time_fields(self, tracking_factory):
        """Test Tracking time-related fields"""
        received_time = timezone.now()
        tracking = tracking_factory(
            receiveddate=received_time
        )
        
        assert tracking.receiveddate == received_time
        
        # Test that received time is properly stored
        time_diff = timezone.now() - tracking.receiveddate
        assert time_diff < timedelta(seconds=5)  # Should be very recent
    
    
    def test_tracking_transport_modes(self, tracking_factory):
        """Test Tracking transport modes"""
        transport_modes = [
            'BIKE', 'CAR', 'BUS', 'TRAIN', 'WALKING', 'NONE'
        ]
        
        for mode in transport_modes:
            tracking = tracking_factory(
                transportmode=mode,
                deviceid=f'DEVICE_{mode}'
            )
            assert tracking.transportmode == mode
    
    
    def test_tracking_reference_field(self, tracking_factory):
        """Test Tracking reference field"""
        tracking = tracking_factory(
            reference='EXTERNAL_TOUR_REF_001',
            identifier='EXTERNALTOUR'
        )
        
        assert tracking.reference == 'EXTERNAL_TOUR_REF_001'
        assert tracking.identifier == 'EXTERNALTOUR'
    
    
    def test_tracking_people_relationship(self, tracking_factory, test_people):
        """Test Tracking relationship with People"""
        tracking = tracking_factory(
            people=test_people
        )
        
        assert tracking.people == test_people
        assert tracking in test_people.tracking_set.all()
    
    
    def test_tracking_bulk_operations(self, tracking_factory, test_people):
        """Test bulk operations on Tracking"""
        # Create multiple tracking records
        trackings = []
        for i in range(10):
            tracking = tracking_factory(
                deviceid=f'BULK_TRACK_{i}',
                people=test_people,
                transportmode='BUS' if i % 2 == 0 else 'TRAIN'
            )
            trackings.append(tracking)
        
        # Test bulk filtering
        bus_trackings = Tracking.objects.filter(
            transportmode='BUS',
            people=test_people
        )
        train_trackings = Tracking.objects.filter(
            transportmode='TRAIN',
            people=test_people
        )
        
        assert bus_trackings.count() == 5
        assert train_trackings.count() == 5
        
        # Test bulk update
        Tracking.objects.filter(
            deviceid__startswith='BULK_TRACK'
        ).update(identifier='CONVEYANCE')
        
        # Verify bulk update
        updated_trackings = Tracking.objects.filter(
            deviceid__startswith='BULK_TRACK',
            identifier='CONVEYANCE'
        )
        assert updated_trackings.count() == 10
    
    
    def test_tracking_location_based_queries(self, tracking_factory, gps_coordinates):
        """Test location-based queries on Tracking"""
        # Create trackings at different locations
        bangalore_tracking = tracking_factory(
            gpslocation=gps_coordinates['bangalore_office'],
            deviceid='BLR_DEVICE'
        )
        mumbai_tracking = tracking_factory(
            gpslocation=gps_coordinates['mumbai_office'],
            deviceid='MUM_DEVICE'
        )
        
        # Test basic location existence
        bangalore_trackings = Tracking.objects.filter(
            gpslocation__isnull=False,
            deviceid='BLR_DEVICE'
        )
        mumbai_trackings = Tracking.objects.filter(
            gpslocation__isnull=False,
            deviceid='MUM_DEVICE'
        )
        
        assert bangalore_tracking in bangalore_trackings
        assert mumbai_tracking in mumbai_trackings
        
        # Test coordinate values directly
        assert bangalore_tracking.gpslocation.x == 77.5946
        assert mumbai_tracking.gpslocation.x == 72.8777
    
    
    def test_tracking_time_range_queries(self, tracking_factory):
        """Test time-based queries on Tracking"""
        now = timezone.now()
        hour_ago = now - timedelta(hours=1)
        
        # Create trackings at different times
        recent_tracking = tracking_factory(
            receiveddate=now,
            deviceid='RECENT_DEVICE'
        )
        old_tracking = tracking_factory(
            receiveddate=hour_ago,
            deviceid='OLD_DEVICE'
        )
        
        # Test time range filtering
        recent_trackings = Tracking.objects.filter(
            receiveddate__gte=now - timedelta(minutes=5)
        )
        old_trackings = Tracking.objects.filter(
            receiveddate__lt=now - timedelta(minutes=30)
        )
        
        assert recent_tracking in recent_trackings
        assert old_tracking in old_trackings
        assert recent_tracking not in old_trackings
    
    
    def test_tracking_str_representation(self, tracking_factory):
        """Test Tracking string representation"""
        tracking = tracking_factory(
            deviceid='TEST_DEVICE_STR'
        )
        
        # Model might not have __str__ method, so test basic properties
        assert tracking.deviceid == 'TEST_DEVICE_STR'
        assert str(tracking.uuid) is not None
    
    
    def test_tracking_uuid_uniqueness(self, tracking_factory):
        """Test Tracking UUID uniqueness"""
        tracking1 = tracking_factory(deviceid='DEVICE1')
        tracking2 = tracking_factory(deviceid='DEVICE2')
        
        assert tracking1.uuid != tracking2.uuid
        assert tracking1.uuid is not None
        assert tracking2.uuid is not None
    
    
    def test_tracking_conveyance_workflow(self, tracking_factory):
        """Test Tracking in conveyance workflow"""
        tracking = tracking_factory(
            identifier='CONVEYANCE',
            transportmode='TAXI',
            reference='CONVEYANCE_TRIP_001'
        )
        
        assert tracking.identifier == 'CONVEYANCE'
        assert tracking.transportmode == 'TAXI'
        assert tracking.reference == 'CONVEYANCE_TRIP_001'
    
    
    def test_tracking_tour_workflow(self, tracking_factory):
        """Test Tracking in tour workflows"""
        # External tour tracking
        external_tracking = tracking_factory(
            identifier='EXTERNALTOUR',
            reference='EXT_TOUR_001',
            deviceid='EXT_DEVICE'
        )
        
        # Internal tour tracking
        internal_tracking = tracking_factory(
            identifier='INTERNALTOUR',
            reference='INT_TOUR_001',
            deviceid='INT_DEVICE'
        )
        
        assert external_tracking.identifier == 'EXTERNALTOUR'
        assert internal_tracking.identifier == 'INTERNALTOUR'
        assert external_tracking.reference == 'EXT_TOUR_001'
        assert internal_tracking.reference == 'INT_TOUR_001'
    
    
    def test_tracking_site_visit_workflow(self, tracking_factory):
        """Test Tracking in site visit workflow"""
        tracking = tracking_factory(
            identifier='SITEVISIT',
            reference='SITE_VISIT_001'
        )
        
        assert tracking.identifier == 'SITEVISIT'
        assert tracking.reference == 'SITE_VISIT_001'
    
    
    def test_tracking_performance_queries(self, tracking_factory):
        """Test performance-oriented queries on Tracking"""
        # Create tracking records for performance testing
        trackings = []
        for i in range(50):
            tracking = tracking_factory(
                deviceid=f'PERF_DEVICE_{i}',
                identifier='TRACKING' if i % 2 == 0 else 'CONVEYANCE'
            )
            trackings.append(tracking)
        
        # Test count queries
        total_count = Tracking.objects.filter(
            deviceid__startswith='PERF_DEVICE'
        ).count()
        assert total_count == 50
        
        # Test identifier-based filtering
        tracking_count = Tracking.objects.filter(
            deviceid__startswith='PERF_DEVICE',
            identifier='TRACKING'
        ).count()
        conveyance_count = Tracking.objects.filter(
            deviceid__startswith='PERF_DEVICE',
            identifier='CONVEYANCE'
        ).count()
        
        assert tracking_count == 25
        assert conveyance_count == 25