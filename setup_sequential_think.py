#!/usr/bin/env python3
"""
Setup script for Sequential Think MCP Server
Initializes the prompt database with sample data from the TypeScript collection.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List

PROMPTS_DB_PATH = Path(__file__).parent / "sequential_think_prompts.db"
SEQUENTIAL_THINK_PATH = Path(__file__).parent / "sequential-think"


def init_database():
    """Initialize the SQLite database with schema and indexes."""
    with sqlite3.connect(PROMPTS_DB_PATH) as conn:
        # Create tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                complexity_level TEXT NOT NULL,
                domain TEXT NOT NULL,
                tags TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS frameworks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                methodology TEXT NOT NULL,
                use_cases TEXT NOT NULL,
                complexity_range TEXT NOT NULL
            )
        """)

        # Create FTS5 virtual table for full-text search
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS prompts_fts USING fts5(
                title, content, category, domain, tags, content=prompts
            )
        """)

        # Create indexes
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_category ON prompts(category)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_complexity ON prompts(complexity_level)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_domain ON prompts(domain)")

        conn.commit()
        print("✅ Database schema initialized")


def load_sample_prompts():
    """Load sample prompts into the database."""
    sample_prompts = [
        {
            "title": "React Performance Optimization",
            "content": "How do I optimize React application performance considering component re-renders, state management, and bundle size?",
            "category": "Development",
            "complexity_level": "L3",
            "domain": "Frontend",
            "tags": "react,performance,optimization,state-management"
        },
        {
            "title": "Systematic Debugging Analysis",
            "content": "Execute comprehensive debugging analysis for production API failures using 5-phase methodology",
            "category": "Problem Solving",
            "complexity_level": "L4",
            "domain": "Backend",
            "tags": "debugging,api,production,methodology"
        },
        {
            "title": "Microservices Architecture Design",
            "content": "Design scalable microservices architecture considering service boundaries, communication patterns, and data consistency",
            "category": "Architecture",
            "complexity_level": "L5",
            "domain": "System Design",
            "tags": "microservices,architecture,scalability,distributed-systems"
        },
        {
            "title": "Database Migration Strategy",
            "content": "Plan database migration from monolithic to distributed architecture with zero downtime",
            "category": "Migration",
            "complexity_level": "L4",
            "domain": "Database",
            "tags": "database,migration,distributed,zero-downtime"
        },
        {
            "title": "CI/CD Pipeline Optimization",
            "content": "Optimize CI/CD pipeline for faster deployment cycles and improved reliability",
            "category": "DevOps",
            "complexity_level": "L3",
            "domain": "Infrastructure",
            "tags": "cicd,deployment,automation,reliability"
        },
        {
            "title": "Code Review Best Practices",
            "content": "How do I establish effective code review practices for my development team?",
            "category": "Process",
            "complexity_level": "L2",
            "domain": "Team Management",
            "tags": "code-review,team-process,best-practices"
        },
        {
            "title": "Security Vulnerability Assessment",
            "content": "Conduct comprehensive security assessment of web application identifying potential vulnerabilities",
            "category": "Security",
            "complexity_level": "L4",
            "domain": "Web Security",
            "tags": "security,vulnerability,assessment,web-application"
        },
        {
            "title": "API Design Guidelines",
            "content": "Design RESTful API following best practices for scalability and maintainability",
            "category": "API Design",
            "complexity_level": "L3",
            "domain": "Backend",
            "tags": "api,rest,design,scalability,maintainability"
        },
        {
            "title": "Docker Container Optimization",
            "content": "Optimize Docker containers for production deployment considering security and performance",
            "category": "DevOps",
            "complexity_level": "L3",
            "domain": "Containerization",
            "tags": "docker,containers,optimization,production,security"
        },
        {
            "title": "Technical Debt Management",
            "content": "How do I prioritize and systematically address technical debt in legacy codebase?",
            "category": "Code Quality",
            "complexity_level": "L4",
            "domain": "Legacy Systems",
            "tags": "technical-debt,legacy,code-quality,prioritization"
        }
    ]

    with sqlite3.connect(PROMPTS_DB_PATH) as conn:
        for prompt in sample_prompts:
            conn.execute("""
                INSERT INTO prompts (title, content, category, complexity_level, domain, tags)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                prompt["title"],
                prompt["content"],
                prompt["category"],
                prompt["complexity_level"],
                prompt["domain"],
                prompt["tags"]
            ))

        # Update FTS5 table
        conn.execute("INSERT INTO prompts_fts(prompts_fts) VALUES('rebuild')")
        conn.commit()
        print(f"✅ Loaded {len(sample_prompts)} sample prompts")


def load_frameworks():
    """Load framework definitions into the database."""
    frameworks = [
        {
            "name": "Enhanced Debugging Framework",
            "description": "5-phase systematic debugging methodology with evidence-based analysis",
            "methodology": "Phase 1: Problem Identification, Phase 2: Hypothesis Formation, Phase 3: Root Cause Analysis, Phase 4: Solution Implementation, Phase 5: Verification",
            "use_cases": "Production issues, complex bugs, system failures, performance problems",
            "complexity_range": "L3-L5"
        },
        {
            "name": "Prompt Taxonomy Classification",
            "description": "Multi-dimensional classification system with L1-L5 complexity levels",
            "methodology": "Classify prompts by complexity, domain, and context requirements",
            "use_cases": "Prompt optimization, complexity assessment, systematic problem-solving",
            "complexity_range": "L1-L5"
        },
        {
            "name": "Cross-Reference System",
            "description": "Semantic relationship mapping with prerequisite and progression tracking",
            "methodology": "Map knowledge dependencies and create adaptive learning paths",
            "use_cases": "Knowledge management, learning path design, skill development",
            "complexity_range": "L2-L4"
        },
        {
            "name": "Implementation Protocol",
            "description": "16-week enhancement roadmap with validation criteria and success metrics",
            "methodology": "Foundation → Enhancement → Integration → Optimization phases",
            "use_cases": "Project planning, systematic implementation, milestone tracking",
            "complexity_range": "L4-L5"
        }
    ]

    with sqlite3.connect(PROMPTS_DB_PATH) as conn:
        for framework in frameworks:
            conn.execute("""
                INSERT INTO frameworks (name, description, methodology, use_cases, complexity_range)
                VALUES (?, ?, ?, ?, ?)
            """, (
                framework["name"],
                framework["description"],
                framework["methodology"],
                framework["use_cases"],
                framework["complexity_range"]
            ))

        conn.commit()
        print(f"✅ Loaded {len(frameworks)} framework definitions")


def check_typescript_integration():
    """Check if TypeScript sequential-think system is available."""
    if SEQUENTIAL_THINK_PATH.exists():
        print("✅ TypeScript Sequential Think system found")

        cli_path = SEQUENTIAL_THINK_PATH / "ai" / "cli.ts"
        if cli_path.exists():
            print("✅ Sequential Think CLI found")
        else:
            print("⚠️  Sequential Think CLI not found at expected location")

        package_json = SEQUENTIAL_THINK_PATH / "package.json"
        if package_json.exists():
            print("✅ Node.js dependencies configured")
        else:
            print("⚠️  package.json not found")
    else:
        print("⚠️  TypeScript Sequential Think system not found")
        print("   The Python MCP server will work with local LLM only")


def main():
    """Main setup function."""
    print("🚀 Setting up Sequential Think MCP Server")
    print("=" * 50)

    # Initialize database
    print("\n📚 Initializing database...")
    init_database()

    # Load sample data
    print("\n📝 Loading sample prompts...")
    load_sample_prompts()

    print("\n🧠 Loading framework definitions...")
    load_frameworks()

    # Check TypeScript integration
    print("\n🔗 Checking TypeScript integration...")
    check_typescript_integration()

    print("\n✨ Setup complete!")
    print("\nNext steps:")
    print("1. Install Ollama: https://ollama.ai/")
    print("2. Install a model: ollama pull llama3.2:1b")
    print("3. Start the server: python sequential_think_server.py")
    print("4. Add to Claude Desktop config for MCP integration")

    print(f"\nDatabase created at: {PROMPTS_DB_PATH}")


if __name__ == "__main__":
    main()
