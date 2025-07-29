#!/usr/bin/env python3
"""
Automated Sync System for Sequential Think Prompt Data
Maintains synchronization between JSON files, Markdown docs, and SQLite database.
"""

import json
import sqlite3
import shutil
from pathlib import Path
from typing import Dict, List, Any, Set
from datetime import datetime
import hashlib


class PromptDataSyncer:
    """Automated synchronization system for prompt data sources."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.sequential_think_path = base_path / "sequential-think"
        self.db_path = base_path / "sequential_think_prompts.db"
        self.backup_path = base_path / "backups"
        self.backup_path.mkdir(exist_ok=True)

        self.source_files = {
            'json_exports': [
                "ai/exports/prompts-by-complexity.json",
                "ai/exports/prompts-by-domain.json",
                "ai/exports/production-prompts.json"
            ],
            'enhanced_collections': [
                "ai/enhanced-demo/enhanced-prompts.json",
                "ai/omom-optimized/enhanced-prompts.json"
            ],
            'markdown_docs': [
                "sequentialthinking-prompts.md",
                "universal-prompt-collection.md"
            ]
        }

    def create_backup(self) -> str:
        """Create timestamped backup of current database."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"prompts_backup_{timestamp}.db"
        backup_file = self.backup_path / backup_name

        if self.db_path.exists():
            shutil.copy2(self.db_path, backup_file)
            return str(backup_file)
        return ""

    def detect_changes(self) -> Dict[str, Any]:
        """Detect changes in source files since last sync."""
        changes = {
            'modified_files': [],
            'new_files': [],
            'database_outdated': False,
            'last_sync': None
        }

        # Check if database exists and get last modification time
        if self.db_path.exists():
            db_mtime = self.db_path.stat().st_mtime
        else:
            changes['database_outdated'] = True
            return changes

        # Check source files
        for category, file_list in self.source_files.items():
            for file_path in file_list:
                full_path = self.sequential_think_path / file_path
                if full_path.exists():
                    file_mtime = full_path.stat().st_mtime
                    if file_mtime > db_mtime:
                        changes['modified_files'].append({
                            'path': file_path,
                            'category': category,
                            'modified': datetime.fromtimestamp(file_mtime).isoformat()
                        })

        changes['database_outdated'] = len(changes['modified_files']) > 0

        return changes

    def export_database_to_json(self, output_file: Path = None) -> str:  # type: ignore
        """Export current database to consolidated JSON format."""
        if not output_file:
            output_file = self.base_path / \
                f"consolidated_prompts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Export prompts
            cursor = conn.execute("""
                SELECT id, hash, title, content, original_prompt, enhanced_prompt,
                       category, complexity_level, domain, tags, effectiveness_score,
                       quality_score, usage_count, source_file, created_at, updated_at
                FROM prompts 
                ORDER BY effectiveness_score DESC, quality_score DESC
            """)

            prompts = [dict(row) for row in cursor.fetchall()]

            # Export frameworks
            cursor = conn.execute("SELECT * FROM frameworks")
            frameworks = [dict(row) for row in cursor.fetchall()]

            # Export statistics
            cursor = conn.execute(
                "SELECT COUNT(*) as total_prompts FROM prompts")
            total_prompts = cursor.fetchone()['total_prompts']

            cursor = conn.execute(
                "SELECT AVG(quality_score) as avg_quality, AVG(effectiveness_score) as avg_effectiveness FROM prompts")
            averages = cursor.fetchone()

            export_data = {
                'metadata': {
                    'export_date': datetime.now().isoformat(),
                    'total_prompts': total_prompts,
                    'average_quality': averages['avg_quality'],
                    'average_effectiveness': averages['avg_effectiveness']
                },
                'prompts': prompts,
                'frameworks': frameworks
            }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return str(output_file)

    def update_production_exports(self):
        """Update production-ready export files."""
        export_dir = self.sequential_think_path / "ai" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Export by complexity
            complexity_data = {}
            for level in ['L1', 'L2', 'L3', 'L4', 'L5']:
                cursor = conn.execute("""
                    SELECT * FROM prompts 
                    WHERE complexity_level = ? AND quality_score >= 0.7
                    ORDER BY effectiveness_score DESC
                    LIMIT 20
                """, (level,))

                complexity_data[level] = [dict(row)
                                          for row in cursor.fetchall()]

            with open(export_dir / "prompts-by-complexity.json", 'w') as f:
                json.dump(complexity_data, f, indent=2, default=str)

            # Export by domain
            cursor = conn.execute("""
                SELECT domain, COUNT(*) as count 
                FROM prompts 
                WHERE quality_score >= 0.7
                GROUP BY domain 
                ORDER BY count DESC
            """)

            domain_data = {}
            for row in cursor.fetchall():
                domain = row['domain']
                cursor2 = conn.execute("""
                    SELECT * FROM prompts 
                    WHERE domain = ? AND quality_score >= 0.7
                    ORDER BY effectiveness_score DESC
                    LIMIT 15
                """, (domain,))

                domain_data[domain] = [dict(row) for row in cursor2.fetchall()]

            with open(export_dir / "prompts-by-domain.json", 'w') as f:
                json.dump(domain_data, f, indent=2, default=str)

            # Export high-quality production prompts
            cursor = conn.execute("""
                SELECT * FROM prompts 
                WHERE quality_score >= 0.8 AND effectiveness_score >= 0.7
                ORDER BY (quality_score * 0.6 + effectiveness_score * 0.4) DESC
                LIMIT 50
            """)

            production_prompts = [dict(row) for row in cursor.fetchall()]

            with open(export_dir / "production-prompts.json", 'w') as f:
                json.dump({
                    'metadata': {
                        'selection_criteria': 'quality_score >= 0.8 AND effectiveness_score >= 0.7',
                        'export_date': datetime.now().isoformat(),
                        'total_selected': len(production_prompts)
                    },
                    'prompts': production_prompts
                }, f, indent=2, default=str)

    def generate_sync_report(self, changes: Dict[str, Any]) -> str:
        """Generate comprehensive sync report."""
        report = f"""
# Sequential Think Data Sync Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Sync Status
- Database exists: {'✅' if self.db_path.exists() else '❌'}
- Files modified since last sync: {len(changes['modified_files'])}
- Sync required: {'✅' if changes['database_outdated'] else '❌'}

## Modified Files
"""

        if changes['modified_files']:
            for file_info in changes['modified_files']:
                report += f"- {file_info['path']} ({file_info['category']}) - Modified: {file_info['modified']}\n"
        else:
            report += "- No files modified since last sync\n"

        # Add database statistics if database exists
        if self.db_path.exists():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) as total FROM prompts")
                total = cursor.fetchone()['total']

                cursor = conn.execute(
                    "SELECT COUNT(*) as high_quality FROM prompts WHERE quality_score >= 0.8")
                high_quality = cursor.fetchone()['high_quality']

                report += f"""
## Database Statistics
- Total prompts: {total}
- High-quality prompts (≥0.8): {high_quality} ({(high_quality/total*100):.1f}%)
- Database size: {self.db_path.stat().st_size / 1024:.1f} KB
"""

        # Add backup information
        backups = list(self.backup_path.glob("prompts_backup_*.db"))
        if backups:
            latest_backup = max(backups, key=lambda p: p.stat().st_mtime)
            report += f"""
## Backup Status
- Total backups: {len(backups)}
- Latest backup: {latest_backup.name}
- Backup age: {datetime.now() - datetime.fromtimestamp(latest_backup.stat().st_mtime)}
"""

        return report

    def full_sync(self, force: bool = False) -> Dict[str, Any]:
        """Perform full synchronization of all data sources."""
        sync_results = {
            'backup_created': '',
            'database_updated': False,
            'exports_updated': False,
            'errors': [],
            'sync_time': datetime.now().isoformat()
        }

        try:
            # Detect changes
            changes = self.detect_changes()

            if not changes['database_outdated'] and not force:
                return {**sync_results, 'message': 'No sync required - all data sources up to date'}

            # Create backup
            if self.db_path.exists():
                backup_file = self.create_backup()
                sync_results['backup_created'] = backup_file

            # Repopulate database
            from populate_prompt_database import PromptDatabasePopulator

            populator = PromptDatabasePopulator(
                self.db_path, self.sequential_think_path)
            populator.populate_database()
            sync_results['database_updated'] = True

            # Apply quality improvements
            from prompt_quality_improver import PromptQualityImprover

            improver = PromptQualityImprover(self.db_path)
            improvements = improver.apply_improvements(limit=200)
            sync_results['quality_improvements'] = improvements['improvement_counts']

            # Update production exports
            self.update_production_exports()
            sync_results['exports_updated'] = True

        except Exception as e:
            sync_results['errors'].append(str(e))

        return sync_results

    def cleanup_old_backups(self, keep_count: int = 10):
        """Remove old backup files, keeping only the most recent ones."""
        backups = sorted(self.backup_path.glob("prompts_backup_*.db"),
                         key=lambda p: p.stat().st_mtime, reverse=True)

        for backup in backups[keep_count:]:
            backup.unlink()

        return len(backups) - keep_count if len(backups) > keep_count else 0


def main():
    """Main sync execution."""
    base_path = Path(__file__).parent
    syncer = PromptDataSyncer(base_path)

    print("🔄 Sequential Think Data Sync Started")

    # Detect changes
    changes = syncer.detect_changes()
    print(
        f"📊 Change Detection: {len(changes['modified_files'])} files modified")

    # Generate sync report
    report = syncer.generate_sync_report(changes)

    # Save report
    report_path = base_path / "sync_report.md"
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"📋 Sync report saved to: {report_path}")

    # Perform sync if needed
    if changes['database_outdated'] or input("\nForce full sync? (y/N): ").lower() == 'y':
        print("🚀 Starting full synchronization...")

        results = syncer.full_sync(force=True)

        print("\n✅ Sync Results:")
        print(f"- Backup created: {results.get('backup_created', 'None')}")
        print(f"- Database updated: {results['database_updated']}")
        print(f"- Exports updated: {results['exports_updated']}")

        if 'quality_improvements' in results:
            improvements = results['quality_improvements']
            print(f"- Quality improvements:")
            print(f"  • Grammar fixed: {improvements['grammar_fixed']}")
            print(
                f"  • Structure improved: {improvements['structure_improved']}")
            print(
                f"  • Domains standardized: {improvements['domain_standardized']}")

        if results['errors']:
            print(f"⚠️  Errors encountered: {len(results['errors'])}")
            for error in results['errors']:
                print(f"  - {error}")

        # Cleanup old backups
        removed = syncer.cleanup_old_backups(keep_count=5)
        if removed > 0:
            print(f"🧹 Cleaned up {removed} old backup files")

        # Export consolidated data
        export_file = syncer.export_database_to_json()
        print(f"📤 Consolidated export saved to: {export_file}")

    else:
        print("✅ All data sources are up to date - no sync required")

    print("\n🎉 Sequential Think Data Sync Complete!")


if __name__ == "__main__":
    main()
