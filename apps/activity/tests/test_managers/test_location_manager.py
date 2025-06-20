import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from apps.activity.models.location_model import Location
from apps.onboarding.models import Bt
from apps.peoples.models import People
from datetime import datetime
from django.utils.timezone import make_aware

@pytest.fixture
def session_request(rf):
    request = rf.get('/')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    bt = Bt.objects.create(bucode='BT1', buname='TestBU', enable=True)
    request.session.save()
    request.session['client_id'] = bt.id
    request.session['bu_id'] = bt.id
    request.session['assignedsites'] = [bt.id]
    request.user = People.objects.create(
        peoplename='Test User', email='test@example.com',
        bu=bt, client=bt,
        dateofbirth="2000-01-01", dateofjoin="2020-01-01", dateofreport="2020-01-01"
    )
    return request


@pytest.mark.django_db
def test_get_locationlistview(session_request):
    loc = Location.objects.create(
        loccode='L001', locname='TestLocation',
        bu_id=session_request.session['bu_id'],
        client_id=session_request.session['client_id'],
        enable=True
    )
    session_request.GET = {'params': 'null'}
    related = []
    fields = ['id', 'loccode', 'locname']

    result = Location.objects.get_locationlistview(related, fields, session_request)
    assert result.exists()


@pytest.mark.django_db
def test_get_locations_modified_after(session_request):
    Location.objects.create(
        loccode='MOD1', locname='ModifiedLocation',
        bu_id=session_request.session['bu_id'],
        client_id=session_request.session['client_id'],
        enable=True,
        mdtz=make_aware(datetime.now())
    )
    result = Location.objects.get_locations_modified_after(
        mdtz=make_aware(datetime(2023, 1, 1, 0, 0, 0)),
        buid=session_request.session['bu_id'],
        ctzoffset=0
    )
    assert result.exists()


@pytest.mark.django_db
def test_filter_for_dd_location_field_with_choices(session_request):
    Location.objects.create(
        loccode='DD1', locname='DropDownLocation',
        bu_id=session_request.session['bu_id'],
        client_id=session_request.session['client_id'],
        enable=True
    )
    result = Location.objects.filter_for_dd_location_field(
        request=session_request, choices=True, sitewise=True
    )
    assert list(result) != []


@pytest.mark.django_db
def test_get_assets_of_location(session_request):
    loc = Location.objects.create(
        loccode='A001', locname='LocWithAsset',
        bu_id=session_request.session['bu_id'],
        client_id=session_request.session['client_id'],
        enable=True
    )
    # Manually create asset assigned to location
    from apps.activity.models.asset_model import Asset
    Asset.objects.create(
        assetcode='AS1', assetname='Asset1',
        bu_id=loc.bu_id, client_id=loc.client_id, location=loc,iscritical=True
    )
    session_request.GET = {'locationid': str(loc.id)}

    result = Location.objects.get_assets_of_location(session_request)
    assert result.exists()




@pytest.mark.django_db
def test_location_choices_for_report(session_request):
    Location.objects.create(
        loccode='C001', locname='ChoiceLocation',
        bu_id=session_request.session['bu_id'],
        client_id=session_request.session['client_id'],
        enable=True
    )
    result = Location.objects.location_choices_for_report(
        session_request, choices=True, sitewise=True
    )
    assert result
