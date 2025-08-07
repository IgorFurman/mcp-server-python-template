#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

/**
 * Script to convert system prompt files from base/ directory to prompts.csv format
 * Usage: node convert-base-to-csv.js
 */

const BASE_DIR = './base';
const OUTPUT_FILE = './prompts.csv';
const BACKUP_FILE = './prompts.csv.backup';

// CSV header
const CSV_HEADER = 'act,prompt,for_devs\n';

/**
 * Extract system prompt content from markdown file
 */
function extractSystemPrompt(content, filename) {
    // Remove markdown headers and metadata
    let cleaned = content
        .replace(/^#[^#\n]*$/gm, '') // Remove H1 headers
        .replace(/^##[^#\n]*$/gm, '') // Remove H2 headers  
        .replace(/^source:\s*<[^>]+>/gm, '') // Remove source lines
        .replace(/^source:\s*\[.*?\]\(.*?\)/gm, '') // Remove source markdown links
        .replace(/^\s*\n/gm, '') // Remove empty lines
        .trim();

    // Try to find content between ## System Prompt and next ## header
    const systemPromptMatch = cleaned.match(/## System Prompt\s*\n([\s\S]*?)(?=\n##|\n#|$)/i);
    if (systemPromptMatch) {
        return systemPromptMatch[1].trim();
    }

    // Try to find content in specific XML-like tags
    const xmlTagMatch = cleaned.match(/<[^>]+>([\s\S]*?)<\/[^>]+>/);
    if (xmlTagMatch) {
        return xmlTagMatch[1].trim();
    }

    // Try to find the main content block (skip source and headers)
    const lines = cleaned.split('\n');
    const contentLines = lines.filter(line => 
        !line.startsWith('source:') && 
        !line.startsWith('#') && 
        !line.startsWith('##') &&
        line.trim().length > 0
    );

    if (contentLines.length > 0) {
        return contentLines.join('\n').trim();
    }

    // Fallback: return cleaned content
    return cleaned;
}

/**
 * Generate a proper act name from filename
 */
function generateActName(filename) {
    const baseName = path.basename(filename, '.md');
    
    // Parse service-model_date format
    const parts = baseName.split('_');
    if (parts.length >= 2) {
        const serviceModel = parts[0];
        const date = parts[1];
        
        // Clean up service name
        const cleanService = serviceModel
            .replace(/-/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase())
            .replace(/\./g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
        
        return `${cleanService} System Prompt`;
    }
    
    // Fallback formatting
    return baseName
        .replace(/-/g, ' ')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase())
        .replace(/\s+/g, ' ')
        .trim() + ' System Prompt';
}

/**
 * Check if this is a developer-oriented system prompt
 */
function isForDevs(content, filename) {
    const devKeywords = [
        'code', 'programming', 'developer', 'api', 'function', 'method',
        'class', 'variable', 'debug', 'compile', 'execute', 'script',
        'json', 'xml', 'html', 'css', 'javascript', 'python', 'java',
        'github', 'git', 'repository', 'commit', 'branch', 'merge',
        'database', 'sql', 'query', 'server', 'client', 'framework',
        'library', 'package', 'module', 'import', 'export', 'syntax'
    ];
    
    const lowerContent = content.toLowerCase();
    const lowerFilename = filename.toLowerCase();
    
    // Check filename for dev-related terms
    if (devKeywords.some(keyword => lowerFilename.includes(keyword))) {
        return true;
    }
    
    // Count dev-related keywords in content
    const devKeywordCount = devKeywords.filter(keyword => 
        lowerContent.includes(keyword)
    ).length;
    
    // If more than 3 dev keywords found, consider it dev-oriented
    return devKeywordCount >= 3;
}

/**
 * Escape CSV field content
 */
function escapeCsvField(field) {
    if (typeof field !== 'string') {
        field = String(field);
    }
    
    // Replace any existing double quotes with double double quotes
    field = field.replace(/"/g, '""');
    
    // Wrap in quotes if contains comma, newline, or quote
    if (field.includes(',') || field.includes('\n') || field.includes('"')) {
        field = `"${field}"`;
    }
    
    return field;
}

/**
 * Main conversion function
 */
function convertBaseToCsv() {
    console.log('Starting conversion from base/ directory to prompts.csv...');
    
    // Check if base directory exists
    if (!fs.existsSync(BASE_DIR)) {
        console.error('Error: base/ directory not found');
        process.exit(1);
    }
    
    // Backup existing prompts.csv if it exists
    if (fs.existsSync(OUTPUT_FILE)) {
        fs.copyFileSync(OUTPUT_FILE, BACKUP_FILE);
        console.log(`Backed up existing prompts.csv to ${BACKUP_FILE}`);
    }
    
    // Read all .md files from base directory
    const files = fs.readdirSync(BASE_DIR).filter(file => 
        file.endsWith('.md') && 
        !file.includes('README') && 
        !file.includes('CLAUDE')
    );
    
    console.log(`Found ${files.length} markdown files to process`);
    
    // Process each file
    const csvRows = [CSV_HEADER];
    let processedCount = 0;
    let skippedCount = 0;
    
    for (const file of files) {
        try {
            const filePath = path.join(BASE_DIR, file);
            const content = fs.readFileSync(filePath, 'utf-8');
            
            // Skip very short files (likely incomplete)
            if (content.trim().length < 100) {
                console.log(`Skipping ${file} (too short)`);
                skippedCount++;
                continue;
            }
            
            // Extract system prompt
            const prompt = extractSystemPrompt(content, file);
            
            if (!prompt || prompt.length < 50) {
                console.log(`Skipping ${file} (no valid prompt found)`);
                skippedCount++;
                continue;
            }
            
            // Generate act name
            const actName = generateActName(file);
            
            // Determine if for developers
            const forDevs = isForDevs(prompt, file);
            
            // Create CSV row
            const csvRow = `${escapeCsvField(actName)},${escapeCsvField(prompt)},${forDevs}\n`;
            csvRows.push(csvRow);
            
            console.log(`Processed: ${file} -> "${actName}" (${forDevs ? 'DEV' : 'GENERAL'})`);
            processedCount++;
            
        } catch (error) {
            console.error(`Error processing ${file}:`, error.message);
            skippedCount++;
        }
    }
    
    // Write to CSV file
    try {
        fs.writeFileSync(OUTPUT_FILE, csvRows.join(''));
        console.log(`\nConversion complete!`);
        console.log(`Summary:`);
        console.log(`   - Processed: ${processedCount} files`);
        console.log(`   - Skipped: ${skippedCount} files`);
        console.log(`   - Output: ${OUTPUT_FILE}`);
        console.log(`   - Backup: ${BACKUP_FILE} (if applicable)`);
        
    } catch (error) {
        console.error('Error writing CSV file:', error.message);
        process.exit(1);
    }
}

// Run the conversion
if (require.main === module) {
    convertBaseToCsv();
}

module.exports = { 
    convertBaseToCsv, 
    extractSystemPrompt, 
    generateActName, 
    isForDevs, 
    escapeCsvField 
};