from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
import uuid

from apps.y_helpdesk.models import Ticket, EscalationMatrix, TicketNumberField, ticket_defaults
from apps.peoples.models import People, Pgroup
from apps.activity.models.asset_model import Asset 
from apps.activity.models.job_model import Job, QuestionSet 
from apps.activity.models.location_model import Location
from apps.onboarding.models import Bt

User = get_user_model()


class TicketNumberFieldTest(TestCase):
    
    def setUp(self):
        self.field = TicketNumberField()

    def test_get_next_value_new_record(self):
        # Mock model with no existing records
        mock_model = type('MockModel', (), {})
        mock_model.objects = type('MockManager', (), {})()
        mock_queryset = type('MockQuerySet', (), {'first': lambda self: None})()
        mock_model.objects.order_by = lambda x: mock_queryset
        
        result = self.field.get_next_value(mock_model, True, None, 'default')
        
        self.assertEqual(result, 'T00001')

    def test_get_next_value_existing_records(self):
        # Mock model with existing records
        mock_last_ticket = type('MockTicket', (), {'id': 5})()
        mock_model = type('MockModel', (), {})
        mock_model.objects = type('MockManager', (), {})()
        mock_queryset = type('MockQuerySet', (), {'first': lambda self: mock_last_ticket})()
        mock_model.objects.order_by = lambda x: mock_queryset
        
        result = self.field.get_next_value(mock_model, True, None, 'default')
        
        self.assertEqual(result, 'T00006')

    def test_get_next_value_not_created(self):
        # Test when record is not being created (update operation)
        mock_model = type('MockModel', (), {})
        
        result = self.field.get_next_value(mock_model, False, 'existing_value', 'default')
        
        self.assertEqual(result, 'existing_value')


class TicketDefaultsTest(TestCase):
    
    def test_ticket_defaults(self):
        defaults = ticket_defaults()
        
        self.assertIsInstance(defaults, dict)
        self.assertIn('ticket_history', defaults)
        self.assertIsInstance(defaults['ticket_history'], list)
        self.assertEqual(len(defaults['ticket_history']), 0)


class TicketModelTest(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            loginid='testuser',
            password='testpass123',
            peoplecode='TEST001',
            peoplename='Test User',
            dateofbirth='1990-01-01',
            email='testuser@example.com'
        )
        
        self.people = People.objects.create(
            peoplename="Test Person",
            email="test@example.com",
            dateofbirth="1990-01-01",
            peoplecode="TEST001"
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
        
        self.location = Location.objects.create(
            loccode="TESTLOC001",
            locname="Test Location",
            iscritical=False
        )
        
        self.ticket_data = {
            'ticketdesc': 'Test ticket description',
            'assignedtopeople': self.people,
            'assignedtogroup': self.group,
            'comments': 'Test comments',
            'bu': self.bt,
            'client': self.bt,
            'priority': Ticket.Priority.HIGH,
            'asset': self.asset,
            'qset': self.questionset,
            'location': self.location,
            'status': Ticket.Status.NEW,
            'performedby': self.people,
            'ticketsource': Ticket.TicketSource.USERDEFINED
        }

    def test_ticket_creation(self):
        ticket = Ticket.objects.create(**self.ticket_data)
        
        self.assertIsInstance(ticket, Ticket)
        self.assertEqual(ticket.ticketdesc, 'Test ticket description')
        self.assertEqual(ticket.priority, Ticket.Priority.HIGH)
        self.assertEqual(ticket.status, Ticket.Status.NEW)
        self.assertIsNotNone(ticket.uuid)

    def test_ticket_str_method(self):
        ticket = Ticket.objects.create(**self.ticket_data)
        
        self.assertEqual(str(ticket), 'Test ticket description')

    def test_ticket_priority_choices(self):
        priorities = [choice[0] for choice in Ticket.Priority.choices]
        expected_priorities = ['LOW', 'MEDIUM', 'HIGH']
        self.assertEqual(priorities, expected_priorities)

    def test_ticket_identifier_choices(self):
        identifiers = [choice[0] for choice in Ticket.Identifier.choices]
        expected_identifiers = ['REQUEST', 'TICKET']
        self.assertEqual(identifiers, expected_identifiers)

    def test_ticket_status_choices(self):
        statuses = [choice[0] for choice in Ticket.Status.choices]
        expected_statuses = ['NEW', 'CANCELLED', 'RESOLVED', 'OPEN', 'ONHOLD', 'CLOSED']
        self.assertEqual(statuses, expected_statuses)

    def test_ticket_source_choices(self):
        sources = [choice[0] for choice in Ticket.TicketSource.choices]
        expected_sources = ['SYSTEMGENERATED', 'USERDEFINED']
        self.assertEqual(sources, expected_sources)

    def test_ticket_uuid_generation(self):
        ticket = Ticket.objects.create(**self.ticket_data)
        
        self.assertIsInstance(ticket.uuid, uuid.UUID)

    def test_ticket_defaults(self):
        ticket = Ticket.objects.create(**self.ticket_data)
        
        self.assertEqual(ticket.identifier, Ticket.Identifier.TICKET)
        self.assertEqual(ticket.status, Ticket.Status.NEW)
        self.assertEqual(ticket.level, 0)
        self.assertFalse(ticket.isescalated)
        self.assertIsNotNone(ticket.modifieddatetime)

    def test_ticket_add_history_method(self):
        ticket = Ticket.objects.create(**self.ticket_data)
        
        # Test add_history method
        ticket.add_history()
        
        self.assertIn('ticket_history', ticket.ticketlog)
        self.assertEqual(len(ticket.ticketlog['ticket_history']), 1)
        self.assertIn('record', ticket.ticketlog['ticket_history'][0])

    def test_ticket_get_changed_keys_method(self):
        ticket = Ticket.objects.create(**self.ticket_data)
        
        dict1 = {'status': 'NEW', 'priority': 'HIGH', 'level': 0}
        dict2 = {'status': 'OPEN', 'priority': 'HIGH', 'level': 1}
        
        changed_keys = ticket.get_changed_keys(dict1, dict2)
        
        self.assertIn('status', changed_keys)
        self.assertIn('level', changed_keys)
        self.assertNotIn('priority', changed_keys)

    def test_ticket_get_changed_keys_invalid_input(self):
        ticket = Ticket.objects.create(**self.ticket_data)
        
        with self.assertRaises(TypeError):
            ticket.get_changed_keys("not_a_dict", {})
        
        with self.assertRaises(TypeError):
            ticket.get_changed_keys({}, "not_a_dict")

    def test_ticket_meta_options(self):
        ticket = Ticket.objects.create(**self.ticket_data)
        meta = ticket._meta
        
        self.assertEqual(meta.db_table, 'ticket')
        self.assertEqual(meta.get_latest_by, ["cdtz", 'mdtz'])

    def test_ticket_unique_constraint(self):
        # Test the unique constraint on bu, id, client
        ticket1 = Ticket.objects.create(**self.ticket_data)
        
        # Try to create another ticket with same bu and client would violate constraint
        # This test verifies the constraint exists in the model definition
        constraints = ticket1._meta.constraints
        self.assertTrue(any(constraint.name == 'bu_id_uk' for constraint in constraints))

    def test_ticket_foreign_key_relationships(self):
        ticket = Ticket.objects.create(**self.ticket_data)
        
        self.assertEqual(ticket.assignedtopeople, self.people)
        self.assertEqual(ticket.assignedtogroup, self.group)
        self.assertEqual(ticket.bu, self.bt)
        self.assertEqual(ticket.client, self.bt)
        self.assertEqual(ticket.asset, self.asset)
        self.assertEqual(ticket.qset, self.questionset)
        self.assertEqual(ticket.location, self.location)
        self.assertEqual(ticket.performedby, self.people)

    def test_ticket_json_field_default(self):
        ticket = Ticket.objects.create(**self.ticket_data)
        
        self.assertIsInstance(ticket.ticketlog, dict)
        self.assertIn('ticket_history', ticket.ticketlog)
        self.assertIsInstance(ticket.ticketlog['ticket_history'], list)

    def test_ticket_nullable_fields(self):
        # Due to the pre_save signal, we need to provide bu and client
        # or use ticketdesc='NONE' to skip the ticketno generation
        minimal_data = {
            'ticketdesc': 'NONE'  # Special value to skip ticketno generation
        }
        
        ticket = Ticket.objects.create(**minimal_data)
        
        self.assertIsNone(ticket.assignedtopeople)
        self.assertIsNone(ticket.assignedtogroup)
        self.assertIsNone(ticket.comments)
        self.assertIsNone(ticket.bu)
        self.assertIsNone(ticket.client)

    def test_ticket_manager_custom_manager(self):
        self.assertTrue(hasattr(Ticket.objects, 'send_ticket_mail'))
        self.assertTrue(hasattr(Ticket.objects, 'get_tickets_listview'))
        self.assertEqual(Ticket.objects.__class__.__name__, 'TicketManager')


class EscalationMatrixModelTest(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            loginid='testuser',
            password='testpass123',
            peoplecode='TEST001',
            peoplename='Test User',
            dateofbirth='1990-01-01',
            email='testuser@example.com'
        )
        
        self.people = People.objects.create(
            peoplename="Test Person",
            email="test@example.com",
            dateofbirth="1990-01-01",
            peoplecode="TEST001"
        )
        
        self.group = Pgroup.objects.create(
            groupname="Test Group"
        )
        
        self.bt = Bt.objects.create(
            buname="Test BU",
            bucode="TESTBU001"
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
        
        self.escalation_data = {
            'body': 'Escalation body text',
            'job': self.job,
            'level': 1,
            'frequency': EscalationMatrix.Frequency.HOUR,
            'frequencyvalue': 2,
            'assignedfor': 'test assignment',
            'assignedperson': self.user,
            'assignedgroup': self.group,
            'bu': self.bt,
            'notify': 'test@example.com',
            'client': self.bt
        }

    def test_escalation_matrix_creation(self):
        escalation = EscalationMatrix.objects.create(**self.escalation_data)
        
        self.assertIsInstance(escalation, EscalationMatrix)
        self.assertEqual(escalation.body, 'Escalation body text')
        self.assertEqual(escalation.level, 1)
        self.assertEqual(escalation.frequency, EscalationMatrix.Frequency.HOUR)
        self.assertEqual(escalation.frequencyvalue, 2)

    def test_escalation_matrix_frequency_choices(self):
        frequencies = [choice[0] for choice in EscalationMatrix.Frequency.choices]
        expected_frequencies = ['MINUTE', 'HOUR', 'DAY', 'WEEK']
        self.assertEqual(frequencies, expected_frequencies)

    def test_escalation_matrix_defaults(self):
        minimal_data = {
            'assignedfor': 'test assignment'
        }
        
        escalation = EscalationMatrix.objects.create(**minimal_data)
        
        self.assertEqual(escalation.frequency, 'DAY')

    def test_escalation_matrix_foreign_key_relationships(self):
        escalation = EscalationMatrix.objects.create(**self.escalation_data)
        
        self.assertEqual(escalation.job, self.job)
        self.assertEqual(escalation.assignedperson, self.user)
        self.assertEqual(escalation.assignedgroup, self.group)
        self.assertEqual(escalation.bu, self.bt)
        self.assertEqual(escalation.client, self.bt)

    def test_escalation_matrix_meta_options(self):
        escalation = EscalationMatrix.objects.create(**self.escalation_data)
        meta = escalation._meta
        
        self.assertEqual(meta.db_table, 'escalationmatrix')
        self.assertEqual(meta.get_latest_by, ["mdtz", 'cdtz'])

    def test_escalation_matrix_constraints(self):
        escalation = EscalationMatrix.objects.create(**self.escalation_data)
        constraints = escalation._meta.constraints
        
        # Check for frequency value constraint
        frequency_constraint = next(
            (c for c in constraints if c.name == 'frequencyvalue_gte_0_ck'), 
            None
        )
        self.assertIsNotNone(frequency_constraint)
        
        # Check for email format constraint
        email_constraint = next(
            (c for c in constraints if c.name == 'valid_notify_format'), 
            None
        )
        self.assertIsNotNone(email_constraint)

    def test_escalation_matrix_negative_frequency_value(self):
        data = self.escalation_data.copy()
        data['frequencyvalue'] = -1
        
        escalation = EscalationMatrix(**data)
        
        with self.assertRaises(ValidationError):
            escalation.full_clean()

    def test_escalation_matrix_invalid_email(self):
        data = self.escalation_data.copy()
        data['notify'] = 'invalid_email'
        
        escalation = EscalationMatrix(**data)
        
        with self.assertRaises(ValidationError):
            escalation.full_clean()

    def test_escalation_matrix_valid_email(self):
        data = self.escalation_data.copy()
        data['notify'] = 'valid@example.com'
        
        escalation = EscalationMatrix.objects.create(**data)
        
        self.assertEqual(escalation.notify, 'valid@example.com')

    def test_escalation_matrix_nullable_fields(self):
        minimal_data = {
            'assignedfor': 'test assignment'
        }
        
        escalation = EscalationMatrix.objects.create(**minimal_data)
        
        self.assertIsNone(escalation.body)
        self.assertIsNone(escalation.job)
        self.assertIsNone(escalation.level)
        self.assertIsNone(escalation.frequencyvalue)
        self.assertIsNone(escalation.assignedperson)
        self.assertIsNone(escalation.assignedgroup)

    def test_escalation_matrix_manager_custom_manager(self):
        self.assertTrue(hasattr(EscalationMatrix.objects, 'get_reminder_config_forppm'))
        self.assertTrue(hasattr(EscalationMatrix.objects, 'handle_reminder_config_postdata'))
        self.assertEqual(EscalationMatrix.objects.__class__.__name__, 'ESCManager')

    def test_escalation_matrix_max_lengths(self):
        # Test body max length
        long_body = 'A' * 501
        data = self.escalation_data.copy()
        data['body'] = long_body
        
        escalation = EscalationMatrix(**data)
        
        with self.assertRaises(ValidationError):
            escalation.full_clean()

    def test_escalation_matrix_frequency_default(self):
        escalation = EscalationMatrix.objects.create(assignedfor='test')
        
        self.assertEqual(escalation.frequency, 'DAY')

    def test_escalation_matrix_inheritance(self):
        escalation = EscalationMatrix.objects.create(**self.escalation_data)
        
        # Check that it inherits from BaseModel
        self.assertTrue(hasattr(escalation, 'cdtz'))
        self.assertTrue(hasattr(escalation, 'mdtz'))
        self.assertTrue(hasattr(escalation, 'cuser'))
        self.assertTrue(hasattr(escalation, 'muser'))
        
        # Check that it inherits from TenantAwareModel
        self.assertTrue(hasattr(escalation, 'tenant'))

    def test_escalation_matrix_use_in_migrations(self):
        self.assertTrue(EscalationMatrix.objects.use_in_migrations)