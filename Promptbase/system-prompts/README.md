# System Prompt Research & Analysis Toolkit

A comprehensive toolkit for analyzing, comparing, and researching AI system prompts from various LLM-based services. This project provides both programmatic APIs and a web-based research interface for studying the evolution and patterns of AI system prompts.

## 🎯 Purpose

This repository serves dual purposes:
1. **Documentation Collection**: A curated collection of leaked system prompts from various AI services for research and educational purposes
2. **Analysis Toolkit**: Advanced tools for analyzing prompt patterns, evolution, and effectiveness

## 🚀 Features

### Core Analysis Capabilities
- **Prompt Parsing**: Extracts system prompts from markdown files with metadata
- **Content Analysis**: Categorizes prompts by personality, capabilities, safety, limitations, etc.
- **Pattern Recognition**: Identifies common phrases, directives, and structural patterns
- **Evolution Tracking**: Analyzes how prompts change over time within services
- **Similarity Comparison**: Compares prompts using multiple similarity metrics
- **Enhancement Suggestions**: Provides recommendations for improving prompt quality

### Web Research Interface
- **Interactive Dashboard**: Browse and explore the prompt collection
- **Advanced Search**: Search prompts by content, service, model, or date
- **Visual Analytics**: Charts and graphs showing prompt trends and patterns
- **Comparison Tools**: Side-by-side prompt comparison with detailed metrics
- **Analysis Views**: Detailed breakdowns of prompt components and effectiveness

### API Endpoints
- REST API for programmatic access to all analysis features
- Real-time analysis and comparison capabilities
- Flexible querying and filtering options

## 📊 What Gets Analyzed

### Content Categories
- **Personality**: Tone, communication style, persona definition
- **Capabilities**: What the AI can and cannot do
- **Safety**: Restrictions, harmful content handling, ethical guidelines
- **Limitations**: Explicit boundaries and constraints
- **Interaction Style**: How the AI should respond and engage
- **Knowledge**: Information about training data, cutoffs, sources
- **Formatting**: Output structure, markdown usage, citations
- **Identity**: Self-description, creator attribution

### Metrics & Insights
- Word count and readability analysis
- Structural complexity (headers, lists, paragraphs)
- Sentiment and tone analysis
- Key phrase extraction and frequency
- Cross-service pattern comparison
- Temporal evolution tracking

## 🛠️ Installation & Setup

### Prerequisites
- Node.js (v14 or higher)
- npm or yarn

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd leaked-system-prompts
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Parse and analyze prompts**
   ```bash
   npm run analyze
   ```

4. **Start the web server**
   ```bash
   npm run serve
   ```

5. **Open the research interface**
   ```
   http://localhost:3001
   ```

## 📚 Usage

### Command Line Interface

#### Parse all prompts
```bash
node src/parser.js
```
Extracts system prompts from all markdown files and saves structured data.

#### Analyze prompts
```bash
node src/analyzer.js
```
Performs comprehensive analysis including categorization, sentiment, and pattern recognition.

#### Compare specific prompts
```bash
node src/index.js compare anthropic-claude-3.5-sonnet_20241022 openai-chatgpt4o_20240520
```

#### Generate enhancement suggestions
```bash
node src/enhancer.js
```

#### Start web server
```bash
node src/index.js serve --port 3001
```

### Programmatic Usage

```javascript
const { SystemPromptParser, SystemPromptAnalyzer, SystemPromptComparator } = require('./src');

// Parse prompts
const parser = new SystemPromptParser('./');
const prompts = await parser.parseAll();

// Analyze prompts
const analyzer = new SystemPromptAnalyzer();
const analysis = analyzer.analyzePrompts(prompts);

// Compare two prompts
const comparator = new SystemPromptComparator();
const comparison = comparator.comparePrompts(promptA, promptB);
```

### API Usage

#### Get all prompts
```bash
curl "http://localhost:3001/api/prompts?service=anthropic&limit=10"
```

#### Get analysis results
```bash
curl "http://localhost:3001/api/analysis"
```

#### Compare prompts
```bash
curl -X POST "http://localhost:3001/api/compare" \
  -H "Content-Type: application/json" \
  -d '{"filenameA": "prompt1.md", "filenameB": "prompt2.md"}'
```

#### Search prompts
```bash
curl "http://localhost:3001/api/search?q=helpful%20assistant&minWords=100"
```

## 📁 Project Structure

```
leaked-system-prompts/
├── src/
│   ├── parser.js          # Markdown parsing and prompt extraction
│   ├── analyzer.js        # Content analysis and categorization
│   ├── comparator.js      # Prompt comparison and similarity
│   ├── enhancer.js        # Quality assessment and suggestions
│   └── index.js           # Main server and CLI interface
├── public/
│   └── index.html         # React-based web interface
├── data/                  # Generated analysis results (auto-created)
├── images/                # Referenced images from prompts
├── *.md                   # System prompt files (service-model_date.md)
└── package.json           # Dependencies and scripts
```

## 🔧 Development Commands

```bash
# Parse all prompts and save to data/
npm run parse

# Run comprehensive analysis
npm run analyze

# Start development server with auto-reload
npm run dev

# Start production server
npm start

# Run tests (if available)
npm test
```

## 📈 Analysis Results

The toolkit generates several types of analysis results:

### Individual Prompt Analysis
- Content categorization scores
- Readability and complexity metrics
- Key phrases and directives
- Structural analysis (headers, lists, formatting)
- Enhancement suggestions with priority ratings

### Aggregate Analysis
- Cross-service pattern comparison
- Category prevalence across all prompts
- Common phrases and directives
- Service-specific characteristics
- Temporal trends and evolution

### Comparison Results
- Similarity scores (Jaccard, Cosine, Levenshtein)
- Content differences and unique elements
- Structural comparison
- Length and complexity changes

## 🎨 Web Interface Features

### Dashboard Tabs
- **Overview**: Statistics and service breakdown
- **Browse Prompts**: Filterable prompt collection
- **Analysis**: Detailed analysis results and visualizations
- **Compare**: Side-by-side prompt comparison tool
- **Search**: Advanced search with filtering options

### Interactive Features
- Real-time search and filtering
- Sortable data tables
- Interactive charts and visualizations
- Responsive design for all devices
- Export capabilities for analysis results

## 🔍 Research Applications

This toolkit is valuable for:

- **AI Safety Research**: Understanding how different services implement safety measures
- **Prompt Engineering**: Learning from successful prompt patterns and structures
- **AI Transparency**: Analyzing how AI systems are instructed to behave
- **Comparative Studies**: Understanding differences between AI services
- **Educational Purposes**: Teaching prompt design and AI system architecture
- **Academic Research**: Empirical studies of AI instruction design

## 📊 Data Format

### Prompt Files
System prompt files follow the naming convention: `service-model_YYYYMMDD.md`

Example structure:
```markdown
# service-model_YYYYMMDD

source: https://example.com/source

## System Prompt

[System prompt content here]

## Additional Context
[Optional additional information]
```

### Analysis Output
Analysis results are saved as JSON files in the `data/` directory:
- `prompts.json`: Parsed prompt data
- `analysis.json`: Comprehensive analysis results
- `enhancement-suggestions.json`: Quality improvement suggestions

## 🤝 Contributing

### Adding New Prompts
1. Create a markdown file following the naming convention
2. Include verifiable source attribution
3. Ensure reproducible prompt extraction method
4. Submit a pull request or create an issue

### Development
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Original Contribution Guidelines
1. If you would like to submit a PR, please match the format of other documents. You must include sources that I can verify or reproducible prompts.
2. If the above process is too cumbersome, you can simply post a link in the Issues section. If there are verifiable sources or reproducible prompts, I will verify them and then proceed with the merge.
3. This repository is cited in many papers. To prevent repository takedown due to [DMCA](https://docs.github.com/en/site-policy/content-removal-policies/dmca-takedown-policy) warnings, please do not include sensitive commercial source code.

## ⚖️ Legal & Ethical Considerations

- All prompts should be obtained through legitimate, reproducible methods
- Sources must be verifiable and properly attributed
- Content is for research and educational purposes only
- Respect copyright and intellectual property rights
- Do not include proprietary or confidential information

## 🛡️ Security & Privacy

- No personal data or private information should be included
- All analysis is performed locally
- No data is transmitted to external services
- API keys and credentials should never be committed

## 📄 License

This project is open source and available under the MIT License. See the LICENSE file for details.

## 🙏 Acknowledgments

- Contributors who have provided verified system prompts
- Academic researchers citing this work in their studies
- The AI research community for responsible disclosure practices
- Open source libraries used in this project

## 📞 Support & Feedback

- **Issues**: Report bugs or feature requests via GitHub Issues
- **Discussions**: Join conversations about AI prompt research
- **Documentation**: Comprehensive API documentation available in the code
- **Community**: Connect with other researchers using this toolkit

---

**Note**: This toolkit is designed for legitimate research and educational purposes. Please use responsibly and in accordance with applicable laws and ethical guidelines.
