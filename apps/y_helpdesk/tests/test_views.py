from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from unittest.mock import patch, Mock, MagicMock
import json
import uuid

from apps.y_helpdesk.views import EscalationMatrixView, TicketView, PostingOrderView, UniformView
from apps.y_helpdesk.models import Ticket, EscalationMatrix
from apps.peoples.models import People, Pgroup
from apps.activity.models.job_model import Job
from apps.onboarding.models import Bt, TypeAssist

User = get_user_model()


class EscalationMatrixViewTest(TestCase):
    
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
            dateofbirth="1990-01-01",
            peoplecode="TEST001"
        )
        
        self.group = Pgroup.objects.create(
            groupname="Test Group"
        )
        
        self.view = EscalationMatrixView()

    def add_session_to_request(self, request):
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['assignedsites'] = [self.bt.id]
        request.session['client_id'] = self.bt.id
        request.session['bu_id'] = self.bt.id
        request.session['sitecode'] = 'TESTBU001'
        request.session['sitename'] = 'Test BU'
        request.session['clientcode'] = 'TESTBU001'
        request.session.save()
        
        message_middleware = MessageMiddleware(lambda x: None)
        message_middleware.process_request(request)
        
        auth_middleware = AuthenticationMiddleware(lambda x: None)
        auth_middleware.process_request(request)
        request.user = self.user

    def test_get_form_action(self):
        request = self.factory.get('/escalation/?action=form')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, HttpResponse)

    @patch('apps.y_helpdesk.views.pm.People.objects.getPeoplesForEscForm')
    def test_get_load_peoples_action(self, mock_get_peoples):
        mock_get_peoples.return_value = [
            {'id': 1, 'peoplename': 'Test Person'}
        ]
        
        request = self.factory.get('/escalation/?action=loadPeoples')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)
        mock_get_peoples.assert_called_once_with(request)

    @patch('apps.y_helpdesk.views.pm.Pgroup.objects.getGroupsForEscForm')
    def test_get_load_groups_action(self, mock_get_groups):
        mock_get_groups.return_value = [
            {'id': 1, 'groupname': 'Test Group'}
        ]
        
        request = self.factory.get('/escalation/?action=loadGroups')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)
        mock_get_groups.assert_called_once_with(request)

    def test_get_template_true(self):
        request = self.factory.get('/escalation/?template=true')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)
        
    @patch('apps.y_helpdesk.views.EscalationMatrix.objects.get_escalation_listview')
    def test_get_list_action(self, mock_get_listview):
        mock_get_listview.return_value = [
            {'id': 1, 'level': 1, 'frequency': 'HOUR'}
        ]
        
        request = self.factory.get('/escalation/?action=list')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)
        mock_get_listview.assert_called_once_with(request)

    @patch('apps.y_helpdesk.views.TypeAssist.objects.get_escalationlevels')
    def test_get_escalation_levels_action(self, mock_get_levels):
        mock_get_levels.return_value = [
            {'level': 1, 'name': 'Level 1'}
        ]
        
        request = self.factory.get('/escalation/?action=get_escalationlevels')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)
        mock_get_levels.assert_called_once_with(request)

    def test_get_with_id(self):
        request = self.factory.get('/escalation/?id=1')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, HttpResponse)

    @patch('apps.y_helpdesk.views.EscalationMatrix.objects.get_reminder_config_forppm')
    def test_get_reminder_config_action(self, mock_get_config):
        mock_get_config.return_value = [
            {'frequency': 'HOUR', 'frequencyvalue': 2}
        ]
        
        request = self.factory.get('/escalation/?action=get_reminder_config&job_id=1')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertIsInstance(response, JsonResponse)
        mock_get_config.assert_called_once()

    @patch('apps.y_helpdesk.views.EscalationMatrix.objects.handle_esclevel_form_postdata')
    def test_post_escalations(self, mock_handle_postdata):
        mock_handle_postdata.return_value = {'data': [{'id': 1}]}
        
        request = self.factory.post('/escalation/', {'post': 'postEscalations'})
        self.add_session_to_request(request)
        
        response = self.view.post(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)
        mock_handle_postdata.assert_called_once_with(request)

    @patch('apps.y_helpdesk.views.EscalationMatrix.objects.handle_reminder_config_postdata')
    def test_post_reminder(self, mock_handle_postdata):
        mock_handle_postdata.return_value = {'data': [{'id': 1}]}
        
        request = self.factory.post('/escalation/', {'post': 'postReminder'})
        self.add_session_to_request(request)
        
        response = self.view.post(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)
        mock_handle_postdata.assert_called_once_with(request)


class TicketViewTest(TestCase):
    
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
            dateofbirth="1990-01-01",
            peoplecode="TEST001"
        )
        
        self.ticket = Ticket.objects.create(
            ticketdesc='Test ticket',
            bu=self.bt,
            client=self.bt,
            status=Ticket.Status.NEW
        )
        
        self.view = TicketView()

    def add_session_to_request(self, request):
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['assignedsites'] = [self.bt.id]
        request.session['client_id'] = self.bt.id
        request.session['bu_id'] = self.bt.id
        request.session['sitecode'] = 'TESTBU001'
        request.session['sitename'] = 'Test BU'
        request.session['clientcode'] = 'TESTBU001'
        request.session.save()
        
        message_middleware = MessageMiddleware(lambda x: None)
        message_middleware.process_request(request)
        
        auth_middleware = AuthenticationMiddleware(lambda x: None)
        auth_middleware.process_request(request)
        request.user = self.user

    def test_get_form_action(self):
        request = self.factory.get('/tickets/?action=form')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, HttpResponse)

    def test_get_template_true(self):
        request = self.factory.get('/tickets/?template=true')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)

    @patch('apps.y_helpdesk.views.Ticket.objects.get_tickets_listview')
    def test_get_list_action(self, mock_get_listview):
        mock_get_listview.return_value = [
            {'id': 1, 'ticketdesc': 'Test ticket', 'status': 'NEW'}
        ]
        
        request = self.factory.get('/tickets/?action=list')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)
        mock_get_listview.assert_called_once_with(request)

    @patch('apps.y_helpdesk.views.utils.get_model_obj')
    def test_get_with_id_new_ticket(self, mock_get_obj):
        mock_get_obj.return_value = self.ticket
        
        request = self.factory.get(f'/tickets/?id={self.ticket.id}')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, HttpResponse)
        
        # Check that ticket status was updated to OPEN
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.OPEN)

    @patch('apps.y_helpdesk.views.utils.get_model_obj')
    def test_get_with_id_existing_open_ticket(self, mock_get_obj):
        self.ticket.status = Ticket.Status.OPEN
        self.ticket.cuser = self.user
        self.ticket.save()
        mock_get_obj.return_value = self.ticket
        
        request = self.factory.get(f'/tickets/?id={self.ticket.id}')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)
        # Status should remain OPEN, not change
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.OPEN)

    @patch('apps.y_helpdesk.views.utils.get_current_db_name')
    @patch('apps.y_helpdesk.views.putils.save_userinfo')
    @patch('apps.y_helpdesk.views.utils.store_ticket_history')
    def test_post_create_ticket(self, mock_store_history, mock_save_userinfo, mock_get_db):
        mock_get_db.return_value = 'default'
        mock_save_userinfo.return_value = self.ticket
        
        form_data = {
            'ticketdesc': 'New ticket description',
            'priority': 'HIGH',
            'status': 'NEW'
        }
        
        post_data = {
            'formData': '&'.join([f'{k}={v}' for k, v in form_data.items()]),
            'uuid': str(uuid.uuid4())
        }
        
        request = self.factory.post('/tickets/', post_data)
        self.add_session_to_request(request)
        
        with patch.object(self.view.params['form'], 'is_valid', return_value=True):
            with patch.object(self.view.params['form'], 'save') as mock_save:
                mock_save.return_value = self.ticket
                
                with patch.object(self.view.params['form'], '__init__', return_value=None):
                    response = self.view.post(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)

    @patch('apps.y_helpdesk.views.utils.get_current_db_name')
    @patch('apps.y_helpdesk.views.utils.get_model_obj')
    def test_post_update_ticket(self, mock_get_obj, mock_get_db):
        mock_get_db.return_value = 'default'
        mock_get_obj.return_value = self.ticket
        
        form_data = {
            'ticketdesc': 'Updated ticket description',
            'priority': 'MEDIUM',
            'status': 'RESOLVED'
        }
        
        post_data = {
            'formData': '&'.join([f'{k}={v}' for k, v in form_data.items()]),
            'pk': str(self.ticket.id),
            'uuid': str(self.ticket.uuid)
        }
        
        request = self.factory.post('/tickets/', post_data)
        self.add_session_to_request(request)
        
        with patch.object(self.view.params['form'], 'is_valid', return_value=True):
            with patch.object(self.view.params['form'], 'save') as mock_save:
                mock_save.return_value = self.ticket
                
                with patch.object(self.view.params['form'], '__init__', return_value=None):
                    response = self.view.post(request)
        
        self.assertIsInstance(response, JsonResponse)

    def test_post_invalid_form(self):
        form_data = {
            'ticketdesc': '',  # Invalid - required field
        }
        
        post_data = {
            'formData': '&'.join([f'{k}={v}' for k, v in form_data.items()]),
            'uuid': str(uuid.uuid4())
        }
        
        request = self.factory.post('/tickets/', post_data)
        self.add_session_to_request(request)
        
        with patch('apps.y_helpdesk.views.utils.get_current_db_name', return_value='default'):
            with patch.object(self.view.params['form'], 'is_valid', return_value=False):
                with patch.object(self.view.params['form'], 'errors', {'ticketdesc': ['This field is required']}):
                    with patch('apps.y_helpdesk.views.utils.handle_invalid_form') as mock_handle_invalid:
                        mock_handle_invalid.return_value = JsonResponse({'errors': 'Invalid form'}, status=400)
                        
                        response = self.view.post(request)
        
        self.assertIsInstance(response, JsonResponse)

    @patch('apps.y_helpdesk.views.putils.save_userinfo')
    @patch('apps.y_helpdesk.views.utils.store_ticket_history')
    def test_handle_valid_form(self, mock_store_history, mock_save_userinfo):
        mock_save_userinfo.return_value = self.ticket
        
        form = Mock()
        form.save.return_value = self.ticket
        
        request = self.factory.post('/tickets/')
        request.POST = {'uuid': str(uuid.uuid4())}
        self.add_session_to_request(request)
        
        response = self.view.handle_valid_form(form, request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)
        mock_save_userinfo.assert_called_once()
        mock_store_history.assert_called_once()


class PostingOrderViewTest(TestCase):
    
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
        
        self.view = PostingOrderView()

    def add_session_to_request(self, request):
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['assignedsites'] = [self.bt.id]
        request.session['client_id'] = self.bt.id
        request.session['bu_id'] = self.bt.id
        request.session['sitecode'] = 'TESTBU001'
        request.session['sitename'] = 'Test BU'
        request.session['clientcode'] = 'TESTBU001'
        request.session.save()
        
        message_middleware = MessageMiddleware(lambda x: None)
        message_middleware.process_request(request)
        
        auth_middleware = AuthenticationMiddleware(lambda x: None)
        auth_middleware.process_request(request)
        request.user = self.user

    def test_get_template_true(self):
        request = self.factory.get('/posting-orders/?template=true')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)

    @patch('apps.activity.models.job_model.Jobneed.objects.get_posting_order_listview')
    def test_get_list_action(self, mock_get_listview):
        mock_get_listview.return_value = [
            {'id': 1, 'jobdesc': 'Test posting order'}
        ]
        
        request = self.factory.get('/posting-orders/?action=list')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)
        mock_get_listview.assert_called_once_with(request)


class UniformViewTest(TestCase):
    
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
        
        self.view = UniformView()

    def add_session_to_request(self, request):
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['assignedsites'] = [self.bt.id]
        request.session['client_id'] = self.bt.id
        request.session['bu_id'] = self.bt.id
        request.session['sitecode'] = 'TESTBU001'
        request.session['sitename'] = 'Test BU'
        request.session['clientcode'] = 'TESTBU001'
        request.session.save()
        
        message_middleware = MessageMiddleware(lambda x: None)
        message_middleware.process_request(request)
        
        auth_middleware = AuthenticationMiddleware(lambda x: None)
        auth_middleware.process_request(request)
        request.user = self.user

    def test_get_uniform_form(self):
        request = self.factory.get('/uniform/')
        self.add_session_to_request(request)
        
        response = self.view.get(request)
        
        self.assertEqual(response.status_code, 200)