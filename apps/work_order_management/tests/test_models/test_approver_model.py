"""
Tests for Approver model
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.work_order_management.models import Approver


@pytest.mark.django_db
class TestApproverModel:
    """Test suite for Approver model"""
    
    def test_approver_creation_basic(self, approver_factory):
        """Test creating a basic Approver instance"""
        approver = approver_factory()
        
        assert approver.id is not None
        assert approver.people is not None
        assert approver.approverfor is not None
        assert approver.forallsites is True
        assert approver.identifier == Approver.Identifier.APPROVER
    
    
    def test_approver_identifier_choices(self, approver_factory):
        """Test Approver identifier choices"""
        # Test APPROVER identifier
        approver_role = approver_factory(
            identifier=Approver.Identifier.APPROVER,
            approverfor=['WORKORDER']
        )
        
        # Test VERIFIER identifier
        verifier_role = approver_factory(
            identifier=Approver.Identifier.VERIFIER,
            approverfor=['WORKPERMIT']
        )
        
        assert approver_role.identifier == Approver.Identifier.APPROVER
        assert verifier_role.identifier == Approver.Identifier.VERIFIER
    
    
    def test_approver_relationships(self, approver_factory, test_people_wom, test_client_wom, test_bu_wom):
        """Test Approver foreign key relationships"""
        approver = approver_factory(
            people=test_people_wom,
            client=test_client_wom,
            bu=test_bu_wom
        )
        
        # Test forward relationships
        assert approver.people == test_people_wom
        assert approver.client == test_client_wom
        assert approver.bu == test_bu_wom
        
        # Test reverse relationships
        assert approver in test_people_wom.approver_set.all()
        assert approver in test_client_wom.approver_clients.all()
    
    
    def test_approver_unique_constraint(self, approver_factory, test_people_wom):
        """Test Approver unique constraint on people, approverfor, sites"""
        approverfor_list = ['WORKORDER']
        sites_list = ['SITE001']
        
        # Create first approver
        approver1 = approver_factory(
            people=test_people_wom,
            approverfor=approverfor_list,
            sites=sites_list
        )
        
        # Try to create duplicate - should raise IntegrityError
        with pytest.raises(IntegrityError):
            approver_factory(
                people=test_people_wom,
                approverfor=approverfor_list,
                sites=sites_list
            )
    
    
    def test_approver_for_array_field(self, approver_factory):
        """Test Approver approverfor array field"""
        # Single approval responsibility
        single_approver = approver_factory(
            approverfor=['WORKORDER']
        )
        
        # Multiple approval responsibilities
        multi_approver = approver_factory(
            approverfor=['WORKORDER', 'WORKPERMIT', 'SLA_TEMPLATE']
        )
        
        assert single_approver.approverfor == ['WORKORDER']
        assert len(single_approver.approverfor) == 1
        
        assert 'WORKORDER' in multi_approver.approverfor
        assert 'WORKPERMIT' in multi_approver.approverfor
        assert 'SLA_TEMPLATE' in multi_approver.approverfor
        assert len(multi_approver.approverfor) == 3
    
    
    def test_approver_sites_array_field(self, approver_factory):
        """Test Approver sites array field"""
        # Site-specific approver
        site_specific = approver_factory(
            sites=['SITE001', 'SITE002'],
            forallsites=False
        )
        
        # All sites approver
        all_sites = approver_factory(
            sites=[],
            forallsites=True
        )
        
        assert site_specific.sites == ['SITE001', 'SITE002']
        assert len(site_specific.sites) == 2
        assert site_specific.forallsites is False
        
        assert all_sites.sites == []
        assert all_sites.forallsites is True
    
    
    def test_approver_for_all_sites_flag(self, approver_factory):
        """Test Approver forallsites functionality"""
        # Global approver
        global_approver = approver_factory(
            forallsites=True,
            sites=[]
        )
        
        # Site-specific approver
        site_approver = approver_factory(
            forallsites=False,
            sites=['SITE001', 'SITE002', 'SITE003']
        )
        
        assert global_approver.forallsites is True
        assert global_approver.sites == []
        
        assert site_approver.forallsites is False
        assert len(site_approver.sites) == 3
    
    
    def test_approver_work_order_approval(self, approver_factory):
        """Test Approver for work order approval"""
        work_order_approver = approver_factory(
            identifier=Approver.Identifier.APPROVER,
            approverfor=['WORKORDER'],
            forallsites=True
        )
        
        assert work_order_approver.identifier == Approver.Identifier.APPROVER
        assert 'WORKORDER' in work_order_approver.approverfor
        assert work_order_approver.forallsites is True
    
    
    def test_approver_work_permit_approval(self, approver_factory):
        """Test Approver for work permit approval"""
        work_permit_approver = approver_factory(
            identifier=Approver.Identifier.APPROVER,
            approverfor=['WORKPERMIT'],
            forallsites=False,
            sites=['SITE001']
        )
        
        work_permit_verifier = approver_factory(
            identifier=Approver.Identifier.VERIFIER,
            approverfor=['WORKPERMIT'],
            forallsites=False,
            sites=['SITE002']  # Different site to avoid unique constraint
        )
        
        assert work_permit_approver.identifier == Approver.Identifier.APPROVER
        assert 'WORKPERMIT' in work_permit_approver.approverfor
        
        assert work_permit_verifier.identifier == Approver.Identifier.VERIFIER
        assert 'WORKPERMIT' in work_permit_verifier.approverfor
    
    
    def test_approver_sla_template_approval(self, approver_factory):
        """Test Approver for SLA template approval"""
        sla_approver = approver_factory(
            identifier=Approver.Identifier.APPROVER,
            approverfor=['SLA_TEMPLATE'],
            forallsites=True
        )
        
        assert sla_approver.identifier == Approver.Identifier.APPROVER
        assert 'SLA_TEMPLATE' in sla_approver.approverfor
        assert sla_approver.forallsites is True
    
    
    def test_approver_multiple_responsibilities(self, approver_factory):
        """Test Approver with multiple approval responsibilities"""
        multi_role_approver = approver_factory(
            identifier=Approver.Identifier.APPROVER,
            approverfor=['WORKORDER', 'WORKPERMIT', 'SLA_TEMPLATE'],
            forallsites=True
        )
        
        assert multi_role_approver.identifier == Approver.Identifier.APPROVER
        assert len(multi_role_approver.approverfor) == 3
        assert 'WORKORDER' in multi_role_approver.approverfor
        assert 'WORKPERMIT' in multi_role_approver.approverfor
        assert 'SLA_TEMPLATE' in multi_role_approver.approverfor
    
    
    def test_approver_site_specific_permissions(self, approver_factory, test_client_wom, test_bu_wom):
        """Test Approver site-specific permissions"""
        # Create additional sites
        site1 = test_bu_wom.__class__.objects.create(
            bucode='SITE001',
            buname='Site 1',
            parent=test_client_wom,
            enable=True
        )
        
        site2 = test_bu_wom.__class__.objects.create(
            bucode='SITE002',
            buname='Site 2',
            parent=test_client_wom,
            enable=True
        )
        
        # Site-specific approver for multiple sites
        multi_site_approver = approver_factory(
            approverfor=['WORKORDER'],
            sites=['SITE001', 'SITE002'],
            forallsites=False,
            client=test_client_wom,
            bu=site1
        )
        
        # Single site approver
        single_site_approver = approver_factory(
            approverfor=['WORKPERMIT'],
            sites=['SITE001'],
            forallsites=False,
            client=test_client_wom,
            bu=site1
        )
        
        assert 'SITE001' in multi_site_approver.sites
        assert 'SITE002' in multi_site_approver.sites
        assert multi_site_approver.forallsites is False
        
        assert single_site_approver.sites == ['SITE001']
        assert single_site_approver.forallsites is False
    
    
    def test_approver_bulk_operations(self, approver_factory, test_client_wom, test_bu_wom):
        """Test bulk operations on Approver"""
        # Create multiple approver records
        approvers = []
        for i in range(15):
            approver = approver_factory(
                approverfor=['WORKORDER'] if i % 2 == 0 else ['WORKPERMIT'],
                identifier=Approver.Identifier.APPROVER if i % 3 == 0 else Approver.Identifier.VERIFIER,
                forallsites=True if i % 4 == 0 else False,
                sites=[] if i % 4 == 0 else [f'SITE{i:03d}'],
                client=test_client_wom,
                bu=test_bu_wom
            )
            approvers.append(approver)
        
        # Test bulk filtering by responsibility
        workorder_approvers = Approver.objects.filter(
            approverfor__contains=['WORKORDER']
        )
        workpermit_approvers = Approver.objects.filter(
            approverfor__contains=['WORKPERMIT']
        )
        
        assert workorder_approvers.count() == 8  # 0,2,4,6,8,10,12,14
        assert workpermit_approvers.count() == 7  # 1,3,5,7,9,11,13
        
        # Test bulk filtering by identifier
        approver_role_count = Approver.objects.filter(
            identifier=Approver.Identifier.APPROVER
        ).count()
        verifier_role_count = Approver.objects.filter(
            identifier=Approver.Identifier.VERIFIER
        ).count()
        
        assert approver_role_count == 5  # 0,3,6,9,12
        assert verifier_role_count == 10  # All others
        
        # Test bulk filtering by site scope
        global_approvers = Approver.objects.filter(
            forallsites=True
        )
        assert global_approvers.count() == 4  # 0,4,8,12
    
    
    def test_approver_filtering_by_client_and_bu(self, approver_factory, test_client_wom, test_bu_wom):
        """Test Approver filtering by client and BU"""
        # Create another client and BU for comparison
        other_client = test_client_wom.__class__.objects.create(
            bucode='OTHER_APP_CLIENT',
            buname='Other Approver Client',
            enable=True
        )
        
        other_bu = test_bu_wom.__class__.objects.create(
            bucode='OTHER_APP_BU',
            buname='Other Approver BU',
            enable=True
        )
        
        # Create approvers for different clients and BUs
        approver1 = approver_factory(
            approverfor=['WORKORDER'],
            client=test_client_wom,
            bu=test_bu_wom
        )
        
        approver2 = approver_factory(
            approverfor=['WORKPERMIT'],
            client=test_client_wom,
            bu=other_bu
        )
        
        approver3 = approver_factory(
            approverfor=['SLA_TEMPLATE'],
            client=other_client,
            bu=test_bu_wom
        )
        
        approver4 = approver_factory(
            approverfor=['WORKORDER'],
            client=other_client,
            bu=other_bu
        )
        
        # Test filtering by client
        client1_approvers = Approver.objects.filter(client=test_client_wom)
        client2_approvers = Approver.objects.filter(client=other_client)
        
        assert approver1 in client1_approvers
        assert approver2 in client1_approvers
        assert approver3 not in client1_approvers
        assert approver4 not in client1_approvers
        
        assert approver3 in client2_approvers
        assert approver4 in client2_approvers
        assert approver1 not in client2_approvers
        assert approver2 not in client2_approvers
    
    
    def test_approver_hierarchy_permissions(self, approver_factory, test_people_wom, test_client_wom, test_bu_wom):
        """Test Approver hierarchy and permission levels"""
        # Senior approver with all permissions
        senior_approver = approver_factory(
            people=test_people_wom,
            identifier=Approver.Identifier.APPROVER,
            approverfor=['WORKORDER', 'WORKPERMIT', 'SLA_TEMPLATE'],
            forallsites=True,
            client=test_client_wom,
            bu=test_bu_wom
        )
        
        # Site manager with limited permissions
        site_manager = approver_factory(
            identifier=Approver.Identifier.APPROVER,
            approverfor=['WORKORDER'],
            forallsites=False,
            sites=['SITE001', 'SITE002'],
            client=test_client_wom,
            bu=test_bu_wom
        )
        
        # Technical verifier
        technical_verifier = approver_factory(
            identifier=Approver.Identifier.VERIFIER,
            approverfor=['WORKPERMIT'],
            forallsites=False,
            sites=['SITE001'],
            client=test_client_wom,
            bu=test_bu_wom
        )
        
        # Verify permission levels
        assert len(senior_approver.approverfor) == 3
        assert senior_approver.forallsites is True
        
        assert len(site_manager.approverfor) == 1
        assert site_manager.forallsites is False
        assert len(site_manager.sites) == 2
        
        assert technical_verifier.identifier == Approver.Identifier.VERIFIER
        assert len(technical_verifier.sites) == 1
    
    
    def test_approver_permission_combinations(self, approver_factory):
        """Test various Approver permission combinations"""
        # Work order only approver
        wo_only = approver_factory(
            approverfor=['WORKORDER'],
            identifier=Approver.Identifier.APPROVER
        )
        
        # Work permit only verifier
        wp_only = approver_factory(
            approverfor=['WORKPERMIT'],
            identifier=Approver.Identifier.VERIFIER
        )
        
        # SLA template only approver
        sla_only = approver_factory(
            approverfor=['SLA_TEMPLATE'],
            identifier=Approver.Identifier.APPROVER
        )
        
        # Work order and permit approver
        wo_wp_approver = approver_factory(
            approverfor=['WORKORDER', 'WORKPERMIT'],
            identifier=Approver.Identifier.APPROVER
        )
        
        # Work permit dual role (approver and verifier in different contexts)
        wp_dual = approver_factory(
            approverfor=['WORKPERMIT'],
            identifier=Approver.Identifier.APPROVER  # Can approve permits
        )
        
        # Verify combinations
        assert wo_only.approverfor == ['WORKORDER']
        assert wp_only.identifier == Approver.Identifier.VERIFIER
        assert sla_only.approverfor == ['SLA_TEMPLATE']
        assert len(wo_wp_approver.approverfor) == 2
        assert wp_dual.identifier == Approver.Identifier.APPROVER
    
    
    def test_approver_performance_queries(self, approver_factory, test_client_wom, test_bu_wom):
        """Test performance-oriented queries on Approver"""
        # Create many approver records for performance testing
        approvers = []
        responsibilities = ['WORKORDER', 'WORKPERMIT', 'SLA_TEMPLATE']
        
        for i in range(60):
            responsibility = [responsibilities[i % len(responsibilities)]]
            approver = approver_factory(
                approverfor=responsibility,
                identifier=Approver.Identifier.APPROVER if i % 2 == 0 else Approver.Identifier.VERIFIER,
                forallsites=True if i % 5 == 0 else False,
                sites=[] if i % 5 == 0 else [f'SITE{i % 10:02d}'],
                client=test_client_wom,
                bu=test_bu_wom
            )
            approvers.append(approver)
        
        # Test count queries
        total_count = Approver.objects.filter(
            client=test_client_wom
        ).count()
        assert total_count >= 60
        
        # Test responsibility-based filtering
        workorder_count = Approver.objects.filter(
            client=test_client_wom,
            approverfor__contains=['WORKORDER']
        ).count()
        workpermit_count = Approver.objects.filter(
            client=test_client_wom,
            approverfor__contains=['WORKPERMIT']
        ).count()
        sla_count = Approver.objects.filter(
            client=test_client_wom,
            approverfor__contains=['SLA_TEMPLATE']
        ).count()
        
        assert workorder_count == 20  # Positions 0,3,6,9,12,15,18,21,24,27,30,33,36,39,42,45,48,51,54,57
        assert workpermit_count == 20  # Positions 1,4,7,10,13,16,19,22,25,28,31,34,37,40,43,46,49,52,55,58
        assert sla_count == 20        # Positions 2,5,8,11,14,17,20,23,26,29,32,35,38,41,44,47,50,53,56,59
        
        # Test identifier filtering
        approver_role_count = Approver.objects.filter(
            client=test_client_wom,
            identifier=Approver.Identifier.APPROVER
        ).count()
        verifier_role_count = Approver.objects.filter(
            client=test_client_wom,
            identifier=Approver.Identifier.VERIFIER
        ).count()
        
        assert approver_role_count == 30  # Even positions
        assert verifier_role_count == 30  # Odd positions
        
        # Test global vs site-specific filtering
        global_approver_count = Approver.objects.filter(
            client=test_client_wom,
            forallsites=True
        ).count()
        
        assert global_approver_count == 12  # Every 5th record (0,5,10,15,20,25,30,35,40,45,50,55)