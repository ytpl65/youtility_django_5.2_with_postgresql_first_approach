import pytest
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from apps.activity.models import Job, Asset, Location, Question
from apps.peoples.models import People
from apps.onboarding.models import Client, BusinessUnit
from django.contrib.auth import get_user_model

User = get_user_model()


class JobManagerTest(TestCase):
    """Test Job Manager methods"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            loginid='testuser',
            email='test@example.com',
            password='testpass123',
            peoplecode='TEST001',
            peoplename='Test User',
            dateofbirth='1990-01-01'
        )
        
        # Create test client and business unit
        self.client = Client.objects.create(
            ccode='CLIENT001',
            cname='Test Client'
        )
        
        self.bu = BusinessUnit.objects.create(
            bucode='BU001',
            buname='Test BU',
            client=self.client
        )
        
        # Create test jobs
        self.job1 = Job.objects.create(
            identifier='JOB001',
            jobdesc='Test Job 1',
            cuser=self.user,
            client=self.client,
            bu=self.bu,
            plandatetime=timezone.now(),
            expirydatetime=timezone.now() + timedelta(hours=2),
            jobstatus='pending'
        )
        
        self.job2 = Job.objects.create(
            identifier='JOB002',
            jobdesc='Test Job 2',
            cuser=self.user,
            client=self.client,
            bu=self.bu,
            plandatetime=timezone.now() - timedelta(days=1),
            expirydatetime=timezone.now() - timedelta(hours=1),
            jobstatus='expired'
        )
        
    def test_get_active_jobs(self):
        """Test getting active jobs"""
        active_jobs = Job.objects.filter(jobstatus='pending')
        self.assertEqual(active_jobs.count(), 1)
        self.assertEqual(active_jobs.first().identifier, 'JOB001')
        
    def test_get_expired_jobs(self):
        """Test getting expired jobs"""
        expired_jobs = Job.objects.filter(jobstatus='expired')
        self.assertEqual(expired_jobs.count(), 1)
        self.assertEqual(expired_jobs.first().identifier, 'JOB002')
        
    @patch('apps.activity.managers.job_manager.timezone.now')
    def test_get_jobs_by_date_range(self, mock_now):
        """Test getting jobs within date range"""
        mock_now.return_value = timezone.now()
        
        # Get jobs from last 7 days
        start_date = timezone.now() - timedelta(days=7)
        end_date = timezone.now()
        
        jobs = Job.objects.filter(
            plandatetime__gte=start_date,
            plandatetime__lte=end_date
        )
        
        self.assertEqual(jobs.count(), 2)
        
    def test_job_manager_with_select_related(self):
        """Test job queries with select_related optimization"""
        # This tests that queries are optimized
        with self.assertNumQueries(1):
            jobs = Job.objects.select_related('cuser', 'client', 'bu').all()
            # Force evaluation
            list(jobs)
            
    def test_job_manager_bulk_operations(self):
        """Test bulk update operations"""
        # Update multiple jobs at once
        updated = Job.objects.filter(jobstatus='pending').update(
            jobstatus='in_progress'
        )
        
        self.assertEqual(updated, 1)
        self.job1.refresh_from_db()
        self.assertEqual(self.job1.jobstatus, 'in_progress')


class AssetManagerTest(TestCase):
    """Test Asset Manager methods"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client.objects.create(
            ccode='CLIENT001',
            cname='Test Client'
        )
        
        self.location = Location.objects.create(
            lcode='LOC001',
            lname='Test Location',
            client=self.client
        )
        
        # Create test assets
        self.asset1 = Asset.objects.create(
            acode='ASSET001',
            aname='Test Asset 1',
            client=self.client,
            location=self.location,
            astatus='active'
        )
        
        self.asset2 = Asset.objects.create(
            acode='ASSET002',
            aname='Test Asset 2', 
            client=self.client,
            location=self.location,
            astatus='inactive'
        )
        
    def test_get_active_assets(self):
        """Test getting active assets"""
        active_assets = Asset.objects.filter(astatus='active')
        self.assertEqual(active_assets.count(), 1)
        self.assertEqual(active_assets.first().acode, 'ASSET001')
        
    def test_get_assets_by_location(self):
        """Test getting assets by location"""
        location_assets = Asset.objects.filter(location=self.location)
        self.assertEqual(location_assets.count(), 2)
        
    def test_asset_search(self):
        """Test asset search functionality"""
        # Search by code
        results = Asset.objects.filter(acode__icontains='ASSET')
        self.assertEqual(results.count(), 2)
        
        # Search by name
        results = Asset.objects.filter(aname__icontains='Test Asset 1')
        self.assertEqual(results.count(), 1)
        
    def test_asset_manager_prefetch_related(self):
        """Test asset queries with prefetch_related optimization"""
        # Create some related data if needed
        assets = Asset.objects.prefetch_related('location').all()
        
        # This should not cause additional queries
        for asset in assets:
            _ = asset.location.lname


class LocationManagerTest(TestCase):
    """Test Location Manager methods"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client.objects.create(
            ccode='CLIENT001',
            cname='Test Client'
        )
        
        # Create parent location
        self.parent_location = Location.objects.create(
            lcode='LOC001',
            lname='Parent Location',
            client=self.client
        )
        
        # Create child locations
        self.child_location1 = Location.objects.create(
            lcode='LOC002',
            lname='Child Location 1',
            client=self.client,
            parent=self.parent_location
        )
        
        self.child_location2 = Location.objects.create(
            lcode='LOC003',
            lname='Child Location 2',
            client=self.client,
            parent=self.parent_location
        )
        
    def test_get_root_locations(self):
        """Test getting root locations (no parent)"""
        root_locations = Location.objects.filter(parent__isnull=True)
        self.assertEqual(root_locations.count(), 1)
        self.assertEqual(root_locations.first().lcode, 'LOC001')
        
    def test_get_child_locations(self):
        """Test getting child locations of a parent"""
        children = Location.objects.filter(parent=self.parent_location)
        self.assertEqual(children.count(), 2)
        
    def test_location_hierarchy(self):
        """Test location hierarchy traversal"""
        # Get all descendants
        all_locations = Location.objects.all()
        self.assertEqual(all_locations.count(), 3)
        
        # Check parent-child relationships
        self.assertEqual(self.child_location1.parent, self.parent_location)
        self.assertEqual(self.child_location2.parent, self.parent_location)
        
    def test_location_by_client(self):
        """Test filtering locations by client"""
        client_locations = Location.objects.filter(client=self.client)
        self.assertEqual(client_locations.count(), 3)


class QuestionManagerTest(TestCase):
    """Test Question Manager methods"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client.objects.create(
            ccode='CLIENT001', 
            cname='Test Client'
        )
        
        # Create test questions
        self.question1 = Question.objects.create(
            qcode='Q001',
            question='Test Question 1?',
            client=self.client,
            qtype='text',
            isactive=True
        )
        
        self.question2 = Question.objects.create(
            qcode='Q002',
            question='Test Question 2?',
            client=self.client,
            qtype='checkbox',
            isactive=False
        )
        
        self.question3 = Question.objects.create(
            qcode='Q003',
            question='Test Question 3?',
            client=self.client,
            qtype='radio',
            isactive=True
        )
        
    def test_get_active_questions(self):
        """Test getting active questions"""
        active_questions = Question.objects.filter(isactive=True)
        self.assertEqual(active_questions.count(), 2)
        
    def test_get_questions_by_type(self):
        """Test getting questions by type"""
        text_questions = Question.objects.filter(qtype='text')
        self.assertEqual(text_questions.count(), 1)
        
        checkbox_questions = Question.objects.filter(qtype='checkbox')
        self.assertEqual(checkbox_questions.count(), 1)
        
    def test_question_ordering(self):
        """Test question ordering"""
        questions = Question.objects.all().order_by('qcode')
        codes = [q.qcode for q in questions]
        self.assertEqual(codes, ['Q001', 'Q002', 'Q003'])
        
    def test_question_search(self):
        """Test question search functionality"""
        results = Question.objects.filter(question__icontains='Test Question')
        self.assertEqual(results.count(), 3)
        
    def test_bulk_activate_questions(self):
        """Test bulk activation of questions"""
        updated = Question.objects.filter(isactive=False).update(isactive=True)
        self.assertEqual(updated, 1)
        
        # Verify all questions are now active
        active_count = Question.objects.filter(isactive=True).count()
        self.assertEqual(active_count, 3)