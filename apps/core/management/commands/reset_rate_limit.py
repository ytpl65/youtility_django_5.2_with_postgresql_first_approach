from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from datetime import timedelta
from apps.core.models import RateLimitAttempt


class Command(BaseCommand):
    help = 'Reset rate limiting data stored in PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Reset all rate limits'
        )
        parser.add_argument(
            '--ip',
            type=str,
            help='Reset rate limit for specific IP address'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Reset rate limit for specific username'
        )
        parser.add_argument(
            '--show',
            action='store_true',
            help='Show current rate limit status'
        )

    def handle(self, *args, **options):
        if options['all']:
            self.reset_all_rate_limits()
        elif options['ip']:
            self.reset_ip_rate_limit(options['ip'])
        elif options['username']:
            self.reset_username_rate_limit(options['username'])
        elif options['show']:
            self.show_current_limits()
        else:
            self.stdout.write(
                self.style.ERROR('Please specify an option: --all, --ip, --username, or --show')
            )

    def reset_all_rate_limits(self):
        """Reset all rate limiting entries in PostgreSQL."""
        self.stdout.write("🔄 Resetting all PostgreSQL rate limiting data...")
        
        # Count current entries
        total_attempts = RateLimitAttempt.objects.count()
        recent_attempts = RateLimitAttempt.objects.filter(
            attempt_time__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        self.stdout.write(f"   📊 Found {total_attempts} total attempts, {recent_attempts} in last 24h")
        
        if total_attempts > 0:
            # Delete all rate limit attempts
            deleted_count, _ = RateLimitAttempt.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f"   ✅ Deleted {deleted_count} rate limit attempts")
            )
        else:
            self.stdout.write(
                self.style.WARNING("   ℹ️  No rate limit attempts to reset")
            )
        
        self.stdout.write(self.style.SUCCESS("🎉 Rate limiting reset complete!"))

    def reset_ip_rate_limit(self, ip_address):
        """Reset rate limit for specific IP address."""
        self.stdout.write(f"🔄 Resetting rate limit for IP: {ip_address}")
        
        deleted_count, _ = RateLimitAttempt.objects.filter(ip_address=ip_address).delete()
        self.stdout.write(
            self.style.SUCCESS(f"✅ Deleted {deleted_count} rate limit attempts for IP: {ip_address}")
        )

    def reset_username_rate_limit(self, username):
        """Reset rate limit for specific username."""
        self.stdout.write(f"🔄 Resetting rate limit for username: {username}")
        
        deleted_count, _ = RateLimitAttempt.objects.filter(username=username).delete()
        self.stdout.write(
            self.style.SUCCESS(f"✅ Deleted {deleted_count} rate limit attempts for username: {username}")
        )

    def show_current_limits(self):
        """Show current rate limit status."""
        self.stdout.write("📊 Current PostgreSQL rate limit status:")
        
        total_attempts = RateLimitAttempt.objects.count()
        recent_attempts = RateLimitAttempt.objects.filter(
            attempt_time__gte=timezone.now() - timedelta(hours=24)
        ).count()
        failed_attempts = RateLimitAttempt.objects.filter(
            success=False,
            attempt_time__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        self.stdout.write(f"  Total logged attempts: {total_attempts}")
        self.stdout.write(f"  Attempts in last 24h: {recent_attempts}")
        self.stdout.write(f"  Failed attempts in last hour: {failed_attempts}")
        
        if recent_attempts > 0:
            self.stdout.write("\n  Recent attempts by IP:")
            recent_by_ip = RateLimitAttempt.objects.filter(
                attempt_time__gte=timezone.now() - timedelta(hours=24)
            ).values('ip_address').annotate(
                attempt_count=models.Count('id')
            ).order_by('-attempt_count')[:5]
            
            for entry in recent_by_ip:
                self.stdout.write(f"    {entry['ip_address']}: {entry['attempt_count']} attempts")