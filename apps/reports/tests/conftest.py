"""
Fixtures for reports app testing
"""
import pytest
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils import timezone
from datetime import datetime, timedelta, date, time
from apps.reports.models import ReportHistory, ScheduleReport, GeneratePDF
from apps.onboarding.models import Bt
from apps.peoples.models import People


@pytest.fixture
def rf():
    """Request factory"""
    return RequestFactory()


@pytest.fixture
def test_client_reports():
    """Create test client for reports"""
    return Bt.objects.create(
        bucode='REPORTCLIENT',
        buname='Reports Test Client',
        enable=True
    )


@pytest.fixture
def test_bu_reports(test_client_reports):
    """Create test business unit for reports"""
    return Bt.objects.create(
        bucode='REPORTBU',
        buname='Reports Test BU',
        parent=test_client_reports,
        enable=True
    )


@pytest.fixture
def test_user_reports(test_client_reports, test_bu_reports):
    """Create test user for reports"""
    return People.objects.create(
        peoplecode='REPORTUSER001',
        peoplename='Report User',
        loginid='reportuser',
        email='reportuser@example.com',
        mobno='9876543210',
        dateofbirth='1990-01-01',
        dateofjoin='2023-01-01',
        client=test_client_reports,
        bu=test_bu_reports,
        isverified=True,
        enable=True
    )


@pytest.fixture
def report_history_factory(test_user_reports, test_client_reports, test_bu_reports):
    """Factory for creating ReportHistory instances"""
    counter = [0]  # Use list to maintain counter state
    
    def _create_report_history(
        user=None,
        export_type=None,
        report_name=None,
        client=None,
        bu=None,
        **kwargs
    ):
        counter[0] += 1
        unique_id = f"{timezone.now().timestamp():.6f}_{counter[0]}"
        
        defaults = {
            'user': user or test_user_reports,
            'datetime': kwargs.get('datetime', timezone.now()),
            'export_type': export_type or ReportHistory.ExportType.D,
            'report_name': report_name or f'Test Report {counter[0]}',
            'params': kwargs.get('params', {'filter': 'test', 'period': 'monthly'}),
            'bu': bu or test_bu_reports,
            'client': client or test_client_reports,
            'has_data': kwargs.get('has_data', True),
            'ctzoffset': kwargs.get('ctzoffset', 330),  # IST timezone
            'cc_mails': kwargs.get('cc_mails', 'cc@example.com'),
            'to_mails': kwargs.get('to_mails', 'to@example.com'),
            'email_body': kwargs.get('email_body', f'Report body {counter[0]}'),
            'traceback': kwargs.get('traceback', None),
        }
        defaults.update(kwargs)
        return ReportHistory.objects.create(**defaults)
    
    return _create_report_history


@pytest.fixture
def schedule_report_factory(test_client_reports, test_bu_reports):
    """Factory for creating ScheduleReport instances"""
    counter = [0]  # Use list to maintain counter state
    
    def _create_schedule_report(
        report_type=None,
        report_name=None,
        client=None,
        bu=None,
        **kwargs
    ):
        counter[0] += 1
        unique_id = f"{timezone.now().timestamp():.6f}_{counter[0]}"
        
        defaults = {
            'report_type': report_type or 'TASKSUMMARY',
            'filename': kwargs.get('filename', f'report_{unique_id}.pdf'),
            'report_name': report_name or f'Scheduled Report {counter[0]}',
            'workingdays': kwargs.get('workingdays', '5'),
            'cron': kwargs.get('cron', f'{counter[0] % 60} {counter[0] % 24} * * *'),
            'report_sendtime': kwargs.get('report_sendtime', time(9, 0)),
            'cc': kwargs.get('cc', ['cc1@example.com', 'cc2@example.com']),
            'to_addr': kwargs.get('to_addr', ['to1@example.com', 'to2@example.com']),
            'enable': kwargs.get('enable', True),
            'crontype': kwargs.get('crontype', 'DAILY'),
            'fromdatetime': kwargs.get('fromdatetime', timezone.now() - timedelta(days=1)),
            'uptodatetime': kwargs.get('uptodatetime', timezone.now() + timedelta(days=1)),
            'lastgeneratedon': kwargs.get('lastgeneratedon', timezone.now() - timedelta(hours=1)),
            'report_params': kwargs.get('report_params', {
                'report_params': {
                    'date_range': 'last_30_days',
                    'include_charts': True,
                    'format': 'pdf'
                }
            }),
            'bu': bu or test_bu_reports,
            'client': client or test_client_reports,
            'cuser': kwargs.get('cuser', None),
            'muser': kwargs.get('muser', None),
        }
        defaults.update(kwargs)
        return ScheduleReport.objects.create(**defaults)
    
    return _create_schedule_report


@pytest.fixture
def generate_pdf_factory():
    """Factory for creating GeneratePDF instances"""
    counter = [0]  # Use list to maintain counter state
    
    def _create_generate_pdf(
        document_type=None,
        company=None,
        additional_filter=None,
        **kwargs
    ):
        counter[0] += 1
        unique_id = f"{timezone.now().timestamp():.6f}_{counter[0]}"
        
        defaults = {
            'document_type': document_type or GeneratePDF.DocumentType.PAYROLL,
            'company': company or GeneratePDF.Company.SPS,
            'additional_filter': additional_filter or GeneratePDF.AdditionalFilter.CUSTOMER,
            'customer': kwargs.get('customer', f'Customer {counter[0]}'),
            'site': kwargs.get('site', f'Site {counter[0]}'),
            'period_from': kwargs.get('period_from', f'2024-{counter[0] % 12 + 1:02d}'),
            'type_of_form': kwargs.get('type_of_form', GeneratePDF.FormType.NORMALFORM),
            'cuser': kwargs.get('cuser', None),
            'muser': kwargs.get('muser', None),
        }
        defaults.update(kwargs)
        return GeneratePDF.objects.create(**defaults)
    
    return _create_generate_pdf


@pytest.fixture
def authenticated_reports_request(rf, test_user_reports, test_client_reports, test_bu_reports):
    """Create an authenticated request with session for reports testing"""
    request = rf.get('/')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    
    # Set session data for reports
    request.session['client_id'] = test_client_reports.id
    request.session['bu_id'] = test_bu_reports.id
    request.session['assignedsites'] = [test_bu_reports.id]
    request.session['user_id'] = test_user_reports.id
    request.session['people_id'] = test_user_reports.id
    request.session['_auth_user_id'] = test_user_reports.id
    request.session['is_superadmin'] = False
    request.session['client_webcaps'] = []
    request.session['client_mobcaps'] = []
    request.session['client_portletcaps'] = []
    request.session['client_reportcaps'] = []
    request.session['client_noccaps'] = []
    request.session['sitecode'] = test_bu_reports.bucode
    request.session['sitename'] = test_bu_reports.buname
    request.session['clientcode'] = test_client_reports.bucode
    request.session['clientname'] = test_client_reports.buname
    request.session['ctzoffset'] = 330  # IST timezone offset
    request.user = test_user_reports
    
    return request


@pytest.fixture
def sample_report_params():
    """Sample report parameters for testing"""
    return {
        'date_range': 'last_30_days',
        'filters': {
            'status': 'active',
            'category': 'maintenance',
            'priority': 'high'
        },
        'output_format': 'pdf',
        'include_charts': True,
        'include_summary': True,
        'group_by': 'asset',
        'sort_order': 'date_desc'
    }


@pytest.fixture
def report_template_choices():
    """All report template choices for testing"""
    return [
        ('TASKSUMMARY', 'Task Summary'),
        ('TOURSUMMARY', 'Tour Summary'),
        ('LISTOFTASKS', 'List of Tasks'),
        ('LISTOFTOURS', 'List of Internal Tours'),
        ('PPMSUMMARY', 'PPM Summary'),
        ('LISTOFTICKETS', 'List of Tickets'),
        ('WORKORDERLIST', 'Work Order List'),
        ('SITEVISITREPORT', 'Site Visit Report'),
        ('SITEREPORT', 'Site Report'),
        ('PeopleQR', 'People-QR'),
        ('ASSETQR', 'Asset-QR'),
        ('CHECKPOINTQR', 'Checkpoint-QR'),
        ('ASSETWISETASKSTATUS', 'Assetwise Task Status'),
        ('DetailedTourSummary', 'Detailed Tour Summary'),
        ('STATICDETAILEDTOURSUMMARY', 'Static Detailed Tour Summary'),
        ('DYNAMICDETAILEDTOURSUMMARY', 'Dynamic Detailed Tour Summary'),
        ('DYNAMICTOURDETAILS', 'Dynamic Tour Details'),
        ('STATICTOURDETAILS', 'Static Tour Details'),
        ('RP_SITEVISITREPORT', 'RP Site Visit Report'),
        ('LOGSHEET', 'Log Sheet'),
        ('PEOPLEATTENDANCESUMMARY', 'People Attendance Summary')
    ]


@pytest.fixture
def export_type_choices():
    """All export type choices for ReportHistory"""
    return [
        ReportHistory.ExportType.D,
        ReportHistory.ExportType.E,
        ReportHistory.ExportType.S
    ]


@pytest.fixture
def working_days_choices():
    """All working days choices for ScheduleReport"""
    return [
        ('5', 'Monday - Friday'),
        ('6', 'Monday - Saturday')
    ]


@pytest.fixture
def document_type_choices():
    """All document type choices for GeneratePDF"""
    return [
        GeneratePDF.DocumentType.PF,
        GeneratePDF.DocumentType.ESIC,
        GeneratePDF.DocumentType.PAYROLL
    ]


@pytest.fixture
def company_choices():
    """All company choices for GeneratePDF"""
    return [
        GeneratePDF.Company.SPS,
        GeneratePDF.Company.SFS,
        GeneratePDF.Company.TARGET
    ]


@pytest.fixture
def additional_filter_choices():
    """All additional filter choices for GeneratePDF"""
    return [
        GeneratePDF.AdditionalFilter.CUSTOMER,
        GeneratePDF.AdditionalFilter.SITE
    ]


@pytest.fixture
def form_type_choices():
    """All form type choices for GeneratePDF"""
    return [
        GeneratePDF.FormType.NORMALFORM,
        GeneratePDF.FormType.FORM16
    ]


@pytest.fixture
def sample_email_data():
    """Sample email data for testing"""
    return {
        'to_mails': 'user1@example.com,user2@example.com',
        'cc_mails': 'cc1@example.com,cc2@example.com',
        'email_body': 'This is a test email body for the report.',
        'to_addr': ['admin@example.com', 'manager@example.com'],
        'cc': ['supervisor@example.com', 'analyst@example.com']
    }


@pytest.fixture
def sample_cron_expressions():
    """Sample cron expressions for testing"""
    return {
        'daily_9am': '0 9 * * *',
        'weekly_monday_8am': '0 8 * * 1',
        'monthly_first_day_10am': '0 10 1 * *',
        'every_5_minutes': '*/5 * * * *',
        'weekdays_6pm': '0 18 * * 1-5',
        'every_hour': '0 * * * *'
    }


@pytest.fixture
def report_time_ranges():
    """Sample time ranges for report testing"""
    base_time = timezone.now()
    return {
        'today': {
            'start': base_time.replace(hour=0, minute=0, second=0, microsecond=0),
            'end': base_time.replace(hour=23, minute=59, second=59, microsecond=999999)
        },
        'yesterday': {
            'start': (base_time - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
            'end': (base_time - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        },
        'last_week': {
            'start': base_time - timedelta(days=7),
            'end': base_time
        },
        'last_month': {
            'start': base_time - timedelta(days=30),
            'end': base_time
        },
        'last_quarter': {
            'start': base_time - timedelta(days=90),
            'end': base_time
        }
    }


@pytest.fixture
def mock_request_reports(authenticated_reports_request):
    """Mock request for forms and views testing"""
    return authenticated_reports_request