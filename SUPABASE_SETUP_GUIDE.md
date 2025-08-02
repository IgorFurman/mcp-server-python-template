# Supabase Database Setup Guide

## 🚀 **Complete Supabase Integration for Your Database**

### **1. Prerequisites Installed** ✅
- ✅ Supabase CLI v2.33.9
- ✅ Docker v28.3.3  
- ✅ Node.js v22.18.0

### **2. Initialize Your Local Supabase Project**

```bash
# Navigate to your project directory
cd /home/slimmite/Dokumenty/mpc-server/mcp-server-python-template

# Initialize Supabase project
supabase init

# This creates:
# - supabase/ directory
# - config.toml file
# - Database migrations folder
```

### **3. Database Configuration Options**

#### **Option A: Create New Supabase Project (Recommended)**
```bash
# Start local development environment
supabase start

# This will:
# - Start PostgreSQL database locally
# - Launch Supabase Studio (Web UI)
# - Create default authentication
# - Set up realtime subscriptions
```

#### **Option B: Link Existing Cloud Project**
```bash
# If you have existing Supabase project
supabase login
supabase link --project-ref YOUR_PROJECT_ID
supabase db pull  # Pull existing schema
```

### **4. VS Code Extension Setup**

After installing the Supabase extension, you'll get:

#### **GitHub Copilot Integration**
- Type `@supabase` in Copilot Chat
- Database schema provided as context
- AI-powered SQL generation

#### **Database Management Features**
- **Tables & Views**: Inspect schema directly in VS Code
- **Migrations**: Guided database migration creation
- **Functions**: View and edit database functions  
- **Storage**: Manage file buckets
- **Real-time**: Monitor database changes

### **5. Integration with Your MCP Server**

For your Sequential Think MCP Server integration:

```typescript
// Database connection configuration
const supabaseConfig = {
  url: process.env.SUPABASE_URL || 'http://localhost:54321',
  anonKey: process.env.SUPABASE_ANON_KEY || 'your-anon-key',
  serviceKey: process.env.SUPABASE_SERVICE_KEY || 'your-service-key'
};

// Enhanced prompt storage with Supabase
export interface PromptRecord {
  id: string;
  title: string;
  content: string;
  domain: string;
  complexity: string;
  quality_score: number;
  created_at: string;
  updated_at: string;
  tags: string[];
  ollama_enhanced: boolean;
}
```

### **6. Database Schema for OMOM React Onboarding**

```sql
-- User onboarding tracking
CREATE TABLE user_onboarding (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  current_step INTEGER DEFAULT 1,
  completed_steps TEXT[] DEFAULT '{}',
  progress_percent DECIMAL DEFAULT 0,
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  form_data JSONB DEFAULT '{}',
  analytics_data JSONB DEFAULT '{}'
);

-- Enhanced prompts with Ollama integration
CREATE TABLE enhanced_prompts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  original_prompt TEXT NOT NULL,
  enhanced_prompt TEXT NOT NULL,
  domain VARCHAR(50) DEFAULT 'development',
  ollama_model VARCHAR(50) DEFAULT 'deepseek-r1:8b',
  enhancement_type VARCHAR(50),
  quality_improvement DECIMAL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- React component analysis results
CREATE TABLE component_analysis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  component_name VARCHAR(100) NOT NULL,
  file_path TEXT,
  analysis_type VARCHAR(50), -- 'onboarding', 'performance', 'accessibility'
  recommendations JSONB,
  ollama_insights JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### **7. Environment Configuration**

Create `.env.local` file:

```bash
# Supabase Configuration
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_KEY=your-service-key-here

# MCP Server Integration
MCP_DATABASE_TYPE=supabase
MCP_SUPABASE_ENABLED=true

# Ollama Integration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=deepseek-r1:8b
```

### **8. Advanced Features Setup**

#### **Real-time Subscriptions**
```typescript
// Monitor onboarding progress in real-time
const subscription = supabase
  .channel('onboarding_updates')
  .on('postgres_changes', {
    event: 'UPDATE',
    schema: 'public',
    table: 'user_onboarding'
  }, (payload) => {
    console.log('Onboarding progress updated:', payload);
  })
  .subscribe();
```

#### **Database Functions**
```sql
-- AI-powered prompt enhancement function
CREATE OR REPLACE FUNCTION enhance_prompt_with_context(
  prompt_text TEXT,
  domain_context TEXT DEFAULT 'development'
)
RETURNS TABLE(enhanced_prompt TEXT, confidence_score DECIMAL)
LANGUAGE plpgsql
AS $$
BEGIN
  -- Integration with Ollama via HTTP requests
  -- Enhanced prompt generation logic
  RETURN QUERY
  SELECT 
    enhanced_prompt_text,
    confidence_score_value
  FROM ai_enhancement_results
  WHERE original_prompt = prompt_text;
END;
$$;
```

### **9. VS Code Workspace Configuration**

Add to `.vscode/settings.json`:

```json
{
  "supabase.projectId": "your-project-id",
  "supabase.localDevelopment": true,
  "supabase.enableCopilotIntegration": true,
  "mcp.servers": {
    "sequential-think-supabase": {
      "type": "stdio", 
      "command": "python",
      "args": ["sequential_think_mcp_server.py", "--database", "supabase"],
      "env": {
        "SUPABASE_URL": "http://localhost:54321",
        "SUPABASE_SERVICE_KEY": "${env:SUPABASE_SERVICE_KEY}"
      }
    }
  }
}
```

### **10. Testing Your Setup**

After setup, verify everything works:

```bash
# Check Supabase status
supabase status

# Expected output:
# API URL: http://localhost:54321
# GraphQL URL: http://localhost:54321/graphql/v1
# DB URL: postgresql://postgres:postgres@localhost:54322/postgres
# Studio URL: http://localhost:54323
# Inbucket URL: http://localhost:54324
# JWT secret: your-jwt-secret
# anon key: your-anon-key
# service_role key: your-service-key
```

### **11. Integration Benefits**

With this setup, you'll have:

✅ **Enhanced MCP Server**: Database-backed prompt storage and retrieval  
✅ **AI-Powered Migrations**: Copilot-assisted database schema changes  
✅ **Real-time Analytics**: Live onboarding progress tracking  
✅ **Type-Safe Operations**: Full TypeScript integration  
✅ **Local Development**: No cloud dependencies during development  
✅ **Scalable Architecture**: Ready for production deployment  

### **12. Next Steps**

1. **Initialize Project**: Run `supabase init` in your workspace
2. **Start Development**: Run `supabase start`
3. **Install VS Code Extension**: Search "Supabase" in Extensions
4. **Configure MCP Integration**: Update your MCP server configuration
5. **Test Integration**: Verify database connectivity and Copilot features

Your Supabase integration will dramatically enhance your Sequential Think MCP Server with production-grade database capabilities and AI-powered development tools! 🚀
