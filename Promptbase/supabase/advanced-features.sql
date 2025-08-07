-- Advanced Features for Awesome ChatGPT Prompts
-- Optional enhancements to add after core optimizations

-- ========================================
-- PROMPT VERSIONING SYSTEM
-- ========================================

CREATE TABLE IF NOT EXISTS prompt_versions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    prompt_id UUID REFERENCES prompts(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    act TEXT NOT NULL,
    prompt TEXT NOT NULL,
    change_description TEXT,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(prompt_id, version_number)
);

-- Index for version queries
CREATE INDEX idx_prompt_versions_prompt_id ON prompt_versions(prompt_id, version_number DESC);

-- Function to create a new version
CREATE OR REPLACE FUNCTION create_prompt_version(
    p_prompt_id UUID,
    p_act TEXT,
    p_prompt TEXT,
    p_change_description TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    new_version_number INTEGER;
    new_version_id UUID;
BEGIN
    -- Get the next version number
    SELECT COALESCE(MAX(version_number), 0) + 1
    INTO new_version_number
    FROM prompt_versions
    WHERE prompt_id = p_prompt_id;

    -- Insert new version
    INSERT INTO prompt_versions (prompt_id, version_number, act, prompt, change_description, created_by)
    VALUES (p_prompt_id, new_version_number, p_act, p_prompt, p_change_description, auth.uid())
    RETURNING id INTO new_version_id;

    -- Update the main prompt
    UPDATE prompts
    SET act = p_act, prompt = p_prompt, updated_at = NOW()
    WHERE id = p_prompt_id AND created_by = auth.uid();

    RETURN new_version_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ========================================
-- USAGE ANALYTICS SYSTEM
-- ========================================

CREATE TABLE IF NOT EXISTS prompt_analytics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    prompt_id UUID REFERENCES prompts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    action_type TEXT NOT NULL CHECK (action_type IN ('view', 'copy', 'share', 'favorite', 'unfavorite')),
    ip_address INET,
    user_agent TEXT,
    referrer TEXT,
    session_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Partitioning for analytics (monthly partitions)
-- Note: This would need to be set up with proper partitioning in production

-- Indexes for analytics
CREATE INDEX idx_analytics_prompt_id_created ON prompt_analytics(prompt_id, created_at DESC);
CREATE INDEX idx_analytics_user_id_created ON prompt_analytics(user_id, created_at DESC);
CREATE INDEX idx_analytics_action_type_created ON prompt_analytics(action_type, created_at DESC);

-- Function to track analytics events
CREATE OR REPLACE FUNCTION track_prompt_analytics(
    p_prompt_id UUID,
    p_action_type TEXT,
    p_ip_address TEXT DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL,
    p_referrer TEXT DEFAULT NULL,
    p_session_id TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    analytics_id UUID;
BEGIN
    INSERT INTO prompt_analytics (
        prompt_id, user_id, action_type, ip_address,
        user_agent, referrer, session_id
    )
    VALUES (
        p_prompt_id, auth.uid(), p_action_type, p_ip_address::INET,
        p_user_agent, p_referrer, p_session_id
    )
    RETURNING id INTO analytics_id;

    -- Update view count if it's a view action
    IF p_action_type = 'view' THEN
        UPDATE prompts
        SET views = views + 1, updated_at = NOW()
        WHERE id = p_prompt_id;
    END IF;

    RETURN analytics_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ========================================
-- ADVANCED ANALYTICS VIEWS
-- ========================================

-- Daily analytics summary
CREATE OR REPLACE VIEW daily_analytics AS
SELECT
    DATE(created_at) as date,
    action_type,
    COUNT(*) as total_actions,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT prompt_id) as unique_prompts
FROM prompt_analytics
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at), action_type
ORDER BY date DESC, action_type;

-- Top performing prompts
CREATE OR REPLACE VIEW top_performing_prompts AS
SELECT
    p.id,
    p.act,
    p.category,
    p.type,
    p.views,
    p.likes,
    COUNT(pa.id) as total_interactions,
    COUNT(DISTINCT pa.user_id) as unique_users,
    p.views + p.likes * 2 + COUNT(pa.id) as performance_score
FROM prompts p
LEFT JOIN prompt_analytics pa ON p.id = pa.prompt_id
WHERE p.is_public = true
GROUP BY p.id, p.act, p.category, p.type, p.views, p.likes
ORDER BY performance_score DESC
LIMIT 100;

-- ========================================
-- PROMPT RECOMMENDATIONS SYSTEM
-- ========================================

CREATE TABLE IF NOT EXISTS prompt_similarities (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    prompt_id_1 UUID REFERENCES prompts(id) ON DELETE CASCADE,
    prompt_id_2 UUID REFERENCES prompts(id) ON DELETE CASCADE,
    similarity_score NUMERIC(5,4) CHECK (similarity_score >= 0 AND similarity_score <= 1),
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(prompt_id_1, prompt_id_2),
    CHECK (prompt_id_1 < prompt_id_2) -- Ensure consistent ordering
);

-- Index for similarity queries
CREATE INDEX idx_similarities_prompt1_score ON prompt_similarities(prompt_id_1, similarity_score DESC);
CREATE INDEX idx_similarities_prompt2_score ON prompt_similarities(prompt_id_2, similarity_score DESC);

-- Function to get similar prompts
CREATE OR REPLACE FUNCTION get_similar_prompts(
    p_prompt_id UUID,
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    prompt_id UUID,
    act TEXT,
    category prompt_category,
    similarity_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        CASE
            WHEN ps.prompt_id_1 = p_prompt_id THEN ps.prompt_id_2
            ELSE ps.prompt_id_1
        END as prompt_id,
        p.act,
        p.category,
        ps.similarity_score
    FROM prompt_similarities ps
    JOIN prompts p ON (
        p.id = CASE
            WHEN ps.prompt_id_1 = p_prompt_id THEN ps.prompt_id_2
            ELSE ps.prompt_id_1
        END
    )
    WHERE (ps.prompt_id_1 = p_prompt_id OR ps.prompt_id_2 = p_prompt_id)
    AND p.is_public = true
    ORDER BY ps.similarity_score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- CONTENT MODERATION SYSTEM
-- ========================================

CREATE TABLE IF NOT EXISTS prompt_reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    prompt_id UUID REFERENCES prompts(id) ON DELETE CASCADE,
    reported_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    reason TEXT NOT NULL CHECK (reason IN ('spam', 'inappropriate', 'copyright', 'low_quality', 'other')),
    description TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'resolved', 'dismissed')),
    reviewed_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS for prompt reports
ALTER TABLE prompt_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can create reports" ON prompt_reports
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Users can view their own reports" ON prompt_reports
    FOR SELECT USING (reported_by = auth.uid());

-- ========================================
-- API RATE LIMITING TABLES
-- ========================================

CREATE TABLE IF NOT EXISTS api_rate_limits (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    request_count INTEGER DEFAULT 1,
    window_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_id, endpoint, window_start)
);

-- Function to check rate limits
CREATE OR REPLACE FUNCTION check_rate_limit(
    p_endpoint TEXT,
    p_limit INTEGER DEFAULT 100,
    p_window_minutes INTEGER DEFAULT 60
)
RETURNS BOOLEAN AS $$
DECLARE
    current_count INTEGER;
    window_start TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Calculate window start
    window_start := DATE_TRUNC('hour', NOW()) +
                   (EXTRACT(MINUTE FROM NOW())::INTEGER / p_window_minutes) *
                   (p_window_minutes || ' minutes')::INTERVAL;

    -- Get or create rate limit record
    INSERT INTO api_rate_limits (user_id, endpoint, window_start, request_count)
    VALUES (auth.uid(), p_endpoint, window_start, 1)
    ON CONFLICT (user_id, endpoint, window_start)
    DO UPDATE SET
        request_count = api_rate_limits.request_count + 1,
        created_at = NOW()
    RETURNING request_count INTO current_count;

    -- Return true if under limit
    RETURN current_count <= p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
