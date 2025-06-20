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

# PostgreSQL-based rate limiting no longer uses cache
# from django.core.cache import cache  
# from apps.core.rate_limiting import get_client_ip
from apps.core.models import RateLimitAttempt
import django.utils.timezone
import django.db.models

def reset_all_rate_limits():
    """Reset all rate limiting entries in PostgreSQL."""
    print("🔄 Resetting all PostgreSQL rate limiting data...")
    
    # Count current entries
    total_attempts = RateLimitAttempt.objects.count()
    recent_attempts = RateLimitAttempt.objects.filter(
        attempt_time__gte=django.utils.timezone.now() - django.utils.timedelta(hours=24)
    ).count()
    
    print(f"   📊 Found {total_attempts} total attempts, {recent_attempts} in last 24h")
    
    if total_attempts > 0:
        # Delete all rate limit attempts
        deleted_count, _ = RateLimitAttempt.objects.all().delete()
        print(f"   ✅ Deleted {deleted_count} rate limit attempts")
    else:
        print(f"   ℹ️  No rate limit attempts to reset")
    
    print("🎉 Rate limiting reset complete!")

def reset_ip_rate_limit(ip_address):
    """Reset rate limit for specific IP address."""
    print(f"🔄 Resetting rate limit for IP: {ip_address}")
    
    deleted_count, _ = RateLimitAttempt.objects.filter(ip_address=ip_address).delete()
    print(f"✅ Deleted {deleted_count} rate limit attempts for IP: {ip_address}")

def reset_username_rate_limit(username):
    """Reset rate limit for specific username."""
    print(f"🔄 Resetting rate limit for username: {username}")
    
    deleted_count, _ = RateLimitAttempt.objects.filter(username=username).delete()
    print(f"✅ Deleted {deleted_count} rate limit attempts for username: {username}")

def show_current_limits():
    """Show current rate limit status."""
    print("📊 Current PostgreSQL rate limit status:")
    
    from django.utils import timezone
    from datetime import timedelta
    
    total_attempts = RateLimitAttempt.objects.count()
    recent_attempts = RateLimitAttempt.objects.filter(
        attempt_time__gte=timezone.now() - timedelta(hours=24)
    ).count()
    failed_attempts = RateLimitAttempt.objects.filter(
        success=False,
        attempt_time__gte=timezone.now() - timedelta(hours=1)
    ).count()
    
    print(f"  Total logged attempts: {total_attempts}")
    print(f"  Attempts in last 24h: {recent_attempts}")
    print(f"  Failed attempts in last hour: {failed_attempts}")
    
    if recent_attempts > 0:
        print("\n  Recent attempts by IP:")
        recent_by_ip = RateLimitAttempt.objects.filter(
            attempt_time__gte=timezone.now() - timedelta(hours=24)
        ).values('ip_address').annotate(
            attempt_count=django.db.models.Count('id')
        ).order_by('-attempt_count')[:5]
        
        for entry in recent_by_ip:
            print(f"    {entry['ip_address']}: {entry['attempt_count']} attempts")

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