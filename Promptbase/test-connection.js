#!/usr/bin/env node

import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'

// Load environment variables
dotenv.config()

const supabaseUrl = process.env.SUPABASE_URL
const supabaseKey = process.env.SUPABASE_ANON_KEY

console.log('🔗 Testing Supabase connection...')
console.log('📍 URL:', supabaseUrl)
console.log('🔑 Key:', supabaseKey ? `${supabaseKey.substring(0, 20)}...` : 'Not found')

if (!supabaseUrl || !supabaseKey) {
  console.error('❌ Missing Supabase credentials in .env file')
  process.exit(1)
}

// Create client
const supabase = createClient(supabaseUrl, supabaseKey)

async function testConnection() {
  try {
    // Test basic connection
    console.log('\n🧪 Testing basic connection...')
    const { data, error } = await supabase.auth.getSession()

    if (error) {
      console.error('❌ Connection error:', error.message)
      return false
    }

    console.log('✅ Successfully connected to Supabase!')
    console.log('👤 Current session:', data.session ? 'Authenticated' : 'Anonymous')

    // Test if we can access the database (this will fail if tables don't exist yet)
    console.log('\n🗄️  Testing database access...')
    const { data: tables, error: dbError } = await supabase
      .from('prompts')
      .select('id')
      .limit(1)

    if (dbError) {
      if (dbError.code === '42P01') {
        console.log('ℹ️  Database schema not yet created (this is expected for new setup)')
        console.log('📝 Next step: Run the schema.sql file in your Supabase dashboard')
      } else {
        console.error('❌ Database error:', dbError.message)
      }
    } else {
      console.log('✅ Database is accessible!')
      console.log('📊 Sample query successful')
    }

    return true

  } catch (error) {
    console.error('❌ Unexpected error:', error.message)
    return false
  }
}

// Run the test
testConnection().then(success => {
  if (success) {
    console.log('\n🎉 Connection test completed!')
    console.log('\n📋 Next steps:')
    console.log('1. Copy the contents of supabase/schema.sql')
    console.log('2. Go to your Supabase dashboard > SQL Editor')
    console.log('3. Paste and run the schema to create tables')
    console.log('4. Then run: npm run sync')
  } else {
    console.log('\n❌ Connection test failed')
    process.exit(1)
  }
})
