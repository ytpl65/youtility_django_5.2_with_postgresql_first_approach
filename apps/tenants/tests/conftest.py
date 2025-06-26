import pytest
from django.utils import timezone

from apps.tenants.models import Tenant


@pytest.fixture
def sample_tenant():
    return Tenant.objects.create(
        tenantname="Test Tenant",
        subdomain_prefix="test"
    )

@pytest.fixture
def multiple_tenants():
    tenant1 = Tenant.objects.create(
        tenantname="Tenant One",
        subdomain_prefix="one"
    )
    tenant2 = Tenant.objects.create(
        tenantname="Tenant Two", 
        subdomain_prefix="two"
    )
    tenant3 = Tenant.objects.create(
        tenantname="Tenant Three",
        subdomain_prefix="three"
    )
    return [tenant1, tenant2, tenant3]

@pytest.fixture
def tenant_data():
    return {
        'tenantname': 'Sample Tenant',
        'subdomain_prefix': 'sample'
    }

@pytest.fixture
def valid_tenant_data():
    return {
        'tenantname': 'Valid Tenant Name',
        'subdomain_prefix': 'valid'
    }

@pytest.fixture
def invalid_tenant_data():
    return {
        'tenantname': 'A' * 51,  # Exceeds max_length
        'subdomain_prefix': 'b' * 51  # Exceeds max_length
    }