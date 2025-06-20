#!/usr/bin/env python3
"""
Phase 2A: Materialized Views Implementation
Create materialized views for high-priority dropdown data with auto-refresh triggers

This script implements:
1. Materialized views for top dropdown candidates
2. Automatic refresh triggers
3. Performance optimization indexes
4. Management commands for maintenance
"""

import os
import sys
import django
import time

# Add the project root to Python path
sys.path.append('/home/satyam/Documents/YOUTILITY-MIGRATION-DJANGO5-POSTGRESQL/YOUTILITY3')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

from django.db import connection, transaction
from django.core.management.base import BaseCommand

class MaterializedViewManager:
    """Manage materialized views for dropdown optimization"""
    
    def __init__(self):
        self.materialized_views = []
        
    def create_people_dropdown_mv(self):
        """Create materialized view for People dropdown"""
        print("🔸 Creating People dropdown materialized view...")
        
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Drop if exists
                    cursor.execute("DROP MATERIALIZED VIEW IF EXISTS mv_people_dropdown CASCADE;")
                    
                    # Create materialized view
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW mv_people_dropdown AS
                        SELECT 
                            p.id,
                            p.peoplename as text,
                            p.loginid,
                            p.email,
                            p.mobno,
                            p.enable,
                            p.tenant_id,
                            p.mdtz as last_modified
                        FROM people p
                        WHERE p.enable = true
                        ORDER BY p.peoplename;
                    """)
                    
                    # Create indexes
                    cursor.execute("""
                        CREATE UNIQUE INDEX idx_mv_people_dropdown_id 
                        ON mv_people_dropdown (id);
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX idx_mv_people_dropdown_tenant 
                        ON mv_people_dropdown (tenant_id, enable);
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX idx_mv_people_dropdown_text 
                        ON mv_people_dropdown (text);
                    """)
                    
                    print("   ✅ People dropdown materialized view created")
                    self.materialized_views.append('mv_people_dropdown')
                    
        except Exception as e:
            print(f"   ❌ People dropdown MV creation failed: {e}")
    
    def create_location_dropdown_mv(self):
        """Create materialized view for Location dropdown"""
        print("🔸 Creating Location dropdown materialized view...")
        
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Drop if exists
                    cursor.execute("DROP MATERIALIZED VIEW IF EXISTS mv_location_dropdown CASCADE;")
                    
                    # Create materialized view
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW mv_location_dropdown AS
                        SELECT 
                            l.id,
                            l.locname as text,
                            l.loccode,
                            l.gpslocation,
                            l.iscritical,
                            l.enable,
                            l.tenant_id,
                            l.mdtz as last_modified
                        FROM location l
                        WHERE l.enable = true
                        ORDER BY l.locname;
                    """)
                    
                    # Create indexes
                    cursor.execute("""
                        CREATE UNIQUE INDEX idx_mv_location_dropdown_id 
                        ON mv_location_dropdown (id);
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX idx_mv_location_dropdown_tenant 
                        ON mv_location_dropdown (tenant_id, enable);
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX idx_mv_location_dropdown_text 
                        ON mv_location_dropdown (text);
                    """)
                    
                    print("   ✅ Location dropdown materialized view created")
                    self.materialized_views.append('mv_location_dropdown')
                    
        except Exception as e:
            print(f"   ❌ Location dropdown MV creation failed: {e}")
    
    def create_asset_dropdown_mv(self):
        """Create materialized view for Asset dropdown"""
        print("🔸 Creating Asset dropdown materialized view...")
        
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Drop if exists
                    cursor.execute("DROP MATERIALIZED VIEW IF EXISTS mv_asset_dropdown CASCADE;")
                    
                    # Create materialized view
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW mv_asset_dropdown AS
                        SELECT 
                            a.id,
                            a.assetname as text,
                            a.assetcode,
                            a.identifier,
                            l.locname as location_name,
                            a.location_id,
                            a.enable,
                            a.tenant_id,
                            a.mdtz as last_modified
                        FROM asset a
                        LEFT JOIN location l ON a.location_id = l.id
                        WHERE a.enable = true
                        ORDER BY a.assetname;
                    """)
                    
                    # Create indexes
                    cursor.execute("""
                        CREATE UNIQUE INDEX idx_mv_asset_dropdown_id 
                        ON mv_asset_dropdown (id);
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX idx_mv_asset_dropdown_tenant 
                        ON mv_asset_dropdown (tenant_id, enable);
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX idx_mv_asset_dropdown_location 
                        ON mv_asset_dropdown (location_id);
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX idx_mv_asset_dropdown_text 
                        ON mv_asset_dropdown (text);
                    """)
                    
                    print("   ✅ Asset dropdown materialized view created")
                    self.materialized_views.append('mv_asset_dropdown')
                    
        except Exception as e:
            print(f"   ❌ Asset dropdown MV creation failed: {e}")
    
    def create_refresh_triggers(self):
        """Create automatic refresh triggers for materialized views"""
        print("🔸 Creating automatic refresh triggers...")
        
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    
                    # Create trigger function for refresh
                    cursor.execute("""
                        CREATE OR REPLACE FUNCTION refresh_materialized_views()
                        RETURNS TRIGGER AS $$
                        BEGIN
                            -- Refresh materialized views based on which table was modified
                            IF TG_TABLE_NAME = 'people' THEN
                                REFRESH MATERIALIZED VIEW CONCURRENTLY mv_people_dropdown;
                            ELSIF TG_TABLE_NAME = 'location' THEN
                                REFRESH MATERIALIZED VIEW CONCURRENTLY mv_location_dropdown;
                            ELSIF TG_TABLE_NAME = 'asset' THEN
                                REFRESH MATERIALIZED VIEW CONCURRENTLY mv_asset_dropdown;
                            END IF;
                            
                            RETURN NULL;
                        END;
                        $$ LANGUAGE plpgsql;
                    """)
                    
                    # Create triggers for each table
                    trigger_configs = [
                        ('people', 'mv_people_dropdown'),
                        ('location', 'mv_location_dropdown'),
                        ('asset', 'mv_asset_dropdown')
                    ]
                    
                    for table_name, mv_name in trigger_configs:
                        # Drop existing triggers
                        cursor.execute(f"""
                            DROP TRIGGER IF EXISTS trigger_refresh_{mv_name} ON {table_name};
                        """)
                        
                        # Create new trigger
                        cursor.execute(f"""
                            CREATE TRIGGER trigger_refresh_{mv_name}
                            AFTER INSERT OR UPDATE OR DELETE
                            ON {table_name}
                            FOR EACH STATEMENT
                            EXECUTE FUNCTION refresh_materialized_views();
                        """)
                    
                    print("   ✅ Automatic refresh triggers created")
                    
        except Exception as e:
            print(f"   ❌ Trigger creation failed: {e}")
    
    def create_manual_refresh_function(self):
        """Create function for manual refresh of all materialized views"""
        print("🔸 Creating manual refresh function...")
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    CREATE OR REPLACE FUNCTION refresh_all_dropdown_mvs()
                    RETURNS TEXT AS $$
                    DECLARE
                        start_time TIMESTAMP;
                        end_time TIMESTAMP;
                        result_text TEXT;
                    BEGIN
                        start_time := clock_timestamp();
                        
                        -- Refresh all materialized views
                        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_people_dropdown;
                        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_location_dropdown;
                        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_asset_dropdown;
                        
                        end_time := clock_timestamp();
                        
                        result_text := 'Refreshed all dropdown materialized views in ' || 
                                     EXTRACT(MILLISECONDS FROM (end_time - start_time)) || 'ms';
                        
                        RETURN result_text;
                    END;
                    $$ LANGUAGE plpgsql;
                """)
                
                print("   ✅ Manual refresh function created")
                
        except Exception as e:
            print(f"   ❌ Manual refresh function creation failed: {e}")
    
    def test_materialized_views_performance(self):
        """Test materialized views performance"""
        print("🔸 Testing materialized views performance...")
        
        try:
            with connection.cursor() as cursor:
                # Test each materialized view
                test_queries = [
                    ("People Dropdown", "SELECT id, text FROM mv_people_dropdown LIMIT 50;"),
                    ("Location Dropdown", "SELECT id, text FROM mv_location_dropdown LIMIT 50;"),
                    ("Asset Dropdown", "SELECT id, text, location_name FROM mv_asset_dropdown LIMIT 50;")
                ]
                
                for name, query in test_queries:
                    start_time = time.time()
                    cursor.execute(query)
                    results = cursor.fetchall()
                    query_time = (time.time() - start_time) * 1000
                    
                    print(f"   📊 {name}: {query_time:.2f}ms ({len(results)} records)")
                
                # Test complex query with JOINs
                start_time = time.time()
                cursor.execute("""
                    SELECT 
                        p.id, p.text as person_name,
                        a.text as asset_name,
                        l.text as location_name
                    FROM mv_people_dropdown p
                    CROSS JOIN mv_asset_dropdown a
                    CROSS JOIN mv_location_dropdown l
                    LIMIT 100;
                """)
                complex_results = cursor.fetchall()
                complex_time = (time.time() - start_time) * 1000
                
                print(f"   📊 Complex JOIN query: {complex_time:.2f}ms ({len(complex_results)} records)")
                
        except Exception as e:
            print(f"   ❌ Performance testing failed: {e}")
    
    def verify_materialized_views(self):
        """Verify materialized views are working correctly"""
        print("🔸 Verifying materialized views...")
        
        try:
            with connection.cursor() as cursor:
                for mv_name in self.materialized_views:
                    # Check if materialized view exists
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM pg_matviews 
                            WHERE matviewname = %s
                        );
                    """, [mv_name])
                    
                    exists = cursor.fetchone()[0]
                    
                    if exists:
                        # Get row count
                        cursor.execute(f"SELECT COUNT(*) FROM {mv_name};")
                        count = cursor.fetchone()[0]
                        
                        # Get last refresh time
                        cursor.execute("""
                            SELECT schemaname, matviewname, hasindexes, ispopulated
                            FROM pg_matviews 
                            WHERE matviewname = %s;
                        """, [mv_name])
                        
                        schema, name, has_indexes, is_populated = cursor.fetchone()
                        
                        print(f"   ✅ {mv_name}: {count} rows, "
                              f"indexes: {'Yes' if has_indexes else 'No'}, "
                              f"populated: {'Yes' if is_populated else 'No'}")
                    else:
                        print(f"   ❌ {mv_name}: Not found")
                
        except Exception as e:
            print(f"   ❌ Verification failed: {e}")
    
    def create_all_materialized_views(self):
        """Create all materialized views and supporting infrastructure"""
        print("🚀 Creating Materialized Views for Dropdown Optimization")
        print("=" * 60)
        
        # Create materialized views
        self.create_people_dropdown_mv()
        self.create_location_dropdown_mv()
        self.create_asset_dropdown_mv()
        
        # Create supporting infrastructure
        self.create_refresh_triggers()
        self.create_manual_refresh_function()
        
        # Verify and test
        self.verify_materialized_views()
        self.test_materialized_views_performance()
        
        print(f"\n✅ Materialized Views Implementation Complete!")
        print(f"📊 Created {len(self.materialized_views)} materialized views:")
        for mv in self.materialized_views:
            print(f"   • {mv}")
        
        print("\n🔧 Management Functions Available:")
        print("   • refresh_all_dropdown_mvs() - Manual refresh all views")
        print("   • Automatic triggers on data changes")
        
        return self.materialized_views

def main():
    """Main execution function"""
    manager = MaterializedViewManager()
    created_views = manager.create_all_materialized_views()
    
    print(f"\n🎯 Next Steps:")
    print("   1. Integrate with Select2 cache backend")
    print("   2. Update dropdown queries to use materialized views")
    print("   3. Monitor performance improvements")
    print("   4. Set up monitoring for refresh operations")
    
    return created_views

if __name__ == "__main__":
    main()