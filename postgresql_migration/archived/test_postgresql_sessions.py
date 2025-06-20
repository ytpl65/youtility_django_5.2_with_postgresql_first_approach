#!/usr/bin/env python3
"""
PostgreSQL-Only Session Testing
Compare performance between Redis+PostgreSQL vs PostgreSQL-only sessions
"""

import os
import sys
import django
import time
from datetime import datetime

# Add the project root to Python path
sys.path.append('/home/satyam/Documents/YOUTILITY-MIGRATION-DJANGO5-POSTGRESQL/YOUTILITY3')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore as DBSessionStore
from django.contrib.sessions.backends.cached_db import SessionStore as CachedDBSessionStore

class SessionPerformanceComparator:
    def __init__(self):
        self.results = {}
        
    def print_header(self, title):
        print(f"\n{'='*60}")
        print(f"⚡ {title}")
        print(f"{'='*60}")
    
    def test_session_store_performance(self, store_class, store_name, num_tests=100):
        """Test performance of a specific session store"""
        print(f"🧪 Testing {store_name} with {num_tests} operations...")
        
        # Measure session creation
        start_time = time.time()
        session_keys = []
        
        for i in range(num_tests):
            session = store_class()
            session['test_data'] = f'test_value_{i}'
            session['user_id'] = i
            session['timestamp'] = str(datetime.now())
            session['complex_data'] = {
                'nested': {'data': [1, 2, 3, 4, 5]},
                'user_preferences': {'theme': 'dark', 'language': 'en'},
                'permissions': ['read', 'write', 'admin']
            }
            session.save()
            session_keys.append(session.session_key)
            
        creation_time = time.time() - start_time
        
        # Measure session retrieval
        start_time = time.time()
        
        for key in session_keys:
            session = store_class(key)
            _ = session.get('test_data')
            _ = session.get('complex_data')
            
        retrieval_time = time.time() - start_time
        
        # Measure session update
        start_time = time.time()
        
        for key in session_keys:
            session = store_class(key)
            session['updated_at'] = str(datetime.now())
            session.save()
            
        update_time = time.time() - start_time
        
        # Measure session deletion
        start_time = time.time()
        
        for key in session_keys:
            session = store_class(key)
            session.delete()
            
        deletion_time = time.time() - start_time
        
        # Store results
        self.results[store_name] = {
            'creation_time': creation_time,
            'retrieval_time': retrieval_time,
            'update_time': update_time,
            'deletion_time': deletion_time,
            'total_time': creation_time + retrieval_time + update_time + deletion_time,
            'avg_creation': creation_time / num_tests * 1000,  # ms
            'avg_retrieval': retrieval_time / num_tests * 1000,  # ms
            'avg_update': update_time / num_tests * 1000,  # ms
            'avg_deletion': deletion_time / num_tests * 1000,  # ms
        }
        
        print(f"📊 Performance Results for {store_name}:")
        print(f"   Creation:  {creation_time:.3f}s total, {creation_time/num_tests*1000:.2f}ms avg")
        print(f"   Retrieval: {retrieval_time:.3f}s total, {retrieval_time/num_tests*1000:.2f}ms avg")
        print(f"   Update:    {update_time:.3f}s total, {update_time/num_tests*1000:.2f}ms avg")
        print(f"   Deletion:  {deletion_time:.3f}s total, {deletion_time/num_tests*1000:.2f}ms avg")
        print(f"   📈 Total:  {creation_time + retrieval_time + update_time + deletion_time:.3f}s")
        
        return self.results[store_name]
    
    def compare_performance(self):
        """Compare performance between different session stores"""
        self.print_header("SESSION STORE PERFORMANCE COMPARISON")
        
        num_tests = 50  # Smaller number for faster testing
        
        # Test current Redis+DB sessions
        current_results = self.test_session_store_performance(
            CachedDBSessionStore, 
            "Current (Redis + PostgreSQL)", 
            num_tests
        )
        
        # Test PostgreSQL-only sessions  
        postgres_results = self.test_session_store_performance(
            DBSessionStore, 
            "PostgreSQL-Only", 
            num_tests
        )
        
        # Calculate performance differences
        self.print_header("PERFORMANCE COMPARISON ANALYSIS")
        
        operations = ['creation', 'retrieval', 'update', 'deletion']
        
        print("📊 Performance Comparison (lower is better):")
        print(f"{'Operation':<12} {'Current':<15} {'PostgreSQL':<15} {'Difference':<15} {'Winner'}")
        print("-" * 70)
        
        for op in operations:
            current_avg = current_results[f'avg_{op}']
            postgres_avg = postgres_results[f'avg_{op}']
            diff = postgres_avg - current_avg
            percentage = (diff / current_avg) * 100 if current_avg > 0 else 0
            
            winner = "PostgreSQL" if diff < 0 else "Current" if diff > 0 else "Tie"
            winner_emoji = "🐘" if winner == "PostgreSQL" else "🔴" if winner == "Current" else "🤝"
            
            print(f"{op.capitalize():<12} {current_avg:>6.2f}ms      {postgres_avg:>6.2f}ms      "
                  f"{diff:>+6.2f}ms      {winner_emoji} {winner}")
        
        # Overall comparison
        current_total = current_results['total_time']
        postgres_total = postgres_results['total_time']  
        total_diff = postgres_total - current_total
        total_percentage = (total_diff / current_total) * 100
        
        print("-" * 70)
        print(f"{'TOTAL':<12} {current_total*1000:>6.0f}ms      {postgres_total*1000:>6.0f}ms      "
              f"{total_diff*1000:>+6.0f}ms      {'🐘' if total_diff < 0 else '🔴'} "
              f"({'PostgreSQL' if total_diff < 0 else 'Current'}) by {abs(total_percentage):.1f}%")
        
        return {
            'current': current_results,
            'postgresql': postgres_results,
            'total_difference_ms': total_diff * 1000,
            'total_percentage': total_percentage
        }
    
    def explain_results(self, comparison_results):
        """Explain what the performance results mean"""
        self.print_header("PERFORMANCE ANALYSIS & RECOMMENDATIONS")
        
        total_diff_ms = comparison_results['total_difference_ms']
        total_percentage = comparison_results['total_percentage']
        
        print("🔍 Key Insights:")
        
        if abs(total_percentage) < 5:
            print("   ✅ Performance difference is NEGLIGIBLE (<5%)")
            print("   🎯 PostgreSQL-first approach is VIABLE with minimal performance impact")
        elif total_percentage < -10:
            print("   🚀 PostgreSQL-only is SIGNIFICANTLY FASTER")
            print("   🎯 Strong case for migration - better performance + reduced complexity")
        elif total_percentage > 10:
            print("   ⚠️  Redis+DB approach is notably faster")
            print("   🎯 Consider keeping hybrid approach or optimizing PostgreSQL further")
        
        print(f"\n💡 Performance Trade-offs:")
        print(f"   Current (Redis+DB): Complex but optimized for read-heavy workloads")
        print(f"   PostgreSQL-Only:   Simple, consistent, easier to maintain and debug")
        
        print(f"\n🎯 Recommendation:")
        if abs(total_percentage) < 10:
            print("   ✅ MIGRATE to PostgreSQL-only sessions")
            print("   📉 Reduce operational complexity with minimal performance impact")
            print("   🔧 Benefits: Simpler architecture, better consistency, easier debugging")
        else:
            print("   ⚖️  EVALUATE trade-offs based on your priorities")
            print("   🏗️  Consider: Operational simplicity vs Peak performance")
            
        print(f"\n🛠️ Next Steps for Migration:")
        print("   1. Update SESSION_ENGINE to 'django.contrib.sessions.backends.db'")
        print("   2. Add session cleanup job (DELETE expired sessions)")
        print("   3. Monitor performance in staging environment")
        print("   4. Gradual rollout with performance monitoring")

def main():
    print("🚀 Starting PostgreSQL Session Performance Comparison")
    print(f"⏰ Test started at: {datetime.now()}")
    
    comparator = SessionPerformanceComparator()
    
    try:
        # Run comprehensive performance comparison
        comparison_results = comparator.compare_performance()
        
        # Explain the results and provide recommendations
        comparator.explain_results(comparison_results)
        
        print(f"\n✅ Performance comparison completed at: {datetime.now()}")
        
    except Exception as e:
        print(f"\n❌ Performance comparison failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()