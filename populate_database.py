#!/usr/bin/env python3
"""
Database Population Script for Law Analysis Tool
Populates the database with parsed law data
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

DATABASE = "laws.db"

class DatabasePopulator:
    def __init__(self, database_path: str = DATABASE):
        self.database_path = database_path
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Connect to the database"""
        self.conn = sqlite3.connect(self.database_path)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.cursor = self.conn.cursor()
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            
    def load_parsed_data(self, json_file: str = "parsed_laws.json") -> List[Dict]:
        """Load parsed law data from JSON file"""
        
        if not os.path.exists(json_file):
            print(f"❌ Parsed data file not found: {json_file}")
            print("💡 Please run parse_laws.py first to generate parsed data")
            return []
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ Loaded parsed data: {len(data)} laws")
            return data
        except Exception as e:
            print(f"❌ Failed to load parsed data: {e}")
            return []
    
    def populate_laws(self, parsed_laws: List[Dict]) -> Dict[int, int]:
        """Insert laws into the database and return mapping of parsed index to database ID"""
        
        print("📚 Populating laws table...")
        
        law_mapping = {}  # parsed_index -> database_id
        
        for idx, law in enumerate(parsed_laws):
            try:
                self.cursor.execute("""
                    INSERT INTO laws (law_name, file_name, category_name)
                    VALUES (?, ?, ?)
                """, (
                    law['law_info']['law_name'],
                    law['file_name'],
                    law['law_info']['category_name']
                ))
                
                law_id = self.cursor.lastrowid
                law_mapping[idx] = law_id
                print(f"   ✅ Added law: {law['law_info']['law_name']} (ID: {law_id})")
                
            except Exception as e:
                print(f"   ❌ Failed to add law {law['law_info']['law_name']}: {e}")
                law_mapping[idx] = None
        
        self.conn.commit()
        print(f"✅ Added {len([v for v in law_mapping.values() if v is not None])} laws")
        return law_mapping
    
    def populate_parts(self, parsed_laws: List[Dict], law_mapping: Dict[int, int]) -> Dict[str, int]:
        """Insert parts into the database and return mapping of part identifier to database ID"""
        
        print("📖 Populating parts table...")
        
        part_mapping = {}  # "law_id:part_number" -> database_id
        
        for parsed_idx, law in enumerate(parsed_laws):
            law_id = law_mapping[parsed_idx]
            if law_id is None:
                continue
                
            for part in law['structure']['parts']:
                try:
                    self.cursor.execute("""
                        INSERT INTO parts (law_id, part_number, part_title)
                        VALUES (?, ?, ?)
                    """, (
                        law_id,
                        part['part_number'],
                        part['part_title']
                    ))
                    
                    part_id = self.cursor.lastrowid
                    part_key = f"{law_id}:{part['part_number']}"
                    part_mapping[part_key] = part_id
                    print(f"   ✅ Added part: {part['part_title']} (ID: {part_id})")
                    
                except Exception as e:
                    print(f"   ❌ Failed to add part {part['part_title']}: {e}")
                    part_key = f"{law_id}:{part['part_number']}"
                    part_mapping[part_key] = None
        
        self.conn.commit()
        print(f"✅ Added {len([v for v in part_mapping.values() if v is not None])} parts")
        return part_mapping
    
    def populate_chapters(self, parsed_laws: List[Dict], part_mapping: Dict[str, int]) -> Dict[str, int]:
        """Insert chapters into the database and return mapping of chapter identifier to database ID"""
        
        print("📋 Populating chapters table...")
        
        chapter_mapping = {}  # "part_id:chapter_number" -> database_id
        
        for law in parsed_laws:
            for chapter in law['structure']['chapters']:
                if chapter['part_number']:
                    part_key = f"{law['law_id']}:{chapter['part_number']}"
                    part_id = part_mapping.get(part_key)
                    
                    if part_id is None:
                        continue
                        
                    try:
                        self.cursor.execute("""
                            INSERT INTO chapters (part_id, chapter_number, chapter_title)
                            VALUES (?, ?, ?)
                        """, (
                            part_id,
                            chapter['chapter_number'],
                            chapter['chapter_title']
                        ))
                        
                        chapter_id = self.cursor.lastrowid
                        chapter_key = f"{part_id}:{chapter['chapter_number']}"
                        chapter_mapping[chapter_key] = chapter_id
                        print(f"   ✅ Added chapter: {chapter['chapter_title']} (ID: {chapter_id})")
                        
                    except Exception as e:
                        print(f"   ❌ Failed to add chapter {chapter['chapter_title']}: {e}")
                        chapter_key = f"{part_id}:{chapter['chapter_number']}"
                        chapter_mapping[chapter_key] = None
        
        self.conn.commit()
        print(f"✅ Added {len([v for v in chapter_mapping.values() if v is not None])} chapters")
        return chapter_mapping
    
    def populate_articles(self, parsed_laws: List[Dict], law_mapping: Dict[int, int], 
                         chapter_mapping: Dict[str, int]) -> Dict[str, int]:
        """Insert articles into the database and return mapping of article identifier to database ID"""
        
        print("📝 Populating articles table...")
        
        article_mapping = {}  # "law_id:article_number" -> database_id
        
        for parsed_idx, law in enumerate(parsed_laws):
            law_id = law_mapping[parsed_idx]
            if law_id is None:
                continue
                
            for article in law['articles']:
                try:
                    # Find chapter_id if this article belongs to a chapter
                    chapter_id = None
                    if article['chapter_id']:
                        # Find the chapter in the mapping
                        for chapter_key, ch_id in chapter_mapping.items():
                            if ch_id is not None:
                                # Extract part_id from chapter_key
                                part_id = int(chapter_key.split(':')[0])
                                # Check if this part belongs to our law
                                if part_id in [p for p in part_mapping.values() if p is not None]:
                                    chapter_id = ch_id
                                    break
                    
                    self.cursor.execute("""
                        INSERT INTO articles (law_id, article_number, article_title, chapter_id)
                        VALUES (?, ?, ?, ?)
                    """, (
                        law_id,
                        article['article_number'],
                        article['article_title'],
                        chapter_id
                    ))
                    
                    article_id = self.cursor.lastrowid
                    article_key = f"{law_id}:{article['article_number']}"
                    article_mapping[article_key] = article_id
                    print(f"   ✅ Added article: {article['article_title']} (ID: {article_id})")
                    
                except Exception as e:
                    print(f"   ❌ Failed to add article {article['article_title']}: {e}")
                    article_key = f"{law_id}:{article['article_number']}"
                    article_mapping[article_key] = None
        
        self.conn.commit()
        print(f"✅ Added {len([v for v in article_mapping.values() if v is not None])} articles")
        return article_mapping
    
    def populate_sub_articles(self, parsed_laws: List[Dict], article_mapping: Dict[str, int], law_mapping: Dict[int, int]):
        """Insert sub-articles into the database"""
        
        print("📄 Populating sub-articles table...")
        
        total_sub_articles = 0
        
        for parsed_idx, law in enumerate(parsed_laws):
            law_id = law_mapping[parsed_idx]
            if law_id is None:
                continue
                
            for article in law['articles']:
                article_key = f"{law_id}:{article['article_number']}"
                article_id = article_mapping.get(article_key)
                
                if article_id is None:
                    continue
                    
                for sub_article in article['sub_articles']:
                    try:
                        self.cursor.execute("""
                            INSERT INTO sub_articles (article_id, sub_article_label, text_content)
                            VALUES (?, ?, ?)
                        """, (
                            article_id,
                            sub_article['sub_article_label'],
                            sub_article['text_content']
                        ))
                        
                        total_sub_articles += 1
                        
                    except Exception as e:
                        print(f"   ❌ Failed to add sub-article {sub_article['sub_article_label']}: {e}")
        
        self.conn.commit()
        print(f"✅ Added {total_sub_articles} sub-articles")
    
    def populate_database(self, parsed_laws: List[Dict]):
        """Main method to populate the entire database"""
        
        print("🚀 Starting database population...")
        print("=" * 50)
        
        try:
            self.connect()
            
            # Step 1: Populate laws
            law_mapping = self.populate_laws(parsed_laws)
            
            # Step 2: Populate parts
            part_mapping = self.populate_parts(parsed_laws, law_mapping)
            
            # Step 3: Populate chapters
            chapter_mapping = self.populate_chapters(parsed_laws, part_mapping)
            
            # Step 4: Populate articles
            article_mapping = self.populate_articles(parsed_laws, law_mapping, chapter_mapping)
            
            # Step 5: Populate sub-articles
            self.populate_sub_articles(parsed_laws, article_mapping, law_mapping)
            
            print("\n🎉 Database population completed successfully!")
            
            # Print summary
            self.print_summary()
            
        except Exception as e:
            print(f"\n💥 Error during population: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.close()
    
    def print_summary(self):
        """Print summary of populated data"""
        
        self.connect()
        
        try:
            # Count records in each table
            tables = ['laws', 'parts', 'chapters', 'articles', 'sub_articles']
            
            print("\n📊 Database Population Summary:")
            print("-" * 40)
            
            for table in tables:
                self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = self.cursor.fetchone()[0]
                print(f"   {table.capitalize()}: {count:,}")
                
        except Exception as e:
            print(f"❌ Error getting summary: {e}")
        finally:
            self.close()

def main():
    """Main execution function"""
    
    print("🗄️  Database Population Script")
    print("=" * 50)
    
    # Check if database exists
    if not os.path.exists(DATABASE):
        print(f"❌ Database not found: {DATABASE}")
        print("💡 Please run setup_database.py first to create the database")
        return
    
    # Check if parsed data exists
    if not os.path.exists("parsed_laws.json"):
        print("❌ Parsed data not found: parsed_laws.json")
        print("💡 Please run parse_laws.py first to generate parsed data")
        return
    
    # Start population
    populator = DatabasePopulator()
    parsed_laws = populator.load_parsed_data()
    
    if parsed_laws:
        populator.populate_database(parsed_laws)
    else:
        print("❌ No parsed data to populate")

if __name__ == "__main__":
    main()
