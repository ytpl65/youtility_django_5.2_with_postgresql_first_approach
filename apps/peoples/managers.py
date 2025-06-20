from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.db.models import Q, F, Value as V
from django.db.models.functions import Concat, Cast
from django.contrib.gis.db.models.functions import  AsGeoJSON
from django.utils.translation import gettext_lazy as _
import logging
log = logging.getLogger('django')

class PeopleManager(BaseUserManager):
    use_in_migrations =  True
    fields = ['id', 'peoplecode', 'peoplename', 'loginid', 'isadmin', 'is_staff', 'isverified',
              'enable', 'department_id', 'designation_id', 'peopletype_id', 'client_id', 'uuid',
              'bu_id', 'cuser_id', 'muser_id', 'reportto_id', 'deviceid', 'enable', 'mobno',
              'cdtz', 'mdtz', 'gender', 'dateofbirth', 'dateofjoin', 'tenant_id', 'ctzoffset']
    related = ['bu', 'client', 'peopletype', 'muser', 'cuser', 'reportto', 'department', 'designation']

    def create_user(self, loginid, password = None, **extra_fields):
        if not loginid:
            raise ValueError("Login id is required for any user!")
        user = self.model(loginid = loginid, **extra_fields)
        user.set_password(password)
        user.save(using = self._db)
        return user

    def create_superuser(self, loginid, password = None, **extra_fields):
        if password is None:
            raise TypeError("Super users must have a password.")
        user = self.create_user(loginid, password, **extra_fields)

        user.is_superuser = True
        user.is_staff     = True
        user.isadmin      = True
        user.isverified  = True
        user.save(using = self._db)
        return user

    def get_people_from_creds(self, loginid, clientcode):
        if qset := self.select_related('client', 'bu').get(
            Q(loginid = loginid) & Q(client__bucode = clientcode)
        ):
            return qset

    def update_deviceid(self, deviceid, peopleid):
        return self.filter(id = peopleid).update(deviceid = deviceid)

    def reset_deviceid(self, peopleid):
        return self.filter(id = peopleid).update(deviceid = "-1")

    def get_people_modified_after(self, mdtz, siteid):
        """
        Returns latest sitepeople
        """
        qset = self.select_related(
            *self.related).filter(
                 Q(id=1) | Q(bu_id = siteid) & Q(mdtz__gte = mdtz)).values(*self.fields).order_by('-mdtz')
        return qset or self.none()

    def get_emergencycontacts(self, siteid, clientid):
        "returns mobnos of people with given assigned siteid"
        qset = self.filter(bu_id = siteid, client_id = clientid, people_extras__isemergencycontact = True).annotate(
            pmobno = Concat(F('peoplename'), V(':', output_field=models.CharField()), Cast('mobno', output_field=models.CharField()))
            ).values_list('pmobno', flat = True).exclude(mobno = None)
        return qset or self.none()

    def get_emergencyemails(self, siteid, clientid):
        "returns emails of people with given assigned siteid"
        qset = self.filter(bu_id = siteid, client_id = clientid, people_extras__isemergencycontact = True).values_list('email', flat = True)
        return qset or self.none()
    
    def controlroomchoices(self, request):
        "returns people whose worktype is in [AO, AM, CR] choices for bu form"
        qset = self.filter(
            Q(designation__tacode__in = ['CR']) |  Q(worktype__tacode__in = ['CR']),
            enable=True, client_id = request.session['client_id']
        ).annotate(text =Concat(F('peoplename'), V(' ('), F('peoplecode'), V(')'))).values_list('id', 'text')
        return qset or self.none()
    
    def get_people_for_posted_ppl_on_bu(self,request):
        qset = self.filter(client_id = request.session['client_id'],enable = True
                           ).exclude(
                               Q(designation__tacode__in = ['CR']) |  Q(worktype__tacode__in = ['CR'])
                           ).annotate( text = Concat(F('peoplename'), V(' ('), F('peoplecode'), V(')'))).values_list('id', 'text')
        return qset or self.none()
    
    def get_assigned_sites(self, clientid, peopleid):
        from apps.onboarding.models import Bt
        qset = Bt.objects.filter(id__gte=12, id__lte=150).annotate(
            text = Concat(F('buname'),  V(' ('), F('bucode'), V(')'))).values_list('id', 'text')
        
        return qset
    
    def get_people_pic(self, peopleid):
        "returns people picture"
        qset = self.filter(id = peopleid).annotate(
            default_img_path = Concat(V('youtility4_media/', output_field=models.CharField()), Cast('peopleimg', output_field=models.CharField()))).values_list('default_img_path', named=True)
        return qset[0] if qset else qset or self.none()
    

    def get_siteincharge_emails(self, buid):
        from apps.peoples.models import Pgbelonging
        
        grps = list(Pgbelonging.objects.annotate(
                groupid = Cast('pgroup_id', models.CharField())
            ).filter(
            assignsites_id=buid,
            people_id__in = [1, None],
            ).values_list(
                'groupid', flat=True))
        return self.filter( 
            Q(Q(bu_id=buid) | Q(people_extras__assignsitegroup__in = grps)) &   
            Q(Q(designation__tacode = 'SITEINCHARGE') | Q(worktype__tacode= 'SITEINCHARGE')) 
            & Q(isverified=True)).values_list(
                'email', flat=True
            ) or []
    
    def get_admin_emails(self, clientid):
        return self.filter(
            (Q(people_extras__alertmails=True) | Q(isadmin=True)) &
            Q(client_id=clientid) & Q(isverified=True),
            enable=True
        ).values_list('email', flat=True) or []
        
    def get_peoples_at_site(self, request):
        R = request.GET
        from apps.peoples.models import Pgbelonging
        from apps.activity.models.deviceevent_log_model import DeviceEventlog
        from itertools import chain
        
        bu_id = request.session['bu_id']
        sitegrp_ids = list(Pgbelonging.objects.filter(
            assignsites_id = bu_id
        ).values_list('pgroup_id', flat=True))
        
        
        qset = DeviceEventlog.objects.filter(
            Q(people__people_extras__assignsitegroup__in = sitegrp_ids) | Q(people__bu_id = bu_id),
            ).annotate(
                gps = AsGeoJSON('gpslocation'),
                peoplename = F('people__peoplename'),
                peoplecode = F('people__peoplecode'),
                mobno = F('people__mobno'),
                email = F('people__email'),
                lastlogin = F('people__last_login'),
                offset = F('people__ctzoffset'),
                designation = F('people__designation__taname'),
                worktype = F('people__worktype__taname')).values(
                    'gps', 'mobno', 'email', 'designation', 'worktype', 'offset','lastlogin',
                    'peoplename', 'peoplecode', 'people_id', 'platformversion',
                    'batterylevel', 'islocationmocked', 'modelname', 'people__bu__buname').order_by(
            'people_id', '-receivedon'
        ).distinct('people_id')
        return qset or self.none()
    
    
    def peoplechoices_for_pgroupform(self, request):
        S = request.session
        qset = self.select_related('client', 'bu').filter(
            enable=True,
                bu_id__in = S['assignedsites'],
            client_id=S['client_id'],            
        ).annotate(peopletext = Concat(F('peoplename'), V(' ('), F('peoplecode'), V(')'))).values_list('id', 'peopletext')
        return qset or self.none()

    def getPeoplesForEscForm(self, request):
        R = request.GET
        qset = self.peoplechoices_for_pgroupform(request)
        qset = qset.filter(peoplename__icontains = R['search']) if R.get('search')  else qset
        qset = qset.annotate(
            text = Concat(F('peoplename'), V(' ('), F('peoplecode'), V(')'))
        ).values('id', 'text')
        return qset or self.none()
    
    
    def filter_for_dd_people_field(self, request, choices=False, sitewise=False):
        S = request.session
        qset = self.filter(
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
            enable=True,
        )
        if sitewise:
            qset = qset.filter(bu_id = S['bu_id'])
        if choices:
            qset = qset.annotate(text = Concat(F('peoplename'), V(' ('), F('peoplecode'), V(')'))).values_list('id', 'text')
        return qset or self.none()
            

    def people_list_view(self, request, fields, related):
        S  = request.session
        if request.user.isadmin:
            qset = self.filter(
                ~Q(peoplecode='NONE'), 
                client_id = S['client_id']).select_related(*related).values(*fields).order_by('peoplename')
        else:
            qset = self.filter(
                ~Q(peoplecode='NONE'), 
                client_id = S['client_id'],
                bu_id__in = S['assignedsites']
            ).select_related(*related).values(*fields).order_by('peoplename')
        return qset or self.none()
    
    def get_sitemanager_or_emergencycontact(self, bu):
        from apps.onboarding.models import Bt
        if Bt.objects.filter(
            ~Q(siteincharge_id=1), id=bu.id, siteincharge__isnull=False).exists():
            return bu.siteincharge
        return self.filter(people_extras__isemergencycontact=True, bu_id=bu.id).first()


class CapabilityManager(models.Manager):
    use_in_migrations = True
    def get_webparentdata(self):
        return self.filter(cfor= self.pm.Capability.Cfor.WEB, parent__capscode='NONE')

    def get_mobparentdata(self):
        return self.filter(cfor = self.pm.Capability.Cfor.MOB, parent__capscode='NONE')

    def get_repparentdata(self):
        return self.filter(cfor = self.pm.Capability.Cfor.REPORT, parent__capscode='NONE')

    def get_portletparentdata(self):
        return self.filter(cfor = self.pm.Capability.Cfor.PORTLET, parent__capscode='NONE')

    def get_child_data(self, parent, cfor):
        return self.filter(cfor = cfor, parent__capscode = parent) if parent else None
    
    def get_caps(self, cfor):
        qset = self.filter(cfor = cfor, enable=True).values_list('capscode', 'capsname')
        return qset or self.none()



class PgblngManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'cuser_id', 'muser_id', 'bu_id', 'client_id', 'people_id', 'cdtz', 'mdtz',
              'assignsites_id', 'pgroup_id', 'isgrouplead', 'ctzoffset', 'tenant_id']
    related = ['cuser', 'muser', 'pgroup', 'people', 'client', 'bu']

    def get_modified_after(self, mdtz, peopleid, buid):
        qset = self.select_related(
            *self.related).filter(
                Q(people_id = peopleid) | Q(bu_id = buid),  mdtz__gte = mdtz).values(*self.fields).order_by('-mdtz')
        return qset or self.none()

    def get_assigned_sitesto_sitegrp(self, id):
        qset = self.select_related('pgroup').filter(pgroup_id = id).annotate(
            buname = F('assignsites__buname'),
            bucode = F('assignsites__bucode'),
            buid = F('assignsites__id'),
            solid = F('assignsites__solid'),
            gps = AsGeoJSON('assignsites__gpslocation')
        ).values('buname', 'buid', 'solid', 'bucode','gps')
        return qset or self.none()
    
    def get_sitesfromgroup(self, job, force=False):
        "return sites under group with given sitegroupid"
        if not force:
            from apps.activity.models.job_model import Job
            qset = Job.objects.get_sitecheckpoints_exttour(job)
        if force or not qset:
            qset = self.annotate(
                bu__gpslocation = AsGeoJSON('assignsites__gpslocation'),
                bu__buname = F('assignsites__buname'), bucode=F('assignsites__bucode'),
                buid = F('assignsites_id'), solid = F('assignsites__solid')
            ).select_related('assignsites', 'identifier').filter(
                pgroup_id = job['sgroup_id']
            ).values('bu__gpslocation', 'bucode', 'bu__buname', 'buid', 'solid')
            if qset:
                for q in qset:
                    q.update(
                        {'seqno':None, 'starttime':None, 'endtime':None, 'qsetid':job['qset_id'],
                        'qsetname':job['qset__qsetname'], 'duration':None, 'expirytime':None,
                        'distance':None, 'jobid':None, 'assetid':1, 'breaktime':None})
        return qset or self.none()
    
    
    def make_choices_of_sites(self, ids):
        from apps.onboarding.models import Bt
        qset = Bt.objects.annotate(
            text = Concat(F('buname'), V(' ('), F('bucode'), V(')'))
        ).filter(
            id__in = ids
        ).values_list('id', 'text')
        return qset or self.none()
    
    def return_sites_for_service(self, ids, fields):
        from apps.onboarding.models import Bt
        qset = Bt.objects.filter(
            id__in = ids
        ).annotate(
        bu_id = F('id')
        ).values(*fields)
        return qset or self.none()
        
    
    def get_assigned_sites_to_people(self, peopleid, makechoice=False, forservice=False):
        from apps.peoples.models import People
        from apps.onboarding.models import Bt
        
        # get default site of people
        people = People.objects.filter(id=peopleid).first()
        
        # if people is admin
        if people and people.isadmin:
            bu_ids = list(Bt.objects.get_all_sites_of_client(clientid=people.client_id).values_list('id', flat=True))
        else:
            assigned_sitegroup_ids = People.objects.filter(id = peopleid).values('people_extras__assignsitegroup').first()
            #get sites assigned to groupids
            bu_ids = list(self.select_related('assignsites').filter(
                pgroup_id__in = assigned_sitegroup_ids['people_extras__assignsitegroup']).values_list('assignsites_id', flat=True))
        
        # total site are: assgined + default
        total_assigned_sites = bu_ids + [people.bu_id]
        
        # for dropdown choices
        if makechoice: return self.make_choices_of_sites(total_assigned_sites + [1])
        
        # for mobile service
        if forservice: return self.return_sites_for_service(
            total_assigned_sites, ['buname', 'bucode', 'bu_id', 'butype_id','enable', 'cdtz', 'mdtz', 'siteincharge_id',
            'cuser_id', 'muser_id', 'skipsiteaudit', 'identifier_id', 'bupreferences', 'solid'])
        
        # for others
        return total_assigned_sites
            
            

class PgroupManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'groupname', 'enable', 'identifier_id', 'ctzoffset',
              'bu_id', 'client_id', 'tenant_id', 'cdtz', 'mdtz', 'cuser_id', 'muser_id']
    related = ['identifier', 'bu', 'client', 'cuser', 'muser']

    def listview(self, request, fields, related, orderby, dir = None, qobjs = None):
        # sourcery skip: assign-if-exp, swap-if-expression
        order = "" if dir == 'asc' else "-"
        if not qobjs:
            objs = self.select_related(
                *related).filter(
                    identifier__tacode = 'SITEGROUP').values(
                        *fields).order_by(f'{order}{orderby}')
        else:
            objs = self.select_related(
                *related).filter(
                    qobjs, identifier__tacode = 'SITEGROUP').values(
                        *fields).order_by(f'{order}{orderby}')

        return objs or self.none()

    def get_groups_modified_after(self, mdtz, buid):
        """
        Return latest group info
        """
        qset = self.select_related(
            *self.related).filter(
                Q(id=1) | Q(mdtz__gte = mdtz) & Q(bu_id = buid) &
                Q(identifier__tacode = "PEOPLEGROUP")).values(
                    *self.fields)
        return qset or None

    def list_view_sitegrp(self, R, request):
        S = request.session
        from apps.core import utils
        qobjs, dir,  fields, length, start = utils.get_qobjs_dir_fields_start_length(R)
        qset = self.filter(
            ~Q(groupname = 'NONE'), 
            identifier__tacode = 'SITEGROUP',
            client_id = S['client_id'],
        ).select_related('identifier').values(*fields).order_by(dir)

        total = qset.count()
        if qobjs:
            filteredqset = qset.filter(qobjs)
            fcount = filteredqset.count()
            filteredqset = filteredqset[start:start+length]
            return total, fcount, filteredqset
        qset = qset[start:start+length]
        return total, total, qset

    def get_assignedsitegroup_forclient(self, clientid, request):
        qset = self.filter(
             enable=True,
            client_id = clientid,
            identifier__tacode = 'SITEGROUP'
            ).values_list('id', 'groupname')
        return qset or self.none()

    def getGroupsForEscForm(self, request):
        R, S = request.GET, request.session 
        qset = self.filter(
            bu_id = S['bu_id'],
            client_id = S['client_id'],
            identifier__tacode = 'PEOPLEGROUP'
        ).select_related('identifier', 'bu', 'client')
        qset = qset.filter(groupname__icontains = R['search']) if R.get('search') else qset
        qset = qset.annotate(
            text = F('groupname')
        ).values('id', 'text')
        return qset or self.none()
    
    
    def filter_for_dd_pgroup_field(self, request, choices=False, sitewise=False):
        S = request.session
        qset = self.filter(
            (Q(groupname='NONE')| Q(enable=True) & Q(client_id = S['client_id']) & Q(bu_id__in = S['assignedsites']) & Q(identifier__tacode = 'PEOPLEGROUP'))
        )        
        if sitewise:
            qset = qset.filter(bu_id = S['bu_id'])
        if choices:
            qset = qset.values_list('id', 'groupname')
        return qset or self.none()
        