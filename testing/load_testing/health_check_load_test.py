#!/usr/bin/env python3
"""
Health Check Load Testing for YOUTILITY3
Tests health check endpoints under various load conditions
"""

import requests
import threading
import time
import statistics
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

class HealthCheckLoadTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
        self.start_time = time.time()
        
    def test_single_endpoint(self, endpoint, duration_seconds=60, requests_per_second=10):
        """Test a single health check endpoint under load"""
        print(f"\n🔍 Testing {endpoint} endpoint...")
        print(f"   Duration: {duration_seconds}s, Target: {requests_per_second} req/s")
        
        url = f"{self.base_url}{endpoint}"
        results = {
            'endpoint': endpoint,
            'duration': duration_seconds,
            'target_rps': requests_per_second,
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'status_codes': {},
            'errors': []
        }
        
        # Use a queue to collect results from threads
        result_queue = queue.Queue()
        stop_event = threading.Event()
        
        def make_request(thread_id):
            """Make HTTP request to health endpoint"""
            local_results = {
                'successful': 0,
                'failed': 0,
                'response_times': [],
                'status_codes': {},
                'errors': []
            }
            
            session = requests.Session()
            
            while not stop_event.is_set():
                try:
                    start_time = time.time()
                    response = session.get(url, timeout=5)
                    end_time = time.time()
                    
                    response_time = (end_time - start_time) * 1000  # Convert to ms
                    local_results['response_times'].append(response_time)
                    
                    # Track status codes
                    status_code = response.status_code
                    local_results['status_codes'][status_code] = local_results['status_codes'].get(status_code, 0) + 1
                    
                    if 200 <= status_code < 400:
                        local_results['successful'] += 1
                        
                        # Validate response content for health endpoints
                        if endpoint in ['/health/', '/ready/', '/health/detailed/']:
                            try:
                                response_json = response.json()
                                if 'status' not in response_json:
                                    local_results['errors'].append(f"Missing 'status' in response")
                            except json.JSONDecodeError:
                                local_results['errors'].append(f"Invalid JSON response")
                    else:
                        local_results['failed'] += 1
                        local_results['errors'].append(f"HTTP {status_code}: {response.text[:100]}")
                    
                except requests.exceptions.Timeout:
                    local_results['failed'] += 1
                    local_results['errors'].append("Request timeout")
                except requests.exceptions.ConnectionError:
                    local_results['failed'] += 1
                    local_results['errors'].append("Connection error")
                except Exception as e:
                    local_results['failed'] += 1
                    local_results['errors'].append(f"Unexpected error: {str(e)}")
                
                # Control request rate
                time.sleep(1.0 / requests_per_second)
            
            result_queue.put(local_results)
        
        # Start worker threads
        num_threads = min(requests_per_second, 50)  # Cap at 50 threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_threads)]
            
            # Let it run for specified duration
            time.sleep(duration_seconds)
            stop_event.set()
            
            # Wait for threads to complete
            for future in as_completed(futures, timeout=30):
                pass
        
        # Collect results from queue
        while not result_queue.empty():
            thread_result = result_queue.get()
            results['successful_requests'] += thread_result['successful']
            results['failed_requests'] += thread_result['failed']
            results['response_times'].extend(thread_result['response_times'])
            results['errors'].extend(thread_result['errors'])
            
            # Merge status codes
            for code, count in thread_result['status_codes'].items():
                results['status_codes'][code] = results['status_codes'].get(code, 0) + count
        
        # Calculate statistics
        results['total_requests'] = results['successful_requests'] + results['failed_requests']
        results['actual_rps'] = round(results['total_requests'] / duration_seconds, 2)
        results['success_rate'] = round((results['successful_requests'] / max(results['total_requests'], 1)) * 100, 2)
        
        if results['response_times']:
            results['avg_response_time'] = round(statistics.mean(results['response_times']), 2)
            results['median_response_time'] = round(statistics.median(results['response_times']), 2)
            results['p95_response_time'] = round(sorted(results['response_times'])[int(len(results['response_times']) * 0.95)], 2)
            results['p99_response_time'] = round(sorted(results['response_times'])[int(len(results['response_times']) * 0.99)], 2)
            results['min_response_time'] = round(min(results['response_times']), 2)
            results['max_response_time'] = round(max(results['response_times']), 2)
        
        # Determine if test passed
        target_avg_response = 100 if endpoint in ['/health/', '/ready/', '/alive/'] else 200
        results['passes_performance'] = (
            results['success_rate'] >= 99.0 and
            results.get('avg_response_time', float('inf')) <= target_avg_response
        )
        
        # Print results
        print(f"   📊 Results for {endpoint}:")
        print(f"      Total requests: {results['total_requests']}")
        print(f"      Actual RPS: {results['actual_rps']}")
        print(f"      Success rate: {results['success_rate']}%")
        print(f"      Avg response: {results.get('avg_response_time', 'N/A')}ms")
        print(f"      95th percentile: {results.get('p95_response_time', 'N/A')}ms")
        print(f"      Status: {'✅ PASS' if results['passes_performance'] else '❌ FAIL'}")
        
        if results['errors']:
            print(f"      Errors: {len(results['errors'])} (showing first 3)")
            for error in results['errors'][:3]:
                print(f"        - {error}")
        
        self.results[endpoint] = results
        return results
    
    def test_concurrent_health_checks(self, duration_seconds=120):
        """Test all health endpoints concurrently"""
        print(f"\n🔥 Testing all health endpoints concurrently for {duration_seconds}s...")
        
        endpoints = ['/health/', '/ready/', '/alive/', '/health/detailed/']
        results = {}
        
        def test_endpoint_continuously(endpoint):
            """Continuously test an endpoint"""
            return self.test_single_endpoint(endpoint, duration_seconds, requests_per_second=20)
        
        # Run all endpoint tests in parallel
        with ThreadPoolExecutor(max_workers=len(endpoints)) as executor:
            future_to_endpoint = {
                executor.submit(test_endpoint_continuously, endpoint): endpoint
                for endpoint in endpoints
            }
            
            for future in as_completed(future_to_endpoint):
                endpoint = future_to_endpoint[future]
                try:
                    result = future.result()
                    results[endpoint] = result
                except Exception as e:
                    print(f"❌ Error testing {endpoint}: {e}")
        
        return results
    
    def test_health_checks_during_app_load(self):
        """Test health checks while simulating application load"""
        print(f"\n⚡ Testing health checks during application load...")
        
        # First, create application load
        app_load_results = {'requests': 0, 'errors': 0}
        stop_app_load = threading.Event()
        
        def create_app_load():
            """Create background load on the application"""
            session = requests.Session()
            
            while not stop_app_load.is_set():
                try:
                    # Mix of different application requests
                    endpoints = ['/dashboard/', '/reports/', '/peoples/', '/admin/']
                    for endpoint in endpoints:
                        if stop_app_load.is_set():
                            break
                        
                        try:
                            response = session.get(f"{self.base_url}{endpoint}", timeout=5)
                            app_load_results['requests'] += 1
                        except:
                            app_load_results['errors'] += 1
                        
                        time.sleep(0.1)  # 10 requests per second per endpoint
                except Exception:
                    pass
        
        # Start application load threads
        app_load_threads = []
        for i in range(5):  # 5 threads creating app load
            thread = threading.Thread(target=create_app_load)
            thread.start()
            app_load_threads.append(thread)
        
        print("   Started application load simulation...")
        time.sleep(5)  # Let app load ramp up
        
        # Now test health checks under load
        health_results = {}
        for endpoint in ['/health/', '/ready/', '/alive/']:
            print(f"   Testing {endpoint} under application load...")
            result = self.test_single_endpoint(endpoint, duration_seconds=60, requests_per_second=30)
            health_results[f"{endpoint}_under_load"] = result
        
        # Stop application load
        stop_app_load.set()
        for thread in app_load_threads:
            thread.join(timeout=5)
        
        print(f"   Application load simulation: {app_load_results['requests']} requests, {app_load_results['errors']} errors")
        
        return health_results
    
    def test_health_check_failure_scenarios(self):
        """Test health check responses during simulated failures"""
        print(f"\n🚨 Testing health check failure scenario responses...")
        
        results = {}
        
        # Test 1: Test health checks when they should report failures
        # (This would require actually causing failures, which is dangerous in a real environment)
        # For now, we'll just test that the endpoints are responsive
        
        print("   Testing baseline health check responses...")
        baseline_results = {}
        for endpoint in ['/health/', '/ready/', '/alive/', '/health/detailed/']:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                baseline_results[endpoint] = {
                    'status_code': response.status_code,
                    'response_time_ms': response.elapsed.total_seconds() * 1000,
                    'has_json': False,
                    'status_field': None
                }
                
                # Try to parse JSON response
                try:
                    json_response = response.json()
                    baseline_results[endpoint]['has_json'] = True
                    baseline_results[endpoint]['status_field'] = json_response.get('status')
                    baseline_results[endpoint]['response_size'] = len(response.text)
                except:
                    pass
                
                print(f"      {endpoint}: {response.status_code} ({baseline_results[endpoint]['response_time_ms']:.1f}ms)")
                
            except Exception as e:
                print(f"      {endpoint}: ERROR - {str(e)}")
                baseline_results[endpoint] = {'error': str(e)}
        
        results['baseline_health_checks'] = baseline_results
        return results
    
    def run_all_tests(self):
        """Run complete health check load test suite"""
        print("🏥 Starting Health Check Load Test Suite")
        print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Target URL: {self.base_url}")
        
        # Test 1: Individual endpoint testing
        print("\n" + "="*50)
        print("Phase 1: Individual Endpoint Testing")
        print("="*50)
        
        endpoints_config = [
            ('/health/', 30, 50),        # 30s, 50 req/s
            ('/ready/', 30, 50),         # 30s, 50 req/s  
            ('/alive/', 30, 100),        # 30s, 100 req/s (should be fastest)
            ('/health/detailed/', 30, 20) # 30s, 20 req/s (more complex)
        ]
        
        for endpoint, duration, rps in endpoints_config:
            self.test_single_endpoint(endpoint, duration, rps)
        
        # Test 2: Concurrent testing
        print("\n" + "="*50)
        print("Phase 2: Concurrent Endpoint Testing")
        print("="*50)
        
        concurrent_results = self.test_concurrent_health_checks(duration_seconds=60)
        
        # Test 3: Testing under application load
        print("\n" + "="*50) 
        print("Phase 3: Health Checks Under Application Load")
        print("="*50)
        
        load_results = self.test_health_checks_during_app_load()
        self.results.update(load_results)
        
        # Test 4: Failure scenario testing
        print("\n" + "="*50)
        print("Phase 4: Failure Scenario Testing")
        print("="*50)
        
        failure_results = self.test_health_check_failure_scenarios()
        self.results.update(failure_results)
        
        # Generate summary
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """Generate comprehensive summary report"""
        print("\n" + "="*60)
        print("🏥 HEALTH CHECK LOAD TEST SUMMARY")
        print("="*60)
        
        total_tests = 0
        passed_tests = 0
        
        # Individual endpoint results
        print("\n📊 Individual Endpoint Performance:")
        for endpoint, result in self.results.items():
            if isinstance(result, dict) and 'passes_performance' in result:
                total_tests += 1
                if result['passes_performance']:
                    passed_tests += 1
                
                status = "✅ PASS" if result['passes_performance'] else "❌ FAIL"
                avg_time = result.get('avg_response_time', 'N/A')
                success_rate = result.get('success_rate', 'N/A')
                print(f"  {endpoint}: {avg_time}ms avg, {success_rate}% success {status}")
        
        # Overall assessment
        if total_tests > 0:
            success_rate = (passed_tests / total_tests) * 100
            print(f"\n📈 Overall Results:")
            print(f"  Tests passed: {passed_tests}/{total_tests}")
            print(f"  Success rate: {success_rate:.1f}%")
            
            if success_rate >= 90:
                print(f"  🎉 EXCELLENT: Health checks ready for production!")
            elif success_rate >= 75:
                print(f"  ✅ GOOD: Health check performance acceptable")
            else:
                print(f"  ❌ NEEDS IMPROVEMENT: Health check performance issues")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        
        # Check for slow endpoints
        slow_endpoints = []
        for endpoint, result in self.results.items():
            if isinstance(result, dict) and result.get('avg_response_time', 0) > 100:
                slow_endpoints.append(f"{endpoint} ({result['avg_response_time']}ms)")
        
        if slow_endpoints:
            print(f"  ⚠️  Slow endpoints needing optimization:")
            for endpoint in slow_endpoints:
                print(f"     - {endpoint}")
        
        # Check for high error rates
        error_endpoints = []
        for endpoint, result in self.results.items():
            if isinstance(result, dict) and result.get('success_rate', 100) < 99:
                error_endpoints.append(f"{endpoint} ({result['success_rate']}% success)")
        
        if error_endpoints:
            print(f"  🚨 Endpoints with reliability issues:")
            for endpoint in error_endpoints:
                print(f"     - {endpoint}")
        
        if not slow_endpoints and not error_endpoints:
            print(f"  ✅ All health checks performing optimally")
        
        # Save results
        self.save_results_to_file()
        
        print(f"\n⏱️  Total test duration: {time.time() - self.start_time:.1f} seconds")
    
    def save_results_to_file(self):
        """Save test results to JSON file"""
        results_file = f"health_check_load_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(results_file, 'w') as f:
                json.dump({
                    'test_timestamp': datetime.now().isoformat(),
                    'test_duration_seconds': time.time() - self.start_time,
                    'base_url': self.base_url,
                    'results': self.results
                }, f, indent=2)
            
            print(f"📄 Results saved to: {results_file}")
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")

def main():
    """Main function to run health check load tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description='YOUTILITY3 Health Check Load Testing')
    parser.add_argument('--url', default='http://localhost:8000', 
                       help='Base URL for testing (default: http://localhost:8000)')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick tests with shorter duration')
    
    args = parser.parse_args()
    
    print("🏥 YOUTILITY3 Health Check Load Testing")
    print("=" * 50)
    
    tester = HealthCheckLoadTester(base_url=args.url)
    
    if args.quick:
        print("⚡ Running in quick mode (reduced duration)")
        # Override durations for quick testing
        tester.test_single_endpoint('/health/', 10, 20)
        tester.test_single_endpoint('/ready/', 10, 20)
        tester.test_single_endpoint('/alive/', 10, 30)
        tester.generate_summary_report()
    else:
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