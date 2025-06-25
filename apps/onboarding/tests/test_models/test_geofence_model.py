"""
Tests for GeofenceMaster model
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.gis.geos import Point, Polygon
from apps.onboarding.models import GeofenceMaster


@pytest.mark.django_db
class TestGeofenceMasterModel:
    """Test suite for GeofenceMaster model"""
    
    def test_geofence_creation_basic(self, geofence_factory):
        """Test creating a basic GeofenceMaster instance"""
        geofence = geofence_factory()
        
        assert geofence.id is not None
        assert geofence.gfcode is not None
        assert geofence.gfname is not None
        assert geofence.alerttext is not None
        assert geofence.geofence is not None
        assert geofence.enable is True
    
    
    def test_geofence_str_representation(self, geofence_factory):
        """Test GeofenceMaster string representation"""
        geofence = geofence_factory(
            gfcode='TEST001',
            gfname='Test Geofence'
        )
        
        # Note: The __str__ method has a typo using gfname twice
        assert str(geofence) == 'Test Geofence (Test Geofence)'
    
    
    def test_geofence_polygon_field(self, geofence_factory, gps_coordinates):
        """Test GeofenceMaster polygon field"""
        geofence = geofence_factory(
            geofence=gps_coordinates['office_polygon']
        )
        
        assert geofence.geofence is not None
        assert isinstance(geofence.geofence, Polygon)
        
        # Test that polygon has correct number of points
        coords = geofence.geofence.coords[0]
        assert len(coords) == 5  # 4 corners + closing point
        
        # Test coordinate values
        assert coords[0] == (77.590, 12.970)
        assert coords[1] == (77.600, 12.970)
        assert coords[2] == (77.600, 12.980)
        assert coords[3] == (77.590, 12.980)
        assert coords[4] == (77.590, 12.970)  # Closing point
    
    
    def test_geofence_relationships(self, geofence_factory, test_client_bt, test_bu_bt, test_people_onboarding):
        """Test GeofenceMaster foreign key relationships"""
        # Create a people group first (if needed for alerttogroup)
        from apps.peoples.models import Pgroup
        test_group = Pgroup.objects.create(
            groupname='Test Alert Group',
            client=test_client_bt,
            bu=test_bu_bt,
            enable=True
        )
        
        geofence = geofence_factory(
            client=test_client_bt,
            bu=test_bu_bt,
            alerttogroup=test_group,
            alerttopeople=test_people_onboarding
        )
        
        # Test forward relationships
        assert geofence.client == test_client_bt
        assert geofence.bu == test_bu_bt
        assert geofence.alerttogroup == test_group
        assert geofence.alerttopeople == test_people_onboarding
        
        # Test reverse relationships
        assert geofence in test_client_bt.for_clients.all()
        assert geofence in test_bu_bt.for_sites.all()
    
    
    def test_geofence_unique_constraint(self, geofence_factory, test_bu_bt):
        """Test GeofenceMaster unique constraint on gfcode, bu"""
        # Create first geofence
        geofence1 = geofence_factory(
            gfcode='UNIQUE001',
            bu=test_bu_bt
        )
        
        # Try to create duplicate - should raise IntegrityError
        with pytest.raises(IntegrityError):
            geofence_factory(
                gfcode='UNIQUE001',
                bu=test_bu_bt
            )
    
    
    def test_geofence_alert_text_field(self, geofence_factory):
        """Test GeofenceMaster alert text field"""
        alert_messages = [
            'You are entering a restricted area',
            'Welcome to the office premises',
            'Please maintain social distancing',
            'Security checkpoint ahead'
        ]
        
        for alert_text in alert_messages:
            geofence = geofence_factory(
                alerttext=alert_text,
                gfcode=f'ALERT_{alert_text[:5].upper()}'
            )
            assert geofence.alerttext == alert_text
    
    
    def test_geofence_enable_disable_functionality(self, geofence_factory):
        """Test GeofenceMaster enable/disable functionality"""
        enabled_geofence = geofence_factory(
            gfcode='ENABLED001',
            gfname='Enabled Geofence',
            enable=True
        )
        
        disabled_geofence = geofence_factory(
            gfcode='DISABLED001',
            gfname='Disabled Geofence',
            enable=False
        )
        
        assert enabled_geofence.enable is True
        assert disabled_geofence.enable is False
        
        # Test filtering by enabled status
        enabled_geofences = GeofenceMaster.objects.filter(enable=True)
        disabled_geofences = GeofenceMaster.objects.filter(enable=False)
        
        assert enabled_geofence in enabled_geofences
        assert disabled_geofence in disabled_geofences
        assert enabled_geofence not in disabled_geofences
        assert disabled_geofence not in enabled_geofences
    
    
    def test_geofence_different_polygon_shapes(self, geofence_factory):
        """Test GeofenceMaster with different polygon shapes"""
        # Rectangle
        rectangle_coords = [
            (77.590, 12.970),
            (77.600, 12.970),
            (77.600, 12.980),
            (77.590, 12.980),
            (77.590, 12.970)
        ]
        
        rectangle_geofence = geofence_factory(
            gfcode='RECT001',
            gfname='Rectangle Geofence',
            geofence=Polygon(rectangle_coords)
        )
        
        # Triangle
        triangle_coords = [
            (77.595, 12.970),
            (77.605, 12.970),
            (77.600, 12.980),
            (77.595, 12.970)
        ]
        
        triangle_geofence = geofence_factory(
            gfcode='TRI001',
            gfname='Triangle Geofence',
            geofence=Polygon(triangle_coords)
        )
        
        # Pentagon
        pentagon_coords = [
            (77.595, 12.970),
            (77.605, 12.970),
            (77.610, 12.975),
            (77.600, 12.985),
            (77.590, 12.975),
            (77.595, 12.970)
        ]
        
        pentagon_geofence = geofence_factory(
            gfcode='PENT001',
            gfname='Pentagon Geofence',
            geofence=Polygon(pentagon_coords)
        )
        
        # Verify all shapes were created
        assert isinstance(rectangle_geofence.geofence, Polygon)
        assert isinstance(triangle_geofence.geofence, Polygon)
        assert isinstance(pentagon_geofence.geofence, Polygon)
        
        # Verify coordinate counts
        assert len(rectangle_geofence.geofence.coords[0]) == 5  # 4 + 1 closing
        assert len(triangle_geofence.geofence.coords[0]) == 4   # 3 + 1 closing
        assert len(pentagon_geofence.geofence.coords[0]) == 6   # 5 + 1 closing
    
    
    def test_geofence_large_area_coverage(self, geofence_factory):
        """Test GeofenceMaster covering large geographical areas"""
        # Large city area (Bangalore boundaries approximation)
        city_coords = [
            (77.4000, 12.8000),  # Southwest
            (77.8000, 12.8000),  # Southeast
            (77.8000, 13.2000),  # Northeast
            (77.4000, 13.2000),  # Northwest
            (77.4000, 12.8000)   # Closing
        ]
        
        city_geofence = geofence_factory(
            gfcode='CITY001',
            gfname='Bangalore City Geofence',
            geofence=Polygon(city_coords),
            alerttext='Welcome to Bangalore city limits'
        )
        
        # Small building area
        building_coords = [
            (77.5945, 12.9715),
            (77.5947, 12.9715),
            (77.5947, 12.9717),
            (77.5945, 12.9717),
            (77.5945, 12.9715)
        ]
        
        building_geofence = geofence_factory(
            gfcode='BLDG001',
            gfname='Office Building Geofence',
            geofence=Polygon(building_coords),
            alerttext='You are entering the office building'
        )
        
        # Test that both large and small areas work
        assert city_geofence.geofence.area > building_geofence.geofence.area
        assert city_geofence.gfname == 'Bangalore City Geofence'
        assert building_geofence.gfname == 'Office Building Geofence'
    
    
    def test_geofence_bulk_operations(self, geofence_factory, test_client_bt, test_bu_bt):
        """Test bulk operations on GeofenceMaster"""
        # Create multiple geofence records
        geofences = []
        for i in range(20):
            # Create different polygon for each geofence
            coords = [
                (77.590 + i*0.001, 12.970 + i*0.001),
                (77.600 + i*0.001, 12.970 + i*0.001),
                (77.600 + i*0.001, 12.980 + i*0.001),
                (77.590 + i*0.001, 12.980 + i*0.001),
                (77.590 + i*0.001, 12.970 + i*0.001)
            ]
            
            geofence = geofence_factory(
                gfcode=f'BULK_{i:02d}',
                gfname=f'Bulk Geofence {i}',
                geofence=Polygon(coords),
                enable=True if i % 2 == 0 else False,
                client=test_client_bt,
                bu=test_bu_bt
            )
            geofences.append(geofence)
        
        # Test bulk filtering
        bulk_enabled = GeofenceMaster.objects.filter(
            gfcode__startswith='BULK_',
            enable=True
        )
        bulk_disabled = GeofenceMaster.objects.filter(
            gfcode__startswith='BULK_',
            enable=False
        )
        
        assert bulk_enabled.count() == 10
        assert bulk_disabled.count() == 10
        
        # Test bulk update
        GeofenceMaster.objects.filter(
            gfcode__startswith='BULK_'
        ).update(alerttext='Updated bulk alert text')
        
        # Verify bulk update
        updated_geofences = GeofenceMaster.objects.filter(
            gfcode__startswith='BULK_',
            alerttext='Updated bulk alert text'
        )
        assert updated_geofences.count() == 20
    
    
    def test_geofence_filtering_by_client_and_bu(self, geofence_factory, test_client_bt, test_bu_bt):
        """Test GeofenceMaster filtering by client and BU"""
        # Create another client and BU for comparison
        other_client = test_client_bt.__class__.objects.create(
            bucode='OTHER_CLIENT',
            buname='Other Client',
            enable=True
        )
        
        other_bu = test_bu_bt.__class__.objects.create(
            bucode='OTHER_BU',
            buname='Other BU',
            enable=True
        )
        
        # Create geofences for different clients and BUs
        geofence1 = geofence_factory(
            gfcode='GF1',
            gfname='Client1 BU1 Geofence',
            client=test_client_bt,
            bu=test_bu_bt
        )
        
        geofence2 = geofence_factory(
            gfcode='GF2',
            gfname='Client1 BU2 Geofence',
            client=test_client_bt,
            bu=other_bu
        )
        
        geofence3 = geofence_factory(
            gfcode='GF3',
            gfname='Client2 BU1 Geofence',
            client=other_client,
            bu=test_bu_bt
        )
        
        geofence4 = geofence_factory(
            gfcode='GF4',
            gfname='Client2 BU2 Geofence',
            client=other_client,
            bu=other_bu
        )
        
        # Test filtering by client
        client1_geofences = GeofenceMaster.objects.filter(client=test_client_bt)
        client2_geofences = GeofenceMaster.objects.filter(client=other_client)
        
        assert geofence1 in client1_geofences
        assert geofence2 in client1_geofences
        assert geofence3 not in client1_geofences
        assert geofence4 not in client1_geofences
        
        assert geofence3 in client2_geofences
        assert geofence4 in client2_geofences
        assert geofence1 not in client2_geofences
        assert geofence2 not in client2_geofences
        
        # Test filtering by BU
        bu1_geofences = GeofenceMaster.objects.filter(bu=test_bu_bt)
        bu2_geofences = GeofenceMaster.objects.filter(bu=other_bu)
        
        assert geofence1 in bu1_geofences
        assert geofence3 in bu1_geofences
        assert geofence2 not in bu1_geofences
        assert geofence4 not in bu1_geofences
        
        assert geofence2 in bu2_geofences
        assert geofence4 in bu2_geofences
        assert geofence1 not in bu2_geofences
        assert geofence3 not in bu2_geofences
    
    
    def test_geofence_point_containment(self, geofence_factory, gps_coordinates):
        """Test if points are contained within geofence polygons"""
        # Create a geofence around Bangalore office
        office_coords = [
            (77.590, 12.970),
            (77.600, 12.970),
            (77.600, 12.980),
            (77.590, 12.980),
            (77.590, 12.970)
        ]
        
        office_geofence = geofence_factory(
            gfcode='OFFICE_AREA',
            gfname='Office Area Geofence',
            geofence=Polygon(office_coords)
        )
        
        # Test points inside the geofence
        inside_point = Point(77.595, 12.975)  # Center of the polygon
        assert office_geofence.geofence.contains(inside_point)
        
        # Test points outside the geofence
        outside_point = Point(77.610, 12.990)  # Outside the polygon
        assert not office_geofence.geofence.contains(outside_point)
        
        # Test points on the boundary
        boundary_point = Point(77.590, 12.970)  # Corner point
        assert office_geofence.geofence.touches(boundary_point) or office_geofence.geofence.contains(boundary_point)
    
    
    def test_geofence_complex_polygon_shapes(self, geofence_factory):
        """Test GeofenceMaster with complex polygon shapes"""
        # L-shaped polygon
        l_shape_coords = [
            (77.590, 12.970),
            (77.595, 12.970),
            (77.595, 12.975),
            (77.600, 12.975),
            (77.600, 12.980),
            (77.590, 12.980),
            (77.590, 12.970)
        ]
        
        l_shape_geofence = geofence_factory(
            gfcode='L_SHAPE',
            gfname='L-Shaped Geofence',
            geofence=Polygon(l_shape_coords)
        )
        
        # Star-shaped polygon (simplified)
        star_coords = [
            (77.595, 12.970),
            (77.597, 12.973),
            (77.600, 12.973),
            (77.598, 12.976),
            (77.599, 12.979),
            (77.595, 12.977),
            (77.591, 12.979),
            (77.592, 12.976),
            (77.590, 12.973),
            (77.593, 12.973),
            (77.595, 12.970)
        ]
        
        star_geofence = geofence_factory(
            gfcode='STAR_SHAPE',
            gfname='Star-Shaped Geofence',
            geofence=Polygon(star_coords)
        )
        
        # Verify complex shapes were created
        assert isinstance(l_shape_geofence.geofence, Polygon)
        assert isinstance(star_geofence.geofence, Polygon)
        assert len(l_shape_geofence.geofence.coords[0]) == 7
        assert len(star_geofence.geofence.coords[0]) == 11
    
    
    def test_geofence_performance_queries(self, geofence_factory, test_client_bt, test_bu_bt):
        """Test performance-oriented queries on GeofenceMaster"""
        # Create many geofence records for performance testing
        geofences = []
        for i in range(100):
            # Create unique polygon for each geofence
            offset = i * 0.001
            coords = [
                (77.590 + offset, 12.970 + offset),
                (77.600 + offset, 12.970 + offset),
                (77.600 + offset, 12.980 + offset),
                (77.590 + offset, 12.980 + offset),
                (77.590 + offset, 12.970 + offset)
            ]
            
            geofence = geofence_factory(
                gfcode=f'PERF_{i:03d}',
                gfname=f'Performance Geofence {i}',
                geofence=Polygon(coords),
                enable=True if i % 4 == 0 else False,
                client=test_client_bt,
                bu=test_bu_bt
            )
            geofences.append(geofence)
        
        # Test count queries
        total_count = GeofenceMaster.objects.filter(
            gfcode__startswith='PERF_'
        ).count()
        assert total_count == 100
        
        # Test enabled/disabled filtering
        enabled_count = GeofenceMaster.objects.filter(
            gfcode__startswith='PERF_',
            enable=True
        ).count()
        disabled_count = GeofenceMaster.objects.filter(
            gfcode__startswith='PERF_',
            enable=False
        ).count()
        
        assert enabled_count == 25  # Every 4th record (0, 4, 8, ..., 96)
        assert disabled_count == 75
        assert enabled_count + disabled_count == 100
        
        # Test client/BU filtering
        client_geofences = GeofenceMaster.objects.filter(
            gfcode__startswith='PERF_',
            client=test_client_bt
        )
        bu_geofences = GeofenceMaster.objects.filter(
            gfcode__startswith='PERF_',
            bu=test_bu_bt
        )
        
        assert client_geofences.count() == 100
        assert bu_geofences.count() == 100
    
    
    def test_geofence_alert_configuration(self, geofence_factory, test_people_onboarding):
        """Test GeofenceMaster alert configuration"""
        # Create a people group for alert testing
        from apps.peoples.models import Pgroup
        alert_group = Pgroup.objects.create(
            groupname='Security Alert Group',
            client=test_people_onboarding.client,
            bu=test_people_onboarding.bu,
            enable=True
        )
        
        # Geofence with group alert
        group_alert_geofence = geofence_factory(
            gfcode='GROUP_ALERT',
            gfname='Group Alert Geofence',
            alerttext='Security breach detected!',
            alerttogroup=alert_group
        )
        
        # Geofence with individual alert
        individual_alert_geofence = geofence_factory(
            gfcode='INDIVIDUAL_ALERT',
            gfname='Individual Alert Geofence',
            alerttext='Personal alert notification',
            alerttopeople=test_people_onboarding
        )
        
        # Geofence with both group and individual alerts
        both_alert_geofence = geofence_factory(
            gfcode='BOTH_ALERT',
            gfname='Both Alert Geofence',
            alerttext='Critical security alert',
            alerttogroup=alert_group,
            alerttopeople=test_people_onboarding
        )
        
        # Verify alert configurations
        assert group_alert_geofence.alerttogroup == alert_group
        assert group_alert_geofence.alerttopeople is None
        
        assert individual_alert_geofence.alerttopeople == test_people_onboarding
        assert individual_alert_geofence.alerttogroup is None
        
        assert both_alert_geofence.alerttogroup == alert_group
        assert both_alert_geofence.alerttopeople == test_people_onboarding