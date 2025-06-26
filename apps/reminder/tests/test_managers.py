from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

from apps.activity.models.job_model import Job, Jobneed
from apps.reminder.models import Reminder
from apps.reminder.managers import ReminderManager
from apps.peoples.models import People, Pgroup
from apps.activity.models.asset_model import Asset 
from apps.activity.models.question_model import QuestionSet
from apps.onboarding.models import Bt


class ReminderManagerTest(TestCase):
    
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
            bucode="TESTBU001",
            buname="Test BU"
        )
        
        self.asset = Asset.objects.create(
            assetcode="TESTASSET001",
            assetname="Test Asset",
            iscritical=False
        )
        
        self.job = Job.objects.create(
            jobname="Test Job",
            jobdesc="Test Job Description",
            fromdate=timezone.now(),
            uptodate=timezone.now() + timedelta(days=30),
            planduration=60,
            gracetime=15,
            expirytime=120,
            priority=Job.Priority.MEDIUM,
            seqno=1,
            scantype=Job.Scantype.SKIP
        )
        
        self.jobneed = Jobneed.objects.create(
            jobdesc="Test Jobneed",
            gracetime=30,
            priority=Jobneed.Priority.MEDIUM,
            seqno=1
        )
        
        self.questionset = QuestionSet.objects.create(
            qsetname="Test Questionset"
        )

    def test_reminder_manager_instance(self):
        self.assertIsInstance(Reminder.objects, ReminderManager)
        self.assertTrue(hasattr(Reminder.objects, 'get_all_due_reminders'))

    def test_get_all_due_reminders_with_future_reminders(self):
        # Create reminders with future reminder dates
        future_date = timezone.now() + timedelta(days=1)
        
        reminder1 = Reminder.objects.create(
            description='Future reminder 1',
            bu=self.bt,
            asset=self.asset,
            qset=self.questionset,
            people=self.people,
            group=self.group,
            job=self.job,
            jobneed=self.jobneed,
            priority=Reminder.Priority.HIGH,
            reminderdate=future_date,
            reminderin=Reminder.Frequency.DAILY,
            reminderbefore=30,
            plandatetime=future_date + timedelta(hours=2),
            mailids='test@example.com',
            status=Reminder.StatusChoices.FAILED
        )
        
        reminder2 = Reminder.objects.create(
            description='Future reminder 2',
            bu=self.bt,
            asset=self.asset,
            qset=self.questionset,
            people=self.people,
            group=self.group,
            job=self.job,
            jobneed=self.jobneed,
            priority=Reminder.Priority.LOW,
            reminderdate=future_date + timedelta(hours=1),
            reminderin=Reminder.Frequency.WEEKLY,
            reminderbefore=60,
            plandatetime=future_date + timedelta(hours=3),
            mailids='test2@example.com',
            status=Reminder.StatusChoices.FAILED
        )
        
        # Test the manager method
        due_reminders = Reminder.objects.get_all_due_reminders()
        
        self.assertEqual(due_reminders.count(), 2)
        
        # Check that the queryset contains the expected values
        reminder_ids = [r['id'] for r in due_reminders]
        self.assertIn(reminder1.id, reminder_ids)
        self.assertIn(reminder2.id, reminder_ids)

    def test_get_all_due_reminders_excludes_success_status(self):
        future_date = timezone.now() + timedelta(days=1)
        
        # Create reminder with SUCCESS status - should be excluded
        Reminder.objects.create(
            description='Success reminder',
            bu=self.bt,
            asset=self.asset,
            qset=self.questionset,
            people=self.people,
            group=self.group,
            job=self.job,
            jobneed=self.jobneed,
            priority=Reminder.Priority.HIGH,
            reminderdate=future_date,
            reminderin=Reminder.Frequency.DAILY,
            reminderbefore=30,
            plandatetime=future_date + timedelta(hours=2),
            mailids='test@example.com',
            status=Reminder.StatusChoices.SUCCESS
        )
        
        # Create reminder with FAILED status - should be included
        failed_reminder = Reminder.objects.create(
            description='Failed reminder',
            bu=self.bt,
            asset=self.asset,
            qset=self.questionset,
            people=self.people,
            group=self.group,
            job=self.job,
            jobneed=self.jobneed,
            priority=Reminder.Priority.HIGH,
            reminderdate=future_date,
            reminderin=Reminder.Frequency.DAILY,
            reminderbefore=30,
            plandatetime=future_date + timedelta(hours=2),
            mailids='test@example.com',
            status=Reminder.StatusChoices.FAILED
        )
        
        due_reminders = Reminder.objects.get_all_due_reminders()
        
        self.assertEqual(due_reminders.count(), 1)
        self.assertEqual(due_reminders.first()['id'], failed_reminder.id)

    def test_get_all_due_reminders_excludes_past_reminders(self):
        past_date = timezone.now() - timedelta(days=1)
        future_date = timezone.now() + timedelta(days=1)
        
        # Create reminder with past date - should be excluded
        Reminder.objects.create(
            description='Past reminder',
            bu=self.bt,
            asset=self.asset,
            qset=self.questionset,
            people=self.people,
            group=self.group,
            job=self.job,
            jobneed=self.jobneed,
            priority=Reminder.Priority.HIGH,
            reminderdate=past_date,
            reminderin=Reminder.Frequency.DAILY,
            reminderbefore=30,
            plandatetime=past_date + timedelta(hours=2),
            mailids='test@example.com',
            status=Reminder.StatusChoices.FAILED
        )
        
        # Create reminder with future date - should be included
        future_reminder = Reminder.objects.create(
            description='Future reminder',
            bu=self.bt,
            asset=self.asset,
            qset=self.questionset,
            people=self.people,
            group=self.group,
            job=self.job,
            jobneed=self.jobneed,
            priority=Reminder.Priority.HIGH,
            reminderdate=future_date,
            reminderin=Reminder.Frequency.DAILY,
            reminderbefore=30,
            plandatetime=future_date + timedelta(hours=2),
            mailids='test@example.com',
            status=Reminder.StatusChoices.FAILED
        )
        
        due_reminders = Reminder.objects.get_all_due_reminders()
        
        self.assertEqual(due_reminders.count(), 1)
        self.assertEqual(due_reminders.first()['id'], future_reminder.id)

    def test_get_all_due_reminders_returns_expected_fields(self):
        future_date = timezone.now() + timedelta(days=1)
        
        reminder = Reminder.objects.create(
            description='Future reminder',
            bu=self.bt,
            asset=self.asset,
            qset=self.questionset,
            people=self.people,
            group=self.group,
            job=self.job,
            jobneed=self.jobneed,
            priority=Reminder.Priority.HIGH,
            reminderdate=future_date,
            reminderin=Reminder.Frequency.DAILY,
            reminderbefore=30,
            plandatetime=future_date + timedelta(hours=2),
            mailids='test@example.com',
            status=Reminder.StatusChoices.FAILED
        )
        
        due_reminders = Reminder.objects.get_all_due_reminders()
        
        self.assertEqual(due_reminders.count(), 1)
        
        reminder_data = due_reminders.first()
        expected_fields = [
            'rdate', 'pdate', 'job__jobname', 'bu__buname', 'asset__assetname',
            'job__jobdesc', 'qset__qsetname', 'priority', 'reminderin',
            'people__peoplename', 'cuser__peoplename', 'group__groupname',
            'people_id', 'group_id', 'cuser_id', 'muser_id', 'mailids',
            'muser__peoplename', 'id'
        ]
        
        for field in expected_fields:
            self.assertIn(field, reminder_data)

    def test_get_all_due_reminders_empty_result(self):
        # Don't create any reminders
        due_reminders = Reminder.objects.get_all_due_reminders()
        
        self.assertEqual(due_reminders.count(), 0)
        self.assertFalse(due_reminders.exists())

    def test_get_all_due_reminders_with_null_dates(self):
        # Create reminder with null reminder date
        reminder = Reminder.objects.create(
            description='Null date reminder',
            bu=self.bt,
            asset=self.asset,
            qset=self.questionset,
            people=self.people,
            group=self.group,
            job=self.job,
            jobneed=self.jobneed,
            priority=Reminder.Priority.HIGH,
            reminderdate=None,
            reminderin=Reminder.Frequency.DAILY,
            reminderbefore=30,
            plandatetime=None,
            mailids='test@example.com',
            status=Reminder.StatusChoices.FAILED
        )
        
        due_reminders = Reminder.objects.get_all_due_reminders()
        
        # Should be excluded because reminderdate is None
        self.assertEqual(due_reminders.count(), 0)

    def test_get_all_due_reminders_select_related(self):
        future_date = timezone.now() + timedelta(days=1)
        
        reminder = Reminder.objects.create(
            description='Future reminder',
            bu=self.bt,
            asset=self.asset,
            qset=self.questionset,
            people=self.people,
            group=self.group,
            job=self.job,
            jobneed=self.jobneed,
            priority=Reminder.Priority.HIGH,
            reminderdate=future_date,
            reminderin=Reminder.Frequency.DAILY,
            reminderbefore=30,
            plandatetime=future_date + timedelta(hours=2),
            mailids='test@example.com',
            status=Reminder.StatusChoices.FAILED
        )
        
        # Test that the method uses select_related for optimization
        with patch.object(Reminder.objects, 'select_related') as mock_select_related:
            # Mock the chaining of queryset methods
            mock_queryset = Mock()
            mock_queryset.annotate.return_value = mock_queryset
            mock_queryset.filter.return_value = mock_queryset
            mock_queryset.values.return_value = mock_queryset
            mock_queryset.distinct.return_value = []
            mock_select_related.return_value = mock_queryset
            
            Reminder.objects.get_all_due_reminders()
            
            mock_select_related.assert_called_once_with(
                'bt', 'job', 'asset', 'qset', 'pgroup', 'people'
            )

    def test_get_all_due_reminders_distinct(self):
        future_date = timezone.now() + timedelta(days=1)
        
        # Create multiple reminders with same properties to test distinct
        for i in range(3):
            Reminder.objects.create(
                description=f'Future reminder {i}',
                bu=self.bt,
                asset=self.asset,
                qset=self.questionset,
                people=self.people,
                group=self.group,
                job=self.job,
            jobneed=self.jobneed,
                priority=Reminder.Priority.HIGH,
                reminderdate=future_date,
                reminderin=Reminder.Frequency.DAILY,
                reminderbefore=30,
                plandatetime=future_date + timedelta(hours=2),
                mailids='test@example.com',
                status=Reminder.StatusChoices.FAILED
            )
        
        due_reminders = Reminder.objects.get_all_due_reminders()
        
        # Should return 3 distinct reminders
        self.assertEqual(due_reminders.count(), 3)

    def test_manager_use_in_migrations(self):
        self.assertTrue(ReminderManager.use_in_migrations)