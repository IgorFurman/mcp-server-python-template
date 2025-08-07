import { createClient } from '@supabase/supabase-js'

// Supabase configuration
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables. Please check your .env file.')
}

// Create Supabase client
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true
  },
  realtime: {
    params: {
      eventsPerSecond: 10,
    },
  },
})

// Auth helpers
export const auth = {
  // Get current user
  getCurrentUser: async () => {
    const { data: { user }, error } = await supabase.auth.getUser()
    if (error) throw error
    return user
  },

  // Sign up with email and password
  signUp: async (email, password, metadata = {}) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: metadata
      }
    })
    if (error) throw error
    return data
  },

  // Sign in with email and password
  signIn: async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    })
    if (error) throw error
    return data
  },

  // Sign in with OAuth provider
  signInWithProvider: async (provider) => {
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/auth/callback`
      }
    })
    if (error) throw error
    return data
  },

  // Sign out
  signOut: async () => {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
  },

  // Reset password
  resetPassword: async (email) => {
    const { data, error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/reset-password`
    })
    if (error) throw error
    return data
  },

  // Update password
  updatePassword: async (password) => {
    const { data, error } = await supabase.auth.updateUser({
      password
    })
    if (error) throw error
    return data
  },

  // Listen to auth changes
  onAuthStateChange: (callback) => {
    return supabase.auth.onAuthStateChange(callback)
  }
}

// Database helpers
export const db = {
  // Generic query builder
  from: (table) => supabase.from(table),

  // Real-time subscription
  subscribe: (table, callback, filters = {}) => {
    return supabase
      .channel(`${table}_changes`)
      .on('postgres_changes', 
        { 
          event: '*', 
          schema: 'public', 
          table,
          ...filters 
        }, 
        callback
      )
      .subscribe()
  },

  // Unsubscribe from real-time
  unsubscribe: (subscription) => {
    return supabase.removeChannel(subscription)
  }
}

// Storage helpers
export const storage = {
  // Upload file
  upload: async (bucket, path, file, options = {}) => {
    const { data, error } = await supabase.storage
      .from(bucket)
      .upload(path, file, {
        cacheControl: '3600',
        upsert: false,
        ...options
      })
    if (error) throw error
    return data
  },

  // Download file
  download: async (bucket, path) => {
    const { data, error } = await supabase.storage
      .from(bucket)
      .download(path)
    if (error) throw error
    return data
  },

  // Get public URL
  getPublicUrl: (bucket, path) => {
    const { data } = supabase.storage
      .from(bucket)
      .getPublicUrl(path)
    return data.publicUrl
  },

  // Delete file
  remove: async (bucket, paths) => {
    const { data, error } = await supabase.storage
      .from(bucket)
      .remove(paths)
    if (error) throw error
    return data
  },

  // List files
  list: async (bucket, path = '', options = {}) => {
    const { data, error } = await supabase.storage
      .from(bucket)
      .list(path, {
        limit: 100,
        offset: 0,
        sortBy: { column: 'name', order: 'asc' },
        ...options
      })
    if (error) throw error
    return data
  }
}

// Error handling utility
export const handleSupabaseError = (error) => {
  console.error('Supabase error:', error)
  
  // Common error messages
  const errorMessages = {
    'Invalid login credentials': 'Invalid email or password',
    'Email not confirmed': 'Please check your email and click the confirmation link',
    'User already registered': 'An account with this email already exists',
    'Password should be at least 6 characters': 'Password must be at least 6 characters long'
  }

  return errorMessages[error.message] || error.message || 'An unexpected error occurred'
}

// Utility functions
export const utils = {
  // Check if user is authenticated
  isAuthenticated: async () => {
    try {
      const user = await auth.getCurrentUser()
      return !!user
    } catch {
      return false
    }
  },

  // Format Supabase timestamp
  formatTimestamp: (timestamp) => {
    return new Date(timestamp).toLocaleString()
  },

  // Generate UUID
  generateUUID: () => {
    return crypto.randomUUID()
  },

  // Sanitize search query
  sanitizeSearchQuery: (query) => {
    return query
      .trim()
      .replace(/[<>'"&]/g, '') // Remove potentially harmful characters
      .substring(0, 100) // Limit length
  }
}

export default supabase