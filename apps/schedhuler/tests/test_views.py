from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from unittest.mock import patch, Mock, MagicMock
import json
from datetime import datetime, time, timedelta, date

from apps.schedhuler.views import (
    Schd_I_TourFormJob, Update_I_TourFormJob, Retrive_I_ToursJob,
    Retrive_I_ToursJobneed, SchdTaskFormJob, RetriveSchdTasksJob
)
from apps.activity.models.job_model import Job, Jobneed
from apps.peoples.models import People, Pgroup
from apps.activity.models.asset_model import Asset
from apps.activity.models.question_model import QuestionSet
from apps.onboarding.models import Bt

User = get_user_model()


class SchdITourFormJobTestCase(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
        
        self.bt = Bt.objects.create(
            buname="Test BU",
            bucode="TESTBU001"
        )
        
        self.user = User.objects.create_user(
            loginid='testuser',
            password='testpass123',
            peoplecode='TEST001',
            peoplename='Test User',
            dateofbirth='1990-01-01',
            email='testuser@example.com',
            bu=self.bt
        )
        
        self.people = People.objects.create(
            peoplename="Test Person",
            email="test@example.com",
            peoplecode="TEST002",
            dateofbirth="1990-01-01"
        )
        
        self.group = Pgroup.objects.create(
            groupname="Test Group"
        )
        
        self.asset = Asset.objects.create(
            assetcode="TESTASSET001",
            assetname="Test Asset",
            iscritical=False
        )
        
        self.questionset = QuestionSet.objects.create(
            qsetname="Test Questionset"
        )
        
        self.view = Schd_I_TourFormJob()

    def add_session_to_request(self, request):
        # Add session middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['assignedsites'] = [self.bt.id]
        request.session['client_id'] = self.bt.id
        request.session['bu_id'] = self.bt.id
        request.session['sitecode'] = 'TESTBU001'
        request.session['sitename'] = 'Test BU'
        request.session['clientcode'] = 'TESTBU001'
        request.session.save()
        
        # Add message middleware
        from django.contrib.messages.middleware import MessageMiddleware
        message_middleware = MessageMiddleware(lambda x: None)
        message_middleware.process_request(request)
        
        # Add auth middleware
        auth_middleware = AuthenticationMiddleware(lambda x: None)
        auth_middleware.process_request(request)
        request.user = self.user


    @patch('apps.schedhuler.views.utils.get_current_db_name')
    @patch('apps.schedhuler.views.putils.save_userinfo')
    def test_post_request_create_tour(self, mock_save_userinfo, mock_get_db):
        mock_get_db.return_value = 'default'
        mock_save_userinfo.return_value = Mock(id=1, jobname="Test Tour")
        
        form_data = {
            'jobname': 'Test Tour',
            'people': self.people.id,
            'pgroup': self.group.id,
            'starttime': '08:00',
            'endtime': '17:00',
            'fromdate': '2024-01-01',
            'uptodate': '2024-12-31',
            'gracetime': 5,
            'expirytime': 0,
            'priority': 'LOW'
        }
        
        post_data = {
            'formData': '&'.join([f'{k}={v}' for k, v in form_data.items()]),
            'asssigned_checkpoints': json.dumps([
                [1, self.asset.id, 'Test Asset', self.questionset.id, 'Test QSet', 10]
            ])
        }
        
        request = self.factory.post('/schedhuler/create-tour/', post_data)
        self.add_session_to_request(request)
        
        # Create a mock form instance
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.data = form_data
        mock_job = Mock()
        mock_job.id = 1
        mock_job.jobname = "Test Tour"
        mock_form.save.return_value = mock_job
        
        self.view.request = request
        with patch.object(self.view, 'form_class', return_value=mock_form):
            response = self.view.post(request)
        
        self.assertIsInstance(response, JsonResponse)

    def test_process_invalid_schd_tourform(self):
        form = Mock()
        form.errors = {'jobname': ['This field is required.']}
        
        response = self.view.process_invalid_schd_tourform(form)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 404)

    @patch('apps.schedhuler.views.putils.save_userinfo')
    def test_save_checkpoints_for_tour(self, mock_save_userinfo):
        checkpoints = [
            [1, self.asset.id, 'Test Asset', self.questionset.id, 'Test QSet', 10]
        ]
        
        job = Mock()
        job.id = 1
        job.jobname = "Test Job"
        
        request = self.factory.post('/')
        self.add_session_to_request(request)
        
        self.view.request = request
        with patch.object(self.view, 'insert_checkpoints') as mock_insert:
            self.view.save_checpoints_for_tour(checkpoints, job, request)
            mock_insert.assert_called_once_with(checkpoints, job, request)


class UpdateITourFormJobTestCase(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
        
        self.bt = Bt.objects.create(
            buname="Test BU",
            bucode="TESTBU001"
        )
        
        self.user = User.objects.create_user(
            loginid='testuser',
            password='testpass123',
            peoplecode='TEST001',
            peoplename='Test User',
            dateofbirth='1990-01-01',
            email='testuser@example.com',
            bu=self.bt
        )
        
        self.people = People.objects.create(
            peoplename="Test Person",
            email="test@example.com",
            peoplecode="TEST002",
            dateofbirth="1990-01-01"
        )
        
        self.job = Job.objects.create(
            jobname="Test Job",
            jobdesc="Test Description",
            people=self.people,
            fromdate=datetime.now(),
            uptodate=datetime.now() + timedelta(days=30),
            planduration=60,
            gracetime=15,
            expirytime=120,
            priority=Job.Priority.MEDIUM,
            seqno=1,
            scantype=Job.Scantype.SKIP
        )
        
        self.view = Update_I_TourFormJob()

    def add_session_to_request(self, request):
        # Add session middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['assignedsites'] = [self.bt.id]
        request.session['client_id'] = self.bt.id
        request.session['bu_id'] = self.bt.id
        request.session['sitecode'] = 'TESTBU001'
        request.session['sitename'] = 'Test BU'
        request.session['clientcode'] = 'TESTBU001'
        request.session.save()
        
        # Add message middleware
        from django.contrib.messages.middleware import MessageMiddleware
        message_middleware = MessageMiddleware(lambda x: None)
        message_middleware.process_request(request)
        
        # Add auth middleware
        auth_middleware = AuthenticationMiddleware(lambda x: None)
        auth_middleware.process_request(request)
        request.user = self.user


    def test_get_nonexistent_job(self):
        request = self.factory.get('/schedhuler/update-tour/999/')
        self.add_session_to_request(request)
        
        self.view.request = request
        response = self.view.get(request, pk=999)
        
        self.assertEqual(response.status_code, 302)

    def test_get_checkpoints(self):
        obj = Mock()
        obj.id = 1
        
        with patch.object(self.view.model.objects, 'select_related') as mock_select:
            mock_queryset = Mock()
            mock_queryset.filter.return_value.values.return_value = [
                {
                    'seqno': 1,
                    'asset__assetname': 'Test Asset',
                    'asset__id': 1,
                    'qset__qset_name': 'Test QSet',
                    'qset__id': 1,
                    'expirytime': 10,
                    'id': 1
                }
            ]
            mock_select.return_value = mock_queryset
            
            checkpoints = self.view.get_checkpoints(obj)
            
            self.assertIsNotNone(checkpoints)


class RetriveIToursJobTestCase(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
        
        self.bt = Bt.objects.create(
            buname="Test BU",
            bucode="TESTBU001"
        )
        
        self.user = User.objects.create_user(
            loginid='testuser',
            password='testpass123',
            peoplecode='TEST001',
            peoplename='Test User',
            dateofbirth='1990-01-01',
            email='testuser@example.com',
            bu=self.bt
        )
        
        self.people = People.objects.create(
            peoplename="Test Person",
            email="test@example.com",
            peoplecode="TEST002",
            dateofbirth="1990-01-01"
        )
        
        self.group = Pgroup.objects.create(
            groupname="Test Group"
        )
        
        self.view = Retrive_I_ToursJob()

    def add_session_to_request(self, request):
        # Add session middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['assignedsites'] = [self.bt.id]
        request.session['client_id'] = self.bt.id
        request.session['bu_id'] = self.bt.id
        request.session['sitecode'] = 'TESTBU001'
        request.session['sitename'] = 'Test BU'
        request.session['clientcode'] = 'TESTBU001'
        request.session.save()
        
        # Add message middleware
        from django.contrib.messages.middleware import MessageMiddleware
        message_middleware = MessageMiddleware(lambda x: None)
        message_middleware.process_request(request)
        
        # Add auth middleware
        auth_middleware = AuthenticationMiddleware(lambda x: None)
        auth_middleware.process_request(request)
        request.user = self.user

    @patch('apps.schedhuler.views.Retrive_I_ToursJob.paginate_results')
    def test_get_tours_list(self, mock_paginate):
        mock_paginate.return_value = {'schdtour_list': [], 'schdtour_filter': Mock()}
        
        request = self.factory.get('/schedhuler/tours/')
        self.add_session_to_request(request)
        
        with patch.object(self.view.model.objects, 'select_related') as mock_select:
            mock_queryset = Mock()
            mock_queryset.filter.return_value.values.return_value.order_by.return_value = []
            mock_select.return_value = mock_queryset
            
            self.view.request = request
            response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)

    def test_paginate_results(self):
        request = self.factory.get('/schedhuler/tours/?page=1')
        objects = []
        
        with patch('apps.schedhuler.filters.SchdTourFilter') as mock_filter:
            mock_filter_instance = Mock()
            mock_filter_instance.form = Mock()
            mock_filter_instance.qs = objects  # Return the same empty list
            mock_filter.return_value = mock_filter_instance
            
            with patch('django.core.paginator.Paginator') as mock_paginator:
                mock_page = Mock()
                mock_page.object_list = objects
                mock_paginator_instance = Mock()
                mock_paginator_instance.get_page.return_value = mock_page
                mock_paginator.return_value = mock_paginator_instance
                
                result = self.view.paginate_results(request, objects)
        
        self.assertIn('schdtour_list', result)
        self.assertIn('schdtour_filter', result)


class SchdTaskFormJobTestCase(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
        
        self.bt = Bt.objects.create(
            buname="Test BU",
            bucode="TESTBU001"
        )
        
        self.user = User.objects.create_user(
            loginid='testuser',
            password='testpass123',
            peoplecode='TEST001',
            peoplename='Test User',
            dateofbirth='1990-01-01',
            email='testuser@example.com',
            bu=self.bt
        )
        
        self.people = People.objects.create(
            peoplename="Test Person",
            email="test@example.com",
            peoplecode="TEST002",
            dateofbirth="1990-01-01"
        )
        
        self.asset = Asset.objects.create(
            assetcode="TESTASSET001",
            assetname="Test Asset",
            iscritical=False
        )
        
        self.questionset = QuestionSet.objects.create(
            qsetname="Test Questionset"
        )
        
        self.view = SchdTaskFormJob()

    def add_session_to_request(self, request):
        # Add session middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['assignedsites'] = [self.bt.id]
        request.session['client_id'] = self.bt.id
        request.session['bu_id'] = self.bt.id
        request.session['sitecode'] = 'TESTBU001'
        request.session['sitename'] = 'Test BU'
        request.session['clientcode'] = 'TESTBU001'
        request.session.save()
        
        # Add message middleware
        from django.contrib.messages.middleware import MessageMiddleware
        message_middleware = MessageMiddleware(lambda x: None)
        message_middleware.process_request(request)
        
        # Add auth middleware
        auth_middleware = AuthenticationMiddleware(lambda x: None)
        auth_middleware.process_request(request)
        request.user = self.user

    @patch('apps.schedhuler.views.utils.get_current_db_name')
    @patch('apps.schedhuler.views.putils.save_userinfo')
    def test_post_create_task(self, mock_save_userinfo, mock_get_db):
        mock_get_db.return_value = 'default'
        mock_save_userinfo.return_value = Mock(id=1, jobname="Test Task")
        
        form_data = {
            'jobname': 'Test Task',
            'asset': self.asset.id,
            'qset': self.questionset.id,
            'people': self.people.id,
            'starttime': '08:00',
            'endtime': '17:00',
            'fromdate': '2024-01-01',
            'uptodate': '2024-12-31',
            'planduration': 60,
            'gracetime': 5,
            'expirytime': 5
        }
        
        post_data = {
            'formData': '&'.join([f'{k}={v}' for k, v in form_data.items()])
        }
        
        request = self.factory.post('/schedhuler/create-task/', post_data)
        self.add_session_to_request(request)
        
        # Create a mock form instance
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.data = form_data
        mock_job = Mock()
        mock_job.id = 1
        mock_job.jobname = "Test Task"
        mock_form.save.return_value = mock_job
        
        self.view.request = request
        with patch.object(self.view, 'form_class', return_value=mock_form):
            response = self.view.post(request)
        
        self.assertIsInstance(response, JsonResponse)

    def test_process_valid_schd_taskform(self):
        form = Mock()
        job = Mock()
        job.id = 1
        job.jobname = "Test Task"
        form.save.return_value = job
        
        request = self.factory.post('/')
        self.add_session_to_request(request)
        
        self.view.request = request
        with patch('apps.schedhuler.views.putils.save_userinfo', return_value=job):
            response = self.view.process_valid_schd_taskform(request, form)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)

    def test_process_invalid_schd_taskform(self):
        form = Mock()
        form.errors = {'jobname': ['This field is required.']}
        
        response = self.view.process_invalid_schd_taskform(form)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 404)


class RetriveSchdTasksJobTestCase(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
        
        self.bt = Bt.objects.create(
            buname="Test BU",
            bucode="TESTBU001"
        )
        
        self.user = User.objects.create_user(
            loginid='testuser',
            password='testpass123',
            peoplecode='TEST001',
            peoplename='Test User',
            dateofbirth='1990-01-01',
            email='testuser@example.com',
            bu=self.bt
        )
        
        self.view = RetriveSchdTasksJob()

    def add_session_to_request(self, request):
        # Add session middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['assignedsites'] = [self.bt.id]
        request.session['client_id'] = self.bt.id
        request.session['bu_id'] = self.bt.id
        request.session['sitecode'] = 'TESTBU001'
        request.session['sitename'] = 'Test BU'
        request.session['clientcode'] = 'TESTBU001'
        request.session.save()
        
        # Add message middleware
        from django.contrib.messages.middleware import MessageMiddleware
        message_middleware = MessageMiddleware(lambda x: None)
        message_middleware.process_request(request)
        
        # Add auth middleware
        auth_middleware = AuthenticationMiddleware(lambda x: None)
        auth_middleware.process_request(request)
        request.user = self.user

    def test_get_template(self):
        request = self.factory.get('/schedhuler/tasks/?template=true')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)

    def test_get_tasks_list(self):
        request = self.factory.get('/schedhuler/tasks/?action=list')
        self.add_session_to_request(request)
        
        with patch.object(self.view.model.objects, 'select_related') as mock_select:
            mock_queryset = Mock()
            mock_queryset.filter.return_value.values.return_value.order_by.return_value = []
            mock_select.return_value = mock_queryset
            
            self.view.request = request
            response = self.view.get(request)
        
        self.assertIsInstance(response, JsonResponse)

    def test_paginate_results(self):
        request = self.factory.get('/schedhuler/tasks/?page=1')
        objects = []
        
        with patch('apps.schedhuler.filters.SchdTaskFilter') as mock_filter:
            mock_filter_instance = Mock()
            mock_filter_instance.form = Mock()
            mock_filter_instance.qs = objects  # Return the same empty list
            mock_filter.return_value = mock_filter_instance
            
            with patch('django.core.paginator.Paginator') as mock_paginator:
                mock_page = Mock()
                mock_page.object_list = objects
                mock_paginator_instance = Mock()
                mock_paginator_instance.get_page.return_value = mock_page
                mock_paginator.return_value = mock_paginator_instance
                
                result = self.view.paginate_results(request, objects)
        
        self.assertIn('schd_task_list', result)
        self.assertIn('schd_task_filter', result)


class DeleteCheckpointFromTourTestCase(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
        
        self.bt = Bt.objects.create(
            buname="Test BU",
            bucode="TESTBU001"
        )
        
        self.user = User.objects.create_user(
            loginid='testuser',
            password='testpass123',
            peoplecode='TEST001',
            peoplename='Test User',
            dateofbirth='1990-01-01',
            email='testuser@example.com',
            bu=self.bt
        )

    @patch('apps.schedhuler.views.sutils.delete_from_job')
    def test_delete_checkpoint_from_job(self, mock_delete_job):
        request = self.factory.get(
            '/schedhuler/delete-checkpoint/?datasource=job&checkpointid=1&checklistid=1&job=1'
        )
        
        from apps.schedhuler.views import deleteChekpointFromTour
        response = deleteChekpointFromTour(request)
        
        self.assertIsInstance(response, JsonResponse)
        mock_delete_job.assert_called_once_with('1', '1', '1')

    @patch('apps.schedhuler.views.sutils.delete_from_jobneed')
    def test_delete_checkpoint_from_jobneed(self, mock_delete_jobneed):
        request = self.factory.get(
            '/schedhuler/delete-checkpoint/?datasource=jobneed&checkpointid=1&checklistid=1&job=1'
        )
        
        from apps.schedhuler.views import deleteChekpointFromTour
        response = deleteChekpointFromTour(request)
        
        self.assertIsInstance(response, JsonResponse)
        mock_delete_jobneed.assert_called_once_with('1', '1', '1')

    def test_delete_checkpoint_invalid_method(self):
        request = self.factory.post('/schedhuler/delete-checkpoint/')
        
        from apps.schedhuler.views import deleteChekpointFromTour
        from django.http import Http404
        
        response = deleteChekpointFromTour(request)
        self.assertEqual(response, Http404)


class RunInternalTourSchedulerTestCase(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
        
        self.bt = Bt.objects.create(
            buname="Test BU",
            bucode="TESTBU001"
        )
        
        self.user = User.objects.create_user(
            loginid='testuser',
            password='testpass123',
            peoplecode='TEST001',
            peoplename='Test User',
            dateofbirth='1990-01-01',
            email='testuser@example.com',
            bu=self.bt
        )

    def add_session_to_request(self, request):
        # Add session middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['assignedsites'] = [self.bt.id]
        request.session['client_id'] = self.bt.id
        request.session['bu_id'] = self.bt.id
        request.session['sitecode'] = 'TESTBU001'
        request.session['sitename'] = 'Test BU'
        request.session['clientcode'] = 'TESTBU001'
        request.session.save()
        
        # Add message middleware
        from django.contrib.messages.middleware import MessageMiddleware
        message_middleware = MessageMiddleware(lambda x: None)
        message_middleware.process_request(request)
        
        # Add auth middleware
        auth_middleware = AuthenticationMiddleware(lambda x: None)
        auth_middleware.process_request(request)
        request.user = self.user

    @patch('apps.schedhuler.views._get_job')
    @patch('apps.schedhuler.views.sutils.create_job')
    def test_run_scheduler_success(self, mock_create_job, mock_get_job):
        mock_get_job.return_value = {
            'id': 1,
            'other_info': {'is_randomized': False, 'isdynamic': False}
        }
        mock_create_job.return_value = ({'status': 'success'}, None)
        
        post_data = {
            'job_id': '1',
            'action': 'schedule',
            'checkpoints': '[]'
        }
        
        request = self.factory.post('/schedhuler/run-scheduler/', post_data)
        self.add_session_to_request(request)
        
        from apps.schedhuler.views import run_internal_tour_scheduler
        response = run_internal_tour_scheduler(request)
        
        self.assertIsInstance(response, JsonResponse)

    def test_run_scheduler_no_job_id(self):
        post_data = {
            'action': 'schedule',
            'checkpoints': '[]'
        }
        
        request = self.factory.post('/schedhuler/run-scheduler/', post_data)
        self.add_session_to_request(request)
        
        from apps.schedhuler.views import run_internal_tour_scheduler
        response = run_internal_tour_scheduler(request)
        
        self.assertEqual(response.status_code, 404)

    @patch('apps.schedhuler.views._get_job')
    def test_run_scheduler_job_not_found(self, mock_get_job):
        mock_get_job.return_value = None
        
        post_data = {
            'job_id': '999',
            'action': 'schedule',
            'checkpoints': '[]'
        }
        
        request = self.factory.post('/schedhuler/run-scheduler/', post_data)
        self.add_session_to_request(request)
        
        from apps.schedhuler.views import run_internal_tour_scheduler
        response = run_internal_tour_scheduler(request)
        
        self.assertEqual(response.status_code, 404)


class GetCronDatetimeTestCase(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()

    def test_get_cron_datetime_valid_cron(self):
        request = self.factory.get('/schedhuler/cron-datetime/?cron=0 * * * *')
        
        from apps.schedhuler.views import get_cron_datetime
        
        # Mock datetime.now() to return a fixed datetime
        with patch('apps.schedhuler.views.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 9, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            with patch('croniter.croniter') as mock_croniter:
                mock_iter = Mock()
                mock_iter.get_next.side_effect = [
                    datetime(2024, 1, 1, 10, 0),
                    datetime(2024, 1, 1, 11, 0),
                    datetime(2024, 1, 2, 10, 0)  # This will be beyond enddtz
                ]
                mock_croniter.return_value = mock_iter
                
                response = get_cron_datetime(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)

    def test_get_cron_datetime_invalid_cron(self):
        request = self.factory.get('/schedhuler/cron-datetime/?cron=invalid_cron')
        
        from apps.schedhuler.views import get_cron_datetime
        
        with patch('croniter.croniter', side_effect=Exception("Bad cron")):
            response = get_cron_datetime(request)
        
        self.assertEqual(response.status_code, 404)

    def test_get_cron_datetime_invalid_method(self):
        request = self.factory.post('/schedhuler/cron-datetime/')
        
        from apps.schedhuler.views import get_cron_datetime
        from django.http import Http404
        
        # The view returns Http404 class, not an instance
        response = get_cron_datetime(request)
        self.assertEqual(response, Http404)