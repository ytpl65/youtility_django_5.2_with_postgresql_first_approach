import pytest
from apps.activity.forms.asset_form import AssetForm, AssetExtrasForm, MasterAssetForm, SmartPlaceForm, AssetComparisionForm
from django import forms


@pytest.mark.django_db
def test_assetform_valid(client_bt, bu_bt, rf):
    request = rf.post("/")
    request.session = {'client_id': client_bt.id, 'bu_id': bu_bt.id}

    form = AssetForm(data={
        "assetcode": "A100",
        "assetname": "Main Pump",
        "runningstatus": "WORKING",
        "type": "",
        "category": "",
        "subcategory": "",
        "brand": "",
        "unit": "",
        "capacity": "100.0",
        "servprov": "",
        "parent": "",
        "location": "",
        "iscritical": True,
        "enable": True,
        "identifier": "ASSET",
        "ctzoffset": "-1"
    }, request=request)

    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_asset_extras_form_valid(rf, client_bt):
    request = rf.post("/")
    request.session = {'client_id': client_bt.id}

    form = AssetExtrasForm(data={
        'supplier': 'Acme Corp',
        'ismeter': True,
        'is_nonengg_asset': False,
        'sfdate': '2023-01-01',
        'stdate': '2023-01-10',
    }, request=request)

    assert form.is_valid(), form.errors

@pytest.mark.django_db
def test_service_from_after_to_raises_error(rf, client_bt):
    request = rf.post("/")
    request.session = {'client_id': client_bt.id}

    form = AssetExtrasForm(data={
        'sfdate': '2023-02-01',
        'stdate': '2023-01-01'
    }, request=request)

    assert not form.is_valid()
    assert "Service from date should be smaller than service to date!" in str(form.errors)


@pytest.mark.django_db
def test_master_asset_form_valid(rf, client_bt, bu_bt):
    request = rf.post("/")
    request.session = {'client_id': client_bt.id, 'bu_id': bu_bt.id}

    form = MasterAssetForm(data={
        'assetcode': 'A100',
        'assetname': 'Pump_Main_01',
        'enable': True,
        'runningstatus': 'WORKING',
        'type': '',  # optional fields will be handled by `check_nones`
        'category': '',
        'subcategory': '',
        'brand': '',
        'unit': '',
        'ctzoffset': '-1',
        'identifier': 'ASSET',
        'iscritical': True,
        'capacity': 100,
        'parent': '',
    }, request=request)

    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_master_asset_form_invalid_assetname(rf):
    request = rf.post("/")
    request.session = {'client_id': 1, 'bu_id': 1}

    form = MasterAssetForm(data={
        'assetcode': 'A100',
        'assetname': 'Pump&Main',  # 🚫 '&' not allowed by regex
        'identifier': 'ASSET',
    }, request=request)

    assert not form.is_valid()
    assert "Only these special characters" in str(form.errors)


@pytest.mark.django_db
def test_master_asset_form_identifier_hidden_by_default(rf):
    request = rf.post("/")
    request.session = {'client_id': 1, 'bu_id': 1}

    form = MasterAssetForm(request=request)
    assert form.fields['identifier'].initial == 'ASSET'
    assert 'display:none' in form.fields['identifier'].widget.attrs.get('style', '')

def test_smartplace_identifier_default(rf):
    request = rf.get("/")
    form = SmartPlaceForm(request=request)
    assert form.fields['identifier'].initial == 'SMARTPLACE'
    assert 'display:none' in form.fields['identifier'].widget.attrs['style']


def test_invalid_gps_raises_error(rf):
    request = rf.post("/", data={'formData': "gpslocation=invaliddata"})
    form = SmartPlaceForm(data={
        'assetcode': 'SP02',
        'assetname': 'SmartNode'
    }, request=request)

    with pytest.raises(forms.ValidationError):
        form.clean_gpslocation("invaliddata")


