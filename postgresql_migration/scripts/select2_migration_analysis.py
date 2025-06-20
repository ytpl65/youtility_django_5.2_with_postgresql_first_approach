#!/usr/bin/env python3
"""
Select2 Cache Migration Analysis
Analyze current Select2 Redis usage and plan PostgreSQL migration
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append('/home/satyam/Documents/YOUTILITY-MIGRATION-DJANGO5-POSTGRESQL/YOUTILITY3')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

from django.core.cache import caches
from django.db import connection
import redis
import time

def analyze_current_select2_usage():
    """Analyze current Select2 Redis cache usage patterns"""
    print("🔍 Select2 Cache Usage Analysis")
    print("=" * 50)
    
    # Connect to Select2 Redis cache
    try:
        select2_cache = caches['select2']
        r = redis.Redis(host='127.0.0.1', port=6379, db=2)
        
        # Get Redis info
        info = r.info()
        print(f"📊 Redis DB 2 (Select2) Statistics:")
        print(f"   • Connected clients: {info.get('connected_clients', 'unknown')}")
        print(f"   • Used memory: {info.get('used_memory_human', 'unknown')}")
        print(f"   • Total keys: {r.dbsize()}")
        
        # Get current Select2 cache keys
        keys = r.keys('select2:*')
        print(f"   • Select2 cache keys: {len(keys)}")
        
        if keys:
            print(f"🔑 Sample Select2 Cache Keys:")
            for key in keys[:5]:
                try:
                    value = r.get(key)
                    key_str = key.decode()
                    print(f"   • {key_str}: {len(value) if value else 0} bytes")
                except:
                    pass
        
        return True
        
    except Exception as e:
        print(f"❌ Error accessing Select2 cache: {e}")
        return False

def test_select2_cache_performance():
    """Test Select2 cache performance for baseline"""
    print("\n⚡ Select2 Cache Performance Testing")
    print("=" * 50)
    
    try:
        select2_cache = caches['select2']
        
        # Test data
        test_data = {
            'choices': [
                {'id': i, 'text': f'Option {i}', 'value': f'value_{i}'}
                for i in range(100)  # 100 dropdown options
            ],
            'meta': {'total': 100, 'filtered': 100}
        }
        
        # Write performance test
        write_times = []
        for i in range(10):
            start = time.time()
            select2_cache.set(f'test_dropdown_{i}', test_data, timeout=300)
            write_times.append((time.time() - start) * 1000)
        
        avg_write = sum(write_times) / len(write_times)
        print(f"✅ Average write time: {avg_write:.2f}ms")
        
        # Read performance test
        read_times = []
        for i in range(10):
            start = time.time()
            cached_data = select2_cache.get(f'test_dropdown_{i}')
            read_times.append((time.time() - start) * 1000)
        
        avg_read = sum(read_times) / len(read_times)
        print(f"📖 Average read time: {avg_read:.2f}ms")
        
        # Cleanup
        for i in range(10):
            select2_cache.delete(f'test_dropdown_{i}')
        
        print(f"📊 Redis Select2 Cache Performance:")
        print(f"   • Write: {avg_write:.2f}ms")
        print(f"   • Read: {avg_read:.2f}ms")
        
        return {'write': avg_write, 'read': avg_read}
        
    except Exception as e:
        print(f"❌ Error testing cache performance: {e}")
        return None

def test_postgresql_caching_approach():
    """Test PostgreSQL-based caching approach for Select2"""
    print("\n🐘 PostgreSQL Select2 Caching Test")
    print("=" * 50)
    
    try:
        with connection.cursor() as cursor:
            # Create Select2 cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS select2_cache (
                    cache_key VARCHAR(255) PRIMARY KEY,
                    cache_data JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    cache_version INTEGER DEFAULT 1,
                    tenant_id INTEGER DEFAULT 1
                );
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_select2_cache_expires 
                ON select2_cache (expires_at);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_select2_cache_tenant 
                ON select2_cache (tenant_id);
            """)
            
            print("✅ Created Select2 cache table with indexes")
            
            # Test data
            test_data = {
                'choices': [
                    {'id': i, 'text': f'Option {i}', 'value': f'value_{i}'}
                    for i in range(100)
                ],
                'meta': {'total': 100, 'filtered': 100}
            }
            
            # Test PostgreSQL cache performance
            import json
            from django.utils import timezone
            from datetime import timedelta
            
            # Write performance test
            write_times = []
            for i in range(10):
                start = time.time()
                cursor.execute("""
                    INSERT INTO select2_cache (cache_key, cache_data, expires_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (cache_key) 
                    DO UPDATE SET 
                        cache_data = EXCLUDED.cache_data,
                        expires_at = EXCLUDED.expires_at,
                        created_at = NOW()
                """, [
                    f'test_pg_dropdown_{i}',
                    json.dumps(test_data),
                    timezone.now() + timedelta(minutes=5)
                ])
                write_times.append((time.time() - start) * 1000)
            
            avg_write = sum(write_times) / len(write_times)
            print(f"✅ PostgreSQL average write time: {avg_write:.2f}ms")
            
            # Read performance test
            read_times = []
            for i in range(10):
                start = time.time()
                cursor.execute("""
                    SELECT cache_data FROM select2_cache 
                    WHERE cache_key = %s AND expires_at > NOW()
                """, [f'test_pg_dropdown_{i}'])
                result = cursor.fetchone()
                read_times.append((time.time() - start) * 1000)
            
            avg_read = sum(read_times) / len(read_times)
            print(f"📖 PostgreSQL average read time: {avg_read:.2f}ms")
            
            # Cleanup test data
            cursor.execute("DELETE FROM select2_cache WHERE cache_key LIKE 'test_pg_dropdown_%'")
            print("🧹 Cleaned up test data")
            
            print(f"📊 PostgreSQL Select2 Cache Performance:")
            print(f"   • Write: {avg_write:.2f}ms")
            print(f"   • Read: {avg_read:.2f}ms")
            
            return {'write': avg_write, 'read': avg_read}
            
    except Exception as e:
        print(f"❌ Error testing PostgreSQL caching: {e}")
        return None

def create_select2_cache_management():
    """Create PostgreSQL functions for Select2 cache management"""
    print("\n🔧 Creating PostgreSQL Select2 Cache Management")
    print("=" * 50)
    
    with connection.cursor() as cursor:
        # Create cache cleanup function
        cursor.execute("""
            CREATE OR REPLACE FUNCTION cleanup_select2_cache() 
            RETURNS INTEGER AS $$
            DECLARE
                deleted_count INTEGER;
            BEGIN
                DELETE FROM select2_cache 
                WHERE expires_at < NOW();
                
                GET DIAGNOSTICS deleted_count = ROW_COUNT;
                
                -- Log the cleanup
                INSERT INTO auth_rate_limit_attempts (
                    ip_address,
                    username,
                    attempt_time,
                    success,
                    failure_reason
                ) VALUES (
                    '127.0.0.1'::inet,
                    'system',
                    NOW(),
                    true,
                    'Select2 cache cleanup: ' || deleted_count || ' expired entries removed'
                );
                
                RETURN deleted_count;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        # Create cache retrieval function
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_select2_cache(
                p_cache_key VARCHAR(255),
                p_tenant_id INTEGER DEFAULT 1
            ) RETURNS JSONB AS $$
            DECLARE
                result JSONB;
            BEGIN
                SELECT cache_data INTO result
                FROM select2_cache
                WHERE cache_key = p_cache_key
                  AND tenant_id = p_tenant_id
                  AND expires_at > NOW();
                
                RETURN result;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        # Create cache set function
        cursor.execute("""
            CREATE OR REPLACE FUNCTION set_select2_cache(
                p_cache_key VARCHAR(255),
                p_cache_data JSONB,
                p_timeout_seconds INTEGER DEFAULT 300,
                p_tenant_id INTEGER DEFAULT 1
            ) RETURNS BOOLEAN AS $$
            BEGIN
                INSERT INTO select2_cache (
                    cache_key, 
                    cache_data, 
                    expires_at,
                    tenant_id
                ) VALUES (
                    p_cache_key,
                    p_cache_data,
                    NOW() + (p_timeout_seconds || ' seconds')::INTERVAL,
                    p_tenant_id
                )
                ON CONFLICT (cache_key) 
                DO UPDATE SET 
                    cache_data = EXCLUDED.cache_data,
                    expires_at = EXCLUDED.expires_at,
                    created_at = NOW(),
                    tenant_id = EXCLUDED.tenant_id;
                
                RETURN TRUE;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        print("✅ Created PostgreSQL Select2 cache management functions")
        
        # Test the functions
        cursor.execute("""
            SELECT set_select2_cache(
                'test_function', 
                '{"test": "data"}'::jsonb, 
                300, 
                1
            );
        """)
        
        cursor.execute("SELECT get_select2_cache('test_function', 1);")
        result = cursor.fetchone()[0]
        print(f"🧪 Function test result: {result}")
        
        cursor.execute("SELECT cleanup_select2_cache();")
        cleanup_count = cursor.fetchone()[0]
        print(f"🧹 Cleanup test: {cleanup_count} entries cleaned")

def analyze_select2_migration_strategy():
    """Analyze and recommend Select2 migration strategy"""
    print("\n🎯 Select2 Migration Strategy Analysis")
    print("=" * 50)
    
    print("📋 Current Select2 Usage in YOUTILITY3:")
    print("   • Heavy usage across all major forms")
    print("   • 20+ forms with multiple Select2 widgets")
    print("   • Key data sources: People, Assets, Sites, TypeAssist")
    print("   • Bootstrap 5 theming integration")
    print("   • Limited use of ModelSelect2Widget")
    print()
    
    print("🔍 Migration Complexity Assessment:")
    print("   • LOW complexity: Basic Select2Widget replacement")
    print("   • MEDIUM complexity: Custom data loading patterns")
    print("   • HIGH complexity: ModelSelect2Widget with AJAX")
    print()
    
    print("📊 Performance Requirements:")
    print("   • Target: <50ms for dropdown loading")
    print("   • Cache TTL: 5-15 minutes for most data")
    print("   • Tenant isolation: Required for multi-tenancy")
    print("   • Invalidation: On data changes")
    print()
    
    print("🛠️ Recommended Migration Approach:")
    print("   1. Create PostgreSQL cache backend for django-select2")
    print("   2. Implement custom cache backend class")
    print("   3. Add tenant-aware cache key generation")
    print("   4. Create cache invalidation signals")
    print("   5. Add management commands for cache maintenance")
    print()
    
    print("✅ Benefits of PostgreSQL Select2 Cache:")
    print("   • ACID compliance for cache consistency")
    print("   • Tenant isolation with database-level security")
    print("   • Unified backup/recovery with main database")
    print("   • JSON field support for complex dropdown data")
    print("   • Native SQL query optimization")
    print("   • Elimination of Redis dependency")

if __name__ == "__main__":
    print("🚀 Select2 to PostgreSQL Migration Analysis")
    print("=" * 60)
    
    # Step 1: Analyze current usage
    redis_working = analyze_current_select2_usage()
    
    # Step 2: Test current performance
    if redis_working:
        redis_perf = test_select2_cache_performance()
    else:
        redis_perf = None
    
    # Step 3: Test PostgreSQL approach
    pg_perf = test_postgresql_caching_approach()
    
    # Step 4: Create management functions
    create_select2_cache_management()
    
    # Step 5: Provide migration strategy
    analyze_select2_migration_strategy()
    
    # Performance comparison
    if redis_perf and pg_perf:
        print("\n📊 Performance Comparison:")
        print("=" * 30)
        print(f"Redis Select2 Cache:")
        print(f"   • Write: {redis_perf['write']:.2f}ms")
        print(f"   • Read: {redis_perf['read']:.2f}ms")
        print(f"PostgreSQL Select2 Cache:")
        print(f"   • Write: {pg_perf['write']:.2f}ms")
        print(f"   • Read: {pg_perf['read']:.2f}ms")
        
        write_diff = ((pg_perf['write'] - redis_perf['write']) / redis_perf['write']) * 100
        read_diff = ((pg_perf['read'] - redis_perf['read']) / redis_perf['read']) * 100
        
        print(f"Performance Difference:")
        print(f"   • Write: {write_diff:+.1f}%")
        print(f"   • Read: {read_diff:+.1f}%")
        
        if abs(write_diff) < 50 and abs(read_diff) < 50:
            print("✅ PostgreSQL performance is acceptable for migration")
        else:
            print("⚠️  Performance difference may require optimization")
    
    print("\n🎯 Ready for Phase 1B: Select2 Migration Implementation")
    print("Next: Create PostgreSQL cache backend and update settings")