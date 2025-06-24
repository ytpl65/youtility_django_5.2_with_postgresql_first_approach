#!/usr/bin/env python3
"""
Standalone Database Performance Testing for YOUTILITY3
Tests PostgreSQL functions and queries under load without Django dependencies
"""

import psycopg2
import time
import statistics
import threading
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class StandaloneDatabaseTester:
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
        
        # Database connection parameters from .env.dev
        self.db_config = {
            'host': 'redmine.youtility.in',
            'database': 'django5db',
            'user': 'django5dbuser', 
            'password': '!!sysadmin!!',
            'port': 5432
        }
        
    def get_db_connection(self):
        """Get a fresh database connection"""
        try:
            return psycopg2.connect(**self.db_config)
        except psycopg2.OperationalError as e:
            print(f"❌ Database connection failed: {e}")
            print("Please ensure PostgreSQL is running and credentials are correct")
            raise
        
    def test_postgresql_function_performance(self, function_name, query, params, target_ms, iterations=50):
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
                
                if i % 10 == 0 and i > 0:
                    print(f"  Progress: {i}/{iterations} - Current: {execution_time:.2f}ms")
                    
            except Exception as e:
                errors += 1
                if errors <= 3:  # Only print first few errors
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
    
    def test_concurrent_database_load(self, num_threads=20, duration_seconds=60):
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
                        # Test rate limiting function (if it exists)
                        cursor.execute(
                            "SELECT CASE WHEN EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_name = 'check_rate_limit') "
                            "THEN check_rate_limit(%s, %s, %s::INTERVAL, %s) "
                            "ELSE '{\"status\": \"no_function\"}'::json END",
                            [f'192.168.1.{thread_id}', f'user{thread_id}', '15 minutes', 5]
                        )
                    elif thread_id % 4 == 1:
                        # Test session query
                        cursor.execute("SELECT COUNT(*) FROM django_session WHERE expire_date > NOW()")
                    elif thread_id % 4 == 2:
                        # Test basic query
                        cursor.execute("SELECT COUNT(*) FROM auth_user LIMIT 10")
                    else:
                        # Test simple query
                        cursor.execute("SELECT NOW(), version()")
                    
                    cursor.fetchall()
                    end_time = time.time()
                    
                    execution_time = (end_time - start_time) * 1000
                    local_times.append(execution_time)
                    local_success += 1
                    
                    cursor.close()
                    conn.close()
                    
                    # Small delay to prevent overwhelming
                    time.sleep(0.05)
                    
                except Exception as e:
                    local_errors += 1
                    if local_errors <= 3:  # Only print first few errors
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
        """Test database connection behavior"""
        print(f"\n🔗 Testing database connection behavior...")
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get current connection stats
            cursor.execute("""
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity 
                WHERE datname = %s
            """, [self.db_config['database']])
            
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
            
            print(f"  📊 Connection Stats:")
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
            
            cursor.close()
            conn.close()
            
            self.results['connection_stats'] = connection_stats
            return connection_stats
            
        except Exception as e:
            print(f"  ❌ Error testing connections: {e}")
            return None
    
    def run_all_tests(self):
        """Run complete database performance test suite"""
        print("🚀 Starting Standalone Database Performance Tests")
        print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Database: {self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}")
        
        # Test database connectivity first
        try:
            conn = self.get_db_connection()
            conn.close()
            print("✅ Database connection successful")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return
        
        # Test individual PostgreSQL functions (if they exist)
        test_functions = [
            {
                'name': 'check_rate_limit_function',
                'query': """
                    SELECT CASE 
                        WHEN EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_name = 'check_rate_limit') 
                        THEN check_rate_limit(%s, %s, %s::INTERVAL, %s)::text
                        ELSE '{"status": "function_not_found"}'
                    END
                """,
                'params': ['192.168.1.100', 'testuser', '15 minutes', 5],
                'target_ms': 20
            },
            {
                'name': 'session_count_query',
                'query': "SELECT COUNT(*) FROM django_session",
                'params': [],
                'target_ms': 10
            },
            {
                'name': 'user_count_query',
                'query': "SELECT COUNT(*) FROM auth_user",
                'params': [],
                'target_ms': 10
            },
            {
                'name': 'basic_postgres_query',
                'query': "SELECT NOW(), version()",
                'params': [],
                'target_ms': 5
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
        
        # Test connection behavior
        self.test_database_connection_pool()
        
        # Test concurrent load
        self.test_concurrent_database_load(num_threads=10, duration_seconds=30)
        
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
        print("\n🔍 Database Function Performance:")
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
                load_result['queries_per_second'] > 20 and  # At least 20 QPS
                load_result['avg_response_time'] < 100 and  # Under 100ms average
                load_result['error_rate'] < 10  # Under 10% error rate
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
        
        if success_rate >= 80:
            print(f"  🎉 EXCELLENT: Database ready for production!")
        elif success_rate >= 60:
            print(f"  ✅ GOOD: Database performance acceptable")
        elif success_rate >= 40:
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
                        'host': self.db_config['host'],
                        'database': self.db_config['database'],
                        'user': self.db_config['user']
                    },
                    'results': self.results
                }, f, indent=2)
            
            print(f"📄 Results saved to: {results_file}")
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")

def main():
    """Main function to run database performance tests"""
    print("🔬 YOUTILITY3 Standalone Database Performance Testing")
    print("=" * 50)
    
    tester = StandaloneDatabaseTester()
    
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        tester.generate_summary_report()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()