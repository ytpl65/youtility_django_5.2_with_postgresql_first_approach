#!/usr/bin/env python3
"""
Phase 2A: Dropdown Usage Analysis for Materialized Views
Analyze current dropdown usage patterns to identify optimal candidates for materialized views

This script analyzes:
1. Select2 cache usage patterns
2. Model relationship analysis for dropdowns
3. Query frequency and performance bottlenecks
4. Static vs dynamic data classification
5. Materialized view candidates prioritization
"""

import os
import sys
import django
from collections import defaultdict
import time

# Add the project root to Python path
sys.path.append('/home/satyam/Documents/YOUTILITY-MIGRATION-DJANGO5-POSTGRESQL/YOUTILITY3')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

from django.db import connection
from django.core.cache import caches
from django.apps import apps
from django.db.models import Count, Q
import json

class DropdownAnalyzer:
    """Analyze dropdown usage patterns for materialized view optimization"""
    
    def __init__(self):
        self.select2_cache = caches['select2']
        self.analysis_results = {}
        
    def analyze_select2_cache_patterns(self):
        """Analyze current Select2 cache usage patterns"""
        print("🔍 Analyzing Select2 Cache Usage Patterns")
        print("=" * 45)
        
        try:
            # Get cache statistics
            if hasattr(self.select2_cache, 'get_stats'):
                stats = self.select2_cache.get_stats()
                print(f"📊 Current cache statistics:")
                print(f"   • Total entries: {stats['total_entries']}")
                print(f"   • Active entries: {stats['active_entries']}")
                print(f"   • Average data size: {stats['avg_data_size_bytes']} bytes")
                
                # Analyze cache content patterns
                self._analyze_cache_content()
            else:
                print("⚠️  Cache statistics not available")
                
        except Exception as e:
            print(f"❌ Cache analysis error: {e}")
    
    def _analyze_cache_content(self):
        """Analyze cache content to identify patterns"""
        print("\n🔸 Analyzing cache content patterns...")
        
        try:
            with connection.cursor() as cursor:
                # Get sample cache entries to analyze patterns
                cursor.execute("""
                    SELECT cache_key, cache_data, created_at
                    FROM select2_cache 
                    WHERE expires_at > NOW()
                    ORDER BY created_at DESC
                    LIMIT 50;
                """)
                
                cache_entries = cursor.fetchall()
                patterns = defaultdict(int)
                data_sizes = []
                
                for cache_key, cache_data, created_at in cache_entries:
                    # Analyze key patterns
                    if 'people' in cache_key.lower():
                        patterns['people_dropdowns'] += 1
                    elif 'asset' in cache_key.lower():
                        patterns['asset_dropdowns'] += 1
                    elif 'location' in cache_key.lower():
                        patterns['location_dropdowns'] += 1
                    elif 'type' in cache_key.lower():
                        patterns['type_dropdowns'] += 1
                    else:
                        patterns['other_dropdowns'] += 1
                    
                    # Analyze data size
                    data_sizes.append(len(cache_data))
                
                print(f"   📋 Cache key patterns found:")
                for pattern, count in patterns.items():
                    print(f"      • {pattern}: {count} entries")
                
                if data_sizes:
                    avg_size = sum(data_sizes) / len(data_sizes)
                    print(f"   📏 Average cached data size: {avg_size:.0f} bytes")
                
        except Exception as e:
            print(f"   ⚠️  Cache content analysis error: {e}")
    
    def analyze_model_relationships(self):
        """Analyze Django models to identify dropdown candidates"""
        print("\n🏗️  Analyzing Model Relationships for Dropdowns")
        print("=" * 48)
        
        # Key apps to analyze for dropdown models
        target_apps = ['peoples', 'activity', 'onboarding', 'work_order_management', 'attendance']
        dropdown_candidates = []
        
        for app_name in target_apps:
            try:
                app = apps.get_app_config(app_name)
                print(f"\n🔸 Analyzing {app_name} models...")
                
                for model in app.get_models():
                    model_info = self._analyze_model_for_dropdown_potential(model)
                    if model_info:
                        dropdown_candidates.append(model_info)
                        print(f"   ✅ {model.__name__}: {model_info['reason']}")
                
            except Exception as e:
                print(f"   ⚠️  Error analyzing {app_name}: {e}")
        
        self.analysis_results['dropdown_candidates'] = dropdown_candidates
        return dropdown_candidates
    
    def _analyze_model_for_dropdown_potential(self, model):
        """Analyze individual model for dropdown potential"""
        try:
            # Check if model has typical dropdown characteristics
            fields = [f.name for f in model._meta.fields]
            
            # Look for dropdown indicators
            dropdown_indicators = {
                'has_name_field': any(f in fields for f in ['name', 'title', 'description']),
                'has_enable_field': 'enable' in fields,
                'has_tenant_field': 'tenant' in fields or 'tenant_id' in fields,
                'has_foreign_keys': len([f for f in model._meta.fields if f.is_relation]) > 0,
                'small_dataset': False  # Will check this with actual query
            }
            
            # Check dataset size (for materialized view feasibility)
            try:
                count = model.objects.count()
                dropdown_indicators['small_dataset'] = count < 10000  # Arbitrary threshold
                dropdown_indicators['record_count'] = count
            except:
                dropdown_indicators['record_count'] = 0
            
            # Determine if this is a good dropdown candidate
            score = sum([
                dropdown_indicators['has_name_field'] * 3,
                dropdown_indicators['has_enable_field'] * 2,
                dropdown_indicators['has_tenant_field'] * 2,
                dropdown_indicators['small_dataset'] * 2,
                min(dropdown_indicators['has_foreign_keys'], 1) * 1
            ])
            
            if score >= 5:  # Threshold for consideration
                reasons = []
                if dropdown_indicators['has_name_field']:
                    reasons.append("has display field")
                if dropdown_indicators['has_enable_field']:
                    reasons.append("has enable flag")
                if dropdown_indicators['small_dataset']:
                    reasons.append(f"manageable size ({dropdown_indicators['record_count']} records)")
                
                return {
                    'model': model,
                    'app': model._meta.app_label,
                    'name': model.__name__,
                    'score': score,
                    'reason': ', '.join(reasons),
                    'indicators': dropdown_indicators
                }
            
        except Exception as e:
            # Skip models that can't be analyzed
            pass
        
        return None
    
    def analyze_query_patterns(self):
        """Analyze database query patterns for dropdown optimization"""
        print("\n📊 Analyzing Database Query Patterns")
        print("=" * 38)
        
        try:
            with connection.cursor() as cursor:
                # Enable query statistics if available
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                    );
                """)
                
                has_pg_stat = cursor.fetchone()[0]
                
                if has_pg_stat:
                    print("✅ pg_stat_statements extension available")
                    self._analyze_query_statistics(cursor)
                else:
                    print("⚠️  pg_stat_statements not available, using alternative analysis")
                    self._analyze_table_access_patterns(cursor)
                
        except Exception as e:
            print(f"❌ Query pattern analysis error: {e}")
    
    def _analyze_query_statistics(self, cursor):
        """Analyze query statistics for optimization opportunities"""
        try:
            # Get most frequent SELECT queries
            cursor.execute("""
                SELECT 
                    query,
                    calls,
                    mean_exec_time,
                    total_exec_time
                FROM pg_stat_statements 
                WHERE query LIKE '%SELECT%'
                  AND query NOT LIKE '%pg_stat%'
                ORDER BY calls DESC
                LIMIT 10;
            """)
            
            queries = cursor.fetchall()
            print("🔸 Top 10 most frequent SELECT queries:")
            
            for i, (query, calls, mean_time, total_time) in enumerate(queries, 1):
                # Truncate long queries
                short_query = query[:100] + "..." if len(query) > 100 else query
                print(f"   {i}. Calls: {calls}, Avg: {mean_time:.2f}ms")
                print(f"      Query: {short_query}")
                
        except Exception as e:
            print(f"   ⚠️  Query statistics error: {e}")
    
    def _analyze_table_access_patterns(self, cursor):
        """Alternative analysis when pg_stat_statements is not available"""
        try:
            # Analyze table sizes and relationships
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins,
                    n_tup_upd,
                    n_tup_del,
                    n_live_tup
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY n_live_tup DESC
                LIMIT 20;
            """)
            
            tables = cursor.fetchall()
            print("🔸 Database table activity analysis:")
            
            for schema, table, inserts, updates, deletes, live_tuples in tables:
                if live_tuples > 0:
                    change_ratio = (inserts + updates + deletes) / live_tuples
                    stability = "stable" if change_ratio < 0.1 else "dynamic"
                    print(f"   • {table}: {live_tuples} rows ({stability})")
                    
        except Exception as e:
            print(f"   ⚠️  Table access analysis error: {e}")
    
    def identify_materialized_view_candidates(self):
        """Identify and prioritize materialized view candidates"""
        print("\n🎯 Identifying Materialized View Candidates")
        print("=" * 45)
        
        if 'dropdown_candidates' not in self.analysis_results:
            print("⚠️  Model analysis not completed, running now...")
            self.analyze_model_relationships()
        
        candidates = self.analysis_results['dropdown_candidates']
        
        # Prioritize candidates
        priority_candidates = []
        
        for candidate in candidates:
            model = candidate['model']
            priority_score = candidate['score']
            
            # Additional scoring based on typical dropdown usage
            if any(word in model.__name__.lower() for word in ['people', 'user', 'person']):
                priority_score += 5
            if any(word in model.__name__.lower() for word in ['asset', 'equipment']):
                priority_score += 4
            if any(word in model.__name__.lower() for word in ['location', 'site']):
                priority_score += 4
            if any(word in model.__name__.lower() for word in ['type', 'category', 'priority']):
                priority_score += 3
            
            candidate['priority_score'] = priority_score
            priority_candidates.append(candidate)
        
        # Sort by priority
        priority_candidates.sort(key=lambda x: x['priority_score'], reverse=True)
        
        print("📋 Top materialized view candidates:")
        for i, candidate in enumerate(priority_candidates[:10], 1):
            print(f"   {i}. {candidate['app']}.{candidate['name']} "
                  f"(score: {candidate['priority_score']}, {candidate['reason']})")
        
        self.analysis_results['priority_candidates'] = priority_candidates[:10]
        return priority_candidates[:10]
    
    def estimate_performance_benefits(self):
        """Estimate performance benefits of materialized views"""
        print("\n⚡ Estimating Performance Benefits")
        print("=" * 35)
        
        if 'priority_candidates' not in self.analysis_results:
            print("⚠️  Priority candidates not identified, running analysis...")
            self.identify_materialized_view_candidates()
        
        candidates = self.analysis_results['priority_candidates']
        
        for candidate in candidates[:5]:  # Top 5 candidates
            model = candidate['model']
            
            try:
                # Simulate typical dropdown query
                start_time = time.time()
                
                # Basic query simulation
                if hasattr(model.objects, 'filter'):
                    if 'enable' in [f.name for f in model._meta.fields]:
                        queryset = model.objects.filter(enable=True)[:50]
                    else:
                        queryset = model.objects.all()[:50]
                    
                    # Force evaluation
                    list(queryset)
                    
                query_time = (time.time() - start_time) * 1000
                
                # Estimate materialized view performance (typically 10-20x faster)
                estimated_mv_time = query_time / 15
                
                print(f"🔸 {model.__name__}:")
                print(f"   Current query time: {query_time:.2f}ms")
                print(f"   Estimated MV time: {estimated_mv_time:.2f}ms")
                print(f"   Expected improvement: {(query_time/estimated_mv_time):.1f}x faster")
                
            except Exception as e:
                print(f"   ⚠️  Performance estimation error for {model.__name__}: {e}")
    
    def generate_recommendations(self):
        """Generate recommendations for Phase 2A implementation"""
        print("\n📝 Phase 2A Implementation Recommendations")
        print("=" * 48)
        
        recommendations = {
            'immediate_candidates': [],
            'secondary_candidates': [],
            'implementation_strategy': [],
            'performance_targets': {}
        }
        
        if 'priority_candidates' in self.analysis_results:
            candidates = self.analysis_results['priority_candidates']
            
            # Immediate candidates (top 3)
            recommendations['immediate_candidates'] = candidates[:3]
            
            # Secondary candidates (next 5)
            recommendations['secondary_candidates'] = candidates[3:8]
            
            print("🎯 Immediate Implementation (Top 3):")
            for i, candidate in enumerate(recommendations['immediate_candidates'], 1):
                print(f"   {i}. {candidate['app']}.{candidate['name']}")
                print(f"      Priority Score: {candidate['priority_score']}")
                print(f"      Records: {candidate['indicators']['record_count']}")
                print(f"      Reason: {candidate['reason']}")
                print()
            
            print("🔄 Secondary Implementation (Next 5):")
            for i, candidate in enumerate(recommendations['secondary_candidates'], 1):
                print(f"   {i}. {candidate['app']}.{candidate['name']} "
                      f"(score: {candidate['priority_score']})")
        
        # Implementation strategy
        strategy = [
            "1. Start with top 3 candidates for immediate impact",
            "2. Create materialized views with automatic refresh triggers", 
            "3. Integrate with existing Select2 cache backend",
            "4. Implement fallback to dynamic queries for edge cases",
            "5. Monitor performance improvements and expand to secondary candidates"
        ]
        
        recommendations['implementation_strategy'] = strategy
        
        print("\n🛠️  Implementation Strategy:")
        for step in strategy:
            print(f"   {step}")
        
        # Performance targets
        targets = {
            'static_dropdown_access': '< 0.5ms',
            'cache_hit_improvement': '> 95%',
            'database_load_reduction': '30-50%',
            'overall_response_improvement': '15-25%'
        }
        
        recommendations['performance_targets'] = targets
        
        print("\n📊 Performance Targets:")
        for metric, target in targets.items():
            print(f"   • {metric.replace('_', ' ').title()}: {target}")
        
        return recommendations
    
    def run_complete_analysis(self):
        """Run complete dropdown analysis for Phase 2A"""
        print("🚀 Phase 2A: Dropdown Analysis for Materialized Views")
        print("=" * 60)
        
        # Run all analysis components
        self.analyze_select2_cache_patterns()
        self.analyze_model_relationships()
        self.analyze_query_patterns()
        self.identify_materialized_view_candidates()
        self.estimate_performance_benefits()
        recommendations = self.generate_recommendations()
        
        print(f"\n✅ Phase 2A Analysis Complete!")
        print("📋 Summary:")
        print(f"   • {len(self.analysis_results.get('dropdown_candidates', []))} dropdown candidates identified")
        print(f"   • {len(recommendations['immediate_candidates'])} immediate implementation targets")
        print(f"   • {len(recommendations['secondary_candidates'])} secondary targets")
        print("   • Performance improvement strategy defined")
        print("\n🚀 Ready to proceed with materialized view implementation!")
        
        return recommendations

def main():
    """Main execution function"""
    analyzer = DropdownAnalyzer()
    recommendations = analyzer.run_complete_analysis()
    
    # Save recommendations for next phase
    import json
    with open('postgresql_migration/phase2a_recommendations.json', 'w') as f:
        # Convert model objects to serializable format
        serializable_recs = {
            'immediate_candidates': [
                {
                    'app': c['app'],
                    'name': c['name'],
                    'priority_score': c['priority_score'],
                    'record_count': c['indicators']['record_count'],
                    'reason': c['reason']
                }
                for c in recommendations['immediate_candidates']
            ],
            'secondary_candidates': [
                {
                    'app': c['app'],
                    'name': c['name'],
                    'priority_score': c['priority_score']
                }
                for c in recommendations['secondary_candidates']
            ],
            'implementation_strategy': recommendations['implementation_strategy'],
            'performance_targets': recommendations['performance_targets']
        }
        
        json.dump(serializable_recs, f, indent=2)
    
    print(f"\n💾 Recommendations saved to: postgresql_migration/phase2a_recommendations.json")

if __name__ == "__main__":
    main()