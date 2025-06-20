import logging
from typing import Type
import os
from django.http import response as rp
from django.shortcuts import  render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.db.models import Q
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.db.utils import IntegrityError
from django.conf import settings
from django.db import transaction
from django.http.request import QueryDict
from .models import Shift,  TypeAssist, Bt, GeofenceMaster, Device, Subscription
from apps.peoples.utils import save_userinfo
from apps.core import utils
from apps.activity.models.asset_model import Asset
from apps.activity.models.job_model import Job,Jobneed
from apps.peoples.models import Pgbelonging
from apps.attendance.models import PeopleEventlog
import apps.onboarding.forms as obforms
import apps.peoples.utils as putils
import apps.onboarding.utils as obutils
from apps.peoples import admin as people_admin
from apps.onboarding import admin as ob_admin
from apps.activity.admin.asset_admin import AssetResource,AssetResourceUpdate
from apps.activity.admin.location_admin import LocationResource,LocationResourceUpdate
from apps.activity.admin.question_admin import QuestionResource,QuestionResourceUpdate,QuestionSetResource,QuestionSetResourceUpdate,QuestionSetBelongingResource,QuestionSetBelongingResourceUpdate
from apps.schedhuler import admin as sc_admin
from django.db import IntegrityError
from apps.y_helpdesk.models import Ticket
from apps.work_order_management.models import Wom
from apps.work_order_management.admin import VendorResource, VendorResourceUpdate
from django.core.exceptions import ObjectDoesNotExist
from pprint import pformat
import uuid
import json
from tablib import Dataset
from django.apps import apps
from apps.onboarding.utils import is_bulk_image_data_correct,save_image_and_image_path,extract_file_id,get_file_metadata, polygon_to_address

CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)

logger = logging.getLogger("django")
log = logger
from apps.core.exceptions import IntegrityConstraintError

def get_caps(request):  # sourcery skip: extract-method
    logger.info('get_caps requested')
    selected_parents = request.GET.getlist('webparents[]')
    logger.info(f'selected_parents {selected_parents}')
    cfor = request.GET.get('cfor')
    logger.info(f'cfor {cfor}')
    if selected_parents:
        from apps.peoples.models import Capability
        import json
        childs = []
        for i in selected_parents:
            child = Capability.objects.get_child_data(i, cfor)
            childs.extend({'capscode': j.capscode} for j in child)
        logger.info(f'childs = [] {childs}')
        return rp.JsonResponse(data=childs, safe=False)


def handle_pop_forms(request):
    if request.method != 'POST':
        return
    form_name = request.POST.get('form_name')
    form_dict = {
        'ta_form': obforms.TypeAssistForm,
    }
    form = form_dict[form_name](request.POST, request=request)
    if not form.is_valid():
        return rp.JsonResponse({'saved': False, 'errors': form.errors})
    ta = form.save(commit=False)
    ta.enable = True
    form.save(commit=True)
    save_userinfo(ta, request.user, request.session)
    if request.session.get('wizard_data'):
        request.session['wizard_data']['taids'].append(ta.id)
    return rp.JsonResponse({'saved': True, 'id': ta.id, 'tacode': ta.tacode})

# -------------------- END Client View Classes ------------------------------#

# ---------------------------- END client onboarding   ---------------------------#


class SuperTypeAssist(LoginRequiredMixin, View):
    params = {
        'form_class': obforms.SuperTypeAssistForm,
        'template_form': 'onboarding/partials/partial_ta_form.html',
        'template_list': 'onboarding/supertypeassist.html',
        'partial_form': 'onboarding/partials/partial_ta_form.html',
        'related': ['parent',  'cuser', 'muser'],
        'model': TypeAssist,
        'fields': ['id', 'tacode', 'client__bucode', 'bu__bucode',
                   'taname', 'tatype__tacode', 'cuser__peoplecode'],
        'form_initials': {}}

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None
        # first load the template
        if R.get('template'):
            return render(request, self.params['template_list'])
        # then load the table with objects for table_view
        if R.get('action') == 'list':
            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                ~Q(tacode='NONE'), enable=True
            ).values(*self.params['fields'])
            return rp.JsonResponse(data={'data': list(objs)})

        if R.get('action', None) == 'form':
            cxt = {'ta_form': self.params['form_class'](request=request),
                   'msg': "create supertypeassist requested"}
            resp = utils.render_form(request, self.params, cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params, True)

        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            resp = utils.render_form_for_update(
                request, self.params, "ta_form", obj)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        R = request.POST
        try:
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            if pk:
                msg = "supertypeassist_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), {'request': request})
                create = False
            else:
                form = self.params['form_class'](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        logger.info('supertypeassist form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            ta = form.save()
            putils.save_userinfo(
                ta, request.user, request.session, create=create)
            logger.info("supertypeassist form saved")
            data = {'msg': f"{ta.tacode}",
                    'row': TypeAssist.objects.values(*self.params['fields']).get(id=ta.id)}
            return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return handle_intergrity_error("SuperTypeAssist")


class TypeAssistView(LoginRequiredMixin, View):
    params = {
        'form_class': obforms.TypeAssistForm,
        'template_form': 'onboarding/partials/partial_ta_form.html',
        'template_list': 'onboarding/typeassist.html',
        'partial_form': 'onboarding/partials/partial_ta_form.html',
        'related': ['parent','tatype', 'cuser', 'muser'],
        'model': TypeAssist,
        'fields': ['id', 'tacode', 'cdtz',
                   'taname', 'tatype__tacode', 'cuser__peoplecode'],
        'form_initials': {}}

    def get(self, request, *args, **kwargs):
        R, S, resp = request.GET, request.session, None
        # first load the template
        if R.get('template'):
            return render(request, self.params['template_list'])
        # then load the table with objects for table_view
        if R.get('action') == 'list':
            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                    ~Q(tacode='NONE'), ~Q(tatype__tacode='NONE'), Q(client_id=S['client_id']) | Q(cuser_id=1), enable=True,
            ).values(*self.params['fields'])
            return rp.JsonResponse(data={'data': list(objs)})

        if R.get('action', None) == 'form':
            cxt = {'ta_form': self.params['form_class'](request=request),
                   'msg': "create typeassist requested"}
            resp = utils.render_form(request, self.params, cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params, True)

        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            resp = utils.render_form_for_update(
                request, self.params, "ta_form", obj)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        R = request.POST
        try:
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            if pk:
                msg = "typeassist_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), {'request': request})
                create = False
            else:
                form = self.params['form_class'](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        logger.info('typeassist form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            ta = form.save()
            putils.save_userinfo(
                ta, request.user, request.session, create=create)
            logger.info("typeassist form saved")
            data = {'msg': f"{ta.tacode}",
                    'row': TypeAssist.objects.values(*self.params['fields']).get(id=ta.id)}
            return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return handle_intergrity_error("TypeAssist")


class ShiftView(LoginRequiredMixin, View):
    params = {
        'form_class': obforms.ShiftForm,
        'template_form': 'onboarding/partials/partial_shiftform.html',
        'shift_form':'onboarding/shift_form.html',
        'template_list': 'onboarding/shift.html',
        'related': ['parent',  'cuser', 'muser', 'bu'],
        'model': Shift,
        'fields': ['id', 'shiftname', 'starttime', 'endtime', 'nightshiftappicable',
                   'bu__bucode', 'bu__buname','designation','peoplecount'],
        'form_initials': {}}

    def get(self, request, *args, **kwargs):
        R, resp, P = request.GET, None, self.params
        # first load the template

        if R.get('template'):
            return render(request, self.params['template_list'])
        
        # then load the table with objects for table_view
        if R.get('action', None) == 'list':
            objs = self.params['model'].objects.shift_listview(request, P['related'], P['fields'])
            resp = rp.JsonResponse(data={'data': list(objs)}, status=200, safe=False)

        elif R.get('action', None) == 'form':
            designation_choices = obutils.get_designation_choices(request,P)
            #contact_details
            total_ppl_count_on_site,count_as_per_design = Bt.objects.get_sitecontract_details(request)
            #current_shift_details
            total_shifts_ppl_count,designation_wise_count,current_shift_ppl_count,current_shift_design_counts = self.params['model'].objects.get_shiftcontract_details(request, R.get('id', 0))
            design_choices_contract = obutils.get_designation_choices_asper_contract(designation_choices,count_as_per_design)
            # designation_choices = obutils.get_designation_choices(request,P)
            cxt = {'shift_form': self.params['form_class'](request=request),
                   'msg': "create shift requested", 
                   'total_ppl_count_on_site':total_ppl_count_on_site,#contract_details,
                   'count_as_per_design':count_as_per_design,#contract_details,
                   'designation_choices': design_choices_contract,
                   'total_shifts_ppl_count':total_shifts_ppl_count,
                   'designation_wise_count':designation_wise_count,
                   'current_shift_ppl_count': current_shift_ppl_count,
                   'current_shift_designation_counts': current_shift_design_counts}
            resp = render(request, P['shift_form'], cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params, True)

        elif R.get('action') == "get_shift_data" and R.get('shift_id'):
            if R.get('shift_id') != 'None':   
                obj = utils.get_model_obj(int(R['shift_id']), request, self.params)
                raw_data = obutils.get_shift_data(obj)
                designation_codes = list(raw_data.keys())
                designation_names = TypeAssist.objects.filter(tacode__in=designation_codes).values('tacode', 'taname')
                designation_lookup = {item['tacode']: item['taname'] for item in designation_names}
                data = [{'designation': designation_lookup.get(designation, 'Unknown'), 'code' : designation, **details }for designation, details in raw_data.items()]
            else:
                data = [{'designation': 'Unknown', 'count':'', 'overtime': 0, 'gracetime': 0}]
            return rp.JsonResponse({'data':data}, status=200, safe=False)
            
        elif R.get('id', None):
            designation_choices = obutils.get_designation_choices(request,P)
            total_ppl_count_on_site,count_as_per_design = Bt.objects.get_sitecontract_details(request)
            total_shifts_ppl_count,designation_wise_count,current_shift_ppl_count,current_shift_designation_counts = self.params['model'].objects.get_shiftcontract_details(request,R.get('id'))
            design_choices_contract = obutils.get_designation_choices_asper_contract(designation_choices,count_as_per_design)
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            cxt = {'shift_form':P['form_class'](instance=obj, request=request),
                   'msg': "update shift requested",
                   'designation_choices': design_choices_contract,
                   'total_ppl_count_on_site':total_ppl_count_on_site,
                   'count_as_per_design':count_as_per_design,
                   'total_shifts_ppl_count':total_shifts_ppl_count,
                   'designation_wise_count':designation_wise_count,
                   'current_shift_ppl_count':current_shift_ppl_count,
                   'current_shift_designation_counts':current_shift_designation_counts}
            resp = render(request, P['shift_form'], context = cxt)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:    
            if request.POST.get('actiond') == 'edit_shift_data':
                return obutils.handle_shift_data_edit(request,self)
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            if pk:
                msg = "shift_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), {'request': request})
                create = False
            else:
                form = self.params['form_class'](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            logger.error("SHIFT saving error!", exc_info=True)
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        logger.info('shift form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            shift = form.save()

            shift.bu_id = int(request.session['client_id'])
            putils.save_userinfo(shift, request.user,
                                 request.session, create=create)
            logger.info("shift form saved")
            data = {'msg': f"{shift.shiftname}",
                    'row': Shift.objects.values(*self.params['fields']).get(id=shift.id)}
            return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return handle_intergrity_error("Shift")


class EditorTa(LoginRequiredMixin, View):
    template = 'onboarding/testEditorTa.html'
    fields = ['id', 'tacode', 'taname', 'tatype__tacode', 'cuser__peoplecode']
    model = TypeAssist
    related = ['cuser', 'tatype']

    def get(self, request, *args, **kwargs):
        R = request.GET
        if R.get('template'):
            return render(request, self.template)

    def post(self, request, *args, **kwargs):
        R = request.POST
        objs = self.model.objects.select_related(
            *self.related).filter(
        ).values(*self.fields)
        count = objs.count()
        logger.info(
            f'Shift objects {count or "No Records!"} retrieved from db')
        if count:
            objects, filtered = utils.get_paginated_results(
                R, objs, count, self.fields, self.related, self.model)
            logger.info('Results paginated'if count else "")
        return rp.JsonResponse(
            data={
                'draw': R['draw'], 'recordsTotal': count,
                'data': list(objects),
                'recordsFiltered': filtered}, status=200
        )


class GeoFence(LoginRequiredMixin, View):
    params = {
        'form_class': obforms.GeoFenceForm,
        'template_list': 'onboarding/geofence_list.html',
        'template_form': 'onboarding/geofence_form.html',
        'fields': ['id', 'gfcode', 'geofence','gfname', 
                   'alerttogroup__groupname', 'alerttopeople__peoplename'],
        'related': ['alerttogroup', 'alerttopeople'],
        'model': GeofenceMaster
    }

    def get(self, request, *args, **kwargs):
        R = request.GET
        params = self.params
        # first load the template
        if R.get('template'):
            return render(request, self.params['template_list'])

        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = self.params['model'].objects.get_geofence_list(
                params['fields'], params['related'], request.session)
            # Convert QuerySet to list and process each object
            data_list = list(objs)
            for item in data_list:
                if 'geofence' in item and item['geofence']:
                    item['geofence_address'] = polygon_to_address(item['geofence'])
                    del item['geofence']
            return rp.JsonResponse(data={'data': data_list})

        if request.GET.get('perform') == 'editAssignedpeople':
            resp = Job.objects.handle_geofencepostdata(request)
            return rp.JsonResponse(resp, status=200)

        if R.get('action') == 'loadPeoples':
            objs = self.params['model'].objects.getPeoplesGeofence(request)
            return rp.JsonResponse(data={'items': list(objs)})

        if R.get('action') == "getAssignedPeople" and R.get('id'):
            objs = Job.objects.get_people_assigned_to_geofence(R['id'])
            return rp.JsonResponse(data={'data': list(objs)})

        if R.get('action', None) == 'form':
            NONE_P = utils.get_or_create_none_people()
            NONE_G = utils.get_or_create_none_pgroup()
            cxt = {'geofenceform': self.params['form_class'](
                initial={'alerttopeople': NONE_P, 'alerttogroup': NONE_G}, request=request)}
            return render(request, self.params['template_form'], context=cxt)

        if R.get('action') == 'drawgeofence':
            return get_geofence_from_point_radii(R)

        if R.get('id') not in [None, 'None']:
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            cxt = {'geofenceform': self.params['form_class'](request=request, instance=obj),
                   'edit': True,
                   'geofencejson': GeofenceMaster.objects.get_geofence_json(pk=obj.id)}
            return render(request, self.params['template_form'], context=cxt)

    def post(self, request, *args, **kwargs):
        resp = None
        try:
            data = QueryDict(request.POST.get('formData'))
            geofence = request.POST.get('geofence')
            if data['pk']:
                msg = "geofence_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(data['pk']), kwargs={'request': request})
            else:
                form = self.params['form_class'](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, geofence)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            logger.error('GEOFENCE saving error!', exc_info=True)
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, geofence):
        logger.info('geofence form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            with transaction.atomic(using=utils.get_current_db_name()):
                gf = form.save()
                self.save_geofence_field(gf, geofence)
                gf = putils.save_userinfo(gf, request.user, request.session)
                logger.info("geofence form saved")
                return rp.JsonResponse(data={'pk': gf.id}, status=200)
        except IntegrityError:
            return handle_intergrity_error("GeoFence")

    @staticmethod
    def save_geofence_field(gf, geofence):
        try:
            from django.contrib.gis.geos import LinearRing, Polygon
            import json
            geofencedata = json.loads(geofence)
            coords = [(i['lng'], i['lat']) for i in geofencedata]
            pg = Polygon(LinearRing(coords, srid=4326), srid=4326)
            gf.geofence = pg
            gf.save()
        except Exception:
            logger.critical('geofence polygon field saving error', exc_info=True)
            raise


def get_geofence_from_point_radii(R):
    try:
        lat, lng, radii = R.get('lat'), R.get('lng'), R.get('radii')
        if all([lat, lng, radii]):
            from django.contrib.gis import geos
            point = geos.Point(float(lng), float(lat), srid=4326)
            point.transform(3857)
            geofence = point.buffer(int(radii))
            geofence.transform(4326)
            return rp.JsonResponse(data={'geojson': utils.getformatedjson(geofence)}, status=200)
        return rp.JsonResponse(data={'errors': "Invalid data provided unable to compute geofence!"}, status=404)
    except Exception:
        logger.critical(
            "something went wrong while computing geofence..", exc_info=True)
        return rp.JsonResponse(data={'errors': 'something went wrong while computing geofence!'}, status=404)


class FileRemovalResponse(rp.FileResponse):
    def close(self):
        super().close()
        os.remove(self.filename)


# Mapping Constants
MODEL_RESOURCE_MAP = {
    # 'MODELNAME'         : 'RESOURCE(ADMIN CLASS for the model which is used to validate and give error messages for importing data )'
    'TYPEASSIST'          : ob_admin.TaResource,
    'BU'                  : ob_admin.BtResource,
    'QUESTION'            : QuestionResource,
    'LOCATION'            : LocationResource,
    'PEOPLE'              : people_admin.PeopleResource,
    'GROUP'               : people_admin.GroupResource,
    'GROUPBELONGING'      : people_admin.GroupBelongingResource,
    'ASSET'               : AssetResource,
    'VENDOR'              : VendorResource,
    'QUESTIONSET'         : QuestionSetResource,
    'QUESTIONSETBELONGING': QuestionSetBelongingResource,
    'SCHEDULEDTASKS'      : sc_admin.TaskResource,
    'SCHEDULEDTOURS'      : sc_admin.TourResource,
    'GEOFENCE'            : ob_admin.GeofenceResource,
    'GEOFENCE_PEOPLE'     : ob_admin.GeofencePeopleResource,
    'SHIFT'               : ob_admin.ShiftResource,
}

MODEL_RESOURCE_MAP_UPDATE = {
    # 'MODELNAME'         : 'RESOURCE(ADMIN CLASS for the model which is used to validate and give error messages for importing data )'
    'TYPEASSIST'          : ob_admin.TaResourceUpdate,
    'BU'                  : ob_admin.BtResourceUpdate,
    'QUESTION'            : QuestionResourceUpdate,
    'LOCATION'            : LocationResourceUpdate,
    'PEOPLE'              : people_admin.PeopleResourceUpdate,
    'GROUP'               : people_admin.GroupResourceUpdate,
    'GROUPBELONGING'      : people_admin.GroupBelongingResourceUpdate,
    'ASSET'               : AssetResourceUpdate,
    'VENDOR'              : VendorResourceUpdate,
    'QUESTIONSET'         : QuestionSetResourceUpdate,
    'QUESTIONSETBELONGING': QuestionSetBelongingResourceUpdate,
    'SCHEDULEDTASKS'      : sc_admin.TaskResourceUpdate,
    'SCHEDULEDTOURS'      : sc_admin.TourResourceUpdate,
}

class ParameterMixin:
    mode_resource_map = MODEL_RESOURCE_MAP
    mode_resource_map_update = MODEL_RESOURCE_MAP_UPDATE
    form = obforms.ImportForm
    form_update = obforms.ImportFormUpdate
    template = 'onboarding/import.html'
    template_import_update = 'onboarding/import_update.html'
    #header_mapping = HEADER_MAPPING
    
class BulkImportData(LoginRequiredMixin,ParameterMixin, View):
    def get(self, request, *args, **kwargs):
        R = request.GET
        
        if (R.get('action') == 'form'):
            #removes the temp file created in the last import
            self.remove_temp_file(request)
            inst = utils.Instructions(tablename='TYPEASSIST')
            '''
            Getting the instructions from the instance and here json.dumps 
            is used to convert the python dictionary to json.
            '''
            instructions = json.dumps(inst.get_insructions())
            cxt = {'importform': self.form(initial={'table': "TYPEASSIST"}), 'instructions':instructions}
            return render(request, self.template, cxt)
        
        if R.get('action') == 'getInstructions':
            inst = utils.Instructions(tablename=R.get('tablename'))
            instructions = inst.get_insructions()
            return rp.JsonResponse({'instructions':instructions}, status=200)

        if  (request.GET.get('action') == 'downloadTemplate') and request.GET.get('template'):
            buffer = utils.excel_file_creation(R)
            return rp.FileResponse(
                buffer, as_attachment=True, filename=f'{R["template"]}.xlsx'
            )

    def post(self, request, *args, **kwargs):
        R = request.POST
        form = self.form(R, request.FILES)
        if R['table'] == 'BULKIMPORTIMAGE':
            if 'action' in R and R['action'] == 'confirmImport':
                try:
                    total_images, results = save_image_and_image_path(
                        R['google_drive_link'],
                        settings.MEDIA_ROOT
                    )
                    return rp.JsonResponse({
                        'totalrows': total_images,
                        'results': results
                    }, status=200)
                except Exception as e:
                    logger.error(f"Error in bulk import: {str(e)}")
                    return rp.JsonResponse({
                        'error': str(e)
                    }, status=500)
            else:
                # Rest of your existing code for validation
                boolean_var, image_data = self.upload_bulk_image_format(R)
                context = {
                    'boolean_var': boolean_var,
                    'image_data': image_data,
                    'google_drive_link': R['google_drive_link']
                }
                return render(request, 'onboarding/import_image_data.html', context=context)
        else:
            if not form.is_valid() and R['action'] != 'confirmImport':
                return rp.JsonResponse({'errors': form.errors}, status=404)
            res, dataset = obutils.get_resource_and_dataset(request, form,self.mode_resource_map)
            if R.get('action') == 'confirmImport':
                results = res.import_data(dataset = dataset, dry_run = False, raise_errors = False)
                return rp.JsonResponse({'totalrows':results.total_rows}, status = 200)
            else:
                try:
                    results = res.import_data(
                        dataset=dataset, dry_run=True, raise_errors=False, use_transactions=True)
                    return render(request, 'onboarding/imported_data.html', {'result':results})
                except Exception as e:
                    logger.critical("error", exc_info=True)
                    return rp.JsonResponse({"error": "something went wrong!"}, status=500)
        
    def upload_bulk_image_format(self,R):
        google_drive_link = R['google_drive_link']
        file_id = extract_file_id(google_drive_link)
        images_bulk_data = get_file_metadata(file_id)
        is_coorect, correct_image_data, incorrect_image_data = is_bulk_image_data_correct(images_bulk_data['files'])
        if not is_coorect:
            return False,incorrect_image_data
        return True,correct_image_data
        

    def get_resource_and_dataset(self, request, form):
        table = form.cleaned_data.get('table')
        if request.POST.get('action') == 'confirmImport':
            tempfile = request.session['temp_file_name']
            with open(tempfile, 'rb') as file:
                dataset = Dataset().load(file)
        else:
            file = request.FILES['importfile']
            dataset = Dataset().load(file)
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as tf:
                for chunk in file.chunks():
                    tf.write(chunk)
                request.session['temp_file_name'] = tf.name
        res = self.mode_resource_map[table](request=request, ctzoffset = form.cleaned_data.get('ctzoffset'))
        return res, dataset

    def get_readable_error(self, error):
        if(isinstance(error, ObjectDoesNotExist)):
            return "Related values does not exist, please check your data."
        if(isinstance(error, IntegrityError)):
            return "Record already exist, please check your data."
        return str(error)
    
    def remove_temp_file(self, request):
        filename = request.session.get('temp_file_name', '')
        try:
            os.remove(filename)
        except FileNotFoundError:
            log.info(f"The file {filename} does not exist.")
        except Exception as e:
            log.info(f"An error occurred while trying to remove the file {filename}: {str(e)}")


class Client(LoginRequiredMixin, View):
    params = {
        'form_class': obforms.BtForm,
        'json_form': obforms.ClentForm,
        'template_form': 'onboarding/client_buform.html',
        'template_list': 'onboarding/client_bulist.html',
        'model': Bt,
        'fields': ['id', 'bucode', 'buname', 'enable'],
        'related': [],
    }

    def get(self, request, *args, **kwargs):
        from .utils import get_bt_prefform
        R, P = request.GET, self.params

        # first load the template
        if R.get('template'):
            return render(request, P['template_list'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = P['model'].objects.get_client_list(
                P['fields'], P['related'])
            return rp.JsonResponse(data={'data': list(objs)})

        if R.get('action', None) == 'form':
            cxt = {'clientform': P['form_class'](client=True, request=request),
                   'clientprefsform': P['json_form'](),
                   'ta_form': obforms.TypeAssistForm(auto_id=False, request=request),
                   'ownerid': uuid.uuid4()
                   }
            return render(request, P['template_form'], context=cxt)

        if R.get('action') == 'loadIdentifiers':
            qset = TypeAssist.objects.load_identifiers(request)
            return rp.JsonResponse({'items': list(qset), 'total_count': len(qset)}, status=200)
        
        if R.get('action') == 'getCurrentlyActiveHandsets' and R.get('client_id') != 'None':
            qset = Device.objects.get_currently_active_handsets(R['client_id'])
            return rp.JsonResponse({'data': list(qset)}, status=200)

        if R.get('action') == 'loadParents':
            qset = Bt.objects.load_parent_choices(request)
            return rp.JsonResponse({'items': list(qset), 'total_count': len(qset)}, status=200)

        if R.get('action') == 'delete':
            return utils.render_form_for_delete(request, self.params, True)

        if R.get('action') == 'getlistbus':
            fields = ['id', 'bucode', 'buname', 'identifier__tacode', 'identifier_id',
                      'parent__buname', 'enable', 'parent_id']
            objs = P['model'].objects.get_allsites_of_client(
                request.GET.get('id'), fields=fields)
            return rp.JsonResponse(data={'data': list(objs)})

        if R.get('action') == 'getadmins':
            objs = P['model'].objects.get_listadmins(request)
            return rp.JsonResponse(data={'data': list(objs)})

        if R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            cxt = {'clientform': self.params['form_class'](request=request, instance=obj),
                   'edit': True, 'ta_form': obforms.TypeAssistForm(auto_id=False, request=request),
                   'clientprefsform': get_bt_prefform(obj), 'ownerid': obj.uuid}
            return render(request, self.params['template_form'], context=cxt)

    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.params
        if R.get('bupostdata'):
            resp = P['model'].objects.handle_bupostdata(request)
            return rp.JsonResponse(resp, status=200)

        if R.get('action') == 'saveDeviceLimits' and R.get('pk') !=None:
            data = QueryDict(request.POST['formData'])
            resp = P['model'].objects.handle_device_limits_post(data)
            return rp.JsonResponse(resp, status=200)
        
        if R.get('action') == 'saveUserLimits' and R.get('pk') !=None:
            data = QueryDict(request.POST['formData'])
            resp = P['model'].objects.handle_user_limits_post(data)
            return rp.JsonResponse(resp, status=200)
        
        if R.get('adminspostdata'):
            resp = P['model'].objects.handle_adminspostdata(request)
            return rp.JsonResponse(resp, status=200)
        data = QueryDict(request.POST['formData'])

        try:
            if pk := request.POST.get('pk', None):
                msg, create = "client_view", False
                client = utils.get_model_obj(pk, request,  P)
                form = P['form_class'](
                    data, request.FILES, instance=client, request=request)
            else:
                form = P['form_class'](data, request=request)
            jsonform = P['json_form'](data, session=request.session)
            if form.is_valid() and jsonform.is_valid():
                resp = self.handle_valid_form(form, jsonform, request)
            else:
                cxt = {'errors': form.errors}
                if jsonform.errors:
                    cxt.update({'errors': jsonform.errors})
                resp = utils.handle_invalid_form(request, P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    @staticmethod
    def handle_valid_form(form, jsonform, request):
        logger.info('client form is valid')
        from .utils import save_json_from_bu_prefsform
        try:
            with transaction.atomic(using=utils.get_current_db_name()):
                client = form.save()
                client.uuid = request.POST.get('uuid')
                logger.debug("Client : %s", client)
                logger.debug("Client.uuid: %s", client.uuid)
                if save_json_from_bu_prefsform(client, jsonform):
                    client = putils.save_userinfo(
                        client, request.user, request.session)
                    logger.info("people form saved")
                data = {'pk': client.id}
                return rp.JsonResponse(data, status=200)
        except Exception:
            return utils.handle_Exception(request)


class BtView(LoginRequiredMixin, View):
    params = {
        'form_class': obforms.BtForm,
        'template_form': 'onboarding/bu_form.html',
        'template_list': 'onboarding/bu_list.html',
        'related': ['parent', 'identifier', 'butype'],
        'model': Bt,
        'fields': ['id', 'bucode', 'buname', 'butree', 'identifier__taname',
                   'enable', 'parent__buname', 'butype__taname', 'solid'],
        'form_initials': {}}

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        # first load the template
        if R.get('template'):
            return render(request, self.params['template_list'])
        # then load the table with objects for table_view
        if R.get('action', None) == 'list':
            start = int(R.get('start', 0))
            length = int(R.get('length', 10))
            search = R.get('search[value]', '').strip()

            order_col = request.GET.get('order[0][column]')
            order_dir = request.GET.get('order[0][dir]')
            column_name = request.GET.get(f'columns[{order_col}][data]')

            buids = self.params['model'].objects.get_whole_tree(
                request.session['client_id'])
            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                    id__in=buids
            ).exclude(identifier__tacode='CLIENT').values(*self.params['fields']).order_by('buname')

            if search:
                objs = objs.filter(Q(buname__icontains=search) | Q(bucode__icontains=search))

            if column_name:
                order_prefix = '' if order_dir == 'asc' else '-'
                objs = objs.order_by(f'{order_prefix}{column_name}')

            total = objs.count()
            paginated = objs[start:start + length]

            return rp.JsonResponse({
                "draw": int(R.get('draw', 1)),
                "recordsTotal": total,
                "recordsFiltered": total,
                "data": list(paginated)
            })

        elif R.get('action', None) == 'form':

            cxt = {'buform': self.params['form_class'](request=request),
                   'ta_form': obforms.TypeAssistForm(auto_id=False, request=request),
                   'msg': "create bu requested"}
            return render(request, self.params['template_form'], context=cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params, True)

        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            # designation_data = obj.bupreferences.get('contract_designcount', {})
            initial = {'controlroom': obj.bupreferences.get('controlroom'),
                       'jsonData': json.dumps(obj.bupreferences.get('contract_designcount', {})),
                       'posted_people': obj.bupreferences.get('posted_people')}
            cxt = {'ta_form': obforms.TypeAssistForm(auto_id=False, request=request),
                   'buform': self.params['form_class'](request=request, instance=obj, initial=initial)}
        return render(request, self.params['template_form'], context=cxt)

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            if pk:
                msg = "bu_view"
                obj = utils.get_model_obj(pk, request, self.params)
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), kwargs={'request': request})
                create = False
            else:
                form = self.params['form_class'](data, request=request)

            if form.is_valid():
                designations_count = request.POST['jsonData']
                resp = self.handle_valid_form(form, request, create,designations_count,obj)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            logger.critical("BU saving error!", exc_info=True)
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create,designations_count,obj):
        logger.info('bu form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            bu = form.save(commit=False)
            if create == False:
                bu.bupreferences['posted_people'] = obj.bupreferences.get('posted_people',[])
                bu.bupreferences['contract_designcount'] = obj.bupreferences.get('contract_designcount',{})
                bu.bupreferences['total_people_count'] = obj.bupreferences.get('total_people_count',0)
            bu.gpslocation = form.cleaned_data['gpslocation']
            bu.bupreferences['permissibledistance'] = form.cleaned_data['permissibledistance']
            bu.bupreferences['controlroom'] = form.cleaned_data['controlroom']
            bu.bupreferences['address'] = form.cleaned_data['address']
            bu.bupreferences['address2'] = json.loads(
                "{}" if request.POST.get('address') == "" else request.POST['address'])
            putils.save_userinfo(
                bu, request.user, request.session, create=create)
            logger.info("bu form saved")
            return rp.JsonResponse({'pk': bu.id}, status=200)
        except IntegrityError:
            return handle_intergrity_error("Bu")


class DashboardView(LoginRequiredMixin, View):
    P = {
        "RP": "dashboard/RP_d/rp_dashboard.html",
        "pel_model": PeopleEventlog,
        "jn_model": Jobneed,
        "wp_model": Wom
    }
    
    def get(self, request, *args, **kwargs):
        P, R = self.P, request.GET
        try:
            if R.get('action') == 'getCounts':
                objs = self.get_all_dashboard_counts(request, P)
                return rp.JsonResponse(objs, status=200)
            return render(request, P['RP'])
        except Exception as e:
            logger.critical(
                "something went wrong DashboardView view", exc_info=True)

    def get_all_dashboard_counts(self, request, P):
        R, S = request.GET, request.session
        if R['from'] and R['upto']:
            ppmtask_arr = Jobneed.objects.get_ppmchart_data(request)
            task_arr = Jobneed.objects.get_taskchart_data(request)
            tour_arr = Jobneed.objects.get_tourchart_data(request)

            return {
                'counts': dict(
                    **self.task_portlet(task_arr),
                    **self.tour_portlet(tour_arr),
                    **self.ppm_portlet(ppmtask_arr),
                    **self.other_counts(P, request),
                    **self.other_chart_data(request)
                )
            }
    
    def task_portlet(self, task_arr):
        return {
            'totalschd_tasks_count': task_arr[-1],
            'assigned_tasks_count': task_arr[0],
            'completed_tasks_count': task_arr[1],
            'autoclosed_tasks_count': task_arr[2]}
    
    def tour_portlet(self, tour_arr):
        return {
            'totalscheduled_tours_count': tour_arr[-1],
            'completed_tours_count': tour_arr[0],
            'inprogress_tours_count': tour_arr[1],
            'partiallycompleted_tours_count': tour_arr[2],
        }
    
    def ppm_portlet(self, ppmtask_arr):
        return {
            'totalschd_ppmtasks_count': ppmtask_arr[-1],
            'assigned_ppmtasks_count': ppmtask_arr[0],
            'completed_ppmtasks_count': ppmtask_arr[1],
            'autoclosed_ppmtasks_count': ppmtask_arr[2],
        }
    
    def other_counts(self, P, request):
        return {
            'sos_count': P['pel_model'].objects.get_sos_count_forcard(request),
            'IR_count': P['jn_model'].objects.get_ir_count_forcard(request),
            'FR_fail_count': P['pel_model'].objects.get_frfail_count_forcard(request),
            'route_count': P['jn_model'].objects.get_schdroutes_count_forcard(request),
            'diversion_count': P['pel_model'].objects.get_diversion_countorlist(request, count=True),
            'sitecrisis_count': P['pel_model'].objects.get_sitecrisis_count_forcard(request),
            'dynamic_tour_count':P['jn_model'].objects.get_dynamic_tour_count(request),
            'workpermit_count':P['wp_model'].objects.get_workpermit_count(request)
        }
    
    def other_chart_data(self, request):
        asset_chart_arr, asset_chart_total = Asset.objects.get_assetchart_data(
                request)
        alert_chart_arr, alert_chart_total = Jobneed.objects.get_alertchart_data(
            request)
        ticket_chart_arr, ticket_chart_total = Ticket.objects.get_ticket_stats_for_dashboard(
            request)
        wom_chart_arr, wom_chart_total = Wom.objects.get_wom_status_chart(
            request)
        return {
            'assetchartdata': asset_chart_arr,
            'alertchartdata': alert_chart_arr,
            'ticketchartdata': ticket_chart_arr,
            'womchartdata': wom_chart_arr,
            'assetchart_total_count': asset_chart_total,
            'alertchart_total_count': alert_chart_total,
            'ticketchart_total_count': ticket_chart_total,
            'wom_total_count': wom_chart_total,
        }
    


class FileUpload(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        pass


class LicenseSubscriptionView(LoginRequiredMixin, View):
    P = {
        'model':Subscription
    }
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.P
        if R.get('action') == 'getLicenseList':
            qset = P['model'].objects.get_license_list(R['client_id'])
            return rp.JsonResponse({'data':list(qset)}, status=200)
        
        if R.get('action') == 'getTerminatedLicenseList':
            qset = P['model'].objects.get_terminated_license_list(R['client_id'])
            return rp.JsonResponse({'data':list(qset)}, status=200)
        
    
    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.P
        if R.get('subscriptionPostData'):
            resp = P['model'].objects.handle_subscription_postdata(request)
            return rp.JsonResponse(resp, status=200)
        
class BulkImportUpdate(LoginRequiredMixin,ParameterMixin, View):
    def get(self, request, *args, **kwargs):
        R, S = request.GET, request.session
        if (R.get('action') == 'form'):
            #removes the temp file created in the last import
            self.remove_temp_file(request)
            inst = utils.Instructions(tablename='TYPEASSIST')
            '''getting the instructions from the instance and here json.dumps 
            is used to convert the python dictionary to json.'''
            get_instructions = inst.get_insructions_update_info()
            cxt = {'importform': self.form_update(initial={'table': "TYPEASSIST"}), 'instructions':get_instructions}
            return render(request, self.template_import_update, cxt)
        
        if R.get('action') == 'getInstructions':
            inst = utils.Instructions(tablename=R.get('tablename'))
            instructions = inst.get_insructions_update_info()
            # get_column = inst.get_column_names_update()
            # instructions['general_instructions'][2] = "Columns marked with an asterisk (*) are required. Please delete any columns from the downloaded Excel sheet that you do not wish to update other then the ID* column."
            # instructions['column_names'] = "Columns: ${}&".format(', '.join(get_column))
            return rp.JsonResponse({'instructions':instructions}, status=200)

        if (request.GET.get('action') == 'downloadTemplate') and request.GET.get('template'):
            buffer = utils.excel_file_creation_update(R, S)
            return rp.FileResponse(
                buffer, as_attachment=True, filename=f'{R["template"]}.xlsx'
            )
    
    def post(self, request, *args, **kwargs):
        R = request.POST
        form = self.form(R, request.FILES)
        if not form.is_valid() and R['action'] != 'confirmImport':
            return rp.JsonResponse({'errors': form.errors}, status=404)
        res, dataset = obutils.get_resource_and_dataset(request, form,self.mode_resource_map_update)
        if R.get('action') == 'confirmImport':
            results = res.import_data(dataset = dataset, dry_run = False, raise_errors = False)
            return rp.JsonResponse({'totalrows':results.total_rows}, status = 200)
        else:
            try:
                results = res.import_data(
                    dataset=dataset, dry_run=True, raise_errors=False, use_transactions=True)
                return render(request, 'onboarding/imported_data_update.html', {'result':results})
            except Exception as e:
                logger.critical("error", exc_info=True)
                return rp.JsonResponse({"error": "something went wrong!"}, status=500)
    
    def upload_bulk_image_format(self,R):
        google_drive_link = R['google_drive_link']
        file_id = extract_file_id(google_drive_link)
        images_bulk_data = get_file_metadata(file_id)
        is_coorect, correct_image_data, incorrect_image_data = is_bulk_image_data_correct(images_bulk_data['files'])
        if not is_coorect:
            return False,incorrect_image_data
        return True,correct_image_data
        

    def get_resource_and_dataset(self, request, form):
        table = form.cleaned_data.get('table')
        if request.POST.get('action') == 'confirmImport':
            tempfile = request.session['temp_file_name']
            with open(tempfile, 'rb') as file:
                dataset = Dataset().load(file)
        else:
            file = request.FILES['importfile']
            dataset = Dataset().load(file)
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as tf:
                for chunk in file.chunks():
                    tf.write(chunk)
                request.session['temp_file_name'] = tf.name
        res = self.mode_resource_map[table](request=request, ctzoffset = form.cleaned_data.get('ctzoffset'))
        return res, dataset

    def get_readable_error(self, error):
        if(isinstance(error, ObjectDoesNotExist)):
            return "Related values does not exist, please check your data."
        if(isinstance(error, IntegrityError)):
            return "Record already exist, please check your data."
        return str(error)
    
    def remove_temp_file(self, request):
        filename = request.session.get('temp_file_name', '')
        try:
            os.remove(filename)
        except FileNotFoundError:
            log.info(f"The file {filename} does not exist.")
        except Exception as e:
            log.info(f"An error occurred while trying to remove the file {filename}: {str(e)}")


class ContractView(LoginRequiredMixin,View):
    params = { 'form_class':obforms.BtForm ,
        'template_form' : 'onboarding/contract_form.html',
        'template_list': 'onboarding/contract_list.html',
        'model':Bt } 

    def get(self,request,*args,**kwargs):
        R, resp = request.GET,None

        if R.get('template'):
            return render(request,self.params['template_list'])
        
        if R.get('action',None) == 'list':
            buids = self.params['model'].objects.get_whole_tree(
                request.session['client_id'])

            objs = self.params['model'].objects.select_related('parent').filter(id__in=buids,
                            identifier__tacode ='SITE').values('id','buname','bucode',
                    'parent__buname','solid','bupreferences__total_people_count',
                    'enable','butype__taname'
                    ).order_by('buname')
            return rp.JsonResponse(data={'data': list(objs)})
        
        elif R.get('action',None) == 'form':
            cxt = {'buform':self.params['form_class'](request=request),
                   'ta_form':obforms.TypeAssistForm(auto_id=False,request=request),
                   'msg':"create_bu_requested"}
            return render(request, self.params['template_form'], context=cxt)
        
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']) , request , self.params )
            # designation_data = obj.bupreferences.get('contract_designcount', {})
            initial = {'controlroom': obj.bupreferences.get('controlroom'),
                       'jsonData': json.dumps(obj.bupreferences.get('contract_designcount', {})),
                       'posted_people': obj.bupreferences.get('posted_people')}
            cxt = {'ta_form': obforms.TypeAssistForm(auto_id=False, request=request),
                   'buform': self.params['form_class'](request=request, instance=obj, initial=initial)}
        return render(request, self.params['template_form'], context=cxt)
    

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            if pk:
                msg = "bu_view"
                obj = utils.get_model_obj(pk, request, self.params)
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), kwargs={'request': request})
                create = False
            else:
                form = self.params['form_class'](data, request=request)

            if form.is_valid():
                designations_count = request.POST['jsonData']
                resp = self.handle_valid_form(form, request, create,designations_count,obj)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            logger.critical("BU saving error!", exc_info=True)
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create,designations_count,obj):
        logger.info('bu form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            bu = form.save(commit=False)
            bu.enable = obj.enable
            bu.gpslocation = obj.gpslocation
            bu.bupreferences['permissibledistance'] = obj.bupreferences['permissibledistance']
            bu.bupreferences['controlroom'] = obj.bupreferences['controlroom']
            bu.bupreferences['address'] = obj.bupreferences['address']
            bu.bupreferences['address2'] = obj.bupreferences['address2']
            bu.butype = obj.butype
            bu.ctzoffset = obj.ctzoffset
            bu.deviceevent = obj.deviceevent
            bu.enablesleepingguard = obj.enablesleepingguard
            bu.gpsenable = obj.gpsenable
            bu.identifier = obj.identifier
            bu.isserviceprovider = obj.isserviceprovider
            bu.isvendor = obj.isvendor
            bu.iswarehouse = obj.iswarehouse
            bu.parent = obj.parent
            bu.siteincharge = obj.siteincharge
            bu.skipsiteaudit = obj.skipsiteaudit
            bu.solid = obj.solid

            bu.bupreferences['posted_people'] = form.cleaned_data['posted_people']
            bu.bupreferences['contract_designcount'] = form.cleaned_data['jsonData']
            bu.bupreferences['total_people_count'] = form.cleaned_data['total_people_count']
            putils.save_userinfo(
                bu, request.user, request.session, create=create)
            logger.info("bu form saved")
            return rp.JsonResponse({'pk': bu.id}, status=200)
        except IntegrityError:
            return handle_intergrity_error("Bu")



class GetAllSites(LoginRequiredMixin, View):
   
    def get(self, request):
        try:
            qset = Bt.objects.get_all_sites_of_client(request.session['client_id'])
            sites = qset.values('id', 'bucode','buname')
            return rp.JsonResponse(list(sites), status=200)
        except Exception as e:
            logger.error("get_allsites() exception: %s", e)
        return rp.JsonResponse({'error':"Invalid Request"}, status=404)

class GetAssignedSites(LoginRequiredMixin, View):
    def get(self, request):
        try:
            if data := Pgbelonging.objects.get_assigned_sites_to_people(request.user.id):
                sites    = Bt.objects.filter(id__in = data).values('id', 'bucode','buname')
                return rp.JsonResponse(list(sites), status=200, safe=False)
        except Exception as e:
            logger.error("get_assignedsites() exception: %s", e)
        return rp.JsonResponse({'error':"Invalid Request"}, status=404)

class SwitchSite(LoginRequiredMixin, View):
    def post(self, request):
        req_buid= request.POST["buid"]
        resp = {}
        if req_buid !=" ":
            sites = Bt.objects.filter(id=req_buid).values('id', 'bucode','buname', 'enable')[:1]
            if len(sites) > 0:
                if sites[0]['enable'] == True:
                    request.session['bu_id']  = sites[0]['id']
                    request.session['sitecode'] = sites[0]['bucode']
                    request.session['sitename'] = sites[0]['buname']
                    resp["rc"] = 0
                    resp['message'] = "successfully switched to site."
                    log.info('successfully switched to site')
                else:
                    resp["rc"] = 1
                    resp['errMsg'] = "Inactive Site"
                    log.info('Inactive Site')
            else:
                    resp["rc"] = 1
                    resp['errMsg'] = "unable to find site."
                    log.info('unable to find site.')
        else:  
            resp["rc"] = 1
            resp['errMsg'] = "unable to find site."
            log.info('unable to find site.')
        return rp.JsonResponse(resp, status=200)


def get_list_of_peoples(request):
    if request.method == 'POST':
        return
    Model = apps.get_model('activity', request.GET['model'])
    obj = Model.objects.get(id=request.GET['id'])
    Pgbelonging = apps.get_model('peoples', 'Pgbelonging')
    data = Pgbelonging.objects.filter(
        Q(assignsites_id = 1) | Q(assignsites__isnull=True),
        pgroup_id = obj.pgroup_id
    ).values('people__peoplecode', 'people__peoplename', 'id') or Pgbelonging.objects.none()
    return rp.JsonResponse({'data':list(data)}, status=200)

