#!/usr/bin/env python3
import sqlite3
import json
import sys

def get_database_stats():
    """Get simple database statistics"""
    try:
        conn = sqlite3.connect('sequential_think_prompts.db')
        conn.row_factory = sqlite3.Row
        
        # Get basic stats
        cursor = conn.execute("SELECT COUNT(*) as total FROM prompts")
        total = cursor.fetchone()['total']
        
        cursor = conn.execute("SELECT COUNT(*) as high_quality FROM prompts WHERE quality_score >= 0.8")
        high_quality = cursor.fetchone()['high_quality']
        
        cursor = conn.execute("SELECT domain, COUNT(*) as count FROM prompts GROUP BY domain ORDER BY count DESC LIMIT 5")
        domains = [dict(row) for row in cursor.fetchall()]
        
        stats = {
            "total_prompts": total,
            "high_quality_prompts": high_quality,
            "top_domains": domains,
            "database_file": "sequential_think_prompts.db"
        }
        
        conn.close()
        return json.dumps(stats, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        print(get_database_stats())
    else:
        print("Usage: python simple-cli-test.py stats")