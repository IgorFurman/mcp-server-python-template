-- Additional Supabase functions for the awesome-chatgpt-prompts database
-- Run these after the main schema.sql

-- Function to increment view count for prompts
CREATE OR REPLACE FUNCTION increment_views(prompt_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE prompts 
    SET views = views + 1 
    WHERE id = prompt_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to increment like count for prompts
CREATE OR REPLACE FUNCTION increment_likes(prompt_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE prompts 
    SET likes = likes + 1 
    WHERE id = prompt_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to decrement like count for prompts
CREATE OR REPLACE FUNCTION decrement_likes(prompt_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE prompts 
    SET likes = GREATEST(likes - 1, 0)
    WHERE id = prompt_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to increment view count for app prompts
CREATE OR REPLACE FUNCTION increment_app_views(app_prompt_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE app_prompts 
    SET views = views + 1 
    WHERE id = app_prompt_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get trending prompts (based on recent activity)
CREATE OR REPLACE FUNCTION get_trending_prompts(limit_count INTEGER DEFAULT 20)
RETURNS TABLE (
    id UUID,
    act TEXT,
    prompt TEXT,
    category prompt_category,
    type prompt_type,
    for_devs BOOLEAN,
    contributor TEXT,
    techstack TEXT[],
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE,
    views INTEGER,
    likes INTEGER,
    trend_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.act,
        p.prompt,
        p.category,
        p.type,
        p.for_devs,
        p.contributor,
        p.techstack,
        p.tags,
        p.created_at,
        p.views,
        p.likes,
        -- Calculate trend score based on views, likes, and recency
        (
            (p.likes * 2.0) + 
            (p.views * 0.1) + 
            (EXTRACT(EPOCH FROM (NOW() - p.created_at)) / 86400 * -1) -- Favor recent posts
        ) as trend_score
    FROM prompts p
    WHERE p.is_public = true
    AND p.created_at > NOW() - INTERVAL '30 days' -- Only last 30 days
    ORDER BY trend_score DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get prompt statistics
CREATE OR REPLACE FUNCTION get_prompt_stats()
RETURNS TABLE (
    total_prompts BIGINT,
    total_system_prompts BIGINT,
    total_app_prompts BIGINT,
    total_views BIGINT,
    total_likes BIGINT,
    dev_prompts BIGINT,
    general_prompts BIGINT,
    recent_prompts BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*) FROM prompts WHERE is_public = true),
        (SELECT COUNT(*) FROM system_prompts),
        (SELECT COUNT(*) FROM app_prompts),
        (SELECT COALESCE(SUM(views), 0) FROM prompts WHERE is_public = true),
        (SELECT COALESCE(SUM(likes), 0) FROM prompts WHERE is_public = true),
        (SELECT COUNT(*) FROM prompts WHERE is_public = true AND for_devs = true),
        (SELECT COUNT(*) FROM prompts WHERE is_public = true AND for_devs = false),
        (SELECT COUNT(*) FROM prompts WHERE is_public = true AND created_at > NOW() - INTERVAL '7 days');
END;
$$ LANGUAGE plpgsql;

-- Function to get popular tags
CREATE OR REPLACE FUNCTION get_popular_tags(limit_count INTEGER DEFAULT 20)
RETURNS TABLE (
    tag TEXT,
    count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        unnest(tags) as tag,
        COUNT(*) as count
    FROM prompts 
    WHERE is_public = true 
    AND tags IS NOT NULL 
    AND array_length(tags, 1) > 0
    GROUP BY unnest(tags)
    ORDER BY count DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get popular tech stacks
CREATE OR REPLACE FUNCTION get_popular_techstacks(limit_count INTEGER DEFAULT 20)
RETURNS TABLE (
    tech TEXT,
    count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        unnest(techstack) as tech,
        COUNT(*) as count
    FROM app_prompts 
    WHERE techstack IS NOT NULL 
    AND array_length(techstack, 1) > 0
    GROUP BY unnest(techstack)
    ORDER BY count DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get user activity summary
CREATE OR REPLACE FUNCTION get_user_activity(user_id UUID)
RETURNS TABLE (
    total_prompts BIGINT,
    total_views BIGINT,
    total_likes BIGINT,
    total_favorites BIGINT,
    total_collections BIGINT,
    recent_activity TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*) FROM prompts WHERE created_by = user_id),
        (SELECT COALESCE(SUM(views), 0) FROM prompts WHERE created_by = user_id),
        (SELECT COALESCE(SUM(likes), 0) FROM prompts WHERE created_by = user_id),
        (SELECT COUNT(*) FROM user_favorites WHERE user_favorites.user_id = get_user_activity.user_id),
        (SELECT COUNT(*) FROM collections WHERE created_by = user_id),
        (SELECT MAX(updated_at) FROM prompts WHERE created_by = user_id);
END;
$$ LANGUAGE plpgsql;

-- Function to search across all prompt types
CREATE OR REPLACE FUNCTION search_all_prompts(search_query TEXT, limit_count INTEGER DEFAULT 50)
RETURNS TABLE (
    source TEXT,
    id UUID,
    title TEXT,
    content TEXT,
    type TEXT,
    category TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    (
        SELECT 
            'prompts' as source,
            p.id,
            p.act as title,
            p.prompt as content,
            p.type::TEXT,
            p.category::TEXT,
            p.created_at,
            ts_rank(p.search_vector, plainto_tsquery('english', search_query)) as rank
        FROM prompts p
        WHERE p.search_vector @@ plainto_tsquery('english', search_query)
        AND p.is_public = true
    )
    UNION ALL
    (
        SELECT 
            'system_prompts' as source,
            sp.id,
            sp.service_name || COALESCE(' ' || sp.model_name, '') as title,
            sp.system_prompt as content,
            'system' as type,
            'system' as category,
            sp.created_at,
            ts_rank(sp.search_vector, plainto_tsquery('english', search_query)) as rank
        FROM system_prompts sp
        WHERE sp.search_vector @@ plainto_tsquery('english', search_query)
    )
    UNION ALL
    (
        SELECT 
            'app_prompts' as source,
            ap.id,
            ap.app_name as title,
            ap.description as content,
            'app' as type,
            'app' as category,
            ap.created_at,
            ts_rank(ap.search_vector, plainto_tsquery('english', search_query)) as rank
        FROM app_prompts ap
        WHERE ap.search_vector @@ plainto_tsquery('english', search_query)
    )
    ORDER BY rank DESC, created_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get related prompts across all types
CREATE OR REPLACE FUNCTION get_related_content(content_id UUID, content_type TEXT, limit_count INTEGER DEFAULT 10)
RETURNS TABLE (
    source TEXT,
    id UUID,
    title TEXT,
    content TEXT,
    type TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    similarity_score REAL
) AS $$
DECLARE
    source_content TEXT;
    source_tags TEXT[];
BEGIN
    -- Get source content based on type
    IF content_type = 'prompts' THEN
        SELECT prompt, tags INTO source_content, source_tags 
        FROM prompts WHERE prompts.id = content_id;
    ELSIF content_type = 'system_prompts' THEN
        SELECT system_prompt INTO source_content 
        FROM system_prompts WHERE system_prompts.id = content_id;
        source_tags := ARRAY[]::TEXT[];
    ELSIF content_type = 'app_prompts' THEN
        SELECT description, techstack INTO source_content, source_tags 
        FROM app_prompts WHERE app_prompts.id = content_id;
    END IF;

    IF source_content IS NULL THEN
        RETURN;
    END IF;

    RETURN QUERY
    (
        SELECT 
            'prompts' as source,
            p.id,
            p.act as title,
            p.prompt as content,
            p.type::TEXT,
            p.created_at,
            similarity(p.prompt, source_content) as similarity_score
        FROM prompts p
        WHERE p.id != content_id
        AND p.is_public = true
        AND (
            similarity(p.prompt, source_content) > 0.1
            OR (source_tags IS NOT NULL AND p.tags && source_tags)
        )
    )
    UNION ALL
    (
        SELECT 
            'system_prompts' as source,
            sp.id,
            sp.service_name || COALESCE(' ' || sp.model_name, '') as title,
            sp.system_prompt as content,
            'system' as type,
            sp.created_at,
            similarity(sp.system_prompt, source_content) as similarity_score
        FROM system_prompts sp
        WHERE sp.id != content_id
        AND similarity(sp.system_prompt, source_content) > 0.1
    )
    UNION ALL
    (
        SELECT 
            'app_prompts' as source,
            ap.id,
            ap.app_name as title,
            ap.description as content,
            'app' as type,
            ap.created_at,
            similarity(ap.description, source_content) as similarity_score
        FROM app_prompts ap
        WHERE ap.id != content_id
        AND (
            similarity(ap.description, source_content) > 0.1
            OR (source_tags IS NOT NULL AND ap.techstack && source_tags)
        )
    )
    ORDER BY similarity_score DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Enable the pg_trgm extension for similarity searches
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create indexes for similarity searches
CREATE INDEX IF NOT EXISTS idx_prompts_prompt_trgm ON prompts USING gin(prompt gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_system_prompts_content_trgm ON system_prompts USING gin(system_prompt gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_app_prompts_description_trgm ON app_prompts USING gin(description gin_trgm_ops);