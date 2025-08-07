# 🚀 Quick Setup - Complete These 2 Steps

## ✅ Step 1: Database Schema
1. Go to: https://supabase.com/dashboard/project/mvajognrlmunncwvelwn/sql
2. Copy ALL contents of `supabase/complete-schema.sql`
3. Paste in SQL editor and click "Run"

## ✅ Step 2: Service Key
1. Go to: https://supabase.com/dashboard/project/mvajognrlmunncwvelwn/settings/api
2. Copy your `service_role` key (the long JWT token)
3. Edit your `.env` file and add:

```bash
# Add this line to your .env file
SUPABASE_SERVICE_KEY=your-service-role-key-here
```

## ✅ Step 3: Run Sync
After completing steps 1 & 2:

```bash
npm run sync
```

---

**Your Supabase Dashboard**: https://supabase.com/dashboard/project/mvajognrlmunncwvelwn
