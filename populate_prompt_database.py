#!/usr/bin/env python3
"""
Prompt Database Population Script
Consolidates all prompt collections into SQLite database with quality validation.
"""

import json
import sqlite3
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import hashlib
from datetime import datetime

class PromptQualityValidator:
    """Validates prompt quality and assigns effectiveness scores."""
    
    def __init__(self):
        self.quality_metrics = {
            'min_length': 20,
            'max_length': 2000,
            'required_elements': ['domain', 'action', 'context'],
            'complexity_patterns': {
                'L1': r'\b(simple|basic|quick|easy)\b',
                'L2': r'\b(moderate|analyze|design|implement)\b',
                'L3': r'\b(complex|systematic|comprehensive|evaluate)\b',
                'L4': r'\b(advanced|optimize|architecture|strategic)\b',
                'L5': r'\b(enterprise|organization|architectural|transformation)\b'
            }
        }
    
    def validate_prompt(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate prompt and calculate quality score."""
        issues = []
        content = prompt_data.get('content', '') or prompt_data.get('enhancedPrompt', '') or prompt_data.get('originalPrompt', '')
        
        # Basic validation
        if len(content) < self.quality_metrics['min_length']:
            issues.append(f"Content too short ({len(content)} chars)")
        
        if len(content) > self.quality_metrics['max_length']:
            issues.append(f"Content too long ({len(content)} chars)")
        
        # Grammar check (basic)
        if re.search(r'\bfor\s+do\s+I\b', content, re.IGNORECASE):
            issues.append("Grammar error detected")
        
        # Complexity validation
        complexity = prompt_data.get('complexity_level') or prompt_data.get('complexity', 'L2')
        if complexity in self.quality_metrics['complexity_patterns']:
            pattern = self.quality_metrics['complexity_patterns'][complexity]
            if not re.search(pattern, content, re.IGNORECASE):
                issues.append(f"Content doesn't match {complexity} complexity level")
        
        # Calculate effectiveness score
        base_score = 0.7
        if not issues:
            base_score = 0.85
        if len(content) > 100 and '.' in content:
            base_score += 0.05
        if prompt_data.get('domain') and '.' in prompt_data.get('domain', ''):
            base_score += 0.05
        
        return {
            'quality_score': min(base_score, 1.0),
            'issues': issues,
            'validated_at': datetime.now().isoformat()
        }

class PromptDatabasePopulator:
    """Consolidates and populates the prompt database from all sources."""
    
    def __init__(self, db_path: Path, sequential_think_path: Path):
        self.db_path = db_path
        self.sequential_think_path = sequential_think_path
        self.validator = PromptQualityValidator()
        self.processed_hashes = set()
    
    def init_database(self):
        """Initialize enhanced database schema."""
        with sqlite3.connect(self.db_path) as conn:
            # Drop existing tables to recreate with enhanced schema
            conn.execute("DROP TABLE IF EXISTS prompts_fts")
            conn.execute("DROP TABLE IF EXISTS prompts")
            conn.execute("DROP TABLE IF EXISTS frameworks")
            
            # Enhanced prompts table
            conn.execute("""
                CREATE TABLE prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    original_prompt TEXT,
                    enhanced_prompt TEXT,
                    category TEXT NOT NULL,
                    complexity_level TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    effectiveness_score REAL DEFAULT 0.7,
                    quality_score REAL DEFAULT 0.7,
                    quality_issues TEXT,
                    usage_count INTEGER DEFAULT 0,
                    source_file TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    validated_at TIMESTAMP
                )
            """)
            
            # Enhanced frameworks table
            conn.execute("""
                CREATE TABLE frameworks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL,
                    methodology TEXT NOT NULL,
                    use_cases TEXT NOT NULL,
                    complexity_range TEXT NOT NULL,
                    phases TEXT,
                    features TEXT,
                    usage_pattern TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Prompt relationships table
            conn.execute("""
                CREATE TABLE prompt_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_id INTEGER,
                    related_prompt_id INTEGER,
                    relationship_type TEXT,
                    strength REAL DEFAULT 0.5,
                    FOREIGN KEY (prompt_id) REFERENCES prompts (id),
                    FOREIGN KEY (related_prompt_id) REFERENCES prompts (id)
                )
            """)
            
            # Enhanced FTS5 virtual table
            conn.execute("""
                CREATE VIRTUAL TABLE prompts_fts USING fts5(
                    title, content, original_prompt, enhanced_prompt, 
                    category, domain, tags, content=prompts
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX idx_prompts_domain ON prompts(domain)")
            conn.execute("CREATE INDEX idx_prompts_complexity ON prompts(complexity_level)")
            conn.execute("CREATE INDEX idx_prompts_effectiveness ON prompts(effectiveness_score)")
            conn.execute("CREATE INDEX idx_prompts_quality ON prompts(quality_score)")
            
            conn.commit()
    
    def generate_hash(self, content: str) -> str:
        """Generate hash for deduplication."""
        return hashlib.md5(content.encode()).hexdigest()
    
    def load_json_prompts(self) -> List[Dict[str, Any]]:
        """Load prompts from all JSON files."""
        prompts = []
        json_files = [
            "ai/exports/prompts-by-complexity.json",
            "ai/exports/prompts-by-domain.json",
            "ai/enhanced-demo/enhanced-prompts.json",
            "ai/omom-optimized/enhanced-prompts.json",
            "ai/examples/sample-prompts.json"
        ]
        
        for file_path in json_files:
            full_path = self.sequential_think_path / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, dict):
                                value['source_file'] = file_path
                                prompts.append(value)
                            elif isinstance(value, list):
                                for item in value:
                                    if isinstance(item, dict):
                                        item['source_file'] = file_path
                                        prompts.append(item)
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                item['source_file'] = file_path
                                prompts.append(item)
                    
                    print(f"Loaded {len(prompts)} prompts from {file_path}")
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")
        
        return prompts
    
    def parse_markdown_prompts(self) -> List[Dict[str, Any]]:
        """Extract prompts from markdown files."""
        prompts = []
        md_files = [
            "sequentialthinking-prompts.md",
            "universal-prompt-collection.md",
            "universal_prompt_collection_scratch.md"
        ]
        
        for file_path in md_files:
            full_path = self.sequential_think_path / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract bash code blocks with sequentialthinking commands
                    pattern = r'```bash\n(.*?sequentialthinking.*?)\n```'
                    matches = re.findall(pattern, content, re.DOTALL)
                    
                    for match in matches:
                        lines = match.strip().split('\n')
                        for line in lines:
                            if 'sequentialthinking' in line and not line.startswith('#'):
                                prompt_content = self.extract_prompt_from_command(line)
                                if prompt_content:
                                    prompts.append({
                                        'content': prompt_content,
                                        'source_file': file_path,
                                        'domain': self.infer_domain_from_context(line),
                                        'complexity_level': self.infer_complexity_from_context(line),
                                        'category': 'extracted'
                                    })
                    
                    print(f"Extracted {len([p for p in prompts if p['source_file'] == file_path])} prompts from {file_path}")
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")
        
        return prompts
    
    def extract_prompt_from_command(self, command: str) -> Optional[str]:
        """Extract prompt text from sequentialthinking command."""
        # Extract text between quotes
        matches = re.findall(r'"([^"]*)"', command)
        if matches:
            return matches[0]
        return None
    
    def infer_domain_from_context(self, text: str) -> str:
        """Infer domain from context."""
        domain_patterns = {
            'Development.Frontend.ReactTypeScript': r'\b(react|typescript|jsx|tsx|component)\b',
            'Development.Architecture.SystemDesign': r'\b(architecture|design|system|microservices)\b',
            'Development.Performance.SystemOptimization': r'\b(performance|optimization|optimize|speed)\b',
            'DevOps.Infrastructure.CloudNative': r'\b(devops|docker|kubernetes|cloud|infrastructure)\b',
            'Development.Debugging.SystematicAnalysis': r'\b(debug|error|troubleshoot|issue)\b',
        }
        
        text_lower = text.lower()
        for domain, pattern in domain_patterns.items():
            if re.search(pattern, text_lower):
                return domain
        
        return 'Development.General'
    
    def infer_complexity_from_context(self, text: str) -> str:
        """Infer complexity level from context."""
        if '-t' in text:
            # Extract -t parameter
            match = re.search(r'-t\s+(\d+)', text)
            if match:
                thoughts = int(match.group(1))
                if thoughts <= 3:
                    return 'L1'
                elif thoughts <= 5:
                    return 'L2'
                elif thoughts <= 8:
                    return 'L3'
                elif thoughts <= 12:
                    return 'L4'
                else:
                    return 'L5'
        
        return 'L2'  # Default
    
    def normalize_prompt_data(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize prompt data to consistent format."""
        # Extract content from various fields
        content = (prompt_data.get('content') or 
                  prompt_data.get('enhancedPrompt') or 
                  prompt_data.get('optimizedPrompt') or 
                  prompt_data.get('originalPrompt') or '')
        
        original = prompt_data.get('originalPrompt', '')
        enhanced = prompt_data.get('enhancedPrompt') or prompt_data.get('optimizedPrompt', '')
        
        # Generate title if missing
        title = prompt_data.get('title', '')
        if not title:
            title = (content[:50] + '...') if len(content) > 50 else content
        
        # Normalize domain
        domain = prompt_data.get('domain', 'Development.General')
        if not '.' in domain:
            domain = f"Development.{domain}"
        
        # Extract tags
        tags = prompt_data.get('tags', '')
        if not tags and 'improvements' in prompt_data:
            tags = ', '.join(prompt_data['improvements'])
        
        return {
            'title': title,
            'content': content,
            'original_prompt': original,
            'enhanced_prompt': enhanced,
            'domain': domain,
            'category': prompt_data.get('category', 'general'),
            'complexity_level': prompt_data.get('complexity_level') or prompt_data.get('complexity', 'L2'),
            'tags': tags,
            'effectiveness_score': prompt_data.get('effectiveness', 0.7),
            'source_file': prompt_data.get('source_file', 'unknown')
        }
    
    def populate_database(self):
        """Populate database with all consolidated prompts."""
        print("Initializing database...")
        self.init_database()
        
        print("Loading JSON prompts...")
        json_prompts = self.load_json_prompts()
        
        print("Parsing Markdown prompts...")
        md_prompts = self.parse_markdown_prompts()
        
        all_prompts = json_prompts + md_prompts
        print(f"Total prompts collected: {len(all_prompts)}")
        
        processed_count = 0
        duplicate_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            for prompt_data in all_prompts:
                try:
                    normalized = self.normalize_prompt_data(prompt_data)
                    
                    # Generate hash for deduplication
                    content_hash = self.generate_hash(normalized['content'])
                    if content_hash in self.processed_hashes:
                        duplicate_count += 1
                        continue
                    
                    self.processed_hashes.add(content_hash)
                    
                    # Validate quality
                    validation = self.validator.validate_prompt(normalized)
                    
                    # Insert into database
                    conn.execute("""
                        INSERT INTO prompts (
                            hash, title, content, original_prompt, enhanced_prompt,
                            category, complexity_level, domain, tags, effectiveness_score,
                            quality_score, quality_issues, source_file, validated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        content_hash, normalized['title'], normalized['content'],
                        normalized['original_prompt'], normalized['enhanced_prompt'],
                        normalized['category'], normalized['complexity_level'],
                        normalized['domain'], normalized['tags'], normalized['effectiveness_score'],
                        validation['quality_score'], json.dumps(validation['issues']),
                        normalized['source_file'], validation['validated_at']
                    ))
                    
                    processed_count += 1
                    
                except Exception as e:
                    print(f"Error processing prompt: {e}")
                    continue
            
            # Populate FTS5 table
            conn.execute("INSERT INTO prompts_fts SELECT title, content, original_prompt, enhanced_prompt, category, domain, tags FROM prompts")
            
            # Add frameworks
            self.populate_frameworks(conn)
            
            conn.commit()
        
        print(f"Database population complete!")
        print(f"- Processed: {processed_count} prompts")
        print(f"- Duplicates skipped: {duplicate_count}")
        print(f"- Quality issues found: {sum(1 for p in all_prompts if self.validator.validate_prompt(self.normalize_prompt_data(p))['issues'])}")
    
    def populate_frameworks(self, conn):
        """Populate frameworks table with predefined frameworks."""
        frameworks = [
            {
                'name': 'Enhanced Debugging',
                'description': '5-phase systematic debugging methodology',
                'methodology': 'Phase-based evidence collection and analysis',
                'use_cases': 'Complex system troubleshooting, root cause analysis',
                'complexity_range': 'L3-L5',
                'phases': json.dumps([
                    'Problem Identification & Evidence Collection',
                    'Hypothesis Formation & Validation', 
                    'Root Cause Analysis',
                    'Solution Implementation',
                    'Verification & Documentation'
                ]),
                'usage_pattern': 'sequentialthinking -t 8 "Execute comprehensive debugging analysis for [problem]"'
            },
            {
                'name': 'Prompt Taxonomy',
                'description': 'Multi-dimensional classification system with L1-L5 complexity levels',
                'methodology': 'Systematic complexity and context classification',
                'use_cases': 'Prompt optimization, complexity assessment',
                'complexity_range': 'L1-L5',
                'features': json.dumps([
                    'L1-L2: Simple, focused problems (1-4 steps)',
                    'L3-L4: Complex problems requiring systematic analysis (5-10 steps)',
                    'L5: Architectural decisions with organization-wide impact (10+ steps)'
                ]),
                'usage_pattern': 'sequentialthinking -t [level] "Domain.Subdomain - [Action] considering [Context]"'
            }
        ]
        
        for framework in frameworks:
            conn.execute("""
                INSERT OR REPLACE INTO frameworks (
                    name, description, methodology, use_cases, complexity_range,
                    phases, features, usage_pattern
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                framework['name'], framework['description'], framework['methodology'],
                framework['use_cases'], framework['complexity_range'],
                framework.get('phases'), framework.get('features'), framework['usage_pattern']
            ))

def main():
    """Main execution function."""
    base_path = Path(__file__).parent
    db_path = base_path / "sequential_think_prompts.db"
    sequential_think_path = base_path / "sequential-think"
    
    if not sequential_think_path.exists():
        print(f"Error: Sequential think directory not found at {sequential_think_path}")
        return
    
    populator = PromptDatabasePopulator(db_path, sequential_think_path)
    populator.populate_database()
    
    print(f"\nDatabase saved to: {db_path}")
    print("You can now use the enhanced MCP server with populated database!")

if __name__ == "__main__":
    main()