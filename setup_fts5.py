#!/usr/bin/env python3
"""
FTS5 Search Setup Script for Law Analysis Tool
Creates and populates full-text search tables
"""

import sqlite3
import os

DATABASE = "laws.db"

def setup_fts5():
    """Setup FTS5 full-text search tables"""
    
    if not os.path.exists(DATABASE):
        print(f"❌ Database not found: {DATABASE}")
        print("💡 Please run setup_database.py and populate_database.py first")
        return False
    
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    print("🔍 Setting up FTS5 full-text search...")
    
    try:
        # Drop existing FTS5 tables if they exist
        print("   🗑️  Cleaning up existing FTS5 tables...")
        conn.execute("DROP TABLE IF EXISTS law_search_fts")
        conn.execute("DROP TABLE IF EXISTS law_search")
        
        # Create main FTS5 table for comprehensive search
        print("   📝 Creating main FTS5 table...")
        conn.execute("""
        CREATE VIRTUAL TABLE law_search USING fts5(
            law_id UNINDEXED,
            law_name,
            article_id UNINDEXED,
            article_number UNINDEXED,
            article_title,
            sub_article_id UNINDEXED,
            sub_article_label,
            content,
            tokenize='porter'
        )
        """)
        
        # Create specialized FTS5 table for law-level search
        print("   📚 Creating law-level FTS5 table...")
        conn.execute("""
        CREATE VIRTUAL TABLE law_search_fts USING fts5(
            law_name,
            article_title,
            sub_article_text,
            content='',
            tokenize='porter'
        )
        """)
        
        print("   ✅ FTS5 tables created successfully")
        
        # Populate main FTS5 table
        print("   📥 Populating main FTS5 table...")
        conn.execute("""
        INSERT INTO law_search (
            law_id, law_name, article_id, article_number, 
            article_title, sub_article_id, sub_article_label, content
        )
        SELECT 
            l.id,
            l.law_name,
            a.id,
            a.article_number,
            a.article_title,
            sa.id,
            sa.sub_article_label,
            sa.text_content
        FROM sub_articles sa
        JOIN articles a ON sa.article_id = a.id
        JOIN laws l ON a.law_id = l.id
        """)
        
        # Populate specialized FTS5 table
        print("   📥 Populating specialized FTS5 table...")
        conn.execute("""
        INSERT INTO law_search_fts (
            rowid, law_name, article_title, sub_article_text
        )
        SELECT 
            sa.id,
            l.law_name,
            a.article_title,
            sa.text_content
        FROM sub_articles sa
        JOIN articles a ON sa.article_id = a.id
        JOIN laws l ON a.law_id = l.id
        """)
        
        conn.commit()
        print("   ✅ FTS5 tables populated successfully")
        
        # Verify population
        print("   🔍 Verifying FTS5 setup...")
        
        # Check main table
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM law_search")
        main_count = cursor.fetchone()[0]
        
        # Check specialized table
        cursor.execute("SELECT COUNT(*) FROM law_search_fts")
        special_count = cursor.fetchone()[0]
        
        # Check source table for comparison
        cursor.execute("SELECT COUNT(*) FROM sub_articles")
        source_count = cursor.fetchone()[0]
        
        print(f"   📊 FTS5 Records:")
        print(f"      Main table: {main_count:,}")
        print(f"      Specialized table: {special_count:,}")
        print(f"      Source records: {source_count:,}")
        
        if main_count == source_count and special_count == source_count:
            print("   ✅ FTS5 setup verification successful!")
        else:
            print("   ⚠️  FTS5 setup verification: Record counts don't match")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error during FTS5 setup: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return False

def test_search():
    """Test the FTS5 search functionality"""
    
    if not os.path.exists(DATABASE):
        print("❌ Database not found for testing")
        return
    
    conn = sqlite3.connect(DATABASE)
    
    print("\n🧪 Testing FTS5 search functionality...")
    
    try:
        # Test basic search
        cursor = conn.cursor()
        
        # Test 1: Search for "penal" in law names
        print("   🔍 Test 1: Searching for 'penal' in law names...")
        cursor.execute("""
        SELECT DISTINCT law_name FROM law_search 
        WHERE law_name MATCH 'penal' 
        LIMIT 5
        """)
        results = cursor.fetchall()
        if results:
            print(f"      Found {len(results)} laws:")
            for row in results:
                print(f"         - {row[0]}")
        else:
            print("      No results found")
        
        # Test 2: Search for "tax" in content
        print("   🔍 Test 2: Searching for 'tax' in content...")
        cursor.execute("""
        SELECT law_name, article_title, sub_article_label 
        FROM law_search 
        WHERE content MATCH 'tax' 
        LIMIT 3
        """)
        results = cursor.fetchall()
        if results:
            print(f"      Found {len(results)} matches:")
            for row in results:
                print(f"         - {row[0]} > {row[1]} > {row[2]}")
        else:
            print("      No results found")
        
        # Test 3: Search for "environment" in specialized table
        print("   🔍 Test 3: Searching for 'environment' in specialized table...")
        cursor.execute("""
        SELECT law_name, article_title 
        FROM law_search_fts 
        WHERE sub_article_text MATCH 'environment' 
        LIMIT 3
        """)
        results = cursor.fetchall()
        if results:
            print(f"      Found {len(results)} matches:")
            for row in results:
                print(f"         - {row[0]} > {row[1]}")
        else:
            print("      No results found")
        
        print("   ✅ FTS5 search tests completed")
        
    except Exception as e:
        print(f"   ❌ Error during search testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

def main():
    """Main execution function"""
    
    print("🔍 FTS5 Search Setup Script")
    print("=" * 50)
    
    # Setup FTS5
    success = setup_fts5()
    
    if success:
        print("\n🎉 FTS5 setup completed successfully!")
        
        # Test search functionality
        test_search()
        
        print("\n💡 FTS5 is now ready for use in the Flask app!")
        print("   The app can now perform full-text searches across:")
        print("   - Law names")
        print("   - Article titles") 
        print("   - Sub-article content")
        print("   - All text content with proper indexing")
        
    else:
        print("\n❌ FTS5 setup failed!")

if __name__ == "__main__":
    main()
