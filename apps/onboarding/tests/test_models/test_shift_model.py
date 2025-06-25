"""
Tests for Shift model
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import time, timedelta
from apps.onboarding.models import Shift


@pytest.mark.django_db
class TestShiftModel:
    """Test suite for Shift model"""
    
    def test_shift_creation_basic(self, shift_factory):
        """Test creating a basic Shift instance"""
        shift = shift_factory()
        
        assert shift.id is not None
        assert shift.shiftname is not None
        assert shift.starttime is not None
        assert shift.endtime is not None
        assert shift.shiftduration is not None
        assert shift.enable is True
        assert shift.nightshiftappicable is True
        assert shift.captchafreq == 10
    
    
    def test_shift_str_representation(self, shift_factory, shift_times):
        """Test Shift string representation"""
        shift = shift_factory(
            shiftname='Morning Shift',
            starttime=shift_times['morning']['start'],
            endtime=shift_times['morning']['end']
        )
        
        assert str(shift) == 'Morning Shift (09:00:00 - 17:00:00)'
    
    
    def test_shift_time_fields(self, shift_factory, shift_times):
        """Test Shift time-related fields"""
        # Test morning shift
        morning_shift = shift_factory(
            shiftname='Morning Shift',
            starttime=shift_times['morning']['start'],
            endtime=shift_times['morning']['end'],
            shiftduration=8
        )
        
        assert morning_shift.starttime == time(9, 0, 0)
        assert morning_shift.endtime == time(17, 0, 0)
        assert morning_shift.shiftduration == 8
        
        # Test night shift
        night_shift = shift_factory(
            shiftname='Night Shift',
            starttime=shift_times['night']['start'],
            endtime=shift_times['night']['end'],
            shiftduration=8
        )
        
        assert night_shift.starttime == time(22, 0, 0)
        assert night_shift.endtime == time(6, 0, 0)
        assert night_shift.shiftduration == 8
    
    
    def test_shift_relationships(self, shift_factory, test_client_bt, test_bu_bt, test_designation_type):
        """Test Shift foreign key relationships"""
        shift = shift_factory(
            client=test_client_bt,
            bu=test_bu_bt,
            designation=test_designation_type
        )
        
        # Test forward relationships
        assert shift.client == test_client_bt
        assert shift.bu == test_bu_bt
        assert shift.designation == test_designation_type
        
        # Test reverse relationships
        assert shift in test_client_bt.shift_client.all()
        assert shift in test_bu_bt.shift_bu.all()
        assert shift in test_designation_type.shift_set.all()
    
    
    def test_shift_unique_constraint(self, shift_factory, test_client_bt, test_bu_bt, test_designation_type):
        """Test Shift unique constraint on shiftname, bu, designation, client"""
        # Create first shift
        shift1 = shift_factory(
            shiftname='Unique Shift',
            bu=test_bu_bt,
            designation=test_designation_type,
            client=test_client_bt
        )
        
        # Try to create duplicate - should raise IntegrityError
        with pytest.raises(IntegrityError):
            shift_factory(
                shiftname='Unique Shift',
                bu=test_bu_bt,
                designation=test_designation_type,
                client=test_client_bt
            )
    
    
    def test_shift_people_count_field(self, shift_factory):
        """Test Shift people count field"""
        shift = shift_factory(
            peoplecount=25
        )
        
        assert shift.peoplecount == 25
        
        # Test with None (should be allowed)
        shift_no_count = shift_factory(
            peoplecount=None
        )
        
        assert shift_no_count.peoplecount is None
    
    
    def test_shift_night_shift_flag(self, shift_factory):
        """Test Shift night shift applicable flag"""
        # Test night shift enabled
        night_shift = shift_factory(
            shiftname='Night Shift',
            nightshiftappicable=True
        )
        
        assert night_shift.nightshiftappicable is True
        
        # Test night shift disabled
        day_shift = shift_factory(
            shiftname='Day Shift',
            nightshiftappicable=False
        )
        
        assert day_shift.nightshiftappicable is False
    
    
    def test_shift_captcha_frequency(self, shift_factory):
        """Test Shift captcha frequency field"""
        shift = shift_factory(
            captchafreq=30
        )
        
        assert shift.captchafreq == 30
        
        # Test default value
        default_shift = shift_factory()
        assert default_shift.captchafreq == 10
    
    
    def test_shift_data_json_field(self, shift_factory, test_designation_type):
        """Test Shift shift_data JSON field"""
        shift_data = {
            'SECURITY_GUARD': {'count': 10, 'hourly_rate': 100},
            'SUPERVISOR': {'count': 2, 'hourly_rate': 150},
            'CLEANER': {'count': 3, 'hourly_rate': 80}
        }
        
        shift = shift_factory(
            shift_data=shift_data,
            designation=test_designation_type
        )
        
        assert shift.shift_data is not None
        assert shift.shift_data['SECURITY_GUARD']['count'] == 10
        assert shift.shift_data['SUPERVISOR']['count'] == 2
        assert shift.shift_data['CLEANER']['count'] == 3
        assert shift.shift_data['SECURITY_GUARD']['hourly_rate'] == 100
    
    
    def test_shift_enable_disable_functionality(self, shift_factory):
        """Test Shift enable/disable functionality"""
        enabled_shift = shift_factory(
            shiftname='Enabled Shift',
            enable=True
        )
        
        disabled_shift = shift_factory(
            shiftname='Disabled Shift',
            enable=False
        )
        
        assert enabled_shift.enable is True
        assert disabled_shift.enable is False
        
        # Test filtering by enabled status
        enabled_shifts = Shift.objects.filter(enable=True)
        disabled_shifts = Shift.objects.filter(enable=False)
        
        assert enabled_shift in enabled_shifts
        assert disabled_shift in disabled_shifts
        assert enabled_shift not in disabled_shifts
        assert disabled_shift not in enabled_shifts
    
    
    def test_shift_common_shift_types(self, shift_factory, shift_times):
        """Test creating common shift types"""
        # Morning shift
        morning_shift = shift_factory(
            shiftname='Morning Shift',
            starttime=shift_times['morning']['start'],
            endtime=shift_times['morning']['end'],
            shiftduration=8,
            nightshiftappicable=False
        )
        
        # Evening shift
        evening_shift = shift_factory(
            shiftname='Evening Shift',
            starttime=shift_times['evening']['start'],
            endtime=shift_times['evening']['end'],
            shiftduration=8,
            nightshiftappicable=True
        )
        
        # Night shift
        night_shift = shift_factory(
            shiftname='Night Shift',
            starttime=shift_times['night']['start'],
            endtime=shift_times['night']['end'],
            shiftduration=8,
            nightshiftappicable=True
        )
        
        # Full day shift
        full_day_shift = shift_factory(
            shiftname='Full Day Shift',
            starttime=shift_times['full_day']['start'],
            endtime=shift_times['full_day']['end'],
            shiftduration=24,
            nightshiftappicable=True
        )
        
        # Verify creation and properties
        assert morning_shift.shiftname == 'Morning Shift'
        assert morning_shift.nightshiftappicable is False
        
        assert evening_shift.shiftname == 'Evening Shift'
        assert evening_shift.nightshiftappicable is True
        
        assert night_shift.shiftname == 'Night Shift'
        assert night_shift.nightshiftappicable is True
        
        assert full_day_shift.shiftname == 'Full Day Shift'
        assert full_day_shift.shiftduration == 24
    
    
    def test_shift_tenant_aware_functionality(self, shift_factory, test_client_bt, test_bu_bt):
        """Test Shift tenant-aware model functionality"""
        shift = shift_factory(
            shiftname='Tenant Test Shift',
            client=test_client_bt,
            bu=test_bu_bt
        )
        
        # Shift inherits from TenantAwareModel
        assert hasattr(shift, 'tenant_id')
        assert shift.client == test_client_bt
        assert shift.bu == test_bu_bt
    
    
    def test_shift_bulk_operations(self, shift_factory, test_client_bt, test_bu_bt):
        """Test bulk operations on Shift"""
        # Create multiple shift records
        shifts = []
        for i in range(15):
            shift = shift_factory(
                shiftname=f'Bulk Shift {i}',
                starttime=time((8 + i) % 24, 0, 0),
                endtime=time((16 + i) % 24, 0, 0),
                shiftduration=8,
                peoplecount=10 + i,
                enable=True if i % 2 == 0 else False,
                client=test_client_bt,
                bu=test_bu_bt
            )
            shifts.append(shift)
        
        # Test bulk filtering
        bulk_enabled = Shift.objects.filter(
            shiftname__startswith='Bulk Shift',
            enable=True
        )
        bulk_disabled = Shift.objects.filter(
            shiftname__startswith='Bulk Shift',
            enable=False
        )
        
        assert bulk_enabled.count() == 8  # 0,2,4,6,8,10,12,14
        assert bulk_disabled.count() == 7  # 1,3,5,7,9,11,13
        
        # Test bulk update
        Shift.objects.filter(
            shiftname__startswith='Bulk Shift'
        ).update(captchafreq=20)
        
        # Verify bulk update
        updated_shifts = Shift.objects.filter(
            shiftname__startswith='Bulk Shift',
            captchafreq=20
        )
        assert updated_shifts.count() == 15
    
    
    def test_shift_filtering_by_client_and_bu(self, shift_factory, test_client_bt, test_bu_bt):
        """Test Shift filtering by client and BU"""
        # Create another client and BU for comparison
        other_client = test_client_bt.__class__.objects.create(
            bucode='OTHER_CLIENT',
            buname='Other Client',
            enable=True
        )
        
        other_bu = test_bu_bt.__class__.objects.create(
            bucode='OTHER_BU',
            buname='Other BU',
            enable=True
        )
        
        # Create shifts for different clients and BUs
        shift1 = shift_factory(
            shiftname='Client1 BU1 Shift',
            client=test_client_bt,
            bu=test_bu_bt
        )
        
        shift2 = shift_factory(
            shiftname='Client1 BU2 Shift',
            client=test_client_bt,
            bu=other_bu
        )
        
        shift3 = shift_factory(
            shiftname='Client2 BU1 Shift',
            client=other_client,
            bu=test_bu_bt
        )
        
        shift4 = shift_factory(
            shiftname='Client2 BU2 Shift',
            client=other_client,
            bu=other_bu
        )
        
        # Test filtering by client
        client1_shifts = Shift.objects.filter(client=test_client_bt)
        client2_shifts = Shift.objects.filter(client=other_client)
        
        assert shift1 in client1_shifts
        assert shift2 in client1_shifts
        assert shift3 not in client1_shifts
        assert shift4 not in client1_shifts
        
        assert shift3 in client2_shifts
        assert shift4 in client2_shifts
        assert shift1 not in client2_shifts
        assert shift2 not in client2_shifts
        
        # Test filtering by BU
        bu1_shifts = Shift.objects.filter(bu=test_bu_bt)
        bu2_shifts = Shift.objects.filter(bu=other_bu)
        
        assert shift1 in bu1_shifts
        assert shift3 in bu1_shifts
        assert shift2 not in bu1_shifts
        assert shift4 not in bu1_shifts
        
        assert shift2 in bu2_shifts
        assert shift4 in bu2_shifts
        assert shift1 not in bu2_shifts
        assert shift3 not in bu2_shifts
    
    
    def test_shift_time_validation_scenarios(self, shift_factory):
        """Test various time validation scenarios for Shift"""
        # Normal shift: 9 AM to 5 PM
        normal_shift = shift_factory(
            shiftname='Normal Shift',
            starttime=time(9, 0, 0),
            endtime=time(17, 0, 0),
            shiftduration=8
        )
        
        # Night shift crossing midnight: 10 PM to 6 AM
        night_shift = shift_factory(
            shiftname='Night Shift',
            starttime=time(22, 0, 0),
            endtime=time(6, 0, 0),
            shiftduration=8,
            nightshiftappicable=True
        )
        
        # Split shift with break: 8 AM to 12 PM, then 1 PM to 5 PM
        split_shift = shift_factory(
            shiftname='Split Shift',
            starttime=time(8, 0, 0),
            endtime=time(17, 0, 0),
            shiftduration=8  # Actual working hours excluding break
        )
        
        # 12-hour shift
        long_shift = shift_factory(
            shiftname='Long Shift',
            starttime=time(7, 0, 0),
            endtime=time(19, 0, 0),
            shiftduration=12
        )
        
        # Verify all shifts were created successfully
        assert normal_shift.shiftduration == 8
        assert night_shift.nightshiftappicable is True
        assert split_shift.starttime == time(8, 0, 0)
        assert long_shift.shiftduration == 12
    
    
    def test_shift_designation_specific_data(self, shift_factory, typeassist_factory):
        """Test Shift with designation-specific data"""
        # Create different designations
        guard_designation = typeassist_factory(
            tacode='SECURITY_GUARD',
            taname='Security Guard'
        )
        
        supervisor_designation = typeassist_factory(
            tacode='SUPERVISOR',
            taname='Supervisor'
        )
        
        # Create shift for guards
        guard_shift = shift_factory(
            shiftname='Guard Shift',
            designation=guard_designation,
            peoplecount=15,
            shift_data={
                'SECURITY_GUARD': {
                    'count': 15,
                    'hourly_rate': 120,
                    'overtime_rate': 180,
                    'requirements': ['Physical fitness', 'Security training']
                }
            }
        )
        
        # Create shift for supervisors
        supervisor_shift = shift_factory(
            shiftname='Supervisor Shift',
            designation=supervisor_designation,
            peoplecount=3,
            shift_data={
                'SUPERVISOR': {
                    'count': 3,
                    'hourly_rate': 200,
                    'overtime_rate': 300,
                    'requirements': ['Management experience', 'Leadership skills']
                }
            }
        )
        
        # Verify designation-specific data
        assert guard_shift.designation.tacode == 'SECURITY_GUARD'
        assert guard_shift.shift_data['SECURITY_GUARD']['count'] == 15
        assert guard_shift.shift_data['SECURITY_GUARD']['hourly_rate'] == 120
        
        assert supervisor_shift.designation.tacode == 'SUPERVISOR'
        assert supervisor_shift.shift_data['SUPERVISOR']['count'] == 3
        assert supervisor_shift.shift_data['SUPERVISOR']['hourly_rate'] == 200
    
    
    def test_shift_performance_queries(self, shift_factory, test_client_bt, test_bu_bt):
        """Test performance-oriented queries on Shift"""
        # Create many shift records for performance testing
        shifts = []
        for i in range(50):
            hour = (8 + i) % 24
            shift = shift_factory(
                shiftname=f'Performance Shift {i:02d}',
                starttime=time(hour, 0, 0),
                endtime=time((hour + 8) % 24, 0, 0),
                shiftduration=8,
                peoplecount=10 + (i % 20),
                enable=True if i % 3 == 0 else False,
                nightshiftappicable=True if hour >= 18 or hour <= 6 else False,
                client=test_client_bt,
                bu=test_bu_bt
            )
            shifts.append(shift)
        
        # Test count queries
        total_count = Shift.objects.filter(
            shiftname__startswith='Performance Shift'
        ).count()
        assert total_count == 50
        
        # Test enabled/disabled filtering
        enabled_count = Shift.objects.filter(
            shiftname__startswith='Performance Shift',
            enable=True
        ).count()
        disabled_count = Shift.objects.filter(
            shiftname__startswith='Performance Shift',
            enable=False
        ).count()
        
        assert enabled_count == 17  # Every 3rd record (0, 3, 6, ..., 48)
        assert disabled_count == 33
        assert enabled_count + disabled_count == 50
        
        # Test night shift filtering
        night_shifts = Shift.objects.filter(
            shiftname__startswith='Performance Shift',
            nightshiftappicable=True
        )
        day_shifts = Shift.objects.filter(
            shiftname__startswith='Performance Shift',
            nightshiftappicable=False
        )
        
        assert night_shifts.count() > 0
        assert day_shifts.count() > 0
        assert night_shifts.count() + day_shifts.count() == 50