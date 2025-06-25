"""
Tests for TypeAssist model
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.onboarding.models import TypeAssist


@pytest.mark.django_db
class TestTypeAssistModel:
    """Test suite for TypeAssist model"""
    
    def test_typeassist_creation_basic(self, typeassist_factory):
        """Test creating a basic TypeAssist instance"""
        ta = typeassist_factory()
        
        assert ta.id is not None
        assert ta.tacode is not None
        assert ta.taname is not None
        assert ta.enable is True
        assert ta.tatype is None  # Default parent
    
    
    def test_typeassist_str_representation(self, typeassist_factory):
        """Test TypeAssist string representation"""
        ta = typeassist_factory(
            tacode='TESTCODE',
            taname='Test Type Assist'
        )
        
        assert str(ta) == 'Test Type Assist (TESTCODE)'
    
    
    def test_typeassist_hierarchy_parent_child(self, typeassist_factory):
        """Test TypeAssist parent-child hierarchy"""
        parent_ta = typeassist_factory(
            tacode='PARENT_TYPE',
            taname='Parent Type'
        )
        
        child_ta = typeassist_factory(
            tacode='CHILD_TYPE',
            taname='Child Type',
            tatype=parent_ta
        )
        
        assert child_ta.tatype == parent_ta
        assert child_ta in parent_ta.children.all()
        assert parent_ta.tatype is None
    
    
    def test_typeassist_unique_constraint(self, typeassist_factory, test_client_bt):
        """Test TypeAssist unique constraint on tacode, tatype, client"""
        parent_ta = typeassist_factory(tacode='PARENT')
        
        # Create first TypeAssist
        ta1 = typeassist_factory(
            tacode='UNIQUE',
            tatype=parent_ta,
            client=test_client_bt
        )
        
        # Try to create duplicate - should raise IntegrityError
        with pytest.raises(IntegrityError):
            typeassist_factory(
                tacode='UNIQUE',
                tatype=parent_ta,
                client=test_client_bt
            )
    
    
    def test_typeassist_relationships(self, typeassist_factory, test_client_bt, test_bu_bt):
        """Test TypeAssist foreign key relationships"""
        parent_ta = typeassist_factory(tacode='PARENT')
        
        ta = typeassist_factory(
            tacode='CHILD',
            taname='Child TypeAssist',
            tatype=parent_ta,
            client=test_client_bt,
            bu=test_bu_bt
        )
        
        # Test forward relationships
        assert ta.tatype == parent_ta
        assert ta.client == test_client_bt
        assert ta.bu == test_bu_bt
        
        # Test reverse relationships
        assert ta in parent_ta.children.all()
        assert ta in test_client_bt.ta_clients.all()
        assert ta in test_bu_bt.ta_bus.all()
    
    
    def test_typeassist_get_all_children(self, typeassist_factory):
        """Test TypeAssist get_all_children method"""
        # Create hierarchy: root -> level1 -> level2
        root_ta = typeassist_factory(
            tacode='ROOT',
            taname='Root Type'
        )
        
        level1_ta = typeassist_factory(
            tacode='LEVEL1',
            taname='Level 1 Type',
            tatype=root_ta
        )
        
        level2_ta = typeassist_factory(
            tacode='LEVEL2',
            taname='Level 2 Type',
            tatype=level1_ta
        )
        
        # Test get_all_children from root
        root_children = root_ta.get_all_children()
        assert root_ta in root_children
        assert level1_ta in root_children
        assert level2_ta in root_children
        assert len(root_children) == 3
        
        # Test get_all_children from level1
        level1_children = level1_ta.get_all_children()
        assert level1_ta in level1_children
        assert level2_ta in level1_children
        assert root_ta not in level1_children
        assert len(level1_children) == 2
    
    
    def test_typeassist_get_all_parents(self, typeassist_factory):
        """Test TypeAssist get_all_parents method"""
        # Create hierarchy: root -> level1 -> level2
        root_ta = typeassist_factory(
            tacode='ROOT',
            taname='Root Type'
        )
        
        level1_ta = typeassist_factory(
            tacode='LEVEL1',
            taname='Level 1 Type',
            tatype=root_ta
        )
        
        level2_ta = typeassist_factory(
            tacode='LEVEL2',
            taname='Level 2 Type',
            tatype=level1_ta
        )
        
        # Test get_all_parents from level2
        level2_parents = level2_ta.get_all_parents()
        assert level2_ta in level2_parents
        assert level1_ta in level2_parents
        assert root_ta in level2_parents
        assert len(level2_parents) == 3
        
        # Test get_all_parents from root
        root_parents = root_ta.get_all_parents()
        assert root_ta in root_parents
        assert len(root_parents) == 1
    
    
    def test_typeassist_circular_reference_validation(self, typeassist_factory):
        """Test TypeAssist circular reference validation"""
        ta1 = typeassist_factory(
            tacode='TYPE1',
            taname='Type 1'
        )
        
        ta2 = typeassist_factory(
            tacode='TYPE2',
            taname='Type 2',
            tatype=ta1
        )
        
        # Try to make ta1 a child of ta2 (circular reference)
        ta1.tatype = ta2
        
        with pytest.raises(ValidationError):
            ta1.clean()
    
    
    def test_typeassist_common_types(self, typeassist_factory):
        """Test creating common TypeAssist types"""
        # Test identifier types
        client_type = typeassist_factory(
            tacode='CLIENT',
            taname='Client'
        )
        
        site_type = typeassist_factory(
            tacode='SITE',
            taname='Site'
        )
        
        # Test designation types
        security_guard = typeassist_factory(
            tacode='SECURITY_GUARD',
            taname='Security Guard'
        )
        
        supervisor = typeassist_factory(
            tacode='SUPERVISOR',
            taname='Supervisor'
        )
        
        # Test event types
        checkin_type = typeassist_factory(
            tacode='CHECKIN',
            taname='Check In'
        )
        
        checkout_type = typeassist_factory(
            tacode='CHECKOUT',
            taname='Check Out'
        )
        
        # Verify creation
        assert client_type.tacode == 'CLIENT'
        assert site_type.tacode == 'SITE'
        assert security_guard.tacode == 'SECURITY_GUARD'
        assert supervisor.tacode == 'SUPERVISOR'
        assert checkin_type.tacode == 'CHECKIN'
        assert checkout_type.tacode == 'CHECKOUT'
    
    
    def test_typeassist_enable_disable_functionality(self, typeassist_factory):
        """Test TypeAssist enable/disable functionality"""
        ta_enabled = typeassist_factory(
            tacode='ENABLED',
            taname='Enabled Type',
            enable=True
        )
        
        ta_disabled = typeassist_factory(
            tacode='DISABLED',
            taname='Disabled Type',
            enable=False
        )
        
        assert ta_enabled.enable is True
        assert ta_disabled.enable is False
        
        # Test filtering by enabled status
        enabled_types = TypeAssist.objects.filter(enable=True)
        disabled_types = TypeAssist.objects.filter(enable=False)
        
        assert ta_enabled in enabled_types
        assert ta_disabled in disabled_types
        assert ta_enabled not in disabled_types
        assert ta_disabled not in enabled_types
    
    
    def test_typeassist_tenant_aware_functionality(self, typeassist_factory, test_client_bt):
        """Test TypeAssist tenant-aware model functionality"""
        ta = typeassist_factory(
            tacode='TENANT_TEST',
            taname='Tenant Test Type',
            client=test_client_bt
        )
        
        # TypeAssist inherits from TenantAwareModel
        assert hasattr(ta, 'tenant_id')
        assert ta.client == test_client_bt
    
    
    def test_typeassist_bulk_operations(self, typeassist_factory):
        """Test bulk operations on TypeAssist"""
        # Create multiple TypeAssist records
        type_assists = []
        for i in range(20):
            ta = typeassist_factory(
                tacode=f'BULK_{i:02d}',
                taname=f'Bulk Type {i}',
                enable=True if i % 2 == 0 else False
            )
            type_assists.append(ta)
        
        # Test bulk filtering
        bulk_enabled = TypeAssist.objects.filter(
            tacode__startswith='BULK_',
            enable=True
        )
        bulk_disabled = TypeAssist.objects.filter(
            tacode__startswith='BULK_',
            enable=False
        )
        
        assert bulk_enabled.count() == 10
        assert bulk_disabled.count() == 10
        
        # Test bulk update
        TypeAssist.objects.filter(
            tacode__startswith='BULK_'
        ).update(taname='Updated Bulk Type')
        
        # Verify bulk update
        updated_types = TypeAssist.objects.filter(
            tacode__startswith='BULK_',
            taname='Updated Bulk Type'
        )
        assert updated_types.count() == 20
    
    
    def test_typeassist_hierarchy_categories(self, typeassist_factory):
        """Test TypeAssist hierarchy for different categories"""
        # Create main category types
        bv_identifier = typeassist_factory(
            tacode='BVIDENTIFIER',
            taname='Business View Identifier'
        )
        
        designation = typeassist_factory(
            tacode='DESIGNATION',
            taname='Designation'
        )
        
        # Create subcategories under BV Identifier
        client_id = typeassist_factory(
            tacode='CLIENT',
            taname='Client',
            tatype=bv_identifier
        )
        
        site_id = typeassist_factory(
            tacode='SITE',
            taname='Site',
            tatype=bv_identifier
        )
        
        # Create subcategories under Designation
        guard = typeassist_factory(
            tacode='GUARD',
            taname='Security Guard',
            tatype=designation
        )
        
        supervisor = typeassist_factory(
            tacode='SUPERVISOR',
            taname='Supervisor',
            tatype=designation
        )
        
        # Test hierarchy relationships
        assert client_id.tatype == bv_identifier
        assert site_id.tatype == bv_identifier
        assert guard.tatype == designation
        assert supervisor.tatype == designation
        
        # Test reverse relationships
        bv_children = bv_identifier.children.all()
        designation_children = designation.children.all()
        
        assert client_id in bv_children
        assert site_id in bv_children
        assert guard in designation_children
        assert supervisor in designation_children
    
    
    def test_typeassist_deep_hierarchy(self, typeassist_factory):
        """Test TypeAssist deep hierarchy (3+ levels)"""
        # Level 0: Main category
        main_category = typeassist_factory(
            tacode='MAIN',
            taname='Main Category'
        )
        
        # Level 1: Sub category
        sub_category = typeassist_factory(
            tacode='SUB',
            taname='Sub Category',
            tatype=main_category
        )
        
        # Level 2: Sub-sub category
        sub_sub_category = typeassist_factory(
            tacode='SUBSUB',
            taname='Sub-Sub Category',
            tatype=sub_category
        )
        
        # Level 3: Specific type
        specific_type = typeassist_factory(
            tacode='SPECIFIC',
            taname='Specific Type',
            tatype=sub_sub_category
        )
        
        # Test deep hierarchy
        assert specific_type.tatype == sub_sub_category
        assert sub_sub_category.tatype == sub_category
        assert sub_category.tatype == main_category
        assert main_category.tatype is None
        
        # Test get_all_parents from deepest level
        all_parents = specific_type.get_all_parents()
        assert len(all_parents) == 4
        assert specific_type in all_parents
        assert sub_sub_category in all_parents
        assert sub_category in all_parents
        assert main_category in all_parents
    
    
    def test_typeassist_filtering_by_client_and_bu(self, typeassist_factory, test_client_bt, test_bu_bt):
        """Test TypeAssist filtering by client and BU"""
        # Create types for specific client and BU
        client_specific = typeassist_factory(
            tacode='CLIENT_SPECIFIC',
            taname='Client Specific Type',
            client=test_client_bt
        )
        
        bu_specific = typeassist_factory(
            tacode='BU_SPECIFIC',
            taname='BU Specific Type',
            bu=test_bu_bt
        )
        
        both_specific = typeassist_factory(
            tacode='BOTH_SPECIFIC',
            taname='Client and BU Specific Type',
            client=test_client_bt,
            bu=test_bu_bt
        )
        
        global_type = typeassist_factory(
            tacode='GLOBAL',
            taname='Global Type'
        )
        
        # Test filtering by client
        client_types = TypeAssist.objects.filter(client=test_client_bt)
        assert client_specific in client_types
        assert both_specific in client_types
        assert bu_specific not in client_types
        assert global_type not in client_types
        
        # Test filtering by BU
        bu_types = TypeAssist.objects.filter(bu=test_bu_bt)
        assert bu_specific in bu_types
        assert both_specific in bu_types
        assert client_specific not in bu_types
        assert global_type not in bu_types
    
    
    def test_typeassist_performance_queries(self, typeassist_factory):
        """Test performance-oriented queries on TypeAssist"""
        # Create many TypeAssist records for performance testing
        categories = ['DESIGNATION', 'ASSET_TYPE', 'EVENT_TYPE', 'WORK_TYPE']
        
        type_assists = []
        for i in range(200):
            category = categories[i % len(categories)]
            ta = typeassist_factory(
                tacode=f'PERF_{category}_{i:03d}',
                taname=f'Performance {category} {i}',
                enable=True if i % 4 == 0 else False
            )
            type_assists.append(ta)
        
        # Test count queries
        total_count = TypeAssist.objects.filter(
            tacode__startswith='PERF_'
        ).count()
        assert total_count == 200
        
        # Test category-based filtering
        for category in categories:
            category_count = TypeAssist.objects.filter(
                tacode__startswith=f'PERF_{category}_'
            ).count()
            assert category_count == 50  # 200 / 4 categories
        
        # Test enabled/disabled filtering
        enabled_count = TypeAssist.objects.filter(
            tacode__startswith='PERF_',
            enable=True
        ).count()
        disabled_count = TypeAssist.objects.filter(
            tacode__startswith='PERF_',
            enable=False
        ).count()
        
        assert enabled_count == 50  # Every 4th record
        assert disabled_count == 150
        assert enabled_count + disabled_count == 200
    
    
    def test_typeassist_self_reference_prevention(self, typeassist_factory):
        """Test TypeAssist cannot reference itself as parent"""
        ta = typeassist_factory(
            tacode='SELF_REF',
            taname='Self Reference Test'
        )
        
        # Try to set itself as parent
        ta.tatype = ta
        
        with pytest.raises(ValidationError):
            ta.clean()