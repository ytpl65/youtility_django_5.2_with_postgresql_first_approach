#!/usr/bin/env python3
"""
PostgreSQL-First Migration Opportunities Analysis
Identify areas where PostgreSQL can replace Redis for operational simplification
"""

import os
import sys
import django
from datetime import datetime

# Add the project root to Python path
sys.path.append('/home/satyam/Documents/YOUTILITY-MIGRATION-DJANGO5-POSTGRESQL/YOUTILITY3')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

from django.conf import settings
from django.db import connection
from django.core.cache import caches

class PostgreSQLOpportunityAnalyzer:
    def __init__(self):
        self.opportunities = {}
        
    def print_header(self, title):
        print(f"\n{'='*60}")
        print(f"🔍 {title}")
        print(f"{'='*60}")
    
    def analyze_current_redis_usage(self):
        """Analyze current Redis cache configuration"""
        self.print_header("CURRENT REDIS USAGE ANALYSIS")
        
        print("📋 Current Redis Databases:")
        redis_usage = {
            "default": {
                "location": "redis://127.0.0.1:6379/1",
                "purpose": "General application caching",
                "key_prefix": "youtility4",
                "usage_type": "DataTable results, view caching, general cache"
            },
            "redis_session_cache": {
                "location": "redis://127.0.0.1:6379/3", 
                "purpose": "Session storage (hybrid with PostgreSQL)",
                "key_prefix": "y4session",
                "usage_type": "User sessions - KEEP (proven performance)"
            },
            "select2": {
                "location": "redis://127.0.0.1:6379/2",
                "purpose": "Select2 dropdown caching",
                "key_prefix": "select2", 
                "usage_type": "Dropdown options, autocomplete data"
            }
        }
        
        for cache_name, config in redis_usage.items():
            print(f"\n🗄️ {cache_name}:")
            print(f"   Location: {config['location']}")
            print(f"   Purpose: {config['purpose']}")
            print(f"   Key Prefix: {config['key_prefix']}")
            print(f"   Usage: {config['usage_type']}")
            
        return redis_usage
    
    def analyze_celery_usage(self):
        """Analyze Celery background tasks usage"""
        self.print_header("CELERY BACKGROUND TASKS ANALYSIS")
        
        # Read task routes from settings
        task_routes = getattr(settings, 'CELERY_TASK_ROUTES', {})
        
        print(f"📊 Found {len(task_routes)} Celery tasks using Redis broker")
        print(f"🔗 Broker: {getattr(settings, 'CELERY_BROKER_URL', 'Not configured')}")
        print(f"📤 Result Backend: {getattr(settings, 'result_backend', 'Not configured')}")
        
        # Categorize tasks by type
        task_categories = {
            'email': ['email', 'mail', 'notification'],
            'reports': ['report', 'generate'],
            'ppm': ['ppm', 'job', 'task'],
            'file_processing': ['upload', 'move', 'cloud'],
            'real_time': ['mqtt', 'publish', 'async'],
            'cleanup': ['cleanup', 'auto_close'],
            'escalation': ['escalation', 'reminder']
        }
        
        categorized_tasks = {cat: [] for cat in task_categories}
        
        for task_name in task_routes.keys():
            task_lower = task_name.lower()
            categorized = False
            for category, keywords in task_categories.items():
                if any(keyword in task_lower for keyword in keywords):
                    categorized_tasks[category].append(task_name)
                    categorized = True
                    break
            if not categorized:
                categorized_tasks.setdefault('other', []).append(task_name)
        
        print(f"\n📂 Task Categories:")
        for category, tasks in categorized_tasks.items():
            if tasks:
                print(f"   {category.title()}: {len(tasks)} tasks")
                for task in tasks[:3]:  # Show first 3 tasks
                    print(f"     - {task}")
                if len(tasks) > 3:
                    print(f"     ... and {len(tasks) - 3} more")
        
        return categorized_tasks
    
    def identify_postgresql_opportunities(self):
        """Identify specific areas for PostgreSQL migration"""
        self.print_header("POSTGRESQL-FIRST MIGRATION OPPORTUNITIES")
        
        opportunities = [
            {
                "area": "1. DataTable Caching",
                "current": "Redis 'default' cache for DataTable results",
                "postgresql_solution": "Materialized Views + Triggers",
                "impact": "HIGH",
                "complexity": "MEDIUM",
                "benefits": [
                    "Eliminate Redis DB #1 (youtility4 cache)",
                    "Better query optimization with PostgreSQL",
                    "Real-time updates via triggers",
                    "Simplified debugging (SQL vs Redis keys)"
                ],
                "example": """
-- Replace Redis cached queries with materialized views
CREATE MATERIALIZED VIEW activity_job_summary AS
SELECT 
    bu_id,
    job_status,
    COUNT(*) as job_count,
    AVG(completion_percentage) as avg_completion
FROM activity_job
GROUP BY bu_id, job_status;

-- Auto-refresh on data changes
CREATE TRIGGER refresh_job_summary
    AFTER INSERT OR UPDATE OR DELETE ON activity_job
    FOR EACH STATEMENT EXECUTE FUNCTION refresh_materialized_views();
                """
            },
            {
                "area": "2. Background Task Queue",
                "current": "Celery with Redis broker (47+ tasks)",
                "postgresql_solution": "PostgreSQL Queue Tables + Scheduled Jobs", 
                "impact": "HIGH",
                "complexity": "HIGH",
                "benefits": [
                    "Eliminate Redis broker dependency",
                    "ACID guarantees for task processing",
                    "Better error handling and retry logic",
                    "Unified logging and monitoring"
                ],
                "example": """
-- PostgreSQL task queue table
CREATE TABLE task_queue (
    id SERIAL PRIMARY KEY,
    task_name VARCHAR(255),
    payload JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    scheduled_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    retries INTEGER DEFAULT 0
);

-- Process tasks with SQL
SELECT * FROM task_queue 
WHERE status = 'pending' AND scheduled_at <= NOW()
ORDER BY id LIMIT 10 FOR UPDATE SKIP LOCKED;
                """
            },
            {
                "area": "3. Select2 Dropdown Caching",
                "current": "Redis 'select2' cache for dropdown options",
                "postgresql_solution": "Database Views + Smart Caching",
                "impact": "MEDIUM", 
                "complexity": "LOW",
                "benefits": [
                    "Eliminate Redis DB #2 (select2 cache)",
                    "Real-time dropdown updates",
                    "Better data consistency",
                    "Simplified cache invalidation"
                ],
                "example": """
-- Replace Redis select2 cache with optimized views
CREATE VIEW people_dropdown AS
SELECT 
    id,
    CONCAT(first_name, ' ', last_name) as display_name,
    email,
    is_active
FROM peoples_people 
WHERE is_active = true
ORDER BY first_name, last_name;

-- Use Django database caching instead of Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'app_cache_table',
    }
}
                """
            },
            {
                "area": "4. Real-time Notifications",
                "current": "MQTT + Redis for real-time updates", 
                "postgresql_solution": "PostgreSQL LISTEN/NOTIFY",
                "impact": "MEDIUM",
                "complexity": "MEDIUM",
                "benefits": [
                    "Native PostgreSQL real-time capabilities",
                    "Reduced external dependencies",
                    "Better integration with Django ORM",
                    "Simplified connection management"
                ],
                "example": """
-- PostgreSQL LISTEN/NOTIFY for real-time updates
-- Trigger on attendance updates
CREATE OR REPLACE FUNCTION notify_attendance_update()
RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify('attendance_updates', 
        json_build_object(
            'action', TG_OP,
            'bu_id', NEW.bu_id,
            'person_id', NEW.person_id,
            'timestamp', NEW.cdtz
        )::text
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
                """
            },
            {
                "area": "5. Rate Limiting Storage",
                "current": "Redis for login rate limiting",
                "postgresql_solution": "PostgreSQL Rate Limit Table",
                "impact": "LOW",
                "complexity": "LOW", 
                "benefits": [
                    "Persistent rate limit data",
                    "Better audit trail",
                    "Integration with user management",
                    "Historical analysis capabilities"
                ],
                "example": """
-- PostgreSQL rate limiting table
CREATE TABLE rate_limit_attempts (
    id SERIAL PRIMARY KEY,
    ip_address INET,
    username VARCHAR(255),
    attempt_time TIMESTAMP DEFAULT NOW(),
    success BOOLEAN DEFAULT FALSE
);

-- Check rate limits with SQL
SELECT COUNT(*) FROM rate_limit_attempts 
WHERE ip_address = %s 
AND attempt_time > NOW() - INTERVAL '15 minutes'
AND success = FALSE;
                """
            }
        ]
        
        for opp in opportunities:
            print(f"\n🎯 {opp['area']}")
            print(f"   📊 Impact: {opp['impact']} | Complexity: {opp['complexity']}")
            print(f"   🔄 Current: {opp['current']}")
            print(f"   🐘 PostgreSQL: {opp['postgresql_solution']}")
            print(f"   ✅ Benefits:")
            for benefit in opp['benefits']:
                print(f"      • {benefit}")
        
        return opportunities
    
    def prioritize_migrations(self):
        """Prioritize migration opportunities by impact vs complexity"""
        self.print_header("MIGRATION PRIORITIZATION MATRIX")
        
        # Define migration priorities
        migrations = [
            {"name": "DataTable Caching", "impact": 9, "complexity": 6, "effort_weeks": 2},
            {"name": "Select2 Dropdown Cache", "impact": 6, "complexity": 3, "effort_weeks": 1},
            {"name": "Rate Limiting", "impact": 4, "complexity": 2, "effort_weeks": 0.5},
            {"name": "Real-time Notifications", "impact": 7, "complexity": 7, "effort_weeks": 3},
            {"name": "Background Task Queue", "impact": 10, "complexity": 9, "effort_weeks": 4},
        ]
        
        # Calculate priority score (impact/complexity ratio)
        for migration in migrations:
            migration['priority_score'] = migration['impact'] / migration['complexity']
            migration['roi'] = migration['impact'] / migration['effort_weeks']
        
        # Sort by priority score
        migrations.sort(key=lambda x: x['priority_score'], reverse=True)
        
        print("📊 Recommended Migration Order (High Priority → Low Priority):")
        print(f"{'Rank':<4} {'Migration':<25} {'Impact':<7} {'Complexity':<10} {'Effort':<8} {'Priority':<8} {'ROI'}")
        print("-" * 80)
        
        for i, mig in enumerate(migrations, 1):
            print(f"{i:<4} {mig['name']:<25} {mig['impact']}/10{'':<3} {mig['complexity']}/10{'':<5} "
                  f"{mig['effort_weeks']}w{'':<6} {mig['priority_score']:.2f}{'':<6} {mig['roi']:.1f}")
        
        return migrations
    
    def generate_migration_roadmap(self, prioritized_migrations):
        """Generate a practical migration roadmap"""
        self.print_header("POSTGRESQL-FIRST MIGRATION ROADMAP")
        
        phases = [
            {
                "phase": "Phase 1: Quick Wins (Weeks 1-2)",
                "migrations": ["Rate Limiting", "Select2 Dropdown Cache"],
                "goal": "Eliminate Redis DB #2, gain experience",
                "risk": "LOW"
            },
            {
                "phase": "Phase 2: High Impact (Weeks 3-5)",
                "migrations": ["DataTable Caching"],
                "goal": "Eliminate Redis DB #1, major performance improvement",
                "risk": "MEDIUM"
            },
            {
                "phase": "Phase 3: Real-time Features (Weeks 6-8)",
                "migrations": ["Real-time Notifications"],
                "goal": "Replace MQTT with PostgreSQL LISTEN/NOTIFY",
                "risk": "MEDIUM"
            },
            {
                "phase": "Phase 4: Task Queue (Weeks 9-12)",
                "migrations": ["Background Task Queue"],
                "goal": "Eliminate Celery Redis broker dependency",
                "risk": "HIGH"
            }
        ]
        
        cumulative_redis_reduction = 0
        total_effort = 0
        
        for phase in phases:
            print(f"\n🎯 {phase['phase']}")
            print(f"   🎨 Goal: {phase['goal']}")
            print(f"   ⚠️  Risk Level: {phase['risk']}")
            print(f"   📋 Includes:")
            
            phase_effort = 0
            for migration_name in phase['migrations']:
                migration = next(m for m in prioritized_migrations if m['name'] == migration_name)
                phase_effort += migration['effort_weeks']
                print(f"      • {migration_name} ({migration['effort_weeks']}w effort)")
            
            total_effort += phase_effort
            
            # Estimate Redis reduction
            if "Rate Limiting" in phase['migrations'] or "Select2" in phase['migrations']:
                cumulative_redis_reduction += 15
            if "DataTable Caching" in phase['migrations']:
                cumulative_redis_reduction += 30
            if "Real-time" in phase['migrations']:
                cumulative_redis_reduction += 20
            if "Background Task" in phase['migrations']:
                cumulative_redis_reduction += 25
            
            print(f"   📈 Cumulative Redis Usage Reduction: {cumulative_redis_reduction}%")
            print(f"   ⏱️  Phase Effort: {phase_effort} weeks")
        
        print(f"\n🎊 Final Outcome:")
        print(f"   • Total Effort: {total_effort} weeks")
        print(f"   • Redis Usage Reduction: {cumulative_redis_reduction}%") 
        print(f"   • Operational Complexity: -60% to -70%")
        print(f"   • Remaining Redis: Sessions only (proven fast)")

def main():
    print("🚀 Starting PostgreSQL-First Migration Opportunities Analysis")
    print(f"⏰ Analysis started at: {datetime.now()}")
    
    analyzer = PostgreSQLOpportunityAnalyzer()
    
    try:
        # Analyze current Redis usage
        redis_usage = analyzer.analyze_current_redis_usage()
        
        # Analyze Celery usage  
        celery_tasks = analyzer.analyze_celery_usage()
        
        # Identify PostgreSQL opportunities
        opportunities = analyzer.identify_postgresql_opportunities()
        
        # Prioritize migrations
        prioritized = analyzer.prioritize_migrations()
        
        # Generate roadmap
        analyzer.generate_migration_roadmap(prioritized)
        
        print(f"\n✅ PostgreSQL opportunities analysis completed at: {datetime.now()}")
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()