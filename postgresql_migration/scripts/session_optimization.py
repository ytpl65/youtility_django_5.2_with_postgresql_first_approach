#!/usr/bin/env python3
"""
PostgreSQL Session Optimization Script
Optimizes session storage and cleanup for pure PostgreSQL sessions
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append('/home/satyam/Documents/YOUTILITY-MIGRATION-DJANGO5-POSTGRESQL/YOUTILITY3')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

from django.db import connection
from django.core.management import execute_from_command_line

def optimize_session_tables():
    """Optimize PostgreSQL session tables for better performance"""
    print("🔧 Optimizing PostgreSQL session tables...")
    
    with connection.cursor() as cursor:
        # Create indexes on session table for better performance
        print("📊 Creating performance indexes...")
        
        # Index on session_key for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_django_session_key_hash 
            ON django_session USING hash(session_key);
        """)
        
        # Index on expire_date for cleanup operations
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_django_session_expire_date 
            ON django_session (expire_date);
        """)
        
        # Composite index for session queries (without immutable function)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_django_session_composite 
            ON django_session (expire_date, session_key);
        """)
        
        print("✅ Created session performance indexes")
        
        # Create cleanup function
        print("🧹 Creating session cleanup function...")
        cursor.execute("""
            CREATE OR REPLACE FUNCTION cleanup_expired_sessions() 
            RETURNS INTEGER AS $$
            DECLARE
                deleted_count INTEGER;
            BEGIN
                DELETE FROM django_session 
                WHERE expire_date < NOW();
                
                GET DIAGNOSTICS deleted_count = ROW_COUNT;
                
                -- Log the cleanup
                INSERT INTO auth_rate_limit_attempts (
                    ip_address,
                    username,
                    attempt_time,
                    success,
                    failure_reason
                ) VALUES (
                    '127.0.0.1'::inet,
                    'system',
                    NOW(),
                    true,
                    'Session cleanup: ' || deleted_count || ' expired sessions removed'
                );
                
                RETURN deleted_count;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        print("✅ Created session cleanup function")
        
        # Get session statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_sessions,
                COUNT(*) FILTER (WHERE expire_date > NOW()) as active_sessions,
                COUNT(*) FILTER (WHERE expire_date <= NOW()) as expired_sessions
            FROM django_session;
        """)
        
        stats = cursor.fetchone()
        total, active, expired = stats
        
        print(f"📈 Session Statistics:")
        print(f"   • Total sessions: {total}")
        print(f"   • Active sessions: {active}")
        print(f"   • Expired sessions: {expired}")
        
        # Clean up expired sessions
        if expired > 0:
            cursor.execute("SELECT cleanup_expired_sessions();")
            cleaned = cursor.fetchone()[0]
            print(f"🧹 Cleaned up {cleaned} expired sessions")

def create_session_management_command():
    """Create Django management command for session cleanup"""
    print("📝 Creating session management command...")
    
    management_dir = "apps/core/management"
    commands_dir = f"{management_dir}/commands"
    
    # Create directories if they don't exist
    os.makedirs(commands_dir, exist_ok=True)
    
    # Create __init__.py files
    for dir_path in [management_dir, commands_dir]:
        init_file = f"{dir_path}/__init__.py"
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write("# Django management commands\n")
    
    # Create cleanup command
    command_content = '''"""
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
'''
    
    with open(f"{commands_dir}/cleanup_sessions.py", 'w') as f:
        f.write(command_content)
    
    print("✅ Created cleanup_sessions management command")

if __name__ == "__main__":
    print("🚀 PostgreSQL Session Optimization Starting...")
    print("")
    
    # Run Django migrations to ensure session table exists
    print("📦 Ensuring session tables exist...")
    execute_from_command_line(['manage.py', 'migrate', 'sessions', '--verbosity=0'])
    
    # Optimize session tables
    optimize_session_tables()
    
    # Create management command
    create_session_management_command()
    
    print("")
    print("✅ PostgreSQL Session Optimization Complete!")
    print("")
    print("🎯 Benefits:")
    print("   • Pure PostgreSQL sessions (eliminated Redis dependency)")
    print("   • Optimized indexes for fast session lookups")
    print("   • Automated cleanup of expired sessions")
    print("   • Management command: python manage.py cleanup_sessions")
    print("")
    print("💡 Operational Complexity Reduced:")
    print("   • No Redis session cache to monitor")
    print("   • Single database for all persistent data")
    print("   • Simplified backup and recovery procedures")