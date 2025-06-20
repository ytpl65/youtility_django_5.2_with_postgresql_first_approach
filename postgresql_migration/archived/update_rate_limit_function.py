#!/usr/bin/env python3
"""
Update rate limiting function to username-first strategy
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

def update_rate_limit_function():
    print("🔄 Updating rate limiting function to username-first strategy...")
    
    with connection.cursor() as cursor:
        # Update the rate limiting function
        cursor.execute("""
            CREATE OR REPLACE FUNCTION check_rate_limit(
                p_ip_address INET,
                p_username VARCHAR(150) DEFAULT NULL,
                p_time_window INTERVAL DEFAULT '15 minutes',
                p_max_attempts INTEGER DEFAULT 5
            ) RETURNS JSON AS $$
            DECLARE
                ip_attempts INTEGER;
                user_attempts INTEGER;
                total_attempts INTEGER;
                result JSON;
                is_blocked BOOLEAN DEFAULT FALSE;
                block_reason TEXT DEFAULT '';
            BEGIN
                -- Count failed attempts by IP in time window
                SELECT COUNT(*) INTO ip_attempts
                FROM auth_rate_limit_attempts
                WHERE ip_address = p_ip_address
                  AND attempt_time > NOW() - p_time_window
                  AND success = FALSE;
                
                -- Count failed attempts by username if provided
                IF p_username IS NOT NULL THEN
                    SELECT COUNT(*) INTO user_attempts
                    FROM auth_rate_limit_attempts
                    WHERE username = p_username
                      AND attempt_time > NOW() - p_time_window
                      AND success = FALSE;
                ELSE
                    user_attempts := 0;
                END IF;
                
                total_attempts := GREATEST(ip_attempts, user_attempts);
                
                -- USERNAME-FIRST blocking strategy
                -- Block primarily by username, IP blocking as secondary protection
                IF p_username IS NOT NULL AND user_attempts >= p_max_attempts THEN
                    is_blocked := TRUE;
                    block_reason := 'Account temporarily locked due to too many failed login attempts';
                ELSIF ip_attempts >= (p_max_attempts * 3) THEN
                    -- IP blocking only after 3x more attempts (15 instead of 5)
                    -- This prevents one user from blocking others at same location
                    is_blocked := TRUE;
                    block_reason := 'IP address temporarily blocked due to excessive failed attempts';
                END IF;
                
                -- Build result JSON
                result := json_build_object(
                    'is_blocked', is_blocked,
                    'ip_attempts', ip_attempts,
                    'user_attempts', user_attempts,
                    'total_attempts', total_attempts,
                    'max_attempts', p_max_attempts,
                    'block_reason', block_reason,
                    'time_window_minutes', EXTRACT(EPOCH FROM p_time_window) / 60,
                    'blocking_strategy', CASE 
                        WHEN is_blocked AND user_attempts >= p_max_attempts THEN 'username'
                        WHEN is_blocked THEN 'ip'
                        ELSE 'none'
                    END
                );
                
                RETURN result;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        print("✅ Updated rate limiting function with username-first strategy")
        
        # Test the new function
        cursor.execute("""
            SELECT check_rate_limit('127.0.0.1'::INET, 'testuser', '15 minutes'::INTERVAL, 5);
        """)
        result = cursor.fetchone()[0]
        print("🧪 Test result:", result)
        
        print("\n🎯 New Blocking Strategy:")
        print("   • PRIMARY: Username-based (5 failed attempts)")
        print("   • SECONDARY: IP-based (15 failed attempts)")
        print("   • This prevents one user from blocking others at same location")

if __name__ == "__main__":
    update_rate_limit_function()