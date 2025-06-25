"""
Tests for Wom (Work Order Management) model
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from django.utils import timezone
from datetime import datetime, timedelta
from apps.work_order_management.models import Wom


@pytest.mark.django_db
class TestWomModel:
    """Test suite for Wom model"""
    
    def test_wom_creation_basic(self, wom_factory):
        """Test creating a basic Wom instance"""
        wom = wom_factory()
        
        assert wom.uuid is not None
        assert wom.description is not None
        assert wom.workstatus == Wom.Workstatus.ASSIGNED
        assert wom.workpermit == Wom.WorkPermitStatus.NOTNEED
        assert wom.priority == Wom.Priority.MEDIUM
        assert wom.verifiers_status == Wom.WorkPermitVerifierStatus.PENDING
        assert wom.alerts is False
        assert wom.ismailsent is False
        assert wom.isdenied is False
        assert wom.attachmentcount == 0
    
    
    def test_wom_work_status_choices(self, wom_factory, work_order_statuses):
        """Test Wom work status choices"""
        for status in work_order_statuses:
            wom = wom_factory(
                workstatus=status,
                description=f'Work Order with {status} status'
            )
            assert wom.workstatus == status
    
    
    def test_wom_work_permit_status_choices(self, wom_factory, work_permit_statuses):
        """Test Wom work permit status choices"""
        for permit_status in work_permit_statuses:
            wom = wom_factory(
                workpermit=permit_status,
                description=f'Work Order with {permit_status} permit'
            )
            assert wom.workpermit == permit_status
    
    
    def test_wom_priority_choices(self, wom_factory, priority_levels):
        """Test Wom priority choices"""
        for priority in priority_levels:
            wom = wom_factory(
                priority=priority,
                description=f'Work Order with {priority} priority'
            )
            assert wom.priority == priority
    
    
    def test_wom_identifier_choices(self, wom_factory):
        """Test Wom identifier choices"""
        identifiers = [
            Wom.Identifier.WO,
            Wom.Identifier.WP,
            Wom.Identifier.SLA
        ]
        
        for identifier in identifiers:
            wom = wom_factory(
                identifier=identifier,
                description=f'Item with {identifier} identifier'
            )
            assert wom.identifier == identifier
    
    
    def test_wom_time_fields(self, wom_factory):
        """Test Wom time-related fields"""
        plan_time = timezone.now() + timedelta(hours=2)
        expiry_time = timezone.now() + timedelta(hours=10)
        start_time = timezone.now() + timedelta(hours=1)
        end_time = timezone.now() + timedelta(hours=9)
        
        wom = wom_factory(
            plandatetime=plan_time,
            expirydatetime=expiry_time,
            starttime=start_time,
            endtime=end_time
        )
        
        assert wom.plandatetime == plan_time
        assert wom.expirydatetime == expiry_time
        assert wom.starttime == start_time
        assert wom.endtime == end_time
    
    
    def test_wom_gps_location_field(self, wom_factory, gps_coordinates_wom):
        """Test Wom GPS location field"""
        wom = wom_factory(
            gpslocation=gps_coordinates_wom['office_location']
        )
        
        assert wom.gpslocation is not None
        assert wom.gpslocation.x == 77.5946
        assert wom.gpslocation.y == 12.9716
    
    
    def test_wom_relationships(self, wom_factory, test_asset, test_location, test_questionset, test_vendor, test_client_wom, test_bu_wom, test_ticket_category):
        """Test Wom foreign key relationships"""
        wom = wom_factory(
            asset=test_asset,
            location=test_location,
            qset=test_questionset,
            vendor=test_vendor,
            client=test_client_wom,
            bu=test_bu_wom,
            ticketcategory=test_ticket_category
        )
        
        # Test forward relationships
        assert wom.asset == test_asset
        assert wom.location == test_location
        assert wom.qset == test_questionset
        assert wom.vendor == test_vendor
        assert wom.client == test_client_wom
        assert wom.bu == test_bu_wom
        assert wom.ticketcategory == test_ticket_category
        
        # Test reverse relationships
        assert wom in test_asset.wo_assets.all()
        assert wom in test_client_wom.wo_clients.all()
        assert wom in test_bu_wom.wo_bus.all()
    
    
    def test_wom_array_fields(self, wom_factory):
        """Test Wom array fields"""
        approvers = ['APPROVER001', 'APPROVER002']
        verifiers = ['VERIFIER001', 'VERIFIER002']
        categories = ['ELECTRICAL', 'MAINTENANCE', 'URGENT']
        
        wom = wom_factory(
            approvers=approvers,
            verifiers=verifiers,
            categories=categories
        )
        
        assert wom.approvers == approvers
        assert wom.verifiers == verifiers
        assert wom.categories == categories
        assert len(wom.approvers) == 2
        assert len(wom.verifiers) == 2
        assert len(wom.categories) == 3
    
    
    def test_wom_json_fields(self, wom_factory, sample_other_data, sample_wo_history):
        """Test Wom JSON fields"""
        wom = wom_factory(
            other_data=sample_other_data,
            wo_history=sample_wo_history
        )
        
        assert wom.other_data is not None
        assert wom.other_data['token'] == 'abc123token'
        # Note: wp_seqno is automatically set by signal, so we test the actual value
        assert wom.other_data['wp_seqno'] == 1  # Signal sets this to 1 for new records
        assert wom.other_data['overall_score'] == 85.5
        
        assert wom.wo_history is not None
        assert len(wom.wo_history['wo_history']) == 2
        assert len(wom.wo_history['wp_history']) == 1
    
    
    def test_wom_geojson_field(self, wom_factory):
        """Test Wom geojson field"""
        geojson_data = {
            'gpslocation': 'Point(77.5946 12.9716)',
            'accuracy': 95.5,
            'timestamp': '2024-01-01T10:00:00Z'
        }
        
        wom = wom_factory(
            geojson=geojson_data
        )
        
        assert wom.geojson is not None
        assert wom.geojson['gpslocation'] == 'Point(77.5946 12.9716)'
        assert wom.geojson['accuracy'] == 95.5
    
    
    def test_wom_hierarchy_parent_child(self, wom_factory):
        """Test Wom parent-child hierarchy"""
        parent_wom = wom_factory(
            description='Parent Work Order',
            identifier=Wom.Identifier.WP
        )
        
        child_wom = wom_factory(
            description='Child Work Order Task',
            parent=parent_wom,
            identifier=Wom.Identifier.WO
        )
        
        assert child_wom.parent == parent_wom
        assert child_wom in parent_wom.wom_set.all()
        assert parent_wom.parent is None
    
    
    def test_wom_sequence_number(self, wom_factory):
        """Test Wom sequence number field"""
        wom1 = wom_factory(seqno=1)
        wom2 = wom_factory(seqno=2)
        wom3 = wom_factory(seqno=3)
        
        assert wom1.seqno == 1
        assert wom2.seqno == 2
        assert wom3.seqno == 3
    
    
    def test_wom_boolean_flags(self, wom_factory):
        """Test Wom boolean flag fields"""
        wom = wom_factory(
            alerts=True,
            ismailsent=True,
            isdenied=True
        )
        
        assert wom.alerts is True
        assert wom.ismailsent is True
        assert wom.isdenied is True
        
        # Test default values
        default_wom = wom_factory()
        assert default_wom.alerts is False
        assert default_wom.ismailsent is False
        assert default_wom.isdenied is False
    
    
    def test_wom_attachment_count(self, wom_factory):
        """Test Wom attachment count field"""
        wom = wom_factory(
            attachmentcount=5
        )
        
        assert wom.attachmentcount == 5
        
        # Test default value
        default_wom = wom_factory()
        assert default_wom.attachmentcount == 0
    
    
    def test_wom_unique_constraint(self, wom_factory, test_questionset, test_client_wom):
        """Test Wom unique constraint on qset, client, id"""
        # Create first work order
        wom1 = wom_factory(
            qset=test_questionset,
            client=test_client_wom
        )
        
        # The unique constraint is on qset, client, id - since id is auto-generated,
        # this should not cause conflicts for different instances
        wom2 = wom_factory(
            qset=test_questionset,
            client=test_client_wom
        )
        
        # Both should be created successfully with different IDs
        assert wom1.id != wom2.id
        assert wom1.qset == wom2.qset
        assert wom1.client == wom2.client
    
    
    def test_wom_work_order_workflow(self, wom_factory):
        """Test complete work order workflow"""
        # Create initial work order
        wom = wom_factory(
            description='Fix broken equipment',
            workstatus=Wom.Workstatus.ASSIGNED,
            priority=Wom.Priority.HIGH,
            workpermit=Wom.WorkPermitStatus.NOTNEED
        )
        
        # Update to in progress
        wom.workstatus = Wom.Workstatus.INPROGRESS
        wom.starttime = timezone.now()
        wom.save()
        
        assert wom.workstatus == Wom.Workstatus.INPROGRESS
        assert wom.starttime is not None
        
        # Complete the work order
        wom.workstatus = Wom.Workstatus.COMPLETED
        wom.endtime = timezone.now()
        wom.save()
        
        assert wom.workstatus == Wom.Workstatus.COMPLETED
        assert wom.endtime is not None
        
        # Close the work order
        wom.workstatus = Wom.Workstatus.CLOSED
        wom.save()
        
        assert wom.workstatus == Wom.Workstatus.CLOSED
    
    
    def test_wom_work_permit_workflow(self, wom_factory):
        """Test work permit workflow"""
        # Create work permit
        wp = wom_factory(
            description='High voltage electrical work',
            identifier=Wom.Identifier.WP,
            workpermit=Wom.WorkPermitStatus.PENDING,
            verifiers_status=Wom.WorkPermitVerifierStatus.PENDING,
            priority=Wom.Priority.HIGH
        )
        
        # Verify work permit
        wp.verifiers_status = Wom.WorkPermitVerifierStatus.APPROVED
        wp.save()
        
        assert wp.verifiers_status == Wom.WorkPermitVerifierStatus.APPROVED
        
        # Approve work permit
        wp.workpermit = Wom.WorkPermitStatus.APPROVED
        wp.save()
        
        assert wp.workpermit == Wom.WorkPermitStatus.APPROVED
        
        # Start work
        wp.workstatus = Wom.Workstatus.INPROGRESS
        wp.starttime = timezone.now()
        wp.save()
        
        assert wp.workstatus == Wom.Workstatus.INPROGRESS
        assert wp.identifier == Wom.Identifier.WP
    
    
    def test_wom_sla_workflow(self, wom_factory):
        """Test SLA workflow"""
        sla = wom_factory(
            description='Monthly service level assessment',
            identifier=Wom.Identifier.SLA,
            priority=Wom.Priority.MEDIUM,
            other_data={
                'overall_score': 0,
                'uptime_score': 0,
                'section_weightage': 0.8,
                'remarks': ''
            }
        )
        
        # Update SLA scores
        sla.other_data['overall_score'] = 92.5
        sla.other_data['uptime_score'] = 98.0
        sla.other_data['remarks'] = 'Excellent service quality'
        sla.save()
        
        assert sla.identifier == Wom.Identifier.SLA
        assert sla.other_data['overall_score'] == 92.5
        assert sla.other_data['uptime_score'] == 98.0
        assert sla.other_data['remarks'] == 'Excellent service quality'
    
    
    def test_wom_add_history_method(self, wom_factory):
        """Test Wom add_history method"""
        wom = wom_factory(
            description='Test work order for history'
        )
        
        # Initial history should be empty
        initial_history_count = len(wom.wo_history.get('wo_history', []))
        
        # Add history entry
        wom.add_history()
        
        # Reload from database
        wom.refresh_from_db()
        
        # Check that history was added
        final_history_count = len(wom.wo_history.get('wo_history', []))
        assert final_history_count == initial_history_count + 1
        
        # Check history content
        latest_history = wom.wo_history['wo_history'][-1]
        assert latest_history['description'] == wom.description
        assert 'wo_history' not in latest_history  # Should be excluded
        assert 'workpermit' not in latest_history  # Should be excluded
        assert 'gpslocation' not in latest_history  # Should be excluded
    
    
    def test_wom_bulk_operations(self, wom_factory, test_client_wom, test_bu_wom):
        """Test bulk operations on Wom"""
        # Create multiple work orders
        woms = []
        for i in range(15):
            wom = wom_factory(
                description=f'Bulk Work Order {i}',
                workstatus=Wom.Workstatus.ASSIGNED if i % 2 == 0 else Wom.Workstatus.COMPLETED,
                priority=Wom.Priority.HIGH if i % 3 == 0 else Wom.Priority.MEDIUM,
                client=test_client_wom,
                bu=test_bu_wom
            )
            woms.append(wom)
        
        # Test bulk filtering
        assigned_woms = Wom.objects.filter(
            description__startswith='Bulk Work Order',
            workstatus=Wom.Workstatus.ASSIGNED
        )
        completed_woms = Wom.objects.filter(
            description__startswith='Bulk Work Order',
            workstatus=Wom.Workstatus.COMPLETED
        )
        
        assert assigned_woms.count() == 8  # 0,2,4,6,8,10,12,14
        assert completed_woms.count() == 7  # 1,3,5,7,9,11,13
        
        # Test bulk update
        Wom.objects.filter(
            description__startswith='Bulk Work Order'
        ).update(ismailsent=True)
        
        # Verify bulk update
        updated_woms = Wom.objects.filter(
            description__startswith='Bulk Work Order',
            ismailsent=True
        )
        assert updated_woms.count() == 15
    
    
    def test_wom_filtering_by_client_and_bu(self, wom_factory, test_client_wom, test_bu_wom):
        """Test Wom filtering by client and BU"""
        # Create another client and BU for comparison
        other_client = test_client_wom.__class__.objects.create(
            bucode='OTHER_WOM_CLIENT',
            buname='Other WOM Client',
            enable=True
        )
        
        other_bu = test_bu_wom.__class__.objects.create(
            bucode='OTHER_WOM_BU',
            buname='Other WOM BU',
            enable=True
        )
        
        # Create work orders for different clients and BUs
        wom1 = wom_factory(
            description='Client1 BU1 Work Order',
            client=test_client_wom,
            bu=test_bu_wom
        )
        
        wom2 = wom_factory(
            description='Client1 BU2 Work Order',
            client=test_client_wom,
            bu=other_bu
        )
        
        wom3 = wom_factory(
            description='Client2 BU1 Work Order',
            client=other_client,
            bu=test_bu_wom
        )
        
        wom4 = wom_factory(
            description='Client2 BU2 Work Order',
            client=other_client,
            bu=other_bu
        )
        
        # Test filtering by client
        client1_woms = Wom.objects.filter(client=test_client_wom)
        client2_woms = Wom.objects.filter(client=other_client)
        
        assert wom1 in client1_woms
        assert wom2 in client1_woms
        assert wom3 not in client1_woms
        assert wom4 not in client1_woms
        
        assert wom3 in client2_woms
        assert wom4 in client2_woms
        assert wom1 not in client2_woms
        assert wom2 not in client2_woms
    
    
    def test_wom_performance_queries(self, wom_factory, test_client_wom, test_bu_wom):
        """Test performance-oriented queries on Wom"""
        # Create many work order records for performance testing
        woms = []
        for i in range(100):
            wom = wom_factory(
                description=f'Performance Work Order {i:03d}',
                workstatus=Wom.Workstatus.ASSIGNED if i % 4 == 0 else Wom.Workstatus.COMPLETED,
                priority=Wom.Priority.HIGH if i % 5 == 0 else Wom.Priority.MEDIUM,
                workpermit=Wom.WorkPermitStatus.NOTNEED if i % 3 == 0 else Wom.WorkPermitStatus.PENDING,
                client=test_client_wom,
                bu=test_bu_wom
            )
            woms.append(wom)
        
        # Test count queries
        total_count = Wom.objects.filter(
            description__startswith='Performance Work Order'
        ).count()
        assert total_count == 100
        
        # Test status-based filtering
        assigned_count = Wom.objects.filter(
            description__startswith='Performance Work Order',
            workstatus=Wom.Workstatus.ASSIGNED
        ).count()
        completed_count = Wom.objects.filter(
            description__startswith='Performance Work Order',
            workstatus=Wom.Workstatus.COMPLETED
        ).count()
        
        assert assigned_count == 25  # Every 4th record
        assert completed_count == 75
        assert assigned_count + completed_count == 100
        
        # Test priority filtering
        high_priority_count = Wom.objects.filter(
            description__startswith='Performance Work Order',
            priority=Wom.Priority.HIGH
        ).count()
        
        assert high_priority_count == 20  # Every 5th record
    
    
    def test_wom_tenant_aware_functionality(self, wom_factory, test_client_wom, test_bu_wom):
        """Test Wom tenant-aware model functionality"""
        wom = wom_factory(
            description='Tenant Test Work Order',
            client=test_client_wom,
            bu=test_bu_wom
        )
        
        # Wom inherits from TenantAwareModel
        assert hasattr(wom, 'tenant_id')
        assert wom.client == test_client_wom
        assert wom.bu == test_bu_wom
    
    
    def test_wom_complex_workflow_scenarios(self, wom_factory):
        """Test complex workflow scenarios"""
        # Scenario 1: Emergency work order
        emergency_wom = wom_factory(
            description='Emergency power outage repair',
            priority=Wom.Priority.HIGH,
            workstatus=Wom.Workstatus.ASSIGNED,
            workpermit=Wom.WorkPermitStatus.NOTNEED,
            alerts=True,
            categories=['EMERGENCY', 'ELECTRICAL', 'CRITICAL']
        )
        
        assert emergency_wom.priority == Wom.Priority.HIGH
        assert emergency_wom.alerts is True
        assert 'EMERGENCY' in emergency_wom.categories
        
        # Scenario 2: Planned maintenance with permit
        maintenance_wom = wom_factory(
            description='Scheduled HVAC maintenance',
            priority=Wom.Priority.MEDIUM,
            workstatus=Wom.Workstatus.ASSIGNED,
            workpermit=Wom.WorkPermitStatus.PENDING,
            verifiers_status=Wom.WorkPermitVerifierStatus.PENDING,
            categories=['MAINTENANCE', 'HVAC', 'SCHEDULED'],
            plandatetime=timezone.now() + timedelta(days=7)
        )
        
        assert maintenance_wom.workpermit == Wom.WorkPermitStatus.PENDING
        assert maintenance_wom.verifiers_status == Wom.WorkPermitVerifierStatus.PENDING
        assert 'MAINTENANCE' in maintenance_wom.categories
        
        # Scenario 3: Cancelled work order
        cancelled_wom = wom_factory(
            description='Cancelled due to weather',
            workstatus=Wom.Workstatus.CANCELLED,
            priority=Wom.Priority.LOW,
            isdenied=True
        )
        
        assert cancelled_wom.workstatus == Wom.Workstatus.CANCELLED
        assert cancelled_wom.isdenied is True