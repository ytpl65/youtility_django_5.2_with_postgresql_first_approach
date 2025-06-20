from django.db.utils import IntegrityError
from django.db import transaction
from django.forms import model_to_dict
from django.http.request import QueryDict
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import response as rp
from django.shortcuts import redirect, render
from django.views import View
from django.http import response as rp
import logging
from apps.onboarding.models import  Bt
# Rate limiting now handled by PostgreSQLRateLimitMiddleware
# from apps.core.rate_limiting import rate_limit_login, record_failed_login, is_ip_blocked, is_username_blocked
from apps.peoples.filters import CapabilityFilter
from apps.core import utils
import apps.peoples.filters as pft
import apps.peoples.forms as pf  
import apps.peoples.models as pm  
import apps.onboarding.forms as obf 
from .models import Pgbelonging, Pgroup, People
from .utils import save_userinfo, save_pgroupbelonging
import apps.peoples.utils as putils
from django.contrib import messages
from .forms import PeopleForm, PeopleExtrasForm, LoginForm
from django_email_verification import send_email

logger = logging.getLogger("django")


class SignIn(View):
    template_path = "peoples/login.html"
    error_msgs = {
        "invalid-details": "Sorry that didn't work <br> please try again \
                            with the proper username and password.",
        "invalid-cookies": "Please enable cookies in your browser...",
        "auth-error": "Authentication failed of user with loginid = %s\
                            password = %s",
        "invalid-form": "sign in form is not valid...",
        "critical-error": "something went wrong please follow the traceback to fix it... ",
        "unauthorized-User" : "You are a Mobile User not authorized to \
                                 access the Web Application"
    }

    def get(self, request, *args, **kwargs):
        logger.info("SignIn View")
        request.session.set_test_cookie()
        form = LoginForm()
        return render(request, self.template_path, context={"loginform": form})

    # Rate limiting now handled by PostgreSQLRateLimitMiddleware automatically
    def post(self, request, *args, **kwargs):
        from .utils import display_user_session_info

        form, response = LoginForm(request.POST), None
        logger.info("form submitted")
        try:
            if not request.session.test_cookie_worked():
                logger.warning("cookies are not enabled in user browser", exc_info=True)
                form.add_error(None, self.error_msgs["invalid-cookies"])
                cxt = {"loginform": form}
                response = render(request, self.template_path, context=cxt)
            elif form.is_valid():
                logger.info("Signin form is valid")
                loginid = form.cleaned_data.get("username")
                password = form.cleaned_data.get("password")
                
                # Rate limiting is now handled by PostgreSQLRateLimitMiddleware
                # The middleware will block requests before they reach this view if rate limited
                # So we can proceed directly with authentication
                user = pm.People.objects.filter(loginid=loginid).values('people_extras__userfor')
                people = authenticate(request, username=loginid, password=password)
                logger.debug("People: %s", people)
                
                if people and user.exists() and (user[0]['people_extras__userfor'] in ['Web', 'Both']):
                    # Successful login
                    login(request, people)
                    request.session["ctzoffset"] = request.POST.get("timezone")
                    logger.info(
                        'Login Successful for people "%s" with loginid "%s" client "%s" site "%s"',
                        people.peoplename,
                        people.loginid,
                        people.client.buname if people.client else "None",
                        people.bu.buname if people.bu else "None",
                    )
                    utils.save_user_session(request, request.user)
                    display_user_session_info(request.session)
                    logger.info(f"User logged in {request.user.peoplecode}")
                    if request.session.get('bu_id') in [1, None]: 
                        response = redirect('peoples:no_site')
                    elif request.session.get('sitecode') not in ["SPSESIC", "SPSPAYROLL", "SPSOPS", "SPSOPERATION", "SPSHR"]:
                        response = redirect('onboarding:wizard_delete') if request.session.get('wizard_data') else redirect('onboarding:rp_dashboard')
                    elif request.session.get('sitecode') in ["SPSOPS"]:
                        response = redirect('reports:generateattendance')
                    elif request.session.get('sitecode') in ["SPSHR"]:
                        response = redirect('employee_creation:employee_creation')
                    elif request.session.get('sitecode') in ["SPSOPERATION"]:
                        response = redirect('reports:generate_declaration_form')
                    else:
                        response = redirect("reports:generatepdf")
                else:
                    # Failed login attempt - will be logged automatically by PostgreSQLRateLimitMiddleware
                    logger.warning(self.error_msgs["auth-error"], loginid, "********")
                    
                    if user.exists() and user[0]['people_extras__userfor'] == 'Mobile':
                        form.add_error(None, self.error_msgs["unauthorized-User"])
                    else:
                        form.add_error(None, self.error_msgs["invalid-details"])
                    
                    cxt = {"loginform": form}
                    response = render(request, self.template_path, context=cxt)
            else:
                logger.warning(self.error_msgs["invalid-form"])
                cxt = {"loginform": form}
                response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(self.error_msgs["critical-error"], exc_info=True)
            form.add_error(None, self.error_msgs["critical-error"])
            cxt = {"loginform": form}
            response = render(request, self.template_path, context=cxt)
        return response

    


class SignOut(LoginRequiredMixin, View):
    @staticmethod
    def get(request, *args, **kwargs):
        response = None
        try:
            logout(request)
            logger.info("User logged out DONE!")
            response = redirect("/")
        except Exception:
            logger.critical("unable to log out user", exc_info=True)
            messages.warning(request, "Unable to log out user...", "alert alert-danger")
            response = redirect("/dashboard")
        return response


class ChangePeoplePassword(LoginRequiredMixin, View):
    template_path = "peoples/people_form.html"
    form_class = PeopleForm
    json_form = PeopleExtrasForm
    model = People

    @staticmethod
    def post(request, *args, **kwargs):
        from django.contrib.auth.forms import SetPasswordForm
        from django.http import JsonResponse

        id, response = request.POST.get("people"), None
        people = People.objects.get(id=id)
        form = SetPasswordForm(people, request.POST)
        if form.is_valid():
            form.save()
            response = JsonResponse(
                {"res": "Password is changed successfully!", "status": 200}
            )
        else:
            response = JsonResponse({"res": form.errors, "status": 500})
        return response


def delete_master(request, params):
    raise NotImplementedError()


class Capability(LoginRequiredMixin, View):
    params = {
        "form_class": pf.CapabilityForm,
        "template_form": "peoples/partials/partial_cap_form.html",
        "template_list": "peoples/capability.html",
        "partial_form": "peoples/partials/partial_cap_form.html",
        "partial_list": "peoples/partials/partial_cap_list.html",
        "related": ["parent"],
        "model": pm.Capability,
        "filter": CapabilityFilter,
        "fields": ["id", "capscode", "capsname", "cfor", "parent__capscode"],
        "form_initials": {"initial": {}},
    }

    def get(self, request, *args, **kwargs):
        R, resp, objects, filtered = request.GET, None, [], 0

        # first load the template
        if R.get("template"):
            return render(request, self.params["template_list"])

        # return cap_list data
        if R.get("action", None) == "list" or R.get("search_term"):
            d = {"list": "cap_list", "filt_name": "cap_filter"}
            self.params.update(d)
            objs = (
                self.params["model"]
                .objects.select_related(*self.params["related"])
                .filter(~Q(capscode="NONE"))
                .values(*self.params["fields"])
            )
            resp = rp.JsonResponse(data={"data": list(objs)}, status=200, safe=False)

        # return cap_form empty
        elif R.get("action", None) == "form":
            cxt = {
                "cap_form": self.params["form_class"](request=request),
                "msg": "create capability requested",
            }
            resp = utils.render_form(request, self.params, cxt)

        # handle delete request
        elif R.get("action", None) == "delete" and R.get("id", None):
            resp = utils.render_form_for_delete(request, self.params, True)

        # return form with instance
        elif R.get("id", None):
            obj = utils.get_model_obj(int(R["id"]), request, self.params)
            resp = utils.render_form_for_update(request, self.params, "cap_form", obj)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            data = QueryDict(request.POST["formData"])
            pk = request.POST.get("pk", None)
            if pk:
                msg, create = "capability_view", False
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), {"request": request}
                )

            else:
                form = self.params["form_class"](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {"errors": form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)

        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        logger.info("capability form is valid")
        from apps.core.utils import handle_intergrity_error

        try:
            cap = form.save()
            putils.save_userinfo(cap, request.user, request.session, create=create)
            logger.info("capability form saved")
            data = {
                "success": "Record has been saved successfully",
                "row": pm.Capability.objects.values(*self.params["fields"]).get(
                    id=cap.id
                ),
            }
            return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return handle_intergrity_error("Capability")


class PeopleView(LoginRequiredMixin, View):
    params = {
        "form_class": pf.PeopleForm,
        "json_form": pf.PeopleExtrasForm,
        "template_form": "peoples/people_form.html",
        "template_list": "peoples/people_list.html",
        "related": ["peopletype", "bu"],
        "model": pm.People,
        "filter": pft.PeopleFilter,
        "fields": [
            "id",
            "peoplecode",
            "peoplename",
            "peopletype__taname",
            "bu__buname",
            "isadmin",
            "enable",
            "email",
            "mobno",
            "department__taname",
            "designation__taname",
        ],
        "form_initials": {"initial": {}},
    }

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        if R.get("template") == "true":
            return render(request, self.params["template_list"])

        # return cap_list data
        if R.get("action", None) == "list" or R.get("search_term"):
            draw = int(request.GET.get("draw", 1))
            start = int(request.GET.get("start", 0))
            length = int(request.GET.get("length", 10))
            search_value = request.GET.get("search[value]", "").strip()
            
            order_col = request.GET.get('order[0][column]')
            order_dir = request.GET.get('order[0][dir]')
            column_name = request.GET.get(f'columns[{order_col}][data]')

            objs = self.params["model"].objects.people_list_view(
                request, self.params["fields"], self.params["related"]
            )
            if search_value:
                objs = objs.filter(
                    Q(peoplename__icontains=search_value) |
                    Q(peoplecode__icontains=search_value) |
                    Q(department__taname__icontains=search_value) |
                    Q(bu__buname__icontains=search_value)
                )

            if column_name:
                order_prefix = '' if order_dir == 'asc' else '-'
                objs = objs.order_by(f'{order_prefix}{column_name}')

            total = objs.count()
            paginated = objs[start:start + length]
            data = list(paginated)        
            return rp.JsonResponse({
                "draw": draw,
                "recordsTotal": total,
                "recordsFiltered": total,
                "data": data,
            }, status=200)

        if (
            R.get("action", None) == "qrdownload"
            and R.get("code", None)
            and R.get("name", None)
        ):
            return utils.download_qrcode(
                R["code"], R["name"], "PEOPLEQR", request.session, request
            )

        # return cap_form empty
        if R.get("action", None) == "form":
            cxt = {
                "peopleform": self.params["form_class"](request=request),
                "pref_form": self.params["json_form"](request=request),
                "ta_form": obf.TypeAssistForm(auto_id=False, request=request),
                "msg": "create people requested",
            }
            resp = render(request, self.params["template_form"], cxt)

        # handle delete request
        elif R.get("action", None) == "delete" and R.get("id", None):
            resp = utils.render_form_for_delete(request, self.params, True)

        # return form with instance
        elif R.get("id", None):
            from .utils import get_people_prefform

            people = utils.get_model_obj(R["id"], request, self.params)
            cxt = {
                "peopleform": self.params["form_class"](
                    instance=people, request=request
                ),
                "pref_form": get_people_prefform(people, request),
                "ta_form": obf.TypeAssistForm(auto_id=False, request=request),
                "msg": "update people requested",
            }
            resp = render(request, self.params["template_form"], context=cxt)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        data = QueryDict(request.POST["formData"])
        try:
            if pk := request.POST.get("pk", None):
                msg, create = "people_view", False
                people = utils.get_model_obj(pk, request, self.params)
                form = self.params["form_class"](
                    data, files=request.FILES, instance=people, request=request
                )
            else:
                form = self.params["form_class"](data, request=request)
            jsonform = self.params["json_form"](data, request=request)
            if form.is_valid() and jsonform.is_valid():
                resp = self.handle_valid_form(form, jsonform, request, create)
            else:
                cxt = {"errors": form.errors}
                if jsonform.errors:
                    cxt["errors"] = jsonform.errors
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    @staticmethod
    def handle_valid_form(form, jsonform, request, create):
        logger.info("people form is valid")
        from apps.core.utils import handle_intergrity_error

        try:
            people = form.save()
            if request.FILES.get("peopleimg"):
                people.peopleimg = request.FILES["peopleimg"]
            if not people.password:
                people.set_password(form.cleaned_data["peoplecode"])
            if putils.save_jsonform(jsonform, people):
                buid = people.bu.id if people.bu else None
                people = putils.save_userinfo(
                    people, request.user, request.session, create=create, bu=buid
                )
                logger.info("people form saved")
            data = {"pk": people.id}
            return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return handle_intergrity_error("People")


class PeopleGroup(LoginRequiredMixin, View):
    params = {
        "form_class": pf.PeopleGroupForm,
        "template_form": "peoples/partials/partial_pgroup_form.html",
        "template_list": "peoples/peoplegroup.html",
        "partial_form": "peoples/partials/partial_pgroup_form.html",
        "related": ["identifier", "bu"],
        "model": pm.Pgroup,
        "fields": ["groupname", "enable", "id", "bu__buname", "bu__bucode"],
        "form_initials": {},
    }

    def get(self, request, *args, **kwargs):
        R, resp, objects, filtered = request.GET, None, [], 0
        # first load the template
        if R.get("template"):
            return render(request, self.params["template_list"])

        # return list data
        if R.get("action", None) == "list" or R.get("search_term"):
            objs = (
                self.params["model"]
                .objects.select_related(*self.params["related"])
                .filter(
                    ~Q(id=-1),
                    bu_id=request.session["bu_id"],
                    identifier__tacode="PEOPLEGROUP",
                    client_id=request.session["client_id"],
                )
                .values(*self.params["fields"])
                .order_by("-mdtz")
            )
            return rp.JsonResponse(data={"data": list(objs)})

        # return form empty
        if R.get("action", None) == "form":
            cxt = {
                "pgroup_form": self.params["form_class"](request=request),
                "msg": "create people group requested",
            }
            resp = utils.render_form(request, self.params, cxt)

        # handle delete request
        elif R.get("action", None) == "delete" and R.get("id", None):
            resp = utils.delete_pgroup_pgbelonging_data(request)

        elif R.get("id", None):
            obj = utils.get_model_obj(int(R["id"]), request, self.params)
            peoples = pm.Pgbelonging.objects.filter(pgroup=obj).values_list(
                "people", flat=True
            )
            FORM = self.params["form_class"](
                request=request, instance=obj, initial={"peoples": list(peoples)}
            )
            resp = utils.render_form_for_update(
                request, self.params, "pgroup_form", obj, FORM=FORM
            )
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            data = QueryDict(request.POST["formData"])
            if pk := request.POST.get("pk", None):
                pm.Pgbelonging.objects.filter(pgroup_id=int(pk)).delete()
                msg = "pgroup_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), kwargs={"request": request}
                )
                create = False
            else:
                form = self.params["form_class"](data, request=request)

            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {"errors": form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        logger.info("pgroup form is valid")
        from apps.core.utils import handle_intergrity_error

        try:
            pg = form.save(commit=False)
            putils.save_userinfo(pg, request.user, request.session, create=create)
            save_pgroupbelonging(pg, request)
            logger.info("people group form saved")
            data = {"row": Pgroup.objects.values(*self.params["fields"]).get(id=pg.id)}
            return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return handle_intergrity_error("Pgroup")


class SiteGroup(LoginRequiredMixin, View):
    params = {
        "form_class": pf.SiteGroupForm,
        "template_form": "peoples/sitegroup_form.html",
        "template_list": "peoples/sitegroup_list.html",
        "related": ["identifier"],
        "model": pm.Pgroup,
        "fields": ["groupname", "enable", "id"],
        "form_initials": {},
    }

    def get(self, request, *args, **kwargs):
        R, resp, objects, filtered = request.GET, None, [], 0
        # first load the template
        if R.get("template"):
            return render(request, self.params["template_list"])

        # for list view of group
        if R.get("action") == "list":
            total, filtered, objs = pm.Pgroup.objects.list_view_sitegrp(R, request)
            logger.info(
                "SiteGroup objects %s retrieved from db", (total or "No Records!")
            )
            utils.printsql(objs)
            resp = rp.JsonResponse(
                data={
                    "draw": R["draw"],
                    "data": list(objs),
                    "recordsFiltered": filtered,
                    "recordsTotal": total,
                }
            )
            return resp

        # to populate all sites table
        if R.get("action", None) == "allsites":
            objs, idfs = Bt.objects.get_bus_idfs(
                R, request=request, idf=R["sel_butype"]
            )
            resp = rp.JsonResponse(data={"data": list(objs), "idfs": list(idfs)})
            return resp

        if R.get("action") == "loadSites":
            data = Pgbelonging.objects.get_assigned_sitesto_sitegrp(R["id"])
            resp = rp.JsonResponse(
                data={
                    "assigned_sites": list(data),
                }
            )
            return resp

        # form without instance to create new data
        if R.get("action", None) == "form":
            # options = self.get_options()
            cxt = {
                "sitegrpform": self.params["form_class"](request=request),
                "msg": "create site group requested",
            }
            return render(request, self.params["template_form"], context=cxt)

        # handle delete request
        if R.get("action", None) == "delete" and R.get("id", None):
            obj = utils.get_model_obj(R["id"], request, self.params)
            pm.Pgbelonging.objects.filter(pgroup_id=obj.id).delete()
            obj.delete()
            return rp.JsonResponse(data=None, status=200, safe=False)

        # form with instance to load existing data
        if R.get("id", None):
            obj = utils.get_model_obj(int(R["id"]), request, self.params)
            sites = pm.Pgbelonging.objects.filter(pgroup=obj).values_list(
                "assignsites", flat=True
            )
            cxt = {
                "sitegrpform": self.params["form_class"](request=request, instance=obj),
                "assignedsites": sites,
            }
            resp = render(request, self.params["template_form"], context=cxt)
            return resp

    def post(self, request, *args, **kwargs):
        import json

        data = QueryDict(request.POST["formData"])
        assignedSites = json.loads(request.POST["assignedSites"])
        pk = data.get("pk", None)
        try:
            if pk not in [None, "None"]:
                msg = "pgroup_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), kwargs={"request": request}
                )
                create = False
            else:
                form = self.params["form_class"](data, request=request)

            if form.is_valid():
                resp = self.handle_valid_form(form, assignedSites, request)
            else:
                cxt = {"errors": form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, assignedSites, request):
        logger.info("pgroup form is valid")
        from apps.core.utils import handle_intergrity_error

        try:
            with transaction.atomic(using=utils.get_current_db_name()):
                pg = form.save(commit=False)
                putils.save_userinfo(pg, request.user, request.session)
                self.save_assignedSites(pg, assignedSites, request)
                logger.info("people group form saved")
                data = {
                    "success": "Record has been saved successfully",
                    "pk": pg.pk,
                    "row": model_to_dict(pg),
                }
                return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return handle_intergrity_error("Pgroup")

    @staticmethod
    def resest_assignedsites(pg):
        pm.Pgbelonging.objects.filter(pgroup_id=pg.id).delete()

    def save_assignedSites(self, pg, sitesArray, request):
        S = request.session
        self.resest_assignedsites(pg)
        for site in sitesArray:
            pgb = pm.Pgbelonging(
                pgroup=pg,
                people_id=1,
                assignsites_id=site["buid"],
                client_id=S["client_id"],
                bu_id=S["bu_id"],
                tenant_id=S.get("tenantid", 1),
            )
            putils.save_userinfo(pgb, request.user, request.session)


class NoSite(View):
    def get(self, request):

        cxt = {"nositeform": pf.NoSiteForm(session=request.session)}
        return render(request, "peoples/nosite.html", cxt)

    def post(self, request):
        form = pf.NoSiteForm(request.POST, session=request.session)
        if form.is_valid():
            bu_id = form.cleaned_data["site"]
            bu = Bt.objects.get(id=bu_id)
            request.session["bu_id"] = bu_id
            request.session["sitename"] = bu.buname
            pm.People.objects.filter(id=request.user.id).update(bu_id=bu_id)
            return redirect("onboarding:rp_dashboard")


def verifyemail(request):
    logger.info("verify email requested for user id %s", request.GET.get("userid"))
    user = People.objects.get(id=request.GET.get("userid"))
    try:
        send_email(user)
        messages.success(
            request,
            "Verification email has been sent to your email address",
            "alert alert-success",
        )
        logger.info("message sent to %s", user.email)
    except Exception as e:
        messages.error(
            request, "Unable to send verification email", "alert alert-danger"
        )
        logger.critical("email verification failed", exc_info=True)
    return redirect("login")
