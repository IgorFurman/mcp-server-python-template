-- Schema Optimizations for Awesome ChatGPT Prompts
-- Apply these optimizations to improve performance and functionality

-- ========================================
-- ENHANCED INDEXING STRATEGY
-- ========================================

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_prompts_category_type_created
ON prompts(category, type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_prompts_public_views
ON prompts(is_public, views DESC) WHERE is_public = true;

CREATE INDEX IF NOT EXISTS idx_user_favorites_user_created
ON user_favorites(user_id, created_at DESC);

-- Additional GIN indexes for array and JSONB columns
CREATE INDEX IF NOT EXISTS idx_prompts_techstack_gin
ON prompts USING gin(techstack);

CREATE INDEX IF NOT EXISTS idx_system_prompts_metadata
ON system_prompts USING gin(metadata);

-- Performance index for search ranking
CREATE INDEX IF NOT EXISTS idx_prompts_search_rank
ON prompts USING gin(search_vector);

-- ========================================
-- ENHANCED SEARCH FUNCTION
-- ========================================

CREATE OR REPLACE FUNCTION enhanced_search_prompts(
    search_query TEXT,
    category_filter prompt_category DEFAULT NULL,
    type_filter prompt_type DEFAULT NULL,
    limit_count INTEGER DEFAULT 20,
    offset_count INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    act TEXT,
    prompt_snippet TEXT,
    category prompt_category,
    type prompt_type,
    techstack TEXT[],
    tags TEXT[],
    views INTEGER,
    likes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    rank REAL,
    snippet TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.act,
        LEFT(p.prompt, 200) as prompt_snippet,
        p.category,
        p.type,
        p.techstack,
        p.tags,
        p.views,
        p.likes,
        p.created_at,
        ts_rank_cd(p.search_vector, plainto_tsquery('english', search_query)) as rank,
        ts_headline('english', p.prompt, plainto_tsquery('english', search_query),
                   'MaxWords=20, MinWords=15') as snippet
    FROM prompts p
    WHERE p.search_vector @@ plainto_tsquery('english', search_query)
    AND p.is_public = true
    AND (category_filter IS NULL OR p.category = category_filter)
    AND (type_filter IS NULL OR p.type = type_filter)
    ORDER BY rank DESC, p.views DESC, p.created_at DESC
    LIMIT limit_count OFFSET offset_count;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- TRENDING PROMPTS FUNCTION
-- ========================================

CREATE OR REPLACE FUNCTION get_trending_prompts(
    days_back INTEGER DEFAULT 7,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    act TEXT,
    category prompt_category,
    views INTEGER,
    likes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    trend_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.act,
        p.category,
        p.views,
        p.likes,
        p.created_at,
        -- Calculate trend score based on views, likes, and recency
        (p.views * 1.0 + p.likes * 2.0) /
        GREATEST(1, EXTRACT(EPOCH FROM (NOW() - p.created_at)) / 86400) as trend_score
    FROM prompts p
    WHERE p.is_public = true
    AND p.created_at > NOW() - INTERVAL '1 day' * days_back
    ORDER BY trend_score DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- ANALYTICS VIEWS
-- ========================================

-- Popular prompts by category
CREATE OR REPLACE VIEW popular_prompts_by_category AS
SELECT
    category,
    COUNT(*) as total_prompts,
    AVG(views) as avg_views,
    MAX(views) as max_views,
    SUM(likes) as total_likes,
    COUNT(CASE WHEN created_at > NOW() - INTERVAL '7 days' THEN 1 END) as new_this_week,
    COUNT(CASE WHEN created_at > NOW() - INTERVAL '30 days' THEN 1 END) as new_this_month
FROM prompts
WHERE is_public = true
GROUP BY category
ORDER BY avg_views DESC;

-- User engagement statistics
CREATE OR REPLACE VIEW user_engagement_stats AS
SELECT
    u.id as user_id,
    u.email,
    COUNT(DISTINCT f.prompt_id) as favorites_count,
    COUNT(DISTINCT c.id) as collections_count,
    COUNT(DISTINCT p.id) as prompts_created,
    SUM(p.views) as total_prompt_views,
    SUM(p.likes) as total_prompt_likes,
    MAX(p.created_at) as last_prompt_created
FROM auth.users u
LEFT JOIN user_favorites f ON u.id = f.user_id
LEFT JOIN collections c ON u.id = c.created_by AND c.is_public = true
LEFT JOIN prompts p ON u.id = p.created_by AND p.is_public = true
GROUP BY u.id, u.email
HAVING COUNT(DISTINCT p.id) > 0 OR COUNT(DISTINCT f.prompt_id) > 0;

-- System prompts statistics
CREATE OR REPLACE VIEW system_prompts_stats AS
SELECT
    service_name,
    COUNT(*) as total_prompts,
    COUNT(DISTINCT model_name) as model_count,
    MIN(version_date) as earliest_version,
    MAX(version_date) as latest_version,
    COUNT(CASE WHEN is_verified = true THEN 1 END) as verified_count
FROM system_prompts
GROUP BY service_name
ORDER BY total_prompts DESC;

-- ========================================
-- ENHANCED SECURITY POLICIES
-- ========================================

-- Drop existing policies to recreate with optimizations
DROP POLICY IF EXISTS "Public prompts are viewable by everyone" ON prompts;
DROP POLICY IF EXISTS "Users can insert prompts" ON prompts;
DROP POLICY IF EXISTS "Users can update their own prompts" ON prompts;
DROP POLICY IF EXISTS "Users can delete their own prompts" ON prompts;

-- Recreate optimized policies
CREATE POLICY "Optimized public prompts access" ON prompts
    FOR SELECT
    USING (is_public = true);

CREATE POLICY "Authenticated users can insert prompts" ON prompts
    FOR INSERT
    WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Users can update their own prompts" ON prompts
    FOR UPDATE
    USING (auth.uid() = created_by)
    WITH CHECK (auth.uid() = created_by);

CREATE POLICY "Users can delete their own prompts" ON prompts
    FOR DELETE
    USING (auth.uid() = created_by);

-- Enhanced collection policies
DROP POLICY IF EXISTS "Public collections are viewable by everyone" ON collections;
DROP POLICY IF EXISTS "Users can create collections" ON collections;
DROP POLICY IF EXISTS "Users can update their own collections" ON collections;
DROP POLICY IF EXISTS "Users can delete their own collections" ON collections;

CREATE POLICY "Optimized collections access" ON collections
    FOR SELECT
    USING (is_public = true OR auth.uid() = created_by);

CREATE POLICY "Authenticated users can create collections" ON collections
    FOR INSERT
    WITH CHECK (auth.role() = 'authenticated' AND auth.uid() = created_by);

CREATE POLICY "Users can update their own collections" ON collections
    FOR UPDATE
    USING (auth.uid() = created_by)
    WITH CHECK (auth.uid() = created_by);

CREATE POLICY "Users can delete their own collections" ON collections
    FOR DELETE
    USING (auth.uid() = created_by);

-- ========================================
-- PERFORMANCE MONITORING
-- ========================================

-- Function to analyze query performance
CREATE OR REPLACE FUNCTION analyze_search_performance()
RETURNS TABLE (
    query_type TEXT,
    avg_execution_time NUMERIC,
    total_calls BIGINT
) AS $$
BEGIN
    -- This would typically connect to pg_stat_statements
    -- For now, return a placeholder structure
    RETURN QUERY
    SELECT
        'enhanced_search_prompts'::TEXT as query_type,
        0.0::NUMERIC as avg_execution_time,
        0::BIGINT as total_calls;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- MAINTENANCE FUNCTIONS
-- ========================================

-- Function to update search vectors (if needed)
CREATE OR REPLACE FUNCTION refresh_search_vectors()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    -- Update search vectors for prompts that might need it
    UPDATE prompts
    SET updated_at = NOW()
    WHERE search_vector IS NULL;

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old analytics data
CREATE OR REPLACE FUNCTION cleanup_old_data(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
BEGIN
    -- This is a placeholder for future analytics cleanup
    -- Add specific cleanup logic based on your analytics tables
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
