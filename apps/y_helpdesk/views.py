from django.shortcuts import render
from django.db.utils import IntegrityError
from apps.onboarding.models import TypeAssist
from .models import EscalationMatrix, Ticket
from .forms import TicketForm, EscalationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import response as rp
from apps.core import utils
from django.db import transaction
from django.http.request import QueryDict
from apps.peoples import utils as putils
from apps.peoples import models as pm

# Create your views here.
class EscalationMatrix(LoginRequiredMixin, View):
    P = {
        'model':EscalationMatrix,
        "fields":['frequencyvalue', 'frequency', 'notify', 'id'],
        'template_list':"y_helpdesk/escalation_list.html",
        'template_form':"y_helpdesk/escalation_form.html",
        'form': EscalationForm 
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.P        
        
        if R.get('action') == 'form':
            cxt = {'escform':P['form'](request=request)}
            return render(request, P['template_form'], cxt)
        
        if R.get('action') == 'loadPeoples':
            qset = pm.People.objects.getPeoplesForEscForm(request)
            return rp.JsonResponse({'items':list(qset), 'total_count':len(qset)}, status=200)
        
        if R.get('action') == 'loadGroups':
            qset = pm.Pgroup.objects.getGroupsForEscForm(request)
            return rp.JsonResponse({'items':list(qset), 'total_count':len(qset)}, status=200)
        
        if R.get('template') == 'true':
            return render(request, P['template_list'])
        
        if R.get('action') == 'list':
            objs = P['model'].objects.get_escalation_listview(request)
            return rp.JsonResponse({'data':list(objs)}, status=200)
        
        if R.get('action') == "get_escalationlevels" :
            objs = TypeAssist.objects.get_escalationlevels(request)
            return rp.JsonResponse({'data':objs}, status=200)
        
        if R.get('id') not in ['None', None]:
            initial = {'escalationtemplate': R['id']}
            cxt = {'escform':P['form'](request=request, initial=initial)}
            return render(request, P['template_form'], cxt)
        
        if R.get('action') == 'get_reminder_config' and R.get('job_id') not in [None, 'None']:
            objs  = P['model'].objects.get_reminder_config_forppm(R['job_id'], P['fields'])
            return rp.JsonResponse(data={'data':list(objs)})
        return rp.JsonResponse(data={'data':[]})
    
        
    
    def post(self, request, *args, **kwargs):
        R,P = request.POST, self.P
        if R.get('post') == 'postEscalations':
            data = P['model'].objects.handle_esclevel_form_postdata(request)
            return rp.JsonResponse(data, status = 200, safe=False)
        
        if R.get('post') == 'postReminder':
            data = P['model'].objects.handle_reminder_config_postdata(request)
            return rp.JsonResponse(data, status = 200, safe=False)



class TicketView(LoginRequiredMixin, View):
    params = {
        'model':Ticket,
        'form':TicketForm,
        'template':'y_helpdesk/ticket_form.html',
        'template_list':'y_helpdesk/ticket_list.html'
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        
        if R.get('action') == 'form':
            import uuid
            cxt = {'ticketform':P['form'](request=request), 'ownerid' : uuid.uuid4()}
            return render(request, P['template'], cxt)
        
        if R.get('template') == 'true':
            return render(request, P['template_list'])
        
        if R.get('action') == 'list':
            objs = P['model'].objects.get_tickets_listview(request)
            return rp.JsonResponse({'data':list(objs)}, status=200)        
        
        if R.get('id'):
            ticket = utils.get_model_obj(R['id'], request, P)
            if ticket.status == Ticket.Status.NEW.value and ticket.cuser != request.user:
                ticket.status, ticket.muser = Ticket.Status.OPEN.value, request.user
                ticket.save()
            cxt = {'ticketform':P['form'](instance=ticket, request=request), 'ownerid': ticket.uuid}
            return render(request, P['template'], cxt)
        
    
    def post(self, request, *args, **kwargs):
        R, P, data = request.POST, self.params, QueryDict(request.POST['formData'])
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                if pk:=R.get('pk'):
                    msg = 'ticket_view'
                    ticket = utils.get_model_obj(pk, request, P)
                    form = P['form'](data, request=request, instance=ticket)
                else:
                    form = P['form'](data, request=request)
                if form.is_valid():
                    return self.handle_valid_form(form, request)
                cxt = {'errors':form.errors}
                return utils.handle_invalid_form(request, P, cxt)
        except Exception as e:
            return utils.handle_Exception(request)
        
    def handle_valid_form(self, form, request):
        try:
            ticket = form.save(commit=False)
            ticket.uuid = request.POST.get('uuid')
            bu = ticket.bu_id if request.POST.get('pk') else None
            ticket = putils.save_userinfo(ticket, request.user, request.session, bu=bu)
            utils.store_ticket_history(ticket, request)
            return rp.JsonResponse({'pk':ticket.id}, status=200)
        except IntegrityError as e:
            return utils.handle_intergrity_error('Ticket')
        

class PostingOrderView(LoginRequiredMixin, View):
    from apps.activity.models.job_model import Jobneed,JobneedDetails
    params = {
        'template_list':'y_helpdesk/posting_order_list.html',
        'model':Jobneed,
    }
    def get(self, request, *args, **kwargs):  
        R, P = request.GET, self.params
        if R.get('template') == 'true':
            return render(request, P['template_list'])
        
        if R.get('action') == 'list':
            objs = P['model'].objects.get_posting_order_listview(request)
            return rp.JsonResponse({'data':list(objs)}, status=200) 
                
class UniformView(LoginRequiredMixin, View):
    params = {
        'template_list':'y_helpdesk/uniform_list.html',
    }
    def get(self, request, *args, **kwargs):  
        return render(request, 'y_helpdesk/uniform_form.html')
