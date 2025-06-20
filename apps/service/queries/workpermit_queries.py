import graphene
from apps.work_order_management.models import Wom, Approver
from apps.service.types import GetPdfUrl, SelectOutputType
from graphql import GraphQLError
from background_tasks.tasks import send_email_notification_for_workpermit_approval,send_email_notification_for_vendor_and_security_after_approval
from apps.work_order_management.utils import check_all_approved, check_all_verified
from apps.work_order_management.models import Wom
from apps.onboarding.models import Bt
from apps.work_order_management.views import WorkPermit
from apps.work_order_management.utils import save_pdf_to_tmp_location
from apps.work_order_management.utils import reject_workpermit
from apps.activity.models.question_model import QuestionSet
from apps.work_order_management.models import Vendor
from apps.peoples.models import People
from apps.service.inputs.workpermit_input import WomPdfUrlFilterInput,VendorFilterInput, WomRecordFilterInput, ApproverFilterInput, ApproveWorkpermitFilterInput,RejectWorkpermitFilterInput
from logging import getLogger
from apps.core import utils
from pydantic import ValidationError
from apps.service.pydantic_schemas.workpermit_schema import WomPdfUrlSchema, WomRecordSchema, ApproveWorkpermitSchema, RejectWorkpermitSchema, ApproverSchema, VendorSchema
log = getLogger('mobile_service_log')



class WorkPermitQueries(graphene.ObjectType):
    get_pdf_url = graphene.Field(
        GetPdfUrl,
        filter = WomPdfUrlFilterInput(required=True)
    )

    get_wom_records = graphene.Field(
        SelectOutputType,
        filter = WomRecordFilterInput(required=True)
    )

    get_approve_workpermit = graphene.Field(
        SelectOutputType,
        filter = ApproveWorkpermitFilterInput(required=True)
    )

    get_reject_workpermit = graphene.Field(
        SelectOutputType,
        filter = RejectWorkpermitFilterInput(required=True)
    )

    get_approvers = graphene.Field(
        SelectOutputType,
        filter = ApproverFilterInput(required=True)
    )

    get_vendors = graphene.Field(
        SelectOutputType,
        filter = VendorFilterInput(required=True)
    )

    @staticmethod
    def resolve_get_vendors(self, info, filter):
        try:
            log.info("request for get_vendors")
            validated = VendorSchema(**filter)
            data = Vendor.objects.get_vendors_for_mobile(info.context,buid = validated.buid, mdtz=validated.mdtz,ctzoffset=validated.ctzoffset,clientid = validated.clientid)
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count,  records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_vendors failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_vendors failed: {str(e)}")

    @staticmethod
    def resolve_get_approvers(self, info, filter):
        try:
            log.info("request for get_approver")
            validated = ApproverSchema(**filter)
            data = Approver.objects.get_approver_list_for_mobile(validated.buid, validated.clientid)
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count,  records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_approver failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_approver failed: {str(e)}")
    
    @staticmethod
    def resolve_approve_workpermit(self, info, filter):
        try:
            log.info("request for change wom status")
            validated = ApproveWorkpermitSchema(**filter)
            wom = Wom.objects.get(uuid=validated.wom_uuid)
            sitename = Bt.objects.get(id=wom.bu_id).buname
            workpermit_status = wom.workstatus
            wp_approvers = wom.other_data['wp_approvers']
            approvers = [approver['name'] for approver in wp_approvers]
            approvers_code = [approver['peoplecode'] for approver in wp_approvers]
            vendor_name = Vendor.objects.get(id=wom.vendor.id).name
            client_id = wom.client.id
            permit_name = QuestionSet.objects.get(id=wom.qset.id).qsetname
            report_object = WorkPermit.get_report_object(wom,permit_name)
            report = report_object(filename=permit_name,client_id=wom.client_id,returnfile=True,formdata = {'id':wom.id},request=None)
            report_pdf_object = report.execute()
            permit_no = wom.other_data['wp_seqno']
            pdf_path = save_pdf_to_tmp_location(report_pdf_object,report_name=permit_name,report_number=wom.other_data['wp_seqno'])
            if validated.identifier == 'APPROVER':
                p = People.objects.filter(id = validated.peopleid).first()
                if is_all_approved := check_all_approved(validated.wom_uuid, p.peoplecode):
                    log.info(f'Is all approved in side of if: {is_all_approved}')
                    updated = Wom.objects.filter(uuid=validated.wom_uuid).update(workpermit=Wom.WorkPermitStatus.APPROVED.value)
                if is_all_approved:
                    workpermit_status = 'APPROVED'
                    Wom.objects.filter(id=wom.id).update(workstatus=Wom.Workstatus.INPROGRESS.value)
                    permit_name = QuestionSet.objects.get(id=wom.qset.id).qsetname
                    report_object = WorkPermit.get_report_object(wom,permit_name)
                    report = report_object(filename=permit_name,client_id=wom.client_id,returnfile=True,formdata = {'id':wom.id},request=None)
                    report_pdf_object = report.execute()
                    permit_no = wom.other_data['wp_seqno']
                    pdf_path = save_pdf_to_tmp_location(report_pdf_object,report_name=permit_name,report_number=wom.other_data['wp_seqno'])
                    send_email_notification_for_vendor_and_security_after_approval.delay(wom.id,sitename,workpermit_status,vendor_name,pdf_path,permit_name,permit_no)
                    pass
                rc, msg = 0, "success"
            else:
                p = People.objects.filter(id = validated.peopleid).first()
                if is_all_verified := check_all_verified(validated.wom_uuid, p.peoplecode):
                    updated = Wom.objects.filter(uuid=validated.wom_uuid).update(verifiers_status=Wom.WorkPermitStatus.APPROVED.value)
                if is_all_verified:
                    send_email_notification_for_workpermit_approval.delay(wom.id,approvers,approvers_code,sitename,workpermit_status,permit_name,pdf_path,vendor_name,client_id)
                    #Sending Email to Approver
                rc, msg = 0, "success"
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"approve_workpermit failed: {str(ve)}")
        except Exception as e:
            log.critical("something went wrong", exc_info=True)
            rc, msg = 1, "failed"
        return SelectOutputType(nrows = rc, records = msg)

    @staticmethod
    def resolve_reject_workpermit(self, info, filter):
        try:
            log.info("request for change wom status")
            validated = RejectWorkpermitSchema(**filter)
            p = People.objects.filter(id = validated.peopleid).first()
            Wom.objects.filter(uuid=validated.wom_uuid).update(workpermit=Wom.WorkPermitStatus.REJECTED.value)
            reject_workpermit(validated.wom_uuid, p.peoplecode)
            rc, msg = 0, "success"
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"reject_workpermit failed: {str(ve)}")
        except Exception as e:
            log.critical("something went wrong", exc_info=True)
            rc, msg = 1, "failed"
        return SelectOutputType(nrows = rc, records = msg)

    @staticmethod
    def resolve_get_wom_records(self, info, filter):
        try:
            log.info('request for get_wom_records')
            validated = WomRecordSchema(**filter)
            data = Wom.objects.get_wom_records_for_mobile(
                fromdate = validated.fromdate, 
                todate = validated.todate, 
                peopleid = validated.peopleid, 
                workpermit = validated.workpermit, 
                buid = validated.buid, 
                clientid = validated.clientid, 
                parentid = validated.parentid
                )
            records, count, msg = utils.get_select_output(data)
            log.info(f'{count} objects returned...')
            return SelectOutputType(nrows = count,  records = records,msg = msg)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_wom_records failed: {str(ve)}")
        except Exception as e:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_wom_records failed: {str(e)}")
    
    @staticmethod
    def resolve_get_pdf_url(self, info, filter):
        import os
        from intelliwiz_config import settings
        from urllib.parse import urljoin
        from apps.work_order_management.utils import save_pdf_to_tmp_location, get_report_object
        from apps.activity.models.question_model import QuestionSet
        try:
            validated = WomPdfUrlSchema(**filter)
            wom = Wom.objects.get(uuid=validated.wom_uuid)
            permit_name = QuestionSet.objects.get(id=wom.qset.id).qsetname
            permit_no = wom.other_data['wp_seqno']
            client_id = wom.client.id
            report_obj = get_report_object(permit_name)
            report = report_obj(filename=permit_name, client_id=client_id, returnfile=True, formdata={'id': wom.id}, request=None)
            report_pdf_object = report.execute()
            pdf_path = save_pdf_to_tmp_location(report_pdf_object, report_name=permit_name, report_number=permit_no)
            file_url = urljoin(settings.MEDIA_URL, pdf_path.split('/')[-1])
            full_url = os.path.join(settings.MEDIA_ROOT, file_url)
            return GetPdfUrl(url=full_url)
        except ValidationError as ve:
            log.error("something went wrong", exc_info=True)
            raise GraphQLError(f"get_pdf_url failed: {str(ve)}")
        except Exception as e:
            raise GraphQLError(f"get_pdf_url failed: {str(e)}")
        
