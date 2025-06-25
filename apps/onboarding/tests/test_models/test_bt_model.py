"""
Tests for Bt (Business Unit) model
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from django.utils import timezone
from apps.onboarding.models import Bt


@pytest.mark.django_db
class TestBtModel:
    """Test suite for Bt model"""
    
    def test_bt_creation_basic(self, bt_factory):
        """Test creating a basic Bt instance"""
        bt = bt_factory()
        
        assert bt.uuid is not None
        assert bt.bucode is not None
        assert bt.buname is not None
        assert bt.enable is True
        assert bt.iswarehouse is False
        assert bt.gpsenable is False
        assert bt.deviceevent is False
        assert bt.pdist == 0.0
        assert bt.isvendor is False
        assert bt.isserviceprovider is False
    
    
    def test_bt_str_representation(self, bt_factory):
        """Test Bt string representation"""
        bt = bt_factory(
            bucode='TESTCODE',
            buname='Test Business Unit'
        )
        
        assert str(bt) == 'Test Business Unit (TESTCODE)'
    
    
    def test_bt_hierarchy_parent_child(self, bt_factory):
        """Test Bt parent-child hierarchy"""
        parent_bt = bt_factory(
            bucode='PARENT',
            buname='Parent BU'
        )
        
        child_bt = bt_factory(
            bucode='CHILD',
            buname='Child BU',
            parent=parent_bt
        )
        
        assert child_bt.parent == parent_bt
        assert child_bt in parent_bt.children.all()
        assert parent_bt.parent is None
    
    
    def test_bt_gps_location_field(self, bt_factory, gps_coordinates):
        """Test Bt GPS location field"""
        bt = bt_factory(
            gpslocation=gps_coordinates['bangalore_office'],
            gpsenable=True
        )
        
        assert bt.gpslocation is not None
        assert bt.gpslocation.x == 77.5946
        assert bt.gpslocation.y == 12.9716
        assert bt.gpsenable is True
    
    
    def test_bt_preferences_json_field(self, bt_factory, bu_preference_data):
        """Test Bt preferences JSON field"""
        bt = bt_factory(
            bupreferences=bu_preference_data
        )
        
        assert bt.bupreferences is not None
        assert bt.bupreferences['maxadmins'] == 5
        assert bt.bupreferences['address'] == 'Test Address, Bangalore'
        assert bt.bupreferences['no_of_devices_allowed'] == 50
        assert 'ATTENDANCE' in bt.bupreferences['mobilecapability']
        assert 'DASHBOARD' in bt.bupreferences['webcapability']
    
    
    def test_bt_unique_constraint(self, bt_factory, test_identifier_client):
        """Test Bt unique constraint on bucode, parent, identifier"""
        parent_bt = bt_factory(bucode='PARENT')
        
        # Create first BU
        bt1 = bt_factory(
            bucode='UNIQUE',
            parent=parent_bt,
            identifier=test_identifier_client
        )
        
        # Try to create duplicate - should raise IntegrityError
        with pytest.raises(IntegrityError):
            bt_factory(
                bucode='UNIQUE',
                parent=parent_bt,
                identifier=test_identifier_client
            )
    
    
    def test_bt_boolean_flags(self, bt_factory):
        """Test Bt boolean flag fields"""
        bt = bt_factory(
            enable=True,
            iswarehouse=True,
            gpsenable=True,
            enablesleepingguard=True,
            skipsiteaudit=True,
            deviceevent=True,
            isvendor=True,
            isserviceprovider=True
        )
        
        assert bt.enable is True
        assert bt.iswarehouse is True
        assert bt.gpsenable is True
        assert bt.enablesleepingguard is True
        assert bt.skipsiteaudit is True
        assert bt.deviceevent is True
        assert bt.isvendor is True
        assert bt.isserviceprovider is True
    
    
    def test_bt_site_includes_array_field(self, bt_factory):
        """Test Bt siincludes array field"""
        site_includes = ['CCTV', 'ACCESS_CONTROL', 'FIRE_SAFETY']
        bt = bt_factory(
            siincludes=site_includes
        )
        
        assert bt.siincludes == site_includes
        assert 'CCTV' in bt.siincludes
        assert len(bt.siincludes) == 3
    
    
    def test_bt_permissible_distance(self, bt_factory):
        """Test Bt permissible distance field"""
        bt = bt_factory(
            pdist=150.5
        )
        
        assert bt.pdist == 150.5
        
        # Test default value
        default_bt = bt_factory()
        assert default_bt.pdist == 0.0
    
    
    def test_bt_solid_field(self, bt_factory):
        """Test Bt solid (Sol ID) field"""
        bt = bt_factory(
            solid='SOL12345'
        )
        
        assert bt.solid == 'SOL12345'
    
    
    def test_bt_relationships(self, bt_factory, test_identifier_client, test_bu_type, test_people_onboarding):
        """Test Bt foreign key relationships"""
        bt = bt_factory(
            identifier=test_identifier_client,
            butype=test_bu_type,
            siteincharge=test_people_onboarding
        )
        
        # Test forward relationships
        assert bt.identifier == test_identifier_client
        assert bt.butype == test_bu_type
        assert bt.siteincharge == test_people_onboarding
        
        # Test reverse relationships
        assert bt in test_identifier_client.bu_idfs.all()
        assert bt in test_bu_type.bu_butypes.all()
        assert bt in test_people_onboarding.siteincharge.all()
    
    
    def test_bt_butree_field(self, bt_factory):
        """Test Bt butree (Bu Path) field"""
        bt = bt_factory(
            butree='Root/Client/Region/Site'
        )
        
        assert bt.butree == 'Root/Client/Region/Site'
    
    
    def test_bt_bulk_operations(self, bt_factory):
        """Test bulk operations on Bt"""
        # Create multiple BU records
        bus = []
        for i in range(10):
            bt = bt_factory(
                bucode=f'BULK_{i}',
                buname=f'Bulk BU {i}',
                enable=True if i % 2 == 0 else False
            )
            bus.append(bt)
        
        # Test bulk filtering
        enabled_bus = Bt.objects.filter(
            bucode__startswith='BULK_',
            enable=True
        )
        disabled_bus = Bt.objects.filter(
            bucode__startswith='BULK_',
            enable=False
        )
        
        assert enabled_bus.count() == 5
        assert disabled_bus.count() == 5
        
        # Test bulk update
        Bt.objects.filter(
            bucode__startswith='BULK_'
        ).update(gpsenable=True)
        
        # Verify bulk update
        updated_bus = Bt.objects.filter(
            bucode__startswith='BULK_',
            gpsenable=True
        )
        assert updated_bus.count() == 10
    
    
    def test_bt_filtering_queries(self, bt_factory, test_identifier_client, test_identifier_site):
        """Test various filtering queries on Bt"""
        # Create BUs with different identifiers
        client_bt = bt_factory(
            bucode='CLIENT001',
            identifier=test_identifier_client
        )
        site_bt = bt_factory(
            bucode='SITE001',
            identifier=test_identifier_site
        )
        
        # Test identifier-based filtering
        clients = Bt.objects.filter(identifier__tacode='CLIENT')
        sites = Bt.objects.filter(identifier__tacode='SITE')
        
        assert client_bt in clients
        assert site_bt in sites
        assert client_bt not in sites
        assert site_bt not in clients
    
    
    def test_bt_warehouse_and_vendor_flags(self, bt_factory):
        """Test Bt warehouse and vendor specific flags"""
        warehouse_bt = bt_factory(
            bucode='WAREHOUSE001',
            buname='Test Warehouse',
            iswarehouse=True,
            isvendor=False,
            isserviceprovider=False
        )
        
        vendor_bt = bt_factory(
            bucode='VENDOR001',
            buname='Test Vendor',
            iswarehouse=False,
            isvendor=True,
            isserviceprovider=False
        )
        
        service_provider_bt = bt_factory(
            bucode='SERVICE001',
            buname='Test Service Provider',
            iswarehouse=False,
            isvendor=False,
            isserviceprovider=True
        )
        
        assert warehouse_bt.iswarehouse is True
        assert vendor_bt.isvendor is True
        assert service_provider_bt.isserviceprovider is True
        
        # Test filtering by type
        warehouses = Bt.objects.filter(iswarehouse=True)
        vendors = Bt.objects.filter(isvendor=True)
        service_providers = Bt.objects.filter(isserviceprovider=True)
        
        assert warehouse_bt in warehouses
        assert vendor_bt in vendors
        assert service_provider_bt in service_providers
    
    
    def test_bt_deep_hierarchy(self, bt_factory):
        """Test Bt deep hierarchy relationships"""
        # Create a 4-level hierarchy: Root -> Client -> Region -> Site
        root_bt = bt_factory(
            bucode='ROOT',
            buname='Root Organization'
        )
        
        client_bt = bt_factory(
            bucode='CLIENT',
            buname='Client Organization',
            parent=root_bt
        )
        
        region_bt = bt_factory(
            bucode='REGION',
            buname='Regional Office',
            parent=client_bt
        )
        
        site_bt = bt_factory(
            bucode='SITE',
            buname='Site Location',
            parent=region_bt
        )
        
        # Test hierarchy relationships
        assert site_bt.parent == region_bt
        assert region_bt.parent == client_bt
        assert client_bt.parent == root_bt
        assert root_bt.parent is None
        
        # Test reverse relationships
        assert site_bt in region_bt.children.all()
        assert region_bt in client_bt.children.all()
        assert client_bt in root_bt.children.all()
    
    
    def test_bt_gps_and_distance_combined(self, bt_factory, gps_coordinates):
        """Test Bt GPS location with permissible distance"""
        bt = bt_factory(
            gpslocation=gps_coordinates['bangalore_office'],
            pdist=200.0,
            gpsenable=True
        )
        
        assert bt.gpslocation is not None
        assert bt.pdist == 200.0
        assert bt.gpsenable is True
        
        # Test coordinate values
        assert bt.gpslocation.x == 77.5946
        assert bt.gpslocation.y == 12.9716
    
    
    def test_bt_sleeping_guard_and_audit_flags(self, bt_factory):
        """Test Bt sleeping guard and audit related flags"""
        bt = bt_factory(
            enablesleepingguard=True,
            skipsiteaudit=True
        )
        
        assert bt.enablesleepingguard is True
        assert bt.skipsiteaudit is True
        
        # Test default values
        default_bt = bt_factory()
        assert default_bt.enablesleepingguard is False
        assert default_bt.skipsiteaudit is False
    
    
    def test_bt_tenant_aware_functionality(self, bt_factory):
        """Test Bt tenant-aware model functionality"""
        bt = bt_factory(
            bucode='TENANT_TEST',
            buname='Tenant Test BU'
        )
        
        # Bt inherits from TenantAwareModel, so it should have tenant-related fields
        assert hasattr(bt, 'tenant_id')
        assert bt.enable is True  # Default enable value
    
    
    def test_bt_performance_queries(self, bt_factory):
        """Test performance-oriented queries on Bt"""
        # Create multiple BU records for performance testing
        bus = []
        for i in range(100):
            bt = bt_factory(
                bucode=f'PERF_{i:03d}',
                buname=f'Performance Test BU {i}',
                enable=True if i % 3 == 0 else False
            )
            bus.append(bt)
        
        # Test count queries
        total_count = Bt.objects.filter(
            bucode__startswith='PERF_'
        ).count()
        assert total_count == 100
        
        # Test enabled/disabled filtering
        enabled_count = Bt.objects.filter(
            bucode__startswith='PERF_',
            enable=True
        ).count()
        disabled_count = Bt.objects.filter(
            bucode__startswith='PERF_',
            enable=False
        ).count()
        
        assert enabled_count == 34  # Every 3rd record (0, 3, 6, ... 99)
        assert disabled_count == 66
        assert enabled_count + disabled_count == 100