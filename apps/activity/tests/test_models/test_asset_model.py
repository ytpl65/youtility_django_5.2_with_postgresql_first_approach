import pytest
from apps.activity.models.asset_model import Asset,AssetLog
from django.contrib.gis.geos import Point
from django.db import IntegrityError
from django.core.exceptions import ValidationError

@pytest.mark.django_db
def test_create_minimal_asset(client_bt, bu_bt):
    asset = Asset.objects.create(
        assetcode="A001",
        assetname="Main Pump",
        iscritical=True,
        gpslocation=Point(77.5946, 12.9716),  # Bangalore
        client=client_bt,
        bu=bu_bt
    )
    
    assert asset.uuid is not None
    assert str(asset) == "Main Pump (A001)"


@pytest.mark.django_db
def test_assetcode_bu_client_unique_constraint(asset_factory):
    asset1 = asset_factory(assetcode="A001")
    with pytest.raises(IntegrityError):
        asset_factory(assetcode="A001", bu=asset1.bu, client=asset1.client)


@pytest.mark.django_db
def test_identifier_choice_fails(client_bt, bu_bt):
    asset = Asset(
        assetcode="A001",
        assetname="Main Pump",
        iscritical=True,
        gpslocation=Point(77.5946, 12.9716),  # Bangalore
        client=client_bt,
        bu=bu_bt,
        identifier="INVALID"
    )
    with pytest.raises(ValidationError):
        asset.full_clean()

    
@pytest.mark.django_db
def test_runningstatus_choice_fails(client_bt, bu_bt):
    asset = Asset(
        assetcode="A001",
        assetname="Main Pump",
        iscritical=True,
        gpslocation=Point(77.5946, 12.9716),  # Bangalore
        client=client_bt,
        bu=bu_bt,
        identifier="ASSET",
        runningstatus="INVALID"
    )

    with pytest.raises(ValidationError):
        asset.full_clean()


@pytest.mark.django_db
def test_assetlog_newstatus(client_bt, bu_bt):
    asset = Asset.objects.create(
        assetcode="A001",
        assetname="Main Pump",
        iscritical=True,
        gpslocation=Point(77.5946, 12.9716),  # Bangalore
        client=client_bt,
        bu=bu_bt
    )
    assetlog = AssetLog(
        asset=asset,
        newstatus='WORKING'
    )
    assert assetlog.cdtz == None
    assert assetlog.gpslocation == None
    assert assetlog.ctzoffset == -1
    assert assetlog.oldstatus == None
    assert assetlog.asset == asset
    assert assetlog.people == None
    assert assetlog.bu == None
    assert assetlog.client == None