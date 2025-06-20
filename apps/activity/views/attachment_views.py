import json
import logging
import mimetypes
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.http import response as rp
from django.shortcuts import render
from django.views.generic.base import View
from apps.activity.models.attachment_model import Attachment
from apps.activity.models.job_model import Job
import apps.activity.utils as av_utils
import apps.onboarding.models as obm
from apps.core import utils
from apps.onboarding.utils import is_point_in_geofence, polygon_to_address
from apps.service.utils import get_model_or_form
import time
from requests.exceptions import RequestException

logger = logging.getLogger('django')
def get_address(lat, lon):
    if lat == 0.0 and lon == 0.0:
        return "Invalid coordinates"

    for attempt in range(3):  # Retry up to 3 times
        try:
            response = av_utils.get_address_from_coordinates(lat, lon)
            if response and response.get("full_address"):
                return response.get("full_address")
        except RequestException as e:
            logger.warning(f"Retrying due to error: {e}")
            time.sleep(2**attempt)  # Exponential backoff
    logger.error(
        f"Failed to retrieve address after retries for coordinates: {lat}, {lon}"
    )
    return "Address lookup failed"



class Attachments(LoginRequiredMixin, View):
    params = {
        'model':Attachment
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        if R.get('action') == 'delete_att'  and R.get('id'):
            res = P['model'].objects.filter(id=R['id']).delete()
            if R['ownername'].lower() in ['ticket', 'jobneed', 'jobneeddetails']:
                #update attachment count
                model = get_model_or_form(R['ownername'].lower())
                model.objects.filter(uuid = R['ownerid']).update(
                    attachmentcount = P['model'].objects.filter(owner = R['ownerid']).count()
                )
            return rp.JsonResponse({'result':res}, status=200)
        
        if R.get('action') == 'get_attachments_of_owner' and R.get('owner'):
            objs = P['model'].objects.get_att_given_owner(R['owner'])   
            return rp.JsonResponse({'data':list(objs)}, status=200)

        if R.get('action') == 'download' and R.get('filepath') and R.get('filename'):
            file = f"{settings.MEDIA_URL}{R['filepath'].replace('youtility4_media/', '')}/{R['filename']}"
            file = open(file, 'r')
            mime_type, _ = mimetypes.guess_type(R['filepath'])
            response = HttpResponse(file, content_type=mime_type)
            response['Content-Disposition'] = f"attachment; filename={R['filename']}"
            return response
    
    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.params
        if 'img' in request.FILES:
            isUploaded, filename, filepath = utils.upload(request)
            filepath = filepath.replace(settings.MEDIA_ROOT, "")
            if isUploaded:
                if data := P['model'].objects.create_att_record(request, filename, filepath):
                    #update attachment count
                    if data['ownername'].lower() in ['ticket' ,'jobneed', 'jobneeddetails', 'wom']:
                        model = get_model_or_form(data['ownername'].lower())
                        model.objects.filter(uuid = R['ownerid']).update(attachmentcount = data['attcount'])
                return rp.JsonResponse(data, status = 200, safe=False)
        return rp.JsonResponse({'error':"Invalid Request"}, status=404)



class PreviewImage(LoginRequiredMixin, View):
    P = {
        'model':Attachment
    }
    def get(self, request, *args, **kwargs):
        R = request.GET
        S = request.session

        if R.get('action') == 'getFRStatus' and R.get('uuid'):
            try:
                # Fetch data
                resp = self.P['model'].objects.get_fr_status(R['uuid'])

                # Validate eventlog_in_out
                if not resp.get('eventlog_in_out') or not resp['eventlog_in_out'][0]:
                    return rp.JsonResponse({'error': 'Invalid eventlog_in_out data'}, status=400)

                eventlog_entry = resp['eventlog_in_out'][0]
                get_people = Job.objects.filter(
                    people_id=eventlog_entry['people_id'], identifier='GEOFENCE'
                ).values()
                base_address = ""

                if get_people:
                    get_geofence_data = obm.GeofenceMaster.objects.filter(
                        id=get_people[0]['geofence_id'], enable=True
                    ).exclude(id=1).values()
                    if get_geofence_data:
                        base_address = polygon_to_address(get_geofence_data[0]['geofence'])

                # Handle startgps
                start_address = ""
                startgps = eventlog_entry.get('startgps')
                if startgps:
                    try:
                        start_coordinates = json.loads(startgps).get('coordinates')
                        if start_coordinates and len(start_coordinates) >= 2:
                            start_address = get_address(
                                start_coordinates[1], start_coordinates[0]
                            )
                    except (ValueError, KeyError, TypeError) as e:
                        logger.error(f"Error parsing startgps: {e}, startgps: {startgps}")
                        start_address = "Error parsing startgps"

                # Handle endgps
                end_address = ""
                endgps = eventlog_entry.get('endgps')
                if endgps:
                    try:
                        end_coordinates = json.loads(endgps).get('coordinates')
                        if end_coordinates and len(end_coordinates) >= 2:
                            end_address = get_address(
                                end_coordinates[1], end_coordinates[0]
                            )
                    except (ValueError, KeyError, TypeError) as e:
                        logger.error(f"Error parsing endgps: {e}, endgps: {endgps}")
                        end_address = "Error parsing endgps"

                # Determine in_address and out_address
                if start_address and get_people and get_geofence_data:
                    eventlog_entry['in_address'] = (
                        f"{start_address} (Inside Geofence)"
                        if is_point_in_geofence(
                            start_coordinates[1], start_coordinates[0], get_geofence_data[0]['geofence']
                        )
                        else f"{start_address} (Outside Geofence)"
                    )
                else:
                    eventlog_entry['in_address'] = start_address or "Unknown address"

                if end_address and get_people and get_geofence_data:
                    eventlog_entry['out_address'] = (
                        f"{end_address} (Inside Geofence)"
                        if is_point_in_geofence(
                            end_coordinates[1], end_coordinates[0], get_geofence_data[0]['geofence']
                        )
                        else f"{end_address} (Outside Geofence)"
                    )
                else:
                    eventlog_entry['out_address'] = end_address or "Unknown address"

                eventlog_entry['base_address'] = base_address
                return rp.JsonResponse(resp, status=200)

            except self.P['model'].objects.model.DoesNotExist:
                logger.error(f"Model not found for uuid: {R.get('uuid')}")
                return rp.JsonResponse({'error': 'Data not found'}, status=404)

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return rp.JsonResponse({'error': 'Internal server error'}, status=500)

        return rp.JsonResponse({'error': 'Invalid request'}, status=400)
