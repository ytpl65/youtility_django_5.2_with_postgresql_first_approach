from import_export import resources, fields, widgets as wg
from apps.activity.models.job_model import Job
from import_export.admin import ImportExportModelAdmin
from django.db.models import Q
from apps.activity.models.asset_model import Asset
from apps.activity.models.question_model import QuestionSet
from apps.service.validators import (
    clean_array_string, clean_code, clean_point_field, clean_string, validate_cron
)
from django.core.exceptions import ValidationError
from apps.peoples import models as pm
from apps.onboarding import models as om
from apps.core.widgets import BVForeignKeyWidget, BVForeignKeyWidgetUpdate, QsetFKWUpdate, TktCategoryFKWUpdate, AssetFKWUpdate, PeopleFKWUpdate, PgroupFKWUpdate
from datetime import time
import math
from apps.core import utils
import logging
logger = logging.getLogger('django')
def default_ta():
    return utils.get_or_create_none_typeassist()[0]

class PeopleFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return pm.People.objects.select_related().filter(
            (Q(client__bucode = row['Client*']) & Q(enable=True)) | 
            Q(peoplecode='NONE')
        )

class PgroupFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return pm.Pgroup.objects.select_related().filter(
            (Q(client__bucode = row['Client*']) & Q(enable=True)) | 
            Q(groupname='NONE')
        )
class QsetFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return QuestionSet.objects.select_related().filter(
            Q(qsetname='NONE') | (Q(client__bucode = row['Client*']) &  Q(enable=True))
        )
class AssetFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return Asset.objects.select_related().filter(
            Q(assetcode='NONE') | (Q(client__bucode = row['Client*']) & Q(enable=True))
        )
class TktCategoryFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return om.TypeAssist.objects.select_related().filter(
            tatype__tacode="NOTIFYCATEGORY"
        )
        
class ParentFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        qset = Job.objects.select_related().filter(
            (Q(client__bucode = row['Client*']) & Q(enable=True)) |
            Q(jobname='NONE'), identifier='INTERNALTOUR'
        )
        logger.info("possible job rows",qset.values_list("jobname", flat=True).order_by('-cdtz'))
        return qset

class BaseJobResource(resources.ModelResource):
    CLIENT      = fields.Field(attribute='client', column_name='Client*',widget=wg.ForeignKeyWidget(om.Bt, 'bucode'))
    SITE        = fields.Field(attribute='bu', column_name='Site*',widget=BVForeignKeyWidget(om.Bt, 'bucode'))
    NAME        = fields.Field(attribute='jobname', column_name='Name*')
    DESC        = fields.Field(attribute='jobdesc', column_name='Description*', default='')
    QSET        = fields.Field(attribute='qset', column_name='Question Set/Checklist*', widget=QsetFKW(QuestionSet, 'qsetname'))
    ASSET       = fields.Field(attribute='asset', column_name='Asset*', widget=AssetFKW(Asset, 'assetcode'))
    PARENT      = fields.Field(attribute='parent', column_name='Belongs To*', widget=wg.ForeignKeyWidget(Job, 'jobname'), default=utils.get_or_create_none_job)
    PDURATION   = fields.Field(attribute='planduration', column_name='Plan Duration*')
    GRACETIME   = fields.Field(attribute='gracetime', column_name='Gracetime Before*')
    EXPTIME     = fields.Field(attribute='expirytime', column_name='Gracetime After*')
    CRON        = fields.Field(attribute='cron', column_name='Scheduler*')
    FROMDATE    = fields.Field(attribute='fromdate', column_name='From Date*', widget=wg.DateTimeWidget())
    UPTODATE    = fields.Field(attribute='uptodate', column_name='Upto Date*', widget=wg.DateTimeWidget())
    SCANTYPE    = fields.Field(attribute='scantype', column_name='Scan Type*', default='QR')
    TKTCATEGORY = fields.Field(attribute='ticketcategory', column_name='Notify Category*', widget=TktCategoryFKW(om.TypeAssist, 'tacode'), default=default_ta)
    PRIORITY    = fields.Field(attribute='priority', column_name='Priority*', default='LOW')
    PEOPLE      = fields.Field(attribute='people', column_name='People*', widget= PeopleFKW(pm.People, 'peoplecode'))
    PGROUP      = fields.Field(attribute='pgroup', column_name='Group Name*', widget=PgroupFKW(pm.Pgroup, 'groupname'))
    STARTTIME   = fields.Field(attribute='starttime', column_name='Start Time', default=time(0,0,0), widget=wg.TimeWidget())
    ENDTIME     = fields.Field(attribute='endtime', column_name='End Time', default=time(0,0,0), widget=wg.TimeWidget())
    SEQNO       = fields.Field(attribute='seqno', column_name='Seq No', default=-1)
    ID          = fields.Field(attribute='id', column_name='ID')
    
    class Meta:
        model = Job
        skip_unchanged = True
        import_id_fields = ['ID']
        report_skipped = True

class TaskResource(BaseJobResource):
    IDF         = fields.Field(attribute='identifier', column_name='Identifier*', default='TASK')
    class Meta:
        model = Job
        skip_unchanged = True
        import_id_fields = ['ID']
        report_skipped = True
        fields = [
            'CLIENT', 'SITE', 'NAME', 'DESC', 'QSET', 'PDURATION', 'GRACETIME', 'EXPTIME','CRON', 'FROMDATE', 'UPTODATE', 'SCANTYPE', 'TKTCATEGORY', 'PRIORITY', 'PEOPLE','PGROUP', 'IDF', 'STARTTIME', 'ENDTIME', 'SEQNO', 'PARENT',
            'bu','client','seqno','parent','geofence','asset','qset','pgroup','people','priority','planduration','gracetime','expirytime','cron','fromdate','uptodate','scantype','ticketcategory','identifier','seqno','enable','geojson','other_info','frequency','scantype','ticketcategory','endtime','id','tenant','cuser','muser','starttime','shift','bu','client','seqno','parent','geofence','asset',
            'cdtz','mdtz','ctzoffset','jobname','jobdesc','lastgeneratedon','sgroup','ID','ASSET'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
        self.ctzoffset = kwargs.pop('ctzoffset', -1)
        
    
    def before_import_row(self, row, row_number, **kwargs):
        self.check_required_fields(row)
        self.validate_row(row)
        self.unique_record_check(row)
        self.check_valid_scantype(row)
        self.check_valid_priority(row)
        if not row.get('Identifier*'):
            row['Identifier*'] = 'TASK'
        super().before_import_row(row, **kwargs)

    def check_valid_scantype(self,row):
        valid_scantypes = ['QR','NFC','SKIP','ENTERED']
        scan_type = row.get('Scan Type*')
        if scan_type not in valid_scantypes:
            raise ValidationError(
                {
                    'Scan Type*': "%(type)s is not a valid Scan Type. Please select a valid Scan Type from %(valid)s" % {
                        "type": scan_type,
                        "valid": valid_scantypes
                    }
                }
            )
        
    def check_valid_priority(self,row):
        valid_priorities = ['LOW','MEDIUM','HIGH']
        priority = row.get('Priority*')
        if priority not in valid_priorities:
            raise ValidationError(
                {
                    'Priority*': "%(priority)s is not a valid Priority. Please select a valid Priority from %(valid)s" % {
                        "priority": priority,
                        "valid": valid_priorities
                    }
                }
            )
        
    def check_required_fields(self, row):
        required_fields = [
            'Name*', 'From Date*', 'Upto Date*', 'Scheduler*',
            'Notify Category*', 'Plan Duration*', 'Gracetime Before*', 'Gracetime After*',
            'Question Set/Checklist*', 'Asset*', 'Priority*', 'People*', 'Group Name*', 'Belongs To*']
        integer_fields = ['Plan Duration*', 'Gracetime Before*', 'Gracetime After*']
    
        for field in required_fields:
            if field in row:
                value = row.get(field)
                if field in integer_fields:
                    try:
                        int_value = int(value)
                        if int_value < 0:
                            raise ValidationError({field: f"{field} must be a non-negative integer"})
                    except (ValueError, TypeError):
                        raise ValidationError({field: f"{field} must be a valid integer"})
                elif value in [None, '']:
                    raise ValidationError({field: f"{field} is a required field"})
    
    def validate_row(self, row):
        row['Name*'] = clean_string(row['Name*'])
        row['Description*'] = clean_string(row['Description*'])
        row['Plan Duration*'] = int(row['Plan Duration*'])
        row['Gracetime Before*'] = int(row['Gracetime Before*'])
        row['Gracetime After*'] = int(row['Gracetime After*'])
        # check valid cron
        if not validate_cron(row['Scheduler*']):
            raise ValidationError({
                'Scheduler*': "Invalid value or Problematic Cron Expression for scheduler"
            })
    
    def unique_record_check(self, row):
        if Job.objects.filter(
            jobname = row['Name*'], asset__assetcode = row['Asset*'], qset__qsetname = row['Question Set/Checklist*'],
            identifier = 'TASK', client__bucode = row['Client*']
        ).exists():
            raise ValidationError('Record Already with these values are already exist')
    
    def before_save_instance(self, instance, using_transactions, dry_run=False):
        utils.save_common_stuff(self.request, instance, self.is_superuser, self.ctzoffset)



class TourResource(resources.ModelResource):
    CLIENT      = fields.Field(attribute='client', column_name='Client*',widget=wg.ForeignKeyWidget(om.Bt, 'bucode'), default=utils.get_or_create_none_bv)
    SITE        = fields.Field(attribute='bu', column_name='Site*',widget=BVForeignKeyWidget(om.Bt, 'bucode'))
    NAME        = fields.Field(attribute='jobname', column_name='Name*')
    DESC        = fields.Field(attribute='jobdesc', column_name='Description*', default='')
    QSET        = fields.Field(attribute='qset', column_name='Question Set/Checklist*', widget=QsetFKW(QuestionSet, 'qsetname'))
    ASSET       = fields.Field(attribute='asset', column_name='Asset*', widget=AssetFKW(Asset, 'assetcode'))
    PARENT      = fields.Field(attribute='parent', column_name='Belongs To*', widget=wg.ForeignKeyWidget(Job, 'jobname'), default=utils.get_or_create_none_job)
    PDURATION   = fields.Field(attribute='planduration', column_name='Plan Duration*')
    GRACETIME   = fields.Field(attribute='gracetime', column_name='Gracetime*')
    EXPTIME     = fields.Field(attribute='expirytime', column_name='Expiry Time*')
    CRON        = fields.Field(attribute='cron', column_name='Scheduler*')
    FROMDATE    = fields.Field(attribute='fromdate', column_name='From Date*', widget=wg.DateTimeWidget())
    UPTODATE    = fields.Field(attribute='uptodate', column_name='Upto Date*', widget=wg.DateTimeWidget())
    SCANTYPE    = fields.Field(attribute='scantype', column_name='Scan Type*', default='QR')
    TKTCATEGORY = fields.Field(attribute='ticketcategory', column_name='Notify Category*', widget=TktCategoryFKW(om.TypeAssist, 'tacode'), default=default_ta)
    PRIORITY    = fields.Field(attribute='priority', column_name='Priority*', default='LOW')
    PEOPLE      = fields.Field(attribute='people', column_name='People*', widget= PeopleFKW(pm.People, 'peoplecode'))
    PGROUP      = fields.Field(attribute='pgroup', column_name='Group Name*', widget=PgroupFKW(pm.Pgroup, 'groupname'))
    IDF         = fields.Field(attribute='identifier', column_name='Identifier*', default='INTERNALTOUR')
    STARTTIME   = fields.Field(attribute='starttime', column_name='Start Time', default=time(0,0,0), widget=wg.TimeWidget())
    ENDTIME     = fields.Field(attribute='endtime', column_name='End Time', default=time(0,0,0), widget=wg.TimeWidget())
    SEQNO       = fields.Field(attribute='seqno', column_name='Seq No*', default=-1)
    ID          = fields.Field(attribute='id', column_name='ID')

    class Meta:
        model = Job
        skip_unchanged = True
        import_id_fields = ['ID']
        report_skipped = True
        fields = [
            'CLIENT', 'SITE', 'NAME', 'DESC', 'QSET', 'PDURATION', 'GRACETIME', 'EXPTIME',
            'CRON', 'FROMDATE', 'UPTODATE', 'SCANTYPE', 'TKTCATEGORY', 'PRIORITY', 'PEOPLE',
            'PGROUP', 'IDF', 'STARTTIME', 'ENDTIME', 'SEQNO', 'PARENT', 'ASSET','ID'
        ]
    
    def __init__(self, *args, **kwargs):
        super(TourResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
        self.ctzoffset = kwargs.pop('ctzoffset', -1)
        
    
    def before_import_row(self, row, row_number, **kwargs):
        self.check_required_fields(row)
        self.validate_row(row)
        self.unique_record_check(row)
        super().before_import_row(row, **kwargs)
        
    def check_required_fields(self, row):
        required_fields = [
            'Name*', 'From Date*', 'Upto Date*', 'Scheduler*', 'Plan Duration*',
            'Notify Category*', 'Expiry Time*', 'Gracetime*', 'Seq No*',
            'Question Set/Checklist*', 'Asset*', 'Priority*', 'People*', 'Group Name*', 'Belongs To*']
        integer_fields = ['Plan Duration*', 'Gracetime*', 'Expiry Time*', 'Seq No*']
    
        for field in required_fields:
            if field in row:
                value = row.get(field)
                if field in integer_fields:
                    try:
                        int_value = int(value)
                        if int_value < 0:
                            raise ValidationError({field: f"{field} must be a non-negative integer"})
                    except (ValueError, TypeError):
                        raise ValidationError({field: f"{field} must be a valid integer"})
                elif value in [None, '']:
                    raise ValidationError({field: f"{field} is a required field"})
    
    def validate_row(self, row):
        row['Identifier*'] = 'INTERNALTOUR'
        row['Name*'] = clean_string(row['Name*'])
        row['Description*'] = clean_string(row['Description*'])
        row['Plan Duration*'] = int(row['Plan Duration*'])
        row['Gracetime*'] = int(row['Gracetime*'])
        row['Expiry Time*'] = int(row['Expiry Time*'])
        row['Seq No*'] = int(row['Seq No*'])
        # check valid cron
        if not validate_cron(row['Scheduler*']):
            raise ValidationError({
                'Scheduler*': "Invalid value or Problematic Cron Expression for scheduler"
            })
    
    def unique_record_check(self, row):
        if Job.objects.filter(
            jobname = row['Name*'], bu__bucode=row["Site*"],
            identifier = 'INTERNALTOUR', client__bucode = row['Client*']
        ).exists():
            raise ValidationError('Record Already with these values are already exist')
    
    def before_save_instance(self, instance, using_transactions, dry_run=False):
        parent = instance.parent
        if parent and parent.jobname !='NONE':
            instance.jobdesc = f"{parent.jobname} :: {instance.asset.assetname} :: {instance.qset.qsetname}"
            instance.save()
        utils.save_common_stuff(self.request, instance, self.is_superuser)

class TaskResourceUpdate(resources.ModelResource):
    CLIENT      = fields.Field(attribute='client', column_name='Client',widget=wg.ForeignKeyWidget(om.Bt, 'bucode'))
    SITE        = fields.Field(attribute='bu', column_name='Site',widget=BVForeignKeyWidgetUpdate(om.Bt, 'bucode'))
    NAME        = fields.Field(attribute='jobname', column_name='Name')
    DESC        = fields.Field(attribute='jobdesc', column_name='Description', default='')
    QSET        = fields.Field(attribute='qset', column_name='Question Set/Checklist', widget=QsetFKWUpdate(QuestionSet, 'qsetname'))
    ASSET       = fields.Field(attribute='asset', column_name='Asset', widget=AssetFKWUpdate(Asset, 'assetcode'))
    PARENT      = fields.Field(attribute='parent', column_name='Belongs To', widget=wg.ForeignKeyWidget(Job, 'jobname'), default=utils.get_or_create_none_job)
    PDURATION   = fields.Field(attribute='planduration', column_name='Plan Duration')
    GRACETIME   = fields.Field(attribute='gracetime', column_name='Gracetime Before')
    EXPTIME     = fields.Field(attribute='expirytime', column_name='Gracetime After')
    CRON        = fields.Field(attribute='cron', column_name='Scheduler')
    FROMDATE    = fields.Field(attribute='fromdate', column_name='From Date', widget=wg.DateTimeWidget())
    UPTODATE    = fields.Field(attribute='uptodate', column_name='Upto Date', widget=wg.DateTimeWidget())
    SCANTYPE    = fields.Field(attribute='scantype', column_name='Scan Type', default='QR')
    TKTCATEGORY = fields.Field(attribute='ticketcategory', column_name='Notify Category', widget=TktCategoryFKWUpdate(om.TypeAssist, 'tacode'), default=default_ta)
    PRIORITY    = fields.Field(attribute='priority', column_name='Priority', default='LOW')
    PEOPLE      = fields.Field(attribute='people', column_name='People', widget= PeopleFKWUpdate(pm.People, 'peoplecode'))
    PGROUP      = fields.Field(attribute='pgroup', column_name='Group Name', widget=PgroupFKWUpdate(pm.Pgroup, 'groupname'))
    STARTTIME   = fields.Field(attribute='starttime', column_name='Start Time', default=time(0,0,0), widget=wg.TimeWidget())
    ENDTIME     = fields.Field(attribute='endtime', column_name='End Time', default=time(0,0,0), widget=wg.TimeWidget())
    SEQNO       = fields.Field(attribute='seqno', column_name='Seq No', default=-1)
    ID          = fields.Field(attribute='id', column_name='ID*')
    
    class Meta:
        model = Job
        skip_unchanged = True
        #import_id_fields = ['ID']
        report_skipped = True
        fields = [
            'ID','CLIENT', 'SITE', 'NAME', 'DESC', 'QSET', 'ASSET','PDURATION', 'GRACETIME', 
            'EXPTIME', 'CRON', 'FROMDATE', 'UPTODATE', 'SCANTYPE', 'TKTCATEGORY', 'PRIORITY', 
            'PEOPLE', 'PGROUP', 'STARTTIME', 'ENDTIME', 'SEQNO', 'PARENT'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
        
    def before_import_row(self, row, row_number, **kwargs):
        self.check_required_fields(row)
        self.validate_row(row)
        self.check_record_exists(row)
        self.check_valid_scantype(row)
        self.check_valid_priority(row)
        super().before_import_row(row, **kwargs)

    def check_valid_scantype(self,row):
        if 'Scan Type' in row:
            valid_scantypes = ['QR','NFC','SKIP','ENTERED']
            scan_type = row.get('Scan Type')
            if scan_type not in valid_scantypes:
                raise ValidationError(
                    {
                        'Scan Type': "%(type)s is not a valid Scan Type. Please select a valid Scan Type from %(valid)s" % {
                            "type": scan_type,
                            "valid": valid_scantypes
                        }
                    }
                )
    
    def check_valid_priority(self,row):
        if 'Priority' in row:
            valid_priorities = ['LOW','MEDIUM','HIGH']
            priority = row.get('Priority')
            if priority not in valid_priorities:
                raise ValidationError(
                    {
                        'Priority': "%(priority)s is not a valid Priority. Please select a valid Priority from %(valid)s" % {
                            "priority": priority,
                            "valid": valid_priorities
                        }
                    }
                )
        
    def check_required_fields(self, row):
        if row.get('ID*') in ['', 'NONE', None] or (isinstance(row.get('ID*'), float) and math.isnan(row.get('ID*'))): raise ValidationError({'ID*':"This field is required"})
        required_fields = [
            'Name', 'From Date', 'Upto Date', 'Scheduler','Notify Category', 'Plan Duration', 
            'Gracetime Before', 'Gracetime After','Question Set/Checklist', 'Asset', 'Priority',
            'People', 'Group Name', 'Belongs To']
        integer_fields = ['Plan Duration', 'Gracetime Before', 'Gracetime After']
    
        for field in required_fields:
            if field in row:
                value = row.get(field)
                if field in integer_fields:
                    try:
                        int_value = int(value)
                        if int_value < 0:
                            raise ValidationError({field: f"{field} must be a non-negative integer"})
                    except (ValueError, TypeError):
                        raise ValidationError({field: f"{field} must be a valid integer"})
                elif value in [None, '']:
                    raise ValidationError({field: f"{field} is a required field"})
    
    def validate_row(self, row):
        if 'Name' in row:
            row['Name'] = clean_string(row['Name'])
        if 'Description' in row:
            row['Description'] = clean_string(row['Description'])
        if 'Plan Duration' in row:
            row['Plan Duration'] = int(row['Plan Duration'])
        if 'Gracetime Before' in row:
            row['Gracetime Before'] = int(row['Gracetime Before'])
        if 'Gracetime After' in row:
            row['Gracetime After'] = int(row['Gracetime After'])
        # check valid cron
        if 'Scheduler' in row:
            if not validate_cron(row['Scheduler']):
                raise ValidationError({'Scheduler': "Invalid value or Problematic Cron Expression for scheduler"})
    
    def check_record_exists(self, row):
        if not Job.objects.filter(id = row['ID*']).exists():
            raise ValidationError(f"Record with these values not exist: ID - {row['ID*']}")
    
    def before_save_instance(self, instance, using_transactions, dry_run=False):
        utils.save_common_stuff(self.request, instance, self.is_superuser)

class TourResourceUpdate(resources.ModelResource):
    CLIENT      = fields.Field(attribute='client', column_name='Client',widget=wg.ForeignKeyWidget(om.Bt, 'bucode'), default=utils.get_or_create_none_bv)
    SITE        = fields.Field(attribute='bu', column_name='Site',widget=BVForeignKeyWidgetUpdate(om.Bt, 'bucode'))
    NAME        = fields.Field(attribute='jobname', column_name='Name')
    DESC        = fields.Field(attribute='jobdesc', column_name='Description', default='')
    QSET        = fields.Field(attribute='qset', column_name='Question Set/Checklist', widget=QsetFKWUpdate(QuestionSet, 'qsetname'))
    ASSET       = fields.Field(attribute='asset', column_name='Asset', widget=AssetFKWUpdate(Asset, 'assetcode'))
    PARENT      = fields.Field(attribute='parent', column_name='Belongs To', widget=wg.ForeignKeyWidget(Job, 'jobname'), default=utils.get_or_create_none_job)
    PDURATION   = fields.Field(attribute='planduration', column_name='Plan Duration')
    GRACETIME   = fields.Field(attribute='gracetime', column_name='Gracetime')
    EXPTIME     = fields.Field(attribute='expirytime', column_name='Expiry Time')
    CRON        = fields.Field(attribute='cron', column_name='Scheduler')
    FROMDATE    = fields.Field(attribute='fromdate', column_name='From Date', widget=wg.DateTimeWidget())
    UPTODATE    = fields.Field(attribute='uptodate', column_name='Upto Date', widget=wg.DateTimeWidget())
    SCANTYPE    = fields.Field(attribute='scantype', column_name='Scan Type', default='QR')
    TKTCATEGORY = fields.Field(attribute='ticketcategory', column_name='Notify Category', widget=TktCategoryFKWUpdate(om.TypeAssist, 'tacode'), default=default_ta)
    PRIORITY    = fields.Field(attribute='priority', column_name='Priority', default='LOW')
    PEOPLE      = fields.Field(attribute='people', column_name='People', widget= PeopleFKWUpdate(pm.People, 'peoplecode'))
    PGROUP      = fields.Field(attribute='pgroup', column_name='Group Name', widget=PgroupFKWUpdate(pm.Pgroup, 'groupname'))
    STARTTIME   = fields.Field(attribute='starttime', column_name='Start Time', default=time(0,0,0), widget=wg.TimeWidget())
    ENDTIME     = fields.Field(attribute='endtime', column_name='End Time', default=time(0,0,0), widget=wg.TimeWidget())
    SEQNO       = fields.Field(attribute='seqno', column_name='Seq No', default=-1)
    ID          = fields.Field(attribute='id', column_name='ID*')

    class Meta:
        model = Job
        skip_unchanged = True
        #import_id_fields = ['ID']
        report_skipped = True
        fields = [
            'ID','CLIENT', 'SITE', 'NAME', 'DESC', 'QSET', 'PDURATION', 'GRACETIME', 
            'EXPTIME','CRON', 'FROMDATE', 'UPTODATE', 'SCANTYPE', 'TKTCATEGORY', 'PRIORITY', 
            'PEOPLE', 'PGROUP', 'STARTTIME', 'ENDTIME', 'SEQNO', 'PARENT', 'ASSET'
        ]
    
    def __init__(self, *args, **kwargs):
        super(TourResourceUpdate, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
        
    
    def before_import_row(self, row, row_number, **kwargs):
        self.check_required_fields(row)
        self.validate_row(row)
        self.check_record_exists(row)
        super().before_import_row(row, **kwargs)
        
    def check_required_fields(self, row):
        if row.get('ID*') in ['', 'NONE', None] or (isinstance(row.get('ID*'), float) and math.isnan(row.get('ID*'))): raise ValidationError({'ID*':"This field is required"})
        required_fields = [
            'Name', 'From Date', 'Upto Date', 'Scheduler','Notify Category', 'Plan Duration', 
            'Expiry Time', 'Gracetime', 'Seq No','Question Set/Checklist', 'Asset', 'Priority', 
            'People', 'Group Name', 'Belongs To']
        integer_fields = ['Plan Duration', 'Gracetime', 'Expiry Time', 'Seq No']
    
        for field in required_fields:
            if field in row:
                value = row.get(field)
                if field in integer_fields:
                    try:
                        int_value = int(value)
                        if int_value < 0:
                            raise ValidationError({field: f"{field} must be a non-negative integer"})
                    except (ValueError, TypeError):
                        raise ValidationError({field: f"{field} must be a valid integer"})
                elif value in [None, '']:
                    raise ValidationError({field: f"{field} is a required field"})
    
    def validate_row(self, row):
        if 'Identifier' in  row:
            row['Identifier'] = 'INTERNALTOUR'
        if 'Name' in row:
            row['Name'] = clean_string(row['Name'])
        if 'Description' in row:
            row['Description'] = clean_string(row['Description'])
        if 'Plan Duration' in row:
            row['Plan Duration'] = int(row['Plan Duration'])
        if 'Gracetime' in row:
            row['Gracetime'] = int(row['Gracetime'])
        if 'Expiry Time' in row:
            row['Expiry Time'] = int(row['Expiry Time'])
        if 'Seq No' in row:
            row['Seq No'] = int(row['Seq No'])
        # check valid cron
        if 'Scheduler' in row:
            if not validate_cron(row['Scheduler']):
                raise ValidationError({'Scheduler': "Invalid value or Problematic Cron Expression for scheduler"})
    
    def check_record_exists(self, row):
        if not Job.objects.filter(id = row['ID*']).exists():
            raise ValidationError(f"Record with these values not exist: ID - {row['ID*']}")
    
    def before_save_instance(self, instance, using_transactions, dry_run=False):
        utils.save_common_stuff(self.request, instance, self.is_superuser)