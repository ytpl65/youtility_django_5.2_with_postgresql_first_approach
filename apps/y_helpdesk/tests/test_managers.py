from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

from apps.y_helpdesk.models import Ticket, EscalationMatrix
from apps.y_helpdesk.managers import TicketManager, ESCManager
from apps.peoples.models import People, Pgroup
from apps.activity.models.job_model import Job
from apps.onboarding.models import Bt, TypeAssist

User = get_user_model()


class TicketManagerTest(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
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
        
        self.ticket = Ticket.objects.create(
            ticketdesc='Test ticket',
            assignedtopeople=self.people,
            bu=self.bt,
            client=self.bt,
            status=Ticket.Status.NEW,
            ticketsource=Ticket.TicketSource.USERDEFINED
        )

    def test_ticket_manager_instance(self):
        self.assertIsInstance(Ticket.objects, TicketManager)
        self.assertTrue(hasattr(Ticket.objects, 'send_ticket_mail'))
        self.assertTrue(hasattr(Ticket.objects, 'get_tickets_listview'))

    def test_send_ticket_mail(self):
        with patch.object(Ticket.objects, 'raw') as mock_raw:
            mock_raw.return_value = [Mock()]
            
            result = Ticket.objects.send_ticket_mail(self.ticket.id)
            
            self.assertIsNotNone(result)
            mock_raw.assert_called_once()

    @patch('apps.y_helpdesk.managers.safe_json_parse_params')
    def test_get_tickets_listview(self, mock_parse_params):
        mock_parse_params.return_value = {
            'from': '2024-01-01',
            'to': '2024-12-31',
            'status': 'NEW'
        }
        
        request = self.factory.get('/tickets/')
        request.session = {
            'assignedsites': [self.bt.id],
            'client_id': self.bt.id
        }
        
        # Create actual tickets in the database instead of mocking
        ticket1 = Ticket.objects.create(
            ticketdesc='Test ticket 1',
            bu=self.bt,
            client=self.bt,
            status=Ticket.Status.NEW,
            ticketsource=Ticket.TicketSource.USERDEFINED
        )
        
        result = Ticket.objects.get_tickets_listview(request)
        
        # Check that the result is a queryset-like object
        self.assertTrue(hasattr(result, '__iter__'))
        # Convert to list for checking
        result_list = list(result)
        self.assertIsInstance(result_list, list)

    def test_get_tickets_for_mob(self):
        mdtz = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with patch.object(Ticket.objects, 'select_related') as mock_select:
            mock_queryset = Mock()
            mock_queryset.filter.return_value = mock_queryset
            mock_queryset.values.return_value = []
            mock_select.return_value = mock_queryset
            
            result = Ticket.objects.get_tickets_for_mob(
                self.people.id, self.bt.id, self.bt.id, mdtz, 330
            )
            
            mock_select.assert_called()

    def test_get_ticketlist_for_escalation(self):
        with patch('apps.core.utils.runrawsql') as mock_raw_sql:
            mock_raw_sql.return_value = [Mock()]
            
            result = Ticket.objects.get_ticketlist_for_escalation()
            
            mock_raw_sql.assert_called_once()

    def test_get_ticket_stats_for_dashboard(self):
        request = self.factory.get('/dashboard/')
        request.session = {
            'assignedsites': [self.bt.id],
            'client_id': self.bt.id
        }
        request.GET = {
            'from': '2024-01-01',
            'upto': '2024-12-31'
        }
        
        with patch.object(Ticket.objects, 'filter') as mock_filter:
            mock_queryset = Mock()
            mock_queryset.filter.return_value = mock_queryset
            mock_queryset.aggregate.return_value = {
                'new': 5, 'open': 3, 'cancelled': 1,
                'resolved': 10, 'closed': 8, 'onhold': 2
            }
            mock_queryset.count.return_value = 4
            mock_filter.return_value = mock_queryset
            
            stats, total = Ticket.objects.get_ticket_stats_for_dashboard(request)
            
            self.assertIsInstance(stats, list)
            self.assertIsInstance(total, int)
            self.assertEqual(len(stats), 7)

    def test_get_events_for_calendar(self):
        request = self.factory.get('/calendar/')
        request.session = {
            'bu_id': self.bt.id,
            'client_id': self.bt.id
        }
        request.GET = {
            'start': '2024-01-01T00:00:00+00:00',
            'end': '2024-12-31T23:59:59+00:00'
        }
        
        with patch.object(Ticket.objects, 'annotate') as mock_annotate:
            mock_queryset = Mock()
            mock_queryset.select_related.return_value = mock_queryset
            mock_queryset.filter.return_value = mock_queryset
            mock_queryset.values.return_value = []
            mock_annotate.return_value = mock_queryset
            
            result = Ticket.objects.get_events_for_calendar(request)
            
            mock_annotate.assert_called()

    def test_manager_use_in_migrations(self):
        self.assertTrue(TicketManager.use_in_migrations)


class ESCManagerTest(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
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

    def test_esc_manager_instance(self):
        self.assertIsInstance(EscalationMatrix.objects, ESCManager)
        self.assertTrue(hasattr(EscalationMatrix.objects, 'get_reminder_config_forppm'))
        self.assertTrue(hasattr(EscalationMatrix.objects, 'handle_reminder_config_postdata'))

    def test_get_reminder_config_forppm(self):
        fields = ['frequency', 'frequencyvalue', 'notify', 'id']
        
        with patch.object(EscalationMatrix.objects, 'filter') as mock_filter:
            mock_queryset = Mock()
            mock_queryset.values.return_value = []
            mock_filter.return_value = mock_queryset
            
            result = EscalationMatrix.objects.get_reminder_config_forppm(self.job.id, fields)
            
            mock_filter.assert_called_with(
                escalationtemplate__tacode="JOB",
                job_id=self.job.id
            )

    @patch('apps.y_helpdesk.managers.TypeAssist.objects.get')
    def test_handle_reminder_config_postdata_create(self, mock_get_type_assist):
        mock_type_assist = Mock()
        mock_get_type_assist.return_value = mock_type_assist
        
        request = self.factory.post('/reminder/')
        request.user = self.user
        request.session = {
            'bu_id': self.bt.id,
            'client_id': self.bt.id
        }
        request.POST = {
            'action': 'create',
            'jobid': str(self.job.id),
            'frequency': 'HOUR',
            'frequencyvalue': '2',
            'notify': 'test@example.com',
            'peopleid': str(self.people.id),
            'groupid': str(self.group.id),
            'ctzoffset': '330'
        }
        
        # Mock the filter to return exists() = False
        mock_exists = Mock(return_value=False)
        mock_filter = Mock()
        mock_filter.exists = mock_exists
        
        # Mock the create method
        mock_instance = Mock()
        mock_instance.id = 1
        
        # Mock filter for getting the created instance
        mock_values = Mock(return_value=[{'id': 1}])
        mock_filter_for_values = Mock()
        mock_filter_for_values.values = mock_values
        
        with patch.object(EscalationMatrix.objects, 'filter') as mock_filter_method:
            # Configure filter to handle both the exists check and the values query
            def filter_side_effect(*args, **kwargs):
                if 'pk' in kwargs:
                    return mock_filter_for_values
                return mock_filter
            mock_filter_method.side_effect = filter_side_effect
            
            with patch.object(EscalationMatrix.objects, 'create', return_value=mock_instance) as mock_create:
                result = EscalationMatrix.objects.handle_reminder_config_postdata(request)
                
                self.assertIn('data', result)
                mock_create.assert_called_once()

    @patch('apps.y_helpdesk.managers.TypeAssist.objects.get')
    def test_handle_reminder_config_postdata_edit(self, mock_get_type_assist):
        mock_type_assist = Mock()
        mock_get_type_assist.return_value = mock_type_assist
        
        request = self.factory.post('/reminder/')
        request.user = self.user
        request.session = {
            'bu_id': self.bt.id,
            'client_id': self.bt.id
        }
        request.POST = {
            'action': 'edit',
            'pk': '1',
            'jobid': str(self.job.id),
            'frequency': 'DAY',
            'frequencyvalue': '1',
            'notify': 'updated@example.com',
            'peopleid': str(self.people.id),
            'groupid': str(self.group.id),
            'ctzoffset': '330'
        }
        
        with patch.object(EscalationMatrix.objects, 'filter') as mock_filter:
            mock_filter.return_value.update.return_value = 1
            mock_filter.return_value.values.return_value = [{'id': 1}]
            
            result = EscalationMatrix.objects.handle_reminder_config_postdata(request)
            
            self.assertIn('data', result)

    @patch('apps.y_helpdesk.managers.TypeAssist.objects.get')
    def test_handle_reminder_config_postdata_delete(self, mock_get_type_assist):
        mock_type_assist = Mock()
        mock_get_type_assist.return_value = mock_type_assist
        
        request = self.factory.post('/reminder/')
        request.user = self.user
        request.session = {
            'bu_id': self.bt.id,
            'client_id': self.bt.id
        }
        request.POST = {
            'action': 'delete',
            'pk': '1',
            'jobid': str(self.job.id),
            'frequency': 'DAY',
            'frequencyvalue': '1',
            'notify': 'test@example.com',
            'peopleid': str(self.people.id),
            'groupid': str(self.group.id),
            'ctzoffset': '330'
        }
        
        with patch.object(EscalationMatrix.objects, 'filter') as mock_filter:
            mock_filter.return_value.delete.return_value = (1, {})
            
            result = EscalationMatrix.objects.handle_reminder_config_postdata(request)
            
            self.assertIn('data', result)

    @patch('apps.y_helpdesk.managers.TypeAssist.objects.get')
    def test_handle_reminder_config_postdata_duplicate_record(self, mock_get_type_assist):
        mock_type_assist = Mock()
        mock_get_type_assist.return_value = mock_type_assist
        
        request = self.factory.post('/reminder/')
        request.user = self.user
        request.session = {
            'bu_id': self.bt.id,
            'client_id': self.bt.id
        }
        request.POST = {
            'action': 'create',
            'jobid': str(self.job.id),
            'frequency': 'HOUR',
            'frequencyvalue': '2',
            'notify': 'test@example.com',
            'peopleid': str(self.people.id),
            'groupid': str(self.group.id),
            'ctzoffset': '330'
        }
        
        with patch.object(EscalationMatrix.objects, 'filter') as mock_filter:
            mock_filter.return_value.exists.return_value = True
            
            result = EscalationMatrix.objects.handle_reminder_config_postdata(request)
            
            self.assertIn('error', result)
            self.assertIn('already added', result['error'])

    def test_get_escalation_listview(self):
        request = self.factory.get('/escalations/')
        request.session = {
            'assignedsites': [self.bt.id],
            'client_id': self.bt.id
        }
        
        with patch('apps.y_helpdesk.managers.TypeAssist.objects.filter') as mock_filter:
            mock_queryset = Mock()
            mock_queryset.select_related.return_value = mock_queryset
            mock_queryset.values.return_value = []
            mock_filter.return_value = mock_queryset
            
            result = EscalationMatrix.objects.get_escalation_listview(request)
            
            mock_filter.assert_called()

    def test_handle_esclevel_form_postdata_create(self):
        request = self.factory.post('/escalation/')
        request.user = self.user
        request.session = {
            'bu_id': self.bt.id,
            'client_id': self.bt.id
        }
        request.POST = {
            'action': 'create',
            'level': '1',
            'frequency': 'HOUR',
            'frequencyvalue': '2',
            'assignedperson': str(self.people.id),
            'assignedgroup': str(self.group.id),
            'assignedfor': 'test assignment',
            'escalationtemplate_id': '1',
            'ctzoffset': '330'
        }
        
        # Mock the filter to return exists() = False
        mock_exists = Mock(return_value=False)
        mock_filter = Mock()
        mock_filter.exists = mock_exists
        
        # Mock the create method
        mock_instance = Mock()
        mock_instance.id = 1
        
        # Mock filter for getting the created instance
        mock_values = Mock(return_value=[{'id': 1}])
        mock_filter_for_values = Mock()
        mock_filter_for_values.values = mock_values
        
        with patch.object(EscalationMatrix.objects, 'filter') as mock_filter_method:
            # Configure filter to handle both the exists check and the values query
            def filter_side_effect(*args, **kwargs):
                if 'pk' in kwargs:
                    return mock_filter_for_values
                return mock_filter
            mock_filter_method.side_effect = filter_side_effect
            
            with patch.object(EscalationMatrix.objects, 'create', return_value=mock_instance) as mock_create:
                result = EscalationMatrix.objects.handle_esclevel_form_postdata(request)
                
                self.assertIn('data', result)
                mock_create.assert_called_once()

    def test_handle_esclevel_form_postdata_duplicate_error(self):
        request = self.factory.post('/escalation/')
        request.user = self.user
        request.session = {
            'bu_id': self.bt.id,
            'client_id': self.bt.id
        }
        request.POST = {
            'action': 'create',
            'level': '1',
            'frequency': 'HOUR',
            'frequencyvalue': '2',
            'assignedperson': str(self.people.id),
            'assignedgroup': str(self.group.id),
            'assignedfor': 'test assignment',
            'escalationtemplate_id': '1',
            'ctzoffset': '330'
        }
        
        with patch.object(EscalationMatrix.objects, 'filter') as mock_filter:
            mock_filter.return_value.exists.return_value = True
            
            result = EscalationMatrix.objects.handle_esclevel_form_postdata(request)
            
            self.assertIn('error', result)
            self.assertIn('already added', result['error'])

    def test_handle_esclevel_form_postdata_negative_frequency_error(self):
        request = self.factory.post('/escalation/')
        request.user = self.user
        request.session = {
            'bu_id': self.bt.id,
            'client_id': self.bt.id
        }
        request.POST = {
            'action': 'create',
            'level': '1',
            'frequency': 'HOUR',
            'frequencyvalue': '-1',
            'assignedperson': str(self.people.id),
            'assignedgroup': str(self.group.id),
            'assignedfor': 'test assignment',
            'escalationtemplate_id': '1',
            'ctzoffset': '330'
        }
        
        with patch.object(EscalationMatrix.objects, 'filter') as mock_filter:
            mock_filter.return_value.exists.return_value = False
            
            with patch.object(EscalationMatrix.objects, 'create') as mock_create:
                mock_create.side_effect = Exception('frequencyvalue_gte_0_ck')
                
                result = EscalationMatrix.objects.handle_esclevel_form_postdata(request)
                
                self.assertIn('error', result)
                self.assertIn('must be greater than or equal to 0', result['error'])

    def test_manager_use_in_migrations(self):
        self.assertTrue(ESCManager.use_in_migrations)