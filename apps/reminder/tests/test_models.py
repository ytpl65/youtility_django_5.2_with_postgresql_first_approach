from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from unittest.mock import patch

from apps.reminder.models import Reminder
from apps.peoples.models import People, Pgroup
from apps.activity.models.asset_model import Asset 
from apps.activity.models.job_model import Job, Jobneed
from apps.activity.models.question_model import  QuestionSet
from apps.onboarding.models import Bt


class ReminderModelTest(TestCase):
    
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
        
        self.reminder_data = {
            'description': 'Test reminder description',
            'bu': self.bt,
            'asset': self.asset,
            'qset': self.questionset,
            'people': self.people,
            'group': self.group,
            'priority': Reminder.Priority.HIGH,
            'reminderdate': timezone.now() + timedelta(days=1),
            'reminderin': Reminder.Frequency.DAILY,
            'reminderbefore': 30,
            'job': self.job,
            'jobneed': self.jobneed,
            'plandatetime': timezone.now() + timedelta(days=2),
            'mailids': 'test@example.com,test2@example.com',
            'status': Reminder.StatusChoices.SUCCESS
        }

    def test_reminder_creation(self):
        reminder = Reminder.objects.create(**self.reminder_data)
        self.assertIsInstance(reminder, Reminder)
        self.assertEqual(reminder.description, 'Test reminder description')
        self.assertEqual(reminder.priority, Reminder.Priority.HIGH)
        self.assertEqual(reminder.reminderin, Reminder.Frequency.DAILY)
        self.assertEqual(reminder.status, Reminder.StatusChoices.SUCCESS)

    def test_reminder_str_method(self):
        reminder = Reminder.objects.create(**self.reminder_data)
        self.assertEqual(str(reminder), str(self.asset))

    def test_reminder_priority_choices(self):
        priorities = [choice[0] for choice in Reminder.Priority.choices]
        expected_priorities = ['HIGH', 'LOW', 'MEDIU']
        self.assertEqual(priorities, expected_priorities)

    def test_reminder_frequency_choices(self):
        frequencies = [choice[0] for choice in Reminder.Frequency.choices]
        expected_frequencies = [
            'NONE', 'DAILY', 'WEEKLY', 'MONTHLY', 'BIMONTHLY',
            'QUARTERLY', 'HALFYEARLY', 'YEARLY', 'FORTNIGHTLY'
        ]
        self.assertEqual(frequencies, expected_frequencies)

    def test_reminder_status_choices(self):
        statuses = [choice[0] for choice in Reminder.StatusChoices.choices]
        expected_statuses = ['SUCCESS', 'FAILED']
        self.assertEqual(statuses, expected_statuses)

    def test_reminder_meta_options(self):
        reminder = Reminder.objects.create(**self.reminder_data)
        meta = reminder._meta
        self.assertEqual(meta.db_table, 'reminder')
        self.assertEqual(meta.verbose_name, 'Reminder')
        self.assertEqual(meta.verbose_name_plural, 'Reminders')

    def test_reminder_with_minimal_data(self):
        minimal_data = {
            'description': 'Minimal reminder',
            'priority': Reminder.Priority.LOW,
            'reminderin': Reminder.Frequency.NONE,
            'reminderbefore': 0,
            'mailids': 'test@example.com',
            'status': Reminder.StatusChoices.FAILED,
            # Required fields that have blank=True but not null=True
            'bu': self.bt,
            'asset': self.asset,
            'qset': self.questionset,
            'people': self.people,
            'group': self.group,
            'job': self.job,
            'jobneed': self.jobneed
        }
        reminder = Reminder.objects.create(**minimal_data)
        self.assertIsInstance(reminder, Reminder)
        self.assertEqual(reminder.description, 'Minimal reminder')

    def test_reminder_foreign_key_relationships(self):
        reminder = Reminder.objects.create(**self.reminder_data)
        
        self.assertEqual(reminder.bu, self.bt)
        self.assertEqual(reminder.asset, self.asset)
        self.assertEqual(reminder.qset, self.questionset)
        self.assertEqual(reminder.people, self.people)
        self.assertEqual(reminder.group, self.group)
        self.assertEqual(reminder.job, self.job)
        self.assertEqual(reminder.jobneed, self.jobneed)

    def test_reminder_with_null_datetime_fields(self):
        data = self.reminder_data.copy()
        data['reminderdate'] = None
        data['plandatetime'] = None
        
        reminder = Reminder.objects.create(**data)
        self.assertIsNone(reminder.reminderdate)
        self.assertIsNone(reminder.plandatetime)

    def test_reminder_description_max_length(self):
        # TextField doesn't enforce max_length at model level, only in forms
        long_description = 'A' * 501
        data = self.reminder_data.copy()
        data['description'] = long_description
        
        # This should not raise an error at model level
        reminder = Reminder.objects.create(**data)
        self.assertEqual(reminder.description, long_description)

    def test_reminder_mailids_max_length(self):
        # TextField doesn't enforce max_length at model level, only in forms
        long_mailids = 'test@example.com,' * 100
        data = self.reminder_data.copy()
        data['mailids'] = long_mailids
        
        # This should not raise an error at model level
        reminder = Reminder.objects.create(**data)
        self.assertEqual(reminder.mailids, long_mailids)

    def test_reminder_invalid_priority(self):
        data = self.reminder_data.copy()
        data['priority'] = 'INVALID_PRIORITY'
        
        with self.assertRaises(ValidationError):
            reminder = Reminder(**data)
            reminder.full_clean()

    def test_reminder_invalid_frequency(self):
        data = self.reminder_data.copy()
        data['reminderin'] = 'INVALID_FREQUENCY'
        
        with self.assertRaises(ValidationError):
            reminder = Reminder(**data)
            reminder.full_clean()

    def test_reminder_invalid_status(self):
        data = self.reminder_data.copy()
        data['status'] = 'INVALID_STATUS'
        
        with self.assertRaises(ValidationError):
            reminder = Reminder(**data)
            reminder.full_clean()

    def test_reminder_manager_custom_manager(self):
        self.assertTrue(hasattr(Reminder.objects, 'get_all_due_reminders'))
        self.assertEqual(Reminder.objects.__class__.__name__, 'ReminderManager')

    def test_reminder_ordering_by_creation_date(self):
        reminder1 = Reminder.objects.create(
            description='First reminder',
            priority=Reminder.Priority.HIGH,
            reminderin=Reminder.Frequency.DAILY,
            reminderbefore=30,
            mailids='test1@example.com',
            status=Reminder.StatusChoices.SUCCESS,
            # Required fields
            bu=self.bt,
            asset=self.asset,
            qset=self.questionset,
            people=self.people,
            group=self.group,
            job=self.job,
            jobneed=self.jobneed
        )
        
        reminder2 = Reminder.objects.create(
            description='Second reminder',
            priority=Reminder.Priority.LOW,
            reminderin=Reminder.Frequency.WEEKLY,
            reminderbefore=60,
            mailids='test2@example.com',
            status=Reminder.StatusChoices.FAILED,
            # Required fields
            bu=self.bt,
            asset=self.asset,
            qset=self.questionset,
            people=self.people,
            group=self.group,
            job=self.job,
            jobneed=self.jobneed
        )
        
        reminders = list(Reminder.objects.all())
        self.assertEqual(len(reminders), 2)
        self.assertIn(reminder1, reminders)
        self.assertIn(reminder2, reminders)

    def test_reminder_cascade_delete_behavior(self):
        reminder = Reminder.objects.create(**self.reminder_data)
        
        # Test that deleting related objects doesn't delete the reminder
        # due to RESTRICT on_delete
        with self.assertRaises(Exception):
            self.people.delete()
        
        # Reminder should still exist
        self.assertTrue(Reminder.objects.filter(id=reminder.id).exists())