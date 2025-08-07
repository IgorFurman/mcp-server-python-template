import { auth, handleSupabaseError } from './client.js'

/**
 * Authentication utilities and helpers
 */

// Auth state management
export class AuthManager {
  constructor() {
    this.user = null
    this.session = null
    this.loading = true
    this.listeners = []
  }

  // Initialize auth state
  async initialize() {
    try {
      this.user = await auth.getCurrentUser()
      this.loading = false
      this.notifyListeners()
    } catch (error) {
      console.error('Auth initialization error:', error)
      this.loading = false
      this.notifyListeners()
    }

    // Listen for auth changes
    auth.onAuthStateChange((event, session) => {
      this.session = session
      this.user = session?.user || null
      this.loading = false
      this.notifyListeners()
    })
  }

  // Subscribe to auth state changes
  subscribe(callback) {
    this.listeners.push(callback)
    return () => {
      this.listeners = this.listeners.filter(listener => listener !== callback)
    }
  }

  // Notify all listeners of state changes
  notifyListeners() {
    this.listeners.forEach(callback => {
      callback({
        user: this.user,
        session: this.session,
        loading: this.loading,
        isAuthenticated: !!this.user
      })
    })
  }

  // Get current auth state
  getState() {
    return {
      user: this.user,
      session: this.session,
      loading: this.loading,
      isAuthenticated: !!this.user
    }
  }
}

// Create global auth manager instance
export const authManager = new AuthManager()

/**
 * Auth form handlers
 */
export const authForms = {
  // Sign up form handler
  signUp: async (formData) => {
    try {
      const { email, password, fullName } = formData
      
      const { user, session } = await auth.signUp(email, password, {
        full_name: fullName
      })

      return {
        success: true,
        user,
        session,
        message: 'Account created successfully! Please check your email for verification.'
      }
    } catch (error) {
      return {
        success: false,
        error: handleSupabaseError(error)
      }
    }
  },

  // Sign in form handler
  signIn: async (formData) => {
    try {
      const { email, password } = formData
      
      const { user, session } = await auth.signIn(email, password)

      return {
        success: true,
        user,
        session,
        message: 'Signed in successfully!'
      }
    } catch (error) {
      return {
        success: false,
        error: handleSupabaseError(error)
      }
    }
  },

  // Password reset form handler
  resetPassword: async (email) => {
    try {
      await auth.resetPassword(email)
      
      return {
        success: true,
        message: 'Password reset link sent to your email!'
      }
    } catch (error) {
      return {
        success: false,
        error: handleSupabaseError(error)
      }
    }
  },

  // Update password form handler
  updatePassword: async (password) => {
    try {
      await auth.updatePassword(password)
      
      return {
        success: true,
        message: 'Password updated successfully!'
      }
    } catch (error) {
      return {
        success: false,
        error: handleSupabaseError(error)
      }
    }
  },

  // OAuth sign in handler
  signInWithProvider: async (provider) => {
    try {
      const { url } = await auth.signInWithProvider(provider)
      
      // Redirect to OAuth provider
      if (url) {
        window.location.href = url
      }
      
      return {
        success: true,
        message: `Redirecting to ${provider}...`
      }
    } catch (error) {
      return {
        success: false,
        error: handleSupabaseError(error)
      }
    }
  },

  // Sign out handler
  signOut: async () => {
    try {
      await auth.signOut()
      
      return {
        success: true,
        message: 'Signed out successfully!'
      }
    } catch (error) {
      return {
        success: false,
        error: handleSupabaseError(error)
      }
    }
  }
}

/**
 * Auth guards and middleware
 */
export const authGuards = {
  // Require authentication
  requireAuth: (callback) => {
    return async (...args) => {
      const { isAuthenticated } = authManager.getState()
      
      if (!isAuthenticated) {
        throw new Error('Authentication required')
      }
      
      return callback(...args)
    }
  },

  // Require specific role/permission
  requireRole: (role, callback) => {
    return async (...args) => {
      const { user } = authManager.getState()
      
      if (!user) {
        throw new Error('Authentication required')
      }
      
      const userRole = user.user_metadata?.role || 'user'
      if (userRole !== role && userRole !== 'admin') {
        throw new Error('Insufficient permissions')
      }
      
      return callback(...args)
    }
  },

  // Allow only owner or admin
  requireOwnership: (resourceOwnerId, callback) => {
    return async (...args) => {
      const { user } = authManager.getState()
      
      if (!user) {
        throw new Error('Authentication required')
      }
      
      const userRole = user.user_metadata?.role || 'user'
      if (user.id !== resourceOwnerId && userRole !== 'admin') {
        throw new Error('Access denied')
      }
      
      return callback(...args)
    }
  }
}

/**
 * Auth utilities
 */
export const authUtils = {
  // Check if user has permission
  hasPermission: (permission) => {
    const { user } = authManager.getState()
    if (!user) return false
    
    const userRole = user.user_metadata?.role || 'user'
    const permissions = user.user_metadata?.permissions || []
    
    return userRole === 'admin' || permissions.includes(permission)
  },

  // Get user display name
  getDisplayName: (user = null) => {
    const currentUser = user || authManager.getState().user
    if (!currentUser) return 'Anonymous'
    
    return (
      currentUser.user_metadata?.full_name ||
      currentUser.user_metadata?.name ||
      currentUser.email?.split('@')[0] ||
      'User'
    )
  },

  // Get user avatar URL
  getAvatarUrl: (user = null) => {
    const currentUser = user || authManager.getState().user
    if (!currentUser) return null
    
    return (
      currentUser.user_metadata?.avatar_url ||
      currentUser.user_metadata?.picture ||
      `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(
        authUtils.getDisplayName(currentUser)
      )}`
    )
  },

  // Format user profile
  formatUserProfile: (user = null) => {
    const currentUser = user || authManager.getState().user
    if (!currentUser) return null
    
    return {
      id: currentUser.id,
      email: currentUser.email,
      displayName: authUtils.getDisplayName(currentUser),
      avatarUrl: authUtils.getAvatarUrl(currentUser),
      role: currentUser.user_metadata?.role || 'user',
      createdAt: currentUser.created_at,
      lastSignIn: currentUser.last_sign_in_at,
      isVerified: currentUser.email_confirmed_at !== null
    }
  },

  // Validate email format
  validateEmail: (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  },

  // Validate password strength
  validatePassword: (password) => {
    const errors = []
    
    if (password.length < 6) {
      errors.push('Password must be at least 6 characters long')
    }
    
    if (!/[A-Z]/.test(password)) {
      errors.push('Password must contain at least one uppercase letter')
    }
    
    if (!/[a-z]/.test(password)) {
      errors.push('Password must contain at least one lowercase letter')
    }
    
    if (!/\d/.test(password)) {
      errors.push('Password must contain at least one number')
    }
    
    return {
      isValid: errors.length === 0,
      errors
    }
  }
}

/**
 * Session management
 */
export const sessionManager = {
  // Save data to session
  set: (key, value) => {
    try {
      sessionStorage.setItem(`supabase_${key}`, JSON.stringify(value))
    } catch (error) {
      console.error('Session storage error:', error)
    }
  },

  // Get data from session
  get: (key) => {
    try {
      const item = sessionStorage.getItem(`supabase_${key}`)
      return item ? JSON.parse(item) : null
    } catch (error) {
      console.error('Session storage error:', error)
      return null
    }
  },

  // Remove data from session
  remove: (key) => {
    try {
      sessionStorage.removeItem(`supabase_${key}`)
    } catch (error) {
      console.error('Session storage error:', error)
    }
  },

  // Clear all session data
  clear: () => {
    try {
      Object.keys(sessionStorage)
        .filter(key => key.startsWith('supabase_'))
        .forEach(key => sessionStorage.removeItem(key))
    } catch (error) {
      console.error('Session storage error:', error)
    }
  }
}

// Initialize auth manager
if (typeof window !== 'undefined') {
  authManager.initialize()
}

export default {
  authManager,
  authForms,
  authGuards,
  authUtils,
  sessionManager
}