from django.db import models
from datetime import datetime, timezone, timedelta
import json
import urllib.parse
from django.db.models import Q, When, Case, F, CharField,Count,IntegerField, Value as V
from django.db.models.functions import Cast
from apps.onboarding.models import TypeAssist
from apps.peoples.models import Pgbelonging
import logging
log = logging.getLogger('django')

def safe_json_parse_params(request_get, param_name='params'):
    """
    Safely parse JSON parameters from request.GET.
    Returns dict with default date range if parsing fails or keys missing.
    """
    from datetime import date, timedelta
    logger = logging.getLogger(__name__)
    
    params_raw = request_get.get(param_name, '{}')
    
    if params_raw in ['null', None, '']:
        parsed = {}
    else:
        try:
            # URL decode if necessary
            if params_raw.startswith('%'):
                params_raw = urllib.parse.unquote(params_raw)
            parsed = json.loads(params_raw)
        except (json.JSONDecodeError, TypeError) as e:
            # Fallback to empty dict if JSON parsing fails
            logger.warning(f"Failed to parse {param_name} JSON: {params_raw}, error: {e}")
            parsed = {}
    
    # Ensure required keys exist with default values
    today = date.today()
    parsed.setdefault('from', (today - timedelta(days=7)).strftime('%Y-%m-%d'))
    parsed.setdefault('to', today.strftime('%Y-%m-%d'))
    
    return parsed

class TicketManager(models.Manager):
    use_in_migrations = True
   
    def send_ticket_mail(self, ticketid):
        ticketmail = self.raw('''SELECT ticket.id, ticket.ticketlog,  ticket.comments, ticket.ticketdesc, ticket.cdtz,ticket.status, ticket.ticketno, ticket.level, bt.buname,
                ( ticket.cdtz + interval'1 minutes' ) createdon, ( ticket.mdtz + interval '1 minutes' ) modifiedon,  modifier.peoplename as  modifiername,                                       
                    people.peoplename, people.email as peopleemail, creator.id as creatorid, creator.email as creatoremail,
                    modifier.id as modifierid, modifier.email as modifiermail,pgroup.id as pgroupid, pgroup.groupname ,
                    ticket.assignedtogroup_id,  ticket.priority,
                    ticket.assignedtopeople_id, ticket.escalationtemplate as tescalationtemplate,                                                
                ( SELECT emnext.frequencyvalue || ' ' || emnext.frequency FROM escalationmatrix AS emnext                         
                WHERE  ticket.bu_id= emnext.bu_id AND ticket.escalationtemplate=emnext.escalationtemplate AND emnext.level=ticket.level + 1   
                ORDER BY cdtz LIMIT 1 ) AS next_escalation,
                (select array_to_string(ARRAY(select email from people where id in(select people_id from pgbelonging where pgroup_id=pgroup.id )),',') ) as pgroupemail                                                                     
                FROM ticket                                                                                                          
                LEFT  JOIN people modifier    ON ticket.muser_id=modifier.id                                                      
                LEFT JOIN people              ON ticket.assignedtopeople_id=people.id 
                LEFT JOIN pgroup              ON ticket.assignedtogroup_id=pgroup.id
                LEFT JOIN people creator      ON ticket.cuser_id =creator.id
                LEFT JOIN bt                  ON ticket.bu_id =bt.id
                WHERE ticket.id in (%s)''', [ticketid])
        return ticketmail or self.none() 
    
    def get_tickets_listview(self, request):
        R, S = request.GET, request.session
        P = safe_json_parse_params(R)
        qset = self.filter(
            cdtz__date__gte = P['from'],
            cdtz__date__lte = P['to'],
            bu_id__in = S['assignedsites'],
            client_id = S['client_id']
        ).select_related(
            'assignedtopeople', 'assignedtogroup', 'bu', 'ticketcategory').values(
            'id','ticketno', 'cdtz', 'bu__buname', 'status', 'bu__bucode', 'isescalated',
            'cuser__peoplename', 'cuser__peoplecode', 'ticketdesc', 'ctzoffset',
            'ticketsource', 'ticketcategory__taname'
        )
        if P.get('status') and P.get('status') != 'SYSTEMGENERATED':
            qset = qset.filter(status =P['status'],ticketsource = 'USERDEFINED')
        if P.get('status') and P.get('status') == 'SYSTEMGENERATED':
            qset = qset.filter(ticketsource='SYSTEMGENERATED')
        return qset or self.none()
    
        
    def get_tickets_for_mob(self, peopleid, buid, clientid, mdtz, ctzoffset):
        from apps.activity.models.attachment_model import Attachment
        
        if not isinstance(mdtz, datetime):
            mdtz = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S") - timedelta(minutes=ctzoffset)
            
        group_ids = list(Pgbelonging.objects.filter(~Q(pgroup_id = 1), people_id = peopleid).values_list('pgroup_id' , flat=True))
        qset = self.select_related(
            'assignedtopeople', 'assignedtogroup', 'bu', 'client', 
            'ticketcategory', 'location', 'performedby').filter(
                (Q(assignedtopeople_id = peopleid) | Q(cuser_id = peopleid) | Q(muser_id = peopleid)| Q(assignedtogroup_id__in = group_ids)),
                mdtz__gte = mdtz,
                bu_id = buid,
                client_id = clientid,
            ).values(
                'id', 'ticketno', 'uuid', 'ticketdesc', 'assignedtopeople_id', 'assignedtogroup_id', 'comments', 'bu_id', 'client_id', 'priority', 
                'events', 'isescalated', 'ticketsource', 'cuser_id', 'muser_id', 'cdtz', 'mdtz', 'ctzoffset', 'attachmentcount',
                'ticketcategory_id', 'location_id', 'asset_id','modifieddatetime', 'level', 'status', 'identifier', 'qset_id'
            )
        return qset or self.none()
    
    def get_ticketlist_for_escalation(self):
        from apps.core import utils, raw_queries
        return utils.runrawsql(raw_queries.get_query('get_ticketlist_for_escalation')) or self.none()

    def get_ticket_stats_for_dashboard(self, request):
        # sourcery skip: avoid-builtin-shadow
        S, R = request.session, request.GET
        qset = self.filter(
            bu_id__in = S['assignedsites'],
            cdtz__date__gte = R['from'],
            cdtz__date__lte = R['upto'],
            client_id = S['client_id']
        )
        user_generated = qset.filter(ticketsource = 'USERDEFINED')
        sys_generated = qset.filter(ticketsource = 'SYSTEMGENERATED')
        aggregate_user_generated_data = user_generated.aggregate(
            new = Count(Case(When(status='NEW',then=1),output_field=IntegerField())),
            open = Count(Case(When(status='OPEN',then=1),output_field=IntegerField())),
            cancelled = Count(Case(When(status='CANCELLED',then=1),output_field=IntegerField())),
            resolved = Count(Case(When(status='RESOLVED',then=1),output_field=IntegerField())),
            closed = Count(Case(When(status='CLOSED',then=1),output_field=IntegerField())),
            onhold = Count(Case(When(status='ONHOLD',then=1),output_field=IntegerField()))
        )
        autoclosed = sys_generated.count()
        stats = [
            aggregate_user_generated_data['new'],
            aggregate_user_generated_data['resolved'],
            aggregate_user_generated_data['open'],
            aggregate_user_generated_data['cancelled'],
            aggregate_user_generated_data['closed'],
            aggregate_user_generated_data['onhold'],
            autoclosed
        ]
        return stats, sum(stats)
    
    def get_events_for_calendar(self, request):
        S,R = request.session, request.GET
        start_date = datetime.strptime(R['start'], "%Y-%m-%dT%H:%M:%S%z").date()
        end_date = datetime.strptime(R['end'], "%Y-%m-%dT%H:%M:%S%z").date()
        
        qset = self.annotate(
            start=Cast(F('cdtz'), output_field=CharField()),
            end=Cast(F('modifieddatetime'), output_field=CharField()),
            title = F('ticketdesc'),
            color = Case(
                When(status__exact = self.model.Status.CANCEL, then = V('#727272')),
                When(status__exact = self.model.Status.ONHOLD, then= V( '#b87707')),
                When(status__exact = self.model.Status.CLOSED, then= V( '#13780e')),
                When(status__exact = self.model.Status.RESOLVED, then=V('#0d96ab')),
                When(status__exact = self.model.Status.NEW, then=V('#a14020')),
                When(status__exact = self.model.Status.OPEN, then=V('#004679')),
                output_field=CharField()
            )
        ).select_related().filter(
            cdtz__date__gte = start_date,
            cdtz__date__lte = end_date,
            bu_id = S['bu_id'],
            client_id = S['client_id']
        )
        qset = qset.values('id', 'start', 'end', 'title','color')
        return qset or self.none()

class ESCManager(models.Manager):
    use_in_migrations=True
    
    def get_reminder_config_forppm(self, job_id, fields):
        qset = self.filter(
            escalationtemplate__tacode="JOB",
            job_id = job_id
        ).values(*fields) 
        return qset or self.none()
    
    
    def handle_reminder_config_postdata(self,request):
        try:
            P, S = request.POST, request.session
            cdtz = datetime.now(tz = timezone.utc)
            mdtz = datetime.now(tz = timezone.utc)
            ppmjob = TypeAssist.objects.get(tatype__tacode='ESCALATIONTEMPLATE', tacode="JOB")
            PostData = {
                'cdtz':cdtz, 'mdtz':mdtz, 'cuser':request.user, 'muser':request.user,
                'level':1, 'job_id':P['jobid'], 'frequency':P['frequency'], 'frequencyvalue':P['frequencyvalue'],
                'notify':P['notify'], 'assignedperson_id':P['peopleid'], 'assignedgroup_id':P['groupid'], 
                'bu_id':S['bu_id'], 'escalationtemplate':ppmjob, 'client_id':S['client_id'], 
                'ctzoffset':P['ctzoffset']
            }
            if P['action'] == 'create':
                if self.filter(
                    job_id = P['jobid'],
                    frequency = PostData['frequency'], frequencyvalue = PostData['frequencyvalue'], 
                    ).exists():
                    return {'data':list(self.none()), 'error':'Warning: Record already added!'}
                ID = self.create(**PostData).id
            
            elif P['action'] == 'edit':
                PostData.pop('cdtz')
                PostData.pop('cuser')
                if updated := self.filter(pk=P['pk']).update(**PostData):
                    ID = P['pk']
            else:
                self.filter(pk = P['pk']).delete()
                return {'data':list(self.none()),}
            qset = self.filter(pk = ID).values('notify', 'frequency', 'frequencyvalue', 'id')
            return {'data':list(qset)}
        except Exception as e:
            log.critical("Unexpected error", exc_info=True)
            if 'frequencyvalue_gte_0_ck' in str(e):
                return {'data': [], 'error': "Invalid Reminder Before. It must be greater than or equal to 0."}
            if 'valid_notify_format' in str(e):
                return {'data': [], 'error': "Invalid Email ID format. Please enter a valid email address."}
            return {'data': [], 'error': "Something went wrong!"}
    

    def get_escalation_listview(self, request):
        R, S = request.GET, request.session
        from apps.onboarding.models import TypeAssist
        qset = TypeAssist.objects.filter(
            Q(bu_id__in = S['assignedsites'] + [1]) | Q(cuser_id=1) | Q(cuser__is_superuser=True),
            Q(client_id = S['client_id']) | Q(client_id=1),
            tatype__tacode__in = ['TICKETCATEGORY', 'TICKET_CATEGORY']
        ).select_related('tatype', 'bu').values(
            'taname', 'cdtz', 'id', 'ctzoffset', 'bu__buname', 'bu__bucode'
        )
        return qset or self.none()
    
    
    
    def handle_esclevel_form_postdata(self,request):
        try:
            P, S = request.POST, request.session
            cdtz = datetime.now(tz = timezone.utc)
            mdtz = datetime.now(tz = timezone.utc)
            PostData = {
                'cdtz':cdtz, 'mdtz':mdtz, 'cuser':request.user, 'muser':request.user,
                'level':P['level'], 'job_id':1, 'frequency':P['frequency'], 'frequencyvalue':P['frequencyvalue'],
                'notify':"", 'assignedperson_id':P['assignedperson'], 'assignedgroup_id':P['assignedgroup'], 
                'assignedfor':P['assignedfor'],
                'bu_id':S['bu_id'], 'escalationtemplate_id':P['escalationtemplate_id'], 'client_id':S['client_id'], 
                'ctzoffset':P['ctzoffset']
            }
        
            if P['action'] == 'create':
                if self.filter(
                    (Q(assignedgroup_id = P['assignedgroup']) & Q(assignedperson_id = P['assignedperson'])),
                    escalationtemplate_id = P['escalationtemplate_id'], 
                    ).exists():
                    return {'data':list(self.none()), 'error':'Warning: Record with this escalation template and people is already added!'}
                ID = self.create(**PostData).id
            
            elif P['action'] == 'edit':
                PostData.pop('cdtz')
                PostData.pop('cuser')
                if updated := self.filter(pk=P['pk']).update(**PostData):
                    ID = P['pk']
            else:
                self.filter(pk = P['pk']).delete()
                return {'data':list(self.none()),}
            qset = self.filter(pk = ID).values(
                'assignedfor', 'assignedperson__peoplename', 'assignedperson__peoplecode', 
                'assignedgroup__groupname', 'frequency', 'frequencyvalue', 'id', 'level',
                'assignedperson_id', 'assignedgroup_id')
            return {'data':list(qset)}
        except Exception as e:
            log.critical("Unexpected error", exc_info=True)
            if 'frequencyvalue_gte_0_ck' in str(e):
                return {'data': [], 'error': "Invalid Value. It must be greater than or equal to 0."}
            return {'data': [], 'error': "Something went wrong!"}

            
        
        