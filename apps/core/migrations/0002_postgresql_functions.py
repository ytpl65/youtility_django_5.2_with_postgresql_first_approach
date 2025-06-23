# Generated for PostgreSQL functions and materialized views

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('auth', '__latest__'),
    ]

    operations = [
        # Create check_rate_limit function
        migrations.RunSQL(
            sql="""
            DROP FUNCTION IF EXISTS check_rate_limit(INET, VARCHAR(150), INTERVAL, INTEGER);
            CREATE OR REPLACE FUNCTION check_rate_limit(
                p_ip_address INET,
                p_username VARCHAR(150),
                p_time_window INTERVAL,
                p_max_attempts INTEGER
            ) RETURNS JSON AS $$
            DECLARE
                ip_attempts INTEGER := 0;
                username_attempts INTEGER := 0;
                last_attempt TIMESTAMP;
                is_blocked BOOLEAN := FALSE;
                block_reason TEXT := '';
                time_since TIMESTAMP;
            BEGIN
                time_since := NOW() - p_time_window;
                
                -- Count failed attempts by IP in time window
                SELECT COUNT(*) INTO ip_attempts
                FROM auth_rate_limit_attempts
                WHERE ip_address = p_ip_address
                AND attempt_time >= time_since
                AND success = FALSE;
                
                -- Count failed attempts by username in time window (if username provided)
                if p_username IS NOT NULL THEN
                    SELECT COUNT(*) INTO username_attempts
                    FROM auth_rate_limit_attempts
                    WHERE username = p_username
                    AND attempt_time >= time_since
                    AND success = FALSE;
                END IF;
                
                -- Get last attempt time
                SELECT MAX(attempt_time) INTO last_attempt
                FROM auth_rate_limit_attempts
                WHERE (ip_address = p_ip_address OR username = p_username)
                AND attempt_time >= time_since;
                
                -- Check if blocked (username-first strategy)
                IF p_username IS NOT NULL AND username_attempts >= p_max_attempts THEN
                    is_blocked := TRUE;
                    block_reason := format('Username %s exceeded %s attempts in %s', 
                                         p_username, p_max_attempts, p_time_window);
                ELSIF ip_attempts >= (p_max_attempts * 3) THEN  -- IP gets 3x more attempts
                    is_blocked := TRUE;
                    block_reason := format('IP %s exceeded %s attempts in %s',
                                         p_ip_address, (p_max_attempts * 3), p_time_window);
                END IF;
                
                -- Return JSON result
                RETURN json_build_object(
                    'is_blocked', is_blocked,
                    'ip_attempts', ip_attempts,
                    'username_attempts', username_attempts,
                    'max_attempts', p_max_attempts,
                    'time_window', p_time_window,
                    'last_attempt', last_attempt,
                    'block_reason', block_reason,
                    'time_until_reset', CASE 
                        WHEN last_attempt IS NOT NULL 
                        THEN last_attempt + p_time_window - NOW()
                        ELSE NULL 
                    END
                );
            END;
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS check_rate_limit(INET, VARCHAR(150), INTERVAL, INTEGER);"
        ),

        # Create cleanup_expired_sessions function
        migrations.RunSQL(
            sql="""
            DROP FUNCTION IF EXISTS cleanup_expired_sessions();
            CREATE OR REPLACE FUNCTION cleanup_expired_sessions() RETURNS JSON AS $$
            DECLARE
                deleted_count INTEGER;
                total_before INTEGER;
                total_after INTEGER;
            BEGIN
                -- Count sessions before cleanup
                SELECT COUNT(*) INTO total_before FROM django_session;
                
                -- Delete expired sessions
                DELETE FROM django_session 
                WHERE expire_date < NOW();
                
                GET DIAGNOSTICS deleted_count = ROW_COUNT;
                
                -- Count sessions after cleanup
                SELECT COUNT(*) INTO total_after FROM django_session;
                
                -- Return cleanup results
                RETURN json_build_object(
                    'deleted_count', deleted_count,
                    'total_before', total_before,
                    'total_after', total_after,
                    'cleanup_time', NOW()
                );
            END;
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS cleanup_expired_sessions();"
        ),

        # Create cleanup_select2_cache function
        migrations.RunSQL(
            sql="""
            DROP FUNCTION IF EXISTS cleanup_select2_cache(INTEGER);
            CREATE OR REPLACE FUNCTION cleanup_select2_cache(p_days_old INTEGER DEFAULT 7) RETURNS JSON AS $$
            DECLARE
                deleted_count INTEGER;
                total_before INTEGER;
                cutoff_time TIMESTAMP;
            BEGIN
                cutoff_time := NOW() - (p_days_old || ' days')::INTERVAL;
                
                -- Count cache entries before cleanup (if table exists)
                SELECT COUNT(*) INTO total_before 
                FROM information_schema.tables 
                WHERE table_name = 'select2_cache';
                
                IF total_before > 0 THEN
                    SELECT COUNT(*) INTO total_before FROM select2_cache;
                    
                    -- Delete old cache entries
                    DELETE FROM select2_cache 
                    WHERE created_at < cutoff_time;
                    
                    GET DIAGNOSTICS deleted_count = ROW_COUNT;
                ELSE
                    total_before := 0;
                    deleted_count := 0;
                END IF;
                
                -- Return cleanup results
                RETURN json_build_object(
                    'deleted_count', deleted_count,
                    'total_before', total_before,
                    'cutoff_time', cutoff_time,
                    'cleanup_time', NOW(),
                    'days_old', p_days_old
                );
            END;
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS cleanup_select2_cache(INTEGER);"
        ),

        # Create materialized views for Select2 dropdowns
        migrations.RunSQL(
            sql="""
            -- Create people dropdown materialized view (if auth_user table exists)
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'auth_user') THEN
                    EXECUTE '
                    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_people_dropdown AS
                    SELECT 
                        id,
                        CONCAT(first_name, '' '', last_name) as display_name,
                        first_name,
                        last_name,
                        email,
                        is_active,
                        date_joined as created_at
                    FROM auth_user
                    WHERE is_active = TRUE
                    ORDER BY first_name, last_name;
                    
                    -- Create index for fast lookups
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_people_dropdown_id ON mv_people_dropdown (id);
                    CREATE INDEX IF NOT EXISTS idx_mv_people_dropdown_name ON mv_people_dropdown (display_name);
                    ';
                END IF;
            END $$;
            """,
            reverse_sql="""
            DROP MATERIALIZED VIEW IF EXISTS mv_people_dropdown CASCADE;
            """
        ),

        migrations.RunSQL(
            sql="""
            -- Create location dropdown materialized view (if locations table exists)
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'locations') THEN
                    EXECUTE '
                    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_location_dropdown AS
                    SELECT 
                        id,
                        name as display_name,
                        description,
                        is_active,
                        created_at
                    FROM locations
                    WHERE is_active = TRUE
                    ORDER BY name;
                    
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_location_dropdown_id ON mv_location_dropdown (id);
                    CREATE INDEX IF NOT EXISTS idx_mv_location_dropdown_name ON mv_location_dropdown (display_name);
                    ';
                END IF;
            END $$;
            """,
            reverse_sql="""
            DROP MATERIALIZED VIEW IF EXISTS mv_location_dropdown CASCADE;
            """
        ),

        migrations.RunSQL(
            sql="""
            -- Create asset dropdown materialized view (if assets table exists)
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'assets') THEN
                    EXECUTE '
                    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_asset_dropdown AS
                    SELECT 
                        id,
                        name as display_name,
                        asset_tag,
                        model,
                        is_active,
                        created_at
                    FROM assets
                    WHERE is_active = TRUE
                    ORDER BY name;
                    
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_asset_dropdown_id ON mv_asset_dropdown (id);
                    CREATE INDEX IF NOT EXISTS idx_mv_asset_dropdown_name ON mv_asset_dropdown (display_name);
                    ';
                END IF;
            END $$;
            """,
            reverse_sql="""
            DROP MATERIALIZED VIEW IF EXISTS mv_asset_dropdown CASCADE;
            """
        ),

        # Create function to refresh materialized views
        migrations.RunSQL(
            sql="""
            DROP FUNCTION IF EXISTS refresh_select2_materialized_views();
            CREATE OR REPLACE FUNCTION refresh_select2_materialized_views() RETURNS JSON AS $$
            DECLARE
                refreshed_views TEXT[] := '{}';
                view_name TEXT;
            BEGIN
                -- Refresh people dropdown view
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'mv_people_dropdown' AND table_type = 'VIEW') THEN
                    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_people_dropdown;
                    refreshed_views := array_append(refreshed_views, 'mv_people_dropdown');
                END IF;
                
                -- Refresh location dropdown view
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'mv_location_dropdown' AND table_type = 'VIEW') THEN
                    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_location_dropdown;
                    refreshed_views := array_append(refreshed_views, 'mv_location_dropdown');
                END IF;
                
                -- Refresh asset dropdown view
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'mv_asset_dropdown' AND table_type = 'VIEW') THEN
                    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_asset_dropdown;
                    refreshed_views := array_append(refreshed_views, 'mv_asset_dropdown');
                END IF;
                
                RETURN json_build_object(
                    'refreshed_views', refreshed_views,
                    'refresh_time', NOW(),
                    'success', TRUE
                );
            END;
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS refresh_select2_materialized_views();"
        ),
    ]