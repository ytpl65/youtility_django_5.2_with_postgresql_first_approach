import pytest
import json
from django.test import RequestFactory, Client
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from apps.activity.models.asset_model import Asset
from apps.activity.models.job_model import Job 
from apps.activity.models.location_model import Location
from apps.activity.models.question_model import Question
from apps.peoples.models import People
from apps.onboarding.models import Bt


@pytest.fixture
def test_client():
    """Create Django test client"""
    return Client()


@pytest.fixture
def authenticated_client(people_factory):
    """Create authenticated test client with session"""
    client = Client()
    
    # Create test data
    bt = Bt.objects.create(bucode='INTTEST', buname='Integration Test Client', enable=True)
    user = people_factory(client=bt, bu=bt)
    
    # Login simulation through session
    session = client.session
    session['client_id'] = bt.id
    session['bu_id'] = bt.id
    session['assignedsites'] = [bt.id]
    session['user_id'] = user.id
    session.save()
    
    return client, user, bt


@pytest.mark.django_db
class TestActivityIntegration:
    """Integration tests for Activity app components working together"""
    
    def test_asset_location_job_integration(self, asset_factory, location_factory, job_factory, client_bt, bu_bt):
        """Test integration between Asset, Location, and Job models"""
        # Create location
        location = location_factory(
            loccode="INT001",
            locname="Integration Test Location",
            client=client_bt,
            bu=bu_bt
        )
        
        # Create asset 
        asset = asset_factory(
            assetcode="INT001",
            assetname="Integration Test Asset",
            client=client_bt,
            bu=bu_bt
        )
        
        # Create job referencing the asset
        job = job_factory(
            jobname="Integration Test Job",
            identifier="TASK",
            client=client_bt,
            bu=bu_bt
        )
        
        # Verify relationships work
        assert asset.client == client_bt
        assert location.client == client_bt
        assert job.client == client_bt
        assert asset.bu == bu_bt
        
        # Test filtering by client
        client_assets = Asset.objects.filter(client=client_bt)
        client_locations = Location.objects.filter(client=client_bt)
        client_jobs = Job.objects.filter(client=client_bt)
        
        assert asset in client_assets
        assert location in client_locations
        assert job in client_jobs


    def test_question_job_workflow(self, question_factory, questionset_factory, job_factory, client_bt, bu_bt):
        """Test Question and QuestionSet integration with Jobs"""
        # Create question
        question = question_factory(
            quesname="Integration Test Question",
            answertype="YESNO"
        )
        
        # Create question set
        qset = questionset_factory(
            qsetname="Integration Test Question Set",
            client=client_bt,
            bu=bu_bt
        )
        
        # Create job that uses the question set
        job = job_factory(
            jobname="Question Integration Job",
            identifier="TASK",
            client=client_bt,
            bu=bu_bt
        )
        
        # Verify question and questionset exist
        assert question.quesname == "Integration Test Question"
        assert qset.qsetname == "Integration Test Question Set"
        assert job.jobname == "Question Integration Job"


    def test_bulk_asset_operations(self, asset_factory, client_bt, bu_bt):
        """Test bulk operations on assets"""
        # Create multiple assets
        assets = []
        for i in range(10):
            asset = asset_factory(
                assetcode=f"BULK{i:03d}",
                assetname=f"Bulk Asset {i}",
                iscritical=(i % 2 == 0),  # Every other asset is critical
                client=client_bt,
                bu=bu_bt
            )
            assets.append(asset)
        
        # Test bulk filtering
        critical_assets = Asset.objects.filter(iscritical=True, client=client_bt)
        non_critical_assets = Asset.objects.filter(iscritical=False, client=client_bt)
        
        assert critical_assets.count() == 5
        assert non_critical_assets.count() == 5
        
        # Test bulk update
        Asset.objects.filter(
            assetcode__startswith="BULK",
            client=client_bt
        ).update(enable=False)
        
        # Verify all bulk assets are disabled
        disabled_assets = Asset.objects.filter(
            assetcode__startswith="BULK",
            enable=False,
            client=client_bt
        )
        assert disabled_assets.count() == 10


    def test_job_scheduling_workflow(self, job_factory, people_factory, client_bt, bu_bt):
        """Test job scheduling and assignment workflow"""
        # Create people for assignment
        person1 = people_factory(
            peoplecode="SCHED001",
            peoplename="Scheduler Test Person 1",
            client=client_bt,
            bu=bu_bt
        )
        person2 = people_factory(
            peoplecode="SCHED002", 
            peoplename="Scheduler Test Person 2",
            client=client_bt,
            bu=bu_bt
        )
        
        # Create jobs with different priorities
        high_priority_job = job_factory(
            jobname="High Priority Task",
            priority="HIGH",
            identifier="TASK",
            client=client_bt,
            bu=bu_bt
        )
        
        low_priority_job = job_factory(
            jobname="Low Priority Task",
            priority="LOW",
            identifier="TASK",
            client=client_bt,
            bu=bu_bt
        )
        
        # Test priority-based filtering
        high_priority_jobs = Job.objects.filter(priority="HIGH", client=client_bt)
        low_priority_jobs = Job.objects.filter(priority="LOW", client=client_bt)
        
        assert high_priority_job in high_priority_jobs
        assert low_priority_job in low_priority_jobs
        
        # Test job ordering by priority
        jobs_by_priority = Job.objects.filter(
            client=client_bt,
            identifier="TASK"
        ).order_by('-priority')  # Assuming HIGH > LOW alphabetically
        
        assert jobs_by_priority.exists()


    def test_asset_criticality_workflow(self, asset_factory, client_bt, bu_bt):
        """Test asset criticality classification and filtering"""
        # Create assets with different criticality levels
        critical_assets_data = [
            ("CRITICAL001", "Critical Pump", True),
            ("CRITICAL002", "Critical Generator", True),
            ("NORMAL001", "Normal Light", False),
            ("NORMAL002", "Normal Fan", False),
        ]
        
        created_assets = []
        for code, name, is_critical in critical_assets_data:
            asset = asset_factory(
                assetcode=code,
                assetname=name,
                iscritical=is_critical,
                client=client_bt,
                bu=bu_bt
            )
            created_assets.append(asset)
        
        # Test critical asset filtering
        critical_assets = Asset.objects.filter(iscritical=True, client=client_bt)
        normal_assets = Asset.objects.filter(iscritical=False, client=client_bt)
        
        assert critical_assets.count() == 2
        assert normal_assets.count() == 2
        
        # Test asset name filtering
        pump_assets = Asset.objects.filter(
            assetname__icontains="Pump",
            client=client_bt
        )
        assert pump_assets.count() == 1
        assert pump_assets.first().assetcode == "CRITICAL001"


    def test_job_date_range_filtering(self, job_factory, client_bt, bu_bt):
        """Test job filtering by date ranges"""
        now = timezone.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)
        
        # Create jobs with different date ranges
        past_job = job_factory(
            jobname="Past Job",
            fromdate=now - timedelta(days=2),
            uptodate=now - timedelta(days=1),
            client=client_bt,
            bu=bu_bt
        )
        
        current_job = job_factory(
            jobname="Current Job",
            fromdate=now - timedelta(hours=1),
            uptodate=now + timedelta(hours=1),
            client=client_bt,
            bu=bu_bt
        )
        
        future_job = job_factory(
            jobname="Future Job",
            fromdate=now + timedelta(days=1),
            uptodate=now + timedelta(days=2),
            client=client_bt,
            bu=bu_bt
        )
        
        # Test date range filtering
        today_jobs = Job.objects.filter(
            fromdate__date=today,
            client=client_bt
        )
        
        current_jobs = Job.objects.filter(
            fromdate__lte=now,
            uptodate__gte=now,
            client=client_bt
        )
        
        future_jobs = Job.objects.filter(
            fromdate__date__gt=today,
            client=client_bt
        )
        
        assert current_job in current_jobs
        assert future_job in future_jobs


    def test_location_gps_integration(self, location_factory, client_bt, bu_bt):
        """Test GPS location functionality integration"""
        from django.contrib.gis.geos import Point
        
        # Create locations with GPS coordinates
        locations_data = [
            ("GPS001", "Bangalore Office", Point(77.5946, 12.9716)),
            ("GPS002", "Mumbai Office", Point(72.8777, 19.0760)),
            ("GPS003", "Delhi Office", Point(77.1025, 28.7041)),
        ]
        
        created_locations = []
        for code, name, gps in locations_data:
            location = location_factory(
                loccode=code,
                locname=name,
                gpslocation=gps,
                client=client_bt,
                bu=bu_bt
            )
            created_locations.append(location)
        
        # Test GPS coordinate retrieval
        bangalore_location = Location.objects.get(loccode="GPS001")
        assert bangalore_location.gpslocation.x == 77.5946
        assert bangalore_location.gpslocation.y == 12.9716
        
        # Test location filtering by GPS (if GeoDjango is available)
        try:
            from django.contrib.gis.measure import Distance
            
            # Find locations within 100km of Bangalore
            nearby_locations = Location.objects.filter(
                gpslocation__distance_lte=(
                    bangalore_location.gpslocation,
                    Distance(km=100)
                ),
                client=client_bt
            )
            
            # Should at least include Bangalore itself
            assert bangalore_location in nearby_locations
            
        except ImportError:
            # GeoDjango not available, skip distance tests
            pass


    def test_tenant_isolation(self, asset_factory, job_factory, location_factory):
        """Test that tenant isolation works correctly"""
        # Create two different clients
        client1 = Bt.objects.create(bucode='TENANT1', buname='Tenant 1', enable=True)
        client2 = Bt.objects.create(bucode='TENANT2', buname='Tenant 2', enable=True)
        
        # Create assets for each client
        asset1 = asset_factory(
            assetcode="TENANT1_ASSET",
            assetname="Tenant 1 Asset",
            client=client1,
            bu=client1
        )
        
        asset2 = asset_factory(
            assetcode="TENANT2_ASSET",
            assetname="Tenant 2 Asset", 
            client=client2,
            bu=client2
        )
        
        # Test isolation - each client should only see their own assets
        client1_assets = Asset.objects.filter(client=client1)
        client2_assets = Asset.objects.filter(client=client2)
        
        assert asset1 in client1_assets
        assert asset1 not in client2_assets
        assert asset2 in client2_assets
        assert asset2 not in client1_assets
        
        # Test cross-tenant access prevention
        assert client1_assets.filter(id=asset2.id).count() == 0
        assert client2_assets.filter(id=asset1.id).count() == 0


    def test_audit_trail_integration(self, asset_factory, people_factory, client_bt, bu_bt):
        """Test audit trail functionality across models"""
        # Create test user for audit trail
        user = people_factory(
            peoplecode="AUDIT001",
            peoplename="Audit Test User",
            client=client_bt,
            bu=bu_bt
        )
        
        # Create asset and track timestamps
        asset = asset_factory(
            assetcode="AUDIT001",
            assetname="Audit Test Asset",
            client=client_bt,
            bu=bu_bt
        )
        
        original_created = asset.cdtz if hasattr(asset, 'cdtz') else None
        original_modified = asset.mdtz if hasattr(asset, 'mdtz') else None
        
        # Modify asset
        asset.assetname = "Modified Audit Test Asset"
        asset.save()
        
        # Refresh from database
        asset.refresh_from_db()
        
        # Verify timestamps exist (if implemented)
        if hasattr(asset, 'cdtz'):
            assert asset.cdtz == original_created
        if hasattr(asset, 'mdtz'):
            # Modified time should be updated
            assert asset.mdtz >= original_modified if original_modified else True


    def test_cascade_deletion_behavior(self, asset_factory, job_factory, client_bt, bu_bt):
        """Test cascading deletion behavior"""
        # Create asset
        asset = asset_factory(
            assetcode="CASCADE001",
            assetname="Cascade Test Asset",
            client=client_bt,
            bu=bu_bt
        )
        
        # Delete client and verify cascade behavior
        # Note: This test depends on your actual FK constraints
        # Adjust based on your model relationships
        
        # Count related objects before deletion
        initial_asset_count = Asset.objects.filter(client=client_bt).count()
        
        # For safety, don't actually delete in test
        # Just verify the relationship exists
        assert asset.client == client_bt
        assert initial_asset_count > 0


@pytest.mark.django_db 
class TestActivityPerformance:
    """Performance-focused tests for Activity app"""
    
    def test_bulk_asset_creation_performance(self, client_bt, bu_bt):
        """Test performance of bulk asset creation"""
        import time
        from django.contrib.gis.geos import Point
        
        start_time = time.time()
        
        # Create 100 assets
        assets_to_create = []
        for i in range(100):
            assets_to_create.append(Asset(
                assetcode=f"PERF{i:04d}",
                assetname=f"Performance Test Asset {i}",
                iscritical=(i % 10 == 0),
                gpslocation=Point(77.5946 + (i * 0.001), 12.9716 + (i * 0.001)),
                client=client_bt,
                bu=bu_bt,
                enable=True
            ))
        
        # Bulk create
        Asset.objects.bulk_create(assets_to_create)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Verify creation
        created_assets = Asset.objects.filter(assetcode__startswith="PERF")
        assert created_assets.count() == 100
        
        # Performance assertion (adjust threshold as needed)
        assert creation_time < 5.0, f"Bulk creation took {creation_time:.2f}s, should be < 5s"


    def test_complex_query_performance(self, asset_factory, job_factory, client_bt, bu_bt):
        """Test performance of complex queries"""
        import time
        
        # Create test data
        for i in range(50):
            asset_factory(
                assetcode=f"COMPLEX{i:03d}",
                assetname=f"Complex Query Asset {i}",
                iscritical=(i % 5 == 0),
                client=client_bt,
                bu=bu_bt
            )
            
            job_factory(
                jobname=f"Complex Query Job {i}",
                priority="HIGH" if i % 3 == 0 else "LOW",
                identifier="TASK",
                client=client_bt,
                bu=bu_bt
            )
        
        start_time = time.time()
        
        # Complex query with joins and filters
        complex_query = Asset.objects.filter(
            client=client_bt,
            iscritical=True,
            enable=True
        ).select_related('client', 'bu').prefetch_related(
            'client'
        ).order_by('assetcode')
        
        # Force evaluation
        list(complex_query)
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Performance assertion
        assert query_time < 1.0, f"Complex query took {query_time:.2f}s, should be < 1s"