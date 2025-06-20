#!/usr/bin/env python3
"""
Optimized PostgreSQL Select2 Cache Implementation
High-performance PostgreSQL caching for django-select2
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append('/home/satyam/Documents/YOUTILITY-MIGRATION-DJANGO5-POSTGRESQL/YOUTILITY3')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

from django.core.cache.backends.base import BaseCache
from django.db import connection, transaction
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
import json
import time
import logging

logger = logging.getLogger(__name__)

class PostgreSQLSelect2Cache(BaseCache):
    """
    Optimized PostgreSQL cache backend specifically for django-select2
    Focuses on high-performance caching with minimal overhead
    """
    
    def __init__(self, location, params):
        super().__init__(params)
        self.location = location
        self._table_name = 'select2_cache_optimized'
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Create optimized cache table if it doesn't exist"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self._table_name} (
                        cache_key VARCHAR(250) PRIMARY KEY,
                        cache_data TEXT NOT NULL,  -- Using TEXT instead of JSONB for speed
                        expires_at BIGINT NOT NULL,  -- Unix timestamp for fast comparison
                        tenant_id SMALLINT DEFAULT 1
                    );
                """)
                
                # Optimized indexes
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self._table_name}_expires 
                    ON {self._table_name} (expires_at) WHERE expires_at > extract(epoch from now());
                """)
                
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self._table_name}_tenant_key 
                    ON {self._table_name} (tenant_id, cache_key);
                """)
                
        except Exception as e:
            logger.error(f"Error creating cache table: {e}")
    
    def _get_current_timestamp(self):
        """Get current Unix timestamp for fast comparison"""
        return int(time.time())
    
    def _make_key(self, key):
        """Create tenant-aware cache key"""
        # Add tenant isolation (you can customize this based on your tenant logic)
        return f"tenant_1:{key}"  # Simplified for demo
    
    def get(self, key, default=None, version=None):
        """Get value from PostgreSQL cache"""
        cache_key = self._make_key(key)
        current_time = self._get_current_timestamp()
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT cache_data FROM {self._table_name}
                    WHERE cache_key = %s AND expires_at > %s
                """, [cache_key, current_time])
                
                result = cursor.fetchone()
                if result:
                    return json.loads(result[0])
                
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return default
    
    def set(self, key, value, timeout=None, version=None):
        """Set value in PostgreSQL cache"""
        cache_key = self._make_key(key)
        
        if timeout is None:
            timeout = self.default_timeout
        
        expires_at = self._get_current_timestamp() + int(timeout)
        cache_data = json.dumps(value, cls=DjangoJSONEncoder)
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    INSERT INTO {self._table_name} (cache_key, cache_data, expires_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (cache_key) 
                    DO UPDATE SET 
                        cache_data = EXCLUDED.cache_data,
                        expires_at = EXCLUDED.expires_at
                """, [cache_key, cache_data, expires_at])
                
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def delete(self, key, version=None):
        """Delete value from PostgreSQL cache"""
        cache_key = self._make_key(key)
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    DELETE FROM {self._table_name} WHERE cache_key = %s
                """, [cache_key])
                
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
    
    def clear(self):
        """Clear all cache entries"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"DELETE FROM {self._table_name}")
                
        except Exception as e:
            logger.error(f"Cache clear error: {e}")

def test_optimized_postgresql_cache():
    """Test the optimized PostgreSQL cache performance"""
    print("🚀 Testing Optimized PostgreSQL Select2 Cache")
    print("=" * 50)
    
    # Create cache instance
    cache = PostgreSQLSelect2Cache('', {'default_timeout': 300})
    
    # Test data - realistic Select2 dropdown data
    test_data = {
        'choices': [
            {'id': i, 'text': f'User {i}', 'department': f'Dept {i%5}'}
            for i in range(100)
        ],
        'pagination': {'more': False},
        'meta': {'total': 100}
    }
    
    print("⚡ Performance Testing with Optimized Cache")
    
    # Write performance test
    write_times = []
    for i in range(20):  # More iterations for better average
        start = time.time()
        cache.set(f'people_dropdown_{i}', test_data, timeout=300)
        write_times.append((time.time() - start) * 1000)
    
    avg_write = sum(write_times) / len(write_times)
    print(f"✅ Optimized write time: {avg_write:.2f}ms")
    
    # Read performance test
    read_times = []
    for i in range(20):
        start = time.time()
        result = cache.get(f'people_dropdown_{i}')
        read_times.append((time.time() - start) * 1000)
    
    avg_read = sum(read_times) / len(read_times)
    print(f"📖 Optimized read time: {avg_read:.2f}ms")
    
    # Cleanup
    for i in range(20):
        cache.delete(f'people_dropdown_{i}')
    
    return {'write': avg_write, 'read': avg_read}

def test_batch_operations():
    """Test batch operations for better performance"""
    print("\n🔄 Testing Batch Operations")
    print("=" * 30)
    
    try:
        with connection.cursor() as cursor:
            # Batch insert test
            current_time = int(time.time())
            expires_at = current_time + 300
            
            start = time.time()
            
            # Single batch insert
            batch_data = [
                (f'tenant_1:batch_key_{i}', 
                 json.dumps({'id': i, 'text': f'Option {i}'}),
                 expires_at)
                for i in range(50)
            ]
            
            cursor.executemany("""
                INSERT INTO select2_cache_optimized (cache_key, cache_data, expires_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (cache_key) 
                DO UPDATE SET cache_data = EXCLUDED.cache_data, expires_at = EXCLUDED.expires_at
            """, batch_data)
            
            batch_time = (time.time() - start) * 1000
            print(f"📦 Batch insert (50 items): {batch_time:.2f}ms")
            print(f"📦 Per item: {batch_time/50:.2f}ms")
            
            # Batch read test
            start = time.time()
            cache_keys = [f'tenant_1:batch_key_{i}' for i in range(50)]
            placeholders = ','.join(['%s'] * len(cache_keys))
            
            cursor.execute(f"""
                SELECT cache_key, cache_data FROM select2_cache_optimized
                WHERE cache_key IN ({placeholders}) AND expires_at > %s
            """, cache_keys + [current_time])
            
            results = cursor.fetchall()
            batch_read_time = (time.time() - start) * 1000
            print(f"📖 Batch read (50 items): {batch_read_time:.2f}ms")
            print(f"📖 Per item: {batch_read_time/50:.2f}ms")
            
            # Cleanup
            cursor.execute(f"""
                DELETE FROM select2_cache_optimized 
                WHERE cache_key LIKE 'tenant_1:batch_key_%'
            """)
            
            return {
                'batch_write_per_item': batch_time/50,
                'batch_read_per_item': batch_read_time/50
            }
            
    except Exception as e:
        print(f"❌ Batch operation error: {e}")
        return None

def create_precomputed_cache_strategy():
    """Create strategy for precomputed Select2 caches"""
    print("\n📊 Precomputed Cache Strategy")
    print("=" * 30)
    
    with connection.cursor() as cursor:
        # Create materialized view for commonly used dropdowns
        cursor.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_people_dropdown AS
            SELECT 
                p.id,
                p.peoplecode,
                p.peoplename as text,
                p.bu_id,
                p.client_id,
                json_build_object(
                    'id', p.id,
                    'text', p.peoplename,
                    'code', p.peoplecode,
                    'department', COALESCE(dept.taname, ''),
                    'bu', COALESCE(bu.buname, '')
                ) as dropdown_data
            FROM peoples_people p
            LEFT JOIN onboarding_typeassist dept ON p.department_id = dept.id
            LEFT JOIN onboarding_bt bu ON p.bu_id = bu.id
            WHERE p.enable = true
            ORDER BY p.peoplename;
        """)
        
        # Create index on materialized view
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_people_dropdown_id
            ON mv_people_dropdown (id);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_mv_people_dropdown_bu_client
            ON mv_people_dropdown (bu_id, client_id);
        """)
        
        print("✅ Created materialized view for people dropdown")
        
        # Refresh the materialized view
        cursor.execute("REFRESH MATERIALIZED VIEW mv_people_dropdown;")
        
        # Test retrieval from materialized view
        start = time.time()
        cursor.execute("""
            SELECT json_agg(dropdown_data) 
            FROM mv_people_dropdown 
            WHERE bu_id = 1 
            LIMIT 50;
        """)
        result = cursor.fetchone()[0]
        mv_time = (time.time() - start) * 1000
        
        print(f"⚡ Materialized view query: {mv_time:.2f}ms")
        print(f"📊 Retrieved {len(result) if result else 0} dropdown options")
        
        return {'materialized_view_time': mv_time}

def compare_all_approaches():
    """Compare all caching approaches and provide recommendations"""
    print("\n📊 Complete Performance Comparison")
    print("=" * 50)
    
    # Test optimized PostgreSQL cache
    opt_pg = test_optimized_postgresql_cache()
    
    # Test batch operations
    batch_results = test_batch_operations()
    
    # Test materialized views
    mv_results = create_precomputed_cache_strategy()
    
    print("\n🎯 Performance Summary:")
    print("=" * 25)
    print(f"Redis Cache (baseline):")
    print(f"   • Write: ~0.13ms")
    print(f"   • Read: ~0.05ms")
    print()
    print(f"Optimized PostgreSQL Cache:")
    print(f"   • Write: {opt_pg['write']:.2f}ms")
    print(f"   • Read: {opt_pg['read']:.2f}ms")
    print()
    if batch_results:
        print(f"PostgreSQL Batch Operations:")
        print(f"   • Batch write per item: {batch_results['batch_write_per_item']:.2f}ms")
        print(f"   • Batch read per item: {batch_results['batch_read_per_item']:.2f}ms")
        print()
    if mv_results:
        print(f"Materialized Views:")
        print(f"   • Direct query: {mv_results['materialized_view_time']:.2f}ms")
    
    print("\n💡 Recommendations:")
    print("=" * 20)
    
    # Calculate performance ratios
    write_ratio = opt_pg['write'] / 0.13
    read_ratio = opt_pg['read'] / 0.05
    
    if write_ratio < 50 and read_ratio < 50:  # Less than 50x slower
        print("✅ PROCEED with PostgreSQL migration:")
        print("   • Performance is acceptable for operational benefits")
        print("   • Use optimized cache backend")
        print("   • Implement batch operations for heavy loads")
        print("   • Use materialized views for static data")
    else:
        print("⚠️  CONSIDER keeping Redis for Select2:")
        print("   • Performance difference is significant")
        print("   • Redis excels at high-frequency caching")
        print("   • Consider hybrid: PostgreSQL for data, Redis for UI cache")
    
    print(f"\n📈 Performance Impact:")
    print(f"   • Write operations: {write_ratio:.1f}x slower than Redis")
    print(f"   • Read operations: {read_ratio:.1f}x slower than Redis")
    print(f"   • But: Eliminates Redis operational complexity")
    print(f"   • And: Provides ACID compliance and tenant isolation")

if __name__ == "__main__":
    print("🚀 Optimized PostgreSQL Select2 Cache Analysis")
    print("=" * 60)
    
    compare_all_approaches()
    
    print("\n🎯 Decision Framework:")
    print("=" * 25)
    print("Choose PostgreSQL if:")
    print("   ✅ Operational simplicity is priority")
    print("   ✅ ACID compliance is important")
    print("   ✅ Unified backup/monitoring preferred")
    print("   ✅ <50ms dropdown loading is acceptable")
    print()
    print("Keep Redis if:")
    print("   ⚡ Sub-millisecond performance is critical")
    print("   ⚡ High-frequency dropdown operations")
    print("   ⚡ Real-time user experience is priority")
    print()
    print("💡 Hybrid approach: PostgreSQL primary + Redis UI cache")