import pytest
from django.urls import reverse
from django.test import override_settings

@override_settings(ROOT_URLCONF='apps.service.rest_service.urls')
@pytest.mark.django_db
def test_people_list(api_client, people_factory):
    people_factory()
    url = reverse('people-list')
    resp = api_client.get(url)
    assert resp.status_code == 200
    assert resp.json() != []

@override_settings(ROOT_URLCONF='apps.service.rest_service.urls')
@pytest.mark.django_db
def test_people_retrieve(api_client, people_factory):
    person = people_factory()
    url = reverse('people-detail', args=[person.id])
    resp = api_client.get(url)
    assert resp.status_code == 200
    assert resp.json()['id'] == person.id
