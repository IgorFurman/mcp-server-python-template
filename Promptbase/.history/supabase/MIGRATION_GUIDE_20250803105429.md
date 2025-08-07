# Supabase Schema Optimization Migration Guide

This guide will help you apply the database optimizations to your awesome-chatgpt-prompts Supabase database.

## 📋 Prerequisites

- Access to your Supabase project dashboard
- SQL Editor access in Supabase
- Backup of your current database (recommended)

## 🚀 Migration Steps

### Step 1: Backup Your Database

```sql
-- Run this in Supabase SQL Editor to check current state
SELECT
    table_name,
    pg_size_pretty(pg_total_relation_size('public.' || table_name)) as size
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY pg_total_relation_size('public.' || table_name) DESC;
```

### Step 2: Apply Core Optimizations

1. **Open Supabase SQL Editor**
2. **Copy and paste the contents of `schema-optimizations.sql`**
3. **Execute the script**

Expected results:

- ✅ New indexes created
- ✅ Enhanced search function available
- ✅ Analytics views created
- ✅ Optimized RLS policies applied

### Step 3: Apply Advanced Features (Optional)

1. **Copy and paste the contents of `advanced-features.sql`**
2. **Execute the script**

This adds:

- ✅ Prompt versioning system
- ✅ Usage analytics tracking
- ✅ Recommendation system
- ✅ Content moderation tables

### Step 4: Set Up Maintenance Scripts

1. **Copy and paste the contents of `maintenance-scripts.sql`**
2. **Execute the script**

This provides:

- ✅ Performance monitoring functions
- ✅ Data quality checks
- ✅ Security audit functions

### Step 5: Update Your Application Code

1. **Install the enhanced client**:

   ```bash
   # Copy enhanced-client.js to your supabase directory
   cp enhanced-client.js ./supabase/
   ```

2. **Update your imports**:

   ```javascript
   // In your application files
   import enhancedAPI from "./supabase/enhanced-client.js";

   // Example usage
   const searchResults = await enhancedAPI.search.searchPrompts("javascript", {
     category: "developer",
     limit: 10,
   });
   ```

## 🔍 Testing the Optimizations

### Test Enhanced Search

```javascript
// Test the new search functionality
const results = await enhancedAPI.search.searchPrompts("react hooks", {
  category: "developer",
  type: "chatgpt",
  limit: 5,
});
console.log("Search results:", results);
```

### Test Analytics

```javascript
// Track a view event
await enhancedAPI.analytics.trackEvent(promptId, "view", {
  userAgent: navigator.userAgent,
  referrer: document.referrer,
});

// Get trending prompts
const trending = await enhancedAPI.search.getTrendingPrompts(7, 5);
console.log("Trending prompts:", trending);
```

### Test User Features

```javascript
// Get user favorites
const favorites = await enhancedAPI.user.getUserFavorites();
console.log("User favorites:", favorites);

// Create a collection
const collection = await enhancedAPI.user.createCollection(
  "My AI Prompts",
  "Collection of useful AI prompts",
  true
);
```

## 📊 Performance Monitoring

Run these queries periodically to monitor performance:

```sql
-- Check index usage
SELECT * FROM find_unused_indexes();

-- Data quality report
SELECT * FROM data_quality_report();

-- Security audit
SELECT * FROM security_audit();
```

## 🔧 Configuration Options

### Rate Limiting

Configure API rate limits by modifying the `check_rate_limit` function parameters:

```sql
-- Example: Allow 200 requests per hour for search
SELECT check_rate_limit('search', 200, 60);
```

### Analytics Retention

Set up automatic cleanup of old analytics data:

```sql
-- Example: Keep analytics data for 90 days
SELECT cleanup_old_data(90);
```

## 🚨 Troubleshooting

### Common Issues

1. **Index Creation Fails**

   ```sql
   -- Check for existing indexes
   SELECT indexname FROM pg_indexes WHERE tablename = 'prompts';
   ```

2. **Function Already Exists**

   ```sql
   -- Drop and recreate if needed
   DROP FUNCTION IF EXISTS enhanced_search_prompts CASCADE;
   ```

3. **RLS Policy Conflicts**
   ```sql
   -- Check existing policies
   SELECT policyname FROM pg_policies WHERE tablename = 'prompts';
   ```

### Performance Issues

If you experience slow queries after applying optimizations:

1. **Update table statistics**:

   ```sql
   SELECT update_table_statistics();
   ```

2. **Check query plans**:

   ```sql
   EXPLAIN ANALYZE SELECT * FROM enhanced_search_prompts('test query');
   ```

3. **Monitor index usage**:
   ```sql
   SELECT * FROM pg_stat_user_indexes WHERE schemaname = 'public';
   ```

## 📈 Expected Performance Improvements

After applying these optimizations, you should see:

- **Search Performance**: 40-60% faster search queries
- **Index Efficiency**: Better query execution plans
- **Analytics**: Real-time usage tracking
- **User Experience**: Faster page loads and interactions

## 🔄 Rollback Plan

If you need to rollback changes:

1. **Restore from backup** (recommended)
2. **Or manually remove optimizations**:

   ```sql
   -- Drop new indexes
   DROP INDEX IF EXISTS idx_prompts_category_type_created;
   DROP INDEX IF EXISTS idx_prompts_public_views;

   -- Drop new functions
   DROP FUNCTION IF EXISTS enhanced_search_prompts CASCADE;
   DROP FUNCTION IF EXISTS get_trending_prompts CASCADE;

   -- Restore original policies (refer to your original schema.sql)
   ```

## 📞 Support

If you encounter issues:

1. Check the Supabase logs in your dashboard
2. Review the data quality report: `SELECT * FROM data_quality_report();`
3. Monitor performance: `SELECT * FROM find_missing_indexes();`

## 🎯 Next Steps

1. **Monitor Performance**: Set up regular monitoring using the maintenance scripts
2. **Implement Caching**: Consider adding Redis or similar for frequently accessed data
3. **Scale Testing**: Test with larger datasets to ensure performance scales
4. **API Integration**: Integrate the enhanced client into your frontend applications

---

**Note**: Always test these changes in a development environment before applying to production!
