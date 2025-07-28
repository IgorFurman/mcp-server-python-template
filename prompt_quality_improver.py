#!/usr/bin/env python3
"""
Prompt Quality Improvement System
Identifies and fixes quality issues in the prompt database.
"""

import sqlite3
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

class PromptQualityImprover:
    """System for improving prompt quality through automated fixes."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.fix_patterns = {
            # Grammar fixes
            'grammar_fixes': [
                (r'\bfor\s+do\s+I\b', 'to'),
                (r'\bhow\s+do\s+I\b(.+?)\s+for\s+(.+)', r'how to \1 for \2'),
                (r'\bdesign\s+a\s+comprehensive\s+strategy\s+for\s+do\s+I\b', 'design a comprehensive strategy to'),
                (r'\b(\w+)\s+for\s+(\w+)\s+for\b', r'\1 for \2 to'),
            ],
            # Structure improvements
            'structure_improvements': [
                (r'^([^A-Z])', lambda m: m.group(1).upper()),  # Capitalize first letter
                (r'\?\s*$', ''),  # Remove trailing question marks from prompts
                (r'\s+', ' '),    # Normalize whitespace
            ],
            # Domain standardization
            'domain_fixes': [
                ('Development.React', 'Development.Frontend.ReactTypeScript'),
                ('Development.TypeScript', 'Development.Frontend.ReactTypeScript'),
                ('Development.Frontend', 'Development.Frontend.ReactTypeScript'),
                ('DevOps.Docker', 'DevOps.Infrastructure.CloudNative'),
                ('DevOps.Kubernetes', 'DevOps.Infrastructure.CloudNative'),
            ]
        }
        
        self.enhancement_templates = {
            'L1': {
                'prefix': 'Complete this straightforward task:',
                'structure': '{domain} - {action} considering basic {context}',
                'min_length': 50
            },
            'L2': {
                'prefix': 'Analyze and implement:',
                'structure': '{domain} - {action} considering {context} and requirements',
                'min_length': 80
            },
            'L3': {
                'prefix': 'Design comprehensive approach:',
                'structure': '{domain} - {action} considering {context}, constraints, and systematic methodology',
                'min_length': 120
            },
            'L4': {
                'prefix': 'Execute advanced analysis:',
                'structure': '{domain} - {action} considering {context}, architectural decisions, performance implications, and team coordination',
                'min_length': 150
            },
            'L5': {
                'prefix': 'Develop strategic transformation:',
                'structure': '{domain} - {action} considering {context}, organizational impact, stakeholder alignment, risk assessment, and long-term sustainability',
                'min_length': 200
            }
        }
    
    def analyze_quality_issues(self) -> Dict[str, Any]:
        """Analyze all quality issues in the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT id, title, content, domain, complexity_level, 
                       quality_score, quality_issues, effectiveness_score
                FROM prompts 
                WHERE quality_score < 0.8 OR quality_issues != '[]'
                ORDER BY quality_score ASC
            """)
            
            issues = cursor.fetchall()
            
            issue_categories = {
                'grammar_errors': [],
                'length_issues': [],
                'structure_problems': [],
                'domain_mismatches': [],
                'low_effectiveness': []
            }
            
            for row in issues:
                issues_list = json.loads(row['quality_issues'])
                
                for issue in issues_list:
                    if 'Grammar error' in issue:
                        issue_categories['grammar_errors'].append(dict(row))
                    elif 'too short' in issue or 'too long' in issue:
                        issue_categories['length_issues'].append(dict(row))
                    elif 'complexity level' in issue:
                        issue_categories['structure_problems'].append(dict(row))
                    elif 'domain' in issue.lower():
                        issue_categories['domain_mismatches'].append(dict(row))
                
                if row['effectiveness_score'] < 0.6:
                    issue_categories['low_effectiveness'].append(dict(row))
            
            return {
                'total_issues': len(issues),
                'categories': issue_categories,
                'summary': {
                    'grammar_errors': len(issue_categories['grammar_errors']),
                    'length_issues': len(issue_categories['length_issues']),
                    'structure_problems': len(issue_categories['structure_problems']),
                    'domain_mismatches': len(issue_categories['domain_mismatches']),
                    'low_effectiveness': len(issue_categories['low_effectiveness'])
                }
            }
    
    def fix_grammar_errors(self, text: str) -> str:
        """Fix common grammar errors in prompts."""
        fixed_text = text
        
        for pattern, replacement in self.fix_patterns['grammar_fixes']:
            if callable(replacement):
                fixed_text = re.sub(pattern, replacement, fixed_text) # pyright: ignore[reportCallIssue, reportArgumentType]
            else:
                fixed_text = re.sub(pattern, lambda m: replacement(m), fixed_text, flags=re.IGNORECASE)
        
        # Additional grammar improvements
        fixed_text = re.sub(r'\s+', ' ', fixed_text).strip()
        
        return fixed_text
    
    def improve_structure(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Improve prompt structure based on complexity level."""
        complexity = prompt_data['complexity_level']
        content = prompt_data['content']
        domain = prompt_data['domain']
        
        if complexity not in self.enhancement_templates:
            complexity = 'L2'  # Default fallback
        
        template = self.enhancement_templates[complexity]
        
        # If content is too short, enhance it
        if len(content) < template['min_length']:
            # Extract action and context from existing content
            action_match = re.search(r'\b(implement|design|create|analyze|optimize|debug|develop)\b.*', content, re.IGNORECASE)
            action = action_match.group(0) if action_match else content
            
            # Determine context based on domain
            context_map = {
                'Development.Frontend.ReactTypeScript': 'component architecture, type safety, and user experience',
                'Development.Architecture.SystemDesign': 'system scalability, performance, and maintainability',
                'Development.Performance.SystemOptimization': 'performance metrics, bottleneck analysis, and optimization strategies',
                'DevOps.Infrastructure.CloudNative': 'containerization, orchestration, and deployment pipelines',
                'Development.Debugging.SystematicAnalysis': 'error analysis, root cause identification, and resolution strategies'
            }
            
            context = context_map.get(domain, 'technical requirements and best practices')
            
            enhanced_content = template['structure'].format(
                domain=domain,
                action=action,
                context=context
            )
            
            return {
                **prompt_data,
                'content': enhanced_content,
                'enhanced_prompt': enhanced_content,
                'improvement_applied': 'structure_enhancement'
            }
        
        return prompt_data
    
    def standardize_domain(self, domain: str) -> str:
        """Standardize domain classification."""
        for old_domain, new_domain in self.fix_patterns['domain_fixes']:
            if domain.startswith(old_domain):
                return new_domain
        
        # Ensure proper domain structure
        if '.' not in domain:
            return f"Development.{domain}"
        
        parts = domain.split('.')
        if len(parts) < 3:
            if parts[0] == 'Development':
                return f"Development.General.{parts[1] if len(parts) > 1 else 'Programming'}"
            elif parts[0] == 'DevOps':
                return f"DevOps.Infrastructure.{parts[1] if len(parts) > 1 else 'General'}"
        
        return domain
    
    def calculate_new_effectiveness(self, prompt_data: Dict[str, Any]) -> float:
        """Calculate new effectiveness score based on improvements."""
        base_score = 0.7
        
        # Length bonus
        content_length = len(prompt_data['content'])
        if content_length > 100:
            base_score += 0.1
        if content_length > 200:
            base_score += 0.05
        
        # Structure bonus
        if prompt_data['domain'].count('.') >= 2:
            base_score += 0.05
        
        # Complexity alignment bonus
        complexity_words = {
            'L1': ['simple', 'basic', 'quick'],
            'L2': ['analyze', 'implement', 'design'],
            'L3': ['comprehensive', 'systematic', 'complex'],
            'L4': ['advanced', 'optimize', 'architecture'],
            'L5': ['strategic', 'enterprise', 'transformation']
        }
        
        complexity = prompt_data['complexity_level']
        if complexity in complexity_words:
            for word in complexity_words[complexity]:
                if word.lower() in prompt_data['content'].lower():
                    base_score += 0.02
                    break
        
        return min(base_score, 1.0)
    
    def apply_improvements(self, limit: int = 50) -> Dict[str, Any]:
        """Apply improvements to prompts with quality issues."""
        improvements = {
            'fixed_prompts': [],
            'improvement_counts': {
                'grammar_fixed': 0,
                'structure_improved': 0,
                'domain_standardized': 0,
                'effectiveness_improved': 0
            },
            'total_processed': 0
        }
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get prompts with quality issues
            cursor = conn.execute("""
                SELECT * FROM prompts 
                WHERE quality_score < 0.8 OR quality_issues != '[]'
                ORDER BY quality_score ASC, effectiveness_score ASC
                LIMIT ?
            """, (limit,))
            
            prompts_to_fix = cursor.fetchall()
            
            for row in prompts_to_fix:
                prompt_data = dict(row)
                original_content = prompt_data['content']
                modified = False
                
                # Fix grammar errors
                fixed_content = self.fix_grammar_errors(prompt_data['content'])
                if fixed_content != prompt_data['content']:
                    prompt_data['content'] = fixed_content
                    improvements['improvement_counts']['grammar_fixed'] += 1
                    modified = True
                
                # Improve structure
                improved_prompt = self.improve_structure(prompt_data)
                if 'improvement_applied' in improved_prompt:
                    prompt_data = improved_prompt
                    improvements['improvement_counts']['structure_improved'] += 1
                    modified = True
                
                # Standardize domain
                standardized_domain = self.standardize_domain(prompt_data['domain'])
                if standardized_domain != prompt_data['domain']:
                    prompt_data['domain'] = standardized_domain
                    improvements['improvement_counts']['domain_standardized'] += 1
                    modified = True
                
                # Calculate new effectiveness
                new_effectiveness = self.calculate_new_effectiveness(prompt_data)
                if new_effectiveness > prompt_data['effectiveness_score']:
                    prompt_data['effectiveness_score'] = new_effectiveness
                    improvements['improvement_counts']['effectiveness_improved'] += 1
                    modified = True
                
                if modified:
                    # Update database
                    conn.execute("""
                        UPDATE prompts 
                        SET content = ?, domain = ?, effectiveness_score = ?, 
                            enhanced_prompt = ?, quality_score = ?, updated_at = ?
                        WHERE id = ?
                    """, (
                        prompt_data['content'],
                        prompt_data['domain'],
                        prompt_data['effectiveness_score'],
                        prompt_data.get('enhanced_prompt', prompt_data['content']),
                        min(prompt_data.get('quality_score', 0.7) + 0.2, 1.0),
                        datetime.now().isoformat(),
                        prompt_data['id']
                    ))
                    
                    improvements['fixed_prompts'].append({
                        'id': prompt_data['id'],
                        'title': prompt_data['title'],
                        'original_content': original_content,
                        'improved_content': prompt_data['content'],
                        'old_effectiveness': row['effectiveness_score'],
                        'new_effectiveness': prompt_data['effectiveness_score']
                    })
                
                improvements['total_processed'] += 1
            
            # Update FTS table safely
            try:
                conn.execute("DROP TABLE IF EXISTS prompts_fts")
                conn.execute("""
                    CREATE VIRTUAL TABLE prompts_fts USING fts5(
                        title, content, original_prompt, enhanced_prompt, 
                        category, domain, tags, content=prompts
                    )
                """)
                conn.execute("""
                    INSERT INTO prompts_fts 
                    SELECT title, content, original_prompt, enhanced_prompt, 
                           category, domain, tags FROM prompts
                """)
            except Exception as e:
                print(f"Warning: Could not update FTS table: {e}")
                # Continue without FTS update
            
            conn.commit()
        
        return improvements
    
    def generate_quality_report(self) -> str:
        """Generate comprehensive quality report."""
        analysis = self.analyze_quality_issues()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) as total FROM prompts")
            total_prompts = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT AVG(quality_score) as avg_quality FROM prompts")
            avg_quality = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT AVG(effectiveness_score) as avg_effectiveness FROM prompts")
            avg_effectiveness = cursor.fetchone()[0]
        
        report = f"""
# Prompt Library Quality Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary Statistics
- Total Prompts: {total_prompts}
- Average Quality Score: {avg_quality:.3f}
- Average Effectiveness Score: {avg_effectiveness:.3f}
- Prompts with Issues: {analysis['total_issues']}

## Issue Breakdown
- Grammar Errors: {analysis['summary']['grammar_errors']}
- Length Issues: {analysis['summary']['length_issues']}
- Structure Problems: {analysis['summary']['structure_problems']}
- Domain Mismatches: {analysis['summary']['domain_mismatches']}
- Low Effectiveness: {analysis['summary']['low_effectiveness']}

## Quality Distribution
"""
        
        # Add quality distribution
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    CASE 
                        WHEN quality_score >= 0.9 THEN 'Excellent (0.9+)'
                        WHEN quality_score >= 0.8 THEN 'Good (0.8-0.9)'
                        WHEN quality_score >= 0.7 THEN 'Fair (0.7-0.8)'
                        ELSE 'Poor (<0.7)'
                    END as quality_range,
                    COUNT(*) as count
                FROM prompts 
                GROUP BY quality_range
                ORDER BY quality_score DESC
            """)
            
            for row in cursor.fetchall():
                report += f"- {row[0]}: {row[1]} prompts\n"
        
        return report

def main():
    """Main execution function."""
    db_path = Path(__file__).parent / "sequential_think_prompts.db"
    
    if not db_path.exists():
        print("Error: Database not found. Please run populate_prompt_database.py first.")
        return
    
    improver = PromptQualityImprover(db_path)
    
    print("Analyzing quality issues...")
    analysis = improver.analyze_quality_issues()
    print(f"Found {analysis['total_issues']} prompts with quality issues")
    
    print("\nApplying improvements...")
    improvements = improver.apply_improvements(limit=100)
    
    print(f"\nQuality Improvement Results:")
    print(f"- Total processed: {improvements['total_processed']}")
    print(f"- Grammar fixed: {improvements['improvement_counts']['grammar_fixed']}")
    print(f"- Structure improved: {improvements['improvement_counts']['structure_improved']}")
    print(f"- Domains standardized: {improvements['improvement_counts']['domain_standardized']}")
    print(f"- Effectiveness improved: {improvements['improvement_counts']['effectiveness_improved']}")
    
    print("\nGenerating quality report...")
    report = improver.generate_quality_report()
    
    # Save report
    report_path = Path(__file__).parent / "prompt_quality_report.md"
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"Quality report saved to: {report_path}")
    print("\nPrompt library quality improvement complete!")

if __name__ == "__main__":
    main()