-- COMPLETE SUPABASE SCHEMA FOR AWESOME CHATGPT PROMPTS
-- Copy this entire file and run it in your Supabase SQL Editor

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create enum types
CREATE TYPE prompt_category AS ENUM ('general', 'developer', 'creative', 'business', 'educational', 'technical');
CREATE TYPE prompt_type AS ENUM ('chatgpt', 'system', 'vibe', 'app');

-- Main prompts table
CREATE TABLE prompts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    act TEXT NOT NULL,
    prompt TEXT NOT NULL,
    category prompt_category DEFAULT 'general',
    type prompt_type DEFAULT 'chatgpt',
    for_devs BOOLEAN DEFAULT FALSE,
    contributor TEXT,
    techstack TEXT[],
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    is_public BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,

    -- Add search functionality
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', act || ' ' || prompt || ' ' || COALESCE(contributor, '') || ' ' || array_to_string(COALESCE(tags, '{}'), ' '))
    ) STORED
);

-- System prompts table
CREATE TABLE system_prompts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    service_name TEXT NOT NULL,
    model_name TEXT,
    version_date DATE,
    filename TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    source_url TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Add search functionality
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', service_name || ' ' || COALESCE(model_name, '') || ' ' || system_prompt)
    ) STORED
);

-- App prompts table
CREATE TABLE app_prompts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    app_name TEXT NOT NULL,
    description TEXT NOT NULL,
    contributor TEXT,
    techstack TEXT[],
    difficulty TEXT CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    estimated_time TEXT,
    features TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,

    -- Add search functionality
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', app_name || ' ' || description || ' ' || array_to_string(COALESCE(techstack, '{}'), ' '))
    ) STORED
);

-- User favorites
CREATE TABLE user_favorites (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    prompt_id UUID REFERENCES prompts(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_id, prompt_id)
);

-- User collections
CREATE TABLE collections (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_by UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Collection items
CREATE TABLE collection_items (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    prompt_id UUID REFERENCES prompts(id) ON DELETE CASCADE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(collection_id, prompt_id)
);

-- Create indexes for better performance
CREATE INDEX idx_prompts_category ON prompts(category);
CREATE INDEX idx_prompts_type ON prompts(type);
CREATE INDEX idx_prompts_for_devs ON prompts(for_devs);
CREATE INDEX idx_prompts_created_at ON prompts(created_at);
CREATE INDEX idx_prompts_search ON prompts USING gin(search_vector);
CREATE INDEX idx_prompts_tags ON prompts USING gin(tags);
CREATE INDEX idx_prompts_views ON prompts(views DESC);
CREATE INDEX idx_prompts_likes ON prompts(likes DESC);

CREATE INDEX idx_system_prompts_service ON system_prompts(service_name);
CREATE INDEX idx_system_prompts_date ON system_prompts(version_date);
CREATE INDEX idx_system_prompts_search ON system_prompts USING gin(search_vector);

CREATE INDEX idx_app_prompts_search ON app_prompts USING gin(search_vector);
CREATE INDEX idx_app_prompts_techstack ON app_prompts USING gin(techstack);
CREATE INDEX idx_app_prompts_views ON app_prompts(views DESC);

-- Trigram indexes for similarity searches
CREATE INDEX idx_prompts_prompt_trgm ON prompts USING gin(prompt gin_trgm_ops);
CREATE INDEX idx_system_prompts_content_trgm ON system_prompts USING gin(system_prompt gin_trgm_ops);
CREATE INDEX idx_app_prompts_description_trgm ON app_prompts USING gin(description gin_trgm_ops);

-- Function for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updating timestamps
CREATE TRIGGER update_prompts_updated_at BEFORE UPDATE ON prompts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_prompts_updated_at BEFORE UPDATE ON system_prompts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_app_prompts_updated_at BEFORE UPDATE ON app_prompts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_collections_updated_at BEFORE UPDATE ON collections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_favorites ENABLE ROW LEVEL SECURITY;
ALTER TABLE collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE collection_items ENABLE ROW LEVEL SECURITY;

-- RLS Policies for prompts
CREATE POLICY "Public prompts are viewable by everyone" ON prompts
    FOR SELECT USING (is_public = true);

CREATE POLICY "Users can insert prompts" ON prompts
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Users can update their own prompts" ON prompts
    FOR UPDATE USING (auth.uid() = created_by);

CREATE POLICY "Users can delete their own prompts" ON prompts
    FOR DELETE USING (auth.uid() = created_by);

-- RLS Policies for system_prompts (read-only for most users)
CREATE POLICY "System prompts are viewable by everyone" ON system_prompts
    FOR SELECT USING (true);

-- RLS Policies for app_prompts
CREATE POLICY "App prompts are viewable by everyone" ON app_prompts
    FOR SELECT USING (true);

-- RLS Policies for user_favorites
CREATE POLICY "Users can manage their own favorites" ON user_favorites
    FOR ALL USING (auth.uid() = user_id);

-- RLS Policies for collections
CREATE POLICY "Public collections are viewable by everyone" ON collections
    FOR SELECT USING (is_public = true OR auth.uid() = created_by);

CREATE POLICY "Users can create collections" ON collections
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Users can update their own collections" ON collections
    FOR UPDATE USING (auth.uid() = created_by);

CREATE POLICY "Users can delete their own collections" ON collections
    FOR DELETE USING (auth.uid() = created_by);

-- RLS Policies for collection_items
CREATE POLICY "Collection items inherit collection visibility" ON collection_items
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM collections
            WHERE collections.id = collection_items.collection_id
            AND (collections.is_public = true OR collections.created_by = auth.uid())
        )
    );

CREATE POLICY "Users can manage items in their collections" ON collection_items
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM collections
            WHERE collections.id = collection_items.collection_id
            AND collections.created_by = auth.uid()
        )
    );

-- Utility Functions

-- Function to increment view count
CREATE OR REPLACE FUNCTION increment_views(prompt_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE prompts SET views = views + 1 WHERE id = prompt_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to increment like count
CREATE OR REPLACE FUNCTION increment_likes(prompt_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE prompts SET likes = likes + 1 WHERE id = prompt_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to decrement like count
CREATE OR REPLACE FUNCTION decrement_likes(prompt_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE prompts SET likes = GREATEST(likes - 1, 0) WHERE id = prompt_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to increment app views
CREATE OR REPLACE FUNCTION increment_app_views(app_prompt_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE app_prompts SET views = views + 1 WHERE id = app_prompt_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Search function for prompts
CREATE OR REPLACE FUNCTION search_prompts(search_query TEXT, limit_count INTEGER DEFAULT 50)
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
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id, p.act, p.prompt, p.category, p.type, p.for_devs,
        p.contributor, p.techstack, p.tags, p.created_at,
        ts_rank(p.search_vector, plainto_tsquery('english', search_query)) as rank
    FROM prompts p
    WHERE p.search_vector @@ plainto_tsquery('english', search_query)
    AND p.is_public = true
    ORDER BY rank DESC, p.created_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Get trending prompts
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
        p.id, p.act, p.prompt, p.category, p.type, p.for_devs,
        p.contributor, p.techstack, p.tags, p.created_at, p.views, p.likes,
        ((p.likes * 2.0) + (p.views * 0.1) +
         (EXTRACT(EPOCH FROM (NOW() - p.created_at)) / 86400 * -1)) as trend_score
    FROM prompts p
    WHERE p.is_public = true
    AND p.created_at > NOW() - INTERVAL '30 days'
    ORDER BY trend_score DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Get statistics
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

-- Search across all content types
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
        SELECT 'prompts'::TEXT, p.id, p.act, p.prompt, p.type::TEXT, p.category::TEXT, p.created_at,
               ts_rank(p.search_vector, plainto_tsquery('english', search_query)) as rank
        FROM prompts p
        WHERE p.search_vector @@ plainto_tsquery('english', search_query) AND p.is_public = true
    )
    UNION ALL
    (
        SELECT 'system_prompts'::TEXT, sp.id,
               (sp.service_name || COALESCE(' ' || sp.model_name, ''))::TEXT,
               sp.system_prompt, 'system'::TEXT, 'system'::TEXT, sp.created_at,
               ts_rank(sp.search_vector, plainto_tsquery('english', search_query)) as rank
        FROM system_prompts sp
        WHERE sp.search_vector @@ plainto_tsquery('english', search_query)
    )
    UNION ALL
    (
        SELECT 'app_prompts'::TEXT, ap.id, ap.app_name, ap.description,
               'app'::TEXT, 'app'::TEXT, ap.created_at,
               ts_rank(ap.search_vector, plainto_tsquery('english', search_query)) as rank
        FROM app_prompts ap
        WHERE ap.search_vector @@ plainto_tsquery('english', search_query)
    )
    ORDER BY rank DESC, created_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;
