from apps.activity.models.asset_model import Asset
from apps.activity.models.question_model import QuestionSet
import apps.schedhuler.utils as sutils
import apps.peoples.utils as putils
from django.db.models import Q, F
from django.contrib import messages
from django.core.exceptions import EmptyResultSet
from django.db.utils import IntegrityError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404, QueryDict, response as rp
from django.shortcuts import redirect, render
from django.views import View
from apps.core import  utils 
from pprint import pformat
from apps.activity.models.job_model import Job, Jobneed, JobneedDetails
import apps.peoples.models as pm
from datetime import datetime, time, timedelta, timezone, date
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
import apps.schedhuler.forms as scd_forms
import logging
from django.db.models.deletion import RestrictedError
from django.urls import reverse
import json
from psycopg2.errors import NotNullViolation
from django.contrib.gis.db.models.functions import AsGeoJSON
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

logger = logging.getLogger('django')
error_logger = logging.getLogger('error_logger')
debug_logger = logging.getLogger('debug_logger')

# Create your views here.


class Schd_I_TourFormJob(LoginRequiredMixin, View):
    template_path = 'schedhuler/schd_i_tourform_job.html'
    form_class    = scd_forms.Schd_I_TourJobForm
    subform       = scd_forms.SchdChild_I_TourJobForm
    model         = Job
    initial       = {
        'starttime'   : time(00, 00, 00),
        'endtime'     : time(00, 00, 00),
        'expirytime'  : 0,
        'identifier'  :Job.Identifier.INTERNALTOUR,
        'priority'    :Job.Priority.LOW,
        'scantype'    :Job.Scantype.QR,
        'gracetime'   : 5,
        'fromdate'   : datetime.combine(date.today(), time(00, 00, 00)),
        'uptodate'   : datetime.combine(date.today(), time(23, 00, 00)) + timedelta(days = 2),
    }

    def get(self, request, *args, **kwargs):
        logger.info("create a guard tour requested")
        cxt = {'schdtourform': self.form_class(request = request, initial = self.initial),
               'childtour_form': self.subform()}
        return render(request, self.template_path, context = cxt)

    def post(self, request, *args, **kwargs):
        """Handles creation of Pgroup instance."""
        logger.info('Guard Tour form submitted')
        data, create = QueryDict(request.POST['formData']), True
        if pk := request.POST.get('pk', None):
            obj = utils.get_model_obj(pk, request, {'model': self.model})
            form = self.form_class(
                instance = obj, data = data, initial = self.initial, request = request)
            logger.info("retrieved existing guard tour jobname:= '%s'", (obj.jobname))
            create = False
        else:
            form = self.form_class(data = data, initial = self.initial, request = request)
            logger.info("new guard tour submitted following is the form-data:\n%s\n", (pformat(form.data)))
        response = None
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                if form.is_valid():
                    response = self.process_valid_schd_tourform(request, form, create)
                else:
                    response = self.process_invalid_schd_tourform(form)
        except Exception:
            logger.critical(
                "failed to process form, something went wrong", exc_info = True)
            response = rp.JsonResponse(
                {'errors': 'Failed to process form, something went wrong'}, status = 404)
        return response

    def process_valid_schd_tourform(self, request, form, create):
        resp = None
        logger.info("guard tour form processing/saving [ START ]")
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                assigned_checkpoints = json.loads(
                request.POST.get("asssigned_checkpoints"))
                job         = form.save(commit = False)
                job.parent_id  = -1
                job.asset_id = -1
                job.qset_id  = -1
                job.save()
                job = putils.save_userinfo(job, request.user, request.session, create = create)
                self.save_checpoints_for_tour(assigned_checkpoints, job, request)
                logger.info('guard tour  and its checkpoints saved success...')
        except Exception as ex:
            logger.critical("guard tour form is processing failed", exc_info = True)
            resp = rp.JsonResponse(
                {'error': "saving schd_tourform failed..."}, status = 404)
            raise ex
        else:
            logger.info("guard tour form is processed successfully")
            resp = rp.JsonResponse({'jobname': job.jobname,
                'url': reverse("schedhuler:update_tour", args=[job.id])},
                status = 200)
        logger.info("guard tour form processing/saving [ END ]")
        return resp

    @staticmethod
    def process_invalid_schd_tourform(form):
        logger.info(
            "processing invalid forms sending errors to the client [ START ]")
        cxt = {"errors": form.errors}
        logger.info(
            "processing invalid forms sending errors to the client [ END ]")
        return rp.JsonResponse(cxt, status = 404)

    def save_checpoints_for_tour(self, checkpoints, job, request):
        try:
            logger.info("saving Checkpoints [started]")
            self.insert_checkpoints(checkpoints, job, request)
            logger.info("saving QuestionSet Belonging [Ended]")
        except Exception as ex:
            logger.critical(
                "failed to save checkpoints, something went wrong", exc_info = True)
            raise ex

    def insert_checkpoints(self, checkpoints, job, request):
        logger.info("inserting checkpoints started...")
        logger.info("inserting checkpoints found %s checkpoints", (len(checkpoints)))
        CP = {}
        try:
            for cp in checkpoints:
                CP['expirytime'] = cp[5]
                CP['asset']    = cp[1]
                CP['qset']     = cp[3]
                CP['seqno']       = cp[0]
                checkpoint, created = self.model.objects.update_or_create(
                    parent_id  = job.id,
                    asset_id = CP['asset'],
                    qset_id  = CP['qset'],

                    defaults   = sutils.job_fields(job, cp)
                )
                checkpoint.save()
                status = "CREATED" if created else "UPDATED"
                logger.info("\nsaving checkpoint:= '%s' for JOB:= '%s' with expirytime:= '%s'  %s\n", cp[2], job.jobname, cp[5], status)
                putils.save_userinfo(checkpoint, request.user, request.session, create = created)
        except Exception as ex:
            logger.critical(
                "failed to insert checkpoints, something went wrong", exc_info = True)
            raise ex
        else:
            logger.info("inserting checkpoints finished...")

class Update_I_TourFormJob(Schd_I_TourFormJob, View):

    def get(self, request, *args, **kwargs):
        logger.info('Update Schedhule Tour form view')
        response = None
        try:
            pk = kwargs.get('pk')
            obj = self.model.objects.get(id = pk)
            logger.info('object retrieved {}'.format(obj))
            form        = self.form_class(instance = obj, initial = self.initial)
            checkpoints = self.get_checkpoints(obj = obj)
            cxt         = {'schdtourform': form, 'childtour_form': self.subform(), 'edit': True,
                   'checkpoints': checkpoints}
            response = render(request, self.template_path,  context = cxt)
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('schedhuler:create_tour')
        except Exception:
            logger.critical('something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('schedhuler:create_tour')
        return response

    def get_checkpoints(self, obj):
        logger.info("getting checkpoints started...")
        checkpoints = None
        try:
            checkpoints = self.model.objects.select_related(
                'parent', 'asset', 'qset', 'pgroup',
                'people',
            ).filter(parent_id = obj.id).values(
                'seqno',
                'asset__assetname',
                'asset__id',
                'qset__qset_name',
                'qset__id',
                'expirytime',
                'id')
        except Exception:
            logger.critical("something went wrong", exc_info = True)
            raise
        else:
            logger.info("checkpoints retrieved returned success")
        return checkpoints

class Retrive_I_ToursJob(LoginRequiredMixin, View):
    params = {
        'model'        : Job,
        'template_path': 'schedhuler/schd_i_tourlist_job.html',
        'fields'       : ['jobname', 'people__peoplename', 'pgroup__groupname', 'fromdate', 'uptodate',
                        'planduration', 'gracetime', 'expirytime', 'id'],
        'related': ['pgroup', 'people']
    }

    model = Job
    template_path = 'schedhuler/schd_i_tourlist_job.html'
    fields = ['jobname', 'people__peoplename', 'pgroup__groupname', 'fromdate', 'uptodate',
              'planduration', 'gracetime', 'expirytime', 'id']
    related = ['pgroup', 'people']

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            logger.info('Retrieve Schedhuled Tours view')
            objects = self.model.objects.select_related(
                *self.related).filter(
                    ~Q(jobname='NONE'), parent__jobname='NONE'
            ).values(*self.fields).order_by('-cdtz')
            logger.info(f'Schedhuled Tours objects {len(objects)} retrieved from db' if objects else "No Records!")

            cxt = self.paginate_results(request, objects)
            logger.info('Results paginated'if objects else "")
            response = render(request, self.template_path, context = cxt)
        except EmptyResultSet:
            logger.warning('empty objects retrieved', exc_info = True)
            response = render(request, self.template_path, context = cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            logger.critical(
                'something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    @staticmethod
    def paginate_results(request, objects):
        '''paginate the results'''
        logger.info('Pagination Start'if objects else "")
        from .filters import SchdTourFilter
        if request.GET:
            objects = SchdTourFilter(request.GET, queryset = objects).qs
        filterform = SchdTourFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            schdtour_list = paginator.page(page)
        except PageNotAnInteger:
            schdtour_list = paginator.page(1)
        except EmptyPage:
            schdtour_list = paginator.page(paginator.num_pages)
        return {'schdtour_list': schdtour_list, 'schdtour_filter': filterform}

def deleteChekpointFromTour(request):
    if request.method != 'GET':
        return Http404

    datasource = request.GET.get('datasource')
    checkpointid = request.GET.get('checkpointid')
    checklistid = request.GET.get('checklistid')
    job = request.GET.get('job')
    statuscode, msg = 404, ""
    try:
        if datasource == 'job':
            sutils.delete_from_job(job, checkpointid, checklistid)
            statuscode, msg = 200, "Success"
        elif datasource == "jobneed":
            sutils.delete_from_jobneed(job, checkpointid, checklistid)
            statuscode, msg = 200, "Success"
    except RestrictedError:
        msg = "Unable to delete, due to its dependencies on other data!"
        error_logger.error("something went wrong", exc_info = True)
    except Exception:
        msg = "Something went wrong"
        logger.critical("something went wrong", exc_info = True)
    return rp.JsonResponse({'errors': msg}, status = statuscode)



class Retrive_I_ToursJobneed(LoginRequiredMixin, View):
    model = Jobneed
    template_path = 'schedhuler/i_tourlist_jobneed.html'
    fields    = ['jobdesc', 'people__peoplename', 'pgroup__groupname', 'id',
              'plandatetime', 'expirydatetime', 'jobstatus', 'gracetime', 'performedby__peoplename',]
    related   = ['pgroup',  'ticketcategory', 'asset', 'client',
               'frequency', 'job', 'qset', 'people', 'parent', 'bu']

    def get(self, request, *args, **kwargs):
        '''returns jobneed (internal-tours) from db'''
        response, session = None, request.session

        try:
            logger.info('Retrieve internal tours(jobneed) view')
            dt = datetime.now(tz = timezone.utc) - timedelta(days = 10)
            objects = self.model.objects.select_related(
                *self.related).filter(
                    Q(bu_id = session['bu_id']) & Q(parent__jobdesc='NONE')
                    & ~Q(jobdesc='NONE') & Q(plandatetime__gte = dt)
            ).values(*self.fields).order_by('-plandatetime')
            logger.info('Internal Tours objects %s retrieved from db' %
                     (len(objects)) if objects else "No Records!")
            cxt = self.paginate_results(request, objects)
            logger.info('Results paginated' if objects else "")
            response = render(request, self.template_path, context = cxt)

        except EmptyResultSet:
            logger.warning('empty objects retrieved', exc_info = True)
            response = render(request, self.template_path, context = cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            logger.critical(
                'something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    @staticmethod
    def paginate_results(request, objects):
        '''paginate the results'''
        logger.info('Pagination Start' if objects else "")
        from .filters import InternalTourFilter

        if request.GET:
            objects = InternalTourFilter(request.GET, queryset = objects).qs
        filterform = InternalTourFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)

        try:
            tour_list = paginator.page(page)
        except PageNotAnInteger:
            tour_list = paginator.page(1)
        except EmptyPage:
            tour_list = paginator.page(paginator.num_pages)
        return {'tour_list': tour_list, 'tour_filter': filterform}

class Get_I_TourJobneed(LoginRequiredMixin, View):
    model         = Jobneed
    template_path = 'schedhuler/i_tourform_jobneed.html'
    form_class    = scd_forms.I_TourFormJobneed
    subform       = scd_forms.Child_I_TourFormJobneed
    initial       = {
        'identifier': Jobneed.Identifier.INTERNALTOUR,
        'frequency' : Jobneed.Frequency.NONE
    }

    def get(self, request, *args, **kwargs):
        logger.info("retrieving internal tour datasource[jobneed]")
        parent_jobneed, response = kwargs.get('pk'), None

        try:
            obj = self.model.objects.get(id = parent_jobneed)
            form = self.form_class(instance = obj, initial = self.initial)
            logger.info("object retrieved %s", (obj.jobdesc))
            checkpoints = self.get_checkpoints(obj = obj)
            cxt = {'internaltourform': form, 'child_internaltour': self.subform(prefix='child'), 'edit': True,
                   'checkpoints': checkpoints}
            response = render(request, self.template_path, context = cxt)

        except self.model.DoesNotExist:
            error_logger.error('object does not exist', exc_info = True)
            response = redirect('schedhuler:retrieve_internaltours')

        except Exception:
            logger.critical('something went wron', exc_info = True)
            response = redirect('schedhuler:retrieve_internaltours')
        return response

    @staticmethod
    def post(request, *args, **kwargs):
        logger.info("saving internal tour datasource[jobneed]")

    def get_checkpoints(self, obj):
        logger.info("getting checkpoints for the internal tour [start]")
        checkpoints = None

        try:
            checkpoints = self.model.objects.select_related(
                'parent', 'asset', 'qset', 'pgroup',
                'people', 'job', 'client', 'bu',
                'ticketcategory'
            ).filter(parent_id = obj.id).values(
                'asset__assetname', 'asset__id', 'qset__id',
                'qset__qset_name', 'plandatetime', 'expirydatetime',
                'gracetime', 'seqno', 'jobstatus', 'id').order_by('seqno')

        except Exception:
            logger.critical("something went wrong", exc_info = True)
            raise

        else:
            logger.info("checkpoints retrieved returned success")
        return checkpoints

def add_cp_internal_tour(request):  # jobneed
    resp = None
    if request.method == 'POST':
        formData = request.POST.get('formData')
        parentid = request.POST.get('parentid')
        try:
            parent = Jobneed.objects.get(id = parentid)
            data  = {'jobdesc' : parent.jobdesc, 'receivedonserver': parent.receivedonserver,
                    'starttime': parent.starttime, 'endtime': parent.endtime, 'gpslocation': parent.gpslocation,
                    'remarks'  : parent.remarks, 'frequency': parent.frequency, 'job': parent.job,
                    'jobstatus': parent.jobstatus, 'jobtype': parent.jobtype, 'performedby': parent.performedby,
                    'priority' : ""}
            form = scd_forms.ChildInternalTourForm(data = formData)

        except Jobneed.DoesNotExist:
            msg = "Parent not found failed to add checkpoint!"
            resp = rp.JsonResponse({'errors': msg}, status = 404)
        except Exception:
            msg = "Something went wrong!"
            logger.critical(f"{msg}", exc_info = True)
            resp = rp.JsonResponse({"errors": msg}, status = 200)

class Schd_E_TourFormJob(LoginRequiredMixin, View):
    params = {
        'model':Jobneed,
        'form_class':scd_forms.Schd_E_TourJobForm,
        'subform':scd_forms.EditAssignedSiteForm,
        'template_path':'schedhuler/schd_e_tourform_job.html',
        'initial':{
            'seqno':-1,
            'scantype':Job.Scantype.QR,
            'frequency':Job.Frequency.NONE,
            'identifier':Job.Identifier.EXTERNALTOUR,
            'starttime':time(00,00,00),
            'endtime':time(00,00,00),
            'priority':Job.Priority.HIGH,    
            'expirytime':0
        }
    }

    def get(self, request, *args, **kwargs):

        logger.info("create a guard tour requested")
        cxt = {'schdexternaltourform': self.form_class(
            request = request, initial = self.initial),
               'editsiteform':self.subform()}
        return render(request, self.template_path, context = cxt)

    def post(self, request, *args, **kwargs):
        """Handles creation of Pgroup instance."""
        logger.info('External Tour form submitted')
        formData, create = QueryDict(request.POST.get('formData')), True
        if pk := request.POST.get('pk', None):
            obj = utils.get_model_obj(pk, request, {'model': self.model})
            form = self.form_class(
                instance = obj, data = formData, initial = self.initial)
            logger.info("retrieved existing guard tour jobname:= '%s'", (obj.jobname))
            create = False
        else:
            form = self.form_class(data = formData, initial = self.initial)
            logger.info("new guard tour submitted following is the form-data:\n%s\n", (pformat(form.data)))
        response = None
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                if form.is_valid():
                    response = self.process_valid_schd_tourform(request, form, create)
                else:
                    response = self.process_invalid_schd_tourform(form)
        except Exception:
            logger.critical(
                "failed to process form, something went wrong", exc_info = True)
            response = rp.JsonResponse(
                {'errors': 'Failed to process form, something went wrong'}, status = 404)
        return response

    @staticmethod
    def process_invalid_schd_tourform(form):
        logger.info(
            "processing invalid forms sending errors to the client [ START ]")
        cxt = {"errors": form.errors}
        logger.info(
            "processing invalid forms sending errors to the client [ END ]")
        return rp.JsonResponse(cxt, status = 404)

    @staticmethod
    def process_valid_schd_tourform(request, form, create):
        resp = None
        logger.info("external tour form processing/saving [ START ]")
        try:
            job         = form.save(commit = False)
            job.parent_id  = 1
            job.asset_id = 1
            job.save()
            job = putils.save_userinfo(job, request.user, request.session)
            logger.info('external tour  and its checkpoints saved success...')
        except Exception as ex:
            logger.critical(
                "external tour form is processing failed", exc_info = True)
            resp = rp.JsonResponse(
                {'error': "saving schd_tourform failed..."}, status = 404)
            raise ex
        else:
            logger.info("external tour form is processed successfully")
            resp = rp.JsonResponse({'jobname': job.jobname,
                                    'url': reverse("schedhuler:update_externaltour", args=[job.id])},
                                   status = 200)
        logger.info("external tour form processing/saving [ END ]")
        return resp


class Update_E_TourFormJob(Schd_E_TourFormJob, LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        logger.info('Update External Schedhule Tour form view')
        response = None
        try:
            pk = kwargs.get('pk')
            obj = self.model.objects.get(id = pk)
            logger.info('object retrieved {}'.format(obj))
            form        = self.form_class(instance = obj, initial = self.initial)
            checkpoints = self.get_checkpoints(obj = obj)
            cxt         = {'schdexternaltourform': form, 'edit': True,
                        'editsiteform':self.subform(),
                        'checkpoints': checkpoints,
                        'qsetname':obj.qset.qsetname,
                        'qset':obj.qset.id}
            response = render(request, self.template_path,  context = cxt)
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('schedhuler:create_tour')
        except Exception:
            logger.critical('something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('schedhuler:create_tour')
        return response

    @staticmethod
    def get_checkpoints(obj):
        logger.info("getting checkpoints started...")
        checkpoints = None
        try:
            checkpoints = pm.Pgbelonging.objects.select_related(
                'assignsites', 'identifier'
            ).filter(pgroup_id = obj.sgroup_id).values(
                'assignsites__buname', 'assignsites_id', 'assignsites__bucode', 'assignsites__gpslocation'
            )
        except Exception:
            logger.critical("something went wrong", exc_info = True)
            raise
        else:
            if checkpoints:
                logger.info("total %s checkpoints retrieved returned success", (len(checkpoints)))
            else: logger.info("checkpoints not found")
        return checkpoints


class Retrive_E_ToursJob(LoginRequiredMixin, View):
    model = Job
    template_path = 'schedhuler/schd_e_tourlist_job.html'
    fields = ['jobname', 'people__peoplename', 'pgroup__groupname',
              'fromdate', 'uptodate',
              'planduration', 'gracetime', 'expirytime', 'id', 'bu__buname']
    related = ['pgroup', 'people']

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            logger.info('Retrieve Schedhuled External Tours view')
            objects = self.model.objects.select_related(
                *self.related).filter(
                    ~Q(jobname='NONE'), parent__jobname='NONE', identifier="EXTERNALTOUR"
            ).values(*self.fields).order_by('-cdtz')
            logger.info('Schedhuled External Tours objects %s retrieved from db'%len(objects) if objects else "No Records!")
            cxt = self.paginate_results(request, objects)
            logger.info('Results paginated'if objects else "")
            response = render(request, self.template_path, context = cxt)
        except EmptyResultSet:
            logger.warning('empty objects retrieved', exc_info = True)
            response = render(request, self.template_path, context = cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            logger.critical(
                'something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    @staticmethod
    def paginate_results(request, objects):
        '''paginate the results'''
        logger.info('Pagination Start'if objects else "")
        from .filters import SchdExtTourFilter
        if request.GET:
            objects = SchdExtTourFilter(request.GET, queryset = objects).qs
        filterform = SchdExtTourFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            schdtour_list = paginator.page(page)
        except PageNotAnInteger:
            schdtour_list = paginator.page(1)
        except EmptyPage:
            schdtour_list = paginator.page(paginator.num_pages)
        return {'ext_schdtour_list': schdtour_list, 'ext_schdtour_filter': filterform}


@require_http_methods(["POST"])
def run_internal_tour_scheduler(request):
    """Schedules an internal tour based on the POST request."""
    job_id = request.POST.get('job_id')
    action = request.POST.get('action')
    checkpoints = json.loads(request.POST.get('checkpoints', '[]'))

    # Start structured logging
    logger.info('run_guardtour_scheduler initiated', extra={'phase': 'START', 'job_id': job_id})

    # Validate inputs
    if not job_id:
        error_logger.error('Job ID not found in request', extra={'request': request.POST})
        return rp.JsonResponse({"errors": "Job ID not found"}, status=404)

    # Fetch the Job
    job = _get_job(job_id)

    if job is None:
        error_logger.error('Job not found in database', extra={'job_id': job_id})
        return rp.JsonResponse({"errors": "Job not found"}, status=404)

    # Handle Randomized External Tour
    if job['other_info']['is_randomized'] in [True, 'true'] and action == 'saveCheckpoints':
        logger.info('Tour type random is going to schedule', extra={'job': job})
        _handle_random_external_tour(job, checkpoints, request)

    if job['other_info']['isdynamic']:
        resp = sutils.create_dynamic_job([job['id']])
        resp = rp.JsonResponse(resp, status=200, safe=False)
    else:
        # Create a new job
        response, _ = sutils.create_job([job['id']])
        resp = rp.JsonResponse(response, status=200, safe=False)

    # End logging
    logger.info('run_guardtour_scheduler ended', extra={'phase': 'END', 'job_id': job_id, 'response': resp})

    return resp

def _get_job(job_id):
    """Fetch a job from the database by its ID"""
    jobs = Job.objects.filter(id=job_id).select_related(
        "asset", "pgroup", 'sgroup', "cuser", "muser", "qset", "people").values(*utils.JobFields.fields)
    return jobs[0] if jobs else None

def _handle_random_external_tour(job, checkpoints, request):
    """Handle a randomized external tour"""
    Job.objects.filter(parent_id=job['id']).delete()
    logger.info("saving checkpoints started...", extra={'job': job})
    
    for checkpoint in checkpoints:
        obj = Job.objects.create(**sutils.job_fields(job, checkpoint, external=True))
        putils.save_userinfo(obj, request.user, request.session, bu=checkpoint['buid'])
        logger.info(f"checkpoint saved", extra={'checkpoint': obj.jobname})
    
    logger.info("saving checkpoints ended...", extra={'job': job})

def get_cron_datetime(request):
    if request.method != 'GET':
        return Http404

    logger.info("get_cron_datetime [start]")
    cron = request.GET.get('cron')
    logger.info(f"get_cron_datetime cron:{cron}")
    cronDateTime= itr= None
    startdtz= datetime.now()
    enddtz= datetime.now() + timedelta(days = 1)
    DT, res= [], None
    try:
        from croniter import croniter
        itr= croniter(cron, startdtz)
        while True:
            cronDateTime = itr.get_next(datetime)
            if cronDateTime < enddtz:
                DT.append(cronDateTime)
            else: break
        res = rp.JsonResponse({'rows':DT}, status = 200)
    except Exception as ex:
        msg = "croniter bad cron error"
        logger.critical(msg, exc_info = True)
        res = rp.JsonResponse({'errors':msg}, status = 404)
    return res

def save_assigned_sites_for_externaltour(request):
    if request.method=='POST':
        logger.info("save_assigned_sites_for_externaltour [start+]")
        formData = QueryDict(request.POST.get('formData'))
        parentJobId = request.POST.get('pk')
        with transaction.atomic(using = utils.get_current_db_name()):
            save_sites_in_job(request, parentJobId)

def save_sites_in_job(request, parentid):
    try:
        checkpoints = json.loads(request.POST.get('assignedSites'))
        job = Job.objects.get(id=parentid)
        for cp in checkpoints:
            Job.objects.update_or_create(
                parent_id=job.id, asset_id=cp['asset'], qset_id=cp['qset'], breaktime=cp['breaktime'],
                defaults=sutils.job_fields(job, cp, external=True))

    except Job.DoesNotExist:
        msg = 'Parent job not found failed to save assigned sites!'
        error_logger.error(f"{msg}", exc_info=True)
        raise
    except Exception:
        logger.critical("something went wrong!", exc_info=True)
        raise


class SchdTaskFormJob(LoginRequiredMixin, View):
    template_path = 'schedhuler/schd_taskform_job.html'
    form_class    = scd_forms.SchdTaskFormJob
    model         = Job
    initial       = {
        'starttime'   : time(00, 00, 00),
        'endtime'     : time(00, 00, 00),
        'fromdate'    : datetime.combine(date.today(), time(00, 00, 00)),
        'uptodate'    : datetime.combine(date.today(), time(23, 00, 00)) + timedelta(days = 2),
        'identifier'  : Job.Identifier.TASK,
        'frequency'   : Job.Frequency.NONE,
        'scantype'    : Job.Scantype.QR,
        'priority'    : Job.Priority.LOW,
        'planduration': 5,
        'gracetime'   : 5,
        'expirytime'  : 5
    }

    def get(self, request, *args, **kwargs):
        logger.info('create task to schedule is requested')
        cxt = {
            'schdtaskform':self.form_class(initial = self.initial)
        }
        return render(request, self.template_path, context = cxt)

    def post(self, request, *args, **kwargs):
        logger.info('Task form submitted')
        data, create = QueryDict(request.POST['formData']), True
        utils.display_post_data(data)
        if pk := request.POST.get('pk', None):
            obj = utils.get_model_obj(pk, request, {'model': self.model})
            form = self.form_class(
                instance = obj, data = data, initial = self.initial)
            logger.info("retrieved existing task whose jobname:= '%s'", (obj.jobname))
        else:
            form = self.form_class(data = data, initial = self.initial)
            logger.info("new task submitted following is the form-data:\n%s\n", (pformat(form.data)))
        response = None
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                if form.is_valid():
                    response = self.process_valid_schd_taskform(request, form)
                else:
                    response = self.process_invalid_schd_taskform(
                        form)
        except Exception:
            logger.critical(
                "failed to process form, something went wrong", exc_info = True)
            response = rp.JsonResponse(
                {'errors': 'Failed to process form, something went wrong'}, status = 404)
        return response

    @staticmethod
    def process_valid_schd_taskform(request, form):
        resp = None
        logger.info("task form processing/saving [ START ]")
        try:
            job         = form.save(commit = False)
            job.parent_id  = 1
            job.save()
            job = putils.save_userinfo(job, request.user, request.session)
            logger.info('task form saved success...')
        except Exception as ex:
            logger.critical("task form is processing failed", exc_info = True)
            resp = rp.JsonResponse(
                {'error': "saving schd_taskform failed..."}, status = 404)
            raise ex from ex
        else:
            logger.info("task form is processed successfully")
            resp = rp.JsonResponse({'jobname': job.jobname,
                'url': reverse("schedhuler:update_task", args=[job.id])},
                status = 200)
        logger.info("task form processing/saving [ END ]")
        return resp

    @staticmethod
    def process_invalid_schd_taskform(form):
        logger.info(
            "processing invalidt task form sending errors to the client [ START ]")
        cxt = {"errors": form.errors}
        logger.info(
            "processing invalidt task form sending errors to the client [ END ]")
        return rp.JsonResponse(cxt, status = 404)


class RetriveSchdTasksJob(LoginRequiredMixin, View):
    model = Job
    template_path = 'schedhuler/schd_tasklist_job.html'
    fields = ['jobname', 'people__peoplename', 'pgroup__groupname',
              'fromdate', 'uptodate', 'qset__qsetname', 'asset__assetname',
              'planduration', 'gracetime', 'expirytime', 'id']
    related = ['pgroup', 'people', 'asset']

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        R, resp = request.GET, None
        try:
            # first load the template
            if R.get('template'): return render(request, self.template_path)

            # then load the table with objects for table_view
            if R.get('action') == 'list':
                logger.info('Retrieve Tasks view')
                objects = self.model.objects.select_related(
                    *self.related).filter(
                        ~Q(jobname='NONE'), parent__jobname='NONE', identifier="TASK"
                ).values(*self.fields).order_by('-cdtz')
                logger.info(f'Tasks objects {len(objects)} retrieved from db' if objects else "No Records!")
                response = rp.JsonResponse(data = {'data':list(objects)})
        except EmptyResultSet:
            logger.warning('empty objects retrieved', exc_info = True)
            response = render(request, self.template_path)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            logger.critical(
                'something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    @staticmethod
    def paginate_results(request, objects):
        '''paginate the results'''
        logger.info('Pagination Start'if objects else "")
        from .filters import SchdTaskFilter
        if request.GET:
            objects = SchdTaskFilter(request.GET, queryset = objects).qs
        filterform = SchdTaskFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            schdtour_list = paginator.page(page)
        except PageNotAnInteger:
            schdtour_list = paginator.page(1)
        except EmptyPage:
            schdtour_list = paginator.page(paginator.num_pages)
        return {'schd_task_list': schdtour_list, 'schd_task_filter': filterform}

class UpdateSchdTaskJob(SchdTaskFormJob):
    def get(self, request, *args, **kwargs):
        logger.info('Update task form view')
        try:
            pk = kwargs.get('pk')
            obj = self.model.objects.get(id = pk)
            logger.info(f'object retrieved {obj}')
            form        = self.form_class(instance = obj)
            cxt         = {'schdtaskform': form, 'edit': True}

            response = render(request, self.template_path,  context = cxt)
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('schedhuler:create_tour')
        except Exception:
            logger.critical('something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('schedhuler:create_task')
        return response

class RetrieveTasksJobneed(LoginRequiredMixin, View):
    model         = Jobneed
    template_path = 'schedhuler/tasklist_jobneed.html'

    fields  = [
        'jobdesc', 'people__peoplename', 'pgroup__groupname', 'id',
        'plandatetime', 'expirydatetime', 'jobstatus', 'gracetime',
        'performedby__peoplename', 'asset__assetname', 'qset__qsetname'
    ]
    related = [
        'pgroup',  'ticketcategory', 'asset', 'client',
        'frequency', 'job', 'qset', 'people', 'parent', 'bu' 
    ]

    def get(self, request, *args, **kwargs):
        '''returns jobneed (tasks) from db'''
        response, session = None, request.session

        try:
            logger.info('Retrieve tasks(jobneed) view')
            dt      = datetime.now(tz = timezone.utc) - timedelta(days = 10)
            objects = self.model.objects.select_related(
                *self.related).filter(
                Q(bu_id = session['bu_id']),  ~Q(parent__jobdesc='NONE')
                , ~Q(jobdesc='NONE') , Q(plandatetime__gte = dt)
                ,Q(identifier = Jobneed.Identifier.TASK)
            ).values(*self.fields).order_by('-plandatetime')
            logger.info('tasks objects %s retrieved from db' % 
                     (len(objects)) if objects else "No Records!")
            cxt = self.paginate_results(request, objects)
            logger.info('Results paginated' if objects else "")
            response = render(request, self.template_path, context = cxt)

        except EmptyResultSet:
            logger.warning('no objects found', exc_info = True)
            response = render(request, self.template_path, context = cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            logger.critical(
                'something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    @staticmethod
    def paginate_results(request, objects):
        '''paginate the results'''
        logger.info('Pagination Start' if objects else "")
        from .filters import TaskListJobneedFilter

        if request.GET:
            objects = TaskListJobneedFilter(request.GET, queryset = objects).qs
        filterform = TaskListJobneedFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)

        try:
            tour_list = paginator.page(page)
        except PageNotAnInteger:
            tour_list = paginator.page(1)
        except EmptyPage:
            tour_list = paginator.page(paginator.num_pages)
        return {'task_list': tour_list, 'task_filter': filterform}

class GetTaskFormJobneed(LoginRequiredMixin, View):
    model         = Jobneed
    template_path = 'schedhuler/taskform_jobneed.html'
    form_class    = scd_forms.TaskFormJobneed
    initial       = {
        'identifier'    : Jobneed.Identifier.TASK,
        'frequency'     : Jobneed.Frequency.NONE
    }

    def get(self, request, *args, **kwargs):
        logger.info("retrieving task datasource[jobneed]")
        parent_jobneed, response = kwargs.get('pk'), None

        try:
            obj = self.model.objects.get(id = parent_jobneed)
            form = self.form_class(instance = obj)
            logger.info(f"object retrieved {obj.jobdesc}")
            cxt = {'taskformjobneed': form, 'edit': True}
            response = render(request, self.template_path, context = cxt)

        except self.model.DoesNotExist:
            error_logger.error('object does not exist', exc_info = True)
            response = redirect('schedhuler:retrieve_tasksjobneed')

        except Exception:
            logger.critical('something went wron', exc_info = True)
            response = redirect('schedhuler:retrieve_tasksjobneed')
        return response

    @staticmethod
    def post(request, *args, **kwargs):
        logger.info("saving tasks datasource[jobneed]")


class JobneedTours(LoginRequiredMixin, View):
    params = {
        'model'        : Jobneed,
        'template_path': 'schedhuler/i_tourlist_jobneed.html',
        'template_form': 'schedhuler/i_tourform_jobneed.html',
        'fields'       : ['jobdesc', 'people__peoplename', 'pgroup__groupname', 'id', 'ctzoffset', 'jobtype',
            'plandatetime', 'expirydatetime', 'jobstatus', 'gracetime', 'performedby__peoplename', 'assignedto', 'other_info__isdynamic',
            'bu__buname', 'bu__bucode','client__buname','client_name','site_name','no_of_checkpoints','completed','missed','starttime','endtime' ],
        'related': ['pgroup',  'ticketcategory', 'asset', 'client',
                'job', 'qset', 'people', 'parent', 'bu'],
        'form_class':scd_forms.I_TourFormJobneed,
        'subform' : scd_forms.Child_I_TourFormJobneed,
        'initial': {
        'identifier': Jobneed.Identifier.INTERNALTOUR,
        'frequency' : Jobneed.Frequency.NONE
        }
    }

    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # first load the template
        if R.get('template'): return render(request, P['template_path'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            start = int(R.get('start', 0))
            length = int(R.get('length', 10))
            search = R.get('search[value]', '').strip()
            order_col = request.GET.get('order[0][column]')
            order_dir = request.GET.get('order[0][dir]')
            column_name = request.GET.get(f'columns[{order_col}][data]')

            objs = P['model'].objects.get_internaltourlist_jobneed(request, P['related'], P['fields'])

            if search:
                objs = objs.filter(
                    Q(bu__buname=search) |
                    Q(bu__bucode=search) |
                    Q(jobdesc__contains = search)
                )

            if column_name:
                order_prefix = '' if order_dir == 'asc' else '-'
                objs = objs.order_by(f'{order_prefix}{column_name}')

            total = objs.count()
            paginated = objs[start:start+length]
            return rp.JsonResponse({
                "draw": int(R.get('draw', 1)),
                "recordsTotal": total,
                "recordsFiltered": total,
                "data": list(paginated)
            })
            # return rp.JsonResponse(data = {'data':list(objs)})
        
        if R.get('action') == 'checklist_details' and R.get('jobneedid'):
            objs = JobneedDetails.objects.get_e_tour_checklist_details(R['jobneedid'])
            return rp.JsonResponse(data = {'data':list(objs)})
        
        if R.get('action') == 'get_checkpointdetails':
            qset = P['model'].objects.get_tourdetails(R)
            return rp.JsonResponse({'data':list(qset)}, status = 200)
        
        if R.get('action') == 'getAttachmentJobneed' and R.get('id'):
            att = P['model'].objects.getAttachmentJobneed(R['id'])
            return rp.JsonResponse(data = {'data':list(att)})

        if R.get('action') == 'getAttachmentJND' and R.get('id'):
            att = JobneedDetails.objects.getAttachmentJND(R['id'])
            return rp.JsonResponse(data = {'data': list(att)})
        
        if R.get('id'):
            obj = P['model'].objects.get(id = R['id'])
            form = P['form_class'](instance = obj, initial = P['initial'], request=request)
            logger.info("object retrieved %s", (obj.jobdesc))
            checkpoints = self.get_checkpoints(P, obj = obj)
            cxt = {'internaltourform': form, 'child_internaltour': P['subform'](prefix='child', request=request), 'edit': True,
                'checkpoints': checkpoints}
            return render(request, P['template_form'], context = cxt)
    
    @staticmethod
    def get_checkpoints(P, obj):
        logger.info("getting checkpoints for the internal tour [start]")
        checkpoints = None

        try:
            checkpoints = P['model'].objects.select_related(
                'parent', 'asset', 'qset', 'pgroup',
                'people', 'job', 'client', 'bu',
                'ticketcategory'
            ).filter(parent_id = obj.id).values(
                'asset__assetname', 'asset__id', 'qset__id', 'ctzoffset',
                'qset__qsetname', 'plandatetime', 'expirydatetime',
                'gracetime', 'seqno', 'jobstatus', 'id').order_by('seqno')

        except Exception:
            logger.critical("something went wrong", exc_info = True)
            raise

        else:
            logger.info("checkpoints retrieved returned success")
        return checkpoints


class JobneedExternalTours(LoginRequiredMixin, View):
    params = {
        'model'        : Jobneed,
        'template_path': 'schedhuler/e_tourlist_jobneed.html',
        'template_form': 'schedhuler/e_tourform_jobneed.html',
        'fields'       : ['jobdesc', 'people__peoplename', 'pgroup__groupname', 'id', 'ctzoffset','bu__buname', 'bu__solid',
            'plandatetime', 'expirydatetime', 'jobstatus', 'gracetime', 'performedby__peoplename', 'seqno', 'qset__qsetname',
            'attachmentcount'],
        'related': ['pgroup',  'ticketcategory', 'asset', 'client',
             'job', 'qset', 'people', 'parent', 'bu'],
        'form_class': scd_forms.E_TourFormJobneed,
        'initial'   : {
            'identifier': Jobneed.Identifier.EXTERNALTOUR,
            'frequency' : Jobneed.Frequency.NONE
        }
    }

    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # first load the template
        if R.get('template'): return render(request, P['template_path'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = P['model'].objects.get_externaltourlist_jobneed(request, P['related'], P['fields'])
            return rp.JsonResponse(data = {'data':list(objs)})
        
        if R.get('action') == "checkpoints":    
            objs = P['model'].objects.get_ext_checkpoints_jobneed(request, P['related'], P['fields'])
            return rp.JsonResponse(data = {'data':list(objs)})
        
        if R.get('action') == 'checklist_details' and R.get('jobneedid'):
            objs = JobneedDetails.objects.get_e_tour_checklist_details(R['jobneedid'])
            return rp.JsonResponse(data = {'data':list(objs)})
        
        if R.get('action') == 'getAttachmentJobneed' and R.get('id'):
            att = P['model'].objects.getAttachmentJobneed(R['id'])
            return rp.JsonResponse(data = {'data':list(att)})
        
        if R.get('action') == 'getAttachmentJND' and R.get('id'):
            att = JobneedDetails.objects.getAttachmentJND(R['id'])
            return rp.JsonResponse(data = {'data': list(att)})
        
        if R.get('id'):
            obj = P['model'].objects.get(id = R['id'])  
            form = P['form_class'](instance = obj, initial = P['initial'])
            logger.info("object retrieved %s", (obj.jobdesc))
            checkpoints = self.get_checkpoints(P, obj = obj)
            cxt = {'externaltourform': form, 'edit': True,
                'checkpoints': checkpoints}
            return render(request, P['template_form'], context = cxt)
        
    @staticmethod
    def get_checkpoints(P, obj):
        logger.info("getting checkpoints for the internal tour [start]")
        checkpoints = None

        try:
            checkpoints = P['model'].objects.select_related(
                'parent', 'asset', 'qset', 'pgroup',
                'people', 'job', 'client', 'bu',
                'ticketcategory','gpslocation'
            ).annotate(bu__gpslocation=AsGeoJSON('bu__gpslocation'),gps = AsGeoJSON('gpslocation')).filter(parent_id = obj.id).values(
                'asset__assetname', 'asset__id', 'qset__id',
                'qset__qsetname', 'plandatetime', 'expirydatetime', 'bu__gpslocation','gps',
                'gracetime', 'seqno', 'jobstatus', 'id').order_by('seqno')

        except Exception:
            logger.critical("something went wrong", exc_info = True)
            raise

        else:
            logger.info("checkpoints retrieved returned success")
        return checkpoints

class JobneedTasks(LoginRequiredMixin, View):
    params = {
        'model'        : Jobneed,
        'model_jnd'        : JobneedDetails,
        'template_path':  'schedhuler/tasklist_jobneed.html',
        'fields': [
                'jobdesc', 'people__peoplename', 'pgroup__groupname', 'id',
                'plandatetime', 'expirydatetime', 'jobstatus', 'gracetime','asset__assetname',
                'performedby__peoplename', 'asset__assetname', 'qset__qsetname','bu__buname', 'bu__bucode',
                'ctzoffset', 'assignedto', 'jobtype', 'ticketcategory__taname', 'other_info__isAcknowledged'],
        'related': [
                'pgroup',  'ticketcategory', 'asset', 'client','ctzoffset',
                'frequency', 'job', 'qset', 'people', 'parent', 'bu'],
        'template_form': 'schedhuler/taskform_jobneed.html',
        'form_class':scd_forms.TaskFormJobneed
    }

    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params

        # first load the template
        if R.get('template'): return render(request, P['template_path'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            draw = int(request.GET.get("draw", 1))
            start = int(request.GET.get("start", 0))
            length = int(request.GET.get("length", 10))
            search_value = request.GET.get("search[value]", "").strip()

            order_col = request.GET.get('order[0][column]')
            order_dir = request.GET.get('order[0][dir]')
            column_name = request.GET.get(f'columns[{order_col}][data]')

            objs = P['model'].objects.get_task_list_jobneed(
                P['related'], P['fields'], request)
            
            if search_value:
                objs = objs.filter(
                    Q(jobdesc__icontains=search_value)|
                    Q(jobstatus__icontains=search_value)|
                    Q(bu__buname__icontains = search_value)|
                    Q(bu__bucode__icontains = search_value)|
                    Q(qset__qsetname__icontains = search_value)|
                    Q(asset__assetname__icontains = search_value)
                )
            if column_name:
                order_prefix = '' if order_dir == 'asc' else '-'
                objs = objs.order_by(f'{order_prefix}{column_name}')

            total = objs.count()
            paginated = objs[start:start+length]
            data = list(paginated)
            return rp.JsonResponse({
                "draw": draw,
                "recordsTotal": total,
                "recordsFiltered": total,
                "data": data,
            }, status=200)
        
        if R.get('action') == 'getAttachmentJND':
            att =  P['model_jnd'].objects.getAttachmentJND(R['id'])
            return rp.JsonResponse(data = {'data': list(att)})

        
        if R.get('action') == 'get_task_details' and R.get('taskid'):
            objs = P['model_jnd'].objects.get_task_details(R['taskid'])
            return rp.JsonResponse({"data":list(objs)})
        
        if R.get('action') == 'acknowledgeAutoCloseTask':
            obj = P['model'].objects.filter(id = R['id']).first()
            obj.other_info['isAcknowledged'] = True
            obj.other_info['acknowledged_by'] = request.user.peoplecode
            obj.save()  
            objs = P['model'].objects.get_task_list_jobneed(P['related'], P['fields'], request, obj.id)
            return rp.JsonResponse({'row':objs[0]}, status = 200)
            
        # load form with instance
        if R.get('id'):
            obj = utils.get_model_obj(int(R['id']), request, P)
            cxt = {'taskformjobneed':P['form_class'](request = request, instance = obj),
                    'edit':True}
            return render(request, P['template_form'], context = cxt)

class SchdTasks(LoginRequiredMixin, View):
    params={
        'model'        : Job,
        'template_path': 'schedhuler/schd_tasklist_job.html',
        'fields'       : ['jobname', 'people__peoplename', 'pgroup__groupname',
                        'fromdate', 'uptodate', 'qset__qsetname', 'asset__assetname',
                        'planduration', 'gracetime', 'expirytime', 'id', 'ctzoffset',
                        'assignedto', 'bu__buname', 'bu__bucode'],
        'related'      : ['pgroup', 'people', 'asset', 'bu'],
        'form_class': scd_forms.SchdTaskFormJob,
        'template_form': 'schedhuler/schd_taskform_job.html',
        'initial': {
                'starttime'   : time(00, 00, 00),
                'endtime'     : time(00, 00, 00),
                'fromdate'   : datetime.combine(date.today(), time(00, 00, 00)),
                'uptodate'   : datetime.combine(date.today(), time(23, 00, 00)) + timedelta(days = 2),
                'identifier'  : Job.Identifier.TASK,
                'frequency'   : Job.Frequency.NONE,
                'scantype'    : Job.Scantype.QR,
                'priority'    : Job.Priority.LOW,
                'planduration': 0,
                'gracetime'   : 0,
                'expirytime'  : 0
            }
    }
    @method_decorator(cache_page(3))
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # first load the template
        if R.get('template'): return render(request, P['template_path'])

        # then load the table with objects for table_view
        if R.get('action') == 'list':
            logger.info('Retrieve Tasks view')
            objects = P['model'].objects.get_scheduled_tasks(request, P['related'], P['fields'])
            logger.info(f'Tasks objects {len(objects)} retrieved from db' if objects else "No Records!")
            return rp.JsonResponse(data = {'data':list(objects)})

        # load form with instance
        if R.get('id'):
            obj = utils.get_model_obj(int(R['id']), request, P)
            cxt = {'schdtaskform':P['form_class'](request = request, instance = obj),
                    'edit':True}
            return render(request, P['template_form'], context = cxt)

        # return empty form
        if R.get('action') == 'form':
            cxt = {
            'schdtaskform':P['form_class'](initial = P['initial'], request = request)
            }
            return render(request, P['template_form'], context = cxt)

        if R.get('runscheduler'):
            # run job scheduler
            pass

    def post(self, request, *args, **kwargs):
        R = request.POST
        logger.info('Task form submitted')
        data, create = QueryDict(R['formData']), True
        utils.display_post_data(data)
        if pk := R.get('pk', None):
            obj = utils.get_model_obj(pk, request, {'model': self.params['model']})
            form = self.params['form_class'](
                instance = obj, data = data, request = request)
            logger.info("retrieved existing task whose jobname:= '%s'", (obj.jobname))
        else:
            form = self.params['form_class'](data = data, request = request)
            logger.info("new task submitted following is the form-data:\n%s\n", (pformat(form.data)))
        response = None
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                if form.is_valid():
                    response = self.process_valid_schd_taskform(request, form)
                else:
                    response = self.process_invalid_schd_taskform(
                        form)
        except Exception:
            logger.critical(
                "failed to process form, something went wrong", exc_info = True)
            response = rp.JsonResponse(
                {'errors': 'Failed to process form, something went wrong'}, status = 404)
        return response

    @staticmethod
    def process_valid_schd_taskform(request, form):
        resp = None
        logger.info("task form processing/saving [ START ]")
        try:
            job         = form.save(commit = False)
            job.parent_id  = 1
            job.save()
            job = putils.save_userinfo(job, request.user, request.session)
            logger.info('task form saved success...')
        except IntegrityError as ex:
            return utils.handle_intergrity_error("Task")
        except Exception as ex:
            logger.critical("task form is processing failed", exc_info = True)
            resp = rp.JsonResponse(
                {'error': "saving schd_taskform failed..."}, status = 404)
            raise ex from ex
        else:
            logger.info("task form is processed successfully")
            resp = rp.JsonResponse({'jobname': job.jobname,
                'url': f'{reverse("schedhuler:jobschdtasks")}?id={job.id}'},
                status = 200)
        logger.info("task form processing/saving [ END ]")
        return resp

    @staticmethod
    def process_invalid_schd_taskform(form):
        logger.info(
            "processing invalidt task form sending errors to the client [ START ]")
        cxt = {"errors": form.errors}
        logger.info(
            "processing invalidt task form sending errors to the client [ END ]")
        return rp.JsonResponse(cxt, status = 404)


class InternalTourScheduling(LoginRequiredMixin, View):
    params = {
        'template_form': 'schedhuler/schd_i_tourform_job.html',
        'template_list': 'schedhuler/schd_i_tourlist_job.html',
        'form_class'   : scd_forms.Schd_I_TourJobForm,
        'subform'      : scd_forms.SchdChild_I_TourJobForm,
        'model'        : Job,
        'related'      : ['pgroup', 'people', 'bu'],
        'initial'      : {
            'starttime' : time(00, 00, 00),
            'endtime'   : time(00, 00, 00),
            'expirytime': 0,
            'identifier': Job.Identifier.INTERNALTOUR,
            'priority'  : Job.Priority.LOW,
            'scantype'  : Job.Scantype.QR,
            'gracetime' : 0,
            'planduration' : 0
        },
        'fields'       : ['id', 'jobname', 'people__peoplename', 'pgroup__groupname', 'fromdate', 'uptodate',
                        'planduration', 'gracetime', 'expirytime', 'assignedto', 'bu__bucode', 'bu__buname',
                        'ctzoffset']
    }

    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # return template
        if R.get('template') == 'true':
            return render(request, P['template_list'])
        
        if R.get('action') == 'loadTourCheckpoints':
            if R['parentid'] != 'None':
                objs = P['model'].objects.filter(parent_id = R['parentid']).select_related('asset', 'qset').values(
                    'pk', 'qset__qsetname', 'asset__assetname', 'seqno', 'expirytime', 'asset_id', 'qset_id'
                ).order_by('seqno')
            else: objs = P['model'].objects.none()
            return rp.JsonResponse({'data':list(objs)})
        
        if R.get('action') == 'loadAssetChekpointsForSelectField':
            objs = Asset.objects.get_asset_checkpoints_for_tour(request)
            return rp.JsonResponse({'items':list(objs), 'total_count':len(objs)}, status = 200)
        
        if R.get('action') == 'loadQuestionSetsForSelectField':
            objs = QuestionSet.objects.get_qsets_for_tour(request)
            return rp.JsonResponse({'items':list(objs), 'total_count':len(objs)}, status = 200)

        if R.get('id'):
            obj = utils.get_model_obj(int(R['id']), request, P)
            logger.info(f'object retrieved {obj}')
            form        = P['form_class'](instance = obj, request=request)
            cxt = {'schdtourform': form, 'edit': True,
                   }
            return render(request, P['template_form'], cxt)
        
        # return resp to delete request
        if R.get('action', None) == "delete" and R.get('id', None):
            return utils.render_form_for_delete(request, self.params, False)
        
        if R.get('action') == 'list':
            objs = P['model'].objects.get_scheduled_internal_tours(
                request, P['related'], P['fields']
            )
            return rp.JsonResponse({'data':list(objs)}, status = 200)
        
        if R.get('action') == 'form':
            cxt = {'schdtourform':P['form_class'](request = request, initial = P['initial'])}
            return render(request, P['template_form'], cxt)

    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.params
        pk, data = request.POST.get('pk', None), QueryDict(request.POST.get('formData'))
        if R.get('postType') == 'saveCheckpoint':
            data = P['model'].objects.handle_save_checkpoint_guardtour(request)
            return rp.JsonResponse(data, status = 200, safe=False)
        try:
            if pk:
                msg = 'internal scheduler tour'
                form = utils.get_instance_for_update(
                    data, P, msg, int(pk), kwargs = {'request':request})
                self.updatecheckpoints(pk)
            else:
                form = P['form_class'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp


    def handle_valid_form(self, form, request):
        data = request.POST.get("asssigned_checkpoints")
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                assigned_checkpoints = json.loads(data)
                job = form.save(commit = False)
                job.parent_id = job.asset_id = job.qset_id = 1
                job.other_info['istimebound'] = form.cleaned_data['istimebound']
                job.other_info['isdynamic'] = form.cleaned_data['isdynamic']
                job.save()
                job = putils.save_userinfo(job, request.user, request.session)
                logger.info('guard tour  and its checkpoints saved success...')
                return rp.JsonResponse({'jobname': job.jobname,
                    'url': f'{reverse("schedhuler:schd_internal_tour")}?id={job.id}'},
                    status = 200)
        except NotNullViolation as e:
            error_logger.error("Not null error catched")
        except IntegrityError as ex:
            return utils.handle_intergrity_error("Tour")
        except Exception as ex:
            logger.critical("error handling valid form", exc_info = True)
            raise ex

    def updatecheckpoints(self, pk):
        job = Job.objects.get(id=pk)
        updated = Job.objects.filter(
            parent_id=pk).update(
                people_id=job.people_id, pgroup_id=job.pgroup_id)
        logger.info("checkpoints also updated according to parent record %s"%(updated))



    # def save_checpoints_for_tour(self, checkpoints, job, request):
    #     try:
    #         logger.info(f"saving Checkpoints found {len(checkpoints)} [started]")
    #         CP = {}
    #         job = Job.objects.filter(id = job.id).values()[0]
    #         self.params['model'].objects.filter(parent_id = job['id']).delete()
    #         count=0
    #         for cp in checkpoints:
    #             CP['expirytime'] = cp[5]
    #             CP['qsetname'] = cp[4]
    #             CP['assetid']    = cp[1]
    #             CP['qsetid']     = cp[3]
    #             CP['seqno']       = cp[0]
    #             obj = Job.objects.create(
    #                 **sutils.job_fields(job, CP)
    #             )
    #             putils.save_userinfo(obj, request.user, request.session)
    #             count+=1
    #         if count == len(checkpoints):
    #             logger.info('all checkpoints saved successfully')
    #     except Exception as ex:
    #         error_logger.error(
    #             "failed to insert checkpoints, something went wrong", exc_info = True)
    #         raise ex
    #     else:
    #         logger.info("inserting checkpoints finished...")

    # @staticmethod
    # def get_checkpoints(obj, P):
    #     logger.info("getting checkpoints started...")
    #     checkpoints = None
    #     try:
    #         checkpoints = P['model'].objects.select_related(
    #             'parent', 'asset', 'qset', 'pgroup',
    #             'people',
    #         ).filter(parent_id = obj.id).annotate(
    #             assetname = F('asset__assetname'),
    #             qsetname = F('qset__qsetname')
    #             ).values(
    #             'seqno',
    #             'assetname',
    #             'asset_id',
    #             'qsetname',
    #             'qset_id',
    #             'expirytime',
    #             'id')
    #     except Exception:
    #         logger.critical("something went wrong", exc_info = True)
    #         raise
    #     else:
    #         logger.info("checkpoints retrieved returned success")
    #     return checkpoints


class ExternalTourScheduling(LoginRequiredMixin, View):
    params = {
        'template_form': 'schedhuler/schd_e_tourform_job.html',
        'template_list': 'schedhuler/schd_e_tourlist_job.html',
        'form_class'   : scd_forms.Schd_E_TourJobForm,
        'model'        : Job,
        'related'      : ['pgroup', 'people'],
        'initial'      : {
            'seqno':-1,
            'identifier': Job.Identifier.EXTERNALTOUR,
            'scantype':Job.Scantype.QR,
            'starttime':time(00,00,00),
            'endtime':time(00,00,00),
            'priority':Job.Priority.HIGH,
            'expirytime':0,
            'gracetime' : 0,
            'planduration' : 0,
            'pgroup':1
        },
        'fields' : ['id', 'jobname', 'people__peoplename', 'pgroup__groupname', 'fromdate', 'uptodate',
                'planduration', 'gracetime', 'expirytime', 'bu__buname', 'assignedto']
    }


    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params


        # return template first
        if R.get('template') == 'true':
            return render(request, P['template_list'])
        
        # return resp for for list view
        if R.get('action') == 'list':
            objs = P['model'].objects.get_listview_objs_schdexttour(request)
            return rp.JsonResponse({'data':list(objs)}, status = 200)
        
        # return resp for job creation 
        if R.get('action') == 'form':
            cxt = {'schdexternaltourform': P['form_class'](
            request = request, initial = P['initial'])}
            return render(request, P['template_form'], context = cxt)
        
        # return resp to populate the sites from sitgroup 
        if R.get('action') == "get_sitesfromgroup":
            if R['id'] == 'None': return rp.JsonResponse({'data':[]}, status = 200)
            job = Job.objects.filter(id = int(R['id'])).values(*utils.JobFields.fields)[0]
            objs = pm.Pgbelonging.objects.get_sitesfromgroup(job)
            return rp.JsonResponse({'data':list(objs)}, status = 200)

        if R.get('action') == "forcegetfromgroup" and R.get('sgroup_id')!='None' and R.get('id')!='None':
            job = Job.objects.filter(id = int(R['id'])).values(*utils.JobFields.fields)[0]
            objs = pm.Pgbelonging.objects.get_sitesfromgroup(job, force=True)
            return rp.JsonResponse({'rows':list(objs)}, status = 200)
        
        # return resp to load checklist
        if R.get('action') == "loadChecklist":
            qset =  QuestionSet.objects.load_checklist(request)
            return rp.JsonResponse({'items':list(qset), 'total_count':len(qset)}, status = 200)
        
        # return resp to delete request
        if R.get('action', None) == "delete" and R.get('id', None):
            return utils.render_form_for_delete(request, self.params, False)
        
        # return resp for updation of job
        if R.get('id'):
            obj = utils.get_model_obj(int(R['id']), request, P)
            initial = {'israndom':obj.other_info['is_randomized'],
                       'tourfrequency':obj.other_info['tour_frequency'],
                       'breaktime':obj.other_info['breaktime']}     #obj.other_info['breaktime']}
            cxt = {'schdexternaltourform': P['form_class'](instance=obj, request = request, initial=initial)}
            return render(request, P['template_form'], context = cxt)
        




    def post(self, request, *args, **kwargs):
        P = self.params
        pk, R = request.POST.get('pk', None), request.POST
        formData = QueryDict(request.POST.get('formData'))
        try:
            if R.get('postType') == 'saveCheckpoint':
                data =  Job.objects.handle_save_checkpoint_sitetour(request)
                return rp.JsonResponse(data, status = 200, safe=False)
            if R.get('action')=='saveCheckpoints':
                checkpoints =  json.loads(R.get('checkpoints'))
                return self.saveCheckpointsinJob(R, checkpoints, P, request)
            if pk:
                msg = 'external scheduler tour'
                form = utils.get_instance_for_update(
                    formData, P, msg, int(pk), kwargs = {'request':request})
            else:
                form = P['form_class'](formData, request=request)
            if form.is_valid():
                return self.handle_valid_form(form, request, P)
            cxt = {'errors': form.errors}
            return utils.handle_invalid_form(request, self.params, cxt)
        except Exception as ex:
            return utils.handle_Exception(request)



    @staticmethod
    def handle_valid_form(form, request, P):
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                job = form.save(commit=False)
                if request.POST.get('pk'):
                    Job.objects.filter(parent_id = job.id).update(
                        qset_id = job.qset_id,
                        people_id= job.people_id,
                        pgroup_id=job.pgroup_id)
                if not request.POST.get('pk'):
                    job.other_info['tour_frequency'] = form.cleaned_data['tourfrequency']
                    job.other_info['is_randomized'] = form.cleaned_data['israndom']
                    job.other_info['breaktime'] = form.cleaned_data['breaktime']
                job.save()
                job = putils.save_userinfo(job, request.user,request.session)
                #self.save_checkpoints_injob_fromgroup(job, P)
                return rp.JsonResponse({'pk':job.id}, status = 200)
        except IntegrityError as ex:
            return utils.handle_intergrity_error("Task")
        except Exception as ex:
            logger.critical("external tour form, handle valid form failed", exc_info = True)
            return utils.handle_Exception(request)

        
    @staticmethod
    def saveCheckpointsinJob(R, checkpoints, P, request):
        try:
            job = Job.objects.filter(id = int(R['job_id'])).values()[0]
            P['model'].objects.filter(parent_id = job['id']).delete()
            count=0
            for cp in checkpoints:
                obj = Job.objects.create(
                    **sutils.job_fields(job, cp, external=True))
                putils.save_userinfo(obj, request.user, request.session, bu=cp['buid'])
                count+=1
            if count == len(checkpoints):
                objs = P['model'].objects.get_sitecheckpoints_exttour(job)
                return rp.JsonResponse({'count':count, 'data':list(objs)}, status = 200 )
            return rp.JsonResponse({"error":"Checkpoints not saved"}, status = 400)
        except Exception:
            logger.critical("something went wrong...", exc_info=True)
            raise

class JobneednJNDEditor(LoginRequiredMixin, View):
    params = {
        'model':Jobneed,
        'jnd':JobneedDetails,
        'fields':['id', 'quesname', 'answertype', 'min', 'max', 'options', 'alerton',
                  'ismandatory']
    }
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        if R.get('action') == 'get_jndofjobneed' and R.get('jobneedid'):
            objs = P['jnd'].objects.get_jndofjobneed(R)
            return rp.JsonResponse({'data':list(objs)}, status=200)
        return rp.JsonResponse({'data':[]}, status=200)
    
    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.params
        if R.get('tourjobneed'):
            data = P['model'].objects.handle_jobneedpostdata(request)
            return rp.JsonResponse({'data':list(data)}, status = 200, safe=False)
        if R.get('question'):
            data = P['qsb'].objects.handle_questionpostdata(request)
            return rp.JsonResponse({'data':list(data)}, status = 200, safe=False)



class ExternalTourTracking(LoginRequiredMixin, View):
    model = Jobneed
    template = 'schedhuler/site_tour_tracking.html'
    
    def get(self,  request, *args, **kwargs):
        R = request.GET
        if R.get('action') == 'get_checkpoints':
            checkpoints, info, path, latestloc = self.model.objects.get_latlng_of_checkpoints(R['jobneed_id'])
            return rp.JsonResponse(
                {'checkpoints':checkpoints, 'info':info, 'path':path, 'latestloc':latestloc}, status=200, safe=False)
        return render(request, self.template, {'jobneed_id':R['jobneed_id']})