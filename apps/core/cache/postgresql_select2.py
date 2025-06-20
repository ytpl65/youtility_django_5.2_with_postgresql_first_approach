"""
PostgreSQL Cache Backend for django-select2
High-performance PostgreSQL caching optimized for Select2 widgets
"""

import json
import time
import logging
from typing import Any, Dict, List, Optional, Union

from django.core.cache.backends.base import BaseCache
from django.db import connection, transaction
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings

logger = logging.getLogger(__name__)


class PostgreSQLSelect2Cache(BaseCache):
    """
    PostgreSQL cache backend optimized for django-select2
    
    Features:
    - Tenant-aware caching
    - Batch operations for performance
    - JSON storage for complex dropdown data
    - Automatic cleanup of expired entries
    - ACID compliance
    """
    
    def __init__(self, location, params):
        super().__init__(params)
        self.location = location
        self._table_name = 'select2_cache'
        self._table_initialized = False
        
        # Get tenant ID from request (simplified for now)
        self._tenant_id = getattr(settings, 'DEFAULT_TENANT_ID', 1)
    
    def _ensure_table_exists(self):
        """Create optimized Select2 cache table (deferred until first use)"""
        if self._table_initialized:
            return
            
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Use advisory lock to prevent concurrent table creation
                    cursor.execute("SELECT pg_advisory_lock(12345678);")
                    
                    try:
                        # Main cache table
                        cursor.execute(f"""
                            CREATE TABLE IF NOT EXISTS {self._table_name} (
                                cache_key VARCHAR(250) NOT NULL,
                                tenant_id INTEGER NOT NULL DEFAULT 1,
                                cache_data TEXT NOT NULL,
                                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                                cache_version INTEGER DEFAULT 1,
                                PRIMARY KEY (cache_key, tenant_id)
                            );
                        """)
                        
                        # Performance indexes
                        cursor.execute(f"""
                            CREATE INDEX IF NOT EXISTS idx_{self._table_name}_expires
                            ON {self._table_name} (expires_at);
                        """)
                        
                        cursor.execute(f"""
                            CREATE INDEX IF NOT EXISTS idx_{self._table_name}_tenant
                            ON {self._table_name} (tenant_id, expires_at);
                        """)
                        
                        # Create cleanup function
                        cursor.execute(f"""
                            CREATE OR REPLACE FUNCTION cleanup_{self._table_name}()
                            RETURNS INTEGER AS $$
                            DECLARE
                                deleted_count INTEGER;
                            BEGIN
                                DELETE FROM {self._table_name}
                                WHERE expires_at < NOW();
                                
                                GET DIAGNOSTICS deleted_count = ROW_COUNT;
                                
                                RETURN deleted_count;
                            END;
                            $$ LANGUAGE plpgsql;
                        """)
                        
                        logger.info(f"Select2 cache table {self._table_name} initialized")
                        self._table_initialized = True
                        
                    finally:
                        # Always release the lock
                        cursor.execute("SELECT pg_advisory_unlock(12345678);")
                
        except Exception as e:
            logger.error(f"Error creating Select2 cache table: {e}")
            # Don't mark as initialized if there was an error
    
    def _get_expiry_timestamp(self, timeout_seconds: int):
        """Get expiry timestamp for cache entries"""
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() + timedelta(seconds=timeout_seconds)
    
    def _make_key(self, key: str, version: Optional[int] = None) -> str:
        """Create versioned cache key"""
        if version is None:
            version = self.version
        return f"v{version}:{key}"
    
    def _get_tenant_id(self) -> int:
        """Get current tenant ID (can be enhanced with request context)"""
        return self._tenant_id
    
    def get(self, key: str, default: Any = None, version: Optional[int] = None) -> Any:
        """Get value from PostgreSQL cache"""
        self._ensure_table_exists()  # Defer table creation until first use
        
        cache_key = self._make_key(key, version)
        tenant_id = self._get_tenant_id()
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT cache_data FROM {self._table_name}
                    WHERE cache_key = %s 
                      AND tenant_id = %s 
                      AND expires_at > NOW()
                """, [cache_key, tenant_id])
                
                result = cursor.fetchone()
                if result:
                    return json.loads(result[0])
                    
        except Exception as e:
            logger.error(f"Select2 cache get error for key {key}: {e}")
        
        return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None, version: Optional[int] = None) -> bool:
        """Set value in PostgreSQL cache"""
        self._ensure_table_exists()  # Defer table creation until first use
        
        cache_key = self._make_key(key, version)
        tenant_id = self._get_tenant_id()
        
        if timeout is None:
            timeout = self.default_timeout
        
        expires_at = self._get_expiry_timestamp(int(timeout))
        
        try:
            cache_data = json.dumps(value, cls=DjangoJSONEncoder)
            
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    INSERT INTO {self._table_name} 
                    (cache_key, tenant_id, cache_data, expires_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (cache_key, tenant_id) 
                    DO UPDATE SET 
                        cache_data = EXCLUDED.cache_data,
                        expires_at = EXCLUDED.expires_at,
                        created_at = NOW()
                """, [cache_key, tenant_id, cache_data, expires_at])
                
            return True
            
        except Exception as e:
            logger.error(f"Select2 cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str, version: Optional[int] = None) -> bool:
        """Delete value from PostgreSQL cache"""
        cache_key = self._make_key(key, version)
        tenant_id = self._get_tenant_id()
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    DELETE FROM {self._table_name} 
                    WHERE cache_key = %s AND tenant_id = %s
                """, [cache_key, tenant_id])
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Select2 cache delete error for key {key}: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries for current tenant"""
        tenant_id = self._get_tenant_id()
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    DELETE FROM {self._table_name} WHERE tenant_id = %s
                """, [tenant_id])
                
            return True
            
        except Exception as e:
            logger.error(f"Select2 cache clear error: {e}")
            return False
    
    def get_many(self, keys: List[str], version: Optional[int] = None) -> Dict[str, Any]:
        """Get multiple values efficiently (batch operation)"""
        if not keys:
            return {}
        
        cache_keys = [self._make_key(key, version) for key in keys]
        tenant_id = self._get_tenant_id()
        
        try:
            with connection.cursor() as cursor:
                placeholders = ','.join(['%s'] * len(cache_keys))
                cursor.execute(f"""
                    SELECT cache_key, cache_data FROM {self._table_name}
                    WHERE cache_key IN ({placeholders})
                      AND tenant_id = %s
                      AND expires_at > NOW()
                """, cache_keys + [tenant_id])
                
                results = {}
                for cache_key, cache_data in cursor.fetchall():
                    # Extract original key from versioned cache_key
                    original_key = cache_key.split(':', 1)[1] if ':' in cache_key else cache_key
                    results[original_key] = json.loads(cache_data)
                
                return results
                
        except Exception as e:
            logger.error(f"Select2 cache get_many error: {e}")
            return {}
    
    def set_many(self, data: Dict[str, Any], timeout: Optional[int] = None, version: Optional[int] = None) -> List[str]:
        """Set multiple values efficiently (batch operation)"""
        if not data:
            return []
        
        if timeout is None:
            timeout = self.default_timeout
        
        tenant_id = self._get_tenant_id()
        expires_at = self._get_expiry_timestamp(int(timeout))
        failed_keys = []
        
        try:
            # Prepare batch data
            batch_data = []
            for key, value in data.items():
                cache_key = self._make_key(key, version)
                cache_data = json.dumps(value, cls=DjangoJSONEncoder)
                batch_data.append((cache_key, tenant_id, cache_data, expires_at))
            
            with connection.cursor() as cursor:
                cursor.executemany(f"""
                    INSERT INTO {self._table_name} 
                    (cache_key, tenant_id, cache_data, expires_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (cache_key, tenant_id) 
                    DO UPDATE SET 
                        cache_data = EXCLUDED.cache_data,
                        expires_at = EXCLUDED.expires_at,
                        created_at = NOW()
                """, batch_data)
                
        except Exception as e:
            logger.error(f"Select2 cache set_many error: {e}")
            failed_keys = list(data.keys())
        
        return failed_keys
    
    def delete_many(self, keys: List[str], version: Optional[int] = None) -> bool:
        """Delete multiple values efficiently"""
        if not keys:
            return True
        
        cache_keys = [self._make_key(key, version) for key in keys]
        tenant_id = self._get_tenant_id()
        
        try:
            with connection.cursor() as cursor:
                placeholders = ','.join(['%s'] * len(cache_keys))
                cursor.execute(f"""
                    DELETE FROM {self._table_name}
                    WHERE cache_key IN ({placeholders}) AND tenant_id = %s
                """, cache_keys + [tenant_id])
                
            return True
            
        except Exception as e:
            logger.error(f"Select2 cache delete_many error: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """Clean up expired cache entries"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT cleanup_{self._table_name}();")
                result = cursor.fetchone()
                deleted_count = result[0] if result else 0
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} expired Select2 cache entries")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"Select2 cache cleanup error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        tenant_id = self._get_tenant_id()
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total_entries,
                        COUNT(*) FILTER (WHERE expires_at > NOW()) as active_entries,
                        COUNT(*) FILTER (WHERE expires_at <= NOW()) as expired_entries,
                        AVG(LENGTH(cache_data)) as avg_data_size
                    FROM {self._table_name}
                    WHERE tenant_id = %s
                """, [tenant_id])
                
                result = cursor.fetchone()
                if result:
                    return {
                        'total_entries': result[0],
                        'active_entries': result[1],
                        'expired_entries': result[2],
                        'avg_data_size_bytes': int(result[3]) if result[3] else 0,
                        'tenant_id': tenant_id
                    }
        
        except Exception as e:
            logger.error(f"Select2 cache stats error: {e}")
        
        return {
            'total_entries': 0,
            'active_entries': 0,
            'expired_entries': 0,
            'avg_data_size_bytes': 0,
            'tenant_id': tenant_id
        }