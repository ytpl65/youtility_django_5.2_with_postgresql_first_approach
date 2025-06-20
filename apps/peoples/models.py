from django.contrib.auth.models import Group
from django.db.models import CharField
from django.urls import reverse
from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid
from django.utils.translation import gettext_lazy as _
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from .managers import PeopleManager, CapabilityManager, PgblngManager, PgroupManager
from apps.tenants.models import TenantAwareModel
import logging
logger = logging.getLogger('django')

# Create your models here.

def peoplejson():
    return {
        "andriodversion"           : "",
        "appversion"               : "",
        "mobilecapability"         : [],
        "portletcapability"        : [],
        "reportcapability"         : [],
        "webcapability"            : [],
        "noccapability"            : [],    
        "loacationtracking"        : False,
        "capturemlog"              : False,
        "showalltemplates"         : False,
        "debug"                    : False,
        "showtemplatebasedonfilter": False,
        "blacklist"                : False,
        "assignsitegroup"          : [],
        "tempincludes"             : [],
        "mlogsendsto"              : "",
        "user_type"                : "",
        "secondaryemails"          : [],
        'secondarymobno'           : [],
        'isemergencycontact'       : False,
        'alertmails'               : False,
        'currentaddress'          : "",
        'permanentaddress'        : "",
        "isworkpermit_approver":  False,
        'userfor':""
    }

def upload_peopleimg(instance, filename):
    try:
        logger.info('uploading peopleimg...')
        from os.path import join
        peoplecode = instance.peoplecode
        peoplename = instance.peoplename.replace(" ", "_")
        full_filename = f'{peoplecode}_{peoplename}__{filename}'
        foldertype = 'people'
        basedir = fyear = fmonth = None
        basedir = "master"
        client = f'{instance.client.bucode}_{instance.client_id}'
        filepath = join(basedir, client, foldertype, full_filename)
        filepath = str(filepath).lower()
        fullpath = filepath
    except Exception:
        logger.critical(
            'upload_peopleimg(instance, filename)... FAILED', exc_info = True)
    else:
        logger.info('people image uploaded... DONE')
        return fullpath

class SecureString(CharField):
    """Custom Encrypted Field"""

    @staticmethod
    def from_db_value(value, expression, connection):
        # from .utils import decrypt
        if value != "":
            return value
            # return decrypt(value)

    @staticmethod
    def get_prep_value(value):
        # from .utils import encrypt
        if value != "":
            return value
            # return encrypt(value)

def now():
    return timezone.now().replace(microsecond = 0)

### Base Model, ALl other models inherit this model properties ###
class BaseModel(models.Model):
    cuser = models.ForeignKey(settings.AUTH_USER_MODEL, null = True, blank = True, on_delete = models.RESTRICT, related_name="%(class)s_cusers")
    muser = models.ForeignKey(settings.AUTH_USER_MODEL,  null = True, blank = True,on_delete = models.RESTRICT, related_name="%(class)s_musers")
    cdtz  = models.DateTimeField(_('cdtz'), default = now)
    mdtz  = models.DateTimeField(_('mdtz'), default = now)
    ctzoffset = models.IntegerField(_("TimeZone"), default=-1)

    class Meta:
        abstract = True
        ordering = ['mdtz']

############## People Table ###############
class People(AbstractBaseUser, PermissionsMixin, TenantAwareModel, BaseModel):
    class Gender(models.TextChoices):
        M = ('M', 'Male')
        F = ('F', 'Female')
        O = ('O', 'Others')
    uuid          = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4, null = True)
    peopleimg     = models.ImageField(_("peopleimg"), upload_to = upload_peopleimg, default="master/people/blank.png", null = True, blank = True)
    peoplecode    = models.CharField(_("Code"), max_length = 50)
    peoplename    = models.CharField(_("Name"), max_length = 120)
    location      = models.ForeignKey("activity.Location",  verbose_name= _('Location'), on_delete=models.RESTRICT, null=True, blank=True)
    loginid       = models.CharField(_("Login Id"), max_length = 50, unique = True, null = True, blank = True)
    isadmin       = models.BooleanField(_("Admin"), default = False)
    is_staff      = models.BooleanField(_('staff status'), default = False)
    isverified    = models.BooleanField(_("Active"), default = False)
    enable        = models.BooleanField(_("Enable"), default = True)
    department    = models.ForeignKey("onboarding.TypeAssist", verbose_name='Department', null = True, blank = True,on_delete = models.RESTRICT, related_name='people_departments')
    designation   = models.ForeignKey("onboarding.TypeAssist", verbose_name='Designation', null = True, blank = True,on_delete = models.RESTRICT, related_name='people_designations')
    peopletype    = models.ForeignKey("onboarding.TypeAssist", verbose_name="People Type",null = True, blank = True, on_delete = models.RESTRICT, related_name='people_types')
    worktype      = models.ForeignKey("onboarding.TypeAssist", verbose_name="Work Type",null = True, blank = True, on_delete = models.RESTRICT, related_name='work_types')
    client        = models.ForeignKey("onboarding.Bt", verbose_name='Client',  null = True, blank = True, on_delete = models.RESTRICT, related_name='people_clients')
    bu            = models.ForeignKey("onboarding.Bt",  verbose_name='Site', null = True, blank = True,on_delete = models.RESTRICT, related_name='people_bus')
    reportto      = models.ForeignKey("self", null = True, blank = True, on_delete = models.RESTRICT, related_name='children', verbose_name='Report to')
    deviceid      = models.CharField(_("Device Id"), max_length = 50, default='-1')
    email         = SecureString(_("Email"), max_length = 254)
    mobno         = SecureString(_("Mob No"), max_length = 254, null = True)
    gender        = models.CharField(_("Gender"), choices = Gender.choices, max_length = 15, null = True)
    dateofbirth   = models.DateField(_("Date of Birth"))
    dateofjoin    = models.DateField(_("Date of Join"), null=True)
    dateofreport  = models.DateField(_("Date of Report"), null = True, blank = True)
    people_extras = models.JSONField(_("people_extras"), default = peoplejson, blank = True, encoder = DjangoJSONEncoder)

    objects = PeopleManager()
    USERNAME_FIELD = 'loginid'
    REQUIRED_FIELDS = ['peoplecode',  'peoplename', 'dateofbirth',
                        'email']

    class Meta:
        db_table = 'people'
        constraints = [
            models.UniqueConstraint(
                fields=['loginid', 'peoplecode', 'bu'], name='peolple_logind_peoplecode_bu_uk'),
            models.UniqueConstraint(
                fields=['peoplecode', 'bu'], name='people_peoplecode_bu'),
            models.UniqueConstraint(
                fields=['loginid', 'bu'], name='people_loginid_bu_uk'),
            models.UniqueConstraint(
                fields=['loginid', 'mobno', 'email', 'bu'], name='loginid_mobno_email_bu_uk'),
        ]

    def __str__(self) -> str:
        return f'{self.peoplename} ({self.peoplecode})'

    def get_absolute_wizard_url(self):
        return reverse("peoples:wiz_people_update", kwargs={"pk": self.pk})
    

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from apps.core import utils
        if self.department is None: self.department = utils.get_none_typeassist()
        if self.designation is None: self.designation = utils.get_none_typeassist()
        if self.peopletype is None: self.peopletype = utils.get_none_typeassist()
        if self.worktype is None: self.worktype = utils.get_none_typeassist()
        if self.reportto is None: self.reportto = utils.get_or_create_none_people()
        
    

############## Pgroup Table ###############
class PermissionGroup(Group):
    class Meta:
        db_table = 'permissiongroup'
        verbose_name = _('permissiongroup')
        verbose_name_plural = _('permissiongroups')

class Pgroup(BaseModel, TenantAwareModel):
    # id= models.BigIntegerField(_("Groupid"), primary_key = True, auto_created=)
    groupname  = models.CharField(_('Name'), max_length = 250)
    grouplead = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.RESTRICT,  related_name="pgroup_groupleads")
    enable     = models.BooleanField(_('Enable'), default = True)
    identifier = models.ForeignKey('onboarding.TypeAssist', verbose_name='Identifier', null = True, blank = True, on_delete = models.RESTRICT, related_name="pgroup_idfs")
    bu       = models.ForeignKey("onboarding.Bt", verbose_name='BV', null = True, blank = True, on_delete = models.RESTRICT, related_name='pgroup_bus')
    client   = models.ForeignKey('onboarding.Bt', verbose_name='Client', null = True, blank = True, on_delete = models.RESTRICT, related_name='pgroup_clients')

    objects = PgroupManager()

    class Meta(BaseModel.Meta):
        db_table = 'pgroup'
        constraints = [
            models.UniqueConstraint(
                fields=['groupname', 'identifier', 'client'],
                name='pgroup_groupname_bu_client_identifier_key'),
            models.UniqueConstraint(
                fields=['groupname', 'identifier', 'client'],
                name='pgroup_groupname_bu_identifier_key')
        ]
        get_latest_by = ["mdtz", 'cdtz']

    def __str__(self) -> str:
        return self.groupname

    def get_absolute_wizard_url(self):
        return reverse("peoples:wiz_pgropup_update", kwargs={"pk": self.pk})
    

############## Pgbelonging Table ###############
class Pgbelonging(BaseModel, TenantAwareModel):
    # id          = models.BigIntegerField(_("Pgbid"), primary_key = True)
    pgroup      = models.ForeignKey('Pgroup', null = True, blank = True, on_delete = models.RESTRICT, related_name="pgbelongs_grps")
    people      = models.ForeignKey(settings.AUTH_USER_MODEL, null = True, blank = True, on_delete = models.RESTRICT,  related_name="pgbelongs_peoples")
    isgrouplead = models.BooleanField(_('Group Lead'), default = False)
    assignsites = models.ForeignKey('onboarding.Bt', null = True,  blank = True, on_delete = models.RESTRICT, related_name="pgbelongs_assignsites")
    bu          = models.ForeignKey("onboarding.Bt", null = True, blank = True, on_delete = models.RESTRICT,  related_name='pgbelonging_sites')
    client      = models.ForeignKey('onboarding.Bt', null = True, blank = True, on_delete = models.RESTRICT, related_name='pgbelonging_clients')

    objects = PgblngManager()

    class Meta(BaseModel.Meta):
        db_table = 'pgbelonging'
        constraints = [
            models.UniqueConstraint(
                fields=['pgroup', 'people', 'assignsites', 'client'],
                name='pgbelonging_pgroup_people_bu_assignsites_client')
        ]
        get_latest_by = ["mdtz", 'cdtz']

    def __str__(self) -> str:
        return str(self.id)

############## Capability Table ###############
class Capability(BaseModel, TenantAwareModel):
    class Cfor(models.TextChoices):
        WEB     = ('WEB', 'WEB')
        PORTLET = ('PORTLET', 'PORTLET')
        REPORT  = ('REPORT', 'REPORT')
        MOB     = ('MOB', 'MOB')
        NOC     = ('NOC','NOC')
    # id   = models.BigIntegerField(_(" Cap Id"), primary_key = True)
    capscode = models.CharField(_('Code'), max_length = 50)
    capsname = models.CharField(_('Capability'), max_length = 1000, default = None, blank = True, null = True)
    parent   = models.ForeignKey('self', on_delete = models.RESTRICT,  null = True, blank = True, related_name='children', verbose_name="Belongs_to")
    cfor     = models.CharField(_('Capability_for'), max_length = 10, default='WEB', choices = Cfor.choices)
    client   = models.ForeignKey('onboarding.Bt', verbose_name='BV',  null = True, blank = True, on_delete = models.RESTRICT)
    enable   = models.BooleanField(_('Enable'), default = True)

    objects = CapabilityManager()

    class Meta(BaseModel.Meta):
        db_table = 'capability'
        verbose_name = 'Capability'
        verbose_name_plural = 'Capabilities'
        get_latest_by = ["mdtz", 'cdtz']
        constraints = [ 
            models.UniqueConstraint(
                fields=['capscode', 'cfor', 'client'],
                name="capability_caps_cfor_uk"), ]

    def __str__(self) -> str:
        return self.capscode

    def get_absolute_url(self):
        return reverse("peoples:cap_update", kwargs={"pk": self.pk})

    def get_all_children(self):
        children = [self]
        try:
            child_list = self.children.all()
        except AttributeError:
            return children
        for child in child_list:
            children.extend(child.get_all_children())
        return children

    def get_all_parents(self):
        parents = [self]
        if self.parent is not None:
            parent = self.parent
            parents.extend(parent.get_all_parents())
        return parents

