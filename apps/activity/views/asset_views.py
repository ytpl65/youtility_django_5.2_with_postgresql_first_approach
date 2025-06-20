import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.http import QueryDict
from django.http import response as rp
from django.shortcuts import render
from django.views.generic.base import View
from apps.activity.filters import MasterAssetFilter
from django.contrib.gis.db.models.functions import AsWKT
from apps.activity.forms.asset_form import AssetForm,CheckpointForm,AssetExtrasForm,AssetComparisionForm,ParameterComparisionForm
from apps.activity.models.job_model import Jobneed,JobneedDetails
from apps.activity.models.asset_model import Asset,AssetLog
from apps.activity.models.question_model import QuestionSet,QuestionSetBelonging
import apps.activity.utils as av_utils
import apps.onboarding.forms as obf
import apps.peoples.utils as putils
from apps.core import utils
from apps.activity.utils import get_asset_jsonform

class AssetView(LoginRequiredMixin,View):
    P = {
        'template_form':'activity/asset_form.html',
        'template_list':'activity/asset_list.html',
        'model':Asset,
        'form':AssetForm,
        'jsonform':AssetExtrasForm,
        'related':['parent', 'location', 'bu'],
        'fields':['assetcode', 'assetname', 'id', 'parent__assetname','bu__bucode',
                  'runningstatus', 'enable', 'gps', 'identifier', 'location__locname',
                  'bu__buname']
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.P
        # first load the template
        if R.get('template'): return render(request, P['template_list'])
        
        # return qset_list data
        if R.get('action', None) == 'list':
            objs = P['model'].objects.get_assetlistview(P['related'], P['fields'], request)
            return  rp.JsonResponse(data = {'data':list(objs)})
        
        if R.get('action',None) == 'qrdownload' and R.get('code',None) and R.get('name', None):
            return utils.download_qrcode(R['code'], R['name'], 'ASSETQR', request.session, request)
            
        # return questionset_form empty
        if R.get('action', None) == 'form':
            cxt = {'assetform': P['form'](request=request),
                   'assetextrasform': P['jsonform'](request=request),
                   'ta_form': obf.TypeAssistForm(auto_id=False, request=request),
                   'msg': "create asset requested"}
            resp = render(request, P['template_form'], cxt)
        
        if R.get('action', None) == "delete" and R.get('id', None):
            return utils.render_form_for_delete(request, P, True)
        
        if R.get('fetchStatus') not in ["", None]:
            period = Asset.objects.get_period_of_assetstatus(R['id'], R['fetchStatus'])
            return rp.JsonResponse({'period':period}, status=200)
        
        # return form with instance
        elif R.get('id', None):
            from apps.activity.utils import get_asset_jsonform
            asset = utils.get_model_obj(R['id'], request, P)
            cxt = {'assetform': P['form'](instance = asset, request=request),
                   'assetextrasform': get_asset_jsonform(asset, request),
                   'ta_form': obf.TypeAssistForm(auto_id=False, request=request),
                   'msg': "Asset Update Requested"}
            resp = render(request, P['template_form'], context = cxt)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        data = QueryDict(request.POST['formData'])
        try:
            if pk := request.POST.get('pk', None):
                msg, create = "asset_view", False  
                people = utils.get_model_obj(pk, request,  self.P)
                form = self.P['form'](data, request=request, instance = people)
            else:
                form = self.P['form'](data, request = request)
            jsonform = self.P['jsonform'](data, request=request)
            if form.is_valid() and jsonform.is_valid():
                resp = self.handle_valid_form(form, jsonform, request, create)
            else:
                cxt = {'errors': form.errors}
                if jsonform.errors:
                    cxt.update({'errors': jsonform.errors})
                resp = utils.handle_invalid_form(request, self.P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    @staticmethod
    def handle_valid_form(form, jsonform, request ,create):
        from apps.core.utils import handle_intergrity_error
        
        try:
            asset = form.save(commit=False)
            asset.gpslocation = form.cleaned_data['gpslocation']
            asset.save()
            if av_utils.save_assetjsonform(jsonform, asset):
                asset = putils.save_userinfo(
                    asset, request.user, request.session, create = create)
            data = {'pk':asset.id}
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return handle_intergrity_error('Asset')
    
class MasterAsset(LoginRequiredMixin, View):
    params = {
        'form_class': None,
        'template_form': 'activity/partials/partial_masterasset_form.html',
        'template_list': 'activity/master_asset_list.html',
        'partial_form': 'peoples/partials/partial_masterasset_form.html',
        'partial_list': 'peoples/partials/master_asset_list.html',
        'related': ['parent', 'type'],
        'model': Asset,
        'filter': MasterAssetFilter,
        'fields': ['assetname', 'assetcode', 'runningstatus',
                   'parent__assetcode', 'gps', 'id', 'enable'],
        'form_initials': {}
    }
    list_grid_lookups = {}
    view_of = label = None

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        # first load the template
        if R.get('template'): return render(request, self.params['template_list'], {'label':self.label})
        # return qset_list data
        if R.get('action', None) == 'list' or R.get('search_term'):
            d = {'list': "master_assetlist", 'filt_name': "master_asset_filter"}
            self.params.update(d)
            objs = self.params['model'].objects.annotate(
                gps = AsWKT('gpslocation')
                ).select_related(
                *self.params['related']).filter(
                    **self.list_grid_lookups).values(*self.params['fields'])
            utils.printsql(objs)
            return  rp.JsonResponse(data = {'data':list(objs)})

        # return questionset_form empty
        if R.get('action', None) == 'form':
            self.params['form_initials'].update({
                'type': 1,
                'parent': 1})
            cxt = {'master_assetform': self.params['form_class'](request = request, initial = self.params['form_initials']),
                   'msg': f"create {self.label} requested",
                   'label': self.label}
            resp = utils.render_form(request, self.params, cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params, True)
        # return form with instance
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            cxt = {'label': self.label}
            resp = utils.render_form_for_update(
                request, self.params, 'master_assetform', obj, extra_cxt = cxt)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, False
        try:
            data = QueryDict(request.POST['formData'])
            if pk := request.POST.get('pk', None):
                msg = f'{self.label}_view'
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

    def handle_valid_form(self, form, request, create):
        raise NotImplementedError()

class AssetMaintainceList(LoginRequiredMixin, View):
    params = {
        'template_list': 'activity/assetmaintainance_list.html',
        'model'        : Jobneed,
        'fields':['id', 'plandatetime', 'jobdesc', 'people__peoplename', 'asset__assetname',
        'ctzoffset', 'asset__runningstatus', 'gpslocation', 'identifier'],
        'related':['asset', 'people']
    }
    
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # first load the template
        if R.get('template'): return render(request, P['template_list'])
        
        if R.get('action') == 'list':
            #last 3 months
            objs = P['model'].objects.get_assetmaintainance_list(request, P['related'], P['fields'])
            return rp.JsonResponse({'data':list(objs)}, status=200)



class AssetComparisionView(LoginRequiredMixin, View):
    template = 'activity/asset_comparision.html'
    form = AssetComparisionForm
    
    def get(self, request, *args, **kwargs):
        R, S = request.GET, request.session
        if R.get('template'):
            cxt = {'asset_cmp_form': self.form(request=request)}
            return render(request, self.template, cxt)
        
        if R.get('action') == 'get_assets' and R.get('of_type'):
            qset = Asset.objects.filter(
                client_id=S['client_id'],
                bu_id = S['bu_id'],
                type_id=R['of_type']).values('id', 'assetname').distinct()
            return rp.JsonResponse(
                data={'options':list(qset)}, status=200
            )
        if R.get('action') == 'get_qsets' and R.getlist('of_assets[]'):
            qset = QuestionSet.objects.filter(
                client_id=S['client_id'],
                bu_id = S['bu_id'],
                type__in=['CHECKLIST', 'ASSETMAINTENANCE'],
                parent_id=1,
                enable=True,
                assetincludes__contains=R.getlist('of_assets[]')).values('id', 'qsetname').distinct()
            return rp.JsonResponse(
                data={'options':list(qset)}, status=200
            )
        if R.get('action') == 'get_questions' and R.getlist('of_qset'):
            qset = QuestionSetBelonging.objects.filter(
                client_id=S['client_id'],
                bu_id = S['bu_id'],
                answertype='NUMERIC',
                qset_id=R.get('of_qset')).select_related('question').values('question_id', 'question__quesname').distinct()
            return rp.JsonResponse(
                data={'options':list(qset)}, status=200
            )
        
        if R.get('action') == 'get_data_for_graph' and R.get('formData'):
            formData = QueryDict(R['formData'])
            data = JobneedDetails.objects.get_asset_comparision(request, formData)
            return rp.JsonResponse({'series':data}, status=200, safe=False)
            
            

class ParameterComparisionView(LoginRequiredMixin, View):
    template = 'activity/parameter_comparision.html'
    form = ParameterComparisionForm
    
    def get(self, request, *args, **kwargs):
        R, S = request.GET, request.session
        if R.get('template'):
            cxt = {'asset_param_form': self.form(request=request)}
            return render(request, self.template, cxt)
        
        if R.get('action') == 'get_assets' and R.get('of_type'):
            qset = Asset.objects.filter(
                client_id=S['client_id'],
                bu_id = S['bu_id'],
                type_id=R['of_type']).values('id', 'assetname').distinct()
            return rp.JsonResponse(
                data={'options':list(qset)}, status=200
            )
        
        if R.get('action') == 'get_questions':
            questionsets = QuestionSet.objects.filter(
                client_id=S['client_id'],
                bu_id = S['bu_id'],
                type__in=['CHECKLIST', 'ASSETMAINTENANCE'],
                parent_id=1,
                enable=True,
                assetincludes__contains=[R.get('of_asset')]).values_list('id', flat=True).distinct()
            qset = QuestionSetBelonging.objects.filter(
                client_id=S['client_id'],
                bu_id = S['bu_id'],
                answertype='NUMERIC',
                qset_id__in=questionsets).select_related('question').values('question_id', 'question__quesname').distinct()
            return rp.JsonResponse(
                data={'options':list(qset)}, status=200
            )
        
        if R.get('action') == 'get_data_for_graph' and R.get('formData'):
            formData = QueryDict(R['formData'])
            data = JobneedDetails.objects.get_parameter_comparision(request, formData)
            return rp.JsonResponse({'series':data}, status=200, safe=False)
        

class PeopleNearAsset(LoginRequiredMixin, View):
    params = {
        'template_list':'activity/peoplenearasset.html',
        'model':Asset,
        'related':[],
        'fields':['id', 'assetcode', 'assetname', 'identifier', 'gpslocation']
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = self.params['model'].objects.get_peoplenearasset(request)
            return  rp.JsonResponse(data = {
                'data':list(objs)}, safe = False)
        

class Checkpoint(LoginRequiredMixin, View):
    params = {
        'form_class': CheckpointForm,
        'template_form': 'activity/partials/partial_checkpoint_form.html',
        'template_list': 'activity/checkpoint_list.html',
        'partial_form': 'peoples/partials/partial_checkpoint_form.html',
        'partial_list': 'peoples/partials/chekpoint_list.html',
        'related': ['parent', 'type', 'bu', 'location'],
        'model': Asset,
        'fields': ['assetname', 'assetcode', 'runningstatus', 'identifier','location__locname',
                   'parent__assetname', 'gps', 'id', 'enable', 'bu__buname', 'bu__bucode'],
        'form_initials': {'runningstatus': 'WORKING',
                          'identifier': 'CHECKPOINT',
                          'iscritical': False, 'enable': True}
    }
    
    def get(self, request, *args, **kwargs):
        R, resp, P = request.GET, None, self.params

        # first load the template
        if R.get('template'): return render(request, P['template_list'], {'label':"Checkpoint"})
        # return qset_list data
        if R.get('action', None) == 'list':
            objs = P['model'].objects.get_checkpointlistview(request, P['related'], P['fields'])
            return  rp.JsonResponse(data = {'data':list(objs)})
        
        if R.get('action',None) == 'qrdownload' and R.get('code',None) and R.get('name',None):
            return utils.download_qrcode(R['code'],R['name'],'CHECKPOINTQR',request.session,request)

        # return questionset_form empty
        if R.get('action', None) == 'form':
            P['form_initials'].update({
                'type': 1,
                'parent': 1})
            cxt = {'master_assetform': P['form_class'](request=request, initial=P['form_initials']),
                   'msg': "create checkpoint requested",
                   'label': "Checkpoint"}

            resp = utils.render_form(request, P, cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, P, True)
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, P)
            cxt = {'label': "Checkpoint"}
            resp = utils.render_form_for_update(
                request, P, 'master_assetform', obj, extra_cxt = cxt)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create, P = None, False, self.params
        try:
            data = QueryDict(request.POST['formData'])
            if pk := request.POST.get('pk', None):
                msg = 'Checkpoint_view'
                form = utils.get_instance_for_update(
                    data, P, msg, int(pk), kwargs={'request':request})
                create = False
            else:
                form = P['form_class'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        P = self.params
        try:
            cp = form.save(commit=False)
            cp.gpslocation = form.cleaned_data['gpslocation']
            putils.save_userinfo(
                cp, request.user, request.session, create = create)
            data = {'msg': f"{cp.assetcode}",
            'row': Asset.objects.get_checkpointlistview(request, P['related'], P['fields'], id=cp.id)}
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return utils.handle_intergrity_error('Checkpoint')



class AssetMaintainceList(LoginRequiredMixin, View):
    params = {
        'template_list': 'activity/assetmaintainance_list.html',
        'model'        : Jobneed,
        'fields':['id', 'plandatetime', 'jobdesc', 'people__peoplename', 'asset__assetname',
        'ctzoffset', 'asset__runningstatus', 'gpslocation', 'identifier'],
        'related':['asset', 'people']
    }
    
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # first load the template
        if R.get('template'): return render(request, P['template_list'])
        
        if R.get('action') == 'list':
            #last 3 months
            objs = P['model'].objects.get_assetmaintainance_list(request, P['related'], P['fields'])
            return rp.JsonResponse({'data':list(objs)}, status=200)



            
class AssetLogView(LoginRequiredMixin, View):
    params = {
        'model':AssetLog,
        'template_list':'activity/asset_log.html'
    }
    
    def get(self, request):
        R, P = request.GET, self.params
        
        if R.get('template'):
            return render(request, P['template_list'])
        
        if R.get('action') == 'asset_log':
            data = P['model'].objects.get_asset_logs(request)
            return rp.JsonResponse(data, status=200)
    