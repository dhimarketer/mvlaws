#!/usr/bin/env python3

import sqlite3

def test_search_directly():
    """Test the search directly in the database"""
    
    # Connect to database
    conn = sqlite3.connect('laws.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Test query: "murder, sentence"
    query = "murder, sentence"
    
    # Parse the query (simplified version)
    keywords = [kw.strip() for kw in query.replace(',', ' ').split() if kw.strip()]
    print(f"Query: '{query}'")
    print(f"Keywords: {keywords}")
    
    # Build the search SQL (same as in app.py)
    where_clauses = []
    params = []
    
    for kw in keywords:
        where_clauses.append("(sub_articles.text_content LIKE ? OR articles.article_title LIKE ?)")
        search_term = f"%{kw}%"
        params.extend([search_term, search_term])

    where_sql = f"({' OR '.join(where_clauses)})"
    
    sql = f"""
        SELECT 
            laws.id AS law_id,
            laws.law_name,
            articles.id AS article_id,
            articles.article_number,
            articles.article_title,
            sub_articles.sub_article_label,
            sub_articles.text_content
        FROM sub_articles
        JOIN articles ON sub_articles.article_id = articles.id
        JOIN laws ON articles.law_id = laws.id
        WHERE {where_sql}
        ORDER BY laws.law_name, articles.article_number, sub_articles.sub_article_label
        LIMIT 20
    """
    
    print(f"\nSQL: {sql}")
    print(f"Parameters: {params}")
    
    # Execute the search
    try:
        cursor.execute(sql, params)
        results = cursor.fetchall()
        
        print(f"\nFound {len(results)} results:")
        print("=" * 80)
        
        for i, row in enumerate(results):
            print(f"\nResult {i+1}:")
            print(f"  Law: {row['law_name']}")
            print(f"  Article: {row['article_number']} - {row['article_title']}")
            print(f"  Sub-article: {row['sub_article_label']}")
            print(f"  Content: {row['text_content'][:200]}...")
            
            # Check which keywords are found
            found_keywords = []
            for kw in keywords:
                if kw.lower() in row['text_content'].lower() or kw.lower() in (row['article_title'] or '').lower():
                    found_keywords.append(kw)
            
            print(f"  Keywords found: {found_keywords}")
            
    except Exception as e:
        print(f"Error executing search: {e}")
    
    conn.close()

if __name__ == "__main__":
    test_search_directly()
