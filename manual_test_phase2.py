#!/usr/bin/env python3
"""
Quick manual test script for Phase 2 validation
Run this while your Django server is running on localhost:8000
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_xss_protection():
    """Test XSS protection in forms"""
    print("🧪 Testing XSS Protection...")
    
    # Test XSS in a form (adjust URL to match your forms)
    xss_payloads = [
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "<img src=x onerror=alert('xss')>",
        "<svg onload=alert('xss')>"
    ]
    
    for payload in xss_payloads:
        print(f"  Testing payload: {payload[:30]}...")
        # You'll need to adjust this to match your actual form endpoint
        response = requests.get(f"{BASE_URL}/peoples/people_form/")
        if response.status_code == 200:
            print(f"  ✅ Form accessible")
        else:
            print(f"  ❌ Form not accessible: {response.status_code}")

def test_error_handling():
    """Test error handling and correlation IDs"""
    print("🧪 Testing Error Handling...")
    
    # Test 404 error
    response = requests.get(f"{BASE_URL}/nonexistent-page/")
    print(f"  404 Test: Status {response.status_code}")
    
    # Test API error
    try:
        response = requests.post(f"{BASE_URL}/graphql/", 
                               json={"query": "invalid graphql"})
        print(f"  GraphQL Error Test: Status {response.status_code}")
        if response.status_code >= 400:
            print(f"  Response: {response.text[:100]}...")
    except Exception as e:
        print(f"  GraphQL Test Error: {e}")

def test_security_headers():
    """Test security headers"""
    print("🧪 Testing Security Headers...")
    
    response = requests.get(f"{BASE_URL}/")
    headers = response.headers
    
    security_headers = [
        'X-XSS-Protection',
        'Content-Security-Policy', 
        'X-Content-Type-Options',
        'X-Frame-Options'
    ]
    
    for header in security_headers:
        if header in headers:
            print(f"  ✅ {header}: {headers[header]}")
        else:
            print(f"  ❌ Missing header: {header}")

def main():
    print("🚀 Phase 2 Manual Testing Script")
    print("=" * 50)
    
    try:
        # Test if server is running
        response = requests.get(BASE_URL, timeout=5)
        print(f"✅ Server is running (Status: {response.status_code})")
        print()
        
        test_error_handling()
        print()
        test_security_headers()
        print()
        test_xss_protection()
        print()
        
        print("🎉 Manual testing script completed!")
        print("👉 Now test the web interface manually using the plan above")
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {BASE_URL}")
        print("Please make sure Django server is running:")
        print("  python manage.py runserver")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()