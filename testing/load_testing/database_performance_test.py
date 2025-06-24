#!/usr/bin/env python3
"""
Database Performance Testing for YOUTILITY3
Tests PostgreSQL functions and queries under load
"""

import os
import sys
import django
import psycopg2
import time
import statistics
import threading
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup Django environment
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

from django.db import connection, connections
from django.conf import settings
from apps.core.models import RateLimitAttempt

class DatabasePerformanceTester:
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
        
    def get_db_connection(self):
        """Get a fresh database connection"""
        return psycopg2.connect(
            host=settings.DATABASES['default']['HOST'],
            database=settings.DATABASES['default']['NAME'],
            user=settings.DATABASES['default']['USER'],
            password=settings.DATABASES['default']['PASSWORD'],
            port=settings.DATABASES['default']['PORT']
        )
    
    def test_postgresql_function_performance(self, function_name, query, params, target_ms, iterations=100):
        """Test performance of a specific PostgreSQL function"""
        print(f"\n🔍 Testing {function_name}...")
        
        times = []
        errors = 0
        
        for i in range(iterations):
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                start_time = time.time()
                cursor.execute(query, params)
                result = cursor.fetchall()
                end_time = time.time()
                
                execution_time = (end_time - start_time) * 1000  # Convert to ms
                times.append(execution_time)
                
                cursor.close()
                conn.close()
                
                if i % 20 == 0:
                    print(f"  Progress: {i+1}/{iterations} - Current: {execution_time:.2f}ms")
                    
            except Exception as e:
                errors += 1
                print(f"  Error in iteration {i+1}: {str(e)}")
        
        if times:
            avg_time = statistics.mean(times)
            median_time = statistics.median(times)
            p95_time = sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0]
            p99_time = sorted(times)[int(len(times) * 0.99)] if len(times) > 1 else times[0]
            min_time = min(times)
            max_time = max(times)
            
            result = {
                'function_name': function_name,
                'iterations': iterations,
                'successful_runs': len(times),
                'errors': errors,
                'average_ms': round(avg_time, 2),
                'median_ms': round(median_time, 2),
                'p95_ms': round(p95_time, 2),
                'p99_ms': round(p99_time, 2),
                'min_ms': round(min_time, 2),
                'max_ms': round(max_time, 2),
                'target_ms': target_ms,
                'passes_target': avg_time <= target_ms,
                'error_rate': round((errors / iterations) * 100, 2)
            }
            
            self.results[function_name] = result
            
            print(f"  ✅ Results for {function_name}:")
            print(f"     Average: {avg_time:.2f}ms (Target: {target_ms}ms)")
            print(f"     95th percentile: {p95_time:.2f}ms")
            print(f"     Error rate: {result['error_rate']}%")
            print(f"     Status: {'✅ PASS' if avg_time <= target_ms else '❌ FAIL'}")
            
            return result
        else:
            print(f"  ❌ All tests failed for {function_name}")
            return None
    
    def test_concurrent_database_load(self, num_threads=50, duration_seconds=300):
        """Test database performance under concurrent load"""
        print(f"\n🔥 Testing concurrent database load ({num_threads} threads, {duration_seconds}s)...")
        
        results = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'avg_response_time': 0,
            'queries_per_second': 0,
            'concurrent_connections': num_threads
        }
        
        query_times = []
        stop_event = threading.Event()
        
        def worker_thread(thread_id):
            """Worker thread that executes database queries"""
            local_times = []
            local_success = 0
            local_errors = 0
            
            while not stop_event.is_set():
                try:
                    conn = self.get_db_connection()
                    cursor = conn.cursor()
                    
                    start_time = time.time()
                    
                    # Mix of different query types
                    if thread_id % 4 == 0:
                        # Test rate limiting function
                        cursor.execute(
                            "SELECT check_rate_limit(%s, %s, %s::INTERVAL, %s)",
                            [f'192.168.1.{thread_id}', f'user{thread_id}', '15 minutes', 5]
                        )
                    elif thread_id % 4 == 1:
                        # Test session query
                        cursor.execute("SELECT COUNT(*) FROM django_session WHERE expire_date > NOW()")
                    elif thread_id % 4 == 2:
                        # Test materialized view
                        cursor.execute("SELECT * FROM mv_people_dropdown LIMIT 10")
                    else:
                        # Test rate limit attempts
                        cursor.execute(
                            "SELECT COUNT(*) FROM auth_rate_limit_attempts WHERE attempt_time > NOW() - INTERVAL '1 hour'"
                        )
                    
                    cursor.fetchall()
                    end_time = time.time()
                    
                    execution_time = (end_time - start_time) * 1000
                    local_times.append(execution_time)
                    local_success += 1
                    
                    cursor.close()
                    conn.close()
                    
                    # Small delay to prevent overwhelming
                    time.sleep(0.01)
                    
                except Exception as e:
                    local_errors += 1
                    if local_errors < 5:  # Only print first few errors
                        print(f"    Thread {thread_id} error: {str(e)[:100]}")
            
            return {
                'thread_id': thread_id,
                'queries': local_success,
                'errors': local_errors,
                'times': local_times
            }
        
        # Start worker threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_thread, i) for i in range(num_threads)]
            
            # Let it run for specified duration
            time.sleep(duration_seconds)
            stop_event.set()
            
            # Collect results
            print("  Collecting results from worker threads...")
            for future in as_completed(futures):
                try:
                    thread_result = future.result(timeout=30)
                    results['successful_queries'] += thread_result['queries']
                    results['failed_queries'] += thread_result['errors']
                    query_times.extend(thread_result['times'])
                except Exception as e:
                    print(f"    Error collecting thread result: {e}")
        
        # Calculate final statistics
        results['total_queries'] = results['successful_queries'] + results['failed_queries']
        if query_times:
            results['avg_response_time'] = round(statistics.mean(query_times), 2)
            results['p95_response_time'] = round(sorted(query_times)[int(len(query_times) * 0.95)], 2)
        results['queries_per_second'] = round(results['successful_queries'] / duration_seconds, 2)
        results['error_rate'] = round((results['failed_queries'] / max(results['total_queries'], 1)) * 100, 2)
        
        print(f"  📊 Concurrent Load Test Results:")
        print(f"     Total queries: {results['total_queries']}")
        print(f"     Successful: {results['successful_queries']}")
        print(f"     Failed: {results['failed_queries']}")
        print(f"     Queries/second: {results['queries_per_second']}")
        print(f"     Avg response: {results['avg_response_time']}ms")
        print(f"     95th percentile: {results.get('p95_response_time', 'N/A')}ms")
        print(f"     Error rate: {results['error_rate']}%")
        
        self.results['concurrent_load_test'] = results
        return results
    
    def test_database_connection_pool(self):
        """Test database connection pool behavior"""
        print(f"\n🔗 Testing database connection pool...")
        
        # Get current connection stats
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        count(*) as total_connections,
                        count(*) FILTER (WHERE state = 'active') as active_connections,
                        count(*) FILTER (WHERE state = 'idle') as idle_connections
                    FROM pg_stat_activity 
                    WHERE datname = %s
                """, [settings.DATABASES['default']['NAME']])
                
                result = cursor.fetchone()
                connection_stats = {
                    'total_connections': result[0],
                    'active_connections': result[1], 
                    'idle_connections': result[2],
                    'max_connections': None
                }
                
                # Get max connections setting
                cursor.execute("SHOW max_connections")
                max_conn = cursor.fetchone()[0]
                connection_stats['max_connections'] = int(max_conn)
                
                print(f"  📊 Connection Pool Status:")
                print(f"     Total connections: {connection_stats['total_connections']}")
                print(f"     Active connections: {connection_stats['active_connections']}")
                print(f"     Idle connections: {connection_stats['idle_connections']}")
                print(f"     Max connections: {connection_stats['max_connections']}")
                
                # Check if we're approaching connection limits
                usage_percent = (connection_stats['total_connections'] / connection_stats['max_connections']) * 100
                if usage_percent > 80:
                    print(f"  ⚠️  WARNING: Connection usage at {usage_percent:.1f}%")
                else:
                    print(f"  ✅ Connection usage: {usage_percent:.1f}%")
                
                self.results['connection_pool'] = connection_stats
                return connection_stats
                
        except Exception as e:
            print(f"  ❌ Error testing connection pool: {e}")
            return None
    
    def run_all_tests(self):
        """Run complete database performance test suite"""
        print("🚀 Starting Database Performance Test Suite")
        print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test individual PostgreSQL functions
        test_functions = [
            {
                'name': 'check_rate_limit',
                'query': "SELECT check_rate_limit(%s, %s, %s::INTERVAL, %s)",
                'params': ['192.168.1.100', 'testuser', '15 minutes', 5],
                'target_ms': 20
            },
            {
                'name': 'cleanup_expired_sessions',
                'query': "SELECT cleanup_expired_sessions()",
                'params': [],
                'target_ms': 100
            },
            {
                'name': 'cleanup_select2_cache',
                'query': "SELECT cleanup_select2_cache(7)",
                'params': [],
                'target_ms': 50
            },
            {
                'name': 'materialized_view_query',
                'query': "SELECT * FROM mv_people_dropdown LIMIT 100",
                'params': [],
                'target_ms': 5
            },
            {
                'name': 'session_count_query',
                'query': "SELECT COUNT(*) FROM django_session",
                'params': [],
                'target_ms': 10
            },
            {
                'name': 'rate_limit_attempts_query',
                'query': "SELECT COUNT(*) FROM auth_rate_limit_attempts WHERE attempt_time > NOW() - INTERVAL '24 hours'",
                'params': [],
                'target_ms': 15
            }
        ]
        
        # Test each function
        for test_func in test_functions:
            self.test_postgresql_function_performance(
                test_func['name'],
                test_func['query'],
                test_func['params'],
                test_func['target_ms']
            )
        
        # Test connection pool
        self.test_database_connection_pool()
        
        # Test concurrent load
        self.test_concurrent_database_load(num_threads=20, duration_seconds=60)
        
        # Generate summary report
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """Generate a comprehensive summary report"""
        print("\n" + "="*60)
        print("📊 DATABASE PERFORMANCE TEST SUMMARY")
        print("="*60)
        
        total_tests = 0
        passed_tests = 0
        
        # Function performance summary
        print("\n🔍 PostgreSQL Function Performance:")
        for func_name, result in self.results.items():
            if isinstance(result, dict) and 'passes_target' in result:
                total_tests += 1
                if result['passes_target']:
                    passed_tests += 1
                
                status = "✅ PASS" if result['passes_target'] else "❌ FAIL"
                print(f"  {func_name}: {result['average_ms']}ms (target: {result['target_ms']}ms) {status}")
        
        # Concurrent load summary
        if 'concurrent_load_test' in self.results:
            load_result = self.results['concurrent_load_test']
            print(f"\n🔥 Concurrent Load Test:")
            print(f"  Queries/second: {load_result['queries_per_second']}")
            print(f"  Average response: {load_result['avg_response_time']}ms")
            print(f"  Error rate: {load_result['error_rate']}%")
            
            # Determine if load test passed
            load_passed = (
                load_result['queries_per_second'] > 50 and  # At least 50 QPS
                load_result['avg_response_time'] < 100 and  # Under 100ms average
                load_result['error_rate'] < 5  # Under 5% error rate
            )
            
            total_tests += 1
            if load_passed:
                passed_tests += 1
            
            print(f"  Status: {'✅ PASS' if load_passed else '❌ FAIL'}")
        
        # Overall assessment
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"\n📈 Overall Results:")
        print(f"  Tests passed: {passed_tests}/{total_tests}")
        print(f"  Success rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print(f"  🎉 EXCELLENT: Database ready for production!")
        elif success_rate >= 75:
            print(f"  ✅ GOOD: Database performance acceptable")
        elif success_rate >= 50:
            print(f"  ⚠️  WARNING: Some performance issues detected")
        else:
            print(f"  ❌ CRITICAL: Significant performance problems")
        
        # Save results to file
        self.save_results_to_file()
        
        print(f"\n⏱️  Total test duration: {time.time() - self.start_time:.1f} seconds")
    
    def save_results_to_file(self):
        """Save test results to JSON file"""
        results_file = f"database_performance_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(results_file, 'w') as f:
                json.dump({
                    'test_timestamp': datetime.now().isoformat(),
                    'test_duration_seconds': time.time() - self.start_time,
                    'database_config': {
                        'host': settings.DATABASES['default']['HOST'],
                        'database': settings.DATABASES['default']['NAME'],
                        'user': settings.DATABASES['default']['USER']
                    },
                    'results': self.results
                }, f, indent=2)
            
            print(f"📄 Results saved to: {results_file}")
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")

def main():
    """Main function to run database performance tests"""
    print("🔬 YOUTILITY3 Database Performance Testing")
    print("=" * 50)
    
    tester = DatabasePerformanceTester()
    
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()