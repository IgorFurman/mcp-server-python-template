const natural = require("natural");
const fs = require("fs-extra");

/**
 * SystemPromptComparator - Compares and finds differences between system prompts
 */
class SystemPromptComparator {
  constructor() {
    this.tokenizer = new natural.WordTokenizer();
    this.stemmer = natural.PorterStemmer;
  }

  /**
   * Compare two system prompts
   * @param {Object} promptA - First prompt object
   * @param {Object} promptB - Second prompt object
   * @returns {Object} Comparison results
   */
  comparePrompts(promptA, promptB) {
    if (!promptA.systemPrompt || !promptB.systemPrompt) {
      return { error: "One or both prompts missing system prompt content" };
    }

    return {
      metadata: {
        promptA: {
          filename: promptA.filename,
          service: promptA.metadata.service,
          model: promptA.metadata.model,
          date: promptA.metadata.date,
          wordCount: promptA.wordCount,
        },
        promptB: {
          filename: promptB.filename,
          service: promptB.metadata.service,
          model: promptB.metadata.model,
          date: promptB.metadata.date,
          wordCount: promptB.wordCount,
        },
      },
      similarity: this.calculateSimilarity(
        promptA.systemPrompt,
        promptB.systemPrompt
      ),
      structuralDifferences: this.compareStructure(
        promptA.systemPrompt,
        promptB.systemPrompt
      ),
      contentDifferences: this.compareContent(
        promptA.systemPrompt,
        promptB.systemPrompt
      ),
      lengthComparison: this.compareLengths(promptA, promptB),
      uniqueElements: this.findUniqueElements(
        promptA.systemPrompt,
        promptB.systemPrompt
      ),
    };
  }

  /**
   * Calculate text similarity between two prompts
   * @param {string} textA - First prompt text
   * @param {string} textB - Second prompt text
   * @returns {Object} Similarity metrics
   */
  calculateSimilarity(textA, textB) {
    // Jaccard similarity
    const tokensA = new Set(this.tokenizer.tokenize(textA.toLowerCase()));
    const tokensB = new Set(this.tokenizer.tokenize(textB.toLowerCase()));

    const intersection = new Set([...tokensA].filter((x) => tokensB.has(x)));
    const union = new Set([...tokensA, ...tokensB]);

    const jaccardSimilarity = intersection.size / union.size;

    // Cosine similarity
    const tfidf = new natural.TfIdf();
    tfidf.addDocument(this.tokenizer.tokenize(textA));
    tfidf.addDocument(this.tokenizer.tokenize(textB));

    const cosineSimilarity = this.calculateCosineSimilarity(tfidf, 0, 1);

    // Levenshtein distance normalized
    const maxLength = Math.max(textA.length, textB.length);
    const levenshteinDistance = natural.LevenshteinDistance(textA, textB);
    const levenshteinSimilarity = 1 - levenshteinDistance / maxLength;

    return {
      jaccard: Math.round(jaccardSimilarity * 1000) / 1000,
      cosine: Math.round(cosineSimilarity * 1000) / 1000,
      levenshtein: Math.round(levenshteinSimilarity * 1000) / 1000,
      overall:
        Math.round(
          ((jaccardSimilarity + cosineSimilarity + levenshteinSimilarity) / 3) *
            1000
        ) / 1000,
      classification: this.classifySimilarity(
        (jaccardSimilarity + cosineSimilarity + levenshteinSimilarity) / 3
      ),
    };
  }

  /**
   * Calculate cosine similarity between two TF-IDF vectors
   * @param {Object} tfidf - TF-IDF object
   * @param {number} docA - Document A index
   * @param {number} docB - Document B index
   * @returns {number} Cosine similarity
   */
  calculateCosineSimilarity(tfidf, docA, docB) {
    const termsA = new Map();
    const termsB = new Map();

    tfidf.listTerms(docA).forEach((item) => termsA.set(item.term, item.tfidf));
    tfidf.listTerms(docB).forEach((item) => termsB.set(item.term, item.tfidf));

    const allTerms = new Set([...termsA.keys(), ...termsB.keys()]);

    let dotProduct = 0;
    let magnitudeA = 0;
    let magnitudeB = 0;

    for (const term of allTerms) {
      const scoreA = termsA.get(term) || 0;
      const scoreB = termsB.get(term) || 0;

      dotProduct += scoreA * scoreB;
      magnitudeA += scoreA * scoreA;
      magnitudeB += scoreB * scoreB;
    }

    if (magnitudeA === 0 || magnitudeB === 0) return 0;

    return dotProduct / (Math.sqrt(magnitudeA) * Math.sqrt(magnitudeB));
  }

  /**
   * Classify similarity level
   * @param {number} similarity - Overall similarity score
   * @returns {string} Classification
   */
  classifySimilarity(similarity) {
    if (similarity > 0.8) return "very_high";
    if (similarity > 0.6) return "high";
    if (similarity > 0.4) return "medium";
    if (similarity > 0.2) return "low";
    return "very_low";
  }

  /**
   * Compare structural differences between prompts
   * @param {string} textA - First prompt text
   * @param {string} textB - Second prompt text
   * @returns {Object} Structural comparison
   */
  compareStructure(textA, textB) {
    const structureA = this.analyzeStructure(textA);
    const structureB = this.analyzeStructure(textB);

    return {
      promptA: structureA,
      promptB: structureB,
      differences: {
        lines: structureB.totalLines - structureA.totalLines,
        paragraphs: structureB.paragraphs - structureA.paragraphs,
        bulletPoints: structureB.bulletPoints - structureA.bulletPoints,
        numberedLists: structureB.numberedLists - structureA.numberedLists,
        headings: structureB.headings - structureA.headings,
      },
    };
  }

  /**
   * Analyze text structure
   * @param {string} text - Input text
   * @returns {Object} Structure analysis
   */
  analyzeStructure(text) {
    const lines = text.split("\n");
    const bulletPoints = lines.filter((line) =>
      line.trim().match(/^[-*•]/)
    ).length;
    const numberedLists = lines.filter((line) =>
      line.trim().match(/^\d+\./)
    ).length;
    const headings = lines.filter((line) => line.trim().match(/^#+/)).length;
    const paragraphs = text.split(/\n\s*\n/).length;

    return {
      totalLines: lines.length,
      bulletPoints,
      numberedLists,
      headings,
      paragraphs,
    };
  }

  /**
   * Compare content themes and topics
   * @param {string} textA - First prompt text
   * @param {string} textB - Second prompt text
   * @returns {Object} Content comparison
   */
  compareContent(textA, textB) {
    const sentencesA = this.extractSentences(textA);
    const sentencesB = this.extractSentences(textB);

    // Find similar sentences
    const similarSentences = this.findSimilarSentences(sentencesA, sentencesB);

    // Extract key themes
    const themesA = this.extractThemes(textA);
    const themesB = this.extractThemes(textB);

    // Find common and unique themes
    const commonThemes = themesA.filter((theme) =>
      themesB.some(
        (t) =>
          t.toLowerCase().includes(theme.toLowerCase()) ||
          theme.toLowerCase().includes(t.toLowerCase())
      )
    );

    const uniqueToA = themesA.filter(
      (theme) =>
        !themesB.some(
          (t) =>
            t.toLowerCase().includes(theme.toLowerCase()) ||
            theme.toLowerCase().includes(t.toLowerCase())
        )
    );

    const uniqueToB = themesB.filter(
      (theme) =>
        !themesA.some(
          (t) =>
            t.toLowerCase().includes(theme.toLowerCase()) ||
            theme.toLowerCase().includes(t.toLowerCase())
        )
    );

    return {
      sentenceComparison: {
        totalA: sentencesA.length,
        totalB: sentencesB.length,
        similar: similarSentences.length,
        similarityRatio:
          Math.round(
            (similarSentences.length /
              Math.max(sentencesA.length, sentencesB.length)) *
              1000
          ) / 1000,
      },
      themes: {
        common: commonThemes,
        uniqueToA: uniqueToA.slice(0, 10),
        uniqueToB: uniqueToB.slice(0, 10),
      },
      topSimilarSentences: similarSentences.slice(0, 5),
    };
  }

  /**
   * Extract sentences from text
   * @param {string} text - Input text
   * @returns {Array} Array of sentences
   */
  extractSentences(text) {
    return text
      .split(/[.!?]+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 10);
  }

  /**
   * Find similar sentences between two texts
   * @param {Array} sentencesA - Sentences from first text
   * @param {Array} sentencesB - Sentences from second text
   * @returns {Array} Array of similar sentence pairs
   */
  findSimilarSentences(sentencesA, sentencesB) {
    const similarPairs = [];
    const threshold = 0.6; // Similarity threshold

    sentencesA.forEach((sentenceA) => {
      sentencesB.forEach((sentenceB) => {
        const similarity = this.calculateTextSimilarity(sentenceA, sentenceB);
        if (similarity > threshold) {
          similarPairs.push({
            sentenceA:
              sentenceA.substring(0, 100) +
              (sentenceA.length > 100 ? "..." : ""),
            sentenceB:
              sentenceB.substring(0, 100) +
              (sentenceB.length > 100 ? "..." : ""),
            similarity: Math.round(similarity * 1000) / 1000,
          });
        }
      });
    });

    return similarPairs.sort((a, b) => b.similarity - a.similarity);
  }

  /**
   * Calculate similarity between two text strings
   * @param {string} textA - First text
   * @param {string} textB - Second text
   * @returns {number} Similarity score
   */
  calculateTextSimilarity(textA, textB) {
    const tokensA = new Set(this.tokenizer.tokenize(textA.toLowerCase()));
    const tokensB = new Set(this.tokenizer.tokenize(textB.toLowerCase()));

    const intersection = new Set([...tokensA].filter((x) => tokensB.has(x)));
    const union = new Set([...tokensA, ...tokensB]);

    return intersection.size / union.size;
  }

  /**
   * Extract key themes from text
   * @param {string} text - Input text
   * @returns {Array} Array of themes
   */
  extractThemes(text) {
    const tfidf = new natural.TfIdf();
    const tokens = this.tokenizer.tokenize(text.toLowerCase());
    tfidf.addDocument(tokens);

    return tfidf
      .listTerms(0)
      .slice(0, 15)
      .map((item) => item.term)
      .filter((term) => term.length > 3);
  }

  /**
   * Compare lengths and provide insights
   * @param {Object} promptA - First prompt object
   * @param {Object} promptB - Second prompt object
   * @returns {Object} Length comparison
   */
  compareLengths(promptA, promptB) {
    const wordDiff = promptB.wordCount - promptA.wordCount;
    const percentChange =
      Math.round((wordDiff / promptA.wordCount) * 10000) / 100;

    return {
      wordCountA: promptA.wordCount,
      wordCountB: promptB.wordCount,
      difference: wordDiff,
      percentChange,
      trend:
        wordDiff > 0 ? "increased" : wordDiff < 0 ? "decreased" : "unchanged",
      significance:
        Math.abs(percentChange) > 50
          ? "major"
          : Math.abs(percentChange) > 20
          ? "moderate"
          : "minor",
    };
  }

  /**
   * Find unique elements in each prompt
   * @param {string} textA - First prompt text
   * @param {string} textB - Second prompt text
   * @returns {Object} Unique elements
   */
  findUniqueElements(textA, textB) {
    // Find unique phrases (3+ words)
    const uniquePhrasesA = this.findUniquePhrases(textA, textB);
    const uniquePhrasesB = this.findUniquePhrases(textB, textA);

    // Find unique directives
    const directivesA = this.extractDirectives(textA);
    const directivesB = this.extractDirectives(textB);

    const uniqueDirectivesA = directivesA.filter(
      (dirA) =>
        !directivesB.some(
          (dirB) => this.calculateTextSimilarity(dirA, dirB) > 0.7
        )
    );

    const uniqueDirectivesB = directivesB.filter(
      (dirB) =>
        !directivesA.some(
          (dirA) => this.calculateTextSimilarity(dirA, dirB) > 0.7
        )
    );

    return {
      uniqueToA: {
        phrases: uniquePhrasesA.slice(0, 10),
        directives: uniqueDirectivesA.slice(0, 5),
      },
      uniqueToB: {
        phrases: uniquePhrasesB.slice(0, 10),
        directives: uniqueDirectivesB.slice(0, 5),
      },
    };
  }

  /**
   * Find phrases unique to one text
   * @param {string} targetText - Text to find unique phrases in
   * @param {string} compareText - Text to compare against
   * @returns {Array} Array of unique phrases
   */
  findUniquePhrases(targetText, compareText) {
    const sentences = this.extractSentences(targetText);
    const compareSentences = this.extractSentences(compareText);

    const uniquePhrases = [];

    sentences.forEach((sentence) => {
      const words = sentence.split(/\s+/);
      for (let i = 0; i <= words.length - 3; i++) {
        const phrase = words
          .slice(i, i + 3)
          .join(" ")
          .toLowerCase();

        // Check if this phrase appears in the comparison text
        if (!compareText.toLowerCase().includes(phrase) && phrase.length > 10) {
          uniquePhrases.push(phrase);
        }
      }
    });

    // Remove duplicates and return most significant
    return [...new Set(uniquePhrases)]
      .filter((phrase) => phrase.match(/[a-zA-Z]/)) // Must contain letters
      .slice(0, 20);
  }

  /**
   * Extract directive statements from text
   * @param {string} text - Input text
   * @returns {Array} Array of directives
   */
  extractDirectives(text) {
    const sentences = this.extractSentences(text);
    const directivePatterns = [
      /^(always|never|should|must|will|when|if)/i,
      /(do not|don't|avoid|ensure|make sure)/i,
      /(respond|answer|provide|generate|create)/i,
    ];

    return sentences
      .filter((sentence) =>
        directivePatterns.some((pattern) => pattern.test(sentence))
      )
      .map(
        (sentence) =>
          sentence.substring(0, 150) + (sentence.length > 150 ? "..." : "")
      );
  }

  /**
   * Compare multiple prompts from the same service over time
   * @param {Array} prompts - Array of prompts from same service, sorted by date
   * @returns {Object} Evolution analysis
   */
  analyzeEvolution(prompts) {
    if (prompts.length < 2) {
      return { error: "Need at least 2 prompts for evolution analysis" };
    }

    const comparisons = [];
    const changes = {
      length: [],
      similarity: [],
      majorChanges: [],
    };

    for (let i = 1; i < prompts.length; i++) {
      const comparison = this.comparePrompts(prompts[i - 1], prompts[i]);
      comparisons.push(comparison);

      changes.length.push(comparison.lengthComparison.percentChange);
      changes.similarity.push(comparison.similarity.overall);

      if (comparison.similarity.overall < 0.7) {
        changes.majorChanges.push({
          from: prompts[i - 1].filename,
          to: prompts[i].filename,
          similarity: comparison.similarity.overall,
          changes: comparison.uniqueElements,
        });
      }
    }

    return {
      totalComparisons: comparisons.length,
      averageSimilarity:
        Math.round(
          (changes.similarity.reduce((a, b) => a + b, 0) /
            changes.similarity.length) *
            1000
        ) / 1000,
      lengthTrend: this.analyzeTrend(changes.length),
      similarityTrend: this.analyzeTrend(changes.similarity),
      majorChanges: changes.majorChanges,
      detailedComparisons: comparisons,
    };
  }

  /**
   * Analyze trend in array of values
   * @param {Array} values - Array of numeric values
   * @returns {Object} Trend analysis
   */
  analyzeTrend(values) {
    if (values.length < 2) return { trend: "insufficient_data" };

    const average = values.reduce((a, b) => a + b, 0) / values.length;
    const first = values[0];
    const last = values[values.length - 1];

    return {
      trend:
        last > first ? "increasing" : last < first ? "decreasing" : "stable",
      average: Math.round(average * 100) / 100,
      first,
      last,
      change: Math.round((last - first) * 100) / 100,
    };
  }
}

module.exports = SystemPromptComparator;

// CLI usage
if (require.main === module) {
  async function runComparison() {
    try {
      const SystemPromptParser = require("./parser");
      const parser = new SystemPromptParser(__dirname + "/..");
      const prompts = await parser.parseAll();

      const comparator = new SystemPromptComparator();

      // Find Claude prompts for evolution analysis
      const claudePrompts = prompts
        .filter(
          (p) =>
            p.metadata.service.includes("claude") ||
            p.metadata.service.includes("anthropic")
        )
        .filter((p) => p.metadata.date)
        .sort((a, b) => a.metadata.date - b.metadata.date);

      if (claudePrompts.length >= 2) {
        console.log(
          `\nAnalyzing evolution of ${claudePrompts.length} Claude prompts...`
        );
        const evolution = comparator.analyzeEvolution(claudePrompts);

        console.log("\nEvolution Analysis:");
        console.log("==================");
        console.log(
          `Average Similarity Between Versions: ${evolution.averageSimilarity}`
        );
        console.log(
          `Length Trend: ${evolution.lengthTrend.trend} (${evolution.lengthTrend.change}% change)`
        );
        console.log(`Major Changes Detected: ${evolution.majorChanges.length}`);

        // Save results
        await fs.writeJson(
          __dirname + "/../data/evolution-analysis.json",
          evolution,
          { spaces: 2 }
        );
        console.log(
          "\nEvolution analysis saved to data/evolution-analysis.json"
        );
      }

      // Compare latest OpenAI vs Claude if available
      const openaiPrompts = prompts.filter((p) =>
        p.metadata.service.includes("openai")
      );

      if (claudePrompts.length > 0 && openaiPrompts.length > 0) {
        const latestClaude = claudePrompts[claudePrompts.length - 1];
        const latestOpenAI = openaiPrompts[openaiPrompts.length - 1];

        console.log("\nComparing latest Claude vs OpenAI prompts...");
        const comparison = comparator.comparePrompts(
          latestClaude,
          latestOpenAI
        );

        console.log("\nCross-Service Comparison:");
        console.log("========================");
        console.log(
          `Overall Similarity: ${comparison.similarity.overall} (${comparison.similarity.classification})`
        );
        console.log(
          `Length Difference: ${comparison.lengthComparison.difference} words (${comparison.lengthComparison.percentChange}%)`
        );
        console.log(
          `Common Themes: ${comparison.contentDifferences.themes.common.length}`
        );

        await fs.writeJson(
          __dirname + "/../data/claude-vs-openai.json",
          comparison,
          { spaces: 2 }
        );
        console.log("\nComparison saved to data/claude-vs-openai.json");
      }
    } catch (error) {
      console.error("Comparison failed:", error);
    }
  }

  runComparison();
}
