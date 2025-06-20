"""
Enhanced PostgreSQL Select2 Cache Backend with Materialized Views
Integrates materialized views for ultra-fast dropdown access
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


class MaterializedViewSelect2Cache(BaseCache):
    """
    Enhanced PostgreSQL Select2 cache backend with materialized view integration
    
    Features:
    - Ultra-fast materialized view access for static dropdowns
    - Fallback to standard cache for dynamic data
    - Automatic detection of materialized view candidates
    - Standard cache backend compatibility
    """
    
    # Materialized view mappings
    MATERIALIZED_VIEWS = {
        'people_dropdown': 'mv_people_dropdown',
        'location_dropdown': 'mv_location_dropdown', 
        'asset_dropdown': 'mv_asset_dropdown',
        # Add more mappings as needed
    }
    
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
    
    def _is_materialized_view_candidate(self, key: str) -> Optional[str]:
        """Check if key maps to a materialized view"""
        key_lower = key.lower()
        for pattern, mv_name in self.MATERIALIZED_VIEWS.items():
            if pattern.replace('_dropdown', '') in key_lower:
                return mv_name
        return None
    
    def _get_from_materialized_view(self, mv_name: str, tenant_id: int = None) -> Optional[Any]:
        """Get data from materialized view"""
        try:
            with connection.cursor() as cursor:
                # Build query based on materialized view
                if mv_name == 'mv_people_dropdown':
                    cursor.execute("""
                        SELECT json_build_object(
                            'results', COALESCE(
                                json_agg(
                                    json_build_object(
                                        'id', id,
                                        'text', text,
                                        'loginid', loginid,
                                        'email', email,
                                        'mobno', mobno
                                    )
                                    ORDER BY text
                                ) FILTER (WHERE id IS NOT NULL),
                                '[]'::json
                            ),
                            'pagination', json_build_object('more', false),
                            'total_count', COALESCE(count(*) FILTER (WHERE id IS NOT NULL), 0)
                        )
                        FROM mv_people_dropdown
                        WHERE (%s IS NULL OR tenant_id = %s);
                    """, [tenant_id, tenant_id])
                    
                elif mv_name == 'mv_location_dropdown':
                    cursor.execute("""
                        SELECT json_build_object(
                            'results', COALESCE(
                                json_agg(
                                    json_build_object(
                                        'id', id,
                                        'text', text,
                                        'loccode', loccode,
                                        'iscritical', iscritical
                                    )
                                    ORDER BY text
                                ) FILTER (WHERE id IS NOT NULL),
                                '[]'::json
                            ),
                            'pagination', json_build_object('more', false),
                            'total_count', COALESCE(count(*) FILTER (WHERE id IS NOT NULL), 0)
                        )
                        FROM mv_location_dropdown
                        WHERE (%s IS NULL OR tenant_id = %s);
                    """, [tenant_id, tenant_id])
                    
                elif mv_name == 'mv_asset_dropdown':
                    cursor.execute("""
                        SELECT json_build_object(
                            'results', COALESCE(
                                json_agg(
                                    json_build_object(
                                        'id', id,
                                        'text', text,
                                        'assetcode', assetcode,
                                        'location_name', location_name,
                                        'location_id', location_id
                                    )
                                    ORDER BY text
                                ) FILTER (WHERE id IS NOT NULL),
                                '[]'::json
                            ),
                            'pagination', json_build_object('more', false),
                            'total_count', COALESCE(count(*) FILTER (WHERE id IS NOT NULL), 0)
                        )
                        FROM mv_asset_dropdown
                        WHERE (%s IS NULL OR tenant_id = %s);
                    """, [tenant_id, tenant_id])
                
                result = cursor.fetchone()
                if result and result[0]:
                    return result[0]
                    
        except Exception as e:
            logger.error(f"Materialized view query error for {mv_name}: {e}")
        
        return None
    
    def get(self, key: str, default: Any = None, version: Optional[int] = None) -> Any:
        """Get value from cache, with materialized view optimization"""
        self._ensure_table_exists()  # Defer table creation until first use
        
        cache_key = self._make_key(key, version)
        tenant_id = self._get_tenant_id()
        
        # Check if this key can use a materialized view
        mv_name = self._is_materialized_view_candidate(key)
        if mv_name:
            logger.debug(f"Attempting materialized view lookup for {key} -> {mv_name}")
            # Try with tenant filter first, then without if no results
            mv_data = self._get_from_materialized_view(mv_name, tenant_id)
            if mv_data and mv_data.get('total_count', 0) > 0:
                logger.info(f"Materialized view hit for {key}")
                return mv_data
            elif mv_data and mv_data.get('total_count', 0) == 0:
                # Try without tenant filter for development/testing
                mv_data_no_tenant = self._get_from_materialized_view(mv_name, None)
                if mv_data_no_tenant and mv_data_no_tenant.get('total_count', 0) > 0:
                    logger.info(f"Materialized view hit for {key} (no tenant filter)")
                    return mv_data_no_tenant
            logger.debug(f"Materialized view miss for {key}, falling back to cache")
        
        # Fallback to standard cache lookup
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
        """Set value in PostgreSQL cache (standard implementation)"""
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
        """Get multiple values efficiently (with MV optimization)"""
        if not keys:
            return {}
        
        results = {}
        remaining_keys = []
        
        # First, try materialized views for applicable keys
        for key in keys:
            mv_name = self._is_materialized_view_candidate(key)
            if mv_name:
                mv_data = self._get_from_materialized_view(mv_name, self._get_tenant_id())
                if mv_data:
                    results[key] = mv_data
                else:
                    remaining_keys.append(key)
            else:
                remaining_keys.append(key)
        
        # Then get remaining keys from standard cache
        if remaining_keys:
            cache_keys = [self._make_key(key, version) for key in remaining_keys]
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
                    
                    for cache_key, cache_data in cursor.fetchall():
                        # Extract original key from versioned cache_key
                        original_key = cache_key.split(':', 1)[1] if ':' in cache_key else cache_key
                        results[original_key] = json.loads(cache_data)
                    
            except Exception as e:
                logger.error(f"Select2 cache get_many error: {e}")
        
        return results
    
    def set_many(self, data: Dict[str, Any], timeout: Optional[int] = None, version: Optional[int] = None) -> List[str]:
        """Set multiple values efficiently (standard implementation)"""
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
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics including materialized view info"""
        tenant_id = self._get_tenant_id()
        
        try:
            with connection.cursor() as cursor:
                # Standard cache stats
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
                stats = {
                    'total_entries': result[0] if result else 0,
                    'active_entries': result[1] if result else 0,
                    'expired_entries': result[2] if result else 0,
                    'avg_data_size_bytes': int(result[3]) if result and result[3] else 0,
                    'tenant_id': tenant_id
                }
                
                # Materialized view stats
                mv_stats = {}
                for pattern, mv_name in self.MATERIALIZED_VIEWS.items():
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {mv_name};")
                        count = cursor.fetchone()[0]
                        mv_stats[mv_name] = count
                    except:
                        mv_stats[mv_name] = 'unavailable'
                
                stats['materialized_views'] = mv_stats
                return stats
        
        except Exception as e:
            logger.error(f"Select2 cache stats error: {e}")
        
        return {
            'total_entries': 0,
            'active_entries': 0,
            'expired_entries': 0,
            'avg_data_size_bytes': 0,
            'tenant_id': tenant_id,
            'materialized_views': {}
        }
    
    def cleanup_expired(self) -> int:
        """Clean up expired cache entries"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    DELETE FROM {self._table_name}
                    WHERE expires_at < NOW()
                """)
                deleted_count = cursor.rowcount
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} expired Select2 cache entries")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"Select2 cache cleanup error: {e}")
            return 0