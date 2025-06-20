from gettext import install
from django.contrib import admin
from import_export import resources, fields
from import_export import widgets as wg
from import_export.admin import ImportExportModelAdmin
import apps.tenants.models as tm
from apps.service.validators import clean_point_field, clean_string
from apps.peoples import models as pm
from .forms import (BtForm, ShiftForm, )
import apps.onboarding.models as om
from apps.core import utils
from django.core.exceptions import ValidationError
import re
from math import isnan
from apps.core.widgets import EnabledTypeAssistWidget
from apps.onboarding.utils import bulk_create_geofence
from apps.activity.models.job_model import Job

class BaseResource(resources.ModelResource):
    CLIENT = fields.Field(
        column_name='Client*',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default='NONE'
    )
    BV = fields.Field(
        column_name='BV*',
        attribute='bu',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default='NONE'
    )
    

    
    def __init__(self, *args, **kwargs):
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
    def before_save_instance(self, instance, using_transactions, dry_run):
        utils.save_common_stuff(self.request, instance, self.is_superuser)
        super().before_save_instance(instance, using_transactions, dry_run)

def default_ta():
    return utils.get_or_create_none_typeassist()[0]


class BaseFieldSet2:
    client = fields.Field(
        column_name='client',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default='NONE'
    )
    bu = fields.Field(
        column_name='bu',
        attribute='bu',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default='NONE'
    )
    tenant = fields.Field(
        column_name='tenant',
        attribute='tenant',
        widget = wg.ForeignKeyWidget(tm.TenantAwareModel, 'tenantname'),
        saves_null_values = True
    )

''''TaResource class provides functionalities for importing and validating data 
related to the om.TypeAssist model in a Django application. It ensures data integrity 
by cleaning, validating, and checking for uniqueness before saving the imported data.'''
class TaResource(resources.ModelResource):
    CLIENT = fields.Field(
        column_name='Client*',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default='NONE'
    )
    
    TYPE = fields.Field(
        column_name       = 'Type*',
        attribute         = 'tatype',
        default           = om.TypeAssist, 
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )
    CODE = fields.Field(attribute='tacode', column_name='Code*')
    NAME = fields.Field(attribute='taname', column_name='Name*')

    class Meta: 
        model = om.TypeAssist
        skip_unchanged = True
        import_id_fields = ('CODE', 'TYPE', 'CLIENT')  # Use tacode as the unique identifier
        exclude = ('id',)
        report_skipped = True
        fields = ('NAME', 'CODE', 'TYPE', 'CLIENT')

        
    def __init__(self, *args, **kwargs):
        super(TaResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
    def before_import_row(self, row, row_number, **kwargs):

        '''cleaning in sence Handles empty string,Removes extra spaces, 
        Converts to uppercase and replaces spaces with underscores (if code is True)'''
        row['Code*'] = clean_string(row.get('Code*', 'NONE'), code=True)
        row['Name*'] = clean_string(row.get('Name*', "NONE"))

        # Validates that required fields (Code*, Type*, and Name*) are not empty.
        if row['Code*'] in ['', None]: raise ValidationError("Code* is required field")
        if row['Type*'] in ['', None]: raise ValidationError("Type* is required field")
        if row['Name*'] in ['', None]: raise ValidationError("Name* is required field")
        
        ''' Validates the format of the Code* field using a regular expression.
         It ensures no spaces and only allows alphanumeric characters, underscores, and hyphens.'''
        regex, value = "^[a-zA-Z0-9\-_]*$", row['Code*']
        if re.search(r'\s|__', value): raise ValidationError("Please enter text without any spaces")
        if  not re.match(regex, value):
            raise ValidationError("Please enter valid text avoid any special characters except [_, -]")

        '''Checks for uniqueness of the record based on a combination of Code*, Type*, 
        and CLIENT* fields. It raises an error if a duplicate record is found.'''
        
        if om.TypeAssist.objects.select_related().filter(
            tacode=row['Code*'], tatype__tacode=row['Type*'],
            client__bucode = row['Client*']).exists():
            raise ValidationError(f"Record with these values already exist {', '.join(row.values())}")
        

        super().before_import_row(row, **kwargs)

    #saving the instance before saving it to the database
    def before_save_instance(self, instance,row, **kwargs):
        """
        Prepares instance before saving — sets cuser, muser, timestamps etc.
        """
        utils.save_common_stuff(self.request, instance, self.is_superuser)
        
    
def clean_nan(value):
    if isinstance(value, float) and isnan(value):
        return None
    if isinstance(value, str) and value.strip().lower() in ['nan', 'none', '']:
        return None
    return value


@admin.register(om.TypeAssist)
class TaAdmin(ImportExportModelAdmin):
    resource_class = TaResource
    list_display = (
        'id', 'tacode', 'tatype', 'mdtz', 'taname',
        'cuser', 'muser', 'cdtz', 'bu', 'client' )

    def get_resource_kwargs(self, request, *args, **kwargs):
        return {'request': request}

    def get_queryset(self, request):
        return om.TypeAssist.objects.select_related(
            'tatype', 'cuser', 'muser', 'bu', 'client', 'tenant').all()

class BtResource(resources.ModelResource):
    BelongsTo = fields.Field(
        column_name='Belongs To*',
        default=utils.get_or_create_none_bv,
        attribute='parent',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'))

    BuType = fields.Field(
        column_name='Site Type',
        default=default_ta,
        attribute='butype',
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'))

    Identifier = fields.Field(
        column_name='Type*',
        attribute='identifier',
        default=default_ta,
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'))
    
    Sitemanager = fields.Field(
        column_name='Site Manager*',
        attribute='siteincharge',
        default=utils.get_or_create_none_people,
        widget = wg.ForeignKeyWidget(pm.People, 'peoplecode'))
    
    Code    = fields.Field(attribute='bucode', column_name='Code*')
    Name    = fields.Field(attribute='buname', column_name='Name*')
    GPS     = fields.Field(attribute='gpslocation', column_name='GPS Location', saves_null_values=True)
    Address = fields.Field(column_name='Address', widget=wg.CharWidget(), saves_null_values=True)
    State   = fields.Field(column_name='State', widget=wg.CharWidget(), saves_null_values=True)
    City    = fields.Field(column_name='City', widget=wg.CharWidget(), saves_null_values=True)
    Country = fields.Field(column_name='Country', widget=wg.CharWidget(), saves_null_values=True)
    SOLID   = fields.Field(attribute='solid', column_name='Sol Id', widget=wg.CharWidget())
    Enable  = fields.Field(attribute='enable', column_name='Enable', default=True)

    class Meta:
        model = om.Bt
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ('Code',)
        fields = (
            'Name', 'Code', 'BuType', 'SOLID', 
            'Enable', 'GPS','Address', 'State',
            'City', 'Country','Identifier', 'BelongsTo','Sitemanager')

    def __init__(self, *args, **kwargs):
        super(BtResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
        
    
    def before_import_row(self, row, **kwargs):
        row['Code*'] = clean_string(row.get('Code*', 'NONE'), code=True)
        row['Name*'] = clean_string(row.get('Name*', "NONE"))
        self._gpslocation = clean_point_field(row['GPS Location'])
        self._solid = clean_nan(row['Sol Id'])
        self._address = clean_nan(row['Address'])
        self._state = clean_nan(row['State'])
        self._city = clean_nan(row['City'])
        self._country = clean_nan(row['Country'])
        self._latlng = clean_nan(row['GPS Location'])
        if row['Control Room']:
            control_room_list = row['Control Room'].strip("[]").replace("'", "").split(", ")
        else:
            control_room_list = []
        from django.db.models import Q
        control_id_list = list(
        pm.People.objects.filter(
                Q(Q(designation__tacode__in=['CR']) | Q(worktype__tacode__in=['CR'])),
                enable=True,
                peoplecode__in=control_room_list
            ).values_list('id', flat=True)
        )
        control_id_list = [str(id) for id in control_id_list]
        self._controlroom = control_id_list
        pdist_val = clean_nan(row['Permissible Distance'])
        if pdist_val not in [None, '']:
            try:
                pdist_val = float(pdist_val)
            except (TypeError, ValueError):
                raise ValidationError("Permissible Distance must be a number")
            if pdist_val < 0:
                raise ValidationError("Permissible Distance is greater than or equal to zero")
        self._permissibledistance = pdist_val
        # check required fields
        if row['Code*'] in ['', None]:
            raise ValidationError("Code* is required field")
        if row['Type*'] in ['', None]:
            raise ValidationError("Type* is required field")
        if row['Name*'] in ['', None]:
            raise ValidationError("Name* is required field")
        if row['Belongs To*'] in ['', None]:
            raise ValidationError("Belongs To* is required field")
        # code validation
        regex, value = "^[a-zA-Z0-9\-_]*$", row['Code*']
        if re.search(r'\s|__', value): raise ValidationError("Please enter text without any spaces")
        if  not re.match(regex, value):
            raise ValidationError("Please enter valid text avoid any special characters except [_, -]")
        
        # unique record check
        if om.Bt.objects.select_related().filter(
            bucode=row['Code*'], parent__bucode=row['Belongs To*'],
            identifier__tacode = row['Type*']).exists():
            raise ValidationError(f"Record with these values already exist {row.values()}")
        
        super().before_import_row(row, **kwargs)


    def before_save_instance(self, instance, row, **kwargs):
        instance.gpslocation = self._gpslocation
        instance.bupreferences['address'] = self._address
        instance.bupreferences['controlroom'] = self._controlroom
        instance.bupreferences['permissibledistance'] = self._permissibledistance
        instance.bupreferences['address2'] = {
            'city':self._city, 'country':self._country,
            'state':self._state, 'formattedAddress':self._address,
            'latlng':self._latlng}
        if self._solid and not (isinstance(self._solid, float) and isnan(self._solid)):
            instance.solid = int(self._solid)
        else:
            instance.solid = None
            
        utils.save_common_stuff(self.request, instance)

    def get_queryset(self):
        return om.Bt.objects.select_related().all()

@admin.register(om.Bt)
class BtAdmin(ImportExportModelAdmin):
    resource_class = BtResource
    fields = ('bucode',  'buname', 'butype', 'parent', 'gpslocation', 'identifier',
              'iswarehouse', 'enable', 'bupreferences')
    exclude = ['bupath']
    list_display = ('bucode', 'id', 'buname', 'butype',
                    'identifier', 'parent', 'butree')
    list_display_links = ('bucode',)
    form = BtForm

    def get_resource_kwargs(self, request, *args, **kwargs):
        return {'request': request}

    def get_queryset(self, request):
        return om.Bt.objects.select_related('butype', 'identifier', 'parent').all()

class ShiftResource(resources.ModelResource):
    Client = fields.Field(
        column_name='Client',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default='NONE'
    )    
    BV = fields.Field(
        column_name='BV',
        attribute='bu',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default='NONE'
    )
    
    Name          = fields.Field(attribute='shiftname', column_name='Shift Name')
    ID            = fields.Field(attribute='id')
    StartTime     = fields.Field(attribute='starttime', column_name='Start Time', widget=wg.TimeWidget())
    EndTime       = fields.Field(attribute='endtime', column_name='End Time', widget=wg.TimeWidget())
    ShiftDuration = fields.Field(attribute='shiftduration', column_name='Shift Duration', widget=wg.TimeWidget())
    IsNightShift  = fields.Field(attribute='nightshiftappicable', column_name="Is Night Shift", widget=wg.BooleanWidget())
    Enable        = fields.Field(attribute='enable', widget=wg.BooleanWidget())
    
    class Meta:
        model = om.Shift
        skip_unchanged = True
        #import_id_fields = ('ID',)
        report_skipped = True
        fields = ('ID', 'Name', 'ShiftDuration', 'StartTime', 'Client',
                  'EndTime', 'IsNightShift', 'Enable', 'BV')

@admin.register(om.Shift)
class ShiftAdmin(ImportExportModelAdmin):
    resource_class = ShiftResource
    form = ShiftForm
    fields = ('bu', 'shiftname', 'shiftduration', 'starttime',
              'endtime', 'nightshiftappicable', 'captchafreq')
    list_display = ('bu', 'shiftname', 'shiftduration',
                    'starttime', 'endtime', 'nightshiftappicable')
    list_display_links = ('shiftname',)




        
class TaResourceUpdate(resources.ModelResource):
    CLIENT = fields.Field(
        column_name = 'Client',
        attribute ='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default = 'NONE'
    )
    
    TYPE = fields.Field(
        column_name = 'Type',
        attribute = 'tatype',
        default = om.TypeAssist, 
        widget = EnabledTypeAssistWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )

    CODE = fields.Field(attribute='tacode', column_name='Code')
    NAME = fields.Field(attribute='taname', column_name='Name')
    ID   = fields.Field(attribute='id', column_name='ID*')

    class Meta: 
        model = om.TypeAssist
        skip_unchanged = True
        #import_id_fields = ['ID']
        report_skipped = True
        fields = ('ID','NAME', 'CODE', 'TYPE', 'CLIENT')

    def __init__(self, *args, **kwargs):
        super(TaResourceUpdate, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
    def before_import_row(self, row, row_number, **kwargs):
        '''cleaning in sence Handles empty string,Removes extra spaces, 
        Converts to uppercase and replaces spaces with underscores (if code is True)'''
        if 'Code' in row:
            row['Code'] = clean_string(row.get('Code'), code=True)
        if 'Name' in row:
            row['Name'] = clean_string(row.get('Name'))

        # Validates that required fields (Code*, Type*, and Name*) are not empty.
        if 'Code' in row:
            if row['Code'] in ['', None]: raise ValidationError("Code is required field")
        if 'Type' in row:
            if row['Type'] in ['', None]: raise ValidationError("Type is required field")
        if 'Name' in row:
            if row['Name'] in ['', None]: raise ValidationError("Name is required field")
        if row.get('ID*') in ['', 'NONE', None] or (isinstance(row.get('ID*'), float) and isnan(row.get('ID*'))): raise ValidationError({'ID*':"This field is required"})
        
        ''' Validates the format of the Code* field using a regular expression.
         It ensures no spaces and only allows alphanumeric characters, underscores, and hyphens.'''
        if 'Code' in row:
            regex, value = "^[a-zA-Z0-9\-_]*$", row['Code']
            if re.search(r'\s|__', value): raise ValidationError("Please enter text without any spaces")
            if not re.match(regex, value):
                raise ValidationError("Please enter valid text avoid any special characters except [_, -]")

        '''check record exists '''
        if not om.TypeAssist.objects.filter(id=row['ID*']).exists():    
            raise ValidationError(f"Record with these values not exist: ID - {row['ID*']}")

        super().before_import_row(row, **kwargs)

    #saving the instance before saving it to the database
    def before_save_instance(self, instance, using_transactions, dry_run=False):
        '''inserts data into the instance object before saving it to 
        the database of cuser, muser, cdtz, and mdtz fields.'''
        utils.save_common_stuff(self.request, instance, self.is_superuser)

class BtResourceUpdate(resources.ModelResource):
    BelongsTo = fields.Field(
        column_name = 'Belongs To',
        default = utils.get_or_create_none_bv,
        attribute = 'parent',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'))

    BuType = fields.Field(
        column_name = 'Site Type',
        default = default_ta,
        attribute = 'butype',
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'))

    Identifier = fields.Field(
        column_name = 'Type',
        attribute = 'identifier',
        default = default_ta,
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'))
    
    Sitemanager = fields.Field(
        column_name = 'Site Manager',
        attribute = 'siteincharge',
        default = utils.get_or_create_none_people,
        widget = wg.ForeignKeyWidget(pm.People, 'peoplecode'))
    
    ID      = fields.Field(attribute='id', column_name="ID*")
    Code    = fields.Field(attribute='bucode', column_name='Code')
    Name    = fields.Field(attribute='buname', column_name='Name')
    GPS     = fields.Field(attribute='gpslocation', column_name='GPS Location', saves_null_values=True)
    Address = fields.Field(column_name='Address', attribute = 'bupreferences.address', widget=wg.CharWidget(), saves_null_values=True)
    State   = fields.Field(column_name='State', attribute = 'bupreferences.address2.state', widget=wg.CharWidget(), saves_null_values=True)
    City    = fields.Field(column_name='City', attribute = 'bupreferences.address2.city', widget=wg.CharWidget(), saves_null_values=True)
    Country = fields.Field(column_name='Country', attribute = 'bupreferences.address2.country', widget=wg.CharWidget(), saves_null_values=True)
    SOLID   = fields.Field(attribute='solid', column_name='Sol Id', widget=wg.CharWidget())
    Enable  = fields.Field(attribute='enable', column_name='Enable', widget=wg.BooleanWidget(), default=True)

    class Meta:
        model = om.Bt
        skip_unchanged = True
        #import_id_fields = ['ID']
        report_skipped = True
        fields = (
            'ID', 'Name', 'Code', 'BuType', 'SOLID', 'Enable', 'GPS', 'Address', 
            'State', 'City', 'Country', 'Identifier', 'BelongsTo','Sitemanager')

    def __init__(self, *args, **kwargs):
        super(BtResourceUpdate, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
        
    def before_import_row(self, row, **kwargs):
        if 'Code' in row:
            row['Code'] = clean_string(row.get('Code'), code=True)
        if 'Name' in row:
            row['Name'] = clean_string(row.get('Name'))
        if 'GPS Location' in row:
            self._gpslocation = clean_point_field(row['GPS Location'])
        if 'Sol Id' in row:
            self._solid = row['Sol Id']
        required_fields = ['Address', 'State', 'City', 'Country', 'GPS Location']
        present_fields = [field for field in required_fields if field in row]
        if len(present_fields) == len(required_fields):
            self._address = row['Address']
            self._state = row['State']
            self._city = row['City']
            self._country = row['Country']
            self._latlng = row['GPS Location']
        elif len(present_fields) > 0:
            raise ValidationError("To create a complete address, you need to provide the Address, State, City, Country, and GPS Location.")
        
        # check required fields
        if row.get('ID*') in ['', 'NONE', None] or (isinstance(row.get('ID*'), float) and isnan(row.get('ID*'))): raise ValidationError({'ID*':"This field is required"})
        if 'Code' in row:
            if row['Code'] in ['', None]: raise ValidationError("Code is required field")
        if 'Type' in row:
            if row['Type'] in ['', None]: raise ValidationError("Type is required field")
        if 'Name' in row:
            if row['Name'] in ['', None]: raise ValidationError("Name is required field")
        if 'Belongs To' in row:
            if row['Belongs To'] in ['', None]: raise ValidationError("Belongs To is required field")
        
        # code validation
        if 'Code' in row:
            regex, value = "^[a-zA-Z0-9\-_]*$", row['Code']
            if re.search(r'\s|__', value): raise ValidationError("Please enter text without any spaces")
            if  not re.match(regex, value):
                raise ValidationError("Please enter valid text avoid any special characters except [_, -]")
        
        # check record exists
        if not om.Bt.objects.filter(id=row['ID*']).exists():
            raise ValidationError(f"Record with these values not exist: ID - {row['ID*']}")
        
        super().before_import_row(row, **kwargs)

    def before_save_instance(self, instance, using_transactions, dry_run):
        if hasattr(self, '_gpslocation') and self._gpslocation is not None:
            instance.gpslocation = self._gpslocation
        if hasattr(self, '_address') and self._gpslocation is not None:
            instance.bupreferences['address'] = self._address
        instance.bupreferences['address2'] = {
            'city': self._city if hasattr(self, '_city') and self._city is not None else None,
            'country': self._country if hasattr(self, '_country') and self._country is not None else None,
            'state': self._state if hasattr(self, '_state') and self._state is not None else None,
            'formattedAddress': self._address if hasattr(self, '_address') and self._address is not None else None,
            'latlng': self._latlng if hasattr(self, '_latlng') and self._latlng is not None else None,
            }
        if self._solid and not (isinstance(self._solid, float) and isnan(self._solid)):
            instance.solid = int(self._solid)
        else:
            instance.solid = None
            
        utils.save_common_stuff(self.request, instance)

class GeofenceResource(resources.ModelResource):
    Client = fields.Field(
        column_name="Client*",
        attribute="client",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        default=utils.get_or_create_none_bv,
    )
    BV = fields.Field(
        column_name="Site*",
        attribute="bu",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        saves_null_values=True,
        default=utils.get_or_create_none_bv,
    )
    AlertToPeople = fields.Field(
        column_name='Alert to People*',
        attribute='alerttopeople',
        widget = wg.ForeignKeyWidget(pm.People, 'peoplecode')
    )
    AlertToGroup = fields.Field( 
        column_name='Alert to Group*',
        attribute='alerttogroup',
        widget = wg.ForeignKeyWidget(pm.Pgroup, 'groupname')
    )

    ID                = fields.Field(attribute='id', column_name="ID")
    Code              = fields.Field(attribute='gfcode', column_name='Code*')
    Name              = fields.Field(attribute='gfname', column_name='Name*')
    AlertText         = fields.Field(attribute='alerttext', column_name='Alert Text*')
    Enable            = fields.Field(attribute='enable', column_name='Enable', default=True)

    class Meta:
        model = om.GeofenceMaster
        skip_unchanged = True
        #import_id_fields = ['ID']
        report_skipped = True
        fields = ('Name', 'Code', 'AlertToPeople', 'AlertToGroup', 'Enable', 'AlertText', 'Site', 'BV', 'Client', 'ID')

    def __init__(self, *args, **kwargs):
        super(GeofenceResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
        
    
    def before_import_row(self, row, **kwargs):
        if row['Code*'] in ['', None]: raise ValidationError("Code* is required field")
        if row['Name*'] in ['', None]: raise ValidationError("Name* is required field")
        if row['Site*'] in ['', None]: raise ValidationError("Site* is required field")
        if row['Client*'] in ['', None]: raise ValidationError("Client* is required field")
        if row['Alert to People*'] in ['', None]: raise ValidationError("Alert to People* is required field")
        if row['Alert to Group*'] in ['', None]: raise ValidationError("Alert to Group* is required field")
        if row['Alert Text*'] in ['', None]: raise ValidationError("Alert Text* is required field")
        
        if row['Alert to People*'] == "NONE" and row['Alert to Group*'] == "NONE":
            raise ValidationError("Either 'Alert to People*' or 'Alert to Group*' must be provided (cannot both be NONE)")
        if row['Alert to People*'] != "NONE" and row['Alert to Group*'] != "NONE":
            raise ValidationError("Only one of 'Alert to People*' or 'Alert to Group*' should be provided")

        row['Code*'] = clean_string(row.get('Code*', 'NONE'), code=True)
        row['Name*'] = clean_string(row.get('Name*', "NONE"))
        self._alerttopeople = row['Alert to People*']
        self._alerttogroup = row['Alert to Group*']
        self._enable = row['Enable']
        self._alerttext = row['Alert Text*']
        self._client = row['Client*']
        self._site = row['Site*']

        # code validation
        regex, value = "^[a-zA-Z0-9\-_]*$", row['Code*']
        if re.search(r'\s|__', value): raise ValidationError("Please enter text without any spaces")
        if  not re.match(regex, value):
            raise ValidationError("Please enter valid text avoid any special characters except [_, -]")
        
        get_geofence = om.Bt.objects.filter(bucode = row['Site*']).values('gpslocation')
        
        get_final_geofence = bulk_create_geofence(get_geofence[0]['gpslocation'], row['Radius*'])
        
        self._geofence = get_final_geofence
        if om.GeofenceMaster.objects.select_related().filter(
            gfcode=row['Code*'], client__bucode=row['Client*']).exists():
            raise ValidationError(f"Record with these values already exist {row.values()}")
        
        super().before_import_row(row, **kwargs)

    def before_save_instance(self, instance, using_transactions, dry_run):
        if hasattr(self, '_geofence'):
            instance.geofence = self._geofence
        utils.save_common_stuff(self.request, instance)

class GeofencePeopleResource(resources.ModelResource):
    ID = fields.Field(attribute='id', column_name="ID")
    Client = fields.Field(
        column_name="Client*",
        attribute="client",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        default=utils.get_or_create_none_bv,
    )
    BV = fields.Field(
        column_name="Site*",
        attribute="bu",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        saves_null_values=True,
        default=utils.get_or_create_none_bv,
    )
    Code = fields.Field(column_name="Code*", attribute="geofence",
            widget=wg.ForeignKeyWidget(om.GeofenceMaster, "gfcode"))
    PeopleCode = fields.Field(
        column_name="People Code*",
        attribute="peoplecode",
        widget=wg.ForeignKeyWidget(pm.People, "peoplecode"),
    )
    ValidFrom = fields.Field(column_name="Valid From*", attribute="fromdate")
    ValidTo = fields.Field(column_name="Valid To*", attribute="uptodate")
    StartTime = fields.Field(column_name="Start Time*", attribute="starttime")
    EndTime = fields.Field(column_name="End Time*", attribute="endtime")

    class Meta:
        model = Job
        skip_unchanged = True
        #import_id_fields = ["ID"]
        report_skipped = True
        fields = ("Code", "PeopleCode", "ValidFrom", "ValidTo", "StartTime", "EndTime", "Site", "Client", "ID","BV",)

    def __init__(self, *args, **kwargs):
        super(GeofencePeopleResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)

    def before_import_row(self, row, **kwargs):
        from datetime import datetime, time
        from django.core.exceptions import ValidationError
        import re

        # Mandatory fields validation
        if row['Site*'] in ['', None]: raise ValidationError("Site* is required field")
        if row['Client*'] in ['', None]: raise ValidationError("Client* is required field")
        if row["Code*"] in ["", None]: raise ValidationError("Code* is required")
        if row["People Code*"] in ["", None]: raise ValidationError("People Code* is required")
        if row["Valid From*"] in ["", None]: raise ValidationError("Valid From* is required")
        if row["Valid To*"] in ["", None]: raise ValidationError("Valid To* is required")
        if row["Start Time*"] in ["", None]: raise ValidationError("Start Time* is required")
        if row["End Time*"] in ["", None]: raise ValidationError("End Time* is required")

        # Validate date fields (convert them to YYYY-MM-DD format if needed)
        try:
            row["Valid From*"] = datetime.strptime(row["Valid From*"], "%d-%m-%Y").strftime("%Y-%m-%d")
        except ValueError:
            raise ValidationError("Invalid format for 'Valid From*', expected DD-MM-YYYY")

        try:
            row["Valid To*"] = datetime.strptime(row["Valid To*"], "%d-%m-%Y").strftime("%Y-%m-%d")
        except ValueError:
            raise ValidationError("Invalid format for 'Valid To*', expected DD-MM-YYYY")

        # Time format validation
        start_time = row["Start Time*"]
        end_time = row["End Time*"]

        if isinstance(start_time, time):
            start_time = start_time.strftime("%H:%M:%S")
        if isinstance(end_time, time):
            end_time = end_time.strftime("%H:%M:%S")

        # Time format validation
        if not re.match(r"^\d{2}:\d{2}:\d{2}$", start_time):
            raise ValidationError("Invalid Start Time format, must be HH:MM:SS")
        if not re.match(r"^\d{2}:\d{2}:\d{2}$", end_time):
            raise ValidationError("Invalid End Time format, must be HH:MM:SS")

        # Code format validation
        regex, value = "^[a-zA-Z0-9\-_]*$", row['Code*']
        if re.search(r'\s|__', value): 
            raise ValidationError("Please enter text without any spaces")
        if not re.match(regex, value):
            raise ValidationError("Please enter valid text avoiding special characters except [_, -]")

        # Validate People and prevent duplicates
        get_people = pm.People.objects.filter(peoplecode=row["People Code*"], client__bucode=row['Client*']).values('id','peoplecode','peoplename')
        if not get_people:
            raise ValidationError("Invalid People Code* for the given Client*")
        
        get_geofence_name = om.GeofenceMaster.objects.filter(gfcode=row["Code*"], client__bucode=row['Client*']).values('gfname')
        if not get_people:
            raise ValidationError("Invalid Code* for the given Client*")

        self._people = get_people[0]['id']
        self._peoplename = get_people[0]['peoplename']
        self._peoplecode = get_people[0]['peoplecode']
        self._geofencecode = row['Code*']
        self._geofencename =  get_geofence_name[0]['gfname']

        if Job.objects.select_related('geofence','client','people').filter(
            geofence__gfcode=row['Code*'], 
            client__bucode=row['Client*'],
            identifier='GEOFENCE',
            people__id=self._people,
            enable=True
        ).exists():
            raise ValidationError(f"Record with these values already exists: {row.values()}")

        super().before_import_row(row, **kwargs)

    def before_save_instance(self, instance, using_transactions, dry_run):
        instance.planduration = 0
        instance.gracetime = 0
        instance.expirytime = 0
        instance.seqno = -1
        instance.people_id = self._people
        instance.identifier = 'GEOFENCE'
        instance.jobname = self._geofencecode + "-" + self._peoplename + " ("+ self._peoplecode +")"
        instance.jobdesc = self._geofencecode + "-" + self._geofencename + "-" + self._peoplename + " ("+ self._peoplecode +")"
        utils.save_common_stuff(self.request, instance)

class ShiftResource(resources.ModelResource):
    Client = fields.Field(
        column_name="Client*",
        attribute="client",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        default=utils.get_or_create_none_bv,
    )
    BV = fields.Field(
        column_name="Site*",
        attribute="bu",
        widget=wg.ForeignKeyWidget(om.Bt, "bucode"),
        saves_null_values=True,
        default=utils.get_or_create_none_bv,
    )
    
    ID                = fields.Field(attribute='id', column_name="ID")
    Name              = fields.Field(attribute='shiftname', column_name='Name*')
    StartTime         = fields.Field(attribute='starttime', column_name='Start Time*')
    EndTime           = fields.Field(attribute='endtime', column_name='End Time*')
    PeopleCount       = fields.Field(attribute='peoplecount', column_name='People Count*')
    Enable            = fields.Field(attribute='enable', column_name='Enable*', default=True)
    NightShift        = fields.Field(attribute='nightshiftappicable', column_name='Night Shift*', default=False)
    ShiftData         = fields.Field(attribute="shift_data", column_name="Shift Data*", widget=wg.JSONWidget(), default=dict)

    class Meta:
        model = om.Shift
        skip_unchanged = True
        #import_id_fields = ['ID']
        report_skipped = True
        fields = ('Name', 'StartTime', 'EndTime', 'PeopleCount', 'Enable', 'NightShift', 'ShiftData','Site', 'BV','Client','ID')

    def __init__(self, *args, **kwargs):
        super(ShiftResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)

    def convert_ist_to_utc(self, time_input):
        import pytz
        from datetime import datetime
        ist = pytz.timezone('Asia/Kolkata')
        if isinstance(time_input, str):
            time_obj = datetime.strptime(time_input, '%H:%M:%S').time()
        else:
            time_obj = time_input
        today = datetime.now(ist).date()
        dt = datetime.combine(today, time_obj)
        ist_dt = ist.localize(dt)
        utc_dt = ist_dt.astimezone(pytz.UTC)
        return utc_dt.time()

    def calculate_duration(self, start_time, end_time):
        from datetime import datetime, timedelta
        today = datetime.now().date()
        start_dt = datetime.combine(today, start_time)
        end_dt = datetime.combine(today, end_time)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        duration = (end_dt - start_dt).total_seconds() / 60
        return int(duration)
        
    def before_import_row(self, row, **kwargs):
        if row['Name*'] in ['', None]: raise ValidationError("Name* is required field")
        if row['Start Time*'] in ['', None]: raise ValidationError("Start Time* is required field")
        if row['End Time*'] in ['', None]: raise ValidationError("End Time* is required field")
        if row['People Count*'] in ['', None]: raise ValidationError("People Count* is required field")
        if row['Enable*'] in ['', None]: raise ValidationError("Enable* is required field")
        if row['Night Shift*'] in ['', None]: raise ValidationError("Night Shift* is required field")
        if row['Type*'] in ['', None]: raise ValidationError("Type* is required field")
        if row['Id*'] in ['', None]: raise ValidationError("Id* is required field")
        if row['Count*'] in ['', None]: raise ValidationError("Count* is required field")
        if row['Overtime*'] in ['', None]: raise ValidationError("Overtime* is required field")
        if row['Gracetime*'] in ['', None]: raise ValidationError("Gracetime* is required field")
        
        row['Name*'] = clean_string(row.get('Name*', "NONE"))
        self._shiftname = row['Name*']
        self._starttime = self.convert_ist_to_utc(row['Start Time*'])
        self._endtime = self.convert_ist_to_utc(row['End Time*'])
        self._peoplecount = int(row['People Count*'])
        self._enable = row['Enable*']
        self._nightshiftappicable = row['Night Shift*']
        self._client = row['Client*']
        self._site = row['Site*']
        
        shift_data_dict = {}

        # Parse fields into lists
        types = [item.strip() for item in row['Type*'].split(",")]
        ids = [item.strip() for item in row['Id*'].split(",")]
        counts = [item.strip() for item in row['Count*'].split(",")]
        overtimes = [item.strip() for item in row['Overtime*'].split(",")]
        gracetimes = [item.strip() for item in row['Gracetime*'].split(",")]

        # Combine the data into the desired structure
        for type_data, id_data, count, overtime, gracetime in zip(types, ids, counts, overtimes, gracetimes):
            shift_data_dict[type_data] = {
                "id": int(id_data),
                "count": count,
                "overtime": overtime,
                "gracetime": gracetime
            }

        if self._peoplecount < 1:
            raise ValidationError("People Count* must be greater than or equal to 1")

        # Validate the shift data dictionary
        shift_data = shift_data_dict  # No need to use self._shift_data if the data is already available as a dictionary

        # Validate gracetime
        for type_key, details in shift_data.items():
            gracetime = details.get("gracetime", "0")
            if gracetime == "" or not gracetime.isdigit() or not (0 < int(gracetime) <= 60):
                raise ValidationError(
                    f"Gracetime for type {type_key} in Shift Data* must be a number greater than 0 and less than or equal to 60"
                )

        # Validate counts and calculate total count
        total_count = 0
        for type_key, details in shift_data.items():
            count = int(details.get("count", 0))
            if count < 1:
                raise ValidationError(f"Count for type {type_key} must be greater than or equal to 1")
            total_count += count

        # Ensure total count does not exceed people count
        if total_count > self._peoplecount:
            raise ValidationError(
                f"Total count in Shift Data* ({total_count}) exceeds the People Count* ({self._peoplecount})"
            )

        # Check for existing records
        if om.Shift.objects.filter(shiftname=row['Name*'], client__bucode=row['Client*']).exists():
            raise ValidationError(f"Record with these values already exists: {row.values()}")

        self._shift_data = shift_data_dict
        super().before_import_row(row, **kwargs)

    # Handle instance before saving
    def before_save_instance(self, instance, using_transactions, dry_run):
        instance.starttime = self._starttime
        instance.endtime = self._endtime
        instance.shiftduration = self.calculate_duration(self._starttime, self._endtime)
        instance.shift_data = self._shift_data
        utils.save_common_stuff(self.request, instance)
