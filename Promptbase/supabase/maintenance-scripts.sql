-- Database Maintenance and Monitoring Scripts
-- Run these periodically to maintain optimal performance

-- ========================================
-- PERFORMANCE MONITORING QUERIES
-- ========================================

-- Check index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan,
    CASE
        WHEN idx_scan = 0 THEN 'UNUSED'
        WHEN idx_tup_read / GREATEST(idx_scan, 1) > 1000 THEN 'HIGH_RATIO'
        ELSE 'NORMAL'
    END as status
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Check table sizes and bloat
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check slow queries (requires pg_stat_statements extension)
-- SELECT
--     query,
--     calls,
--     total_time,
--     mean_time,
--     rows
-- FROM pg_stat_statements
-- WHERE query LIKE '%prompts%'
-- ORDER BY total_time DESC
-- LIMIT 10;

-- ========================================
-- DATABASE MAINTENANCE FUNCTIONS
-- ========================================

-- Function to analyze and vacuum tables
CREATE OR REPLACE FUNCTION maintenance_vacuum_analyze()
RETURNS TEXT AS $$
DECLARE
    table_name TEXT;
    result TEXT := '';
BEGIN
    FOR table_name IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE 'VACUUM ANALYZE ' || table_name;
        result := result || 'Vacuumed and analyzed ' || table_name || E'\n';
    END LOOP;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to update table statistics
CREATE OR REPLACE FUNCTION update_table_statistics()
RETURNS TEXT AS $$
DECLARE
    table_name TEXT;
    result TEXT := '';
BEGIN
    FOR table_name IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE 'ANALYZE ' || table_name;
        result := result || 'Analyzed ' || table_name || E'\n';
    END LOOP;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- DATA QUALITY CHECKS
-- ========================================

-- Check for data integrity issues
CREATE OR REPLACE FUNCTION data_quality_report()
RETURNS TABLE (
    check_name TEXT,
    status TEXT,
    count BIGINT,
    description TEXT
) AS $$
BEGIN
    -- Check for prompts without search vectors
    RETURN QUERY
    SELECT
        'Missing Search Vectors'::TEXT,
        CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'WARNING' END::TEXT,
        COUNT(*),
        'Prompts without search vectors'::TEXT
    FROM prompts WHERE search_vector IS NULL;

    -- Check for orphaned favorites
    RETURN QUERY
    SELECT
        'Orphaned Favorites'::TEXT,
        CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'ERROR' END::TEXT,
        COUNT(*),
        'Favorites pointing to non-existent prompts'::TEXT
    FROM user_favorites f
    LEFT JOIN prompts p ON f.prompt_id = p.id
    WHERE p.id IS NULL;

    -- Check for empty collections
    RETURN QUERY
    SELECT
        'Empty Collections'::TEXT,
        CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'INFO' END::TEXT,
        COUNT(*),
        'Collections with no items'::TEXT
    FROM collections c
    LEFT JOIN collection_items ci ON c.id = ci.collection_id
    WHERE ci.collection_id IS NULL;

    -- Check for prompts with very long content
    RETURN QUERY
    SELECT
        'Long Prompts'::TEXT,
        'INFO'::TEXT,
        COUNT(*),
        'Prompts longer than 2000 characters'::TEXT
    FROM prompts
    WHERE LENGTH(prompt) > 2000;

    -- Check for duplicate prompts (same act and content)
    RETURN QUERY
    SELECT
        'Potential Duplicates'::TEXT,
        CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'WARNING' END::TEXT,
        COUNT(*),
        'Groups of prompts with same act and content'::TEXT
    FROM (
        SELECT act, prompt, COUNT(*) as cnt
        FROM prompts
        GROUP BY act, prompt
        HAVING COUNT(*) > 1
    ) duplicates;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- PERFORMANCE OPTIMIZATION QUERIES
-- ========================================

-- Find unused indexes
CREATE OR REPLACE FUNCTION find_unused_indexes()
RETURNS TABLE (
    schema_name TEXT,
    table_name TEXT,
    index_name TEXT,
    index_size TEXT,
    scans BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        schemaname::TEXT,
        tablename::TEXT,
        indexname::TEXT,
        pg_size_pretty(pg_relation_size(indexrelid))::TEXT,
        idx_scan
    FROM pg_stat_user_indexes
    WHERE idx_scan = 0
    AND schemaname = 'public'
    ORDER BY pg_relation_size(indexrelid) DESC;
END;
$$ LANGUAGE plpgsql;

-- Find missing indexes (tables with high sequential scans)
CREATE OR REPLACE FUNCTION find_missing_indexes()
RETURNS TABLE (
    schema_name TEXT,
    table_name TEXT,
    seq_scans BIGINT,
    seq_tup_read BIGINT,
    ratio NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        schemaname::TEXT,
        tablename::TEXT,
        seq_scan,
        seq_tup_read,
        CASE WHEN seq_scan = 0 THEN 0
             ELSE seq_tup_read::NUMERIC / seq_scan::NUMERIC
        END as ratio
    FROM pg_stat_user_tables
    WHERE schemaname = 'public'
    AND seq_scan > 0
    ORDER BY seq_tup_read DESC;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- BACKUP AND RESTORE HELPERS
-- ========================================

-- Function to export data for backup
CREATE OR REPLACE FUNCTION export_data_summary()
RETURNS TABLE (
    table_name TEXT,
    row_count BIGINT,
    size TEXT,
    last_modified TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.tablename::TEXT,
        (SELECT COUNT(*) FROM prompts WHERE t.tablename = 'prompts')::BIGINT,
        pg_size_pretty(pg_total_relation_size('public.' || t.tablename))::TEXT,
        NOW()::TIMESTAMP WITH TIME ZONE
    FROM pg_tables t
    WHERE t.schemaname = 'public'
    AND t.tablename IN ('prompts', 'system_prompts', 'app_prompts', 'collections', 'user_favorites');
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- SECURITY AUDIT FUNCTIONS
-- ========================================

-- Check RLS policies
CREATE OR REPLACE FUNCTION audit_rls_policies()
RETURNS TABLE (
    table_name TEXT,
    rls_enabled BOOLEAN,
    policy_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.tablename::TEXT,
        t.rowsecurity,
        COUNT(p.policyname)
    FROM pg_tables t
    LEFT JOIN pg_policies p ON t.tablename = p.tablename
    WHERE t.schemaname = 'public'
    GROUP BY t.tablename, t.rowsecurity
    ORDER BY t.tablename;
END;
$$ LANGUAGE plpgsql;

-- Check for potential security issues
CREATE OR REPLACE FUNCTION security_audit()
RETURNS TABLE (
    check_name TEXT,
    status TEXT,
    description TEXT
) AS $$
BEGIN
    -- Check for public prompts without RLS
    RETURN QUERY
    SELECT
        'Public Data Access'::TEXT,
        'INFO'::TEXT,
        'Total public prompts: ' || COUNT(*)::TEXT
    FROM prompts WHERE is_public = true;

    -- Check for users with many prompts (potential spam)
    RETURN QUERY
    SELECT
        'High Volume Users'::TEXT,
        CASE WHEN COUNT(*) > 0 THEN 'WARNING' ELSE 'OK' END::TEXT,
        'Users with more than 100 prompts: ' || COUNT(*)::TEXT
    FROM (
        SELECT created_by, COUNT(*) as prompt_count
        FROM prompts
        WHERE created_by IS NOT NULL
        GROUP BY created_by
        HAVING COUNT(*) > 100
    ) high_volume;

END;
$$ LANGUAGE plpgsql;
