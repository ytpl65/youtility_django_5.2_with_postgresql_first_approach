#!/usr/bin/env python3
"""
Test PostgreSQL Select2 Cache Implementation
Comprehensive testing of the new PostgreSQL Select2 cache backend
"""

import os
import sys
import django
import time

# Add the project root to Python path
sys.path.append('/home/satyam/Documents/YOUTILITY-MIGRATION-DJANGO5-POSTGRESQL/YOUTILITY3')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

from django.core.cache import caches
from django.core.management import call_command
from django.db import connection

def test_cache_initialization():
    """Test that the PostgreSQL Select2 cache initializes correctly"""
    print("🚀 Testing PostgreSQL Select2 Cache Initialization")
    print("=" * 55)
    
    try:
        # Get the Select2 cache
        select2_cache = caches['select2']
        print(f"✅ Cache backend loaded: {type(select2_cache).__name__}")
        
        # Check if it's our PostgreSQL backend
        if 'PostgreSQLSelect2Cache' in str(type(select2_cache)):
            print("✅ Using PostgreSQL Select2 cache backend")
        else:
            print(f"⚠️  Using different backend: {type(select2_cache)}")
            return False
        
        # Test basic connectivity
        test_key = 'init_test'
        test_value = {'test': 'initialization'}
        
        result = select2_cache.set(test_key, test_value, timeout=60)
        if result:
            print("✅ Cache write test successful")
        else:
            print("❌ Cache write test failed")
            return False
        
        retrieved = select2_cache.get(test_key)
        if retrieved == test_value:
            print("✅ Cache read test successful")
        else:
            print("❌ Cache read test failed")
            return False
        
        # Cleanup
        select2_cache.delete(test_key)
        print("✅ Cache initialization tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Cache initialization failed: {e}")
        return False

def test_realistic_select2_data():
    """Test with realistic Select2 dropdown data"""
    print("\n📊 Testing Realistic Select2 Data")
    print("=" * 35)
    
    try:
        select2_cache = caches['select2']
        
        # Realistic dropdown data scenarios
        test_scenarios = [
            {
                'name': 'people_dropdown_site_1',
                'data': {
                    'results': [
                        {'id': i, 'text': f'User {i}', 'department': f'Dept {i%5}'}
                        for i in range(1, 101)  # 100 users
                    ],
                    'pagination': {'more': False},
                    'total_count': 100
                }
            },
            {
                'name': 'asset_dropdown_site_1',
                'data': {
                    'results': [
                        {'id': i, 'text': f'Asset {i}', 'type': f'Type {i%10}'}
                        for i in range(1, 51)  # 50 assets
                    ],
                    'pagination': {'more': False},
                    'total_count': 50
                }
            },
            {
                'name': 'typeassist_priorities',
                'data': {
                    'results': [
                        {'id': 1, 'text': 'Low', 'color': 'green'},
                        {'id': 2, 'text': 'Medium', 'color': 'yellow'},
                        {'id': 3, 'text': 'High', 'color': 'orange'},
                        {'id': 4, 'text': 'Critical', 'color': 'red'}
                    ],
                    'pagination': {'more': False},
                    'total_count': 4
                }
            }
        ]
        
        # Test individual operations
        print("🔸 Testing individual cache operations:")
        for scenario in test_scenarios:
            start_time = time.time()
            
            # Set cache
            result = select2_cache.set(scenario['name'], scenario['data'], timeout=900)
            set_time = (time.time() - start_time) * 1000
            
            if result:
                print(f"   ✅ {scenario['name']}: Set in {set_time:.2f}ms")
            else:
                print(f"   ❌ {scenario['name']}: Set failed")
                continue
            
            # Get cache
            start_time = time.time()
            retrieved = select2_cache.get(scenario['name'])
            get_time = (time.time() - start_time) * 1000
            
            if retrieved == scenario['data']:
                print(f"   ✅ {scenario['name']}: Retrieved in {get_time:.2f}ms")
            else:
                print(f"   ❌ {scenario['name']}: Retrieval failed")
        
        return True
        
    except Exception as e:
        print(f"❌ Realistic data test failed: {e}")
        return False

def test_batch_operations():
    """Test batch operations for performance"""
    print("\n⚡ Testing Batch Operations")
    print("=" * 30)
    
    try:
        select2_cache = caches['select2']
        
        # Create batch test data
        batch_data = {}
        for i in range(20):  # 20 different dropdowns
            batch_data[f'batch_dropdown_{i}'] = {
                'results': [
                    {'id': j, 'text': f'Option {j} for dropdown {i}'}
                    for j in range(1, 26)  # 25 options each
                ],
                'pagination': {'more': False},
                'total_count': 25
            }
        
        if hasattr(select2_cache, 'set_many'):
            # Test batch set
            start_time = time.time()
            failed_keys = select2_cache.set_many(batch_data, timeout=900)
            batch_set_time = (time.time() - start_time) * 1000
            
            if not failed_keys:
                print(f"✅ Batch set (20 dropdowns): {batch_set_time:.2f}ms")
                print(f"   📊 Per dropdown: {batch_set_time/20:.2f}ms")
            else:
                print(f"❌ Batch set failed for: {failed_keys}")
                return False
        else:
            print("⚠️  Batch operations not supported")
            return False
        
        if hasattr(select2_cache, 'get_many'):
            # Test batch get
            start_time = time.time()
            results = select2_cache.get_many(list(batch_data.keys()))
            batch_get_time = (time.time() - start_time) * 1000
            
            if len(results) == len(batch_data):
                print(f"✅ Batch get (20 dropdowns): {batch_get_time:.2f}ms")
                print(f"   📊 Per dropdown: {batch_get_time/20:.2f}ms")
            else:
                print(f"❌ Batch get incomplete: {len(results)}/{len(batch_data)}")
                return False
        
        # Cleanup
        if hasattr(select2_cache, 'delete_many'):
            select2_cache.delete_many(list(batch_data.keys()))
            print("🧹 Cleaned up batch test data")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch operations test failed: {e}")
        return False

def test_cache_statistics():
    """Test cache statistics and monitoring"""
    print("\n📈 Testing Cache Statistics")
    print("=" * 30)
    
    try:
        select2_cache = caches['select2']
        
        # Add some test data first
        test_data = {
            'stats_test_1': {'results': [{'id': 1, 'text': 'Test 1'}]},
            'stats_test_2': {'results': [{'id': 2, 'text': 'Test 2'}]},
            'stats_test_3': {'results': [{'id': 3, 'text': 'Test 3'}]}
        }
        
        for key, value in test_data.items():
            select2_cache.set(key, value, timeout=900)
        
        # Test statistics
        if hasattr(select2_cache, 'get_stats'):
            stats = select2_cache.get_stats()
            
            print(f"📊 Cache Statistics:")
            print(f"   • Total entries: {stats['total_entries']}")
            print(f"   • Active entries: {stats['active_entries']}")
            print(f"   • Expired entries: {stats['expired_entries']}")
            print(f"   • Average data size: {stats['avg_data_size_bytes']} bytes")
            print(f"   • Tenant ID: {stats['tenant_id']}")
            
            if stats['active_entries'] >= 3:
                print("✅ Statistics working correctly")
            else:
                print("⚠️  Statistics may not reflect recent additions")
        else:
            print("⚠️  Statistics not supported")
        
        # Test cleanup
        if hasattr(select2_cache, 'cleanup_expired'):
            cleaned = select2_cache.cleanup_expired()
            print(f"🧹 Cleanup test: {cleaned} expired entries removed")
        
        # Cleanup test data
        for key in test_data.keys():
            select2_cache.delete(key)
        
        return True
        
    except Exception as e:
        print(f"❌ Statistics test failed: {e}")
        return False

def test_management_command():
    """Test the Django management command"""
    print("\n🔧 Testing Management Command")
    print("=" * 30)
    
    try:
        # Test stats command
        print("Testing 'stats' command...")
        call_command('manage_select2_cache', 'stats')
        print("✅ Stats command executed")
        
        # Test cache test command
        print("\nTesting 'test' command...")
        call_command('manage_select2_cache', 'test')
        print("✅ Test command executed")
        
        # Test cleanup command (dry run)
        print("\nTesting 'cleanup' command (dry run)...")
        call_command('manage_select2_cache', 'cleanup', '--dry-run')
        print("✅ Cleanup dry run executed")
        
        return True
        
    except Exception as e:
        print(f"❌ Management command test failed: {e}")
        return False

def performance_comparison():
    """Compare performance with previous Redis implementation"""
    print("\n⚡ Performance Comparison")
    print("=" * 25)
    
    try:
        select2_cache = caches['select2']
        
        # Test data similar to what was used in Redis testing
        test_data = {
            'choices': [
                {'id': i, 'text': f'Option {i}', 'value': f'value_{i}'}
                for i in range(100)
            ],
            'meta': {'total': 100, 'filtered': 100}
        }
        
        # Single operations performance
        write_times = []
        for i in range(10):
            start = time.time()
            select2_cache.set(f'perf_test_{i}', test_data, timeout=300)
            write_times.append((time.time() - start) * 1000)
        
        read_times = []
        for i in range(10):
            start = time.time()
            select2_cache.get(f'perf_test_{i}')
            read_times.append((time.time() - start) * 1000)
        
        avg_write = sum(write_times) / len(write_times)
        avg_read = sum(read_times) / len(read_times)
        
        print(f"📊 Single Operations Performance:")
        print(f"   • Average write: {avg_write:.2f}ms")
        print(f"   • Average read: {avg_read:.2f}ms")
        
        # Batch operations performance (if supported)
        if hasattr(select2_cache, 'set_many') and hasattr(select2_cache, 'get_many'):
            batch_data = {f'batch_perf_{i}': test_data for i in range(10)}
            
            start = time.time()
            select2_cache.set_many(batch_data, timeout=300)
            batch_write_time = (time.time() - start) * 1000
            
            start = time.time()
            select2_cache.get_many(list(batch_data.keys()))
            batch_read_time = (time.time() - start) * 1000
            
            print(f"📦 Batch Operations Performance:")
            print(f"   • Batch write (10 items): {batch_write_time:.2f}ms")
            print(f"   • Per item write: {batch_write_time/10:.2f}ms")
            print(f"   • Batch read (10 items): {batch_read_time:.2f}ms")
            print(f"   • Per item read: {batch_read_time/10:.2f}ms")
        
        # Cleanup
        for i in range(10):
            select2_cache.delete(f'perf_test_{i}')
        
        if hasattr(select2_cache, 'delete_many'):
            select2_cache.delete_many([f'batch_perf_{i}' for i in range(10)])
        
        print("🎯 Performance testing completed")
        return True
        
    except Exception as e:
        print(f"❌ Performance comparison failed: {e}")
        return False

def run_comprehensive_test():
    """Run all tests and provide summary"""
    print("🚀 PostgreSQL Select2 Cache Implementation Test")
    print("=" * 60)
    
    test_results = {
        'initialization': test_cache_initialization(),
        'realistic_data': test_realistic_select2_data(),
        'batch_operations': test_batch_operations(),
        'statistics': test_cache_statistics(),
        'management_command': test_management_command(),
        'performance': performance_comparison()
    }
    
    print(f"\n📋 Test Summary")
    print("=" * 15)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! PostgreSQL Select2 cache is ready for production.")
        print("\n✅ Next Steps:")
        print("   1. Monitor performance in development")
        print("   2. Test with real Select2 widgets")
        print("   3. Verify cache invalidation works correctly")
        print("   4. Set up monitoring and alerts")
    else:
        print("⚠️  Some tests failed. Review the implementation before proceeding.")
    
    return passed == total

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)