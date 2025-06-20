from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.utils import IntegrityError
from django.db import transaction
from django.http import response as rp
from django.http.request import QueryDict
from django.shortcuts import render
from django.views import View
import apps.attendance.forms as atf
import apps.attendance.models as atdm
import apps.onboarding.models as ob
from apps.activity import models as am
from .filters import AttendanceFilter
import apps.peoples.utils as putils
from apps.service.utils import save_linestring_and_update_pelrecord

import logging
from apps.core import utils
logger = logging.getLogger('django')
# Create your views here.

class Attendance(LoginRequiredMixin, View):
    params = {
        'form_class': atf.AttendanceForm,
        'template_form': 'attendance/partials/partial_attendance_form.html',
        'template_list': 'attendance/attendance.html',
        'template_list_sos': 'attendance/sos_list.html',
        'template_list_site_diversions': 'attendance/site_diversions.html',
        'template_list_sitecrisis': 'attendance/sitecrisis_list.html',
        'partial_form': 'attendance/partials/partial_attendance_form.html',
        'partial_list': 'attendance/partials/partial_attendance_list.html',
        'related': ['people', 'bu', 'verifiedby', 'peventtype', 'shift'],
        'model': atdm.PeopleEventlog,
        'filter': AttendanceFilter,
        'form_initials':{},
        'fields': ['id', 'people__peoplename', 'people__peoplecode', 'verifiedby__peoplename', 'peventtype__taname','peventtype__tacode', 'bu__buname', 'datefor','uuid', 'people__id',
                   'punchintime', 'punchouttime', 'facerecognitionin', 'facerecognitionout','shift__shiftname', 'ctzoffset', 'peventlogextras', 'sL', 'eL', 'people__location__locname',
                   'people__mobno', 'bu__siteincharge__peoplename', 'bu__siteincharge__mobno', 'bu__siteincharge__email','shift__starttime', 'shift__endtime']}

    def get(self, request, *args, **kwargs):
        R, P, resp = request.GET, self.params, None

        if R.get('template') == 'sos_template': return render(request, P['template_list_sos'])
        if R.get('template') == 'site_diversions': return render(request, P['template_list_site_diversions'])
        if R.get('template') == 'sitecrisis': return render(request, P['template_list_sitecrisis'])
        
        if R.get('template'): return render(request, self.params['template_list'])
        # return attendance_list data
        
        if R.get('action') == 'sos_list_view':
            objs = self.params['model'].objects.get_sos_listview(request)
            return rp.JsonResponse({'data':list(objs)}, status=200)
        
        if R.get('action') == 'get_site_diversion_list':
            objs = self.params['model'].objects.get_diversion_countorlist(request)
            return rp.JsonResponse({'data':list(objs)}, status=200)
        
        if R.get('action') == 'get_sitecrisis_list':
            objs = self.params['model'].objects.get_sitecrisis_countorlist(request)
            return rp.JsonResponse({'data':list(objs)}, status=200)
        
        if R.get('action', None) == 'list' or R.get('search_term'):
            d = {'list': "attd_list", 'filt_name': "attd_filter"}
            self.params.update(d)
            objs = self.params['model'].objects.get_peopleevents_listview(P['related'], P['fields'], request)
            return rp.JsonResponse({'data':list(objs)}, status=200)

        if request.GET.get("action") == "getLocationStatus":
            people_id = request.GET.get("peopleid")
            # client_code = request.GET.get("clientcode")

            # Query geofence_id
            get_geofence_id = am.Job.objects.filter(
                people_id=people_id, identifier='GEOFENCE'
            ).values('geofence_id')
            
            # Check if geofence_id exists
            if not get_geofence_id.exists():
                return rp.JsonResponse({"error": "No geofence_id found for this people_id"}, status=404)
            
            geofence_id = get_geofence_id[0]['geofence_id']

            # Query geofence
            get_geofence = ob.GeofenceMaster.objects.filter(id=geofence_id, enable=True).exclude(id=1).values('geofence')
            
            # Check if geofence exists
            if not get_geofence.exists():
                return rp.JsonResponse({"error": "Geofence not found or disabled"}, status=404)
            
            try:
                from shapely.wkt import loads
                # Clean WKT and process polygon
                geofence_wkt_cleaned = str(get_geofence[0]['geofence']).split(";")[1]
                polygon = loads(geofence_wkt_cleaned)
                coordinates_list = list(polygon.exterior.coords)
                
                # Return coordinates
                return rp.JsonResponse({"geofence_coords": coordinates_list}, status=200)

            except Exception as e:
                return rp.JsonResponse({"error": str(e)}, status=500)


        # return attemdance_form empty
        if R.get('action', None) == 'form': 
            cxt = {'attd_form': self.params['form_class'](),
                   'msg': "create attendance requested"}
            resp = utils.render_form(request, self.params, cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params)
        
        # return form with instance
        elif R.get('id', None):
            obj = utils.get_model_obj(R['id'], request, self.params)
            resp = utils.render_form_for_update(
                request, self.params, "attd_form", obj)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            data = QueryDict(request.POST['formData'])
            if pk := request.POST.get('pk', None):
                msg = "attendance_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk))
                create = False
            else:
                form = self.params['form_class'](data)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    @staticmethod
    def handle_valid_form(form, request, create):
        logger.info('attendance form is valid')
        try:
            attd = form.save()
            putils.save_userinfo(attd, request.user, request.session, create)
            logger.info("attendance form saved")
            data = {'success': "Record has been saved successfully",
                    'type': attd.peventtype.tacode}
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return putils.handle_intergrity_error('Attendance')



class Conveyance(LoginRequiredMixin, View):
    model = atdm.PeopleEventlog,
    params = {
        'fields': [
            'punchintime', 'punchouttime', 'bu__buname', 'ctzoffset',
            'bu__bucode', 'people__peoplename', 'people__peoplecode',
            'transportmodes', 'distance', 'duration', 'expamt', 'id', 
            'start', 'end'],
        'template_list': 'attendance/travel_expense.html',
        'template_form': 'attendance/travel_expense_form.html',
        'related'      : ['bu', 'people'],
        'model'        : atdm.PeopleEventlog,
       'form_class':atf.ConveyanceForm}

    def get(self, request, *args, **kwargs):
        R, resp, objects, filtered = request.GET, None, [], 0

        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = self.params['model'].objects.get_lastmonth_conveyance(
                request, self.params['fields'], self.params['related'] )
            resp = rp.JsonResponse(data = {'data':list(objs)})

        # return cap_form empty for creation
        elif R.get('action', None) == 'form':
            cxt = {'conveyanceform': self.params['form_class'](),
                   'msg': "create conveyance requested"}
            resp  = render(request, self.params['template_form'], context = cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params, False)

        # return form with instance for update
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            save_linestring_and_update_pelrecord(obj)
            cxt = {'conveyanceform':self.params['form_class'](request = request, instance = obj),
                    'edit':True}
            resp = render(request, self.params['template_form'], context = cxt)

        # return journey path of instance
        elif R.get('action') == 'getpath':
            data = atdm.PeopleEventlog.objects.getjourneycoords(R['conid'])
            resp = rp.JsonResponse(data = {'obj':list(data)}, status = 200)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            # convert queryparams to python datatypes
            data = QueryDict(request.POST['formData'])
            if pk := data.get('pk', None):
                msg = 'conveyance_view'
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk))
                create = False
            else:
                form = self.params['form_class'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    @staticmethod
    def handle_valid_form(form, request, create):
        logger.info('conveyance form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                cy = form.save()
                putils.save_userinfo(cy, request.user, request.session, create = create)
                logger.info("conveyance form saved")
                return rp.JsonResponse(data={'pk':cy.id}, status = 200)
        except IntegrityError:
            return handle_intergrity_error("conveyance")
    
   


class GeofenceTracking(LoginRequiredMixin, View):
    params = {
        'template_list':'attendance/geofencetracking.html',
        'model':atdm.PeopleEventlog,
        'related':['geofence', 'peventtype', 'people'],
        'fields':['datefor', 'geofence__gfname', 'startlocation', 'endlocation',
                  'people__peoplename']
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])
        
        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            total, filtered, objs = self.params['model'].objects.get_geofencetracking(request)
            return  rp.JsonResponse(data = {
                'draw':R['draw'],
                'data':list(objs),
                'recordsFiltered':filtered,
                'recordsTotal':total,
            }, safe = False)
            
