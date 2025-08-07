// Enhanced Supabase Client with Optimized Functions
// This extends your existing client.js with the new optimized functions

import { supabase } from './client.js';

// ========================================
// ENHANCED SEARCH FUNCTIONS
// ========================================

export const searchAPI = {
    // Enhanced search with filters and pagination
    async searchPrompts(query, options = {}) {
        const {
            category = null,
            type = null,
            limit = 20,
            offset = 0
        } = options;

        const { data, error } = await supabase.rpc('enhanced_search_prompts', {
            search_query: query,
            category_filter: category,
            type_filter: type,
            limit_count: limit,
            offset_count: offset
        });

        if (error) throw error;
        return data;
    },

    // Get trending prompts
    async getTrendingPrompts(daysBack = 7, limit = 10) {
        const { data, error } = await supabase.rpc('get_trending_prompts', {
            days_back: daysBack,
            limit_count: limit
        });

        if (error) throw error;
        return data;
    },

    // Get similar prompts
    async getSimilarPrompts(promptId, limit = 5) {
        const { data, error } = await supabase.rpc('get_similar_prompts', {
            p_prompt_id: promptId,
            p_limit: limit
        });

        if (error) throw error;
        return data;
    },

    // Advanced filters
    async getPromptsByFilters(filters = {}) {
        let query = supabase
            .from('prompts')
            .select(`
        id, act, prompt, category, type, techstack, tags,
        views, likes, created_at, contributor,
        created_by
      `)
            .eq('is_public', true);

        if (filters.category) {
            query = query.eq('category', filters.category);
        }

        if (filters.type) {
            query = query.eq('type', filters.type);
        }

        if (filters.forDevs !== undefined) {
            query = query.eq('for_devs', filters.forDevs);
        }

        if (filters.tags && filters.tags.length > 0) {
            query = query.contains('tags', filters.tags);
        }

        if (filters.techstack && filters.techstack.length > 0) {
            query = query.contains('techstack', filters.techstack);
        }

        if (filters.minViews) {
            query = query.gte('views', filters.minViews);
        }

        if (filters.sortBy) {
            const order = filters.sortOrder || 'desc';
            query = query.order(filters.sortBy, { ascending: order === 'asc' });
        } else {
            query = query.order('created_at', { ascending: false });
        }

        if (filters.limit) {
            query = query.limit(filters.limit);
        }

        const { data, error } = await query;
        if (error) throw error;
        return data;
    }
};

// ========================================
// ANALYTICS FUNCTIONS
// ========================================

export const analyticsAPI = {
    // Track user interactions
    async trackEvent(promptId, actionType, metadata = {}) {
        const { data, error } = await supabase.rpc('track_prompt_analytics', {
            p_prompt_id: promptId,
            p_action_type: actionType,
            p_ip_address: metadata.ipAddress || null,
            p_user_agent: metadata.userAgent || null,
            p_referrer: metadata.referrer || null,
            p_session_id: metadata.sessionId || null
        });

        if (error) throw error;
        return data;
    },

    // Get analytics data
    async getDailyAnalytics(days = 30) {
        const { data, error } = await supabase
            .from('daily_analytics')
            .select('*')
            .gte('date', new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0])
            .order('date', { ascending: false });

        if (error) throw error;
        return data;
    },

    // Get popular prompts by category
    async getPopularByCategory() {
        const { data, error } = await supabase
            .from('popular_prompts_by_category')
            .select('*')
            .order('avg_views', { ascending: false });

        if (error) throw error;
        return data;
    },

    // Get user engagement stats
    async getUserEngagement(userId = null) {
        let query = supabase.from('user_engagement_stats').select('*');

        if (userId) {
            query = query.eq('user_id', userId);
        }

        const { data, error } = await query.order('total_prompt_views', { ascending: false });
        if (error) throw error;
        return data;
    },

    // Get top performing prompts
    async getTopPerformingPrompts(limit = 20) {
        const { data, error } = await supabase
            .from('top_performing_prompts')
            .select('*')
            .limit(limit);

        if (error) throw error;
        return data;
    }
};

// ========================================
// USER MANAGEMENT FUNCTIONS
// ========================================

export const userAPI = {
    // Get user's favorites with prompt details
    async getUserFavorites(userId = null) {
        const targetUserId = userId || (await supabase.auth.getUser()).data.user?.id;

        const { data, error } = await supabase
            .from('user_favorites')
            .select(`
        id, created_at,
        prompts:prompt_id (
          id, act, prompt, category, type, views, likes, created_at
        )
      `)
            .eq('user_id', targetUserId)
            .order('created_at', { ascending: false });

        if (error) throw error;
        return data;
    },

    // Get user's collections with items
    async getUserCollections(userId = null) {
        const targetUserId = userId || (await supabase.auth.getUser()).data.user?.id;

        const { data, error } = await supabase
            .from('collections')
            .select(`
        id, name, description, is_public, created_at,
        collection_items (
          prompts:prompt_id (
            id, act, category, type, views, likes
          )
        )
      `)
            .eq('created_by', targetUserId)
            .order('created_at', { ascending: false });

        if (error) throw error;
        return data;
    },

    // Add prompt to favorites
    async addToFavorites(promptId) {
        const { data, error } = await supabase
            .from('user_favorites')
            .insert({ prompt_id: promptId })
            .select();

        if (error) throw error;
        return data;
    },

    // Remove from favorites
    async removeFromFavorites(promptId) {
        const user = await supabase.auth.getUser();
        const { error } = await supabase
            .from('user_favorites')
            .delete()
            .eq('prompt_id', promptId)
            .eq('user_id', user.data.user?.id);

        if (error) throw error;
        return true;
    },

    // Create collection
    async createCollection(name, description, isPublic = false) {
        const { data, error } = await supabase
            .from('collections')
            .insert({
                name,
                description,
                is_public: isPublic
            })
            .select();

        if (error) throw error;
        return data[0];
    },

    // Add prompt to collection
    async addToCollection(collectionId, promptId) {
        const { data, error } = await supabase
            .from('collection_items')
            .insert({
                collection_id: collectionId,
                prompt_id: promptId
            })
            .select();

        if (error) throw error;
        return data;
    }
};

// ========================================
// PROMPT MANAGEMENT FUNCTIONS
// ========================================

export const promptAPI = {
    // Create new prompt with versioning
    async createPrompt(promptData) {
        const { data, error } = await supabase
            .from('prompts')
            .insert({
                act: promptData.act,
                prompt: promptData.prompt,
                category: promptData.category || 'general',
                type: promptData.type || 'chatgpt',
                for_devs: promptData.forDevs || false,
                contributor: promptData.contributor,
                techstack: promptData.techstack || [],
                tags: promptData.tags || [],
                is_public: promptData.isPublic !== false
            })
            .select();

        if (error) throw error;
        return data[0];
    },

    // Update prompt with versioning
    async updatePrompt(promptId, updates, changeDescription = null) {
        if (changeDescription) {
            // Create version before updating
            const { error: versionError } = await supabase.rpc('create_prompt_version', {
                p_prompt_id: promptId,
                p_act: updates.act,
                p_prompt: updates.prompt,
                p_change_description: changeDescription
            });

            if (versionError) throw versionError;
        } else {
            // Direct update
            const { data, error } = await supabase
                .from('prompts')
                .update(updates)
                .eq('id', promptId)
                .select();

            if (error) throw error;
            return data[0];
        }
    },

    // Get prompt versions
    async getPromptVersions(promptId) {
        const { data, error } = await supabase
            .from('prompt_versions')
            .select('*')
            .eq('prompt_id', promptId)
            .order('version_number', { ascending: false });

        if (error) throw error;
        return data;
    },

    // Get prompt by ID with related data
    async getPromptById(promptId, includeAnalytics = false) {
        let query = supabase
            .from('prompts')
            .select(`
        id, act, prompt, category, type, for_devs,
        contributor, techstack, tags, views, likes,
        created_at, updated_at, is_public
      `)
            .eq('id', promptId)
            .single();

        const { data: prompt, error } = await query;
        if (error) throw error;

        if (includeAnalytics) {
            // Get analytics data
            const { data: analytics } = await supabase
                .from('prompt_analytics')
                .select('action_type, created_at')
                .eq('prompt_id', promptId)
                .order('created_at', { ascending: false })
                .limit(100);

            prompt.analytics = analytics || [];
        }

        return prompt;
    }
};

// ========================================
// MAINTENANCE FUNCTIONS
// ========================================

export const maintenanceAPI = {
    // Run data quality check
    async runDataQualityCheck() {
        const { data, error } = await supabase.rpc('data_quality_report');
        if (error) throw error;
        return data;
    },

    // Get performance statistics
    async getPerformanceStats() {
        const { data, error } = await supabase.rpc('find_unused_indexes');
        if (error) throw error;
        return data;
    },

    // Security audit
    async runSecurityAudit() {
        const { data, error } = await supabase.rpc('security_audit');
        if (error) throw error;
        return data;
    }
};

// ========================================
// BATCH OPERATIONS
// ========================================

export const batchAPI = {
    // Bulk import prompts
    async bulkImportPrompts(prompts) {
        const batchSize = 100;
        const results = [];

        for (let i = 0; i < prompts.length; i += batchSize) {
            const batch = prompts.slice(i, i + batchSize);
            const { data, error } = await supabase
                .from('prompts')
                .insert(batch)
                .select();

            if (error) throw error;
            results.push(...data);
        }

        return results;
    },

    // Bulk update views (for analytics)
    async bulkUpdateViews(updates) {
        // This would need to be implemented as a stored procedure
        // for better performance in production
        const promises = updates.map(update =>
            supabase
                .from('prompts')
                .update({ views: update.views })
                .eq('id', update.id)
        );

        const results = await Promise.all(promises);
        return results;
    }
};

// Export all APIs
export default {
    search: searchAPI,
    analytics: analyticsAPI,
    user: userAPI,
    prompt: promptAPI,
    maintenance: maintenanceAPI,
    batch: batchAPI
};
