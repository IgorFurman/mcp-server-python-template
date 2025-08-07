import { db, supabase, utils } from './client.js'

/**
 * CRUD operations for prompts
 */
export const promptsAPI = {
  // Get all prompts with pagination and filtering
  getAll: async (options = {}) => {
    const {
      page = 1,
      limit = 50,
      category = null,
      type = 'chatgpt',
      forDevs = null,
      search = null,
      sortBy = 'created_at',
      sortOrder = 'desc'
    } = options

    let query = db.from('prompts')
      .select('*')
      .eq('is_public', true)

    // Apply filters
    if (category) query = query.eq('category', category)
    if (type) query = query.eq('type', type)
    if (forDevs !== null) query = query.eq('for_devs', forDevs)

    // Apply search
    if (search) {
      const sanitizedSearch = utils.sanitizeSearchQuery(search)
      query = query.textSearch('search_vector', sanitizedSearch)
    }

    // Apply sorting and pagination
    const offset = (page - 1) * limit
    query = query
      .order(sortBy, { ascending: sortOrder === 'asc' })
      .range(offset, offset + limit - 1)

    const { data, error, count } = await query

    if (error) throw error

    return {
      data,
      pagination: {
        page,
        limit,
        total: count,
        totalPages: Math.ceil(count / limit)
      }
    }
  },

  // Get prompt by ID
  getById: async (id) => {
    const { data, error } = await db.from('prompts')
      .select('*')
      .eq('id', id)
      .eq('is_public', true)
      .single()

    if (error) throw error

    // Increment view count
    await promptsAPI.incrementViews(id)

    return data
  },

  // Search prompts using full-text search
  search: async (query, limit = 50) => {
    const sanitizedQuery = utils.sanitizeSearchQuery(query)

    const { data, error } = await supabase
      .rpc('search_prompts', {
        search_query: sanitizedQuery,
        limit_count: limit
      })

    if (error) throw error
    return data
  },

  // Create new prompt
  create: async (promptData) => {
    const user = await supabase.auth.getUser()
    if (!user.data.user) throw new Error('Authentication required')

    const newPrompt = {
      ...promptData,
      created_by: user.data.user.id,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }

    const { data, error } = await db.from('prompts')
      .insert(newPrompt)
      .select()
      .single()

    if (error) throw error
    return data
  },

  // Update prompt
  update: async (id, updates) => {
    const user = await supabase.auth.getUser()
    if (!user.data.user) throw new Error('Authentication required')

    const { data, error } = await db.from('prompts')
      .update({
        ...updates,
        updated_at: new Date().toISOString()
      })
      .eq('id', id)
      .eq('created_by', user.data.user.id)
      .select()
      .single()

    if (error) throw error
    return data
  },

  // Delete prompt
  delete: async (id) => {
    const user = await supabase.auth.getUser()
    if (!user.data.user) throw new Error('Authentication required')

    const { error } = await db.from('prompts')
      .delete()
      .eq('id', id)
      .eq('created_by', user.data.user.id)

    if (error) throw error
    return true
  },

  // Get user's prompts
  getUserPrompts: async (userId, options = {}) => {
    const { page = 1, limit = 20 } = options
    const offset = (page - 1) * limit

    const { data, error, count } = await db.from('prompts')
      .select('*', { count: 'exact' })
      .eq('created_by', userId)
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1)

    if (error) throw error

    return {
      data,
      pagination: {
        page,
        limit,
        total: count,
        totalPages: Math.ceil(count / limit)
      }
    }
  },

  // Increment view count
  incrementViews: async (id) => {
    const { error } = await supabase.rpc('increment_views', { prompt_id: id })
    if (error) console.error('Error incrementing views:', error)
  },

  // Like/unlike prompt
  toggleLike: async (id) => {
    const user = await supabase.auth.getUser()
    if (!user.data.user) throw new Error('Authentication required')

    // Check if already liked
    const { data: existingLike } = await db.from('user_favorites')
      .select('id')
      .eq('user_id', user.data.user.id)
      .eq('prompt_id', id)
      .single()

    if (existingLike) {
      // Unlike - remove from favorites and decrement likes
      await db.from('user_favorites')
        .delete()
        .eq('user_id', user.data.user.id)
        .eq('prompt_id', id)

      await supabase.rpc('decrement_likes', { prompt_id: id })
      return { liked: false }
    } else {
      // Like - add to favorites and increment likes
      await db.from('user_favorites')
        .insert({
          user_id: user.data.user.id,
          prompt_id: id
        })

      await supabase.rpc('increment_likes', { prompt_id: id })
      return { liked: true }
    }
  },

  // Check if user has liked a prompt
  isLiked: async (id) => {
    const user = await supabase.auth.getUser()
    if (!user.data.user) return false

    const { data } = await db.from('user_favorites')
      .select('id')
      .eq('user_id', user.data.user.id)
      .eq('prompt_id', id)
      .single()

    return !!data
  },

  // Get user's favorites
  getFavorites: async (userId, options = {}) => {
    const { page = 1, limit = 20 } = options
    const offset = (page - 1) * limit

    const { data, error, count } = await db.from('user_favorites')
      .select(`
        created_at,
        prompts (*)
      `, { count: 'exact' })
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1)

    if (error) throw error

    return {
      data: data.map(item => ({
        ...item.prompts,
        favorited_at: item.created_at
      })),
      pagination: {
        page,
        limit,
        total: count,
        totalPages: Math.ceil(count / limit)
      }
    }
  },

  // Get popular prompts
  getPopular: async (limit = 20, timeframe = 'week') => {
    let dateFilter = new Date()

    switch (timeframe) {
      case 'day':
        dateFilter.setDate(dateFilter.getDate() - 1)
        break
      case 'week':
        dateFilter.setDate(dateFilter.getDate() - 7)
        break
      case 'month':
        dateFilter.setMonth(dateFilter.getMonth() - 1)
        break
      case 'all':
        dateFilter = null
        break
    }

    let query = db.from('prompts')
      .select('*')
      .eq('is_public', true)
      .order('likes', { ascending: false })
      .limit(limit)

    if (dateFilter) {
      query = query.gte('created_at', dateFilter.toISOString())
    }

    const { data, error } = await query
    if (error) throw error
    return data
  },

  // Get trending prompts (high views/likes ratio recently)
  getTrending: async (limit = 20) => {
    const { data, error } = await supabase.rpc('get_trending_prompts', {
      limit_count: limit
    })

    if (error) throw error
    return data
  },

  // Get related prompts based on tags/category
  getRelated: async (promptId, limit = 10) => {
    // First get the current prompt's tags and category
    const { data: currentPrompt } = await db.from('prompts')
      .select('tags, category')
      .eq('id', promptId)
      .single()

    if (!currentPrompt) return []

    const { data, error } = await db.from('prompts')
      .select('*')
      .eq('is_public', true)
      .neq('id', promptId)
      .or(`category.eq.${currentPrompt.category},tags.ov.{${currentPrompt.tags?.join(',') || ''}}`)
      .order('likes', { ascending: false })
      .limit(limit)

    if (error) throw error
    return data
  }
}

/**
 * System prompts API
 */
export const systemPromptsAPI = {
  // Get all system prompts
  getAll: async (options = {}) => {
    const {
      page = 1,
      limit = 50,
      service = null,
      search = null,
      sortBy = 'version_date',
      sortOrder = 'desc'
    } = options

    let query = db.from('system_prompts').select('*')

    if (service) query = query.eq('service_name', service)

    if (search) {
      const sanitizedSearch = utils.sanitizeSearchQuery(search)
      query = query.textSearch('search_vector', sanitizedSearch)
    }

    const offset = (page - 1) * limit
    query = query
      .order(sortBy, { ascending: sortOrder === 'asc' })
      .range(offset, offset + limit - 1)

    const { data, error, count } = await query

    if (error) throw error

    return {
      data,
      pagination: {
        page,
        limit,
        total: count,
        totalPages: Math.ceil(count / limit)
      }
    }
  },

  // Get system prompt by ID
  getById: async (id) => {
    const { data, error } = await db.from('system_prompts')
      .select('*')
      .eq('id', id)
      .single()

    if (error) throw error
    return data
  },

  // Get services list
  getServices: async () => {
    const { data, error } = await db.from('system_prompts')
      .select('service_name')
      .order('service_name')

    if (error) throw error

    // Return unique services
    return [...new Set(data.map(item => item.service_name))]
  }
}

/**
 * App prompts API
 */
export const appPromptsAPI = {
  // Get all app prompts
  getAll: async (options = {}) => {
    const {
      page = 1,
      limit = 50,
      difficulty = null,
      techstack = null,
      search = null,
      sortBy = 'created_at',
      sortOrder = 'desc'
    } = options

    let query = db.from('app_prompts').select('*')

    if (difficulty) query = query.eq('difficulty', difficulty)
    if (techstack) query = query.contains('techstack', [techstack])

    if (search) {
      const sanitizedSearch = utils.sanitizeSearchQuery(search)
      query = query.textSearch('search_vector', sanitizedSearch)
    }

    const offset = (page - 1) * limit
    query = query
      .order(sortBy, { ascending: sortOrder === 'asc' })
      .range(offset, offset + limit - 1)

    const { data, error, count } = await query

    if (error) throw error

    return {
      data,
      pagination: {
        page,
        limit,
        total: count,
        totalPages: Math.ceil(count / limit)
      }
    }
  },

  // Get app prompt by ID
  getById: async (id) => {
    const { data, error } = await db.from('app_prompts')
      .select('*')
      .eq('id', id)
      .single()

    if (error) throw error

    // Increment view count
    await appPromptsAPI.incrementViews(id)

    return data
  },

  // Increment view count
  incrementViews: async (id) => {
    const { error } = await supabase.rpc('increment_app_views', { app_prompt_id: id })
    if (error) console.error('Error incrementing app views:', error)
  },

  // Get popular tech stacks
  getTechStacks: async () => {
    const { data, error } = await db.from('app_prompts')
      .select('techstack')

    if (error) throw error

    // Flatten and count tech stacks
    const allTechStacks = data.flatMap(item => item.techstack || [])
    const techStackCounts = {}

    allTechStacks.forEach(tech => {
      techStackCounts[tech] = (techStackCounts[tech] || 0) + 1
    })

    return Object.entries(techStackCounts)
      .sort(([,a], [,b]) => b - a)
      .map(([tech, count]) => ({ name: tech, count }))
  }
}
