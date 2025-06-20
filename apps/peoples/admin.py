from datetime import date,datetime
import apps.core.utils as utils
from apps.onboarding import models as om
from apps.peoples import models as pm
from import_export import widgets as wg
from apps.core.widgets import(BVForeignKeyWidget, TypeAssistDepartmentFKW, TypeAssistDesignationFKW, 
                              TypeAssistEmployeeTypeFKW, TypeAssistWorkTypeFKW, TypeAssistDepartmentFKWUpdate,
                              TypeAssistDesignationFKWUpdate, TypeAssistEmployeeTypeFKWUpdate, TypeAssistWorkTypeFKWUpdate, 
                              EnabledTypeAssistWidget)
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from django.db.models import Q
from .models import People,  Pgroup, Pgbelonging, Capability
from django.core.exceptions import ValidationError
from apps.service.validators import clean_string, clean_point_field, clean_array_string
from django.contrib import admin
import re, math


def save_people_passwd(user):
    paswd = f'{user.loginid}' if not user.password else user.password
    user.set_password(paswd)
 

def clean_value(value):
    if isinstance(value, str) and value.strip().upper() == "NONE":
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value

def default_ta():
    return utils.get_or_create_none_typeassist()[0]

# Register your models here
class PeopleResource(resources.ModelResource):
    Client = fields.Field(
        column_name='Client*',  
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default=utils.get_or_create_none_bv
    )
    BV = fields.Field(
        column_name='Site*',
        attribute='bu',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default=utils.get_or_create_none_bv
    )
    
    Department = fields.Field(
        column_name='Department',
        attribute='department',
        widget = TypeAssistDepartmentFKW(om.TypeAssist, 'tacode'),
        default=default_ta
    )
    Designation = fields.Field(
        column_name='Designation',
        attribute='designation',
        widget = TypeAssistDesignationFKW(om.TypeAssist, 'tacode'),
        default=default_ta
    )
    PeopleType = fields.Field(
        column_name='Employee Type*',
        attribute='peopletype',
        widget = TypeAssistEmployeeTypeFKW(om.TypeAssist, 'tacode'),
        default=default_ta
    )
    WorkType = fields.Field(
        column_name='Work Type',
        attribute='worktype',
        widget = TypeAssistWorkTypeFKW(om.TypeAssist, 'tacode'),
        default=default_ta
    )
    Reportto = fields.Field(
        column_name='Report To',
        attribute='reportto',
        widget = wg.ForeignKeyWidget(pm.People, 'peoplename'),
        default=utils.get_or_create_none_people
    )
    DateOfBirth = fields.Field(
        column_name='Date of Birth*',
        attribute='dateofbirth',
        widget = wg.DateWidget()
    )
    
    DateOfJoin = fields.Field(
        column_name='Date of Join*',
        attribute='dateofjoin',
        widget = wg.DateWidget()
    )
    
    date_of_release = fields.Field(
        column_name='Date of Release',
        attribute='dateofreport',
        widget = wg.DateWidget()
    )
    

    Code               = fields.Field(attribute='peoplecode', column_name='Code*')
    userfor            = fields.Field(column_name='User For*', default='Mobile')
    deviceid           = fields.Field(attribute='deviceid', column_name='Device Id', default=-1)
    Name               = fields.Field(attribute='peoplename', column_name='Name*')
    LoginId            = fields.Field(attribute='loginid', column_name='Login ID*')
    Password           = fields.Field(attribute='password', column_name='Password*')
    MobNo              = fields.Field(attribute='mobno', column_name='Mob No*')
    Email              = fields.Field(attribute='email', column_name='Email*')
    Gender             = fields.Field(attribute='gender', column_name='Gender*')
    Enable             = fields.Field(widget=wg.BooleanWidget(), attribute='enable', default=True)
    isemergencycontact = fields.Field(widget=wg.BooleanWidget(), default=False, column_name='Emergency Contact')
    alertmails         = fields.Field(default=False,  column_name='Alert Emails')
    mobilecaps         = fields.Field(default='NONE', column_name='Mobile Capability')
    reportcaps         = fields.Field(default='NONE', column_name='Report Capability')
    webcaps            = fields.Field(default='NONE', column_name='Web Capability')
    currentaddr        = fields.Field(default='NONE', column_name='Current Address')
    permanentaddr      = fields.Field(default='NONE', column_name='Permanent Address')
    portletcaps        = fields.Field(default='NONE', column_name='Portlet Capability')
    blacklist          = fields.Field(widget=wg.BooleanWidget(), default=False, column_name='Blacklist')

    class Meta:
        model = pm.People
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ['Code']
        fields = [
            'Code', 'Name', 'LoginId', 'Designation', 'Department', 'MobNo', 'Email', 'deviceid',
            'Site', 'DateOfJoin', 'date_of_release', 'DateOfBirth', 'Gender', 'PeopleType','WorkType', 'Enable',
            'Client', 'isemergencycontact', 'alertmails', 'mobilecaps', 'reportcaps', 'webcaps',
            'portletcaps', 'blacklist', 'currentaddr', 'permanentaddr', 'Reportto', 'Password', 'userfor','BV']

    def __init__(self, *args, **kwargs):
        super(PeopleResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
        
    def before_import_row(self, row, **kwargs):
        for key in row:
            row[key] = clean_value(row[key])
        for field in ['Date of Birth*', 'Date of Join*']:
            value = row.get(field)
            if isinstance(value, (datetime, date)):
                row[field] = value.strftime('%Y-%m-%d')
            elif isinstance(value, str):
                pass
            else:
                row[field] = ""

        self.validations(row)
        self.validations(row)
        self._mobilecaps         = clean_array_string(row['Mobile Capability']) if row.get('Mobile Capability') else []
        self._reportcaps         = clean_array_string(row["Report Capability"]) if row.get('Report Capability') else []
        self._webcaps            = clean_array_string(row["Web Capability"]) if row.get('Web Capability') else []
        self._portletcaps        = clean_array_string(row["Portlet Capability"]) if row.get('Portlet Capability') else []
        self._alertmails         = row.get('Alert Emails') or False
        self._blacklist          = row.get('Blacklist') or False
        self._currentaddr        = row.get('Current Address', "")
        self._permanentaddr      = row.get('Permanent Address', "")
        self._isemergencycontact = row.get('Emergency Contact') or False
        self._userfor            = (row.get('User For*').capitalize() if row.get('User For*') else 'Mobile')
        row['Mob No*'] = str(row['Mob No*'])

    def before_save_instance(self, instance, row, **kwargs):
        instance.email        = instance.email.lower()
        instance.people_extras['mobilecapability']   = self._mobilecaps
        instance.people_extras['reportcapability']   = self._reportcaps
        instance.people_extras['webcapability']      = self._webcaps
        instance.people_extras['portletcapability']  = self._portletcaps
        instance.people_extras['blacklist']          = self._blacklist
        instance.people_extras['isemergencycontact'] = self._isemergencycontact
        instance.people_extras['alertmails']         = self._alertmails
        instance.people_extras['currentaddress']     = clean_string(self._currentaddr)
        instance.people_extras['permanentaddress']   = clean_string(self._permanentaddr)
        instance.people_extras['userfor']          = self._userfor
        utils.save_common_stuff(self.request, instance)
        save_people_passwd(instance)
    
    def validations(self, row):
        row['Code*'] = clean_string(row.get('Code*', 'NONE'), code=True)
        row['Name*'] = clean_string(row.get('Name*', "NONE"))
        # check required fields
        if row['Code*'] in ['', None]: raise ValidationError("Code* is required field")
        # if row['Employee Type*'] in ['', None]: raise ValidationError("Employee Type* is required field")
        if row['Name*'] in ['', None]: raise ValidationError("Name* is required field")
        if row['User For*'] in ['', None]: raise ValidationError("User For* is required field")
        utils.validate_date_format(row.get('Date of Join*'), 'Date of Join*')
        utils.validate_date_format(row.get('Date of Birth*'), 'Date of Birth*')
        
        if value := row.get('Name*'):
            regex = "^[a-zA-Z0-9\-_@#.\(\|\)&\s]*$"
            if not re.match(regex, value):
                raise ValidationError("Only these special characters [-, _, @, #, ., &] are allowed in name field")
        
        # mob no validation
        if not utils.verify_mobno(str(row.get('Mob No*', -1))):
            raise ValidationError("Mob No* is not valid")
        else: 
            mob_no = str(row['Mob No*'])
            row['Mob No*'] = mob_no if '+' in mob_no else f'+{mob_no}'
        
        # unique record check
        if People.objects.select_related().filter(
            loginid=row['Login ID*'], peoplecode=row['Code*'],
            bu__bucode = row['Site*']).exists():
            raise ValidationError(f"Record with the se values already exist {row.values()}")
        

@admin.register(People)
class PeopleAdmin(ImportExportModelAdmin):
    resource_class = PeopleResource

    list_display = ['id', 'peoplecode', 'peoplename', 'loginid',  'mobno', 'email', 'password',
                    'gender', 'peopletype', 'isadmin', 'client', 'cuser', 'muser', 'cdtz', 'mdtz']

    list_display_links = ['peoplecode', 'peoplename']
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('loginid', 'password1', 'password2'),
        }),
    )
    fieldsets = (
        ('Create/Update People', {'fields':['peoplecode', 'peoplename', 'loginid',  'mobno', 'email',
              'bu', 'dateofjoin', 'dateofbirth', 'gender',  'enable', 'tenant',
              'isadmin', 'client']}),
        ('Add/Remove Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
        })
    )

    def get_resource_kwargs(self, request, *args, **kwargs):
        return {'request': request}

    def get_queryset(self, request):
        return pm.People.objects.select_related().all()



class GroupResource(resources.ModelResource):
    Client = fields.Field(
        column_name='Client*',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default='NONE'
    )
    BV = fields.Field(
        column_name='Site*',
        attribute='bu',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default='NONE'
    )
    Identifier = fields.Field(
        attribute='identifier',
        column_name='Type*',
        widget=wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
    )
    ID = fields.Field(attribute='id', column_name='ID')
    Enable = fields.Field(attribute='enable', column_name='Enable', widget=wg.BooleanWidget(), default=True)
    Name = fields.Field(attribute='groupname', column_name='Group Name*')
    
    class Meta:
        model = pm.Pgroup
        skip_unchanged = True
        import_id_fields = ['ID']
        report_skipped = True,
        fields = ['ID', 'Client', 'BV','Identifier', 'Enable', 'Name']
    
    def __init__(self, *args, **kwargs):
        super(GroupResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
    def before_import_row(self, row, row_number, **kwargs):
        row['Name*'] = clean_string(row.get('Name*', "NONE"))
        # check required fields
        if row.get('Name*') in ['', None]: raise ValidationError(
            {'Name*': "This field is required"})
        if row.get('Type*') in ['', None]: raise ValidationError(
            {'Type*':'This field is required'}
        )
        
        if row['Type*'] not in ['PEOPLEGROUP', 'SITEGROUP']:
            raise ValidationError({
                'Type*':"The value must be from ['PEOPLEGROUP', 'SITEGROUP']"
            })

        # unique record check
        if Pgroup.objects.select_related().filter(
            groupname=row['Name*'], identifier__tacode=row['Type*'],
            client__bucode = row['Client*'], bu__bucode=row['Site*']).exists():
            raise ValidationError(f"Record with these values already exist {row.values()}")
        super().before_import_row(row, **kwargs)

    def before_save_instance(self, instance, using_transactions, dry_run=False):
        utils.save_common_stuff(self.request, instance, self.is_superuser)



@admin.register(Pgroup)
class GroupAdmin(ImportExportModelAdmin):
    resource_class = GroupResource
    fields = ['groupname', 'enable',
              'identifier', 'client', 'bu']
    list_display = ['id', 'groupname',
                    'enable', 'identifier', 'client', 'bu']
    list_display_links = ['groupname', 'enable', 'identifier']


class PgroupFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.select_related().filter(
            Q(client__bucode__exact=row["Client*"]),
        )
class PeopleFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.select_related().filter(
            Q(client__bucode__exact=row["Client*"]),
        )
class SiteFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.select_related().filter(
            Q(client__bucode__exact=row["Client*"]),
        )

class GroupBelongingResource(resources.ModelResource):
    CLIENT = fields.Field(
        column_name='Client*',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default=utils.get_or_create_none_bv
    )
    BV = fields.Field(
        column_name='Site*',
        attribute='bu',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default=utils.get_or_create_none_bv
    )
    GROUP = fields.Field(
        column_name='Group Name*',
        attribute='pgroup',
        widget = PgroupFKW(pm.Pgroup, 'groupname'),
        default=utils.get_or_create_none_pgroup
    )
    PEOPLE = fields.Field(
        column_name='Of People',
        attribute='people',
        widget=PeopleFKW(pm.People, 'peoplecode'),
        default=utils.get_or_create_none_people
    )
    SITE = fields.Field(
        column_name='Of Site',
        widget= BVForeignKeyWidget(om.Bt, 'bucode'),
        attribute='assignsites',
        default=utils.get_or_create_none_bv
    )
    ID = fields.Field(attribute='id')
    class Meta:
        model = pm.Pgbelonging
        skip_unchanged = True
        report_skipped = True
        #import_id_fields = ['ID']
        fields = ['GROUP', 'PEOPLE', 'CLIENT', 'BV', 'SITE','ID']

    def __init__(self, *args, **kwargs):
        super(GroupBelongingResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
    def before_import_row(self, row, row_number, **kwargs):
        if row.get('Group Name*') in ['', 'NONE', None]: raise ValidationError({'Group Name':"This field is required"})
        if row.get('Of Site') in ['', 'NONE', None] and row.get('Of People') in ['', 'NONE', None]:
            raise ValidationError("Either Site or People should be set, both cannot be None")
        
        # unique record check
        if pm.Pgbelonging.objects.select_related().filter(
            people__peoplecode=row['Of People'], pgroup__groupname=row['Group Name*'],
            client__bucode = row['Client*'],
            assignsites__bucode = row['Of Site'], bu__bucode=row['Site*']).exists():
            raise ValidationError(f"Record with these values already exist {row.values()}")
        super().before_import_row(row, **kwargs)
    
    


@admin.register(Pgbelonging)
class PgbelongingAdmin(ImportExportModelAdmin):
    resource_class = GroupBelongingResource
    fields = ['id', 'pgroup', 'people',
              'isgrouplead', 'assignsites', 'bu', 'client']
    list_display = ['id', 'pgroup', 'people',
                    'isgrouplead', 'assignsites', 'bu']
    list_display_links = ['pgroup', 'people']

class CapabilityResource(resources.ModelResource):

    parent = fields.Field(
        column_name='Belongs To',
        attribute='parent',
        widget = wg.ForeignKeyWidget(pm.Capability, 'capscode'))

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
    Code = fields.Field(attribute='capscode')
    Name = fields.Field(attribute='capsname')
    cfor = fields.Field(attribute='cfor', column_name='Capability For')


    class Meta:
        model = Capability
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ('Code',)
        fields = ('Code',  'Name', 'cfor',
                  'parent', 'Client', 'BV', 'tenant')


    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.is_superuser = kwargs.pop('is_superuser', None)
        super(CapabilityResource, self).__init__(*args, **kwargs)

    def before_save_instance(self, instance, row=None, **kwargs):
        instance.capscode = instance.capscode.upper()
        utils.save_common_stuff(self.request, instance, self.is_superuser)

    def skip_row(self, instance, original, row, import_validation_errors=None):
        super().skip_row(instance, original, row, import_validation_errors=None)
        return Capability.objects.filter(capscode = instance.capscode, cfor = instance.cfor).exists()
    
@admin.register(Capability)
class CapabilityAdmin(ImportExportModelAdmin):
    resource_class = CapabilityResource
    fields = ['capscode', 'capsname', 'cfor', 'parent']
    list_display = ['capscode', 'capsname', 'enable', 'cfor', 'parent',
                    'cdtz', 'mdtz', 'cuser', 'muser']
    list_display_links = ['capscode', 'capsname']


    def get_resource_kwargs(self, request, *args, **kwargs):
        return {'request': request}

    def get_queryset(self, request):
        return pm.Capability.objects.select_related(
            'parent', 'cuser', 'muser').all()

class GroupResourceUpdate(resources.ModelResource):
    Client = fields.Field(
        column_name = 'Client',
        attribute = 'client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default = 'NONE'
    )

    BV = fields.Field(
        column_name = 'Site',
        attribute = 'bu',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default = 'NONE'
    )

    Identifier = fields.Field(
        attribute = 'identifier',
        column_name = 'Type',
        widget = EnabledTypeAssistWidget(om.TypeAssist, 'tacode'),
    )

    ID = fields.Field(attribute='id', column_name='ID*')
    Enable = fields.Field(attribute='enable', column_name='Enable', widget=wg.BooleanWidget(), default=True)
    Name = fields.Field(attribute='groupname', column_name='Group Name')
    
    class Meta:
        model = pm.Pgroup
        skip_unchanged = True
        #import_id_fields = ['ID']
        report_skipped = True,
        fields = ['ID', 'Client', 'BV','Identifier', 'Enable', 'Name']
    
    def __init__(self, *args, **kwargs):
        super(GroupResourceUpdate, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
    def before_import_row(self, row, row_number, **kwargs):
        if 'Name' in row:
            row['Name'] = clean_string(row.get('Name'))
        # check required fields
        if row.get('ID*') in ['', 'NONE', None] or (isinstance(row.get('ID*'), float) and math.isnan(row.get('ID*'))): raise ValidationError({'ID*':"This field is required"})
        if 'Name' in row:
            if row.get('Name') in ['', None]: raise ValidationError({'Name': "This field is required"})
        if 'Type' in row:
            if row.get('Type') in ['', None]: raise ValidationError({'Type':'This field is required'})
            if row['Type'] not in ['PEOPLEGROUP', 'SITEGROUP']:
                raise ValidationError({'Type':"The value must be from ['PEOPLEGROUP', 'SITEGROUP']"})

        # unique record check
        if not Pgroup.objects.filter(id=row['ID*']).exists():
            raise ValidationError(f"Record with these values not exist: ID - {row['ID*']}")
        super().before_import_row(row, **kwargs)

    def before_save_instance(self, instance, using_transactions, dry_run=False):
        utils.save_common_stuff(self.request, instance, self.is_superuser)

class GroupBelongingResourceUpdate(resources.ModelResource):
    CLIENT = fields.Field(
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

    GROUP = fields.Field(
        column_name = 'Group Name',
        attribute = 'pgroup',
        widget = wg.ForeignKeyWidget(pm.Pgroup, 'groupname'),
        default = utils.get_or_create_none_pgroup
    )

    PEOPLE = fields.Field(
        column_name = 'Of People',
        attribute = 'people',
        widget = wg.ForeignKeyWidget(pm.People, 'peoplecode'),
        default = utils.get_or_create_none_people
    )

    SITE = fields.Field(
        column_name = 'Of Site',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        attribute = 'assignsites',
        default = utils.get_or_create_none_bv
    )

    ID = fields.Field(attribute='id', column_name='ID*')
    
    class Meta:
        model = pm.Pgbelonging
        skip_unchanged = True
        report_skipped = True
        #import_id_fields = ['ID']
        fields = ['ID', 'GROUP', 'PEOPLE', 'CLIENT', 'BV', 'SITE']

    def __init__(self, *args, **kwargs):
        super(GroupBelongingResourceUpdate, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
    def before_import_row(self, row, row_number, **kwargs):
        if row.get('ID*') in ['', 'NONE', None] or (isinstance(row.get('ID*'), float) and math.isnan(row.get('ID*'))): raise ValidationError({'ID*':"This field is required"})
        if 'Group Name' in row:
            if row.get('Group Name') in ['', 'NONE', None]: raise ValidationError({'Group Name':"This field is required"})
        if 'Of Site' in row and 'Of People' in row:
            if row.get('Of Site') in ['', 'NONE', None] and row.get('Of People') in ['', 'NONE', None]:
                raise ValidationError("Either Site or People should be set, both cannot be None")
        
        # check record exists
        if not pm.Pgbelonging.objects.filter(id=row['ID*']).exists():
            raise ValidationError(f"Record with these values not exist: ID - {row['ID*']}")
        super().before_import_row(row, **kwargs)


class PeopleResourceUpdate(resources.ModelResource):
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
    
    Department = fields.Field(
        column_name = 'Department',
        attribute = 'department',
        widget = TypeAssistDepartmentFKWUpdate(om.TypeAssist, 'tacode'),
        default = default_ta
    )

    Designation = fields.Field(
        column_name = 'Designation',
        attribute = 'designation',
        widget = TypeAssistDesignationFKWUpdate(om.TypeAssist, 'tacode'),
        default = default_ta
    )

    PeopleType = fields.Field(
        column_name = 'Employee Type',
        attribute = 'peopletype',
        widget = TypeAssistEmployeeTypeFKWUpdate(om.TypeAssist, 'tacode'),
        default = default_ta
    )

    WorkType = fields.Field(
        column_name = 'Work Type',
        attribute = 'worktype',
        widget = TypeAssistWorkTypeFKWUpdate(om.TypeAssist, 'tacode'),
        default = default_ta
    )

    Reportto = fields.Field(
        column_name = 'Report To',
        attribute = 'reportto',
        widget = wg.ForeignKeyWidget(pm.People, 'peoplename'),
        default = utils.get_or_create_none_people
    )

    DateOfBirth = fields.Field(
        column_name = 'Date of Birth',
        attribute = 'dateofbirth',
        widget = wg.DateWidget()
    )
    
    DateOfJoin = fields.Field(
        column_name='Date of Join',
        attribute='dateofjoin',
        widget = wg.DateWidget()
    )
    
    date_of_release = fields.Field(
        column_name='Date of Release',
        attribute='dateofreport',
        widget = wg.DateWidget()
    )
    
    ID                 = fields.Field(attribute='id', column_name='ID*')
    Code               = fields.Field(attribute='peoplecode', column_name='Code')
    userfor            = fields.Field(column_name='User For', attribute='people_extras.userfor', default='Mobile')
    deviceid           = fields.Field(attribute='deviceid', column_name='Device Id', default=-1)
    Name               = fields.Field(attribute='peoplename', column_name='Name')
    LoginId            = fields.Field(attribute='loginid', column_name='Login ID')
    MobNo              = fields.Field(attribute='mobno', column_name='Mob No')
    Email              = fields.Field(attribute='email', column_name='Email')
    Gender             = fields.Field(attribute='gender', column_name='Gender')
    Enable             = fields.Field(widget=wg.BooleanWidget(), attribute='enable', default=True)
    isemergencycontact = fields.Field(column_name='Is Emergency Contact', attribute='people_extras.isemergencycontact', widget=wg.BooleanWidget(), default=False)
    alertmails         = fields.Field(column_name='Alert Mails', attribute='people_extras.alertmails', widget=wg.BooleanWidget(), default=False)
    mobilecaps         = fields.Field(column_name='Mobile Capability', attribute='people_extras.mobilecapability', default=[])
    reportcaps         = fields.Field(column_name='Report Capability', attribute='people_extras.reportcapability', default=[])
    webcaps            = fields.Field(column_name='Web Capability', attribute='people_extras.webcapability', default=[])
    currentaddr        = fields.Field(column_name='Current Address', attribute='people_extras.currentaddress', default="")
    portletcaps        = fields.Field(column_name='Portlet Capability', attribute='people_extras.portletcapability', default=[])
    blacklist          = fields.Field(column_name='Blacklist', attribute='people_extras.blacklist', widget=wg.BooleanWidget(), default=False)

    class Meta:
        model = pm.People
        skip_unchanged = True
        report_skipped = True
        #import_id_fields = ['ID']
        fields = [
            'ID', 'Code', 'Name', 'LoginId', 'Designation', 'Department', 'MobNo', 'Email', 'deviceid',
            'Site', 'DateOfJoin', 'date_of_release', 'DateOfBirth', 'Gender', 'PeopleType','WorkType', 
            'Enable', 'Client', 'isemergencycontact', 'alertmails', 'mobilecaps', 'reportcaps', 
            'webcaps', 'portletcaps', 'blacklist', 'currentaddr', 'Reportto', 'userfor']

    def __init__(self, *args, **kwargs):
        super(PeopleResourceUpdate, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
        
    def before_import_row(self, row, **kwargs):
        self.validations(row)
        if 'Mobile Capability' in row:
            self._mobilecaps         = clean_array_string(row['Mobile Capability']) if row.get('Mobile Capability') else []
        if "Report Capability" in row:
            self._reportcaps         = clean_array_string(row["Report Capability"]) if row.get('Report Capability') else []
        if "Web Capability" in row:
            self._webcaps            = clean_array_string(row["Web Capability"]) if row.get('Web Capability') else []
        if "Portlet Capability" in row:
            self._portletcaps        = clean_array_string(row["Portlet Capability"]) if row.get('Portlet Capability') else []
        if 'Alert Mails' in row:
            self._alertmails         = row.get('Alert Mails') or False
        if 'Blacklist' in row:
            self._blacklist          = row.get('Blacklist') or False
        if 'Current Address' in row:
            self._currentaddr        = row.get('Current Address', "")
        if 'Is Emergency Contact' in row:
            self._isemergencycontact = row.get('Is Emergency Contact') or False
        if 'User For' in row:
            self._userfor            = row.get('User For') or 'Mobile'
        if 'Mob No' in row:
            row['Mob No'] = str(row['Mob No'])

    def before_save_instance(self, instance, using_transactions, dry_run):
        instance.email        = instance.email.lower()
        if not hasattr(instance, 'people_extras') or instance.people_extras is None:
            instance.people_extras = {}
        if hasattr(self, '_mobilecaps'):
            instance.people_extras['mobilecapability']   = self._mobilecaps
        if hasattr(self, '_reportcaps'):
            instance.people_extras['reportcapability']   = self._reportcaps
        if hasattr(self, '_webcaps'):
            instance.people_extras['webcapability']      = self._webcaps
        if hasattr(self, '_portletcaps'):
            instance.people_extras['portletcapability']  = self._portletcaps
        if hasattr(self, '_blacklist'):
            instance.people_extras['blacklist']          = self._blacklist
        if hasattr(self, '_isemergencycontact'):
            instance.people_extras['isemergencycontact'] = self._isemergencycontact
        if hasattr(self, '_alertmails'):
            instance.people_extras['alertmails']         = self._alertmails
        if hasattr(self, '_currentaddr'):
            instance.people_extras['currentaddress']     = clean_string(self._currentaddr)
        if hasattr(self, '_userfor'):
            instance.people_extras['userfor']          = self._userfor
        utils.save_common_stuff(self.request, instance)
    
    def validations(self, row):
        if 'Code' in row:
            row['Code'] = clean_string(row.get('Code', 'NONE'), code=True)
        if 'Name' in row:
            row['Name'] = clean_string(row.get('Name', "NONE"))
        # check required fields
        if row.get('ID*') in ['', 'NONE', None] or (isinstance(row.get('ID*'), float) and math.isnan(row.get('ID*'))): raise ValidationError({'ID*':"This field is required"})
        if 'Code' in row:
            if row['Code'] in ['', None]: raise ValidationError("Code is required field")
        # if 'Employee Type' in row:
        #     if row['Employee Type'] in ['', None, 'NONE']: raise ValidationError("Employee Type is required field & should not be NONE")
        if 'Name' in row:
            if row['Name'] in ['', None]: raise ValidationError("Name is required field")
        if 'User For' in row:
            if row['User For'] in ['', None]: raise ValidationError("User For is required field")
        # if 'Work Type' in row:
        #     if row['Work Type'] in ['', None, 'NONE']: raise ValidationError("Work Type is required field & should not be NONE")
        # if 'Designation' in row:
        #     if row['Designation'] in ['', None, 'NONE']: raise ValidationError("Designation is required field & should not be NONE")
        # if 'Department' in row:
        #     if row['Department'] in ['', None, 'NONE']: raise ValidationError("Department is required field & should not be NONE")
        
        # code validation
        if 'Code' in row:
            regex, value = "^[a-zA-Z0-9\-_]*$", row['Code']
            if re.search(r'\s|__', value): raise ValidationError("Please enter text without any spaces")
            if not re.match(regex, value):
                raise ValidationError("Please enter valid text avoid any special characters except [_, -]")
        
        # mob no validation
        if 'Mob No' in row:
            if not utils.verify_mobno(str(row.get('Mob No', -1))):
                raise ValidationError("Mob No is not valid")
            else: 
                mob_no = str(row['Mob No'])
                row['Mob No'] = mob_no if '+' in mob_no else f'+{mob_no}'
        
        # check record exists
        if not pm.People.objects.filter(id=row['ID*']).exists():
            raise ValidationError(f"Record with these values not exist: ID - {row['ID*']}")