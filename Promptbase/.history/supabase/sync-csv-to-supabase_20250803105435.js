#!/usr/bin/env node

import { createClient } from '@supabase/supabase-js'
import csv from 'csv-parser'
import dotenv from 'dotenv'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

// Load environment variables
dotenv.config()

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

/**
 * Sync CSV files to Supabase
 * Usage: node sync-csv-to-supabase.js [--dry-run] [--batch-size=100] [--file=prompts.csv]
 */

// Configuration
const SUPABASE_URL = process.env.SUPABASE_URL
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY // Service role key for admin operations

if (!SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
  console.error('❌ Missing required environment variables:')
  console.error('   SUPABASE_URL - Your Supabase project URL')
  console.error('   SUPABASE_SERVICE_KEY - Your Supabase service role key')
  process.exit(1)
}

// Create Supabase client with service role key
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY)

// Parse command line arguments
const args = process.argv.slice(2)
const isDryRun = args.includes('--dry-run')
const batchSize = parseInt(args.find(arg => arg.startsWith('--batch-size='))?.split('=')[1]) || 100
const targetFile = args.find(arg => arg.startsWith('--file='))?.split('=')[1] || null

// File paths
const ROOT_DIR = path.join(__dirname, '..')
const FILES_TO_SYNC = {
  prompts: path.join(ROOT_DIR, 'prompts.csv'),
  vibePrompts: path.join(ROOT_DIR, 'vibeprompts.csv'),
  systemPrompts: path.join(ROOT_DIR, 'base')
}

/**
 * Utility functions
 */
const utils = {
  // Parse CSV file
  parseCsv: (filePath) => {
    return new Promise((resolve, reject) => {
      const results = []
      fs.createReadStream(filePath)
        .pipe(csv())
        .on('data', (data) => results.push(data))
        .on('end', () => resolve(results))
        .on('error', reject)
    })
  },

  // Process data in batches
  processBatches: async (data, batchSize, processor) => {
    const results = []
    for (let i = 0; i < data.length; i += batchSize) {
      const batch = data.slice(i, i + batchSize)
      const batchResult = await processor(batch, i)
      results.push(...batchResult)
    }
    return results
  },

  // Clean and validate data
  cleanString: (str) => {
    if (!str) return null
    return str.trim().replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  },

  // Parse boolean values
  parseBoolean: (value) => {
    if (typeof value === 'boolean') return value
    if (typeof value === 'string') {
      return value.toLowerCase() === 'true' || value === '1' || value === 'yes'
    }
    return false
  },

  // Parse array values
  parseArray: (value, delimiter = ',') => {
    if (!value) return []
    if (Array.isArray(value)) return value
    return value.split(delimiter).map(item => item.trim()).filter(Boolean)
  },

  // Generate UUID
  generateUuid: () => {
    return crypto.randomUUID()
  }
}

/**
 * Data transformers
 */
const transformers = {
  // Transform prompts.csv data
  transformPrompts: (csvData) => {
    return csvData.map(row => ({
      id: utils.generateUuid(),
      act: utils.cleanString(row.act),
      prompt: utils.cleanString(row.prompt),
      category: 'general', // Default category
      type: 'chatgpt',
      for_devs: utils.parseBoolean(row.for_devs),
      contributor: utils.cleanString(row.contributor) || null,
      techstack: row.techstack ? utils.parseArray(row.techstack) : [],
      tags: row.tags ? utils.parseArray(row.tags) : [],
      is_public: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })).filter(item => item.act && item.prompt)
  },

  // Transform vibeprompts.csv data
  transformVibePrompts: (csvData) => {
    return csvData.map(row => ({
      id: utils.generateUuid(),
      app_name: utils.cleanString(row.app),
      description: utils.cleanString(row.prompt),
      contributor: utils.cleanString(row.contributor) || null,
      techstack: row.techstack ? utils.parseArray(row.techstack) : [],
      difficulty: 'intermediate', // Default difficulty
      estimated_time: null,
      features: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })).filter(item => item.app_name && item.description)
  },

  // Transform system prompts from base/ directory
  transformSystemPrompts: (filePath, content) => {
    const filename = path.basename(filePath)
    const nameMatch = filename.match(/^([^_]+)(?:_([^_]+))?(?:_(\d{8}))?\.md$/)

    if (!nameMatch) return null

    const [, serviceName, modelName, dateStr] = nameMatch
    let versionDate = null

    if (dateStr) {
      const year = dateStr.substring(0, 4)
      const month = dateStr.substring(4, 6)
      const day = dateStr.substring(6, 8)
      versionDate = `${year}-${month}-${day}`
    }

    // Extract source URL from content
    const sourceMatch = content.match(/source:\s*<([^>]+)>|source:\s*\[.*?\]\(([^)]+)\)/i)
    const sourceUrl = sourceMatch ? (sourceMatch[1] || sourceMatch[2]) : null

    // Extract system prompt content
    let systemPrompt = content
    const systemPromptMatch = content.match(/## System Prompt\s*\n([\s\S]*?)(?=\n##|\n#|$)/i)
    if (systemPromptMatch) {
      systemPrompt = systemPromptMatch[1].trim()
    }

    return {
      id: utils.generateUuid(),
      service_name: serviceName.replace(/-/g, ' '),
      model_name: modelName ? modelName.replace(/-/g, ' ') : null,
      version_date: versionDate,
      filename: filename,
      system_prompt: utils.cleanString(systemPrompt),
      source_url: sourceUrl,
      is_verified: !!sourceUrl,
      metadata: {
        file_size: content.length,
        word_count: content.split(/\s+/).length
      },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
  }
}

/**
 * Sync functions
 */
const syncFunctions = {
  // Sync prompts.csv
  syncPrompts: async () => {
    console.log('📋 Syncing prompts.csv...')

    if (!fs.existsSync(FILES_TO_SYNC.prompts)) {
      console.log('⚠️  prompts.csv not found, skipping...')
      return { synced: 0, errors: 0 }
    }

    try {
      const csvData = await utils.parseCsv(FILES_TO_SYNC.prompts)
      const transformedData = transformers.transformPrompts(csvData)

      console.log(`📊 Found ${transformedData.length} prompts to sync`)

      if (isDryRun) {
        console.log('🔍 Dry run - would sync:', transformedData.slice(0, 3))
        return { synced: transformedData.length, errors: 0 }
      }

      // Clear existing data
      const { error: deleteError } = await supabase
        .from('prompts')
        .delete()
        .neq('id', '00000000-0000-0000-0000-000000000000') // Delete all

      if (deleteError) {
        console.error('❌ Error clearing prompts table:', deleteError)
      }

      // Insert in batches
      let synced = 0
      let errors = 0

      await utils.processBatches(transformedData, batchSize, async (batch, offset) => {
        const { data, error } = await supabase
          .from('prompts')
          .insert(batch)

        if (error) {
          console.error(`❌ Error inserting batch ${offset}-${offset + batch.length}:`, error)
          errors += batch.length
          return []
        } else {
          synced += batch.length
          console.log(`✅ Synced batch ${offset}-${offset + batch.length}`)
          return data || []
        }
      })

      return { synced, errors }
    } catch (error) {
      console.error('❌ Error syncing prompts:', error)
      return { synced: 0, errors: 1 }
    }
  },

  // Sync vibeprompts.csv
  syncVibePrompts: async () => {
    console.log('🎨 Syncing vibeprompts.csv...')

    if (!fs.existsSync(FILES_TO_SYNC.vibePrompts)) {
      console.log('⚠️  vibeprompts.csv not found, skipping...')
      return { synced: 0, errors: 0 }
    }

    try {
      const csvData = await utils.parseCsv(FILES_TO_SYNC.vibePrompts)
      const transformedData = transformers.transformVibePrompts(csvData)

      console.log(`📊 Found ${transformedData.length} vibe prompts to sync`)

      if (isDryRun) {
        console.log('🔍 Dry run - would sync:', transformedData.slice(0, 3))
        return { synced: transformedData.length, errors: 0 }
      }

      // Clear existing data
      const { error: deleteError } = await supabase
        .from('app_prompts')
        .delete()
        .neq('id', '00000000-0000-0000-0000-000000000000') // Delete all

      if (deleteError) {
        console.error('❌ Error clearing app_prompts table:', deleteError)
      }

      // Insert in batches
      let synced = 0
      let errors = 0

      await utils.processBatches(transformedData, batchSize, async (batch, offset) => {
        const { data, error } = await supabase
          .from('app_prompts')
          .insert(batch)

        if (error) {
          console.error(`❌ Error inserting batch ${offset}-${offset + batch.length}:`, error)
          errors += batch.length
          return []
        } else {
          synced += batch.length
          console.log(`✅ Synced batch ${offset}-${offset + batch.length}`)
          return data || []
        }
      })

      return { synced, errors }
    } catch (error) {
      console.error('❌ Error syncing vibe prompts:', error)
      return { synced: 0, errors: 1 }
    }
  },

  // Sync system prompts from base/ directory
  syncSystemPrompts: async () => {
    console.log('🔧 Syncing system prompts from base/ directory...')

    if (!fs.existsSync(FILES_TO_SYNC.systemPrompts)) {
      console.log('⚠️  base/ directory not found, skipping...')
      return { synced: 0, errors: 0 }
    }

    try {
      const files = fs.readdirSync(FILES_TO_SYNC.systemPrompts)
        .filter(file => file.endsWith('.md') && !file.includes('README') && !file.includes('CLAUDE'))

      console.log(`📊 Found ${files.length} system prompt files to sync`)

      const transformedData = []

      for (const file of files) {
        const filePath = path.join(FILES_TO_SYNC.systemPrompts, file)
        const content = fs.readFileSync(filePath, 'utf-8')

        const transformed = transformers.transformSystemPrompts(filePath, content)
        if (transformed && transformed.system_prompt && transformed.system_prompt.length > 50) {
          transformedData.push(transformed)
        }
      }

      console.log(`📊 Processed ${transformedData.length} valid system prompts`)

      if (isDryRun) {
        console.log('🔍 Dry run - would sync:', transformedData.slice(0, 3))
        return { synced: transformedData.length, errors: 0 }
      }

      // Clear existing data
      const { error: deleteError } = await supabase
        .from('system_prompts')
        .delete()
        .neq('id', '00000000-0000-0000-0000-000000000000') // Delete all

      if (deleteError) {
        console.error('❌ Error clearing system_prompts table:', deleteError)
      }

      // Insert in batches
      let synced = 0
      let errors = 0

      await utils.processBatches(transformedData, batchSize, async (batch, offset) => {
        const { data, error } = await supabase
          .from('system_prompts')
          .insert(batch)

        if (error) {
          console.error(`❌ Error inserting batch ${offset}-${offset + batch.length}:`, error)
          errors += batch.length
          return []
        } else {
          synced += batch.length
          console.log(`✅ Synced batch ${offset}-${offset + batch.length}`)
          return data || []
        }
      })

      return { synced, errors }
    } catch (error) {
      console.error('❌ Error syncing system prompts:', error)
      return { synced: 0, errors: 1 }
    }
  }
}

/**
 * Main sync function
 */
async function main() {
  console.log('🚀 Starting CSV to Supabase sync...')
  console.log(`📋 Mode: ${isDryRun ? 'DRY RUN' : 'LIVE SYNC'}`)
  console.log(`📦 Batch size: ${batchSize}`)

  if (targetFile) {
    console.log(`🎯 Target file: ${targetFile}`)
  }

  console.log('─'.repeat(60))

  const results = {
    prompts: { synced: 0, errors: 0 },
    vibePrompts: { synced: 0, errors: 0 },
    systemPrompts: { synced: 0, errors: 0 }
  }

  try {
    // Sync based on target file or sync all
    if (!targetFile || targetFile === 'prompts.csv') {
      results.prompts = await syncFunctions.syncPrompts()
    }

    if (!targetFile || targetFile === 'vibeprompts.csv') {
      results.vibePrompts = await syncFunctions.syncVibePrompts()
    }

    if (!targetFile || targetFile === 'base') {
      results.systemPrompts = await syncFunctions.syncSystemPrompts()
    }

  } catch (error) {
    console.error('❌ Sync failed:', error)
    process.exit(1)
  }

  // Summary
  console.log('─'.repeat(60))
  console.log('📊 SYNC SUMMARY:')
  console.log(`📋 Prompts: ${results.prompts.synced} synced, ${results.prompts.errors} errors`)
  console.log(`🎨 Vibe Prompts: ${results.vibePrompts.synced} synced, ${results.vibePrompts.errors} errors`)
  console.log(`🔧 System Prompts: ${results.systemPrompts.synced} synced, ${results.systemPrompts.errors} errors`)

  const totalSynced = results.prompts.synced + results.vibePrompts.synced + results.systemPrompts.synced
  const totalErrors = results.prompts.errors + results.vibePrompts.errors + results.systemPrompts.errors

  console.log(`📈 TOTAL: ${totalSynced} synced, ${totalErrors} errors`)

  if (totalErrors === 0) {
    console.log('✅ Sync completed successfully!')
  } else {
    console.log('⚠️  Sync completed with errors. Check the logs above.')
  }
}

// Handle command line execution
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error)
}

export default {
  syncFunctions,
  transformers,
  utils
}
