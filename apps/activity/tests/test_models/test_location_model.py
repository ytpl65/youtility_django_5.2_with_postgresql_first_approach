import pytest
from apps.activity.models.location_model import Location

@pytest.mark.django_db
def test_location_model(location_factory):
    location = location_factory()
    assert str(location) == "Test Location (LOC001)"



@pytest.mark.django_db
def test_locationcode_bu_client_unique_constraint(location_factory):
    location1 = location_factory(loccode="LOC001")
    with pytest.raises(Exception):
        location_factory(loccode="LOC001", bu=location1.bu, client=location1.client)
