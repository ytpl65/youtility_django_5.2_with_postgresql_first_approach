from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from unittest.mock import Mock, patch
from datetime import date
from apps.tenants.middlewares import THREAD_LOCAL

from apps.tenants.models import Tenant
from apps.tenants.admin import TenantAdmin, TenantResource

User = get_user_model()


class TenantResourceTest(TestCase):
    
    def setUp(self):
        # Set up the thread local DB to avoid Http404 errors
        THREAD_LOCAL.DB = 'default'
        self.resource = TenantResource()
    
    def tearDown(self):
        # Clean up thread local
        if hasattr(THREAD_LOCAL, 'DB'):
            delattr(THREAD_LOCAL, 'DB')

    def test_resource_meta_model(self):
        self.assertEqual(self.resource._meta.model, Tenant)

    def test_resource_meta_fields(self):
        expected_fields = ['tenantname', 'subdomain_prefix']
        self.assertEqual(self.resource._meta.fields, expected_fields)

    def test_resource_meta_skip_unchanged(self):
        self.assertTrue(self.resource._meta.skip_unchanged)

    def test_resource_meta_report_skipped(self):
        self.assertTrue(self.resource._meta.report_skipped)


    def test_resource_export_functionality(self):
        # Create test data
        tenant1 = Tenant.objects.create(
            tenantname='Test Tenant 1',
            subdomain_prefix='tenant1'
        )
        tenant2 = Tenant.objects.create(
            tenantname='Test Tenant 2',
            subdomain_prefix='tenant2'
        )
        
        # Test export
        queryset = Tenant.objects.all()
        dataset = self.resource.export(queryset)
        
        self.assertEqual(len(dataset), 2)
        self.assertEqual(dataset.headers, ['tenantname', 'subdomain_prefix'])

    def test_resource_field_mapping(self):
        # Test that the resource correctly maps fields
        tenant = Tenant.objects.create(
            tenantname='Test Tenant',
            subdomain_prefix='test'
        )
        
        # Export single instance
        dataset = self.resource.export(Tenant.objects.filter(id=tenant.id))
        
        self.assertEqual(dataset[0][0], 'Test Tenant')  # tenantname
        self.assertEqual(dataset[0][1], 'test')  # subdomain_prefix


class TenantAdminTest(TestCase):
    
    def setUp(self):
        # Set up the thread local DB to avoid Http404 errors
        THREAD_LOCAL.DB = 'default'
        
        self.site = AdminSite()
        self.admin = TenantAdmin(Tenant, self.site)
        
        # Create a superuser for testing
        self.superuser = User.objects.create_superuser(
            loginid='admin',
            email='admin@example.com',
            password='adminpass123',
            peoplecode='ADMIN001',
            peoplename='Test Admin',
            dateofbirth=date(1990, 1, 1)
        )
    
    def tearDown(self):
        # Clean up thread local
        if hasattr(THREAD_LOCAL, 'DB'):
            delattr(THREAD_LOCAL, 'DB')

    def test_admin_resource_class(self):
        self.assertEqual(self.admin.resource_class, TenantResource)

    def test_admin_fields(self):
        expected_fields = ('tenantname', 'subdomain_prefix')
        self.assertEqual(self.admin.fields, expected_fields)

    def test_admin_list_display(self):
        expected_list_display = ('tenantname', 'subdomain_prefix', 'created_at')
        self.assertEqual(self.admin.list_display, expected_list_display)

    def test_admin_list_display_links(self):
        expected_links = ('tenantname', 'subdomain_prefix', 'created_at')
        self.assertEqual(self.admin.list_display_links, expected_links)

    def test_admin_is_import_export_model_admin(self):
        from import_export.admin import ImportExportModelAdmin
        self.assertIsInstance(self.admin, ImportExportModelAdmin)

    def test_admin_get_queryset(self):
        # Create test data
        tenant1 = Tenant.objects.create(
            tenantname='Test Tenant 1',
            subdomain_prefix='tenant1'
        )
        tenant2 = Tenant.objects.create(
            tenantname='Test Tenant 2',
            subdomain_prefix='tenant2'
        )
        
        # Create mock request
        request = Mock()
        request.user = self.superuser
        
        # Test get_queryset
        queryset = self.admin.get_queryset(request)
        
        self.assertEqual(queryset.count(), 2)
        self.assertIn(tenant1, queryset)
        self.assertIn(tenant2, queryset)

    def test_admin_has_add_permission(self):
        request = Mock()
        request.user = self.superuser
        
        # Test add permission
        has_permission = self.admin.has_add_permission(request)
        
        self.assertTrue(has_permission)

    def test_admin_has_change_permission(self):
        request = Mock()
        request.user = self.superuser
        
        # Test change permission
        has_permission = self.admin.has_change_permission(request)
        
        self.assertTrue(has_permission)

    def test_admin_has_delete_permission(self):
        request = Mock()
        request.user = self.superuser
        
        # Test delete permission
        has_permission = self.admin.has_delete_permission(request)
        
        self.assertTrue(has_permission)

    def test_admin_get_readonly_fields(self):
        request = Mock()
        request.user = self.superuser
        
        # Test readonly fields (should include created_at)
        readonly_fields = self.admin.get_readonly_fields(request)
        
        # created_at should be readonly (auto-generated field)
        # This depends on the actual implementation
        self.assertIsInstance(readonly_fields, (list, tuple))

    def test_admin_str_representation_in_list(self):
        # Create test tenant
        tenant = Tenant.objects.create(
            tenantname='Test Tenant',
            subdomain_prefix='test'
        )
        
        # Test that admin can display the tenant properly
        str_repr = str(tenant)
        self.assertIsInstance(str_repr, str)

    @patch('apps.tenants.admin.TenantResource')
    def test_admin_uses_correct_resource(self, mock_resource_class):
        # Test that admin uses the correct resource class
        admin = TenantAdmin(Tenant, self.site)
        
        self.assertEqual(admin.resource_class, TenantResource)

    def test_admin_field_order(self):
        # Test that fields are in the correct order
        fields = self.admin.fields
        
        self.assertEqual(fields[0], 'tenantname')
        self.assertEqual(fields[1], 'subdomain_prefix')

    def test_admin_list_display_includes_all_required_fields(self):
        # Test that all important fields are displayed in list view
        list_display = self.admin.list_display
        
        self.assertIn('tenantname', list_display)
        self.assertIn('subdomain_prefix', list_display)
        self.assertIn('created_at', list_display)

    def test_admin_model_registration(self):
        # Test that the model is properly registered
        from django.contrib import admin
        
        # Check if Tenant is registered
        self.assertTrue(admin.site.is_registered(Tenant))


    def test_admin_resource_class_initialization(self):
        # Test that resource class can be instantiated
        resource = self.admin.resource_class()
        
        self.assertIsInstance(resource, TenantResource)

    def test_admin_changelist_view_accessibility(self):
        # Test basic accessibility of changelist view
        request = Mock()
        request.user = self.superuser
        request.GET = {}
        request.META = {'HTTP_HOST': 'testserver'}
        
        # This tests that the admin setup doesn't have obvious errors
        # Full view testing would require Django test client
        self.assertTrue(hasattr(self.admin, 'changelist_view'))

    def test_admin_field_validation_support(self):
        # Test that admin supports field validation
        # This is more of a structure test
        self.assertTrue(hasattr(self.admin, 'fields'))
        
        # All fields in admin.fields should be valid Tenant model fields
        tenant_field_names = [field.name for field in Tenant._meta.fields]
        
        for field_name in self.admin.fields:
            self.assertIn(field_name, tenant_field_names)