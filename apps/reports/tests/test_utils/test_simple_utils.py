"""
Simplified Tests for Reports Utils
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import pandas as pd
from apps.reports.utils import (
    BaseReportsExport, ReportEssentials, format_data, 
    generate_days_in_range, get_day_header
)


class TestBaseReportsExportSimple:
    """Simplified test suite for BaseReportsExport class"""
    
    def test_base_reports_export_initialization(self):
        """Test BaseReportsExport initialization"""
        export = BaseReportsExport(
            filename='test_report',
            client_id=1,
            design_file='test_template.html',
            data=[{'name': 'test', 'value': 100}]
        )
        
        assert export.filename == 'test_report'
        assert export.client_id == 1
        assert export.design_file == 'test_template.html'
        assert export.data == [{'name': 'test', 'value': 100}]
        assert export.returnfile is False
    
    def test_get_col_widths_basic(self):
        """Test BaseReportsExport get_col_widths method"""
        df = pd.DataFrame({
            'short': ['a', 'b'],
            'medium_length': ['hello', 'world'],
            'very_long_column_name': ['very long content here', 'another long content']
        })
        
        export = BaseReportsExport(filename='test', client_id=1)
        widths = export.get_col_widths(df)
        
        assert len(widths) == 3
        assert all(isinstance(w, int) for w in widths)
        assert widths[2] > widths[1] > widths[0]  # Longer columns should have greater width
    
    def test_excel_columns_override(self):
        """Test BaseReportsExport excel_columns method can be overridden"""
        class CustomExport(BaseReportsExport):
            def excel_columns(self, df):
                df['custom_column'] = 'custom_value'
                return df
        
        export = CustomExport(filename='test', client_id=1)
        df = pd.DataFrame({'original': [1, 2, 3]})
        
        result = export.excel_columns(df)
        
        assert 'custom_column' in result.columns
        assert result['custom_column'].iloc[0] == 'custom_value'


class TestReportEssentialsSimple:
    """Simplified test suite for ReportEssentials class"""
    
    def test_report_essentials_initialization(self):
        """Test ReportEssentials initialization"""
        essentials = ReportEssentials(report_name='TASKSUMMARY')
        
        assert essentials.report_name == 'TASKSUMMARY'
        assert essentials.TaskSummary == 'TASKSUMMARY'
        assert essentials.TourSummary == 'TOURSUMMARY'
        assert essentials.PPMSummary == 'PPMSUMMARY'
    
    def test_report_essentials_constants(self):
        """Test ReportEssentials has all expected constants"""
        essentials = ReportEssentials(report_name='TEST')
        
        # Test that all expected report type constants exist
        expected_constants = [
            'TaskSummary', 'TourSummary', 'ListOfTasks', 'ListOfTickets',
            'PPMSummary', 'SiteReport', 'ListOfTours', 'WorkOrderList',
            'SiteVisitReport', 'PeopleQR', 'AssetQR', 'CheckpointQR',
            'AssetwiseTaskStatus', 'StaticDetailedTourSummary', 
            'DynamicDetailedTourSummary', 'LogSheet', 'RP_SiteVisitReport'
        ]
        
        for constant in expected_constants:
            assert hasattr(essentials, constant)
            assert isinstance(getattr(essentials, constant), str)


class TestUtilityFunctionsSimple:
    """Simplified test suite for utility functions"""
    
    def test_format_data_function_basic(self):
        """Test format_data function with basic data"""
        input_data = [
            {
                'department': 'IT',
                'designation': 'Developer',
                'peoplecode': 'EMP001',
                'peoplename': 'John Doe',
                'day': 1,
                'day_of_week': 'Mon',
                'punch_intime': '09:00',
                'punch_outtime': '18:00',
                'totaltime': '09:00'
            }
        ]
        
        result = format_data(input_data)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert 'IT' in result[0]
        assert 'Developer' in result[0]['IT']
        assert 'EMP001' in result[0]['IT']['Developer']
    
    def test_format_data_none_handling(self):
        """Test format_data function handles NONE values"""
        input_data = [
            {
                'department': 'NONE',
                'designation': 'NONE',
                'peoplecode': 'EMP001',
                'peoplename': 'John Doe',
                'day': 1,
                'day_of_week': ' Mon ',  # With spaces
                'punch_intime': '09:00',
                'punch_outtime': '18:00',
                'totaltime': '09:00'
            }
        ]
        
        result = format_data(input_data)
        
        # Test that NONE values are converted to --
        assert '--' in result[0]
        
        # Test that day_of_week spaces are stripped
        emp_data = result[0]['--']['--']['EMP001'][0]
        assert emp_data['day_of_week'] == 'Mon'
    
    def test_generate_days_in_range_basic(self):
        """Test generate_days_in_range function"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)
        
        days = generate_days_in_range(start_date, end_date)
        
        assert len(days) == 3
        assert days[0] == (1, 'Mon', 'Jan')
        assert days[1] == (2, 'Tue', 'Jan')
        assert days[2] == (3, 'Wed', 'Jan')
    
    def test_generate_days_in_range_single_day(self):
        """Test generate_days_in_range function with single day"""
        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 15)
        
        days = generate_days_in_range(start_date, end_date)
        
        assert len(days) == 1
        assert days[0][0] == 15  # Day of month
        assert days[0][2] == 'Jan'  # Month abbreviation
    
    def test_get_day_header_basic(self):
        """Test get_day_header function with basic data"""
        data = [
            {
                'day': '1',
                'day_of_week': 'Mon',
                'month': '01',
                'year': '2024'
            },
            {
                'day': '2',
                'day_of_week': 'Tue',
                'month': '01',
                'year': '2024'
            }
        ]
        
        start_date = '01/01/2024 00:00:00'
        end_date = '03/01/2024 23:59:59'
        
        result = get_day_header(data, start_date, end_date)
        
        assert isinstance(result, list)
        assert len(result) == 2  # [day_numbers, day_names]
        assert isinstance(result[0], list)  # day numbers
        assert isinstance(result[1], list)  # day names
        assert len(result[0]) > 0  # Should have some days
        assert len(result[1]) > 0  # Should have some day names


class TestBaseReportsExportMethods:
    """Test BaseReportsExport methods that don't require complex setup"""
    
    def test_excel_columns_default(self):
        """Test BaseReportsExport default excel_columns method"""
        export = BaseReportsExport(filename='test', client_id=1)
        df = pd.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
        
        # Default implementation should return the DataFrame unchanged
        result = export.excel_columns(df)
        
        assert result.equals(df)
        assert list(result.columns) == ['col1', 'col2']
    
    def test_get_col_widths_empty_dataframe(self):
        """Test get_col_widths with empty DataFrame"""
        export = BaseReportsExport(filename='test', client_id=1)
        df = pd.DataFrame()
        
        widths = export.get_col_widths(df)
        
        assert isinstance(widths, list)
        assert len(widths) == 0
    
    def test_get_col_widths_single_column(self):
        """Test get_col_widths with single column DataFrame"""
        export = BaseReportsExport(filename='test', client_id=1)
        df = pd.DataFrame({'single_col': ['short', 'medium_length_text', 'very_very_long_text_content']})
        
        widths = export.get_col_widths(df)
        
        assert len(widths) == 1
        assert widths[0] > 10  # Should be at least as long as the longest content


class TestUtilityFunctionEdgeCases:
    """Test utility functions with edge cases"""
    
    def test_format_data_empty_input(self):
        """Test format_data with empty input"""
        result = format_data([])
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert len(result[0]) == 0
    
    def test_generate_days_same_start_end(self):
        """Test generate_days_in_range with same start and end"""
        same_date = datetime(2024, 2, 29)  # Leap year date
        
        days = generate_days_in_range(same_date, same_date)
        
        assert len(days) == 1
        assert days[0] == (29, 'Thu', 'Feb')
    
    def test_format_data_decimal_day_conversion(self):
        """Test format_data converts Decimal day to int"""
        from decimal import Decimal
        
        input_data = [
            {
                'department': 'Finance',
                'designation': 'Analyst',
                'peoplecode': 'EMP001',
                'peoplename': 'Jane Smith',
                'day': Decimal('15'),  # Decimal day
                'day_of_week': 'Wed',
                'punch_intime': '08:30',
                'punch_outtime': '17:30',
                'totaltime': '09:00'
            }
        ]
        
        result = format_data(input_data)
        
        # Check that the day was converted to int
        emp_data = result[0]['Finance']['Analyst']['EMP001'][0]
        assert emp_data['day'] == 15
        assert isinstance(emp_data['day'], int)