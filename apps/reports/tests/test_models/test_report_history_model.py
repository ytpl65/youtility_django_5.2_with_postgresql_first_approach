"""
Tests for ReportHistory model
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta
from apps.reports.models import ReportHistory


@pytest.mark.django_db
class TestReportHistoryModel:
    """Test suite for ReportHistory model"""
    
    def test_report_history_creation_basic(self, report_history_factory):
        """Test creating a basic ReportHistory instance"""
        report_history = report_history_factory()
        
        assert report_history.id is not None
        assert report_history.user is not None
        assert report_history.datetime is not None
        assert report_history.export_type == ReportHistory.ExportType.D
        assert report_history.report_name is not None
        assert report_history.has_data is True
        assert report_history.ctzoffset == 330
    
    
    def test_report_history_str_representation(self, report_history_factory, test_user_reports):
        """Test ReportHistory string representation"""
        report_history = report_history_factory(
            user=test_user_reports,
            report_name='Task Summary Report'
        )
        
        expected_str = f'User: {test_user_reports.peoplename} Report: Task Summary Report'
        assert str(report_history) == expected_str
    
    
    def test_report_history_export_type_choices(self, report_history_factory, export_type_choices):
        """Test ReportHistory export type choices"""
        # Test each export type
        for export_type in export_type_choices:
            report_history = report_history_factory(
                export_type=export_type,
                report_name=f'Report {export_type.value}'
            )
            assert report_history.export_type == export_type
    
    
    def test_report_history_relationships(self, report_history_factory, test_user_reports, test_client_reports, test_bu_reports):
        """Test ReportHistory foreign key relationships"""
        report_history = report_history_factory(
            user=test_user_reports,
            client=test_client_reports,
            bu=test_bu_reports
        )
        
        # Test forward relationships
        assert report_history.user == test_user_reports
        assert report_history.client == test_client_reports
        assert report_history.bu == test_bu_reports
        
        # Test reverse relationships
        assert report_history in test_user_reports.reporthistory_set.all()
        assert report_history in test_client_reports.rh_clients.all()
    
    
    def test_report_history_json_params_field(self, report_history_factory, sample_report_params):
        """Test ReportHistory params JSON field"""
        report_history = report_history_factory(
            params=sample_report_params
        )
        
        assert report_history.params is not None
        assert report_history.params['date_range'] == 'last_30_days'
        assert report_history.params['filters']['status'] == 'active'
        assert report_history.params['output_format'] == 'pdf'
        assert report_history.params['include_charts'] is True
    
    
    def test_report_history_email_fields(self, report_history_factory, sample_email_data):
        """Test ReportHistory email-related fields"""
        report_history = report_history_factory(
            export_type=ReportHistory.ExportType.E,
            to_mails=sample_email_data['to_mails'],
            cc_mails=sample_email_data['cc_mails'],
            email_body=sample_email_data['email_body']
        )
        
        assert report_history.export_type == ReportHistory.ExportType.E
        assert 'user1@example.com' in report_history.to_mails
        assert 'user2@example.com' in report_history.to_mails
        assert 'cc1@example.com' in report_history.cc_mails
        assert 'cc2@example.com' in report_history.cc_mails
        assert report_history.email_body == sample_email_data['email_body']
    
    
    def test_report_history_download_export(self, report_history_factory):
        """Test ReportHistory for download export type"""
        report_history = report_history_factory(
            export_type=ReportHistory.ExportType.D,
            report_name='Asset Status Report',
            has_data=True
        )
        
        assert report_history.export_type == ReportHistory.ExportType.D
        assert report_history.has_data is True
        assert report_history.to_mails is not None
        assert report_history.cc_mails is not None
    
    
    def test_report_history_email_export(self, report_history_factory):
        """Test ReportHistory for email export type"""
        report_history = report_history_factory(
            export_type=ReportHistory.ExportType.E,
            report_name='Weekly Maintenance Report',
            to_mails='manager@company.com,supervisor@company.com',
            cc_mails='admin@company.com',
            email_body='Weekly maintenance report attached.'
        )
        
        assert report_history.export_type == ReportHistory.ExportType.E
        assert 'manager@company.com' in report_history.to_mails
        assert 'supervisor@company.com' in report_history.to_mails
        assert report_history.cc_mails == 'admin@company.com'
        assert 'maintenance report' in report_history.email_body
    
    
    def test_report_history_scheduled_export(self, report_history_factory):
        """Test ReportHistory for scheduled export type"""
        report_history = report_history_factory(
            export_type=ReportHistory.ExportType.S,
            report_name='Daily Task Summary',
            params={
                'schedule_time': '09:00:00',
                'frequency': 'daily',
                'recipients': ['daily-reports@company.com']
            }
        )
        
        assert report_history.export_type == ReportHistory.ExportType.S
        assert report_history.params['schedule_time'] == '09:00:00'
        assert report_history.params['frequency'] == 'daily'
        assert 'daily-reports@company.com' in report_history.params['recipients']
    
    
    def test_report_history_has_data_flag(self, report_history_factory):
        """Test ReportHistory has_data functionality"""
        # Report with data
        report_with_data = report_history_factory(
            report_name='Assets Report',
            has_data=True
        )
        
        # Report without data
        report_without_data = report_history_factory(
            report_name='Empty Report',
            has_data=False
        )
        
        assert report_with_data.has_data is True
        assert report_without_data.has_data is False
        
        # Test filtering
        reports_with_data = ReportHistory.objects.filter(has_data=True)
        reports_without_data = ReportHistory.objects.filter(has_data=False)
        
        assert report_with_data in reports_with_data
        assert report_without_data in reports_without_data
        assert report_with_data not in reports_without_data
        assert report_without_data not in reports_with_data
    
    
    def test_report_history_traceback_field(self, report_history_factory):
        """Test ReportHistory traceback field for error handling"""
        # Successful report (no traceback)
        successful_report = report_history_factory(
            report_name='Successful Report',
            traceback=None
        )
        
        # Failed report (with traceback)
        error_traceback = """
        Traceback (most recent call last):
          File "report_generator.py", line 42, in generate_report
            data = fetch_data()
          File "data_fetcher.py", line 15, in fetch_data
            raise DatabaseError("Connection timeout")
        DatabaseError: Connection timeout
        """
        
        failed_report = report_history_factory(
            report_name='Failed Report',
            traceback=error_traceback.strip(),
            has_data=False
        )
        
        assert successful_report.traceback is None
        assert failed_report.traceback is not None
        assert 'DatabaseError' in failed_report.traceback
        assert 'Connection timeout' in failed_report.traceback
        assert failed_report.has_data is False
    
    
    def test_report_history_timezone_handling(self, report_history_factory):
        """Test ReportHistory timezone handling"""
        # Test different timezone offsets
        timezones = [
            (330, 'Asia/Kolkata'),     # IST
            (0, 'UTC'),                # UTC
            (-300, 'America/New_York'), # EST
            (540, 'Asia/Tokyo')        # JST
        ]
        
        for offset, tz_name in timezones:
            report_history = report_history_factory(
                report_name=f'Report for {tz_name}',
                ctzoffset=offset
            )
            assert report_history.ctzoffset == offset
    
    
    def test_report_history_datetime_fields(self, report_history_factory):
        """Test ReportHistory datetime fields"""
        custom_datetime = timezone.now() - timedelta(hours=2)
        
        report_history = report_history_factory(
            datetime=custom_datetime
        )
        
        assert report_history.datetime == custom_datetime
        assert report_history.cdtz is not None
        assert report_history.mdtz is not None
        
        # Test that default datetime is recent
        recent_report = report_history_factory()
        time_diff = timezone.now() - recent_report.datetime
        assert time_diff.total_seconds() < 60  # Within last minute
    
    
    def test_report_history_filtering_by_user(self, report_history_factory, test_user_reports, test_client_reports, test_bu_reports):
        """Test ReportHistory filtering by user"""
        # Create another user
        other_user = test_user_reports.__class__.objects.create(
            peoplecode='OTHERUSER',
            peoplename='Other User',
            loginid='otheruser',
            email='other@example.com',
            mobno='9876543211',
            dateofbirth='1990-01-01',
            dateofjoin='2023-01-01',
            client=test_client_reports,
            bu=test_bu_reports,
            enable=True
        )
        
        # Create reports for different users
        user1_report = report_history_factory(
            user=test_user_reports,
            report_name='User 1 Report'
        )
        
        user2_report = report_history_factory(
            user=other_user,
            report_name='User 2 Report'
        )
        
        # Test filtering
        user1_reports = ReportHistory.objects.filter(user=test_user_reports)
        user2_reports = ReportHistory.objects.filter(user=other_user)
        
        assert user1_report in user1_reports
        assert user2_report in user2_reports
        assert user1_report not in user2_reports
        assert user2_report not in user1_reports
    
    
    def test_report_history_filtering_by_client_and_bu(self, report_history_factory, test_client_reports, test_bu_reports):
        """Test ReportHistory filtering by client and BU"""
        # Create another client and BU
        other_client = test_client_reports.__class__.objects.create(
            bucode='OTHERCLIENT',
            buname='Other Client',
            enable=True
        )
        
        other_bu = test_bu_reports.__class__.objects.create(
            bucode='OTHERBU',
            buname='Other BU',
            parent=other_client,
            enable=True
        )
        
        # Create reports for different clients and BUs
        report1 = report_history_factory(
            client=test_client_reports,
            bu=test_bu_reports,
            report_name='Client1 BU1 Report'
        )
        
        report2 = report_history_factory(
            client=test_client_reports,
            bu=other_bu,
            report_name='Client1 BU2 Report'
        )
        
        report3 = report_history_factory(
            client=other_client,
            bu=test_bu_reports,
            report_name='Client2 BU1 Report'
        )
        
        # Test filtering by client
        client1_reports = ReportHistory.objects.filter(client=test_client_reports)
        client2_reports = ReportHistory.objects.filter(client=other_client)
        
        assert report1 in client1_reports
        assert report2 in client1_reports
        assert report3 not in client1_reports
        
        assert report3 in client2_reports
        assert report1 not in client2_reports
        assert report2 not in client2_reports
    
    
    def test_report_history_bulk_operations(self, report_history_factory, test_user_reports):
        """Test bulk operations on ReportHistory"""
        # Create multiple report history records
        reports = []
        export_types = [ReportHistory.ExportType.D, ReportHistory.ExportType.E, ReportHistory.ExportType.S]
        
        for i in range(20):
            report = report_history_factory(
                user=test_user_reports,
                export_type=export_types[i % len(export_types)],
                report_name=f'Bulk Report {i}',
                has_data=True if i % 2 == 0 else False
            )
            reports.append(report)
        
        # Test bulk filtering by export type
        download_reports = ReportHistory.objects.filter(export_type=ReportHistory.ExportType.D)
        email_reports = ReportHistory.objects.filter(export_type=ReportHistory.ExportType.E)
        scheduled_reports = ReportHistory.objects.filter(export_type=ReportHistory.ExportType.S)
        
        assert download_reports.count() >= 6  # 0,3,6,9,12,15,18
        assert email_reports.count() >= 6     # 1,4,7,10,13,16,19
        assert scheduled_reports.count() >= 6  # 2,5,8,11,14,17
        
        # Test bulk filtering by has_data
        reports_with_data = ReportHistory.objects.filter(has_data=True)
        reports_without_data = ReportHistory.objects.filter(has_data=False)
        
        assert reports_with_data.count() == 10  # Even indices
        assert reports_without_data.count() == 10  # Odd indices
    
    
    def test_report_history_complex_params(self, report_history_factory):
        """Test ReportHistory with complex parameter structures"""
        complex_params = {
            'filters': {
                'date_range': {
                    'start': '2024-01-01',
                    'end': '2024-01-31'
                },
                'status': ['active', 'pending'],
                'priority': ['high', 'medium'],
                'categories': ['maintenance', 'inspection', 'repair'],
                'sites': [1, 2, 3, 4],
                'assets': {
                    'include': [101, 102, 103],
                    'exclude': [999]
                }
            },
            'grouping': {
                'primary': 'asset',
                'secondary': 'status',
                'aggregation': 'count'
            },
            'output': {
                'format': 'pdf',
                'orientation': 'landscape',
                'include_charts': True,
                'include_summary': True,
                'page_size': 'A4'
            },
            'customization': {
                'logo': True,
                'company_name': 'Test Company',
                'footer_text': 'Confidential Report',
                'color_scheme': 'blue'
            }
        }
        
        report_history = report_history_factory(
            report_name='Complex Parameters Report',
            params=complex_params
        )
        
        # Test nested parameter access
        assert report_history.params['filters']['date_range']['start'] == '2024-01-01'
        assert 'active' in report_history.params['filters']['status']
        assert report_history.params['grouping']['primary'] == 'asset'
        assert report_history.params['output']['format'] == 'pdf'
        assert report_history.params['customization']['company_name'] == 'Test Company'
    
    
    def test_report_history_performance_queries(self, report_history_factory, test_user_reports, test_client_reports, test_bu_reports):
        """Test performance-oriented queries on ReportHistory"""
        # Create many report history records for performance testing
        reports = []
        for i in range(100):
            report = report_history_factory(
                user=test_user_reports,
                export_type=ReportHistory.ExportType.D if i % 3 == 0 else ReportHistory.ExportType.E,
                report_name=f'Performance Report {i}',
                has_data=True if i % 4 == 0 else False,
                client=test_client_reports,
                bu=test_bu_reports
            )
            reports.append(report)
        
        # Test count queries
        total_count = ReportHistory.objects.filter(
            client=test_client_reports
        ).count()
        assert total_count >= 100
        
        # Test export type filtering
        download_count = ReportHistory.objects.filter(
            client=test_client_reports,
            export_type=ReportHistory.ExportType.D
        ).count()
        email_count = ReportHistory.objects.filter(
            client=test_client_reports,
            export_type=ReportHistory.ExportType.E
        ).count()
        
        assert download_count >= 33  # Every 3rd record
        assert email_count >= 67     # Remaining records
        
        # Test has_data filtering
        reports_with_data_count = ReportHistory.objects.filter(
            client=test_client_reports,
            has_data=True
        ).count()
        
        assert reports_with_data_count == 25  # Every 4th record
    
    
    def test_report_history_date_range_queries(self, report_history_factory, report_time_ranges):
        """Test ReportHistory date range queries"""
        # Create reports at different times
        yesterday_report = report_history_factory(
            report_name='Yesterday Report',
            datetime=report_time_ranges['yesterday']['start']
        )
        
        today_report = report_history_factory(
            report_name='Today Report',
            datetime=report_time_ranges['today']['start']
        )
        
        last_week_report = report_history_factory(
            report_name='Last Week Report',
            datetime=report_time_ranges['last_week']['start']
        )
        
        # Test date range filtering
        today_reports = ReportHistory.objects.filter(
            datetime__gte=report_time_ranges['today']['start'],
            datetime__lte=report_time_ranges['today']['end']
        )
        
        last_week_reports = ReportHistory.objects.filter(
            datetime__gte=report_time_ranges['last_week']['start'],
            datetime__lte=report_time_ranges['last_week']['end']
        )
        
        assert today_report in today_reports
        assert yesterday_report not in today_reports
        
        assert last_week_report in last_week_reports
        assert today_report in last_week_reports
        assert yesterday_report in last_week_reports