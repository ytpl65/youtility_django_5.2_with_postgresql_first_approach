from django.test import TestCase, RequestFactory
from django.http import Http404
from django.conf import settings
from unittest.mock import patch, Mock, MagicMock

from apps.tenants.middlewares import TenantMiddleware, TenantDbRouter
from apps.core.utils import THREAD_LOCAL


class TenantMiddlewareTest(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = TenantMiddleware(lambda request: Mock())

    @patch('apps.tenants.middlewares.tenant_db_from_request')
    def test_middleware_sets_thread_local_db(self, mock_tenant_db):
        mock_tenant_db.return_value = 'test_tenant_db'
        
        request = self.factory.get('/')
        
        self.middleware(request)
        
        mock_tenant_db.assert_called_once_with(request)
        self.assertEqual(getattr(THREAD_LOCAL, 'DB'), 'test_tenant_db')

    @patch('apps.tenants.middlewares.tenant_db_from_request')
    def test_middleware_calls_get_response(self, mock_tenant_db):
        mock_tenant_db.return_value = 'test_db'
        mock_get_response = Mock()
        mock_get_response.return_value = 'response'
        
        middleware = TenantMiddleware(mock_get_response)
        request = self.factory.get('/')
        
        response = middleware(request)
        
        mock_get_response.assert_called_once_with(request)
        self.assertEqual(response, 'response')

    @patch('apps.tenants.middlewares.tenant_db_from_request')
    def test_middleware_with_different_databases(self, mock_tenant_db):
        databases = ['db1', 'db2', 'default']
        
        for db in databases:
            mock_tenant_db.return_value = db
            request = self.factory.get('/')
            
            self.middleware(request)
            
            self.assertEqual(getattr(THREAD_LOCAL, 'DB'), db)

    def test_middleware_initialization(self):
        get_response = Mock()
        middleware = TenantMiddleware(get_response)
        
        self.assertEqual(middleware.get_response, get_response)


class TenantDbRouterTest(TestCase):
    
    def setUp(self):
        self.router = TenantDbRouter()

    def test_multi_db_with_thread_local_db(self):
        # Set up THREAD_LOCAL.DB
        setattr(THREAD_LOCAL, 'DB', 'test_tenant_db')
        
        with patch.object(settings, 'DATABASES', {'test_tenant_db': {}, 'default': {}}):
            result = self.router._multi_db()
            
        self.assertEqual(result, 'test_tenant_db')

    def test_multi_db_without_thread_local_db(self):
        # Clear THREAD_LOCAL.DB
        if hasattr(THREAD_LOCAL, 'DB'):
            delattr(THREAD_LOCAL, 'DB')
        
        result = self.router._multi_db()
        
        self.assertEqual(result, 'default')

    def test_multi_db_with_invalid_database(self):
        # Set THREAD_LOCAL.DB to a database not in settings
        setattr(THREAD_LOCAL, 'DB', 'nonexistent_db')
        
        with patch.object(settings, 'DATABASES', {'default': {}, 'other_db': {}}):
            with self.assertRaises(Http404):
                self.router._multi_db()

    def test_db_for_read(self):
        setattr(THREAD_LOCAL, 'DB', 'read_db')
        
        with patch.object(settings, 'DATABASES', {'read_db': {}, 'default': {}}):
            result = self.router.db_for_read(Mock())
            
        self.assertEqual(result, 'read_db')

    def test_db_for_write(self):
        setattr(THREAD_LOCAL, 'DB', 'write_db')
        
        with patch.object(self.router, 'db_for_read') as mock_db_for_read:
            mock_db_for_read.return_value = 'write_db'
            
            result = self.router.db_for_write(Mock())
            
        mock_db_for_read.assert_called_once()
        self.assertEqual(result, 'write_db')

    def test_db_for_read_with_model_hints(self):
        setattr(THREAD_LOCAL, 'DB', 'model_db')
        
        with patch.object(settings, 'DATABASES', {'model_db': {}, 'default': {}}):
            result = self.router.db_for_read(Mock(), instance=Mock(), some_hint='value')
            
        self.assertEqual(result, 'model_db')

    def test_allow_relation_always_true(self):
        obj1 = Mock()
        obj2 = Mock()
        
        result = self.router.allow_relation(obj1, obj2)
        
        self.assertTrue(result)

    def test_allow_relation_with_hints(self):
        obj1 = Mock()
        obj2 = Mock()
        
        result = self.router.allow_relation(obj1, obj2, some_hint='value')
        
        self.assertTrue(result)

    def test_allow_migrate_always_true(self):
        result = self.router.allow_migrate('test_db', 'test_app')
        
        self.assertTrue(result)

    def test_allow_migrate_with_model_name(self):
        result = self.router.allow_migrate('test_db', 'test_app', 'TestModel')
        
        self.assertTrue(result)

    def test_allow_migrate_with_hints(self):
        result = self.router.allow_migrate(
            'test_db', 
            'test_app', 
            'TestModel', 
            some_hint='value'
        )
        
        self.assertTrue(result)

    def test_router_consistency(self):
        # Test that db_for_read and db_for_write return the same database
        setattr(THREAD_LOCAL, 'DB', 'consistent_db')
        
        with patch.object(settings, 'DATABASES', {'consistent_db': {}, 'default': {}}):
            read_db = self.router.db_for_read(Mock())
            write_db = self.router.db_for_write(Mock())
            
        self.assertEqual(read_db, write_db)

    def test_multiple_database_scenarios(self):
        test_cases = [
            ('tenant1_db', {'tenant1_db': {}, 'default': {}}),
            ('tenant2_db', {'tenant2_db': {}, 'default': {}}),
            ('main_db', {'main_db': {}, 'default': {}})
        ]
        
        for db_name, databases in test_cases:
            setattr(THREAD_LOCAL, 'DB', db_name)
            
            with patch.object(settings, 'DATABASES', databases):
                result = self.router.db_for_read(Mock())
                
            self.assertEqual(result, db_name)

    def test_thread_local_cleanup(self):
        # Test router behavior when THREAD_LOCAL is modified during execution
        setattr(THREAD_LOCAL, 'DB', 'initial_db')
        
        with patch.object(settings, 'DATABASES', {'initial_db': {}, 'default': {}}):
            # Get initial result
            result1 = self.router.db_for_read(Mock())
            
            # Change THREAD_LOCAL.DB
            setattr(THREAD_LOCAL, 'DB', 'changed_db')
            
            with patch.object(settings, 'DATABASES', {'changed_db': {}, 'default': {}}):
                result2 = self.router.db_for_read(Mock())
            
        self.assertEqual(result1, 'initial_db')
        self.assertEqual(result2, 'changed_db')

    def test_error_propagation(self):
        # Test that Http404 is properly raised when database is not found
        setattr(THREAD_LOCAL, 'DB', 'nonexistent')
        
        with patch.object(settings, 'DATABASES', {'default': {}}):
            with self.assertRaises(Http404):
                self.router.db_for_read(Mock())

    def test_static_method_independence(self):
        # Test that static methods work independently of instance
        router1 = TenantDbRouter()
        router2 = TenantDbRouter()
        
        # Test allow_relation
        result1 = router1.allow_relation(Mock(), Mock())
        result2 = router2.allow_relation(Mock(), Mock())
        
        self.assertEqual(result1, result2)
        self.assertTrue(result1)
        
        # Test allow_migrate
        result1 = router1.allow_migrate('db1', 'app1')
        result2 = router2.allow_migrate('db2', 'app2')
        
        self.assertEqual(result1, result2)
        self.assertTrue(result1)