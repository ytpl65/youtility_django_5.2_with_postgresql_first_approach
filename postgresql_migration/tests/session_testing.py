#!/usr/bin/env python3
"""
Manual PostgreSQL Session Testing Script
Test and verify pure PostgreSQL session functionality
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append('/home/satyam/Documents/YOUTILITY-MIGRATION-DJANGO5-POSTGRESQL/YOUTILITY3')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore
from django.utils import timezone
from django.db import connection
import json

def test_session_storage():
    """Test PostgreSQL session storage functionality"""
    print("🧪 Testing PostgreSQL Session Storage")
    print("=" * 50)
    
    # Test 1: Create a new session
    print("🔧 Test 1: Creating new session...")
    session = SessionStore()
    session['test_key'] = 'test_value'
    session['user_data'] = {'name': 'Test User', 'role': 'admin'}
    session['timestamp'] = str(timezone.now())
    session.save()
    
    session_key = session.session_key
    print(f"✅ Created session: {session_key}")
    
    # Test 2: Verify session in database
    print("\n🔍 Test 2: Verifying session in database...")
    try:
        db_session = Session.objects.get(session_key=session_key)
        print(f"✅ Found session in database")
        print(f"   • Session Key: {db_session.session_key}")
        print(f"   • Expires: {db_session.expire_date}")
        print(f"   • Data Size: {len(db_session.session_data)} bytes")
        
        # Decode session data
        decoded_data = db_session.get_decoded()
        print(f"   • Decoded Keys: {list(decoded_data.keys())}")
    except Session.DoesNotExist:
        print("❌ Session not found in database!")
        return False
    
    # Test 3: Retrieve session data
    print("\n📖 Test 3: Retrieving session data...")
    retrieved_session = SessionStore(session_key=session_key)
    if retrieved_session.exists(session_key):
        print("✅ Session exists and can be retrieved")
        print(f"   • test_key: {retrieved_session.get('test_key')}")
        print(f"   • user_data: {retrieved_session.get('user_data')}")
    else:
        print("❌ Could not retrieve session!")
        return False
    
    # Test 4: Update session
    print("\n✏️  Test 4: Updating session...")
    retrieved_session['updated'] = True
    retrieved_session['update_time'] = str(timezone.now())
    retrieved_session.save()
    print("✅ Session updated successfully")
    
    # Test 5: Performance check
    print("\n⚡ Test 5: Performance check...")
    import time
    
    start_time = time.time()
    for i in range(10):
        test_session = SessionStore(session_key=session_key)
        _ = test_session.get('test_key')
    end_time = time.time()
    
    avg_time = (end_time - start_time) * 1000 / 10  # Convert to milliseconds
    print(f"✅ Average read time: {avg_time:.2f}ms per operation")
    
    # Test 6: Delete session
    print("\n🗑️  Test 6: Deleting test session...")
    retrieved_session.delete()
    
    if not Session.objects.filter(session_key=session_key).exists():
        print("✅ Session deleted successfully")
    else:
        print("❌ Session deletion failed!")
        return False
    
    return True

def show_session_configuration():
    """Show current session configuration"""
    print("\n⚙️  Current Session Configuration")
    print("=" * 50)
    
    from django.conf import settings
    
    print(f"📦 Session Engine: {settings.SESSION_ENGINE}")
    print(f"🍪 Cookie Age: {settings.SESSION_COOKIE_AGE} seconds")
    print(f"🔐 Cookie Secure: {getattr(settings, 'SESSION_COOKIE_SECURE', False)}")
    print(f"🔄 Save Every Request: {getattr(settings, 'SESSION_SAVE_EVERY_REQUEST', False)}")
    print(f"🚪 Expire at Browser Close: {getattr(settings, 'SESSION_EXPIRE_AT_BROWSER_CLOSE', False)}")

def show_live_session_monitoring():
    """Show live session monitoring commands"""
    print("\n📊 Live Session Monitoring Commands")
    print("=" * 50)
    
    print("🐘 PostgreSQL Commands:")
    print("""
-- View all sessions
SELECT session_key, expire_date, 
       CASE WHEN expire_date > NOW() THEN 'ACTIVE' ELSE 'EXPIRED' END as status,
       LENGTH(session_data) as size_bytes
FROM django_session 
ORDER BY expire_date DESC;

-- Count active vs expired sessions
SELECT 
    COUNT(*) FILTER (WHERE expire_date > NOW()) as active_sessions,
    COUNT(*) FILTER (WHERE expire_date <= NOW()) as expired_sessions,
    COUNT(*) as total_sessions
FROM django_session;

-- Show session size distribution
SELECT 
    CASE 
        WHEN LENGTH(session_data) < 1000 THEN 'Small (<1KB)'
        WHEN LENGTH(session_data) < 5000 THEN 'Medium (1-5KB)'
        ELSE 'Large (>5KB)'
    END as size_category,
    COUNT(*) as count
FROM django_session
GROUP BY size_category;
""")
    
    print("\n🐍 Django Commands:")
    print("python manage.py cleanup_sessions          # Clean expired sessions")
    print("python manage.py cleanup_sessions --dry-run # Show what would be cleaned")
    print("python manage.py shell                      # Interactive session inspection")

if __name__ == "__main__":
    print("🚀 PostgreSQL Session Testing & Monitoring")
    print("=" * 60)
    
    # Show configuration
    show_session_configuration()
    
    # Run tests
    print("\n" + "="*60)
    success = test_session_storage()
    
    if success:
        print("\n✅ All PostgreSQL session tests passed!")
        print("🎯 Session system is working correctly with pure PostgreSQL storage")
    else:
        print("\n❌ Some tests failed!")
        print("🔧 Check your session configuration")
    
    # Show monitoring commands
    show_live_session_monitoring()
    
    print("\n💡 Key Benefits of PostgreSQL Sessions:")
    print("   • No Redis dependency for sessions")
    print("   • ACID compliance for session data")
    print("   • Unified backup/recovery with main database")
    print("   • Simplified operational complexity")
    print("   • Built-in cleanup and optimization")