const fs = require('fs-extra');
const path = require('path');
const { marked } = require('marked');

/**
 * SystemPromptParser - Extracts and parses system prompts from markdown files
 */
class SystemPromptParser {
  constructor(rootDir) {
    this.rootDir = rootDir;
    this.prompts = [];
  }

  /**
   * Parse all markdown files in the repository
   * @returns {Promise<Array>} Array of parsed prompt objects
   */
  async parseAll() {
    const files = await this.getMarkdownFiles();
    console.log(`Found ${files.length} markdown files to parse`);

    for (const file of files) {
      try {
        const promptData = await this.parseFile(file);
        if (promptData) {
          this.prompts.push(promptData);
        }
      } catch (error) {
        console.error(`Error parsing ${file}:`, error.message);
      }
    }

    return this.prompts;
  }

  /**
   * Get all markdown files in the repository
   * @returns {Promise<Array>} Array of file paths
   */
  async getMarkdownFiles() {
    const files = await fs.readdir(this.rootDir);
    return files
      .filter(file => file.endsWith('.md') && file !== 'README.md' && file !== 'CLAUDE.md')
      .map(file => path.join(this.rootDir, file));
  }

  /**
   * Parse a single markdown file
   * @param {string} filePath - Path to the markdown file
   * @returns {Promise<Object>} Parsed prompt data
   */
  async parseFile(filePath) {
    const content = await fs.readFile(filePath, 'utf-8');
    const filename = path.basename(filePath, '.md');
    
    // Extract metadata from filename (service-model_date.md format)
    const metadata = this.parseFilename(filename);
    
    // Extract source URL if present
    const source = this.extractSource(content);
    
    // Extract system prompt content
    const systemPrompt = this.extractSystemPrompt(content);
    
    // Extract additional sections
    const sections = this.extractSections(content);

    return {
      filename,
      filepath: filePath,
      metadata,
      source,
      systemPrompt,
      sections,
      wordCount: systemPrompt ? systemPrompt.split(/\s+/).length : 0,
      lastModified: (await fs.stat(filePath)).mtime,
      raw: content
    };
  }

  /**
   * Parse filename to extract service, model, and date information
   * @param {string} filename - The filename without extension
   * @returns {Object} Metadata object
   */
  parseFilename(filename) {
    // Pattern: service-model_YYYYMMDD or variations
    const patterns = [
      /^([^_]+)_(\d{8})$/,  // service_YYYYMMDD
      /^([^-]+)-([^_]+)_(\d{8})$/,  // service-model_YYYYMMDD
      /^([^-]+)-([^_]+)-([^_]+)_(\d{8})$/  // service-model-version_YYYYMMDD
    ];

    for (const pattern of patterns) {
      const match = filename.match(pattern);
      if (match) {
        if (match.length === 3) {
          return {
            service: match[1],
            model: null,
            version: null,
            date: this.parseDate(match[2])
          };
        } else if (match.length === 4) {
          return {
            service: match[1],
            model: match[2],
            version: null,
            date: this.parseDate(match[3])
          };
        } else if (match.length === 5) {
          return {
            service: match[1],
            model: match[2],
            version: match[3],
            date: this.parseDate(match[4])
          };
        }
      }
    }

    // Fallback parsing
    const parts = filename.split(/[-_]/);
    return {
      service: parts[0] || 'unknown',
      model: parts[1] || null,
      version: parts[2] || null,
      date: parts[parts.length - 1] ? this.parseDate(parts[parts.length - 1]) : null
    };
  }

  /**
   * Parse date string YYYYMMDD to Date object
   * @param {string} dateStr - Date string in YYYYMMDD format
   * @returns {Date|null} Parsed date or null if invalid
   */
  parseDate(dateStr) {
    if (!/^\d{8}$/.test(dateStr)) return null;
    
    const year = parseInt(dateStr.substr(0, 4));
    const month = parseInt(dateStr.substr(4, 2)) - 1; // Month is 0-indexed
    const day = parseInt(dateStr.substr(6, 2));
    
    return new Date(year, month, day);
  }

  /**
   * Extract source URL from markdown content
   * @param {string} content - Markdown content
   * @returns {string|null} Source URL or null if not found
   */
  extractSource(content) {
    const lines = content.split('\n');
    for (const line of lines.slice(0, 10)) { // Check first 10 lines
      const match = line.match(/source:\s*<?(https?:\/\/[^>\s]+)>?/i);
      if (match) {
        return match[1];
      }
    }
    return null;
  }

  /**
   * Extract system prompt content from markdown
   * @param {string} content - Markdown content
   * @returns {string|null} System prompt text or null if not found
   */
  extractSystemPrompt(content) {
    // Look for common system prompt indicators
    const patterns = [
      /## System Prompt\s*\n\n([\s\S]*?)(?=\n##|\n#|$)/i,
      /# System Prompt\s*\n\n([\s\S]*?)(?=\n##|\n#|$)/i,
      /System Prompt:\s*\n\n([\s\S]*?)(?=\n##|\n#|$)/i,
      /---\s*\n\n([\s\S]*?)(?=\n##|\n#|$)/i, // Content after metadata separator
    ];

    for (const pattern of patterns) {
      const match = content.match(pattern);
      if (match && match[1]) {
        return match[1].trim();
      }
    }

    // If no specific section found, try to extract main content after metadata
    const lines = content.split('\n');
    let startIndex = 0;
    
    // Skip metadata and headers
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].includes('source:') || lines[i].startsWith('#') || lines[i] === '---') {
        continue;
      }
      if (lines[i].trim() && !lines[i].startsWith('##') && !lines[i].startsWith('#')) {
        startIndex = i;
        break;
      }
    }

    if (startIndex > 0) {
      return lines.slice(startIndex).join('\n').trim();
    }

    return null;
  }

  /**
   * Extract all sections from markdown content
   * @param {string} content - Markdown content
   * @returns {Object} Object with section titles as keys and content as values
   */
  extractSections(content) {
    const sections = {};
    const tokens = marked.lexer(content);
    
    let currentSection = null;
    let currentContent = [];

    for (const token of tokens) {
      if (token.type === 'heading') {
        // Save previous section
        if (currentSection) {
          sections[currentSection] = currentContent.join('\n').trim();
        }
        
        // Start new section
        currentSection = token.text;
        currentContent = [];
      } else if (currentSection) {
        // Add content to current section
        if (token.raw) {
          currentContent.push(token.raw);
        }
      }
    }

    // Save final section
    if (currentSection) {
      sections[currentSection] = currentContent.join('\n').trim();
    }

    return sections;
  }

  /**
   * Get statistics about parsed prompts
   * @returns {Object} Statistics object
   */
  getStats() {
    if (this.prompts.length === 0) return null;

    const services = [...new Set(this.prompts.map(p => p.metadata.service))];
    const models = [...new Set(this.prompts.map(p => p.metadata.model).filter(Boolean))];
    const totalWords = this.prompts.reduce((sum, p) => sum + p.wordCount, 0);
    const avgWords = Math.round(totalWords / this.prompts.length);

    // Date range
    const dates = this.prompts
      .map(p => p.metadata.date)
      .filter(Boolean)
      .sort((a, b) => a - b);

    return {
      totalPrompts: this.prompts.length,
      services: services.length,
      models: models.length,
      totalWords,
      avgWords,
      dateRange: dates.length > 0 ? {
        earliest: dates[0],
        latest: dates[dates.length - 1]
      } : null,
      servicesList: services,
      modelsList: models
    };
  }

  /**
   * Save parsed data to JSON file
   * @param {string} outputPath - Path to save the JSON file
   */
  async saveToJson(outputPath) {
    const data = {
      timestamp: new Date().toISOString(),
      stats: this.getStats(),
      prompts: this.prompts
    };

    await fs.writeJson(outputPath, data, { spaces: 2 });
    console.log(`Saved parsed data to: ${outputPath}`);
  }
}

module.exports = SystemPromptParser;

// CLI usage
if (require.main === module) {
  const parser = new SystemPromptParser(__dirname + '/..');
  
  parser.parseAll()
    .then(() => {
      console.log('\nParsing complete!');
      console.log('Statistics:', parser.getStats());
      
      // Save to JSON file
      return parser.saveToJson(path.join(__dirname, '../data/parsed-prompts.json'));
    })
    .catch(console.error);
}