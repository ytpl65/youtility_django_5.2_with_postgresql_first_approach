"""
Tests for ScheduleReport model
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta, time
from apps.reports.models import ScheduleReport


@pytest.mark.django_db
class TestScheduleReportModel:
    """Test suite for ScheduleReport model"""
    
    def test_schedule_report_creation_basic(self, schedule_report_factory):
        """Test creating a basic ScheduleReport instance"""
        schedule_report = schedule_report_factory()
        
        assert schedule_report.id is not None
        assert schedule_report.report_type == 'TASKSUMMARY'
        assert schedule_report.filename is not None
        assert schedule_report.report_name is not None
        assert schedule_report.enable is True
        assert schedule_report.workingdays == '5'
        assert schedule_report.cron is not None
        assert schedule_report.report_sendtime is not None
    
    
    def test_schedule_report_str_representation(self, schedule_report_factory):
        """Test ScheduleReport string representation"""
        schedule_report = schedule_report_factory(
            report_name='Daily Task Summary',
            report_type='TASKSUMMARY'
        )
        
        # Test if it has a proper string representation (inherited from BaseModel)
        str_repr = str(schedule_report)
        assert 'Daily Task Summary' in str_repr or 'TASKSUMMARY' in str_repr
    
    
    def test_schedule_report_template_choices(self, schedule_report_factory, report_template_choices):
        """Test ScheduleReport template choices"""
        # Test different report templates
        for template_code, template_name in report_template_choices[:5]:  # Test first 5
            if template_code:  # Skip empty choice
                schedule_report = schedule_report_factory(
                    report_type=template_code,
                    report_name=f'{template_name} Schedule'
                )
                assert schedule_report.report_type == template_code
    
    
    def test_schedule_report_relationships(self, schedule_report_factory, test_client_reports, test_bu_reports):
        """Test ScheduleReport foreign key relationships"""
        schedule_report = schedule_report_factory(
            client=test_client_reports,
            bu=test_bu_reports
        )
        
        # Test forward relationships
        assert schedule_report.client == test_client_reports
        assert schedule_report.bu == test_bu_reports
        
        # Test reverse relationships
        assert schedule_report in test_client_reports.schd_clients.all()
        assert schedule_report in test_bu_reports.schd_sites.all()
    
    
    def test_schedule_report_working_days_choices(self, schedule_report_factory, working_days_choices):
        """Test ScheduleReport working days choices"""
        for days_code, days_name in working_days_choices:
            schedule_report = schedule_report_factory(
                workingdays=days_code,
                report_name=f'Report for {days_name}'
            )
            assert schedule_report.workingdays == days_code
    
    
    def test_schedule_report_cron_expressions(self, schedule_report_factory, sample_cron_expressions):
        """Test ScheduleReport cron expressions"""
        for cron_name, cron_expr in sample_cron_expressions.items():
            schedule_report = schedule_report_factory(
                cron=cron_expr,
                report_name=f'Report {cron_name}',
                crontype=cron_name.upper()
            )
            assert schedule_report.cron == cron_expr
            assert schedule_report.crontype == cron_name.upper()
    
    
    def test_schedule_report_email_arrays(self, schedule_report_factory, sample_email_data):
        """Test ScheduleReport email array fields"""
        schedule_report = schedule_report_factory(
            to_addr=sample_email_data['to_addr'],
            cc=sample_email_data['cc'],
            report_name='Email Test Report'
        )
        
        # Test to_addr array field
        assert 'admin@example.com' in schedule_report.to_addr
        assert 'manager@example.com' in schedule_report.to_addr
        assert len(schedule_report.to_addr) == 2
        
        # Test cc array field
        assert 'supervisor@example.com' in schedule_report.cc
        assert 'analyst@example.com' in schedule_report.cc
        assert len(schedule_report.cc) == 2
    
    
    def test_schedule_report_json_params_field(self, schedule_report_factory, sample_report_params):
        """Test ScheduleReport report_params JSON field"""
        schedule_report = schedule_report_factory(
            report_params={
                'report_params': sample_report_params
            }
        )
        
        assert schedule_report.report_params is not None
        assert schedule_report.report_params['report_params']['date_range'] == 'last_30_days'
        assert schedule_report.report_params['report_params']['output_format'] == 'pdf'
        assert schedule_report.report_params['report_params']['include_charts'] is True
    
    
    def test_schedule_report_datetime_fields(self, schedule_report_factory):
        """Test ScheduleReport datetime fields"""
        now = timezone.now()
        from_datetime = now - timedelta(hours=1)
        upto_datetime = now + timedelta(hours=1)
        last_generated = now - timedelta(minutes=30)
        
        schedule_report = schedule_report_factory(
            fromdatetime=from_datetime,
            uptodatetime=upto_datetime,
            lastgeneratedon=last_generated
        )
        
        assert schedule_report.fromdatetime == from_datetime
        assert schedule_report.uptodatetime == upto_datetime
        assert schedule_report.lastgeneratedon == last_generated
    
    
    def test_schedule_report_time_field(self, schedule_report_factory):
        """Test ScheduleReport report_sendtime field"""
        send_times = [
            time(9, 0),    # 9:00 AM
            time(12, 30),  # 12:30 PM
            time(18, 0),   # 6:00 PM
            time(23, 59)   # 11:59 PM
        ]
        
        for send_time in send_times:
            schedule_report = schedule_report_factory(
                report_sendtime=send_time,
                report_name=f'Report at {send_time}'
            )
            assert schedule_report.report_sendtime == send_time
    
    
    def test_schedule_report_enable_disable_functionality(self, schedule_report_factory):
        """Test ScheduleReport enable/disable functionality"""
        enabled_report = schedule_report_factory(
            report_name='Enabled Report',
            enable=True
        )
        
        disabled_report = schedule_report_factory(
            report_name='Disabled Report',
            enable=False
        )
        
        assert enabled_report.enable is True
        assert disabled_report.enable is False
        
        # Test filtering by enabled status
        enabled_reports = ScheduleReport.objects.filter(enable=True)
        disabled_reports = ScheduleReport.objects.filter(enable=False)
        
        assert enabled_report in enabled_reports
        assert disabled_report in disabled_reports
        assert enabled_report not in disabled_reports
        assert disabled_report not in enabled_reports
    
    
    def test_schedule_report_unique_constraints(self, schedule_report_factory, test_client_reports, test_bu_reports):
        """Test ScheduleReport unique constraints"""
        common_params = {
            'cron': '0 9 * * *',
            'report_type': 'TASKSUMMARY',
            'bu': test_bu_reports,
            'report_params': {'report_params': {'filter': 'test'}}
        }
        
        # Create first schedule report
        schedule_report1 = schedule_report_factory(**common_params)
        
        # Try to create duplicate - should raise IntegrityError
        with pytest.raises(IntegrityError):
            schedule_report_factory(**common_params)
    
    
    def test_schedule_report_daily_schedule(self, schedule_report_factory):
        """Test ScheduleReport for daily scheduling"""
        daily_report = schedule_report_factory(
            report_type='TASKSUMMARY',
            report_name='Daily Task Summary',
            cron='0 9 * * *',  # Every day at 9 AM
            crontype='DAILY',
            workingdays='5',  # Monday-Friday
            report_sendtime=time(9, 0)
        )
        
        assert daily_report.crontype == 'DAILY'
        assert daily_report.workingdays == '5'
        assert daily_report.report_sendtime == time(9, 0)
        assert daily_report.cron == '0 9 * * *'
    
    
    def test_schedule_report_weekly_schedule(self, schedule_report_factory):
        """Test ScheduleReport for weekly scheduling"""
        weekly_report = schedule_report_factory(
            report_type='TOURSUMMARY',
            report_name='Weekly Tour Summary',
            cron='0 8 * * 1',  # Every Monday at 8 AM
            crontype='WEEKLY',
            workingdays='6',  # Monday-Saturday
            report_sendtime=time(8, 0)
        )
        
        assert weekly_report.crontype == 'WEEKLY'
        assert weekly_report.workingdays == '6'
        assert weekly_report.cron == '0 8 * * 1'
    
    
    def test_schedule_report_monthly_schedule(self, schedule_report_factory):
        """Test ScheduleReport for monthly scheduling"""
        monthly_report = schedule_report_factory(
            report_type='PPMSUMMARY',
            report_name='Monthly PPM Summary',
            cron='0 10 1 * *',  # First day of month at 10 AM
            crontype='MONTHLY',
            report_sendtime=time(10, 0)
        )
        
        assert monthly_report.crontype == 'MONTHLY'
        assert monthly_report.cron == '0 10 1 * *'
        assert monthly_report.report_sendtime == time(10, 0)
    
    
    def test_schedule_report_complex_params(self, schedule_report_factory):
        """Test ScheduleReport with complex parameter structures"""
        complex_params = {
            'report_params': {
                'filters': {
                    'date_range': 'last_7_days',
                    'status': ['completed', 'in_progress'],
                    'priority': ['high', 'medium'],
                    'assets': [1, 2, 3, 4, 5]
                },
                'grouping': {
                    'primary': 'asset_category',
                    'secondary': 'status'
                },
                'output': {
                    'format': 'pdf',
                    'include_charts': True,
                    'include_summary': True
                },
                'email_settings': {
                    'subject_prefix': '[AUTO-REPORT]',
                    'include_attachment': True,
                    'compress_attachment': True
                }
            }
        }
        
        schedule_report = schedule_report_factory(
            report_name='Complex Parameters Report',
            report_params=complex_params
        )
        
        # Test nested parameter access
        params = schedule_report.report_params['report_params']
        assert params['filters']['date_range'] == 'last_7_days'
        assert 'completed' in params['filters']['status']
        assert params['grouping']['primary'] == 'asset_category'
        assert params['output']['format'] == 'pdf'
        assert params['email_settings']['subject_prefix'] == '[AUTO-REPORT]'
    
    
    def test_schedule_report_filename_generation(self, schedule_report_factory):
        """Test ScheduleReport filename field"""
        schedule_report = schedule_report_factory(
            report_type='LISTOFTASKS',
            report_name='Task List Report',
            filename='task_list_2024.pdf'
        )
        
        assert schedule_report.filename == 'task_list_2024.pdf'
        assert '.pdf' in schedule_report.filename
    
    
    def test_schedule_report_bulk_operations(self, schedule_report_factory, test_client_reports, test_bu_reports):
        """Test bulk operations on ScheduleReport"""
        # Create multiple schedule report records
        reports = []
        report_types = ['TASKSUMMARY', 'TOURSUMMARY', 'PPMSUMMARY', 'LISTOFTASKS']
        
        for i in range(20):
            report = schedule_report_factory(
                report_type=report_types[i % len(report_types)],
                report_name=f'Bulk Schedule Report {i}',
                enable=True if i % 2 == 0 else False,
                workingdays='5' if i % 3 == 0 else '6',
                cron=f'{i % 60} {i % 24} * * *',  # Unique cron for each
                client=test_client_reports,
                bu=test_bu_reports
            )
            reports.append(report)
        
        # Test bulk filtering by report type
        task_summaries = ScheduleReport.objects.filter(report_type='TASKSUMMARY')
        tour_summaries = ScheduleReport.objects.filter(report_type='TOURSUMMARY')
        
        assert task_summaries.count() == 5  # 0,4,8,12,16
        assert tour_summaries.count() == 5  # 1,5,9,13,17
        
        # Test bulk filtering by enabled status
        enabled_reports = ScheduleReport.objects.filter(enable=True)
        disabled_reports = ScheduleReport.objects.filter(enable=False)
        
        assert enabled_reports.count() == 10  # Even indices
        assert disabled_reports.count() == 10  # Odd indices
        
        # Test bulk filtering by working days
        weekday_reports = ScheduleReport.objects.filter(workingdays='5')
        six_day_reports = ScheduleReport.objects.filter(workingdays='6')
        
        assert weekday_reports.count() >= 6  # Every 3rd record
        assert six_day_reports.count() >= 13  # Remaining records
    
    
    def test_schedule_report_filtering_by_client_and_bu(self, schedule_report_factory, test_client_reports, test_bu_reports):
        """Test ScheduleReport filtering by client and BU"""
        # Create another client and BU
        other_client = test_client_reports.__class__.objects.create(
            bucode='OTHERSCHDCLIENT',
            buname='Other Schedule Client',
            enable=True
        )
        
        other_bu = test_bu_reports.__class__.objects.create(
            bucode='OTHERSCHDBU',
            buname='Other Schedule BU',
            parent=other_client,
            enable=True
        )
        
        # Create reports for different clients and BUs
        report1 = schedule_report_factory(
            client=test_client_reports,
            bu=test_bu_reports,
            report_name='Client1 BU1 Schedule',
            cron='0 9 * * *'
        )
        
        report2 = schedule_report_factory(
            client=test_client_reports,
            bu=other_bu,
            report_name='Client1 BU2 Schedule',
            cron='0 10 * * *'
        )
        
        report3 = schedule_report_factory(
            client=other_client,
            bu=test_bu_reports,
            report_name='Client2 BU1 Schedule',
            cron='0 11 * * *'
        )
        
        # Test filtering by client
        client1_reports = ScheduleReport.objects.filter(client=test_client_reports)
        client2_reports = ScheduleReport.objects.filter(client=other_client)
        
        assert report1 in client1_reports
        assert report2 in client1_reports
        assert report3 not in client1_reports
        
        assert report3 in client2_reports
        assert report1 not in client2_reports
        assert report2 not in client2_reports
    
    
    def test_schedule_report_cron_validation_scenarios(self, schedule_report_factory):
        """Test ScheduleReport cron expression scenarios"""
        cron_scenarios = [
            ('0 9 * * *', 'Daily at 9 AM'),
            ('0 8 * * 1', 'Weekly on Monday at 8 AM'),
            ('0 10 1 * *', 'Monthly on 1st at 10 AM'),
            ('*/15 * * * *', 'Every 15 minutes'),
            ('0 18 * * 1-5', 'Weekdays at 6 PM'),
            ('0 0 1 1 *', 'Yearly on January 1st')
        ]
        
        for cron_expr, description in cron_scenarios:
            schedule_report = schedule_report_factory(
                cron=cron_expr,
                report_name=f'Report: {description}',
                crontype='CUSTOM'
            )
            assert schedule_report.cron == cron_expr
            assert schedule_report.crontype == 'CUSTOM'
    
    
    def test_schedule_report_email_recipients_scenarios(self, schedule_report_factory):
        """Test ScheduleReport email recipient scenarios"""
        # Single recipient
        single_recipient = schedule_report_factory(
            report_name='Single Recipient Report',
            to_addr=['manager@company.com'],
            cc=[]
        )
        
        # Multiple recipients
        multiple_recipients = schedule_report_factory(
            report_name='Multiple Recipients Report',
            to_addr=['manager@company.com', 'supervisor@company.com', 'admin@company.com'],
            cc=['analyst@company.com', 'director@company.com']
        )
        
        # No CC recipients
        no_cc_recipients = schedule_report_factory(
            report_name='No CC Report',
            to_addr=['operations@company.com'],
            cc=[]
        )
        
        assert len(single_recipient.to_addr) == 1
        assert len(single_recipient.cc) == 0
        
        assert len(multiple_recipients.to_addr) == 3
        assert len(multiple_recipients.cc) == 2
        assert 'manager@company.com' in multiple_recipients.to_addr
        assert 'analyst@company.com' in multiple_recipients.cc
        
        assert len(no_cc_recipients.to_addr) == 1
        assert len(no_cc_recipients.cc) == 0
    
    
    def test_schedule_report_performance_queries(self, schedule_report_factory, test_client_reports, test_bu_reports):
        """Test performance-oriented queries on ScheduleReport"""
        # Create many schedule report records for performance testing
        reports = []
        for i in range(100):
            report = schedule_report_factory(
                report_type='TASKSUMMARY' if i % 4 == 0 else 'TOURSUMMARY',
                report_name=f'Performance Schedule {i}',
                enable=True if i % 3 == 0 else False,
                workingdays='5' if i % 5 == 0 else '6',
                cron=f'{i % 60} {i % 24} * * *',  # Unique cron for each
                client=test_client_reports,
                bu=test_bu_reports
            )
            reports.append(report)
        
        # Test count queries
        total_count = ScheduleReport.objects.filter(
            client=test_client_reports
        ).count()
        assert total_count >= 100
        
        # Test report type filtering
        task_summary_count = ScheduleReport.objects.filter(
            client=test_client_reports,
            report_type='TASKSUMMARY'
        ).count()
        tour_summary_count = ScheduleReport.objects.filter(
            client=test_client_reports,
            report_type='TOURSUMMARY'
        ).count()
        
        assert task_summary_count == 25  # Every 4th record
        assert tour_summary_count == 75  # Remaining records
        
        # Test enabled filtering
        enabled_count = ScheduleReport.objects.filter(
            client=test_client_reports,
            enable=True
        ).count()
        
        assert enabled_count >= 33  # Every 3rd record
    
    
    def test_schedule_report_scheduling_workflow(self, schedule_report_factory):
        """Test ScheduleReport scheduling workflow"""
        now = timezone.now()
        
        # Create a scheduled report
        schedule_report = schedule_report_factory(
            report_type='LISTOFTASKS',
            report_name='Workflow Test Report',
            cron='0 9 * * *',
            crontype='DAILY',
            enable=True,
            fromdatetime=now - timedelta(days=1),
            uptodatetime=now + timedelta(days=1),
            lastgeneratedon=None  # Not generated yet
        )
        
        # Simulate report generation
        schedule_report.lastgeneratedon = now
        schedule_report.save()
        
        # Update next scheduled time
        schedule_report.uptodatetime = now + timedelta(days=1)
        schedule_report.save()
        
        assert schedule_report.lastgeneratedon is not None
        assert schedule_report.uptodatetime > now
        assert schedule_report.enable is True