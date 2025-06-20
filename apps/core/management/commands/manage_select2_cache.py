"""
Django management command for PostgreSQL Select2 cache management
Usage: python manage.py manage_select2_cache [action]
"""

from django.core.management.base import BaseCommand
from django.core.cache import caches
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Manage PostgreSQL Select2 cache operations'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['stats', 'cleanup', 'clear', 'test'],
            help='Action to perform on Select2 cache'
        )
        parser.add_argument(
            '--tenant-id',
            type=int,
            default=1,
            help='Tenant ID for cache operations'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        action = options['action']
        tenant_id = options['tenant_id']
        dry_run = options['dry_run']

        try:
            select2_cache = caches['select2']
            
            if action == 'stats':
                self.show_stats(select2_cache)
            elif action == 'cleanup':
                self.cleanup_cache(select2_cache, dry_run)
            elif action == 'clear':
                self.clear_cache(select2_cache, dry_run)
            elif action == 'test':
                self.test_cache(select2_cache)
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error performing {action}: {str(e)}')
            )
            logger.error(f'Select2 cache management error: {e}')

    def show_stats(self, cache):
        """Show cache statistics"""
        self.stdout.write(self.style.SUCCESS('📊 Select2 Cache Statistics'))
        self.stdout.write('=' * 40)
        
        if hasattr(cache, 'get_stats'):
            stats = cache.get_stats()
            
            self.stdout.write(f"Total entries: {stats['total_entries']}")
            self.stdout.write(f"Active entries: {stats['active_entries']}")
            self.stdout.write(f"Expired entries: {stats['expired_entries']}")
            self.stdout.write(f"Average data size: {stats['avg_data_size_bytes']} bytes")
            self.stdout.write(f"Tenant ID: {stats['tenant_id']}")
            
            # Calculate efficiency
            if stats['total_entries'] > 0:
                efficiency = (stats['active_entries'] / stats['total_entries']) * 100
                self.stdout.write(f"Cache efficiency: {efficiency:.1f}%")
            
        else:
            self.stdout.write("Cache statistics not available")

    def cleanup_cache(self, cache, dry_run):
        """Clean up expired cache entries"""
        self.stdout.write(self.style.WARNING('🧹 Select2 Cache Cleanup'))
        
        if dry_run:
            self.stdout.write("DRY RUN: Would clean up expired entries")
            return
        
        if hasattr(cache, 'cleanup_expired'):
            deleted_count = cache.cleanup_expired()
            
            if deleted_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Cleaned up {deleted_count} expired entries')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ No expired entries to clean up')
                )
        else:
            self.stdout.write("Cache cleanup not supported")

    def clear_cache(self, cache, dry_run):
        """Clear all cache entries"""
        self.stdout.write(self.style.WARNING('🗑️  Select2 Cache Clear'))
        
        if dry_run:
            self.stdout.write("DRY RUN: Would clear all cache entries")
            return
        
        cache.clear()
        self.stdout.write(
            self.style.SUCCESS('✅ Cleared all Select2 cache entries')
        )

    def test_cache(self, cache):
        """Test cache functionality"""
        self.stdout.write(self.style.SUCCESS('🧪 Select2 Cache Test'))
        self.stdout.write('=' * 30)
        
        # Test basic operations
        test_key = 'test_dropdown'
        test_data = {
            'choices': [
                {'id': 1, 'text': 'Option 1'},
                {'id': 2, 'text': 'Option 2'},
                {'id': 3, 'text': 'Option 3'}
            ],
            'pagination': {'more': False}
        }
        
        # Test set
        self.stdout.write("Testing cache set...")
        result = cache.set(test_key, test_data, timeout=300)
        if result:
            self.stdout.write(self.style.SUCCESS('✅ Cache set successful'))
        else:
            self.stdout.write(self.style.ERROR('❌ Cache set failed'))
            return
        
        # Test get
        self.stdout.write("Testing cache get...")
        cached_data = cache.get(test_key)
        if cached_data == test_data:
            self.stdout.write(self.style.SUCCESS('✅ Cache get successful'))
        else:
            self.stdout.write(self.style.ERROR('❌ Cache get failed'))
        
        # Test batch operations
        self.stdout.write("Testing batch operations...")
        batch_data = {
            'people_dropdown': {'choices': [{'id': 1, 'text': 'John Doe'}]},
            'asset_dropdown': {'choices': [{'id': 1, 'text': 'Asset 1'}]},
            'site_dropdown': {'choices': [{'id': 1, 'text': 'Site 1'}]}
        }
        
        # Test set_many
        if hasattr(cache, 'set_many'):
            failed_keys = cache.set_many(batch_data, timeout=300)
            if not failed_keys:
                self.stdout.write(self.style.SUCCESS('✅ Batch set successful'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ Batch set failed for: {failed_keys}'))
        
        # Test get_many
        if hasattr(cache, 'get_many'):
            results = cache.get_many(list(batch_data.keys()))
            if len(results) == len(batch_data):
                self.stdout.write(self.style.SUCCESS('✅ Batch get successful'))
            else:
                self.stdout.write(self.style.ERROR('❌ Batch get failed'))
        
        # Cleanup test data
        cache.delete(test_key)
        if hasattr(cache, 'delete_many'):
            cache.delete_many(list(batch_data.keys()))
        
        self.stdout.write(self.style.SUCCESS('🎯 Cache test completed'))

    def show_database_info(self):
        """Show database-level cache information"""
        self.stdout.write(self.style.SUCCESS('🐘 Database Cache Information'))
        self.stdout.write('=' * 35)
        
        try:
            with connection.cursor() as cursor:
                # Check if table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'select2_cache'
                    );
                """)
                
                table_exists = cursor.fetchone()[0]
                
                if table_exists:
                    self.stdout.write("✅ Select2 cache table exists")
                    
                    # Get table size
                    cursor.execute("""
                        SELECT 
                            pg_size_pretty(pg_total_relation_size('select2_cache')) as total_size,
                            pg_size_pretty(pg_relation_size('select2_cache')) as table_size
                    """)
                    
                    size_info = cursor.fetchone()
                    self.stdout.write(f"📊 Table size: {size_info[1]}")
                    self.stdout.write(f"📊 Total size (with indexes): {size_info[0]}")
                    
                else:
                    self.stdout.write("❌ Select2 cache table does not exist")
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Database info error: {e}'))