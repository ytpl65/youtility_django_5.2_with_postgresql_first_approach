"""
Django management command for PostgreSQL session cleanup
Usage: python manage.py cleanup_sessions
"""

from django.core.management.base import BaseCommand
from django.db import connection
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up expired sessions from PostgreSQL database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        with connection.cursor() as cursor:
            # Count expired sessions
            cursor.execute("""
                SELECT COUNT(*) FROM django_session 
                WHERE expire_date < NOW();
            """)
            expired_count = cursor.fetchone()[0]
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f'DRY RUN: Would delete {expired_count} expired sessions')
                )
                return
            
            if expired_count == 0:
                self.stdout.write(
                    self.style.SUCCESS('No expired sessions to clean up')
                )
                return
            
            # Clean up expired sessions
            cursor.execute("SELECT cleanup_expired_sessions();")
            deleted_count = cursor.fetchone()[0]
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleaned up {deleted_count} expired sessions')
            )
            
            logger.info(f'Session cleanup completed: {deleted_count} sessions removed')
