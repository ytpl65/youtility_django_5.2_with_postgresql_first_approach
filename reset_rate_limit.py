#!/usr/bin/env python3
"""
Script to reset rate limiting cache for login attempts.
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

from django.core.cache import cache
from apps.core.rate_limiting import get_client_ip

def reset_all_rate_limits():
    """Reset all rate limiting cache entries."""
    print("🔄 Resetting all rate limiting cache...")
    
    # Get all cache keys (this method depends on cache backend)
    try:
        # For Redis cache backend
        if hasattr(cache, '_cache') and hasattr(cache._cache, 'get_client'):
            redis_client = cache._cache.get_client()
            keys = redis_client.keys('rate_limit:*')
            if keys:
                redis_client.delete(*keys)
                print(f"✅ Deleted {len(keys)} rate limit cache entries")
            else:
                print("ℹ️ No rate limit cache entries found")
                
            # Also clear login attempt keys
            login_keys = redis_client.keys('rate_limit:login_attempts:*')
            failed_ip_keys = redis_client.keys('rate_limit:failed_login_ip:*')
            failed_user_keys = redis_client.keys('rate_limit:failed_login_user:*')
            
            all_keys = login_keys + failed_ip_keys + failed_user_keys
            if all_keys:
                redis_client.delete(*all_keys)
                print(f"✅ Deleted {len(all_keys)} additional login cache entries")
                
        else:
            print("⚠️ Unable to access Redis client directly")
            print("💡 Try the manual reset methods below")
            
    except Exception as e:
        print(f"❌ Error accessing cache: {e}")
        print("💡 Try the manual reset methods below")

def reset_ip_rate_limit(ip_address):
    """Reset rate limit for specific IP address."""
    print(f"🔄 Resetting rate limit for IP: {ip_address}")
    
    keys_to_delete = [
        f"rate_limit:login_attempts:{ip_address}",
        f"rate_limit:failed_login_ip:{ip_address}"
    ]
    
    for key in keys_to_delete:
        cache.delete(key)
        print(f"✅ Deleted cache key: {key}")

def reset_username_rate_limit(username):
    """Reset rate limit for specific username."""
    print(f"🔄 Resetting rate limit for username: {username}")
    
    key = f"rate_limit:failed_login_user:{username}"
    cache.delete(key)
    print(f"✅ Deleted cache key: {key}")

def show_current_limits():
    """Show current rate limit status."""
    print("📊 Current rate limit cache status:")
    
    # This is a simplified check - you might need to adjust based on your specific needs
    sample_keys = [
        "rate_limit:login_attempts:127.0.0.1",
        "rate_limit:failed_login_ip:127.0.0.1",
    ]
    
    for key in sample_keys:
        value = cache.get(key)
        if value:
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: Not set")

def main():
    """Main function to handle command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Reset rate limiting cache')
    parser.add_argument('--all', action='store_true', help='Reset all rate limits')
    parser.add_argument('--ip', help='Reset rate limit for specific IP address')
    parser.add_argument('--username', help='Reset rate limit for specific username')
    parser.add_argument('--show', action='store_true', help='Show current rate limit status')
    
    args = parser.parse_args()
    
    if args.all:
        reset_all_rate_limits()
    elif args.ip:
        reset_ip_rate_limit(args.ip)
    elif args.username:
        reset_username_rate_limit(args.username)
    elif args.show:
        show_current_limits()
    else:
        print("🚀 Rate Limit Reset Tool")
        print("=" * 40)
        print("Choose an option:")
        print("1. Reset all rate limits")
        print("2. Reset for specific IP")
        print("3. Reset for specific username") 
        print("4. Show current status")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            reset_all_rate_limits()
        elif choice == '2':
            ip = input("Enter IP address: ").strip()
            reset_ip_rate_limit(ip)
        elif choice == '3':
            username = input("Enter username: ").strip()
            reset_username_rate_limit(username)
        elif choice == '4':
            show_current_limits()
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()