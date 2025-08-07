const natural = require('natural');
const fs = require('fs-extra');

/**
 * SystemPromptEnhancer - Provides suggestions for improving system prompts
 */
class SystemPromptEnhancer {
  constructor() {
    this.tokenizer = new natural.WordTokenizer();
    
    // Best practice patterns identified from high-quality prompts
    this.bestPractices = {
      clarity: {
        patterns: [
          /clearly/i, /specific/i, /detailed/i, /precise/i, /explicit/i
        ],
        suggestions: [
          "Use specific, concrete language instead of vague terms",
          "Define key concepts and terms explicitly",
          "Provide clear examples of desired behavior"
        ]
      },
      
      structure: {
        patterns: [
          /##?\s+/g, /\*\s+/g, /\d+\.\s+/g, /\n\n/g
        ],
        suggestions: [
          "Use headers to organize different sections",
          "Break long instructions into numbered lists",
          "Separate different types of instructions with clear formatting"
        ]
      },
      
      personality: {
        patterns: [
          /helpful/i, /friendly/i, /professional/i, /tone/i, /personality/i
        ],
        suggestions: [
          "Define the AI's personality and communication style",
          "Specify the appropriate tone for different situations",
          "Include examples of how the AI should interact with users"
        ]
      },
      
      safety: {
        patterns: [
          /harmful/i, /dangerous/i, /inappropriate/i, /avoid/i, /refuse/i, /safety/i
        ],
        suggestions: [
          "Include clear safety guidelines and restrictions",
          "Specify what types of content or requests to avoid",
          "Define how to handle potentially harmful requests"
        ]
      },
      
      capabilities: {
        patterns: [
          /can/i, /ability/i, /capable/i, /function/i, /feature/i
        ],
        suggestions: [
          "Clearly describe what the AI can and cannot do",
          "List specific capabilities and tools available",
          "Set appropriate expectations for performance"
        ]
      },
      
      examples: {
        patterns: [
          /example/i, /instance/i, /such as/i, /like/i, /including/i
        ],
        suggestions: [
          "Provide concrete examples of good responses",
          "Include examples of how to handle edge cases",
          "Show examples of proper formatting and structure"
        ]
      }
    };

    // Quality metrics and scoring
    this.qualityMetrics = {
      length: { min: 200, optimal: 800, max: 2000 },
      sentences: { min: 10, optimal: 30, max: 100 },
      structure: { minSections: 3, optimalSections: 6 },
      clarity: { minExamples: 1, optimalExamples: 3 }
    };
  }

  /**
   * Analyze a prompt and provide enhancement suggestions
   * @param {Object} prompt - Parsed prompt object
   * @param {Object} analysis - Analysis results for the prompt
   * @returns {Object} Enhancement suggestions
   */
  analyzeAndSuggest(prompt, analysis) {
    if (!prompt.systemPrompt) {
      return { error: 'No system prompt content found' };
    }

    const suggestions = {
      filename: prompt.filename,
      overallScore: 0,
      suggestions: [],
      improvements: {
        structure: [],
        content: [],
        clarity: [],
        completeness: []
      },
      strengths: [],
      metrics: this.calculateMetrics(prompt, analysis)
    };

    // Analyze different aspects
    this.analyzeStructure(prompt, suggestions);
    this.analyzeContent(prompt, analysis, suggestions);
    this.analyzeClarity(prompt, suggestions);
    this.analyzeCompleteness(prompt, analysis, suggestions);
    this.identifyStrengths(prompt, analysis, suggestions);

    // Calculate overall score
    suggestions.overallScore = this.calculateOverallScore(suggestions.metrics);

    return suggestions;
  }

  /**
   * Calculate various metrics for the prompt
   * @param {Object} prompt - Parsed prompt object
   * @param {Object} analysis - Analysis results
   * @returns {Object} Calculated metrics
   */
  calculateMetrics(prompt, analysis) {
    const text = prompt.systemPrompt;
    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 10);
    
    return {
      wordCount: prompt.wordCount,
      sentenceCount: sentences.length,
      avgSentenceLength: Math.round(prompt.wordCount / sentences.length),
      structure: this.analyzeStructureMetrics(text),
      readability: this.calculateReadability(text),
      categories: analysis ? this.calculateCategoryScore(analysis.categories) : null
    };
  }

  /**
   * Analyze structure metrics
   * @param {string} text - Prompt text
   * @returns {Object} Structure metrics
   */
  analyzeStructureMetrics(text) {
    const lines = text.split('\n');
    const headers = lines.filter(line => line.trim().match(/^#+/)).length;
    const bulletPoints = lines.filter(line => line.trim().match(/^[-*•]/)).length;
    const numberedLists = lines.filter(line => line.trim().match(/^\d+\./)).length;
    const paragraphs = text.split(/\n\s*\n/).length;

    return {
      headers,
      bulletPoints,
      numberedLists,
      paragraphs,
      hasGoodStructure: headers > 0 || bulletPoints > 3 || numberedLists > 3
    };
  }

  /**
   * Calculate readability score (simplified Flesch Reading Ease)
   * @param {string} text - Input text
   * @returns {number} Readability score
   */
  calculateReadability(text) {
    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 10);
    const words = this.tokenizer.tokenize(text);
    const syllables = words.reduce((sum, word) => sum + this.countSyllables(word), 0);

    if (sentences.length === 0 || words.length === 0) return 0;

    const avgSentenceLength = words.length / sentences.length;
    const avgSyllablesPerWord = syllables / words.length;

    // Simplified Flesch Reading Ease formula
    const score = 206.835 - (1.015 * avgSentenceLength) - (84.6 * avgSyllablesPerWord);
    return Math.max(0, Math.min(100, score));
  }

  /**
   * Count syllables in a word (approximation)
   * @param {string} word - Input word
   * @returns {number} Estimated syllable count
   */
  countSyllables(word) {
    if (!word || word.length === 0) return 0;
    
    word = word.toLowerCase();
    let count = 0;
    let previousWasVowel = false;
    
    for (let i = 0; i < word.length; i++) {
      const isVowel = /[aeiouy]/.test(word[i]);
      if (isVowel && !previousWasVowel) {
        count++;
      }
      previousWasVowel = isVowel;
    }
    
    // Handle silent e
    if (word.endsWith('e')) count--;
    
    return Math.max(1, count);
  }

  /**
   * Calculate category coverage score
   * @param {Object} categories - Category analysis results
   * @returns {Object} Category score breakdown
   */
  calculateCategoryScore(categories) {
    const importantCategories = ['personality', 'capabilities', 'safety', 'limitations'];
    const scores = {};
    let totalScore = 0;
    let coveredCategories = 0;

    for (const category of importantCategories) {
      if (categories[category]) {
        scores[category] = categories[category].score;
        totalScore += categories[category].score;
        if (categories[category].score > 0) coveredCategories++;
      } else {
        scores[category] = 0;
      }
    }

    return {
      individual: scores,
      average: totalScore / importantCategories.length,
      coverage: coveredCategories / importantCategories.length,
      totalScore
    };
  }

  /**
   * Analyze prompt structure and suggest improvements
   * @param {Object} prompt - Parsed prompt object
   * @param {Object} suggestions - Suggestions object to modify
   */
  analyzeStructure(prompt, suggestions) {
    const text = prompt.systemPrompt;
    const metrics = suggestions.metrics.structure;

    // Check for headers
    if (metrics.headers === 0) {
      suggestions.improvements.structure.push({
        type: 'headers',
        priority: 'high',
        issue: 'No section headers found',
        suggestion: 'Add headers like "## Personality", "## Capabilities", "## Guidelines" to organize content',
        example: '## Core Instructions\n\n## Interaction Style\n\n## Safety Guidelines'
      });
    }

    // Check for lists
    if (metrics.bulletPoints === 0 && metrics.numberedLists === 0) {
      suggestions.improvements.structure.push({
        type: 'lists',
        priority: 'medium',
        issue: 'No lists or bullet points found',
        suggestion: 'Break down complex instructions into numbered lists or bullet points',
        example: '1. Always be helpful and accurate\n2. Provide detailed explanations\n3. Ask clarifying questions when needed'
      });
    }

    // Check paragraph structure
    if (metrics.paragraphs < 3) {
      suggestions.improvements.structure.push({
        type: 'paragraphs',
        priority: 'medium',
        issue: 'Very few paragraph breaks',
        suggestion: 'Break long text into smaller paragraphs for better readability',
        example: 'Use double line breaks to separate different topics or instructions'
      });
    }

    // Check overall structure
    if (!metrics.hasGoodStructure) {
      suggestions.improvements.structure.push({
        type: 'overall',
        priority: 'high',
        issue: 'Poor overall structure',
        suggestion: 'Organize content with clear sections, headers, and formatting',
        example: 'Use a consistent structure: Introduction → Core Instructions → Examples → Limitations'
      });
    }
  }

  /**
   * Analyze content and suggest improvements
   * @param {Object} prompt - Parsed prompt object
   * @param {Object} analysis - Analysis results
   * @param {Object} suggestions - Suggestions object to modify
   */
  analyzeContent(prompt, analysis, suggestions) {
    const text = prompt.systemPrompt.toLowerCase();

    // Check for essential categories
    if (analysis && analysis.categories) {
      const categoryScores = suggestions.metrics.categories;
      
      if (categoryScores.individual.personality < 1) {
        suggestions.improvements.content.push({
          type: 'personality',
          priority: 'high',
          issue: 'No clear personality definition',
          suggestion: 'Define the AI\'s personality, tone, and communication style',
          example: 'You are a helpful, friendly, and professional assistant. Always maintain a warm but professional tone.'
        });
      }

      if (categoryScores.individual.capabilities < 1) {
        suggestions.improvements.content.push({
          type: 'capabilities',
          priority: 'high',
          issue: 'Capabilities not clearly defined',
          suggestion: 'Explicitly state what the AI can and cannot do',
          example: 'You can: analyze text, answer questions, provide explanations. You cannot: browse the internet, remember past conversations.'
        });
      }

      if (categoryScores.individual.safety < 1) {
        suggestions.improvements.content.push({
          type: 'safety',
          priority: 'high',
          issue: 'Missing safety guidelines',
          suggestion: 'Include safety restrictions and guidelines for handling sensitive content',
          example: 'Do not provide information that could be harmful, illegal, or unethical. Refuse requests for dangerous activities.'
        });
      }

      if (categoryScores.individual.limitations < 1) {
        suggestions.improvements.content.push({
          type: 'limitations',
          priority: 'medium',
          issue: 'Limitations not specified',
          suggestion: 'Clearly state the AI\'s limitations and boundaries',
          example: 'I cannot access real-time information, remember previous conversations, or perform actions outside this chat.'
        });
      }
    }

    // Check for examples
    if (!text.includes('example') && !text.includes('instance') && !text.includes('such as')) {
      suggestions.improvements.content.push({
        type: 'examples',
        priority: 'medium',
        issue: 'No examples provided',
        suggestion: 'Include concrete examples of good responses or behavior',
        example: 'For example, when asked about a complex topic, provide: 1) A clear explanation, 2) Relevant examples, 3) Additional resources if helpful.'
      });
    }
  }

  /**
   * Analyze clarity and suggest improvements
   * @param {Object} prompt - Parsed prompt object
   * @param {Object} suggestions - Suggestions object to modify
   */
  analyzeClarity(prompt, suggestions) {
    const text = prompt.systemPrompt;
    const readability = suggestions.metrics.readability;

    // Check readability
    if (readability < 30) {
      suggestions.improvements.clarity.push({
        type: 'readability',
        priority: 'high',
        issue: 'Very difficult to read (complex sentences)',
        suggestion: 'Use shorter sentences and simpler language',
        example: 'Break long sentences into shorter ones. Use common words instead of complex terminology.'
      });
    } else if (readability < 50) {
      suggestions.improvements.clarity.push({
        type: 'readability',
        priority: 'medium',
        issue: 'Somewhat difficult to read',
        suggestion: 'Simplify sentence structure for better clarity',
        example: 'Use active voice and clear, direct language.'
      });
    }

    // Check for vague language
    const vagueTerms = ['things', 'stuff', 'various', 'etc', 'and so on', 'somewhat', 'kind of'];
    const foundVague = vagueTerms.filter(term => text.toLowerCase().includes(term));
    
    if (foundVague.length > 0) {
      suggestions.improvements.clarity.push({
        type: 'vague_language',
        priority: 'medium',
        issue: `Vague terms found: ${foundVague.join(', ')}`,
        suggestion: 'Replace vague terms with specific, concrete language',
        example: 'Instead of "various things", specify exactly what you mean: "questions, requests, and tasks"'
      });
    }

    // Check sentence length
    if (suggestions.metrics.avgSentenceLength > 25) {
      suggestions.improvements.clarity.push({
        type: 'sentence_length',
        priority: 'medium',
        issue: 'Average sentence length is very long',
        suggestion: 'Break long sentences into shorter, more digestible ones',
        example: 'Aim for 15-20 words per sentence on average. Use periods instead of commas to separate ideas.'
      });
    }
  }

  /**
   * Analyze completeness and suggest improvements
   * @param {Object} prompt - Parsed prompt object
   * @param {Object} analysis - Analysis results
   * @param {Object} suggestions - Suggestions object to modify
   */
  analyzeCompleteness(prompt, analysis, suggestions) {
    const text = prompt.systemPrompt.toLowerCase();
    const wordCount = prompt.wordCount;

    // Check length
    if (wordCount < this.qualityMetrics.length.min) {
      suggestions.improvements.completeness.push({
        type: 'length',
        priority: 'high',
        issue: `Prompt is too short (${wordCount} words)`,
        suggestion: `Expand to at least ${this.qualityMetrics.length.min} words for adequate guidance`,
        example: 'Add more specific instructions, examples, and guidelines to provide comprehensive direction.'
      });
    } else if (wordCount > this.qualityMetrics.length.max) {
      suggestions.improvements.completeness.push({
        type: 'length',
        priority: 'medium',
        issue: `Prompt is very long (${wordCount} words)`,
        suggestion: 'Consider condensing or organizing into sections for better digestibility',
        example: 'Break into focused sections or remove redundant information.'
      });
    }

    // Check for missing key elements
    const keyElements = {
      'role definition': ['you are', 'your role', 'acting as'],
      'interaction style': ['respond', 'answer', 'communicate', 'tone'],
      'output format': ['format', 'structure', 'organize', 'present'],
      'error handling': ['if unsure', 'when unclear', 'cannot', 'unable']
    };

    Object.entries(keyElements).forEach(([element, keywords]) => {
      const hasElement = keywords.some(keyword => text.includes(keyword));
      if (!hasElement) {
        suggestions.improvements.completeness.push({
          type: 'missing_element',
          priority: 'medium',
          issue: `Missing ${element}`,
          suggestion: `Add clear guidance about ${element}`,
          example: `Include instructions about ${element} to provide complete guidance.`
        });
      }
    });
  }

  /**
   * Identify strengths in the prompt
   * @param {Object} prompt - Parsed prompt object
   * @param {Object} analysis - Analysis results
   * @param {Object} suggestions - Suggestions object to modify
   */
  identifyStrengths(prompt, analysis, suggestions) {
    const text = prompt.systemPrompt.toLowerCase();
    const metrics = suggestions.metrics;

    // Good length
    if (prompt.wordCount >= this.qualityMetrics.length.min && 
        prompt.wordCount <= this.qualityMetrics.length.optimal) {
      suggestions.strengths.push('Well-balanced length - comprehensive without being overwhelming');
    }

    // Good structure
    if (metrics.structure.hasGoodStructure) {
      suggestions.strengths.push('Well-organized with clear structure and formatting');
    }

    // Good readability
    if (metrics.readability > 60) {
      suggestions.strengths.push('Highly readable and accessible language');
    } else if (metrics.readability > 40) {
      suggestions.strengths.push('Good readability with clear language');
    }

    // Category coverage
    if (analysis && analysis.categories && metrics.categories) {
      if (metrics.categories.coverage > 0.75) {
        suggestions.strengths.push('Excellent coverage of important prompt categories');
      } else if (metrics.categories.coverage > 0.5) {
        suggestions.strengths.push('Good coverage of essential prompt elements');
      }
    }

    // Specific strengths based on content
    if (text.includes('example')) {
      suggestions.strengths.push('Includes helpful examples for clarity');
    }

    if (text.includes('professional') || text.includes('helpful')) {
      suggestions.strengths.push('Clear personality and tone definition');
    }

    if (text.includes('cannot') || text.includes('avoid') || text.includes('refuse')) {
      suggestions.strengths.push('Includes appropriate limitations and safety measures');
    }
  }

  /**
   * Calculate overall quality score
   * @param {Object} metrics - Calculated metrics
   * @returns {number} Overall score (0-100)
   */
  calculateOverallScore(metrics) {
    let score = 0;
    let maxScore = 0;

    // Length score (20 points max)
    maxScore += 20;
    if (metrics.wordCount >= this.qualityMetrics.length.min) {
      if (metrics.wordCount <= this.qualityMetrics.length.optimal) {
        score += 20;
      } else if (metrics.wordCount <= this.qualityMetrics.length.max) {
        score += 15;
      } else {
        score += 10;
      }
    } else {
      score += Math.max(0, (metrics.wordCount / this.qualityMetrics.length.min) * 20);
    }

    // Structure score (25 points max)
    maxScore += 25;
    if (metrics.structure.hasGoodStructure) {
      score += 15;
      if (metrics.structure.headers > 0) score += 5;
      if (metrics.structure.bulletPoints > 0 || metrics.structure.numberedLists > 0) score += 5;
    }

    // Readability score (20 points max)
    maxScore += 20;
    score += Math.min(20, metrics.readability / 5);

    // Category coverage (25 points max)
    maxScore += 25;
    if (metrics.categories) {
      score += metrics.categories.coverage * 25;
    }

    // Sentence structure (10 points max)
    maxScore += 10;
    if (metrics.avgSentenceLength >= 10 && metrics.avgSentenceLength <= 20) {
      score += 10;
    } else {
      score += Math.max(0, 10 - Math.abs(metrics.avgSentenceLength - 15));
    }

    return Math.round((score / maxScore) * 100);
  }

  /**
   * Generate an enhanced version of the prompt
   * @param {Object} prompt - Original prompt object
   * @param {Object} suggestions - Enhancement suggestions
   * @returns {Object} Enhanced prompt with improvements
   */
  generateEnhancedPrompt(prompt, suggestions) {
    const originalText = prompt.systemPrompt;
    let enhancedText = originalText;

    // Apply structural improvements
    if (suggestions.improvements.structure.length > 0) {
      enhancedText = this.applyStructuralImprovements(enhancedText, suggestions.improvements.structure);
    }

    // Apply content improvements
    if (suggestions.improvements.content.length > 0) {
      enhancedText = this.applyContentImprovements(enhancedText, suggestions.improvements.content);
    }

    return {
      original: originalText,
      enhanced: enhancedText,
      improvements: suggestions.improvements,
      estimatedScoreImprovement: this.estimateScoreImprovement(suggestions)
    };
  }

  /**
   * Apply structural improvements to text
   * @param {string} text - Original text
   * @param {Array} improvements - Structural improvements
   * @returns {string} Improved text
   */
  applyStructuralImprovements(text, improvements) {
    let improved = text;

    improvements.forEach(improvement => {
      switch (improvement.type) {
        case 'headers':
          // Add basic headers if none exist
          improved = this.addBasicHeaders(improved);
          break;
        case 'paragraphs':
          // Add paragraph breaks
          improved = this.addParagraphBreaks(improved);
          break;
      }
    });

    return improved;
  }

  /**
   * Add basic headers to unstructured text
   * @param {string} text - Input text
   * @returns {string} Text with headers
   */
  addBasicHeaders(text) {
    // Simple heuristic to add headers
    const lines = text.split('\n');
    let result = [];
    let currentSection = '';

    lines.forEach(line => {
      if (line.trim().length === 0) {
        result.push(line);
        return;
      }

      // Detect potential section starts
      if (line.toLowerCase().includes('you are') || line.toLowerCase().includes('your role')) {
        if (currentSection !== 'role') {
          result.push('\n## Role Definition\n');
          currentSection = 'role';
        }
      } else if (line.toLowerCase().includes('respond') || line.toLowerCase().includes('answer')) {
        if (currentSection !== 'interaction') {
          result.push('\n## Interaction Guidelines\n');
          currentSection = 'interaction';
        }
      } else if (line.toLowerCase().includes('avoid') || line.toLowerCase().includes('never') || line.toLowerCase().includes('safety')) {
        if (currentSection !== 'safety') {
          result.push('\n## Safety Guidelines\n');
          currentSection = 'safety';
        }
      }

      result.push(line);
    });

    return result.join('\n');
  }

  /**
   * Add paragraph breaks to improve readability
   * @param {string} text - Input text
   * @returns {string} Text with better paragraph breaks
   */
  addParagraphBreaks(text) {
    // Add breaks after sentences that end with periods and are followed by capital letters
    return text.replace(/\. ([A-Z])/g, '.\n\n$1');
  }

  /**
   * Apply content improvements
   * @param {string} text - Original text
   * @param {Array} improvements - Content improvements
   * @returns {string} Improved text
   */
  applyContentImprovements(text, improvements) {
    let improved = text;

    improvements.forEach(improvement => {
      switch (improvement.type) {
        case 'personality':
          if (!improved.toLowerCase().includes('personality') && !improved.toLowerCase().includes('tone')) {
            improved = '## Personality and Tone\n\n' + improvement.example + '\n\n' + improved;
          }
          break;
        case 'capabilities':
          if (!improved.toLowerCase().includes('capabilit') && !improved.toLowerCase().includes('can do')) {
            improved += '\n\n## Capabilities\n\n' + improvement.example;
          }
          break;
        case 'safety':
          if (!improved.toLowerCase().includes('safety') && !improved.toLowerCase().includes('avoid')) {
            improved += '\n\n## Safety Guidelines\n\n' + improvement.example;
          }
          break;
      }
    });

    return improved;
  }

  /**
   * Estimate potential score improvement
   * @param {Object} suggestions - Enhancement suggestions
   * @returns {number} Estimated score improvement
   */
  estimateScoreImprovement(suggestions) {
    let improvement = 0;

    // High priority improvements
    const highPriorityCount = Object.values(suggestions.improvements)
      .flat()
      .filter(imp => imp.priority === 'high').length;
    
    improvement += highPriorityCount * 10;

    // Medium priority improvements
    const mediumPriorityCount = Object.values(suggestions.improvements)
      .flat()
      .filter(imp => imp.priority === 'medium').length;
    
    improvement += mediumPriorityCount * 5;

    return Math.min(improvement, 40); // Cap at 40 point improvement
  }
}

module.exports = SystemPromptEnhancer;

// CLI usage
if (require.main === module) {
  async function runEnhancement() {
    try {
      const SystemPromptParser = require('./parser');
      const SystemPromptAnalyzer = require('./analyzer');
      
      // Parse and analyze prompts
      const parser = new SystemPromptParser(__dirname + '/..');
      const prompts = await parser.parseAll();
      
      const analyzer = new SystemPromptAnalyzer();
      const analysis = analyzer.analyzePrompts(prompts);
      
      const enhancer = new SystemPromptEnhancer();
      const enhancements = [];

      console.log(`\nAnalyzing ${prompts.length} prompts for enhancement opportunities...\n`);

      // Analyze each prompt
      prompts.forEach(prompt => {
        const promptAnalysis = analysis.individual.find(a => a.filename === prompt.filename);
        if (promptAnalysis && !promptAnalysis.error) {
          const suggestions = enhancer.analyzeAndSuggest(prompt, promptAnalysis);
          enhancements.push(suggestions);
        }
      });

      // Sort by score (lowest first - most room for improvement)
      enhancements.sort((a, b) => a.overallScore - b.overallScore);

      console.log('Enhancement Results:');
      console.log('===================\n');

      // Show top 5 prompts with most room for improvement
      enhancements.slice(0, 5).forEach(enhancement => {
        console.log(`📄 ${enhancement.filename}`);
        console.log(`📊 Current Score: ${enhancement.overallScore}/100`);
        console.log(`💪 Strengths: ${enhancement.strengths.length}`);
        console.log(`🔧 Total Suggestions: ${Object.values(enhancement.improvements).flat().length}`);
        
        if (enhancement.improvements.structure.length > 0) {
          console.log(`   📋 Structure: ${enhancement.improvements.structure.length} suggestions`);
        }
        if (enhancement.improvements.content.length > 0) {
          console.log(`   📝 Content: ${enhancement.improvements.content.length} suggestions`);
        }
        if (enhancement.improvements.clarity.length > 0) {
          console.log(`   🔍 Clarity: ${enhancement.improvements.clarity.length} suggestions`);
        }
        if (enhancement.improvements.completeness.length > 0) {
          console.log(`   ✅ Completeness: ${enhancement.improvements.completeness.length} suggestions`);
        }
        
        console.log('');
      });

      // Save enhancement results
      await fs.ensureDir(__dirname + '/../data');
      await fs.writeJson(__dirname + '/../data/enhancement-suggestions.json', enhancements, { spaces: 2 });
      
      console.log(`✅ Enhancement analysis complete! Results saved to data/enhancement-suggestions.json`);

      // Show overall statistics
      const avgScore = enhancements.reduce((sum, e) => sum + e.overallScore, 0) / enhancements.length;
      const highScoring = enhancements.filter(e => e.overallScore >= 80).length;
      const needingImprovement = enhancements.filter(e => e.overallScore < 60).length;

      console.log('\nOverall Statistics:');
      console.log(`📊 Average Quality Score: ${Math.round(avgScore)}/100`);
      console.log(`⭐ High Quality Prompts (80+): ${highScoring}`);
      console.log(`🔧 Needing Improvement (<60): ${needingImprovement}`);

    } catch (error) {
      console.error('Enhancement analysis failed:', error);
    }
  }

  runEnhancement();
}