from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.transaction import atomic
from .models import Features, Discounts, Billing
from .forms import FeaturesForm, DiscountForm, BillingForm
from django.http import response as rp
from django.http.request import QueryDict
from apps.core import utils
from apps.peoples import utils as putils
import logging

logger = logging.getLogger('django')

# Create your views here.
class FeatureView(LoginRequiredMixin, View):
    PARAMS = {
        'model':Features,
        'form':FeaturesForm,
        'template_path':'clientbilling/features.html',
    }
    
    
    def get(self, request, *args, **kwargs):
        logger.info('FeatureView')
        R = request.GET
        if R.get('action') == 'list':
            qset = self.PARAMS['model'].objects.get_feature_list(request)
            return rp.JsonResponse(data={'data':list(qset)})
        if R.get('action') == 'approved_feature_list':
            qset = self.PARAMS['model'].objects.get_approvedfeature_list(request)
            return rp.JsonResponse(data={'data':list(qset)})
        form = FeaturesForm()
        return render(request, self.PARAMS['template_path'], context={'form': form})
    
    def post(self, request, *args, **kwargs):
        R ,P = request.POST, self.PARAMS
        data = QueryDict(request.POST['formData'])

        try:
            if pk := request.POST.get('pk', None):
                msg, create = "feature_view", False
                obj = utils.get_model_obj(pk, request,  P)
                form = P['form_class'](
                    data, request.FILES, instance=obj, request=request)
            else:
                form = P['form'](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp
    
    def handle_valid_form(self, form, request):
        logger.info('client form is valid')
        try:
            with atomic(using=utils.get_current_db_name()):
                obj = form.save()
                obj = putils.save_userinfo(
                obj, request.user, request.session)
                logger.info("features form saved")
                data = {'pk': obj.id}
                return rp.JsonResponse(data, status=200)
        except Exception:
            return utils.handle_Exception(request)
        
