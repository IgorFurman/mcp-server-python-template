const natural = require('natural');
const fs = require('fs-extra');
const SystemPromptParser = require('./parser');

/**
 * SystemPromptAnalyzer - Analyzes and categorizes system prompt components
 */
class SystemPromptAnalyzer {
  constructor() {
    this.tokenizer = new natural.WordTokenizer();
    this.stemmer = natural.PorterStemmer;
    
    // Define prompt component categories and their keywords
    this.categories = {
      personality: {
        keywords: ['friendly', 'helpful', 'professional', 'casual', 'formal', 'empathetic', 'curious', 'patient', 'direct', 'conversational', 'warm', 'engaging'],
        patterns: [/personality/i, /tone/i, /character/i, /persona/i, /behave/i]
      },
      capabilities: {
        keywords: ['can', 'able', 'capable', 'skills', 'functions', 'features', 'tools', 'analyze', 'generate', 'create', 'process', 'understand'],
        patterns: [/can do/i, /able to/i, /capabilities/i, /functions/i, /features/i]
      },
      limitations: {
        keywords: ['cannot', 'unable', 'limit', 'restriction', 'avoid', 'refrain', 'prevent', 'prohibited', 'forbidden', 'not allowed'],
        patterns: [/cannot/i, /unable to/i, /limitations/i, /restrictions/i, /not.*able/i]
      },
      safety: {
        keywords: ['safe', 'harmful', 'dangerous', 'inappropriate', 'offensive', 'toxic', 'abuse', 'violence', 'illegal', 'unethical'],
        patterns: [/safety/i, /harmful/i, /dangerous/i, /inappropriate/i, /guidelines/i, /policy/i]
      },
      interaction_style: {
        keywords: ['respond', 'answer', 'reply', 'communicate', 'engage', 'conversation', 'dialogue', 'ask', 'question', 'follow-up'],
        patterns: [/when.*ask/i, /should.*respond/i, /interaction/i, /communication/i, /conversation/i]
      },
      knowledge: {
        keywords: ['know', 'knowledge', 'information', 'data', 'facts', 'cutoff', 'training', 'learned', 'database', 'search'],
        patterns: [/knowledge/i, /cutoff/i, /training.*data/i, /information/i, /database/i]
      },
      formatting: {
        keywords: ['format', 'structure', 'markdown', 'code', 'list', 'bullet', 'heading', 'paragraph', 'citation'],
        patterns: [/format/i, /markdown/i, /structure/i, /code.*block/i, /citation/i]
      },
      identity: {
        keywords: ['assistant', 'ai', 'model', 'created', 'developed', 'anthropic', 'openai', 'claude', 'gpt', 'chatbot'],
        patterns: [/i am/i, /created by/i, /developed by/i, /assistant/i, /model/i]
      }
    };
  }

  /**
   * Analyze a collection of system prompts
   * @param {Array} prompts - Array of parsed prompt objects
   * @returns {Object} Analysis results
   */
  analyzePrompts(prompts) {
    const results = {
      individual: prompts.map(prompt => this.analyzePrompt(prompt)),
      aggregate: this.aggregateAnalysis(prompts),
      patterns: this.findPatterns(prompts),
      evolution: this.analyzeEvolution(prompts)
    };

    return results;
  }

  /**
   * Analyze a single system prompt
   * @param {Object} prompt - Parsed prompt object
   * @returns {Object} Analysis result for single prompt
   */
  analyzePrompt(prompt) {
    if (!prompt.systemPrompt) {
      return {
        filename: prompt.filename,
        error: 'No system prompt content found'
      };
    }

    const text = prompt.systemPrompt.toLowerCase();
    const tokens = this.tokenizer.tokenize(text);
    const sentences = this.extractSentences(prompt.systemPrompt);

    return {
      filename: prompt.filename,
      metadata: prompt.metadata,
      wordCount: prompt.wordCount,
      sentenceCount: sentences.length,
      avgWordsPerSentence: Math.round(prompt.wordCount / sentences.length),
      categories: this.categorizeContent(text, sentences),
      sentiment: this.analyzeSentiment(text),
      complexity: this.analyzeComplexity(text, tokens),
      directives: this.extractDirectives(sentences),
      keyPhrases: this.extractKeyPhrases(tokens),
      structure: this.analyzeStructure(prompt.systemPrompt)
    };
  }

  /**
   * Categorize prompt content into different components
   * @param {string} text - Lowercase prompt text
   * @param {Array} sentences - Array of sentences
   * @returns {Object} Categorization results
   */
  categorizeContent(text, sentences) {
    const results = {};

    for (const [category, config] of Object.entries(this.categories)) {
      let score = 0;
      const matchedKeywords = [];
      const matchedSentences = [];

      // Check keywords
      for (const keyword of config.keywords) {
        if (text.includes(keyword)) {
          score += 1;
          matchedKeywords.push(keyword);
        }
      }

      // Check patterns
      for (const pattern of config.patterns) {
        const matches = text.match(pattern);
        if (matches) {
          score += 2; // Patterns get higher weight
        }
      }

      // Find relevant sentences
      for (const sentence of sentences) {
        const sentenceLower = sentence.toLowerCase();
        const hasKeyword = config.keywords.some(kw => sentenceLower.includes(kw));
        const hasPattern = config.patterns.some(pattern => pattern.test(sentence));
        
        if (hasKeyword || hasPattern) {
          matchedSentences.push(sentence.trim());
        }
      }

      results[category] = {
        score,
        relevance: score > 0 ? Math.min(score / 5, 1) : 0, // Normalize to 0-1
        keywords: matchedKeywords,
        sentences: matchedSentences.slice(0, 3) // Top 3 relevant sentences
      };
    }

    return results;
  }

  /**
   * Extract sentences from text
   * @param {string} text - Input text
   * @returns {Array} Array of sentences
   */
  extractSentences(text) {
    return text
      .split(/[.!?]+/)
      .map(s => s.trim())
      .filter(s => s.length > 10); // Filter out very short fragments
  }

  /**
   * Analyze sentiment of the prompt
   * @param {string} text - Input text
   * @returns {Object} Sentiment analysis
   */
  analyzeSentiment(text) {
    const analyzer = new natural.SentimentAnalyzer('English', 
      natural.PorterStemmer, 'afinn');
    const tokens = this.tokenizer.tokenize(text);
    const score = analyzer.getSentiment(tokens);

    return {
      score,
      classification: score > 0.1 ? 'positive' : score < -0.1 ? 'negative' : 'neutral'
    };
  }

  /**
   * Analyze text complexity
   * @param {string} text - Input text
   * @param {Array} tokens - Tokenized text
   * @returns {Object} Complexity metrics
   */
  analyzeComplexity(text, tokens) {
    const sentences = this.extractSentences(text);
    const avgSentenceLength = sentences.reduce((sum, s) => sum + s.split(' ').length, 0) / sentences.length;
    const uniqueWords = new Set(tokens.map(t => this.stemmer.stem(t))).size;
    const lexicalDiversity = uniqueWords / tokens.length;

    return {
      avgSentenceLength: Math.round(avgSentenceLength),
      lexicalDiversity: Math.round(lexicalDiversity * 100) / 100,
      complexity: avgSentenceLength > 20 || lexicalDiversity > 0.7 ? 'high' : 
                 avgSentenceLength > 15 || lexicalDiversity > 0.5 ? 'medium' : 'low'
    };
  }

  /**
   * Extract directive statements (commands/instructions)
   * @param {Array} sentences - Array of sentences
   * @returns {Array} Array of directive sentences
   */
  extractDirectives(sentences) {
    const directivePatterns = [
      /^(always|never|should|must|will|when|if)/i,
      /(do not|don't|avoid|ensure|make sure)/i,
      /(respond|answer|provide|generate|create)/i
    ];

    return sentences
      .filter(sentence => 
        directivePatterns.some(pattern => pattern.test(sentence))
      )
      .slice(0, 10); // Top 10 directives
  }

  /**
   * Extract key phrases using TF-IDF
   * @param {Array} tokens - Tokenized text
   * @returns {Array} Array of key phrases with scores
   */
  extractKeyPhrases(tokens) {
    const tfidf = new natural.TfIdf();
    tfidf.addDocument(tokens);

    const phrases = [];
    tfidf.listTerms(0).slice(0, 20).forEach(item => {
      if (item.term.length > 3) { // Filter out very short terms
        phrases.push({
          term: item.term,
          score: Math.round(item.tfidf * 100) / 100
        });
      }
    });

    return phrases;
  }

  /**
   * Analyze prompt structure
   * @param {string} text - Original prompt text
   * @returns {Object} Structure analysis
   */
  analyzeStructure(text) {
    const lines = text.split('\n');
    const bulletPoints = lines.filter(line => line.trim().match(/^[-*•]/)).length;
    const numberedLists = lines.filter(line => line.trim().match(/^\d+\./)).length;
    const headings = lines.filter(line => line.trim().match(/^#+/)).length;
    const paragraphs = text.split(/\n\s*\n/).length;

    return {
      totalLines: lines.length,
      bulletPoints,
      numberedLists,
      headings,
      paragraphs,
      hasStructure: bulletPoints > 0 || numberedLists > 0 || headings > 0
    };
  }

  /**
   * Aggregate analysis across all prompts
   * @param {Array} prompts - Array of parsed prompt objects
   * @returns {Object} Aggregate analysis
   */
  aggregateAnalysis(prompts) {
    const validPrompts = prompts.filter(p => p.systemPrompt);
    
    const categoryScores = {};
    const services = {};
    const totalWords = validPrompts.reduce((sum, p) => sum + p.wordCount, 0);

    // Initialize category aggregation
    Object.keys(this.categories).forEach(cat => {
      categoryScores[cat] = { total: 0, count: 0, prompts: [] };
    });

    // Analyze each prompt and aggregate
    validPrompts.forEach(prompt => {
      const analysis = this.analyzePrompt(prompt);
      
      // Aggregate by service
      const service = prompt.metadata.service;
      if (!services[service]) {
        services[service] = { count: 0, totalWords: 0, categories: {} };
      }
      services[service].count++;
      services[service].totalWords += prompt.wordCount;

      // Aggregate categories
      Object.entries(analysis.categories).forEach(([cat, data]) => {
        categoryScores[cat].total += data.score;
        categoryScores[cat].count++;
        if (data.score > 0) {
          categoryScores[cat].prompts.push(prompt.filename);
        }

        if (!services[service].categories[cat]) {
          services[service].categories[cat] = 0;
        }
        services[service].categories[cat] += data.score;
      });
    });

    // Calculate averages
    Object.keys(categoryScores).forEach(cat => {
      categoryScores[cat].average = categoryScores[cat].count > 0 ? 
        Math.round((categoryScores[cat].total / categoryScores[cat].count) * 100) / 100 : 0;
    });

    return {
      totalPrompts: validPrompts.length,
      totalWords,
      avgWordsPerPrompt: Math.round(totalWords / validPrompts.length),
      categoryScores,
      serviceBreakdown: services
    };
  }

  /**
   * Find common patterns across prompts
   * @param {Array} prompts - Array of parsed prompt objects
   * @returns {Object} Pattern analysis
   */
  findPatterns(prompts) {
    const validPrompts = prompts.filter(p => p.systemPrompt);
    const commonPhrases = new Map();
    const commonDirectives = new Map();

    validPrompts.forEach(prompt => {
      const analysis = this.analyzePrompt(prompt);
      
      // Track common key phrases
      analysis.keyPhrases.forEach(phrase => {
        const key = phrase.term;
        commonPhrases.set(key, (commonPhrases.get(key) || 0) + 1);
      });

      // Track common directives
      analysis.directives.forEach(directive => {
        const key = directive.toLowerCase().trim();
        if (key.length > 20) { // Only track substantial directives
          commonDirectives.set(key, (commonDirectives.get(key) || 0) + 1);
        }
      });
    });

    // Sort and filter common patterns
    const topPhrases = Array.from(commonPhrases.entries())
      .filter(([phrase, count]) => count > 1)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20);

    const topDirectives = Array.from(commonDirectives.entries())
      .filter(([directive, count]) => count > 1)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);

    return {
      commonPhrases: topPhrases,
      commonDirectives: topDirectives
    };
  }

  /**
   * Analyze evolution of prompts over time
   * @param {Array} prompts - Array of parsed prompt objects
   * @returns {Object} Evolution analysis
   */
  analyzeEvolution(prompts) {
    const datedPrompts = prompts
      .filter(p => p.metadata.date && p.systemPrompt)
      .sort((a, b) => a.metadata.date - b.metadata.date);

    if (datedPrompts.length < 2) {
      return { error: 'Insufficient dated prompts for evolution analysis' };
    }

    const evolution = {
      timespan: {
        start: datedPrompts[0].metadata.date,
        end: datedPrompts[datedPrompts.length - 1].metadata.date
      },
      trends: {},
      wordCountTrend: this.analyzeTrend(datedPrompts.map(p => p.wordCount)),
      serviceEvolution: {}
    };

    // Analyze category trends over time
    Object.keys(this.categories).forEach(category => {
      const scores = datedPrompts.map(prompt => {
        const analysis = this.analyzePrompt(prompt);
        return analysis.categories[category].score;
      });
      evolution.trends[category] = this.analyzeTrend(scores);
    });

    return evolution;
  }

  /**
   * Analyze trend in a series of values
   * @param {Array} values - Array of numeric values
   * @returns {Object} Trend analysis
   */
  analyzeTrend(values) {
    if (values.length < 2) return { trend: 'insufficient_data' };

    const first = values.slice(0, Math.ceil(values.length / 3)).reduce((a, b) => a + b, 0) / Math.ceil(values.length / 3);
    const last = values.slice(-Math.ceil(values.length / 3)).reduce((a, b) => a + b, 0) / Math.ceil(values.length / 3);
    
    const change = ((last - first) / first) * 100;
    
    return {
      trend: Math.abs(change) < 5 ? 'stable' : change > 0 ? 'increasing' : 'decreasing',
      changePercent: Math.round(change * 100) / 100,
      firstThirdAvg: Math.round(first * 100) / 100,
      lastThirdAvg: Math.round(last * 100) / 100
    };
  }
}

module.exports = SystemPromptAnalyzer;

// CLI usage
if (require.main === module) {
  async function runAnalysis() {
    try {
      // Parse prompts first
      const parser = new SystemPromptParser(__dirname + '/..');
      const prompts = await parser.parseAll();
      
      console.log(`\nAnalyzing ${prompts.length} system prompts...`);
      
      // Analyze prompts
      const analyzer = new SystemPromptAnalyzer();
      const analysis = analyzer.analyzePrompts(prompts);
      
      // Create data directory
      await fs.ensureDir(__dirname + '/../data');
      
      // Save analysis results
      await fs.writeJson(__dirname + '/../data/analysis-results.json', analysis, { spaces: 2 });
      
      console.log('\nAnalysis Summary:');
      console.log('================');
      console.log(`Total Prompts Analyzed: ${analysis.aggregate.totalPrompts}`);
      console.log(`Total Words: ${analysis.aggregate.totalWords}`);
      console.log(`Average Words per Prompt: ${analysis.aggregate.avgWordsPerPrompt}`);
      
      console.log('\nTop Categories by Average Score:');
      const sortedCategories = Object.entries(analysis.aggregate.categoryScores)
        .sort((a, b) => b[1].average - a[1].average)
        .slice(0, 5);
      
      sortedCategories.forEach(([category, data]) => {
        console.log(`  ${category}: ${data.average} (found in ${data.prompts.length} prompts)`);
      });
      
      console.log('\nService Breakdown:');
      Object.entries(analysis.aggregate.serviceBreakdown).forEach(([service, data]) => {
        console.log(`  ${service}: ${data.count} prompts, avg ${Math.round(data.totalWords / data.count)} words`);
      });
      
      console.log('\nAnalysis complete! Results saved to data/analysis-results.json');
      
    } catch (error) {
      console.error('Analysis failed:', error);
    }
  }

  runAnalysis();
}