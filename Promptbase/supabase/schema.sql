-- Supabase Database Schema for Awesome ChatGPT Prompts
-- Run this in your Supabase SQL editor

-- Create enum for prompt categories
CREATE TYPE prompt_category AS ENUM ('general', 'developer', 'creative', 'business', 'educational', 'technical');

-- Create enum for prompt types
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
        to_tsvector('english', act || ' ' || prompt || ' ' || COALESCE(contributor, '') || ' ' || array_to_string(tags, ' '))
    ) STORED
);

-- System prompts table (for base/ directory content)
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

-- App prompts table (for vibe prompts)
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
        to_tsvector('english', app_name || ' ' || description || ' ' || array_to_string(techstack, ' '))
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

CREATE INDEX idx_system_prompts_service ON system_prompts(service_name);
CREATE INDEX idx_system_prompts_date ON system_prompts(version_date);
CREATE INDEX idx_system_prompts_search ON system_prompts USING gin(search_vector);

CREATE INDEX idx_app_prompts_search ON app_prompts USING gin(search_vector);
CREATE INDEX idx_app_prompts_techstack ON app_prompts USING gin(techstack);

-- Create functions for updating timestamps
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

-- Row Level Security (RLS) policies
ALTER TABLE prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_favorites ENABLE ROW LEVEL SECURITY;
ALTER TABLE collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE collection_items ENABLE ROW LEVEL SECURITY;

-- Policies for prompts table
CREATE POLICY "Public prompts are viewable by everyone" ON prompts
    FOR SELECT USING (is_public = true);

CREATE POLICY "Users can insert prompts" ON prompts
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Users can update their own prompts" ON prompts
    FOR UPDATE USING (auth.uid() = created_by);

CREATE POLICY "Users can delete their own prompts" ON prompts
    FOR DELETE USING (auth.uid() = created_by);

-- Policies for system_prompts table (read-only for most users)
CREATE POLICY "System prompts are viewable by everyone" ON system_prompts
    FOR SELECT USING (true);

-- Policies for app_prompts table
CREATE POLICY "App prompts are viewable by everyone" ON app_prompts
    FOR SELECT USING (true);

-- Policies for user_favorites table
CREATE POLICY "Users can manage their own favorites" ON user_favorites
    FOR ALL USING (auth.uid() = user_id);

-- Policies for collections table
CREATE POLICY "Public collections are viewable by everyone" ON collections
    FOR SELECT USING (is_public = true OR auth.uid() = created_by);

CREATE POLICY "Users can create collections" ON collections
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Users can update their own collections" ON collections
    FOR UPDATE USING (auth.uid() = created_by);

CREATE POLICY "Users can delete their own collections" ON collections
    FOR DELETE USING (auth.uid() = created_by);

-- Policies for collection_items table
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

-- Create functions for search
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
        ts_rank(p.search_vector, plainto_tsquery('english', search_query)) as rank
    FROM prompts p
    WHERE p.search_vector @@ plainto_tsquery('english', search_query)
    AND p.is_public = true
    ORDER BY rank DESC, p.created_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;
