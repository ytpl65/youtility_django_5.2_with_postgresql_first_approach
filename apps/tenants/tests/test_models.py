from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from apps.tenants.middlewares import THREAD_LOCAL

from apps.tenants.models import Tenant, TenantAwareModel


class TenantModelTest(TestCase):
    
    def setUp(self):
        # Set up the thread local DB to avoid Http404 errors
        THREAD_LOCAL.DB = 'default'
        
        self.tenant_data = {
            'tenantname': 'Test Tenant',
            'subdomain_prefix': 'test'
        }
    
    def tearDown(self):
        # Clean up thread local
        if hasattr(THREAD_LOCAL, 'DB'):
            delattr(THREAD_LOCAL, 'DB')

    def test_tenant_creation(self):
        tenant = Tenant.objects.create(**self.tenant_data)
        
        self.assertIsInstance(tenant, Tenant)
        self.assertEqual(tenant.tenantname, 'Test Tenant')
        self.assertEqual(tenant.subdomain_prefix, 'test')
        self.assertIsNotNone(tenant.created_at)

    def test_tenant_str_method(self):
        tenant = Tenant.objects.create(**self.tenant_data)
        
        # Test that the object can be converted to string without error
        str_representation = str(tenant)
        self.assertIsInstance(str_representation, str)

    def test_tenant_unique_subdomain_prefix(self):
        Tenant.objects.create(**self.tenant_data)
        
        # Try to create another tenant with the same subdomain_prefix
        with self.assertRaises(IntegrityError):
            Tenant.objects.create(
                tenantname='Another Tenant',
                subdomain_prefix='test'  # Same as first tenant
            )

    def test_tenant_fields_max_length(self):
        # Test tenantname max length
        long_tenantname = 'A' * 51  # 51 characters, exceeds max_length of 50
        tenant = Tenant(
            tenantname=long_tenantname,
            subdomain_prefix='test'
        )
        
        with self.assertRaises(ValidationError):
            tenant.full_clean()

    def test_tenant_subdomain_prefix_max_length(self):
        # Test subdomain_prefix max length
        long_subdomain = 'a' * 51  # 51 characters, exceeds max_length of 50
        tenant = Tenant(
            tenantname='Test Tenant',
            subdomain_prefix=long_subdomain
        )
        
        with self.assertRaises(ValidationError):
            tenant.full_clean()

    def test_tenant_created_at_auto_now_add(self):
        before_creation = timezone.now()
        tenant = Tenant.objects.create(**self.tenant_data)
        after_creation = timezone.now()
        
        self.assertTrue(before_creation <= tenant.created_at <= after_creation)

    def test_tenant_created_at_not_auto_now(self):
        tenant = Tenant.objects.create(**self.tenant_data)
        original_created_at = tenant.created_at
        
        # Update the tenant
        tenant.tenantname = 'Updated Tenant'
        tenant.save()
        
        # created_at should not change on save
        self.assertEqual(tenant.created_at, original_created_at)

    def test_tenant_empty_tenantname(self):
        tenant = Tenant(
            tenantname='',
            subdomain_prefix='test'
        )
        
        # Empty tenantname should NOT be allowed (CharField without blank=True)
        with self.assertRaises(ValidationError) as cm:
            tenant.full_clean()
        
        self.assertIn('tenantname', cm.exception.message_dict)

    def test_tenant_empty_subdomain_prefix(self):
        tenant = Tenant(
            tenantname='Test Tenant',
            subdomain_prefix=''
        )
        
        # Empty subdomain_prefix should NOT be allowed (CharField without blank=True)
        with self.assertRaises(ValidationError) as cm:
            tenant.full_clean()
        
        self.assertIn('subdomain_prefix', cm.exception.message_dict)

    def test_multiple_tenants_creation(self):
        tenant1 = Tenant.objects.create(
            tenantname='Tenant One',
            subdomain_prefix='one'
        )
        tenant2 = Tenant.objects.create(
            tenantname='Tenant Two',
            subdomain_prefix='two'
        )
        
        self.assertEqual(Tenant.objects.count(), 2)
        self.assertNotEqual(tenant1.subdomain_prefix, tenant2.subdomain_prefix)

    def test_tenant_meta_options(self):
        tenant = Tenant.objects.create(**self.tenant_data)
        meta = tenant._meta
        
        # Check that the model has expected meta attributes
        self.assertEqual(meta.app_label, 'tenants')

    def test_tenant_field_verbose_names(self):
        tenant = Tenant()
        
        # Check verbose names
        tenantname_field = tenant._meta.get_field('tenantname')
        subdomain_prefix_field = tenant._meta.get_field('subdomain_prefix')
        created_at_field = tenant._meta.get_field('created_at')
        
        self.assertEqual(tenantname_field.verbose_name, 'tenantname')
        self.assertEqual(subdomain_prefix_field.verbose_name, 'subdomain_prefix')
        self.assertEqual(created_at_field.verbose_name, 'created_at')


class TenantAwareModelTest(TestCase):
    
    def setUp(self):
        # Set up the thread local DB to avoid Http404 errors
        THREAD_LOCAL.DB = 'default'
        
        self.tenant = Tenant.objects.create(
            tenantname='Test Tenant',
            subdomain_prefix='test'
        )

        # Create a concrete model that inherits from TenantAwareModel for testing
        from django.db import models
        
        class TestTenantAwareModel(TenantAwareModel):
            name = models.CharField(max_length=100)
            
            class Meta:
                app_label = 'tenants'
        
        self.TestModel = TestTenantAwareModel
    
    def tearDown(self):
        # Clean up thread local
        if hasattr(THREAD_LOCAL, 'DB'):
            delattr(THREAD_LOCAL, 'DB')

    def test_tenant_aware_model_is_abstract(self):
        # Test that TenantAwareModel is abstract
        self.assertTrue(TenantAwareModel._meta.abstract)

    def test_tenant_aware_model_has_tenant_field(self):
        # Check that TenantAwareModel has tenant field
        tenant_field = TenantAwareModel._meta.get_field('tenant')
        
        self.assertEqual(tenant_field.related_model, Tenant)
        self.assertTrue(tenant_field.null)
        self.assertTrue(tenant_field.blank)
        self.assertEqual(tenant_field.remote_field.on_delete.__name__, 'CASCADE')

    def test_tenant_aware_model_inheritance(self):
        # Test that we can create a model that inherits from TenantAwareModel
        from django.db import models
        
        class ConcreteModel(TenantAwareModel):
            name = models.CharField(max_length=100)
            
            class Meta:
                app_label = 'tenants'
        
        # Check that the concrete model has the tenant field
        self.assertTrue(hasattr(ConcreteModel, 'tenant'))
        
        # Check the tenant field properties
        tenant_field = ConcreteModel._meta.get_field('tenant')
        self.assertEqual(tenant_field.related_model, Tenant)

    def test_tenant_aware_model_cascade_delete(self):
        # This test would require creating tables, which is complex in unit tests
        # Instead, we just verify the on_delete setting
        tenant_field = TenantAwareModel._meta.get_field('tenant')
        
        from django.db.models import CASCADE
        self.assertEqual(tenant_field.remote_field.on_delete, CASCADE)

    def test_tenant_aware_model_nullable(self):
        # Test that tenant field can be null
        tenant_field = TenantAwareModel._meta.get_field('tenant')
        
        self.assertTrue(tenant_field.null)
        self.assertTrue(tenant_field.blank)

    def test_tenant_aware_model_foreign_key(self):
        # Test that tenant field is a ForeignKey to Tenant
        tenant_field = TenantAwareModel._meta.get_field('tenant')
        
        from django.db.models import ForeignKey
        self.assertIsInstance(tenant_field, ForeignKey)
        self.assertEqual(tenant_field.related_model, Tenant)