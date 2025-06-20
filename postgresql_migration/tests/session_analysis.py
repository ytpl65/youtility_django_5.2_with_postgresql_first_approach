#!/usr/bin/env python3
"""
Session Analysis Tool - PostgreSQL First Migration
Tests current session behavior and performance characteristics
"""

import os
import sys
import django
import time
import psutil
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.append('/home/satyam/Documents/YOUTILITY-MIGRATION-DJANGO5-POSTGRESQL/YOUTILITY3')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore as DBSessionStore
from django.contrib.sessions.backends.cached_db import SessionStore as CachedDBSessionStore
from django.contrib.sessions.models import Session
from django.db import connection
from django.core.cache import caches
from django.test import RequestFactory

class SessionAnalyzer:
    def __init__(self):
        self.factory = RequestFactory()
        self.results = {}
        
    def print_header(self, title):
        print(f"\n{'='*60}")
        print(f"🔍 {title}")
        print(f"{'='*60}")
    
    def test_current_configuration(self):
        """Test what's actually configured vs what's working"""
        self.print_header("CURRENT SESSION CONFIGURATION ANALYSIS")
        
        print(f"📋 Current Settings:")
        print(f"   SESSION_ENGINE: {settings.SESSION_ENGINE}")
        print(f"   SESSION_CACHE_ALIAS: {getattr(settings, 'SESSION_CACHE_ALIAS', 'Not set')}")
        print(f"   SESSION_COOKIE_AGE: {getattr(settings, 'SESSION_COOKIE_AGE', 'Not set')} seconds")
        print(f"   SESSION_SAVE_EVERY_REQUEST: {getattr(settings, 'SESSION_SAVE_EVERY_REQUEST', 'Not set')}")
        
        # Test cache configuration
        print(f"\n🗄️ Cache Configuration:")
        if hasattr(settings, 'CACHES'):
            for alias, config in settings.CACHES.items():
                print(f"   {alias}: {config.get('BACKEND', 'Unknown backend')}")
                if alias == getattr(settings, 'SESSION_CACHE_ALIAS', None):
                    print(f"      ⚠️  This is the session cache!")
        else:
            print("   ❌ No CACHES configuration found!")
            
        # Test if session cache actually works
        print(f"\n🧪 Testing Session Cache Availability:")
        session_cache_alias = getattr(settings, 'SESSION_CACHE_ALIAS', None)
        if session_cache_alias:
            try:
                cache = caches[session_cache_alias]
                cache.set('test_key', 'test_value', 10)
                result = cache.get('test_key')
                if result == 'test_value':
                    print(f"   ✅ Session cache '{session_cache_alias}' is working")
                    cache.delete('test_key')
                else:
                    print(f"   ❌ Session cache '{session_cache_alias}' failed to retrieve test data")
            except Exception as e:
                print(f"   ❌ Session cache '{session_cache_alias}' error: {str(e)}")
        else:
            print("   ⚠️  No session cache alias configured")
    
    def test_session_behavior(self):
        """Test how sessions actually behave"""
        self.print_header("SESSION BEHAVIOR TESTING")
        
        # Test current session store
        print("🏪 Testing Current Session Store:")
        try:
            if settings.SESSION_ENGINE == 'django.contrib.sessions.backends.cached_db':
                session_store = CachedDBSessionStore()
                print("   📦 Using CachedDBSessionStore")
            else:
                session_store = DBSessionStore()
                print("   📦 Using DBSessionStore")
                
            # Create a test session
            session_store['test_key'] = 'test_value'
            session_store['user_id'] = 12345
            session_store['timestamp'] = str(datetime.now())
            session_store.save()
            
            session_key = session_store.session_key
            print(f"   ✅ Session created with key: {session_key}")
            
            # Try to retrieve the session
            new_session_store = type(session_store)(session_key)
            retrieved_value = new_session_store.get('test_key')
            
            if retrieved_value == 'test_value':
                print(f"   ✅ Session data retrieved successfully")
                print(f"   📊 Session data: {dict(new_session_store.items())}")
            else:
                print(f"   ❌ Session data retrieval failed")
                
            # Clean up
            session_store.delete()
            print(f"   🧹 Test session cleaned up")
            
        except Exception as e:
            print(f"   ❌ Session testing failed: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def measure_session_performance(self, num_tests=100):
        """Measure session performance"""
        self.print_header("SESSION PERFORMANCE MEASUREMENT")
        
        print(f"🏃 Running {num_tests} session operations...")
        
        # Test current configuration
        if settings.SESSION_ENGINE == 'django.contrib.sessions.backends.cached_db':
            session_class = CachedDBSessionStore
            store_type = "CachedDB (Current)"
        else:
            session_class = DBSessionStore  
            store_type = "Database (Current)"
            
        # Measure session creation
        start_time = time.time()
        session_keys = []
        
        for i in range(num_tests):
            session = session_class()
            session['test_data'] = f'test_value_{i}'
            session['user_id'] = i
            session.save()
            session_keys.append(session.session_key)
            
        creation_time = time.time() - start_time
        
        # Measure session retrieval
        start_time = time.time()
        
        for key in session_keys:
            session = session_class(key)
            _ = session.get('test_data')
            
        retrieval_time = time.time() - start_time
        
        # Measure session deletion
        start_time = time.time()
        
        for key in session_keys:
            session = session_class(key)
            session.delete()
            
        deletion_time = time.time() - start_time
        
        # Store results
        self.results[store_type] = {
            'creation_time': creation_time,
            'retrieval_time': retrieval_time,
            'deletion_time': deletion_time,
            'total_time': creation_time + retrieval_time + deletion_time,
            'avg_creation': creation_time / num_tests * 1000,  # ms
            'avg_retrieval': retrieval_time / num_tests * 1000,  # ms
            'avg_deletion': deletion_time / num_tests * 1000,  # ms
        }
        
        print(f"📊 Performance Results for {store_type}:")
        print(f"   Creation:  {creation_time:.3f}s total, {creation_time/num_tests*1000:.2f}ms avg")
        print(f"   Retrieval: {retrieval_time:.3f}s total, {retrieval_time/num_tests*1000:.2f}ms avg")
        print(f"   Deletion:  {deletion_time:.3f}s total, {deletion_time/num_tests*1000:.2f}ms avg")
        print(f"   Total:     {creation_time + retrieval_time + deletion_time:.3f}s")
    
    def analyze_database_sessions(self):
        """Analyze current session data in database"""
        self.print_header("DATABASE SESSION ANALYSIS")
        
        with connection.cursor() as cursor:
            # Check if session table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'django_session'
                );
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                print("❌ django_session table does not exist!")
                return
                
            print("✅ django_session table exists")
            
            # Get session table stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_sessions,
                    COUNT(CASE WHEN expire_date > NOW() THEN 1 END) as active_sessions,
                    COUNT(CASE WHEN expire_date <= NOW() THEN 1 END) as expired_sessions,
                    MIN(expire_date) as oldest_expiry,
                    MAX(expire_date) as newest_expiry
                FROM django_session;
            """)
            
            stats = cursor.fetchone()
            print(f"📊 Session Statistics:")
            print(f"   Total sessions: {stats[0]}")
            print(f"   Active sessions: {stats[1]}")
            print(f"   Expired sessions: {stats[2]}")
            print(f"   Oldest expiry: {stats[3]}")
            print(f"   Newest expiry: {stats[4]}")
            
            # Check for indexes on session table
            cursor.execute("""
                SELECT 
                    indexname, 
                    indexdef 
                FROM pg_indexes 
                WHERE tablename = 'django_session'
                ORDER BY indexname;
            """)
            
            indexes = cursor.fetchall()
            print(f"\n🗂️ Current Indexes on django_session:")
            if indexes:
                for index_name, index_def in indexes:
                    print(f"   {index_name}: {index_def}")
            else:
                print("   ⚠️  No indexes found! This could impact performance.")
                
            # Analyze session data size
            cursor.execute("""
                SELECT 
                    pg_size_pretty(pg_total_relation_size('django_session')) as table_size,
                    AVG(length(session_data)) as avg_session_size,
                    MAX(length(session_data)) as max_session_size,
                    MIN(length(session_data)) as min_session_size
                FROM django_session;
            """)
            
            size_stats = cursor.fetchone()
            if size_stats[0]:
                print(f"\n💾 Session Storage Analysis:")
                print(f"   Table size: {size_stats[0]}")
                print(f"   Average session data size: {size_stats[1]:.0f} bytes")
                print(f"   Max session data size: {size_stats[2]} bytes")
                print(f"   Min session data size: {size_stats[3]} bytes")
    
    def explain_postgresql_optimization(self):
        """Explain PostgreSQL session optimization strategy"""
        self.print_header("POSTGRESQL SESSION OPTIMIZATION STRATEGY")
        
        print("🎯 Optimization Goals:")
        print("   1. Eliminate Redis dependency and configuration complexity")
        print("   2. Optimize PostgreSQL for session workload")
        print("   3. Add proper indexing for session lookup patterns")
        print("   4. Implement session cleanup strategies")
        
        print("\n📈 Recommended Optimizations:")
        print("   1. CREATE INDEX CONCURRENTLY django_session_expire_date_idx")
        print("      ON django_session(expire_date);")
        print("      → Speeds up expired session cleanup")
        
        print("\n   2. CREATE INDEX CONCURRENTLY django_session_session_key_idx") 
        print("      ON django_session(session_key);")
        print("      → Speeds up session key lookups (if not primary key)")
        
        print("\n   3. Periodic cleanup of expired sessions:")
        print("      DELETE FROM django_session WHERE expire_date < NOW();")
        
        print("\n   4. Consider partitioning by expire_date for large deployments")
        
        print("\n🔧 Configuration Changes:")
        print("   Before: SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'")
        print("   After:  SESSION_ENGINE = 'django.contrib.sessions.backends.db'")
        print("   Impact: Removes Redis dependency, uses optimized PostgreSQL directly")
        
        print("\n📊 Expected Performance Impact:")
        print("   • Latency: Potentially lower (no Redis round-trip)")
        print("   • Consistency: Higher (ACID guarantees)")
        print("   • Complexity: Much lower (one less service)")
        print("   • Monitoring: Simpler (database-only metrics)")

def main():
    print("🚀 Starting Session Analysis for PostgreSQL-First Migration")
    print(f"⏰ Analysis started at: {datetime.now()}")
    
    analyzer = SessionAnalyzer()
    
    try:
        # Step 1: Analyze current configuration
        analyzer.test_current_configuration()
        
        # Step 2: Test actual session behavior
        analyzer.test_session_behavior()
        
        # Step 3: Measure performance
        analyzer.measure_session_performance(50)  # Smaller test for speed
        
        # Step 4: Analyze database state
        analyzer.analyze_database_sessions()
        
        # Step 5: Explain optimization strategy
        analyzer.explain_postgresql_optimization()
        
        print(f"\n✅ Analysis completed successfully at: {datetime.now()}")
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()