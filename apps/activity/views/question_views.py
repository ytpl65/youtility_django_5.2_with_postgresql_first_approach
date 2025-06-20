import logging
from pprint import pformat
import psycopg2.errors as pg_errs

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction

from django.http import Http404,QueryDict
from django.http import response as rp
from django.shortcuts import render
from django.views.generic.base import View

import apps.activity.filters as aft
from apps.activity.forms.question_form import QuestionForm,ChecklistForm,QsetBelongingForm
from apps.activity.forms.asset_form import CheckpointForm
from apps.activity.models.question_model import QuestionSet, QuestionSetBelonging,Question
from apps.activity.models.asset_model import Asset
import apps.activity.utils as av_utils
import apps.peoples.utils as putils
from apps.core import utils

logger = logging.getLogger('django')


# Create your views here.
class Question(LoginRequiredMixin, View):
    params = {
        'form_class'   : QuestionForm,
        'template_form': 'activity/partials/partial_ques_form.html',
        'template_list': 'activity/question.html',
        'partial_form' : 'peoples/partials/partial_ques_form.html',
        'partial_list' : 'peoples/partials/partial_people_list.html',
        'related'      : ['unit'],
        'model'        : Question,
        'filter'       : aft.QuestionFilter,
        'fields'       : ['id', 'quesname', 'answertype', 'isworkflow', 'unit__tacode', 'cdtz', 'cuser__peoplename' ],
        'form_initials': {
        'answertype'   : Question.AnswerType.DROPDOWN,
        'category'     : 1,                               
        'unit': 1}
    }

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        # return cap_list data
        if R.get('template'): return render(request, self.params['template_list'])
        if R.get('action', None) == 'list':
            objs = self.params['model'].objects.questions_listview(request, self.params['fields'], self.params['related'])
            return  rp.JsonResponse(data = {'data':list(objs)})
            

        # return cap_form empty
        elif R.get('action', None) == 'form':
            cxt = {'ques_form': self.params['form_class'](request = request, initial = self.params['form_initials']),
                   'msg': "create question requested"}
            resp = utils.render_form(request, self.params, cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params, True)
        # return form with instance
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            resp = utils.render_form_for_update(
                request, self.params, 'ques_form', obj)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            data = QueryDict(request.POST['formData']).copy()
            if pk := request.POST.get('pk', None):
                msg = "question_view"
                ques = utils.get_model_obj(pk, request, self.params)
                form = self.params['form_class'](
                    data, instance = ques, request = request)
                create = False
            else:
                form = self.params['form_class'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form,  request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form,  request, create):
        logger.info('ques form is valid')
        ques = None
        from apps.activity.models.question_model import Question
        try:
            ques = form.save()
            ques = putils.save_userinfo(
                ques, request.user, request.session, create = create)
            logger.info("question form saved")
            data = {'msg': f"{ques.quesname}",
            'row': Question.objects.values(*self.params['fields']).get(id = ques.id)}
            return rp.JsonResponse(data, status = 200)
        except (IntegrityError, pg_errs.UniqueViolation):
            return utils.handle_intergrity_error('Question')



class QuestionSet(LoginRequiredMixin, View):
    params = {
        'form_class'   : ChecklistForm,
        'template_form': 'activity/questionset_form.html',
        'template_list' : 'activity/questionset_list.html',
        'related'      : ['unit', 'bu'],
        'model'        : QuestionSet,
        'filter'       : aft.MasterQsetFilter,
        'fields'       : ['qsetname', 'type', 'id', 'ctzoffset', 'cdtz', 'mdtz', 'bu__bucode', 'bu__buname'],
        'form_initials': { 'type':'CHECKLIST'}
    }
    
    def get(self, request, *args, **kwargs):
        R, P, resp = request.GET, self.params, None
        # first load the template
        if R.get('template'):
            return render(request, P['template_list'])

        # return qset_list data
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = self.params['model'].objects.checklist_listview(request, P['fields'], P['related'])
            return  rp.JsonResponse(data = {'data':list(objs)})

        # return questionset_form empty
        if R.get('action', None) == 'form':
            cxt = {'checklistform': self.params['form_class'](request=request, initial=self.params['form_initials']),
                   'qsetbng': QsetBelongingForm(initial={'ismandatory': True}), 'msg': "create checklist form requested"}

            resp = render(request, self.params['template_form'], context = cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params, False)

        elif R.get('id', None):
            logger.info('detail view requested')
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            cxt = {'checklistform': self.params['form_class'](request = request, instance = obj)}
            resp = render(request, self.params['template_form'], context = cxt)
        return resp
    
    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            data = QueryDict(request.POST['formData'])
            if pk := request.POST.get('pk', None):
                msg = 'checklist'
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), {'request':request})
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
    def get_questions_for_form(qset):
        try:
            questions = list(QuestionSetBelonging.objects.select_related(
                "question").filter(qset_id = qset).values(
                'ismandatory', 'seqno', 'max', 'min', 'alerton','isavpt', 'avpttype',
                'options', 'question__quesname', 'answertype', 'question__id'
            ))
        except Exception:
            logger.critical("Something went wrong", exc_info = True)
            raise
        else:
            return questions


    def handle_valid_form(self, form, request, create):
        logger.info('checklist form is valid')
        try:
            with transaction.atomic(using=utils.get_current_db_name()):
                # assigned_questions = json.loads(
                #     request.POST.get("asssigned_questions"))
                qset = form.save()
                putils.save_userinfo(qset, request.user,
                                    request.session, create = create)
                logger.info('checklist form is valid')
                fields = {'qset': qset.id, 'qsetname': qset.qsetname,
                        'client': qset.client_id}
                #self.save_qset_belonging(request, assigned_questions, fields)
                data = {'success': "Record has been saved successfully",
                        'parent_id':qset.id
                        }
                return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return utils.handle_intergrity_error('Question Set')

    @staticmethod
    def save_qset_belonging(request, assigned_questions, fields):
        try:
            logger.info("saving QuestoinSet Belonging [started]")
            logger.info(f'{" " * 4} saving QuestoinSet Belonging found {len(assigned_questions)} questions')
            av_utils.insert_questions_to_qsetblng(
                assigned_questions, QuestionSetBelonging, fields, request)
            logger.info("saving QuestionSet Belongin [Ended]")
        except Exception:
            logger.critical("Something went wrong", exc_info = True)
            raise

def deleteQSB(request):
    if request.method != 'GET':
        return Http404

    status = None
    try:
        quesname = request.GET.get('quesname')
        answertype = request.GET.get('answertype')
        qset = request.GET.get('qset')
        logger.info("request for delete QSB '%s' start", (quesname))
        QuestionSetBelonging.objects.get(
            question__quesname = quesname,
            answertype = answertype,
            qset_id = qset).delete()
        statuscode = 200
        logger.info("Delete request executed successfully")
    except Exception:
        logger.critical("something went wrong", exc_info = True)
        statuscode = 404
        raise
    status = "success" if statuscode == 200 else "failed"
    data = {"status": status}
    return rp.JsonResponse(data, status = statuscode)




class QsetNQsetBelonging(LoginRequiredMixin, View):
    params = {
        'model1':QuestionSet,
        'qsb':QuestionSetBelonging,
        'fields':['id', 'quesname', 'answertype', 'min', 'max', 'options', 'alerton',
                  'ismandatory', 'isavpt', 'avpttype']
    }
    def get(self, request, *args, **kwargs):
        from apps.activity.models.question_model import Question
        R, P = request.GET, self.params
        if(R.get('action') == 'loadQuestions'):
            qset =  Question.objects.questions_of_client(request, R)
            return rp.JsonResponse({'items':list(qset), 'total_count':len(qset)}, status = 200)

        if(R.get('action') == 'getquestion') and R.get('questionid') not in [None, 'null']:
            objs = Question.objects.get_questiondetails(R['questionid'])
            return rp.JsonResponse({'qsetbng':list(objs)}, status=200)
        
        if R.get('action') == 'get_questions_of_qset':
            objs = P['qsb'].objects.get_questions_of_qset(R)
            return rp.JsonResponse({'data':list(objs)}, status=200)

        
    
    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.params
        if R.get('questionset'):
            data = P['model1'].objects.handle_qsetpostdata(request)
            return rp.JsonResponse({'data':list(data)}, status = 200, safe=False)
        if R.get('question'):
            data = P['qsb'].objects.handle_questionpostdata(request)
            return rp.JsonResponse(data, status = 200, safe=False)
        
        

class Checkpoint(LoginRequiredMixin, View):
    params = {
        "form_class": CheckpointForm,
        "template_form": "activity/partials/partial_checkpoint_form.html",
        "template_list": "activity/checkpoint_list.html",
        "partial_form": "peoples/partials/partial_checkpoint_form.html",
        "partial_list": "peoples/partials/chekpoint_list.html",
        "related": ["parent", "type", "bu", "location"],
        "model": Asset,
        "fields": [
            "assetname",
            "assetcode",
            "runningstatus",
            "identifier",
            "location__locname",
            "parent__assetname",
            "gps",
            "id",
            "enable",
            "bu__buname",
            "bu__bucode",
        ],
        "form_initials": {
            "runningstatus": "WORKING",
            "identifier": "CHECKPOINT",
            "iscritical": False,
            "enable": True,
        },
    }

    def get(self, request, *args, **kwargs):
        R, resp, P = request.GET, None, self.params

        # first load the template
        if R.get("template"):
            return render(request, P["template_list"], {"label": "Checkpoint"})
        # return qset_list data
        if R.get("action", None) == "list":
            objs = P["model"].objects.get_checkpointlistview(
                request, P["related"], P["fields"]
            )
            return rp.JsonResponse(data={"data": list(objs)})

        if (
            R.get("action", None) == "qrdownload"
            and R.get("code", None)
            and R.get("name", None)
        ):
            return utils.download_qrcode(
                R["code"], R["name"], "CHECKPOINTQR", request.session, request
            )

        # return questionset_form empty
        if R.get("action", None) == "form":
            P["form_initials"].update({"type": 1, "parent": 1})
            cxt = {
                "master_assetform": P["form_class"](
                    request=request, initial=P["form_initials"]
                ),
                "msg": "create checkpoint requested",
                "label": "Checkpoint",
            }

            resp = utils.render_form(request, P, cxt)

        elif R.get("action", None) == "delete" and R.get("id", None):
            resp = utils.render_form_for_delete(request, P, True)
        elif R.get("id", None):
            obj = utils.get_model_obj(int(R["id"]), request, P)
            cxt = {"label": "Checkpoint"}
            resp = utils.render_form_for_update(
                request, P, "master_assetform", obj, extra_cxt=cxt
            )
        return resp

    def post(self, request, *args, **kwargs):
        resp, create, P = None, False, self.params
        try:
            data = QueryDict(request.POST["formData"])
            if pk := request.POST.get("pk", None):
                msg = "Checkpoint_view"
                form = utils.get_instance_for_update(
                    data, P, msg, int(pk), kwargs={"request": request}
                )
                create = False
            else:
                form = P["form_class"](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {"errors": form.errors}
                resp = utils.handle_invalid_form(request, P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        logger.info("checkpoint form is valid")
        P = self.params
        try:
            cp = form.save(commit=False)
            cp.gpslocation = form.cleaned_data["gpslocation"]
            putils.save_userinfo(cp, request.user, request.session, create=create)
            logger.info("checkpoint form saved")
            data = {
                "msg": f"{cp.assetcode}",
                "row": Asset.objects.get_checkpointlistview(
                    request, P["related"], P["fields"], id=cp.id
                ),
            }
            return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return utils.handle_intergrity_error("Checkpoint")

