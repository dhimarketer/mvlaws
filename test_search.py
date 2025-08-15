#!/usr/bin/env python3

def parse_search_query(query):
    """
    Parse search query to extract exact phrases (quoted strings) and regular keywords.
    Returns tuple of (exact_phrases, keywords)
    """
    exact_phrases = []
    keywords = []
    
    # Find all quoted strings first
    import re
    quote_pattern = r'"([^"]*)"'
    quoted_matches = re.findall(quote_pattern, query)
    
    # Remove quoted strings from query to get remaining keywords
    remaining_query = re.sub(quote_pattern, '', query)
    
    # Extract exact phrases (remove quotes and add to list)
    for match in quoted_matches:
        if match.strip():  # Only add non-empty phrases
            exact_phrases.append(match.strip())
    
    # Parse remaining query for keywords
    if remaining_query.strip():
        normalized_query = re.sub(r"[,+\s]+", " ", remaining_query).strip()
        keywords = [kw.strip() for kw in normalized_query.split() if kw.strip()]
    
    return exact_phrases, keywords

def build_search_sql(exact_phrases, keywords, match_type="any"):
    """Build the SQL query for search"""
    
    if match_type == "all":
        # For "Match all terms": each sub-article must contain ALL keywords AND exact phrases
        sql = """
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
            WHERE 1=1
        """
        params = []
        
        # Add exact phrase conditions
        for phrase in exact_phrases:
            sql += " AND (sub_articles.text_content LIKE ? OR articles.article_title LIKE ?)"
            search_term = f"%{phrase}%"
            params.extend([search_term, search_term])
        
        # Add keyword conditions
        for kw in keywords:
            sql += " AND (sub_articles.text_content LIKE ? OR articles.article_title LIKE ?)"
            search_term = f"%{kw}%"
            params.extend([search_term, search_term])
    else:
        # For "Match any term": sub-articles containing ANY keyword OR exact phrase
        where_clauses = []
        params = []
        
        # Add exact phrase conditions
        for phrase in exact_phrases:
            where_clauses.append("(sub_articles.text_content LIKE ? OR articles.article_title LIKE ?)")
            search_term = f"%{phrase}%"
            params.extend([search_term, search_term])
        
        # Add keyword conditions
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
        """

    sql += " ORDER BY laws.law_name, articles.article_number, sub_articles.sub_article_label"
    return sql, params

# Test the search
query = "murder, sentence"
print(f"Query: '{query}'")

exact_phrases, keywords = parse_search_query(query)
print(f"Exact phrases: {exact_phrases}")
print(f"Keywords: {keywords}")

# Test with "any" match type
sql, params = build_search_sql(exact_phrases, keywords, "any")
print(f"\nSQL (any): {sql}")
print(f"Parameters: {params}")

# Test with "all" match type
sql, params = build_search_sql(exact_phrases, keywords, "all")
print(f"\nSQL (all): {sql}")
print(f"Parameters: {params}")
