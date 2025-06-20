import logging
from apps.peoples import models as pm
from apps.tenants.models import Tenant
from apps.peoples import utils as putils
from apps.core import utils
from django.core.cache import cache

logger = logging.getLogger('django')
error_logger = logging.getLogger('error_logger')
debug_logger = logging.getLogger('debug_logger')

def save_jsonform(peoplepref_form, p):
    try:
        logger.info('saving jsonform ...')
        for k in [
            'blacklist', 'assignsitegroup', 'tempincludes', 'currentaddress', 'permanentaddress',
            'showalltemplates', 'showtemplatebasedonfilter', 'mobilecapability','noccapability','isemergencycontact',
            'portletcapability', 'reportcapability', 'webcapability', 'isworkpermit_approver',
            'alertmails', 'userfor']:
            p.people_extras[k] = peoplepref_form.cleaned_data.get(k)
    except Exception:
        logger.critical(
            'save_jsonform(peoplepref_form, p)... FAILED', exc_info=True)
        raise
    else:
        logger.info('jsonform saved DONE ... ')
        return True


def get_people_prefform(people,  request):
    try:
        logger.info('people prefform (json form) retrieving...')
        from .forms import PeopleExtrasForm
        d = {
            k: v
            for k, v in people.people_extras.items()
            if k
            in (
                'blacklist',
                'assignsitegroup',
                'tempincludes',
                'showalltemplates',
                'showtemplatebasedonfilter',
                'mobilecapability',
                'portletcapability',
                'reportcapability',
                'webcapability',
                'noccapability',
                'currentaddress',
                'permanentaddress',
                'isemergencycontact',
                'isworkpermit_approver',
                'alertmails',
                'userfor'
            )
        }

    except Exception:
        logger.critical('get_people_prefform(people)... FAILED', exc_info=True)
        raise
    else:
        logger.info('people prefform (json form) retrieved... DONE')
        return PeopleExtrasForm(data=d, request=request)


def save_cuser_muser(instance, user, create=None):
    from django.utils import timezone
    #instance is already created
    debug_logger.debug(f"while saving cuser and muser {instance.muser = } {instance.cuser = } {instance.mdtz = } {instance.cdtz = }")
    if instance.cuser is not None:
        logger.info("instance is already created")
        instance.muser = user
        instance.mdtz = timezone.now().replace(microsecond=0)
    #instance is being created
    else:
        logger.info("instance is being created")
        instance.cuser = instance.muser = user
        instance.cdtz = instance.mdtz = timezone.now().replace(microsecond=0)
    return instance


def save_client_tenantid(instance, user, session, client=None, bu=None):
    tenantid = session.get('tenantid')
    if bu is None:
        bu = session.get('bu_id')
    
    if hasattr(instance, 'client_id'):
        client = session.get('client_id') if instance.client_id  in [1, None] else instance.client_id
    if client is None: session.get('client_id')
    
    logger.info('client_id from session: %s', client)
    instance.tenant_id = tenantid
    instance.client_id = client
    instance.bu_id = bu
    logger.info("client info saved...DONE")
    return instance


def save_userinfo(instance, user, session, client=None, bu=None, create=True):
    """saves user's related info('cuser', 'muser', 'client', 'tenantid')
    from request and session"""
    from django.core.exceptions import ObjectDoesNotExist
    if user.is_authenticated:
        try:
            msg = "saving user and client info for the instance have been created"
            logger.info(f'{msg} STARTED')
            instance = save_client_tenantid(
                instance, user, session, client, bu)
            instance = save_cuser_muser(instance, user)
            instance.save()
            logger.info(f"while saving cdtz and mdtz id {instance.cdtz=} {instance.mdtz=}")
            logger.info(f'{msg} DONE')
        except (KeyError, ObjectDoesNotExist):
            instance.tenant = None
            instance.client = None
        except Exception:
            logger.critical("something went wrong !!!", exc_info=True)
            raise
        return instance


def validate_emailadd(val):
    try:
        from django import forms
        from .models import People
        user = People.objects.filter(email__exact=val)
        if not user.exists():
            raise forms.ValidationError("User with this email doesn't exist")
    except Exception:
        logger.critical('validate_emailadd(val)... FAILED', exc_info=True)
        raise


def validate_mobileno(val):
    try:
        from django import forms
        from .models import People
        user = People.objects.filter(mobno__exact=val)
        if not user.exists():
            raise forms.ValidationError(
                "User with this mobile no doesn't exist")
    except Exception:
        error_logger.error('validate_mobileno(val)... FAILED', exc_info=True)
        raise


def save_tenant_client_info(request):
    from apps.onboarding.models import Bt
    try:
        logger.info('saving tenant & client info into the session...STARTED')
        request.session['client_id'] = request.user.client.id
        request.session['bu_id'] = request.user.bu.id
        logger.info('saving tenant & client info into the session...DONE')
    except Exception:
        logger.critical('save_tenant_client_info failed', exc_info=True)
        raise

def get_caps_from_db():
    from apps.peoples.models import Capability
    from apps.core.raw_queries import get_query
    web, mob, portlet, report = [], [], [], []
    cache_ttl = 10
    web     = cache.get('webcaps')
    mob     = cache.get('mobcaps')
    portlet = cache.get('portletcaps')
    report  = cache.get('reportcaps')
    noc     = cache.get('noccaps')
    
    if not web:
        web = Capability.objects.get_caps(cfor=Capability.Cfor.WEB)
        cache.set('webcaps', web, cache_ttl)
    if not mob:
        mob = Capability.objects.get_caps(cfor=Capability.Cfor.MOB)
        cache.set('mobcaps', mob, cache_ttl)
    if not portlet:
        portlet = Capability.objects.get_caps(cfor=Capability.Cfor.PORTLET)
        cache.set('portletcaps', portlet, cache_ttl)
    if not report:
        report = Capability.objects.get_caps(cfor=Capability.Cfor.REPORT)
        cache.set('reportcaps', report, cache_ttl)
    return web, mob, portlet, report
    
    
def create_caps_choices_for_clientform():
    #get caps from db 
    return get_caps_from_db()


def create_caps_choices_for_peopleform(client):
    from apps.peoples.models import Capability
    from apps.core.raw_queries import get_query

    web, mob, portlet, report = [], [], [], []
    
    web     = cache.get('webcaps')
    mob     = cache.get('mobcaps')
    portlet = cache.get('portletcaps')
    report  = cache.get('reportcaps')
    noc     = cache.get('noccaps')
    
    if client:
        if not web:
            web = Capability.objects.filter(
                capscode__in = client.bupreferences['webcapability'], cfor=Capability.Cfor.WEB, enable=True).values_list('capscode', 'capsname')
            cache.set('webcaps', web, 30)
        if not mob:
            mob = Capability.objects.filter(
                capscode__in = client.bupreferences['mobilecapability'], cfor=Capability.Cfor.MOB, enable=True).values_list('capscode', 'capsname')
            cache.set('mobcaps', mob, 30)
        if not portlet:
            portlet = Capability.objects.filter(
                capscode__in = client.bupreferences['portletcapability'], cfor=Capability.Cfor.PORTLET, enable=True).values_list('capscode', 'capsname')
            cache.set('portletcaps', portlet, 30)
        if not report:
            report = Capability.objects.filter(
                capscode__in = client.bupreferences['reportcapability'], cfor=Capability.Cfor.REPORT, enable=True).values_list('capscode', 'capsname')
            cache.set('reportcaps', report, 30)
        if not noc:
            noc = Capability.objects.filter(cfor=Capability.Cfor.NOC, enable=True).values_list('capscode', 'capsname')
            cache.set('noccaps', report, 30)
    return web, mob, portlet, report, noc


def save_caps_inside_session_for_people_client(people, caps, session, client):
    debug_logger.debug(
        'saving capabilities info inside session for people and client...')
    #if client and people:
    #    session['people_mobcaps'] = make_choices(client.bu_preferences['mobilecapability'], fromclient=True) 
    session['people_webcaps'] = make_choices(
        people.people_extras['webcapability'], caps)
    session['people_mobcaps'] = make_choices(
        people.people_extras['mobilecapability'], caps)
    session['people_reportcaps'] = make_choices(
        people.people_extras['reportcapability'], caps)
    session['people_portletcaps'] = make_choices(
        people.people_extras['portletcapability'], caps)
    session['client_webcaps'] = make_choices(
        client.bupreferences['webcapability'], caps)
    session['client_mobcaps'] = make_choices(
        client.bupreferences['mobilecapability'], caps)
    session['client_noccaps'] = make_choices(
        client.bupreferences['noccapability'], caps)
    session['client_reportcaps'] = make_choices(
        client.bupreferences['reportcapability'], caps)
    session['client_portletcaps'] = make_choices(
        client.bupreferences['portletcapability'], caps)
    debug_logger.debug(
        'capabilities info saved in session for people and client... DONE')


def make_choices(caps_assigned, caps, fromclient=False):
    choices, parent_menus,  tmp = [], [], []
    logger.info('making choices started ...')
    for i in range(1, len(caps)):
        if i.cfor == 'WEB':
            if caps[i].capscode in caps_assigned and caps[i].depth == 3:
                tmp.append(caps[i])
            if tmp and caps[i].depth == 2 and caps[i-1].depth == 3:
                choice, menucode = get_choice(tmp, queryset=True)
                parent_menus.append(menucode)
                choices.append(choice)
                tmp = []
            if i == (len(caps)-1) and choices:
                choice, menucode = get_choice(tmp, queryset=True)
                parent_menus.append(menucode)
                choices.append(choice)
    if choices:
        debug_logger.debug('choices are made and returned... DONE')
    return choices, parent_menus


def get_choice(li, queryset=False):
    '''return tuple for making choices
        according to django synatax
    '''
    if not queryset:
        label = li[0].capscode
        t = (label, [])
        for i in li[1:]:
            t[1].append((i.capscode, i.capsname))
    else:
        label = li[0].parent.capscode
        t = (label, [])
        for i in li:
            t[1].append((i.capscode, i.capsname))

    tuple(t[1])
    return t


def get_cap_choices_for_clientform(caps, cfor):
    choices, temp = [], []
    debug_logger.debug('collecting caps choices for client form...')
    for i in range(1, len(caps)):
        if caps[i].cfor == 'WEB':
            if caps[i].depth in [3, 2]:
                if caps[i-1].depth == 3 and caps[i].depth == 2 and caps[i-1].cfor == cfor:
                    choices.append(get_choice(temp))
                    temp = []
                    temp.append(caps[i])
                else:
                    if caps[i].cfor == cfor:
                        temp.append(caps[i])
                    if i == len(caps)-1 and choices:
                        choices.append(get_choice(temp))
    if choices:
        debug_logger.debug('caps collected and returned... DONE')
    return choices


def make_choices(caps_assigned, caps):
    choices, tmp = [], []
    logger.info('making choices started ...')
    for i in range(1, len(caps)):
        if caps[i].capscode in caps_assigned and caps[i].depth == 3:
            tmp.append(caps[i])
        if tmp and caps[i].depth == 2 and caps[i-1].depth == 3:
            choice = get_choice(tmp, queryset=True)
            choices.append(choice)
            tmp = []
        if i == (len(caps)-1) and choices and tmp:
            choice = get_choice(tmp, queryset=True)
            choices.append(choice)
    if choices:
        debug_logger.debug('choices are made and returned... DONE')
    return choices

# call this method in session to save data inside session


def get_caps_choices(client=None, cfor=None,  session=None, people=None):
    '''get choices for capability clientform 
        or save choices in session'''
    from apps.peoples.models import Capability
    from apps.core.raw_queries import get_query
    caps = Capability.objects.raw(get_query('get_web_caps_for_client'))

    if cfor == Capability.Cfor.MOB:
        return Capability.objects.select_related(
            'parent').filter(cfor=cfor, enable=True).values_list('capscode', 'capsname')
    caps = cache.get('caps')
    if cfor == Capability.Cfor.NOC:
        return Capability.objects.select_related(
            'parent').filter(cfor=cfor, enable=True).values_list('capscode', 'capsname')
    if caps:
        debug_logger.debug('got caps from cache...')
    if not caps:
        debug_logger.debug('got caps from db...')
        caps = Capability.objects.raw(get_query('get_web_caps_for_client'))
        cache.set('caps', caps, 1*60)
        debug_logger.debug('results are stored in cache... DONE')

    if cfor:
        # return choices for client form
        return get_cap_choices_for_clientform(caps, cfor)




def save_user_paswd(user):
    logger.info('Password is created by system... DONE')
    paswd = f'{user.loginid}@youtility'
    user.set_password(paswd)
    user.save()


def display_user_session_info(session):
    logger.info('Following user data saved in sesion\n')
    


def get_choices_for_peoplevsgrp(request):
    site = request.user.bu
    return pm.People.objects.filter(
        bu__btid=site.btid).values_list(
            'people', 'peoplename')


def save_pgroupbelonging(pg, request):
    debug_logger.debug("saving pgbelonging for pgroup %s", (pg))
    from apps.onboarding.models import Bt
    peoples = request.POST.getlist('peoples[]')
    S = request.session
    if peoples:
        try:
            for i, item in enumerate(peoples):
                people = pm.People.objects.get(id=int(item))
                pgb = pm.Pgbelonging.objects.create(
                    pgroup=pg,
                    people=people,
                    client_id=S['client_id'],
                    bu_id=S['bu_id'],
                    assignsites_id = 1
                )
                if request.session.get('wizard_data'):
                    request.session['wizard_data']['pgbids'].append(pgb.id)
                save_cuser_muser(pgb, request.user)
        except Exception:
            debug_logger.debug("saving pgbelonging for pgroup %s FAILED", (pg))
            logger.critical("somthing went wrong", exc_info=True)
            raise
        else:
            debug_logger.debug("saving pgbelonging for pgroup %s DONE", (pg))

