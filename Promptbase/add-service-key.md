# 🔑 Adding Service Key to .env

To use admin functionality, you'll need to add your Supabase service role key:

1. **Get your service role key** from: Supabase Dashboard > Settings > API > service_role key

2. **Copy your service_role key** (it should start with `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`)

3. **Add this line to your .env file:**

```bash
# Service key for admin operations
SUPABASE_SERVICE_KEY=your-actual-service-key-here
```

**Your complete .env file should then look like this:**

```bash
# Supabase Configuration
SUPABASE_URL=https://mvajognrlmunncwvelwn.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im12YWpvZ25ybG11bm5jd3ZlbHduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQwNjU0NDksImV4cCI6MjA2OTY0MTQ0OX0.GoN2BDUT933tM6zMxHOGZczmaZFkSEHKQ6_5_ESBr5M

# For frontend applications (if using Next.js/React)
NEXT_PUBLIC_SUPABASE_URL=https://mvajognrlmunncwvelwn.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im12YWpvZ25ybG11bm5jd3ZlbHduIiwicm9zZSI6ImFub24iLCJpYXQiOjE3NTQwNjU0NDksImV4cCI6MjA2OTY0MTQ0OX0.GoN2BDUT933tM6zMxHOGZczmaZFkSEHKQ6_5_ESBr5M

# Service key for admin operations
SUPABASE_SERVICE_KEY=your-actual-service-key-here
```

⚠️ **Important**: The service key has admin privileges - keep it secure and never expose it in client-side code!
