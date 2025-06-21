-- ============================================================================
-- PostgreSQL Task Queue System Schema
-- Phase 2B: Celery/Redis to PostgreSQL Migration
-- ============================================================================

-- Enable UUID extension for unique task IDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. TASK QUEUE TABLES
-- ============================================================================

-- Main task queue table
CREATE TABLE IF NOT EXISTS task_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_name VARCHAR(255) NOT NULL,
    task_module VARCHAR(255) NOT NULL,
    task_args JSONB DEFAULT '[]',
    task_kwargs JSONB DEFAULT '{}',
    
    -- Task scheduling and execution
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'retrying')),
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10), -- 1=highest, 10=lowest
    queue_name VARCHAR(100) DEFAULT 'default',
    
    -- Timing information
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Retry mechanism
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    retry_delay INTEGER DEFAULT 60, -- seconds
    
    -- Worker assignment
    worker_id VARCHAR(100),
    worker_hostname VARCHAR(255),
    worker_pid INTEGER,
    
    -- Result storage
    result JSONB,
    error_message TEXT,
    traceback TEXT,
    
    -- Metadata
    expires_at TIMESTAMP WITH TIME ZONE,
    tenant_id INTEGER, -- For multi-tenant isolation
    
    -- Audit fields
    created_by VARCHAR(100),
    tags JSONB DEFAULT '[]'
);

-- Task execution history (for audit and monitoring)
CREATE TABLE IF NOT EXISTS task_execution_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES task_queue(id) ON DELETE CASCADE,
    
    -- Execution details
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    
    -- Worker information
    worker_id VARCHAR(100),
    worker_hostname VARCHAR(255),
    worker_pid INTEGER,
    
    -- Result and error information
    result JSONB,
    error_message TEXT,
    traceback TEXT,
    
    -- Performance metrics
    memory_usage_mb INTEGER,
    cpu_time_ms INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 2. SCHEDULED TASKS (Celery Beat Replacement)
-- ============================================================================

-- Scheduled task definitions
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    task_name VARCHAR(255) NOT NULL,
    task_module VARCHAR(255) NOT NULL,
    
    -- Scheduling configuration
    schedule_type VARCHAR(20) NOT NULL CHECK (schedule_type IN ('cron', 'interval', 'once')),
    
    -- Cron schedule (for cron type)
    cron_minute VARCHAR(20),
    cron_hour VARCHAR(20),
    cron_day_of_month VARCHAR(20),
    cron_month VARCHAR(20),
    cron_day_of_week VARCHAR(20),
    
    -- Interval schedule (for interval type)
    interval_seconds INTEGER,
    
    -- Task configuration
    task_args JSONB DEFAULT '[]',
    task_kwargs JSONB DEFAULT '{}',
    queue_name VARCHAR(100) DEFAULT 'default',
    priority INTEGER DEFAULT 5,
    
    -- Control flags
    enabled BOOLEAN DEFAULT TRUE,
    one_off BOOLEAN DEFAULT FALSE, -- For 'once' type tasks
    
    -- Timing
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    description TEXT,
    
    -- Tenant isolation
    tenant_id INTEGER
);

-- Scheduled task execution log
CREATE TABLE IF NOT EXISTS scheduled_task_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scheduled_task_id INTEGER NOT NULL REFERENCES scheduled_tasks(id) ON DELETE CASCADE,
    task_id UUID REFERENCES task_queue(id) ON DELETE SET NULL,
    
    -- Execution information
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    duration_ms INTEGER,
    
    -- Result information
    result JSONB,
    error_message TEXT,
    
    -- Next run calculation
    next_run_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- 3. WORKER MANAGEMENT
-- ============================================================================

-- Active workers registry
CREATE TABLE IF NOT EXISTS task_workers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id VARCHAR(100) UNIQUE NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    pid INTEGER NOT NULL,
    
    -- Worker configuration
    queues TEXT[] DEFAULT ARRAY['default'],
    max_concurrent_tasks INTEGER DEFAULT 4,
    current_task_count INTEGER DEFAULT 0,
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'idle', 'busy', 'stopping', 'stopped')),
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Performance metrics
    total_tasks_processed INTEGER DEFAULT 0,
    total_processing_time_ms BIGINT DEFAULT 0,
    
    -- Lifecycle
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    stopped_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    worker_version VARCHAR(50),
    python_version VARCHAR(50),
    environment JSONB
);

-- Worker heartbeat log (for monitoring)
CREATE TABLE IF NOT EXISTS worker_heartbeats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id VARCHAR(100) NOT NULL,
    
    -- System metrics
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    cpu_percent DECIMAL(5,2),
    memory_percent DECIMAL(5,2),
    memory_mb INTEGER,
    active_tasks INTEGER,
    
    -- Task queue status
    queue_lengths JSONB, -- {"default": 5, "high_priority": 2}
    
    -- Performance metrics
    tasks_per_minute DECIMAL(8,2),
    avg_task_duration_ms INTEGER
);

-- ============================================================================
-- 4. TASK DEPENDENCIES AND WORKFLOWS
-- ============================================================================

-- Task dependencies (for workflow management)
CREATE TABLE IF NOT EXISTS task_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES task_queue(id) ON DELETE CASCADE,
    depends_on_task_id UUID NOT NULL REFERENCES task_queue(id) ON DELETE CASCADE,
    
    -- Dependency type
    dependency_type VARCHAR(20) DEFAULT 'success' CHECK (dependency_type IN ('success', 'completion', 'failure')),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(task_id, depends_on_task_id)
);

-- Task chains/workflows
CREATE TABLE IF NOT EXISTS task_workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Workflow configuration
    workflow_definition JSONB NOT NULL, -- DAG definition
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'deprecated')),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    version INTEGER DEFAULT 1,
    
    -- Tenant isolation
    tenant_id INTEGER
);

-- ============================================================================
-- 5. PERFORMANCE MONITORING
-- ============================================================================

-- Task performance metrics
CREATE TABLE IF NOT EXISTS task_performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_name VARCHAR(255) NOT NULL,
    
    -- Time period
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Execution metrics
    total_executions INTEGER DEFAULT 0,
    successful_executions INTEGER DEFAULT 0,
    failed_executions INTEGER DEFAULT 0,
    
    -- Timing metrics
    avg_duration_ms INTEGER,
    min_duration_ms INTEGER,
    max_duration_ms INTEGER,
    p95_duration_ms INTEGER,
    p99_duration_ms INTEGER,
    
    -- Throughput metrics
    tasks_per_hour DECIMAL(10,2),
    
    -- Resource usage
    avg_memory_mb INTEGER,
    max_memory_mb INTEGER,
    avg_cpu_percent DECIMAL(5,2),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 6. INDEXES FOR PERFORMANCE
-- ============================================================================

-- Task queue indexes
CREATE INDEX IF NOT EXISTS idx_task_queue_status ON task_queue(status);
CREATE INDEX IF NOT EXISTS idx_task_queue_priority ON task_queue(priority, created_at);
CREATE INDEX IF NOT EXISTS idx_task_queue_scheduled_at ON task_queue(scheduled_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_task_queue_queue_name ON task_queue(queue_name);
CREATE INDEX IF NOT EXISTS idx_task_queue_worker_id ON task_queue(worker_id);
CREATE INDEX IF NOT EXISTS idx_task_queue_tenant_id ON task_queue(tenant_id);
CREATE INDEX IF NOT EXISTS idx_task_queue_task_name ON task_queue(task_name);
CREATE INDEX IF NOT EXISTS idx_task_queue_expires_at ON task_queue(expires_at) WHERE expires_at IS NOT NULL;

-- Composite index for task pickup
CREATE INDEX IF NOT EXISTS idx_task_queue_pickup ON task_queue(status, priority, scheduled_at, queue_name) 
WHERE status = 'pending';

-- Scheduled tasks indexes
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run ON scheduled_tasks(next_run_at) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_name ON scheduled_tasks(name);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_enabled ON scheduled_tasks(enabled);

-- Worker indexes
CREATE INDEX IF NOT EXISTS idx_task_workers_status ON task_workers(status);
CREATE INDEX IF NOT EXISTS idx_task_workers_heartbeat ON task_workers(last_heartbeat);
CREATE INDEX IF NOT EXISTS idx_task_workers_queues ON task_workers USING GIN(queues);

-- History indexes
CREATE INDEX IF NOT EXISTS idx_task_execution_history_task_id ON task_execution_history(task_id);
CREATE INDEX IF NOT EXISTS idx_task_execution_history_created_at ON task_execution_history(created_at);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_task_performance_metrics_name ON task_performance_metrics(task_name);
CREATE INDEX IF NOT EXISTS idx_task_performance_metrics_period ON task_performance_metrics(period_start, period_end);

-- ============================================================================
-- 7. FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update next_run_at for scheduled tasks
CREATE OR REPLACE FUNCTION calculate_next_run_at(
    schedule_type VARCHAR(20),
    cron_minute VARCHAR(20),
    cron_hour VARCHAR(20),
    cron_day_of_month VARCHAR(20),
    cron_month VARCHAR(20),
    cron_day_of_week VARCHAR(20),
    interval_seconds INTEGER,
    current_run_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
) RETURNS TIMESTAMP WITH TIME ZONE AS $$
DECLARE
    next_run TIMESTAMP WITH TIME ZONE;
BEGIN
    IF schedule_type = 'interval' THEN
        next_run := current_run_at + (interval_seconds || ' seconds')::INTERVAL;
    ELSIF schedule_type = 'cron' THEN
        -- For now, simple implementation - can be enhanced with proper cron parsing
        next_run := current_run_at + INTERVAL '1 day';
    ELSIF schedule_type = 'once' THEN
        next_run := NULL; -- One-time tasks don't have next run
    END IF;
    
    RETURN next_run;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update scheduled task next_run_at
CREATE OR REPLACE FUNCTION update_scheduled_task_next_run()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.enabled = TRUE THEN
        NEW.next_run_at := calculate_next_run_at(
            NEW.schedule_type,
            NEW.cron_minute,
            NEW.cron_hour,
            NEW.cron_day_of_month,
            NEW.cron_month,
            NEW.cron_day_of_week,
            NEW.interval_seconds,
            COALESCE(NEW.last_run_at, CURRENT_TIMESTAMP)
        );
    END IF;
    
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_scheduled_task_next_run
    BEFORE UPDATE ON scheduled_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_scheduled_task_next_run();

-- Function to clean up old tasks
CREATE OR REPLACE FUNCTION cleanup_old_tasks(
    retention_days INTEGER DEFAULT 30
) RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete completed tasks older than retention period
    DELETE FROM task_queue 
    WHERE status IN ('completed', 'failed') 
    AND completed_at < CURRENT_TIMESTAMP - (retention_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Delete old execution history
    DELETE FROM task_execution_history 
    WHERE created_at < CURRENT_TIMESTAMP - (retention_days || ' days')::INTERVAL;
    
    -- Delete old worker heartbeats
    DELETE FROM worker_heartbeats 
    WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '7 days';
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get queue statistics
CREATE OR REPLACE FUNCTION get_queue_statistics(
    queue_name_param VARCHAR(100) DEFAULT NULL
) RETURNS TABLE (
    queue_name VARCHAR(100),
    pending_tasks INTEGER,
    processing_tasks INTEGER,
    completed_tasks INTEGER,
    failed_tasks INTEGER,
    avg_processing_time_ms INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tq.queue_name,
        COUNT(*) FILTER (WHERE tq.status = 'pending')::INTEGER AS pending_tasks,
        COUNT(*) FILTER (WHERE tq.status = 'processing')::INTEGER AS processing_tasks,
        COUNT(*) FILTER (WHERE tq.status = 'completed')::INTEGER AS completed_tasks,
        COUNT(*) FILTER (WHERE tq.status = 'failed')::INTEGER AS failed_tasks,
        AVG(EXTRACT(EPOCH FROM (tq.completed_at - tq.started_at)) * 1000)::INTEGER AS avg_processing_time_ms
    FROM task_queue tq
    WHERE (queue_name_param IS NULL OR tq.queue_name = queue_name_param)
    AND tq.created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
    GROUP BY tq.queue_name;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 8. INITIAL DATA SETUP
-- ============================================================================

-- Insert default queue configuration
INSERT INTO scheduled_tasks (
    name, 
    task_name, 
    task_module, 
    schedule_type, 
    interval_seconds, 
    description,
    queue_name,
    priority
) VALUES 
    ('cleanup_old_tasks', 'cleanup_old_tasks', 'postgresql_migration.tasks', 'interval', 86400, 'Daily cleanup of old completed tasks', 'maintenance', 8),
    ('update_performance_metrics', 'update_performance_metrics', 'postgresql_migration.tasks', 'interval', 3600, 'Hourly performance metrics update', 'maintenance', 7)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- 9. VIEWS FOR MONITORING
-- ============================================================================

-- Active tasks view
CREATE OR REPLACE VIEW v_active_tasks AS
SELECT 
    tq.id,
    tq.task_name,
    tq.status,
    tq.priority,
    tq.queue_name,
    tq.created_at,
    tq.scheduled_at,
    tq.started_at,
    tq.worker_id,
    tq.retry_count,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - tq.started_at)) AS processing_seconds
FROM task_queue tq
WHERE tq.status IN ('pending', 'processing', 'retrying')
ORDER BY tq.priority, tq.created_at;

-- Worker status view
CREATE OR REPLACE VIEW v_worker_status AS
SELECT 
    tw.worker_id,
    tw.hostname,
    tw.status,
    tw.current_task_count,
    tw.max_concurrent_tasks,
    tw.last_heartbeat,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - tw.last_heartbeat)) AS seconds_since_heartbeat,
    tw.total_tasks_processed,
    CASE 
        WHEN tw.total_tasks_processed > 0 THEN 
            (tw.total_processing_time_ms::DECIMAL / tw.total_tasks_processed)::INTEGER 
        ELSE 0 
    END AS avg_task_duration_ms
FROM task_workers tw
ORDER BY tw.last_heartbeat DESC;

-- Queue performance view
CREATE OR REPLACE VIEW v_queue_performance AS
SELECT 
    queue_name,
    COUNT(*) AS total_tasks,
    COUNT(*) FILTER (WHERE status = 'pending') AS pending_tasks,
    COUNT(*) FILTER (WHERE status = 'processing') AS processing_tasks,
    COUNT(*) FILTER (WHERE status = 'completed') AS completed_tasks,
    COUNT(*) FILTER (WHERE status = 'failed') AS failed_tasks,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000)::INTEGER AS avg_duration_ms,
    MAX(EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000)::INTEGER AS max_duration_ms
FROM task_queue
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
GROUP BY queue_name
ORDER BY total_tasks DESC;

-- ============================================================================
-- SCHEMA COMPLETE
-- ============================================================================

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_app_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO your_app_user;

-- Performance optimization settings (can be applied at session level)
-- SET work_mem = '256MB';
-- SET maintenance_work_mem = '1GB';
-- SET checkpoint_completion_target = 0.9;
-- SET wal_buffers = '32MB';
-- SET effective_cache_size = '4GB';

COMMENT ON SCHEMA public IS 'PostgreSQL Task Queue System - Celery/Redis Replacement';