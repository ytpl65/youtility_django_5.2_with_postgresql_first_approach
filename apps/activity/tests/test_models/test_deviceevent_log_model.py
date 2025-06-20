import pytest
from apps.activity.models.deviceevent_log_model import DeviceEventlog
from django.contrib.gis.geos import Point


@pytest.mark.django_db
def test_create_minimal_deviceeventlog(client_bt, bu_bt):
    deviceeventlog = DeviceEventlog.objects.create(
        deviceid="1234567890",
        eventvalue="stepcount",
        bu=bu_bt,
        client=client_bt
    )
    assert deviceeventlog.uuid is not None
    assert str(deviceeventlog) == "1234567890 stepcount"


