from django.contrib import admin
from django.core.exceptions import ValidationError
from apps.service.validators import clean_code, clean_string, clean_point_field, validate_email
from apps.core import utils
from django.db.models import Q
from import_export import fields, resources, widgets as wg
from apps.work_order_management import models as wom
from apps.onboarding import models as om
import re, math
from apps.core.widgets import EnabledTypeAssistWidget

# Register your models here
def default_ta():
    return utils.get_or_create_none_typeassist()[0]

class VendorTypeFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.filter(
            Q(client__bucode = row['Client*']) |  Q(client_id = 1),
            tatype__tacode = 'VENDOR_TYPE',
        )

class VendorTypeFKWUpdate(wg.ForeignKeyWidget):
   def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.filter(
            Q(client__bucode = row['Client']) |  Q(client_id = 1),
            tatype__tacode = 'VENDOR_TYPE',
        )


class VendorResource(resources.ModelResource):
    Client = fields.Field(
        column_name = 'Client*',
        attribute   = 'client',
        widget      = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default     = utils.get_or_create_none_bv
    )
    BV = fields.Field(
        column_name       = 'Site*',
        attribute         = 'bu',
        widget            = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default           = utils.get_or_create_none_bv
    )
    Type = fields.Field(
        column_name='Type*',
        attribute='type',
        widget=VendorTypeFKW(om.TypeAssist, 'tacode'),
        default=default_ta
    )
    
    SHOWTOALLSITES = fields.Field(attribute='show_to_all_sites', column_name='Applicable to All Sites', default=False)
    ID             = fields.Field(attribute='id')
    CODE           = fields.Field(attribute='code', column_name='Code*')
    NAME           = fields.Field(attribute='name', column_name='Name*')
    ADDRESS        = fields.Field(attribute='address', column_name='Address*')
    ENABLE         = fields.Field(attribute='enable', column_name='Enable', default=True)
    MOB            = fields.Field(attribute='mobno', column_name='Mob No*')
    EMAIL          = fields.Field(attribute='email', column_name='Email*')
    GPS            = fields.Field(attribute='gpslocation', column_name='GPS Location')
    
    class Meta:
        model = wom.Vendor
        skip_unchanged = True
        #import_id_fields = ['ID']
        report_skipped = True
        fields = [
            'CODE', 'NAME', 'GPS', 'Client', 'BV', 'EMAIL',
            'MOB', 'ENABLE', 'ADDRESS', 'SHOWTOALLSITES','ID','Type']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
    def before_import_row(self, row, row_number=None, **kwargs):
        row['Code*'] = clean_string(row.get('Code*'), code=True)
        row['Name*'] = clean_string(row.get('Name*'))
        row['Address*'] = clean_string(row.get('Address*'))
        row['GPS Location'] = clean_point_field(row.get('GPS Location'))
        row['Mob No*'] = str(row['Mob No*'])
        
        #check required fields
        if row.get('Code*') in  ['', None]:raise ValidationError("Code* is required field")
        if row.get('Name*') in  ['', None]:raise ValidationError("Name* is required field")
        if row.get('Type*') in  ['', None]:raise ValidationError("Type* is required field")
        
        # code validation
        regex, value = "^[a-zA-Z0-9\-_]*$", row['Code*']
        if re.search(r'\s|__', value): raise ValidationError("Please enter text without any spaces")
        if  not re.match(regex, value):
            raise ValidationError("Please enter valid text avoid any special characters except [_, -]")
        
        # mob no validation
        # if not utils.verify_mobno(str(row.get('Mob No*', -1))): raise ValidationError("Mob No* is not valid")

        # mob no validation
        if not utils.verify_mobno(str(row.get('Mob No*', -1))):
            raise ValidationError("Mob No* is not valid")
        else: 
            mob_no = str(row['Mob No*'])
            row['Mob No*'] = mob_no if '+' in mob_no else f'+{mob_no}'
        
        # unique record check
        if wom.Vendor.objects.select_related().filter(
            code=row['Code*'],
            client__bucode = row['Client*']).exists():
            raise ValidationError(f"Record with these values already exist {', '.join(row.values())}")
        super().before_import_row(row, row_number, **kwargs)
        
        # validate email
        if not validate_email(row.get('Email*')): raise ValidationError('Email is not valid!')
        
    def before_save_instance(self, instance, using_transactions, dry_run=False):
        utils.save_common_stuff(self.request, instance, self.is_superuser)

class VendorResourceUpdate(resources.ModelResource):
    Client = fields.Field(
        column_name = 'Client',
        attribute = 'client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default = utils.get_or_create_none_bv
    )

    BV = fields.Field(
        column_name = 'Site',
        attribute = 'bu',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default = utils.get_or_create_none_bv
    )

    Type = fields.Field(
        column_name = 'Type',
        attribute = 'type',
        widget = EnabledTypeAssistWidget(om.TypeAssist, 'tacode'),
        default = default_ta
    )
    
    SHOWTOALLSITES = fields.Field(attribute='show_to_all_sites', column_name='Applicable to All Sites', default=False)
    ID             = fields.Field(attribute='id', column_name="ID*")
    CODE           = fields.Field(attribute='code', column_name='Code')
    NAME           = fields.Field(attribute='name', column_name='Name')
    ADDRESS        = fields.Field(attribute='address', column_name='Address')
    ENABLE         = fields.Field(attribute='enable', column_name='Enable', default=True)
    MOB            = fields.Field(attribute='mobno', column_name='Mob No')
    EMAIL          = fields.Field(attribute='email', column_name='Email')
    GPS            = fields.Field(attribute='gpslocation', column_name='GPS Location')
    
    class Meta:
        model = wom.Vendor
        skip_unchanged = True
        #import_id_fields = ['ID']
        report_skipped = True
        fields = [
            'ID','CODE', 'NAME', 'GPS', 'Client', 'BV', 'EMAIL',
            'MOB', 'ENABLE', 'ADDRESS', 'SHOWTOALLSITES','Type']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
    def before_import_row(self, row, row_number=None, **kwargs):
        if 'Code' in row:
            row['Code'] = clean_string(row.get('Code'), code=True)
        if 'Name' in row:
            row['Name'] = clean_string(row.get('Name'))
        if 'Address' in row:
            row['Address'] = clean_string(row.get('Address'))
        if 'GPS Location' in row:
            row['GPS Location'] = clean_point_field(row.get('GPS Location'))
        if 'Mob No' in row:
            row['Mob No'] = str(row['Mob No'])
        
        #check required fields
        if row.get('ID*') in ['', 'NONE', None] or (isinstance(row.get('ID*'), float) and math.isnan(row.get('ID*'))): raise ValidationError({'ID*':"This field is required"})
        
        # code validation
        if 'Code' in row:
            regex, value = "^[a-zA-Z0-9\-_]*$", row['Code']
            if re.search(r'\s|__', value): raise ValidationError("Please enter text without any spaces")
            if not re.match(regex, value):
                raise ValidationError("Please enter valid text avoid any special characters except [_, -]")
        
        # mob no validation
        # if not utils.verify_mobno(str(row.get('Mob No*', -1))): raise ValidationError("Mob No* is not valid")

        # mob no validation
        if 'Mob No' in row:
            if not utils.verify_mobno(str(row.get('Mob No', -1))):
                raise ValidationError("Mob No is not valid")
            else: 
                mob_no = str(row['Mob No'])
                row['Mob No'] = mob_no if '+' in mob_no else f'+{mob_no}'
        
        # check record exists
        if not wom.Vendor.objects.filter(id=row['ID*']).exists():
            raise ValidationError(f"Record with these values not exist: ID - {row['ID*']}")
        super().before_import_row(row, row_number, **kwargs)
        
        # validate email
        if 'Email' in row:
            if not validate_email(row.get('Email')): raise ValidationError('Email is not valid!')
        
    def before_save_instance(self, instance, using_transactions, dry_run=False):
        utils.save_common_stuff(self.request, instance, self.is_superuser)