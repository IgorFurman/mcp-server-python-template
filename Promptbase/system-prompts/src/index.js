const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs-extra');
const { program } = require('commander');

const SystemPromptParser = require('./parser');
const SystemPromptAnalyzer = require('./analyzer');
const SystemPromptComparator = require('./comparator');

/**
 * System Prompt Research API Server
 */
class SystemPromptServer {
  constructor(port = 3001) {
    this.app = express();
    this.port = port;
    this.setupMiddleware();
    this.setupRoutes();
    this.data = {
      prompts: [],
      analysis: null,
      comparisons: {}
    };
  }

  setupMiddleware() {
    this.app.use(cors());
    this.app.use(express.json());
    this.app.use(express.static(path.join(__dirname, '../public')));
  }

  setupRoutes() {
    // Health check
    this.app.get('/api/health', (req, res) => {
      res.json({ status: 'healthy', timestamp: new Date().toISOString() });
    });

    // Get all prompts
    this.app.get('/api/prompts', (req, res) => {
      const { service, model, limit = 50, offset = 0 } = req.query;
      
      let filteredPrompts = this.data.prompts;
      
      if (service) {
        filteredPrompts = filteredPrompts.filter(p => 
          p.metadata.service.toLowerCase().includes(service.toLowerCase())
        );
      }
      
      if (model) {
        filteredPrompts = filteredPrompts.filter(p => 
          p.metadata.model && p.metadata.model.toLowerCase().includes(model.toLowerCase())
        );
      }

      const total = filteredPrompts.length;
      const paginatedPrompts = filteredPrompts
        .slice(parseInt(offset), parseInt(offset) + parseInt(limit));

      res.json({
        prompts: paginatedPrompts,
        pagination: {
          total,
          limit: parseInt(limit),
          offset: parseInt(offset),
          hasMore: parseInt(offset) + parseInt(limit) < total
        }
      });
    });

    // Get specific prompt
    this.app.get('/api/prompts/:filename', (req, res) => {
      const prompt = this.data.prompts.find(p => p.filename === req.params.filename);
      if (!prompt) {
        return res.status(404).json({ error: 'Prompt not found' });
      }
      res.json(prompt);
    });

    // Get analysis results
    this.app.get('/api/analysis', (req, res) => {
      if (!this.data.analysis) {
        return res.status(404).json({ error: 'Analysis not available' });
      }
      res.json(this.data.analysis);
    });

    // Get analysis for specific prompt
    this.app.get('/api/analysis/:filename', (req, res) => {
      if (!this.data.analysis || !this.data.analysis.individual) {
        return res.status(404).json({ error: 'Analysis not available' });
      }

      const analysis = this.data.analysis.individual.find(a => a.filename === req.params.filename);
      if (!analysis) {
        return res.status(404).json({ error: 'Analysis not found for this prompt' });
      }

      res.json(analysis);
    });

    // Compare two prompts
    this.app.post('/api/compare', async (req, res) => {
      try {
        const { filenameA, filenameB } = req.body;
        
        if (!filenameA || !filenameB) {
          return res.status(400).json({ error: 'Both filenameA and filenameB required' });
        }

        const promptA = this.data.prompts.find(p => p.filename === filenameA);
        const promptB = this.data.prompts.find(p => p.filename === filenameB);

        if (!promptA || !promptB) {
          return res.status(404).json({ error: 'One or both prompts not found' });
        }

        const comparisonKey = `${filenameA}_vs_${filenameB}`;
        
        if (!this.data.comparisons[comparisonKey]) {
          const comparator = new SystemPromptComparator();
          this.data.comparisons[comparisonKey] = comparator.comparePrompts(promptA, promptB);
        }

        res.json(this.data.comparisons[comparisonKey]);
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });

    // Get evolution analysis for a service
    this.app.get('/api/evolution/:service', async (req, res) => {
      try {
        const service = req.params.service.toLowerCase();
        const servicePrompts = this.data.prompts
          .filter(p => p.metadata.service.toLowerCase().includes(service))
          .filter(p => p.metadata.date)
          .sort((a, b) => a.metadata.date - b.metadata.date);

        if (servicePrompts.length < 2) {
          return res.status(404).json({ error: 'Insufficient prompts for evolution analysis' });
        }

        const comparator = new SystemPromptComparator();
        const evolution = comparator.analyzeEvolution(servicePrompts);

        res.json(evolution);
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });

    // Search prompts
    this.app.get('/api/search', (req, res) => {
      const { q, category, minWords, maxWords } = req.query;
      
      if (!q) {
        return res.status(400).json({ error: 'Query parameter q is required' });
      }

      let results = this.data.prompts.filter(prompt => {
        if (!prompt.systemPrompt) return false;
        
        const searchText = `${prompt.filename} ${prompt.systemPrompt} ${JSON.stringify(prompt.metadata)}`.toLowerCase();
        const queryMatch = searchText.includes(q.toLowerCase());
        
        if (!queryMatch) return false;

        if (minWords && prompt.wordCount < parseInt(minWords)) return false;
        if (maxWords && prompt.wordCount > parseInt(maxWords)) return false;

        return true;
      });

      // If category filter is specified, also check analysis data
      if (category && this.data.analysis && this.data.analysis.individual) {
        results = results.filter(prompt => {
          const analysis = this.data.analysis.individual.find(a => a.filename === prompt.filename);
          return analysis && analysis.categories[category] && analysis.categories[category].score > 0;
        });
      }

      res.json({
        query: q,
        results: results.slice(0, 50), // Limit to 50 results
        total: results.length
      });
    });

    // Get statistics
    this.app.get('/api/stats', (req, res) => {
      const parser = new SystemPromptParser();
      parser.prompts = this.data.prompts;
      const stats = parser.getStats();
      
      // Add analysis stats if available
      if (this.data.analysis) {
        stats.analysis = {
          categoriesAnalyzed: Object.keys(this.data.analysis.aggregate.categoryScores).length,
          topCategory: Object.entries(this.data.analysis.aggregate.categoryScores)
            .sort((a, b) => b[1].average - a[1].average)[0]
        };
      }

      res.json(stats);
    });

    // Trigger re-analysis
    this.app.post('/api/reanalyze', async (req, res) => {
      try {
        await this.loadAndAnalyzeData();
        res.json({ message: 'Reanalysis completed', timestamp: new Date().toISOString() });
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });

    // Serve React app for any non-API routes
    this.app.get('*', (req, res) => {
      res.sendFile(path.join(__dirname, '../public/index.html'));
    });
  }

  async loadAndAnalyzeData() {
    console.log('Loading and analyzing system prompts...');
    
    try {
      // Parse all prompts
      const parser = new SystemPromptParser(__dirname + '/..');
      this.data.prompts = await parser.parseAll();
      console.log(`Loaded ${this.data.prompts.length} prompts`);

      // Analyze prompts
      const analyzer = new SystemPromptAnalyzer();
      this.data.analysis = analyzer.analyzePrompts(this.data.prompts);
      console.log('Analysis completed');

      // Save data to files
      await fs.ensureDir(__dirname + '/../data');
      await fs.writeJson(__dirname + '/../data/prompts.json', this.data.prompts, { spaces: 2 });
      await fs.writeJson(__dirname + '/../data/analysis.json', this.data.analysis, { spaces: 2 });

      return true;
    } catch (error) {
      console.error('Error loading and analyzing data:', error);
      throw error;
    }
  }

  async start() {
    try {
      // Load data on startup
      await this.loadAndAnalyzeData();
      
      this.app.listen(this.port, () => {
        console.log(`\n🚀 System Prompt Research Server running on http://localhost:${this.port}`);
        console.log(`📊 API available at http://localhost:${this.port}/api/`);
        console.log(`🔍 Loaded ${this.data.prompts.length} system prompts for analysis\n`);
        
        console.log('Available endpoints:');
        console.log('  GET  /api/prompts           - List all prompts');
        console.log('  GET  /api/prompts/:filename - Get specific prompt');
        console.log('  GET  /api/analysis          - Get analysis results');
        console.log('  POST /api/compare           - Compare two prompts');
        console.log('  GET  /api/evolution/:service - Get evolution analysis');
        console.log('  GET  /api/search            - Search prompts');
        console.log('  GET  /api/stats             - Get statistics');
        console.log('  POST /api/reanalyze         - Trigger reanalysis');
      });
    } catch (error) {
      console.error('Failed to start server:', error);
      process.exit(1);
    }
  }
}

// CLI Commands
program
  .name('system-prompt-analyzer')
  .description('System Prompt Analysis and Research Tool')
  .version('1.0.0');

program
  .command('parse')
  .description('Parse all system prompt files')
  .action(async () => {
    const parser = new SystemPromptParser(__dirname + '/..');
    const prompts = await parser.parseAll();
    console.log('Parsing Results:');
    console.log(parser.getStats());
    await parser.saveToJson(__dirname + '/../data/parsed-prompts.json');
  });

program
  .command('analyze')
  .description('Analyze all system prompts')
  .action(async () => {
    const parser = new SystemPromptParser(__dirname + '/..');
    const prompts = await parser.parseAll();
    
    const analyzer = new SystemPromptAnalyzer();
    const analysis = analyzer.analyzePrompts(prompts);
    
    console.log('Analysis Results:');
    console.log(`Total Prompts: ${analysis.aggregate.totalPrompts}`);
    console.log(`Average Words: ${analysis.aggregate.avgWordsPerPrompt}`);
    
    await fs.writeJson(__dirname + '/../data/analysis-results.json', analysis, { spaces: 2 });
  });

program
  .command('compare <fileA> <fileB>')
  .description('Compare two specific prompt files')
  .action(async (fileA, fileB) => {
    const parser = new SystemPromptParser(__dirname + '/..');
    const prompts = await parser.parseAll();
    
    const promptA = prompts.find(p => p.filename === fileA);
    const promptB = prompts.find(p => p.filename === fileB);
    
    if (!promptA || !promptB) {
      console.error('One or both files not found');
      return;
    }
    
    const comparator = new SystemPromptComparator();
    const comparison = comparator.comparePrompts(promptA, promptB);
    
    console.log('Comparison Results:');
    console.log(`Similarity: ${comparison.similarity.overall} (${comparison.similarity.classification})`);
    console.log(`Length difference: ${comparison.lengthComparison.difference} words`);
    
    await fs.writeJson(__dirname + `/../data/comparison-${fileA}-vs-${fileB}.json`, comparison, { spaces: 2 });
  });

program
  .command('serve')
  .description('Start the web server')
  .option('-p, --port <port>', 'Port to run server on', '3001')
  .action(async (options) => {
    const server = new SystemPromptServer(parseInt(options.port));
    await server.start();
  });

// Add missing dependencies to package.json
const addDependencies = async () => {
  const packagePath = path.join(__dirname, '../package.json');
  const packageJson = await fs.readJson(packagePath);
  
  // Add missing dependencies
  packageJson.dependencies = {
    ...packageJson.dependencies,
    'express': '^4.18.2',
    'cors': '^2.8.5'
  };
  
  await fs.writeJson(packagePath, packageJson, { spaces: 2 });
};

if (require.main === module) {
  addDependencies().then(() => {
    program.parse();
  });
}

module.exports = { SystemPromptServer, SystemPromptParser, SystemPromptAnalyzer, SystemPromptComparator };