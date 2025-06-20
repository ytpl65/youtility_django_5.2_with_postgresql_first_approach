import pytest
import warnings
from django.test import TestCase, Client

from django.urls import reverse

from apps.core.utils import save_user_session
from django.contrib.sessions.backends.db import SessionStore
import json
from apps.core.utils import basic_user_setup
from django.apps import apps
from django.contrib.gis.geos import Point
from datetime import datetime, timezone
from urllib.parse import urlencode

def create_attendance_instance():
    PeopleEventlog = apps.get_model('attendance', 'PeopleEventlog')
    return PeopleEventlog.objects.create(
        **{
            'tenant_id': 1,
            'cuser_id': 4,
            'muser_id': 4,
            'ctzoffset': 330,
            'people_id': 4,
            'client_id': 4,
            'bu_id': 5,
            'verifiedby_id': 1,
            'geofence_id': 1,
            'peventtype_id': 68,
            'transportmodes': ['NONE'],
            'punchintime': datetime(2023, 5,22,9,30,00).replace(tzinfo=timezone.utc),
            'punchouttime': None,
            'datefor': datetime.now().date(),
            'distance': 0.0,
            'duration': 0,
            'expamt': 0.0,
            'accuracy': 56.099998474121094,
            'deviceid': '562817f5d303de0c',
            'startlocation':Point(0.0, 0.0) ,
            'endlocation': None,
            'journeypath': None,
            'remarks': 'None',
            'facerecognitionin': False,
            'facerecognitionout': False,
            'peventlogextras': {'model': 'VGG',
            'threshold': '0.4',
            'distance_in': None,
            'verified_in': False,
            'distance_out': None,
            'verified_out': False,
            'similarity_metric': 'cosine'},
            'otherlocation': 'SPS HO',
            'reference': 'NONE',
            'geojson': {'endlocation': '', 'startlocation': ''}}
    )


@pytest.mark.django_db  # Required for DB access
class TestAttendanceView(TestCase):
    
    
    def setUp(self):
        # override this method setting up
        # things for every test case method wise
        
        self.client = basic_user_setup()
        self.url = reverse('attendance:attendance_view')
        self.pel = create_attendance_instance()
        session = self.client.session
        session['sitecode'] = 'SPSOPERATION'
        session['sitename'] = 'YTPL'
        session['clientcode'] = 'SUKHI'
        session['bu_id'] = [1]
        session.save()

        
    def test_attendance_get_template(self):
        response = self.client.get(self.url, data={'template':'true'})
        self.assertEqual(response.status_code, 200)
    
    def test_attendance_get_sos_template(self):
        response = self.client.get(self.url, data={'template':'sos_template'})
        self.assertEqual(response.status_code, 200)

    def test_attendance_action_sos_list_view(self):
        params = json.dumps({'from':'2023-05-01', 'to':'2023-05-30'})
        response = self.client.get(self.url, data={'action':'sos_list_view', 'params':params})
        self.assertEqual(response.status_code, 200)
        
    def test_attendance_action_list_view(self):
        params = json.dumps({'from':'2023-05-01', 'to':'2023-05-30'})
        response = self.client.get(self.url, data={'action':'list', 'params':params})
        self.assertEqual(response.status_code, 200)
        
    def test_attendance_action_form(self):
        response = self.client.get(self.url, data={'action':'form'})
        self.assertContains(response, 'Attendance')
        self.assertEqual(response.status_code, 200)
    
    def test_attendance_form_with_instance(self):
        Bt = apps.get_model('onboarding', 'Bt')
        response = self.client.get(self.url, data={'id':self.pel.id})
        self.assertIn(b'Attendance', response.content)
        self.assertEqual(response.status_code, 200)
    
    def test_attendance_delete_request(self):
        response = self.client.get(self.url, data = {'action':"delete", 'id':self.pel.id})
        self.assertEqual(response.status_code, 200)

    def test_attendance_update_instance(self):
        response = self.client.post(
            self.url,
            data= {
            'formData':urlencode({
                "ctzoffset":330, "people":4, "datefor":'27-Jun-2023', "peventtype":68,
                'verifiedby':4, 'remarks':None, 'punchintime':'27-Jun-2023 12:45:06', 
                'punchouttime':'27-Jun-2023 14:38:06'}), 'pk':self.pel.id
            },
        )
        self.assertEqual(response.status_code, 200)
    
    def test_attendance_update_instance_invalid_form(self):
        response = self.client.post(
            self.url,
            data= {
            'formData':urlencode({
                "ctzoffset":330, "people":4, "datefor":'27-Jun', "peventtype":68,
                'verifiedby':4, 'remarks':None, 'punchintime':'27-Jun-2023 12:45:06', 
                'punchouttime':'27-Jun-2023 14:38:06'}), 'pk':self.pel.id
            },
        )
        self.assertEqual(response.status_code, 404)
    
    def test_attendance_create_record(self):
        response = self.client.post(
            self.url,
            data= {
            'formData':urlencode({
                "ctzoffset":330, "people":4, "datefor":'27-Jun-2023', "peventtype":68,
                'verifiedby':4, 'remarks':None, 'punchintime':'27-Jun-2023 12:45:06', 
                'punchouttime':'27-Jun-2023 14:38:06'})
            },
        )
        self.assertEqual(response.status_code, 200)
    
    def test_attendance_create_record_invalid(self):
        response = self.client.post(
            self.url,
            data= {
            'formData':urlencode({
                "ctzoffset":330, "people":None, "datefor":'27-Jun-2023', "peventtype":68,
                'verifiedby':4, 'remarks':None, 'punchintime':'27-Jun-2023 12:45:06', 
                'punchouttime':'27-Jun-2023 14:38:06'})
            },
        )
        self.assertEqual(response.status_code, 404)
        


class ConveyanceView(TestCase):
    def setUp(self):
        # override this method setting up
        # things for every test case method wise
        
        self.client = basic_user_setup()
        self.url = reverse('attendance:conveyance')
        session = self.client.session
        session['sitecode'] = 'SPSOPERATION'
        session['sitename'] = 'YTPL'
        session['clientcode'] = 'SUKHI'
        session['bu_id'] = [1]
        session.save()
        
    
    def test_conveyance_get_template(self):
        response = self.client.get(self.url, data={'template':'true'})
        self.assertEqual(response.status_code, 200)