import logging
from datetime import datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.db.models import Q
from django.http import QueryDict
from django.http import response as rp
from django.shortcuts import render
from django.views.generic.base import View
from apps.activity.forms.job_form import PPMForm, PPMFormJobneed ,AdhocTaskForm
from apps.activity.models.job_model import Job, Jobneed, JobneedDetails
import apps.peoples.utils as putils
from apps.core import utils

logger = logging.getLogger('django')
    
class PPMView(LoginRequiredMixin, View):
    P = {
        'template_list':'activity/ppm/ppm_list.html',
        'template_form':'activity/ppm/ppm_form.html',
        'template_form_jn':'activity/ppm/jobneed_ppmform.html',
        'model_jn':Jobneed,
        'model':Job,
        'related':['asset', 'qset', 'people', 'pgroup', 'bu'],
        'fields':['plandatetime', 'expirydatetime', 'gracetime', 'asset__assetname', 
                  'assignedto', 'performedby__peoplename', 'jobdesc', 'frequency', 
                  'qset__qsetname', 'id', 'ctzoffset', 'bu__bucode', 'bu__buname'],
        'form':PPMForm,
        'form_jn':PPMFormJobneed
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.P
        # first load the template
        cxt = {
            'status_options':[
                ('COMPLETED', 'Completed'),
                ('AUTOCLOSED', 'AutoClosed'),
                ('ASSIGNED', 'Assigned'),
            ]
        }
        if R.get('template'): return render(request, P['template_list'], context=cxt)
        
        
        if R.get('action') == 'job_ppmlist':
            objs = P['model'].objects.get_jobppm_listview(request)
            return  rp.JsonResponse(data = {'data':list(objs)})
        
        # return questionset_form empty
        if R.get('action', None) == 'form':
            cxt = {'ppmform': P['form'](request=request),
                   'msg': "create PPM requested"}
            return render(request, P['template_form'], cxt)
        
        if R.get('action', None) == "delete" and R.get('id', None):
            return utils.render_form_for_delete(request, P, True)


        # return form with instance
        elif R.get('action') == "getppm_jobneedform" and  R.get('id', None):
            obj = Jobneed.objects.get(id = R['id'])
            cxt = {'ppmjobneedform': P['form_jn'](instance = obj, request=request),
                   'msg': "PPM Jobneed Update Requested"}
            return render(request, P['template_form_jn'], context = cxt)
        
        
        # return form with instance
        elif R.get('action') == "getppm_jobneedform" and  R.get('id', None):
            obj = Jobneed.objects.get(id = R['id'])
            cxt = {'ppmjobneedform': P['form_jn'](instance = obj, request=request),
                   'msg': "PPM Jobneed Update Requested"}
            return render(request, P['template_form_jn'], context = cxt)
        
        # return form with instance
        elif R.get('id', None):
            ppm = utils.get_model_obj(R['id'], request, P)
            cxt = {'ppmform': P['form'](instance = ppm, request=request),
                   'msg': "PPM Update Requested"}
            return render(request, P['template_form'], context = cxt)
    
    def post(self, request, *args, **kwargs):
        resp, create = None, True
        data = QueryDict(request.POST.get('formData'))
        try:
            if request.POST.get('action') == 'runScheduler':
                from background_tasks.tasks import create_ppm_job
                resp, F, d, story =  create_ppm_job(request.POST.get('job_id'))
                return rp.JsonResponse(resp, status=200)
            if pk := request.POST.get('pk', None):
                msg, create = "ppm view", False
                people = utils.get_model_obj(pk, request,  self.P)
                form = self.P['form'](data, request=request, instance = people)
            else:
                form = self.P['form'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    @staticmethod
    def handle_valid_form(form, request ,create):
        logger.info('ppm form is valid')
        from apps.core.utils import handle_intergrity_error
        
        try:
            ppm = form.save()
            ppm = putils.save_userinfo(
                ppm, request.user, request.session, create = create)
            logger.info("ppm form saved")
            data = {'pk':ppm.id}
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return handle_intergrity_error('PPM')
        
        
class PPMJobneedView(LoginRequiredMixin, View):
    P = {
        'template_list':'activity/ppm/ppm_jobneed_list.html',
        'template_form':'activity/ppm/jobneed_ppmform.html',
        'model':Jobneed,
        'related':['asset', 'qset', 'people', 'pgroup', 'bu', 'job'],
        'fields':['plandatetime', 'expirydatetime', 'gracetime', 'asset__assetname', 
                  'assignedto', 'performedby__peoplename', 'jobdesc', 'job__frequency', 
                  'qset__qsetname', 'id', 'ctzoffset', 'jobstatus', 'bu__bucode', 'bu__buname'],
        'form':PPMFormJobneed,
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.P
        # first load the template
        cxt = {
            'status_options':[
                ('COMPLETED', 'Completed'),
                ('AUTOCLOSED', 'AutoClosed'),
                ('ASSIGNED', 'Assigned'),
            ]
        }
        if R.get('template'): return render(request, P['template_list'], context=cxt)
        
        if R.get('action') == 'jobneed_ppmlist':
            objs = P['model'].objects.get_ppm_listview(request, P['fields'], P['related'])
            return  rp.JsonResponse(data = {'data':list(objs)})
        
        if R.get('action') == 'get_ppmtask_details' and R.get('taskid'):
            objs = JobneedDetails.objects.get_ppm_details(request)
            return rp.JsonResponse({"data":list(objs)})
        
        if R.get('action', None) == "delete" and R.get('id', None):
            return utils.render_form_for_delete(request, P, True)

        # return form with instance
        elif R.get('action') == "getppm_jobneedform" and  R.get('id', None):
            obj = Jobneed.objects.get(id = R['id'])
            cxt = {'ppmjobneedform': P['form'](instance = obj, request=request),
                   'msg': "PPM Jobneed Update Requested"}
            return render(request, P['template_form'], context = cxt)
        
    
    def post(self, request, *args, **kwargs):
        resp, create = None, True
        data = QueryDict(request.POST['formData'])
        try:
            if pk := request.POST.get('pk', None):
                msg, create = "ppm view", False
                people = utils.get_model_obj(pk, request,  self.P)
                form = self.P['form'](data, request=request, instance = people)
            else:
                form = self.P['form'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    @staticmethod
    def handle_valid_form(form, request ,create):
        logger.info('ppm form is valid')
        from apps.core.utils import handle_intergrity_error
        
        try:
            ppm = form.save()
            ppm = putils.save_userinfo(
                ppm, request.user, request.session, create = create)
            logger.info("ppm form saved")
            data = {'pk':ppm.id}
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return handle_intergrity_error('PPM')

def testCalendar(request):
    R = request.GET
    start, end = R.get('start'), R.get('end')
    if start and end:
        start = datetime.strptime(start, '%Y-%m-%dT%H:%M:%S%z')
        end = datetime.strptime(end,  "%Y-%m-%dT%H:%M:%S%z")
        return rp.JsonResponse([], status=200, safe=False)
    return render(request, 'activity/testCalendar.html', {})



class CalendarView(View):
    
    def get(self, request):
        R = request.GET
        start, end = R.get('start'), R.get('end')
        if R.get('action') == 'ED':#Event Detail
            if R.get('eventType') in ['Tasks', 'Tours', 'PPM', 'Route Plan']:
                eventdetails = Jobneed.objects.get_event_details(request)
                return rp.JsonResponse(eventdetails, safe=False)
        elif start and end:
            if R.get('eventType') in ['Tasks', 'Tours', 'PPM', 'Route Plan']:
                events  = Jobneed.objects.get_events_for_calendar(request)
                return rp.JsonResponse(list(events), safe=False)
            
            if R.get('eventType') in ('Work Permits', 'Work Orders'):   
                from apps.work_order_management.models import Wom
                events  = Wom.objects.get_events_for_calendar(request)
                return rp.JsonResponse(list(events), safe=False)
            
            if R.get('eventType') in ['Tickets']:
                from apps.y_helpdesk.models import Ticket
                events = Ticket.objects.get_events_for_calendar(request)
                return rp.JsonResponse(list(events), safe=False)
        return render(request, 'activity/testCalendar.html')
        
    

class AdhocTasks(LoginRequiredMixin, View):
    params = {
        'form_class'   : AdhocTaskForm,
        'template_form': 'activity/adhoc_jobneed_taskform.html',
        'template_list': 'activity/adhoc_jobneed_task.html',
        'related'      : ['performedby', 'qset', 'asset'],
        'model'        : Jobneed,
        'fields'       : ['id', 'plandatetime', 'jobdesc', 'performedby__peoplename', 'jobstatus',
                   'qset__qsetname', 'asset__assetname', 'ctzoffset'],
        'form_initials': {},
        'idf'          : ''}

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None
        from datetime import datetime
        now = datetime.now()

        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            total, filtered, objs = self.params['model'].objects.get_adhoctasks_listview(R, self.params['idf'])
            return  rp.JsonResponse(data = {
                'draw':R['draw'],
                'data':list(objs),
                'recordsFiltered':filtered,
                'recordsTotal':total,
            }, safe = False)

        if R.get('action', None) == 'form':
            cxt = {'adhoctaskform': self.params['form_class'](request = request),
                   'msg': "create adhoc task requested"}
            return render(request, self.params['template_form'], context = cxt)


class AdhocTours(LoginRequiredMixin, View):
    params = {
        'template_list':'activity/adhoc_jobneed_tours.html',
        'model':Jobneed,
        'fields':['id', 'plandatetime', 'jobdesc', 'performedby__peoplename', 'jobstatus',
                  'ctzoffset', 'qset__qsetname', 'asset__assetname'],
        'related':['performedby', 'qset', 'asset'],
    }
    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None
        from datetime import datetime
        now = datetime.now()
        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            total, filtered, objs = self.params['model'].objects.get_adhoctour_listview(R)
            return  rp.JsonResponse(data = {
                'draw':R['draw'],
                'data':list(objs),
                'recordsFiltered':filtered,
                'recordsTotal':total,
            }, safe = False)
    
