# apps/activity/tests/test_forms/test_location_form.py

import pytest
from django import forms
from django.contrib.gis.geos import GEOSGeometry
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from apps.activity.forms.location_form import LocationForm
from apps.activity.models.location_model import Location
from apps.onboarding.models import TypeAssist


@pytest.fixture
def request_with_session(client_bt, bu_bt):
    rf = RequestFactory()
    request = rf.post("/", data={'formData': 'gpslocation=12.9716,77.5946'})
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session['client_id'] = client_bt.id
    request.session['bu_id'] = bu_bt.id
    request.session.save()
    return request


@pytest.mark.django_db
def test_locationform_valid_submission(request_with_session):
    loc_type = TypeAssist.objects.create(tacode='LOCATIONTYPE', client_id=request_with_session.session['client_id'])
    form_data = {
        'loccode': 'BLR01',
        'locname': 'Bangalore HQ',
        'enable': True,
        'iscritical': False,
        'ctzoffset': -1,
        'locstatus': 'WORKING',
        'type': loc_type.id
    }

    form = LocationForm(data=form_data, request=request_with_session)
    form.fields['type'].queryset = TypeAssist.objects.all()
    form.fields['parent'].queryset = Location.objects.none()

    assert form.is_valid(), form.errors
    assert form.cleaned_data['loccode'] == 'BLR01'


@pytest.mark.django_db
def test_locationform_duplicate_loccode_raises_error(request_with_session):
    Location.objects.create(
        loccode='LOC123',
        locname='Existing',
        client_id=request_with_session.session['client_id'],
        bu_id=request_with_session.session['bu_id']
    )
    form_data = {
        'loccode': 'LOC123',
        'locname': 'Duplicate',
        'enable': True,
        'iscritical': False,
        'ctzoffset': -1,
        'locstatus': 'WORKING',
    }

    form = LocationForm(data=form_data, request=request_with_session)
    form.fields['type'].queryset = TypeAssist.objects.none()
    form.fields['parent'].queryset = Location.objects.none()

    assert not form.is_valid()
    assert "Location code already exists" in str(form.errors)


@pytest.mark.django_db
def test_locationform_invalid_gpslocation(request_with_session):
    form = LocationForm(data={'loccode': 'XYZ', 'locname': 'GPS Invalid'}, request=request_with_session)
    with pytest.raises(forms.ValidationError):
        form.clean_gpslocation("invalid_gps")


@pytest.mark.django_db
def test_locationform_valid_gpslocation_parsing(request_with_session):
    form = LocationForm(data={'loccode': 'XYZ', 'locname': 'GPS Test'}, request=request_with_session)
    gps = form.clean_gpslocation("12.9716,77.5946")
    assert isinstance(gps, GEOSGeometry)
    assert gps.coords == (77.5946, 12.9716)
