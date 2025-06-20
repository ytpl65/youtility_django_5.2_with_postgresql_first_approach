#!/usr/bin/env python
"""
Simple test script to verify SQL injection protection.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

def test_get_db_rows_security():
    """Test the get_db_rows function security features."""
    print("🧪 Testing get_db_rows() SQL injection protection...")
    
    from apps.service.querys import get_db_rows
    
    # Test 1: Valid stored procedure (should pass validation)
    print("\n1️⃣ Testing valid stored procedure call:")
    try:
        sql = "select * from fun_getexttourjobneed(%s, %s, %s)"
        args = [1, 1, 1]
        result = get_db_rows(sql, args)
        print("✅ Valid stored procedure: Passed validation (may fail on execution if SP doesn't exist)")
    except ValueError as e:
        if "SQL execution not allowed" in str(e):
            print("❌ Valid stored procedure: FAILED - Incorrectly blocked")
            return False
        else:
            print("✅ Valid stored procedure: Passed validation, failed execution (expected)")
    except Exception as e:
        print(f"✅ Valid stored procedure: Passed validation, failed execution: {type(e).__name__}")
    
    # Test 2: Malicious SQL injection attempts (should be blocked)
    malicious_queries = [
        "DROP TABLE users",
        "SELECT * FROM users WHERE 1=1; DROP TABLE logs;",
        "'; UNION SELECT username, password FROM users; --",
        "EXEC xp_cmdshell('dir')",
        "SELECT * FROM information_schema.tables",
    ]
    
    print("\n2️⃣ Testing malicious SQL injection attempts:")
    blocked_count = 0
    
    for i, sql in enumerate(malicious_queries, 1):
        try:
            get_db_rows(sql, [])
            print(f"❌ Malicious query {i}: NOT BLOCKED - {sql[:40]}...")
        except ValueError as e:
            if "SQL execution not allowed" in str(e):
                print(f"✅ Malicious query {i}: BLOCKED - {sql[:40]}...")
                blocked_count += 1
            else:
                print(f"❓ Malicious query {i}: Failed for other reason - {sql[:40]}...")
        except Exception as e:
            print(f"❓ Malicious query {i}: Failed with {type(e).__name__} - {sql[:40]}...")
    
    success_rate = blocked_count / len(malicious_queries) * 100
    print(f"\n📊 Security Test Results: {blocked_count}/{len(malicious_queries)} malicious queries blocked ({success_rate:.1f}%)")
    
    return blocked_count == len(malicious_queries)

def test_middleware_patterns():
    """Test the middleware SQL injection pattern detection."""
    print("\n🧪 Testing middleware pattern detection...")
    
    from apps.core.sql_security import SQLInjectionProtectionMiddleware
    
    def dummy_get_response(request):
        return None
    
    middleware = SQLInjectionProtectionMiddleware(dummy_get_response)
    
    # Test malicious patterns
    malicious_inputs = [
        "1' OR '1'='1",
        "'; DROP TABLE users; --",
        "UNION SELECT username FROM users",
        "1; EXEC xp_cmdshell('dir')",
        "SELECT @@version",
        "/* comment */ UNION",
        "1' AND SLEEP(5) --",
    ]
    
    # Test safe inputs
    safe_inputs = [
        "john@company.com",
        "Asset #123",
        "Normal search text",
        "User's Name",
        "Location: Building A",
    ]
    
    print("\n3️⃣ Testing malicious pattern detection:")
    malicious_detected = 0
    for i, input_text in enumerate(malicious_inputs, 1):
        is_malicious = middleware._contains_sql_injection(input_text)
        if is_malicious:
            print(f"✅ Malicious input {i}: DETECTED - {input_text[:30]}...")
            malicious_detected += 1
        else:
            print(f"❌ Malicious input {i}: NOT DETECTED - {input_text[:30]}...")
    
    print("\n4️⃣ Testing safe input handling:")
    safe_blocked = 0
    for i, input_text in enumerate(safe_inputs, 1):
        is_malicious = middleware._contains_sql_injection(input_text)
        if is_malicious:
            print(f"❌ Safe input {i}: INCORRECTLY BLOCKED - {input_text[:30]}...")
            safe_blocked += 1
        else:
            print(f"✅ Safe input {i}: CORRECTLY ALLOWED - {input_text[:30]}...")
    
    malicious_rate = malicious_detected / len(malicious_inputs) * 100
    safe_rate = (len(safe_inputs) - safe_blocked) / len(safe_inputs) * 100
    
    print(f"\n📊 Pattern Detection Results:")
    print(f"   Malicious inputs detected: {malicious_detected}/{len(malicious_inputs)} ({malicious_rate:.1f}%)")
    print(f"   Safe inputs allowed: {len(safe_inputs) - safe_blocked}/{len(safe_inputs)} ({safe_rate:.1f}%)")
    
    return malicious_detected >= len(malicious_inputs) * 0.8 and safe_blocked == 0

def test_query_logging():
    """Test query logging functionality."""
    print("\n🧪 Testing query logging...")
    
    from apps.core.sql_security import QueryLogger
    import logging
    from io import StringIO
    
    # Setup test logging
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    logger = logging.getLogger('security')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    try:
        # Test logging
        QueryLogger.log_raw_query("SELECT * FROM test_table", [1, 2, 3], "test_function")
        
        # Check log output
        log_output = log_stream.getvalue()
        if "Raw SQL executed by test_function" in log_output and "SELECT * FROM test_table" in log_output:
            print("✅ Query logging: WORKING")
            return True
        else:
            print("❌ Query logging: NOT WORKING")
            return False
    finally:
        logger.removeHandler(handler)
        handler.close()

def main():
    """Run all security tests."""
    print("🔒 YOUTILITY3 SQL Security Verification")
    print("=" * 50)
    
    tests = [
        ("SQL Query Security", test_get_db_rows_security),
        ("Pattern Detection", test_middleware_patterns),
        ("Query Logging", test_query_logging),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} Test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} Test: FAILED with exception - {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SECURITY TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL SECURITY TESTS PASSED!")
        print("✅ SQL injection protection is working correctly")
        print("✅ Your system is protected against SQL injection attacks")
        return True
    else:
        print(f"\n⚠️  {total-passed} test(s) failed")
        print("❌ Please review the security implementation")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)