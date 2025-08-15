#!/usr/bin/env python3
"""
Database Setup Script for Law Analysis Tool
Creates all necessary tables with proper relationships and indexes
"""

import sqlite3
import os
from datetime import datetime

DATABASE = "laws.db"
BACKUP_DB = "BAKlaws.db"

def create_database():
    """Create the laws database with proper schema"""
    
    # Backup existing database if it exists
    if os.path.exists(DATABASE):
        backup_name = f"laws_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        os.rename(DATABASE, backup_name)
        print(f"✅ Backed up existing database to {backup_name}")
    
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    print("🔧 Creating database schema...")
    
    # Create laws table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS laws (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        law_name TEXT NOT NULL,
        file_name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        category_name TEXT
    )
    """)
    
    # Create parts table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS parts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        law_id INTEGER NOT NULL,
        part_number TEXT NOT NULL,
        part_title TEXT,
        FOREIGN KEY (law_id) REFERENCES laws(id)
    )
    """)
    
    # Create chapters table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS chapters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        part_id INTEGER NOT NULL,
        chapter_number TEXT NOT NULL,
        chapter_title TEXT,
        FOREIGN KEY (part_id) REFERENCES parts(id)
    )
    """)
    
    # Create articles table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        law_id INTEGER NOT NULL,
        article_number INTEGER NOT NULL,
        article_title TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        chapter_id INTEGER,
        FOREIGN KEY (law_id) REFERENCES laws(id),
        FOREIGN KEY (chapter_id) REFERENCES chapters(id)
    )
    """)
    
    # Create sub_articles table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS sub_articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER NOT NULL,
        sub_article_label TEXT NOT NULL,
        text_content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (article_id) REFERENCES articles(id)
    )
    """)
    
    # Create votes table (for future features)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        vote TEXT NOT NULL,
        reasoning TEXT,
        voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (article_id) REFERENCES articles(id)
    )
    """)
    
    # Create indexes for performance
    print("📊 Creating indexes...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_laws_name ON laws(law_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_law_id ON articles(law_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_number ON articles(article_number)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sub_articles_article_id ON sub_articles(article_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_parts_law_id ON parts(law_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chapters_part_id ON chapters(part_id)")
    
    conn.commit()
    conn.close()
    
    print("✅ Database schema created successfully!")
    print(f"📁 Database file: {DATABASE}")
    
    return True

def verify_schema():
    """Verify the created schema matches expected structure"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = ['laws', 'parts', 'chapters', 'articles', 'sub_articles', 'votes']
    
    print("\n🔍 Schema Verification:")
    for table in expected_tables:
        if table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            print(f"✅ {table}: {len(columns)} columns")
        else:
            print(f"❌ {table}: MISSING")
    
    conn.close()
    
    return all(table in tables for table in expected_tables)

if __name__ == "__main__":
    print("🚀 Setting up Law Analysis Tool Database")
    print("=" * 50)
    
    try:
        success = create_database()
        if success:
            verify_schema()
            print("\n🎉 Database setup complete! Ready for data population.")
        else:
            print("\n❌ Database setup failed!")
            
    except Exception as e:
        print(f"\n💥 Error during setup: {e}")
        import traceback
        traceback.print_exc()
