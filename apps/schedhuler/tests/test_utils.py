from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime, timedelta
import json

from apps.schedhuler import utils as sutils
from apps.activity.models.job_model import Job, Jobneed, JobneedDetails
from apps.activity.models.asset_model import Asset 
from apps.activity.models.question_model import QuestionSet
from apps.peoples.models import People, Pgroup
from apps.onboarding.models import Bt


class CreateJobTestCase(TransactionTestCase):
    
    def setUp(self):
        self.people = People.objects.create(
            peoplename="Test Person",
            email="test@example.com",
            peoplecode="TEST001",
            dateofbirth="1990-01-01"
        )
        
        self.group = Pgroup.objects.create(
            groupname="Test Group"
        )
        
        self.bt = Bt.objects.create(
            buname="Test BU",
            bucode="TESTBU001"
        )
        
        self.asset = Asset.objects.create(
            assetcode="TESTASSET001",
            assetname="Test Asset",
            iscritical=False
        )
        
        self.questionset = QuestionSet.objects.create(
            qsetname="Test Questionset"
        )

    @patch('apps.schedhuler.utils.filter_jobs')
    @patch('apps.schedhuler.utils.process_job')
    def test_create_job_success(self, mock_process_job, mock_filter_jobs):
        job_data = {
            'id': 1,
            'jobname': 'Test Job',
            'cron': '0 8 * * *',
            'ctzoffset': 330,
            'cdtz': timezone.now(),
            'mdtz': timezone.now(),
            'fromdate': timezone.now(),
            'uptodate': timezone.now() + timedelta(days=30),
            'lastgeneratedon': timezone.now() - timedelta(days=1)
        }
        
        mock_filter_jobs.return_value = [job_data]
        mock_process_job.return_value = {'msg': 'Success'}
        
        response, result = sutils.create_job()
        
        self.assertIsNotNone(response)
        self.assertIn('story', result)

    @patch('apps.schedhuler.utils.filter_jobs')
    def test_create_job_no_jobs(self, mock_filter_jobs):
        mock_filter_jobs.return_value = []
        
        response, result = sutils.create_job()
        
        self.assertIn('story', result)

    @patch('apps.schedhuler.utils.filter_jobs')
    @patch('apps.schedhuler.utils.process_job')
    def test_create_job_with_jobids(self, mock_process_job, mock_filter_jobs):
        job_data = {
            'id': 1,
            'jobname': 'Test Job',
            'cron': '0 8 * * *'
        }
        
        mock_filter_jobs.return_value = [job_data]
        mock_process_job.return_value = {'msg': 'Success'}
        
        response, result = sutils.create_job([1])
        
        mock_filter_jobs.assert_called_once_with([1])


class FilterJobsTestCase(TestCase):
    
    def setUp(self):
        self.asset = Asset.objects.create(
            assetcode="TESTASSET001",
            assetname="Test Asset",
            iscritical=False
        )

    @patch('apps.schedhuler.utils.Job.objects.filter')
    def test_filter_jobs_with_jobids(self, mock_filter):
        mock_queryset = Mock()
        mock_queryset.select_related.return_value.values.return_value = [{'id': 1}]
        mock_filter.return_value = mock_queryset
        
        result = sutils.filter_jobs([1, 2])
        
        self.assertIsInstance(result, list)

    @patch('apps.schedhuler.utils.Job.objects.filter')
    def test_filter_jobs_without_jobids(self, mock_filter):
        mock_queryset = Mock()
        mock_queryset.select_related.return_value.values.return_value = []
        mock_filter.return_value = mock_queryset
        
        result = sutils.filter_jobs()
        
        self.assertIsInstance(result, list)


class ProcessJobTestCase(TestCase):
    
    def setUp(self):
        self.job_data = {
            'id': 1,
            'jobname': 'Test Job',
            'cron': '0 8 * * *',
            'ctzoffset': 330,
            'cdtz': timezone.now(),
            'mdtz': timezone.now(),
            'fromdate': timezone.now(),
            'uptodate': timezone.now() + timedelta(days=30),
            'lastgeneratedon': timezone.now() - timedelta(days=1)
        }

    @patch('apps.schedhuler.utils.calculate_startdtz_enddtz')
    @patch('apps.schedhuler.utils.get_datetime_list')
    @patch('apps.schedhuler.utils.insert_into_jn_and_jnd')
    def test_process_job_success(self, mock_insert, mock_get_dt, mock_calc_dt):
        mock_calc_dt.return_value = (timezone.now(), timezone.now() + timedelta(hours=24))
        mock_get_dt.return_value = ([timezone.now()], True, {})
        mock_insert.return_value = ('success', {'msg': 'Success'})
        
        result = {'story': []}
        response = sutils.process_job(self.job_data, result)
        
        self.assertIsNotNone(response)

    @patch('apps.schedhuler.utils.calculate_startdtz_enddtz')
    @patch('apps.schedhuler.utils.get_datetime_list')
    def test_process_job_invalid_cron(self, mock_get_dt, mock_calc_dt):
        mock_calc_dt.return_value = (timezone.now(), timezone.now() + timedelta(hours=24))
        mock_get_dt.return_value = ([], False, {'msg': 'Invalid cron'})
        
        result = {'story': []}
        response = sutils.process_job(self.job_data, result)
        
        self.assertEqual(response['msg'], 'Invalid cron expression for job 1: 0 8 * * *')

    @patch('apps.schedhuler.utils.calculate_startdtz_enddtz')
    @patch('apps.schedhuler.utils.get_datetime_list')
    def test_process_job_no_datetime(self, mock_get_dt, mock_calc_dt):
        start_dt = timezone.now()
        end_dt = timezone.now() + timedelta(hours=24)
        mock_calc_dt.return_value = (start_dt, end_dt)
        mock_get_dt.return_value = ([], True, {})
        
        result = {'story': []}
        response = sutils.process_job(self.job_data, result)
        
        self.assertIn('Jobs are scheduled between', response['msg'])


class CalculateStartdtzEnddtzTestCase(TestCase):
    
    def test_calculate_startdtz_enddtz_basic(self):
        now = timezone.now()
        job = {
            'id': 1,
            'ctzoffset': 330,
            'cdtz': now - timedelta(days=1),
            'mdtz': now - timedelta(days=1),
            'fromdate': now - timedelta(days=1),
            'uptodate': now + timedelta(days=30),
            'lastgeneratedon': now - timedelta(days=1)
        }
        
        start_dt, end_dt = sutils.calculate_startdtz_enddtz(job)
        
        self.assertIsInstance(start_dt, datetime)
        self.assertIsInstance(end_dt, datetime)
        self.assertTrue(start_dt < end_dt)

    @patch('apps.schedhuler.utils.delete_old_jobs')
    def test_calculate_startdtz_enddtz_modified_job(self, mock_delete):
        now = timezone.now()
        job = {
            'id': 1,
            'ctzoffset': 330,
            'cdtz': now - timedelta(days=1),
            'mdtz': now,  # Modified time is newer than created time
            'fromdate': now - timedelta(days=1),
            'uptodate': now + timedelta(days=30),
            'lastgeneratedon': now - timedelta(days=1)
        }
        
        start_dt, end_dt = sutils.calculate_startdtz_enddtz(job)
        
        mock_delete.assert_called_once_with(1)


class GetDatetimeListTestCase(TestCase):
    
    @patch('croniter.croniter')
    def test_get_datetime_list_valid_cron(self, mock_croniter_class):
        mock_iter = Mock()
        mock_iter.get_next.side_effect = [
            datetime(2024, 1, 1, 8, 0),
            datetime(2024, 1, 2, 8, 0),
            datetime(2024, 1, 3, 8, 0)  # This will exceed end date
        ]
        mock_croniter_class.return_value = mock_iter
        
        start_dt = datetime(2024, 1, 1, 0, 0)
        end_dt = datetime(2024, 1, 2, 23, 59)
        
        dt_list, is_valid, resp = sutils.get_datetime_list('0 8 * * *', start_dt, end_dt, {})
        
        self.assertTrue(is_valid)
        self.assertEqual(len(dt_list), 2)

    @patch('croniter.croniter')
    def test_get_datetime_list_invalid_cron(self, mock_croniter_class):
        from croniter import CroniterBadCronError
        mock_croniter_class.side_effect = CroniterBadCronError("Bad cron")
        
        start_dt = datetime(2024, 1, 1, 0, 0)
        end_dt = datetime(2024, 1, 2, 23, 59)
        
        dt_list, is_valid, resp = sutils.get_datetime_list('invalid', start_dt, end_dt, {})
        
        self.assertFalse(is_valid)
        self.assertEqual(dt_list, [])
        self.assertIn('errors', resp)


class InsertIntoJnAndJndTestCase(TransactionTestCase):
    
    def setUp(self):
        self.asset = Asset.objects.create(
            assetcode="TESTASSET001",
            assetname="Test Asset",
            iscritical=False
        )
        
        self.people = People.objects.create(
            peoplename="Test Person",
            email="test@example.com",
            peoplecode="TEST001",
            dateofbirth="1990-01-01"
        )
        
        self.group = Pgroup.objects.create(
            groupname="Test Group"
        )
        
        self.questionset = QuestionSet.objects.create(
            qsetname="Test Questionset"
        )

    @patch('apps.schedhuler.utils.utils.get_or_create_none_jobneed')
    @patch('apps.schedhuler.utils.utils.get_or_create_none_people')
    @patch('apps.schedhuler.utils.Asset.objects.get')
    @patch('apps.schedhuler.utils.insert_into_jn_for_parent')
    @patch('apps.schedhuler.utils.insert_update_jobneeddetails')
    @patch('apps.schedhuler.utils.update_lastgeneratedon')
    def test_insert_into_jn_and_jnd_success(self, mock_update_last, mock_insert_jnd, 
                                           mock_insert_jn, mock_get_asset, 
                                           mock_get_none_people, mock_get_none_jn):
        mock_get_none_jn.return_value = Mock(id=1)
        mock_get_none_people.return_value = Mock(id=1)
        
        mock_asset = Mock()
        mock_asset.asset_json = {'multifactor': 1}
        mock_get_asset.return_value = mock_asset
        
        mock_jobneed = Mock()
        mock_jobneed.id = 1
        mock_jobneed.other_info = {}
        mock_insert_jn.return_value = mock_jobneed
        
        job = {
            'id': 1,
            'jobname': 'Test Job',
            'identifier': 'TASK',
            'asset_id': self.asset.id,
            'people_id': self.people.id,
            'pgroup_id': self.group.id,
            'qset_id': self.questionset.id,
            'gracetime': 5,
            'planduration': 60,
            'expirytime': 10,
            'sgroup__groupname': 'Test Site Group',
            'sgroup_id': 1,
            'client_id': 1,
            'cuser_id': 1,
            'muser_id': 1,
            'ticketcategory_id': 1,
            'frequency': 'NONE',
            'bu_id': 1,
            'scantype': 'QR',
            'ctzoffset': 330,
            'priority': 'HIGH'
        }
        
        dt_list = [timezone.now()]
        
        with patch('apps.schedhuler.utils.utils.to_utc', return_value=dt_list):
            status, resp = sutils.insert_into_jn_and_jnd(job, dt_list, {})
        
        self.assertEqual(status, 'success')
        self.assertIn('msg', resp)

    def test_insert_into_jn_and_jnd_empty_dt(self):
        job = {'id': 1}
        dt_list = []
        
        status, resp = sutils.insert_into_jn_and_jnd(job, dt_list, {})
        
        self.assertIsNone(status)


class JobFieldsTestCase(TestCase):
    
    def test_job_fields_internal_tour(self):
        job = {
            'id': 1,
            'jobname': 'Test Job',
            'cron': '0 8 * * *',
            'identifier': 'INTERNALTOUR',
            'priority': 'HIGH',
            'pgroup_id': 1,
            'geofence_id': 1,
            'ticketcategory_id': 1,
            'fromdate': datetime(2024, 1, 1),
            'uptodate': datetime(2024, 12, 31),
            'planduration': 60,
            'gracetime': 5,
            'frequency': 'DAILY',
            'people_id': 1,
            'scantype': 'QR',
            'ctzoffset': 330,
            'bu_id': 1,
            'client_id': 1,
            'lastgeneratedon': datetime(2024, 1, 1)
        }
        
        checkpoint = {
            'expirytime': 10,
            'qsetname': 'Test QSet',
            'qsetid': 1,
            'assetid': 1,
            'seqno': 1,
            'starttime': '08:00',
            'endtime': '17:00'
        }
        
        result = sutils.job_fields(job, checkpoint)
        
        self.assertIn('jobname', result)
        self.assertIn('jobdesc', result)
        self.assertIn('expirytime', result)
        self.assertEqual(result['expirytime'], 10)

    def test_job_fields_external_tour(self):
        job = {
            'id': 1,
            'jobname': 'Test Job',
            'cron': '0 8 * * *',
            'identifier': 'EXTERNALTOUR',
            'priority': 'HIGH',
            'pgroup_id': 1,
            'geofence_id': 1,
            'ticketcategory_id': 1,
            'fromdate': datetime(2024, 1, 1),
            'uptodate': datetime(2024, 12, 31),
            'planduration': 60,
            'gracetime': 5,
            'frequency': 'DAILY',
            'people_id': 1,
            'scantype': 'QR',
            'ctzoffset': 330,
            'bu_id': 1,
            'client_id': 1,
            'lastgeneratedon': datetime(2024, 1, 1),
            'other_info': {
                'istimebound': True,
                'is_randomized': False,
                'tour_frequency': 1
            }
        }
        
        checkpoint = {
            'expirytime': 10,
            'qsetname': 'Test QSet',
            'qsetid': 1,
            'assetid': 1,
            'seqno': 1,
            'starttime': '08:00',
            'endtime': '17:00',
            'bu__buname': 'Test Site',
            'distance': 5.5,
            'breaktime': 15
        }
        
        result = sutils.job_fields(job, checkpoint, external=True)
        
        self.assertIn('other_info', result)
        self.assertIn('distance', result['other_info'])
        self.assertIn('breaktime', result['other_info'])


class DeleteFromJobTestCase(TestCase):
    
    def setUp(self):
        self.people = People.objects.create(
            peoplename="Test Person",
            email="test@example.com",
            peoplecode="TEST001",
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
        
        self.parent_job = Job.objects.create(
            jobname="Parent Job",
            jobdesc="Parent Description",
            people=self.people,
            fromdate=timezone.now(),
            uptodate=timezone.now() + timedelta(days=30),
            planduration=60,
            gracetime=15,
            expirytime=120,
            priority=Job.Priority.MEDIUM,
            seqno=1,
            scantype=Job.Scantype.SKIP
        )
        
        self.child_job = Job.objects.create(
            jobname="Child Job",
            jobdesc="Child Description",
            people=self.people,
            parent=self.parent_job,
            asset=self.asset,
            qset=self.questionset,
            fromdate=timezone.now(),
            uptodate=timezone.now() + timedelta(days=30),
            planduration=60,
            gracetime=15,
            expirytime=120,
            priority=Job.Priority.MEDIUM,
            seqno=2,
            scantype=Job.Scantype.SKIP
        )

    def test_delete_from_job_success(self):
        sutils.delete_from_job(
            self.parent_job.id, 
            self.asset.id, 
            self.questionset.id
        )
        
        self.assertFalse(Job.objects.filter(id=self.child_job.id).exists())

    def test_delete_from_job_not_found(self):
        with self.assertRaises(Job.DoesNotExist):
            sutils.delete_from_job(999, 999, 999)


class DeleteFromJobneedTestCase(TransactionTestCase):
    
    def setUp(self):
        self.people = People.objects.create(
            peoplename="Test Person",
            email="test@example.com",
            peoplecode="TEST001",
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
        
        self.job = Job.objects.create(
            jobname="Test Job",
            jobdesc="Test Description",
            people=self.people,
            fromdate=timezone.now(),
            uptodate=timezone.now() + timedelta(days=30),
            planduration=60,
            gracetime=15,
            expirytime=120,
            priority=Job.Priority.MEDIUM,
            seqno=1,
            scantype=Job.Scantype.SKIP
        )
        
        self.parent_jobneed = Jobneed.objects.create(
            jobdesc="Parent Jobneed",
            job=self.job,
            people=self.people,
            asset=self.asset,
            qset=self.questionset,
            gracetime=15,
            priority=Jobneed.Priority.MEDIUM,
            seqno=1
        )
        
        self.child_jobneed = Jobneed.objects.create(
            jobdesc="Child Jobneed",
            job=self.job,
            people=self.people,
            parent=self.parent_jobneed,
            asset=self.asset,
            qset=self.questionset,
            gracetime=15,
            priority=Jobneed.Priority.MEDIUM,
            seqno=2
        )

    def test_delete_from_jobneed_success(self):
        sutils.delete_from_jobneed(
            self.parent_jobneed.id,
            self.asset.id,
            self.questionset.id
        )
        
        self.assertFalse(Jobneed.objects.filter(id=self.child_jobneed.id).exists())

    def test_delete_from_jobneed_not_found(self):
        with self.assertRaises(Jobneed.DoesNotExist):
            sutils.delete_from_jobneed(999, 999, 999)


class UpdateLastGeneratedonTestCase(TestCase):
    
    def setUp(self):
        self.people = People.objects.create(
            peoplename="Test Person",
            email="test@example.com",
            peoplecode="TEST001",
            dateofbirth="1990-01-01"
        )
        
        self.job = Job.objects.create(
            jobname="Test Job",
            jobdesc="Test Description",
            people=self.people,
            fromdate=timezone.now(),
            uptodate=timezone.now() + timedelta(days=30),
            planduration=60,
            gracetime=15,
            expirytime=120,
            priority=Job.Priority.MEDIUM,
            seqno=1,
            scantype=Job.Scantype.SKIP
        )

    def test_update_lastgeneratedon_success(self):
        new_date = timezone.now()
        job_data = {'id': self.job.id}
        
        sutils.update_lastgeneratedon(job_data, new_date)
        
        self.job.refresh_from_db()
        self.assertIsNotNone(self.job.lastgeneratedon)

    def test_update_lastgeneratedon_job_not_found(self):
        new_date = timezone.now()
        job_data = {'id': 999}
        
        # The function doesn't raise an error, it just logs a warning
        sutils.update_lastgeneratedon(job_data, new_date)
        
        # Verify the job doesn't exist
        self.assertFalse(Job.objects.filter(id=999).exists())


class ToLocalTestCase(TestCase):
    
    def test_to_local_conversion(self):
        from django.utils import timezone as django_timezone
        utc_time = django_timezone.now()
        
        # Don't mock get_current_timezone, let it return the actual timezone
        result = sutils.to_local(utc_time)
        
        self.assertIsInstance(result, str)
        self.assertRegex(result, r'\d{2}-\w{3}-\d{4} \d{2}:\d{2}')


class GetReadableDatesTestCase(TestCase):
    
    def test_get_readable_dates_list(self):
        dt_list = [
            datetime(2024, 1, 1, 8, 0),
            datetime(2024, 1, 2, 8, 0)
        ]
        
        result = sutils.get_readable_dates(dt_list)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], '01-Jan-2024 08:00')

    def test_get_readable_dates_not_list(self):
        dt = datetime(2024, 1, 1, 8, 0)
        
        result = sutils.get_readable_dates(dt)
        
        self.assertIsNone(result)