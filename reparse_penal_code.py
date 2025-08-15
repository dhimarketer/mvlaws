#!/usr/bin/env python3
"""
Script to re-parse the Maldives Penal Code and update the database
"""

import sqlite3
import os
from parse_laws import LawParser
from pathlib import Path

def reparse_penal_code():
    """Re-parse the penal code and update the database"""
    
    print("🔍 Re-parsing Maldives Penal Code...")
    
    # Initialize parser
    parser = LawParser()
    
    # Parse the penal code file specifically
    penal_code_path = Path("laws/MALDIVES PENAL CODE .txt")
    
    if not penal_code_path.exists():
        print(f"❌ Penal code file not found: {penal_code_path}")
        return False
    
    try:
        # Parse the penal code
        parsed_law = parser.parse_law_file(penal_code_path)
        
        print(f"✅ Parsed penal code: {len(parsed_law['articles'])} articles, {sum(len(article['sub_articles']) for article in parsed_law['articles'])} sub-articles")
        
        # Connect to database
        conn = sqlite3.connect('laws.db')
        cursor = conn.cursor()
        
        # Remove existing penal code entries
        print("🗑️ Removing existing penal code entries...")
        cursor.execute("DELETE FROM sub_articles WHERE article_id IN (SELECT id FROM articles WHERE law_id IN (SELECT id FROM laws WHERE law_name LIKE '%PENAL CODE%'))")
        cursor.execute("DELETE FROM articles WHERE law_id IN (SELECT id FROM laws WHERE law_name LIKE '%PENAL CODE%')")
        cursor.execute("DELETE FROM laws WHERE law_name LIKE '%PENAL CODE%'")
        
        # Insert new penal code
        print("💾 Inserting new penal code data...")
        
        # Insert law
        cursor.execute("""
            INSERT INTO laws (law_name, file_name, category_name)
            VALUES (?, ?, ?)
        """, (
            parsed_law['law_info']['law_name'],
            parsed_law['file_name'],
            parsed_law['law_info']['category_name']
        ))
        
        law_id = cursor.lastrowid
        
        # Insert articles
        for article in parsed_law['articles']:
            cursor.execute("""
                INSERT INTO articles (law_id, article_number, article_title)
                VALUES (?, ?, ?)
            """, (
                law_id,
                article['article_number'],
                article['article_title']
            ))
            
            article_id = cursor.lastrowid
            
            # Insert sub-articles
            for sub_article in article['sub_articles']:
                cursor.execute("""
                    INSERT INTO sub_articles (article_id, sub_article_label, text_content)
                    VALUES (?, ?, ?)
                """, (
                    article_id,
                    sub_article['sub_article_label'],
                    sub_article['text_content']
                ))
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print(f"✅ Successfully updated database with {len(parsed_law['articles'])} articles and {sum(len(article['sub_articles']) for article in parsed_law['articles'])} sub-articles")
        
        # Test search for murder/homicide
        print("\n🔍 Testing search for 'murder'...")
        conn = sqlite3.connect('laws.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM sub_articles 
            JOIN articles ON sub_articles.article_id = articles.id 
            JOIN laws ON articles.law_id = laws.id 
            WHERE laws.law_name LIKE '%PENAL CODE%' 
            AND (sub_articles.text_content LIKE '%murder%' OR sub_articles.text_content LIKE '%homicide%')
        """)
        
        count = cursor.fetchone()[0]
        print(f"Found {count} references to murder/homicide in penal code")
        
        if count > 0:
            cursor.execute("""
                SELECT articles.article_number, articles.article_title, sub_articles.text_content 
                FROM sub_articles 
                JOIN articles ON sub_articles.article_id = articles.id 
                JOIN laws ON articles.law_id = laws.id 
                WHERE laws.law_name LIKE '%PENAL CODE%' 
                AND (sub_articles.text_content LIKE '%murder%' OR sub_articles.text_content LIKE '%homicide%')
                LIMIT 3
            """)
            
            results = cursor.fetchall()
            print("\nSample results:")
            for result in results:
                print(f"Article {result[0]}: {result[1]}")
                print(f"Content: {result[2][:100]}...")
                print()
        
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error re-parsing penal code: {e}")
        return False

if __name__ == "__main__":
    reparse_penal_code()
