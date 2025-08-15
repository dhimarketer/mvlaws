from flask import Flask, render_template, request, g
import sqlite3
import re

app = Flask(__name__)
DATABASE = "laws.db"  # Make sure this matches your database filename


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def natural_sort_key(text):
    """
    Convert any input (str or int) into sortable chunks for natural sorting.
    Ensures '43-1' < '43-2' and '2' < '10'.
    """
    text = str(text)  # Ensure string
    def try_int(s):
        try:
            return int(s)
        except ValueError:
            return s
    return [try_int(c) for c in re.split(r'(\d+)', text)]


def highlight_text(text, keywords):
    """
    Highlight all occurrences of keywords in text using <mark> tag.
    Case-insensitive and safe.
    """
    if not keywords or not text:
        return text
    highlighted = text
    for kw in keywords:
        kw = kw.strip()
        if not kw:
            continue
        highlighted = re.sub(
            f"({re.escape(kw)})",
            r"<mark>\1</mark>",
            highlighted,
            flags=re.IGNORECASE
        )
    return highlighted


@app.route("/", methods=["GET", "POST"])
def index():
    query = request.form.get("query", "").strip()
    match_type = request.form.get("match_type", "any")  # 'any' or 'all'
    results = []

    if query:
        db = get_db()
        
        # Parse query for exact matches (quoted strings) and regular keywords
        exact_phrases, keywords = parse_search_query(query)
        
        if not exact_phrases and not keywords:
            return render_template("index.html", results=[], query=query, match_type=match_type)

        # Build WHERE clause based on match type and query components
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

        cursor = db.execute(sql, params)
        fetched_results = cursor.fetchall()

        processed_results = []
        for row in fetched_results:
            text = row["text_content"]
            title = row["article_title"] or ""

            # Relevance score - count how many keywords and exact phrases are found
            score = 0
            # Count exact phrase matches (weighted higher)
            for phrase in exact_phrases:
                if phrase.lower() in text.lower() or phrase.lower() in title.lower():
                    score += 2  # Exact phrases get higher weight
            
            # Count keyword matches
            for kw in keywords:
                if kw.lower() in text.lower() or kw.lower() in title.lower():
                    score += 1

            # Highlight keywords and exact phrases
            highlighted_text = highlight_text(text, keywords + exact_phrases)

            processed_results.append({
                "law_id": row["law_id"],
                "law_name": row["law_name"],
                "article_id": row["article_id"],
                "article_number": row["article_number"],
                "article_title": row["article_title"],
                "sub_article_label": row["sub_article_label"],
                "text_content": highlighted_text,
                "relevance": score
            })

        # Sort by relevance, law name, and natural sort of article number
        processed_results.sort(
            key=lambda x: (-x["relevance"], x["law_name"], natural_sort_key(x["article_number"]))
        )
        results = processed_results
        
        # Generate search suggestions based on results
        suggestions = generate_search_suggestions(results, query, exact_phrases, keywords)
        print(f"[2024-12-17 15:30] | app.py:line 175 | Generated {len(suggestions)} search suggestions for query: {query} | ok")
    else:
        # Even with no results, try to generate some basic suggestions
        # This could include common legal terms, law names, etc.
        suggestions = []
        if query:
            # Try to find any content that might be related
            db = get_db()
            try:
                # Look for any content that contains parts of the query
                query_parts = query.split()
                if len(query_parts) > 1:
                    # Try with just the first word
                    simple_query = query_parts[0]
                    cursor = db.execute("""
                        SELECT DISTINCT laws.law_name, articles.article_title
                        FROM sub_articles
                        JOIN articles ON sub_articles.article_id = articles.id
                        JOIN laws ON articles.law_id = laws.id
                        WHERE sub_articles.text_content LIKE ? OR articles.article_title LIKE ?
                        LIMIT 5
                    """, [f"%{simple_query}%", f"%{simple_query}%"])
                    
                    basic_results = cursor.fetchall()
                    if basic_results:
                        suggestions.append({
                            'type': 'term',
                            'text': f'Try searching for "{simple_query}"',
                            'query': simple_query,
                            'description': 'Simplified search with fewer terms'
                        })
                        
                        # Add some law name suggestions
                        for row in basic_results[:3]:
                            if row['law_name']:
                                suggestions.append({
                                    'type': 'law',
                                    'text': f'Search in "{row["law_name"]}"',
                                    'query': f'"{row["law_name"]}"',
                                    'description': 'Search within this specific law'
                                })
            except Exception:
                pass  # If anything fails, just return empty suggestions
        
        print(f"[2024-12-17 15:30] | app.py:line 200 | Generated {len(suggestions)} alternative suggestions for no-results query: {query} | ok")

    return render_template("index.html", results=results, query=query, match_type=match_type, suggestions=suggestions)


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


def generate_search_suggestions(results, original_query, exact_phrases, keywords):
    """
    Generate search term suggestions based on current search results.
    Returns a list of suggested search terms that are brief and prominently found.
    """
    if not results:
        return []
    
    # Extract common terms from results with better analysis
    common_terms = {}
    law_names = set()
    article_titles = set()
    prominent_terms = {}  # Terms that appear prominently (high frequency + relevance)
    
    for result in results:
        # Collect law names
        law_names.add(result['law_name'])
        
        # Collect article titles
        if result['article_title']:
            article_titles.add(result['article_title'])
        
        # Extract potential terms from text content with better filtering
        text = result['text_content'].lower()
        # Remove HTML tags if any
        import re
        text = re.sub(r'<[^>]+>', '', text)
        
        # Find potential legal terms (words that appear multiple times)
        # Focus on legal/technical terms that are more meaningful
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text)  # Increased minimum length to 4
        
        # Define priority legal/technical terms that should get higher weight
        legal_priority_terms = {'act', 'law', 'regulation', 'article', 'section', 'clause', 'provision', 'penalty', 'fine', 'imprisonment', 'offence', 'crime', 'criminal', 'civil', 'administrative', 'judicial', 'court', 'tribunal', 'appeal', 'review', 'enforcement', 'compliance', 'licence', 'permit', 'authority', 'minister', 'government', 'ministry', 'department', 'agency', 'board', 'commission', 'committee', 'corporation', 'company', 'business', 'trade', 'commerce', 'employment', 'labor', 'tax', 'revenue', 'customs', 'immigration', 'citizenship', 'property', 'land', 'building', 'construction', 'environment', 'health', 'education', 'transport', 'communication', 'finance', 'banking', 'insurance', 'contract', 'agreement', 'liability', 'damages', 'compensation', 'rights', 'duties', 'obligations', 'prohibited', 'required', 'authorized', 'permitted', 'restricted', 'exempted', 'amended', 'repealed', 'enacted', 'established', 'constituted', 'appointed', 'elected', 'removed', 'suspended', 'terminated'}
        
        for word in words:
            # Filter out common grammatical words and focus on meaningful legal/technical terms
            if word not in ['the', 'and', 'for', 'with', 'this', 'that', 'shall', 'will', 'may', 'must', 'have', 'been', 'from', 'they', 'were', 'said', 'each', 'such', 'time', 'there', 'their', 'would', 'could', 'should', 'other', 'about', 'many', 'then', 'them', 'these', 'people', 'some', 'very', 'when', 'into', 'just', 'only', 'know', 'take', 'like', 'than', 'more', 'over', 'even', 'most', 'after', 'before', 'under', 'during', 'between', 'within', 'without', 'against', 'among', 'through', 'throughout', 'despite', 'except', 'beyond', 'above', 'below', 'behind', 'beside', 'beneath', 'alongside', 'here', 'where', 'what', 'which', 'who', 'whom', 'whose', 'why', 'how', 'all', 'any', 'both', 'either', 'neither', 'none', 'one', 'several', 'some', 'such', 'that', 'these', 'this', 'those', 'us', 'we', 'you', 'your', 'yours', 'yourself', 'yourselves', 'him', 'himself', 'her', 'herself', 'it', 'its', 'itself', 'me', 'myself', 'our', 'ours', 'ourselves', 'she', 'them', 'themselves', 'they', 'us', 'we', 'what', 'whatever', 'which', 'whichever', 'who', 'whoever', 'whom', 'whomever', 'whose']:
                # Give higher weight to legal priority terms
                weight = 2 if word.lower() in legal_priority_terms else 1
                common_terms[word] = common_terms.get(word, 0) + weight
                
                # Track prominent terms (appear in multiple results with high frequency)
                if word not in prominent_terms:
                    prominent_terms[word] = {'count': 0, 'results': set()}
                prominent_terms[word]['count'] += weight
                prominent_terms[word]['results'].add(result['law_name'])
    
    suggestions = []
    
    # 1. Suggest prominent terms that appear across multiple laws (most valuable)
    prominent_sorted = sorted(prominent_terms.items(), key=lambda x: (len(x[1]['results']), x[1]['count']), reverse=True)
    for term, data in prominent_sorted[:4]:  # Top 4 most prominent terms
        if term.lower() not in [kw.lower() for kw in keywords] and term.lower() not in [p.lower() for p in exact_phrases]:
            if len(data['results']) >= 2:  # Appears in at least 2 different laws
                # Create additive suggestion (add to current query)
                if keywords:
                    additive_query = f'{original_query} {term}'
                    suggestions.append({
                        'type': 'term',
                        'text': f'+ {term}',  # Brief - shows it's additive
                        'query': additive_query,
                        'description': f'Add "{term}" to current search (found in {len(data["results"])} laws)'
                    })
                else:
                    # If no current keywords, just suggest the term
                    suggestions.append({
                        'type': 'term',
                        'text': term,
                        'query': term,
                        'description': f'Found in {len(data["results"])} laws, {data["count"]} times total'
                    })
    
    # 2. Suggest brief law names (shortened for brevity)
    for law_name in list(law_names)[:3]:
        if law_name.lower() not in original_query.lower():
            # Make law names more brief
            brief_name = law_name
            if len(law_name) > 30:
                # Truncate long law names
                brief_name = law_name[:30] + "..."
            elif "Act" in law_name and len(law_name) > 20:
                # Try to extract just the main part
                parts = law_name.split()
                if len(parts) > 3:
                    brief_name = " ".join(parts[:3]) + "..."
            
            # Create additive suggestion for law names
            if keywords:
                additive_query = f'{original_query} "{law_name}"'
                suggestions.append({
                    'type': 'law',
                    'text': f'+ {brief_name}',  # Show it's additive
                    'query': additive_query,
                    'description': f'Add "{law_name}" to current search'
                })
            else:
                suggestions.append({
                    'type': 'law',
                    'text': brief_name,
                    'query': f'"{law_name}"',
                    'description': 'Search within this law'
                })
    
    # 3. Suggest brief article titles
    for title in list(article_titles)[:2]:  # Reduced to 2
        if title and title.lower() not in original_query.lower():
            # Make article titles more brief
            brief_title = title
            if len(title) > 25:
                brief_title = title[:25] + "..."
            
            # Create additive suggestion for article titles
            if keywords:
                additive_query = f'{original_query} "{title}"'
                suggestions.append({
                    'type': 'article',
                    'text': f'+ {brief_title}',  # Show it's additive
                    'query': additive_query,
                    'description': f'Add "{title}" to current search'
                })
            else:
                suggestions.append({
                    'type': 'article',
                    'text': brief_title,
                    'query': f'"{title}"',
                    'description': 'Search for this article'
                })
    
    # 4. Suggest high-frequency single terms (very brief)
    sorted_terms = sorted(common_terms.items(), key=lambda x: x[1], reverse=True)
    for term, count in sorted_terms[:3]:  # Top 3 most frequent
        if term.lower() not in [kw.lower() for kw in keywords] and term.lower() not in [p.lower() for p in exact_phrases]:
            if count >= 3 and term not in [s['query'] for s in suggestions]:  # Higher threshold
                # Create additive suggestion for high-frequency terms
                if keywords:
                    additive_query = f'{original_query} {term}'
                    suggestions.append({
                        'type': 'term',
                        'text': f'+ {term}',  # Show it's additive
                        'query': additive_query,
                        'description': f'Add "{term}" to current search (appears {count} times)'
                    })
                else:
                    suggestions.append({
                        'type': 'term',
                        'text': term,
                        'query': term,
                        'description': f'High frequency: {count} times'
                    })
    
    # 5. Suggest meaningful combinations (only if we have space)
    if len(suggestions) < 6 and keywords:
        for keyword in keywords[:1]:  # Use only first keyword
            for term, count in sorted_terms[:2]:  # Top 2 terms
                if term.lower() != keyword.lower() and count >= 3:
                    # Create additive combination suggestion
                    additive_query = f'{original_query} {term}'
                    if additive_query not in [s['query'] for s in suggestions]:
                        suggestions.append({
                            'type': 'combination',
                            'text': f'+ {term}',  # Show it's additive
                            'query': additive_query,
                            'description': f'Add "{term}" to current search'
                        })
    
    # Remove duplicates and limit total suggestions to 6 (more focused)
    unique_suggestions = []
    seen_queries = set()
    for suggestion in suggestions:
        if suggestion['query'] not in seen_queries and len(unique_suggestions) < 6:
            unique_suggestions.append(suggestion)
            seen_queries.add(suggestion['query'])
    
    return unique_suggestions


@app.route("/law/<int:law_id>")
def view_law(law_id):
    db = get_db()
    
    # Get search query and highlight flag
    search_query = request.args.get("q", "").strip()
    highlight_flag = request.args.get("highlight")
    
    # Parse query for exact matches (quoted strings) and regular keywords
    exact_phrases, keywords = parse_search_query(search_query)
    all_search_terms = exact_phrases + keywords
    
    # Build SQL based on whether we're filtering by search terms
    if search_query and all_search_terms and highlight_flag:
        # Filter by search terms within this specific law (filtered view)
        sql = """
            SELECT laws.law_name, articles.article_number, articles.article_title,
                   sub_articles.sub_article_label, sub_articles.text_content
            FROM laws
            JOIN articles ON laws.id = articles.law_id
            JOIN sub_articles ON articles.id = sub_articles.article_id
            WHERE laws.id = ? AND (
        """
        params = [law_id]
        
        # Add search conditions for each search term
        search_conditions = []
        for term in all_search_terms:
            search_conditions.append("(sub_articles.text_content LIKE ? OR articles.article_title LIKE ?)")
            search_term = f"%{term}%"
            params.extend([search_term, search_term])
        
        sql += " OR ".join(search_conditions) + ")"
        sql += " ORDER BY articles.article_number, sub_articles.sub_article_label"
    else:
        # Show all sub-articles from this law (full law view)
        # Use a more intelligent ordering to group related sub-articles
        sql = """
            SELECT laws.law_name, articles.article_number, articles.article_title,
                   sub_articles.sub_article_label, sub_articles.text_content,
                   sub_articles.id
            FROM laws
            JOIN articles ON laws.id = articles.law_id
            JOIN sub_articles ON articles.id = sub_articles.article_id
            WHERE laws.id = ?
            ORDER BY 
                articles.article_number,
                CASE 
                    WHEN sub_articles.sub_article_label GLOB '[a-zA-Z]' THEN 0
                    ELSE 1
                END,
                sub_articles.sub_article_label,
                sub_articles.id
        """
        params = [law_id]
    
    cursor = db.execute(sql, params)
    sections = cursor.fetchall()

    # Process sections with optional highlighting and deduplication
    processed_sections = []
    current_article = None
    seen_labels = set()

    for sec in sections:
        # Track article headers
        if current_article != sec["article_number"]:
            current_article = sec["article_number"]
            processed_sections.append({
                "type": "header",
                "article_number": sec["article_number"],
                "article_title": sec["article_title"]
            })

        # Highlight text if requested
        display_text = sec["text_content"]
        if highlight_flag and all_search_terms:
            display_text = highlight_text(display_text, all_search_terms)

        # Create a unique key for deduplication within this article
        label_key = f"{sec['article_number']}_{sec['sub_article_label']}_{sec['text_content'][:50]}"
        
        # Only add if we haven't seen this combination before
        if label_key not in seen_labels:
            seen_labels.add(label_key)
            processed_sections.append({
                "type": "sub_article",
                "law_name": sec["law_name"],
                "article_number": sec["article_number"],
                "article_title": sec["article_title"],
                "sub_article_label": sec["sub_article_label"],
                "text_content": display_text
            })

    return render_template(
        "law.html",
        sections=processed_sections,
        query=search_query,
        highlight_flag=highlight_flag
    )


@app.route("/article/<int:article_id>")
def view_article(article_id):
    db = get_db()
    
    # Get search query and highlight flag
    search_query = request.args.get("q", "").strip()
    highlight_flag = request.args.get("highlight")
    
    # Parse query for exact matches (quoted strings) and regular keywords
    exact_phrases, keywords = parse_search_query(search_query)
    all_search_terms = exact_phrases + keywords
    
    # Build SQL based on whether we're filtering by search terms
    if search_query and all_search_terms and highlight_flag:
        # Filter by search terms within this specific article (filtered view)
        sql = """
            SELECT laws.id as law_id, laws.law_name, articles.article_number, articles.article_title,
                   sub_articles.sub_article_label, sub_articles.text_content
            FROM articles
            JOIN laws ON articles.law_id = laws.id
            JOIN sub_articles ON articles.id = sub_articles.article_id
            WHERE articles.id = ? AND (
        """
        params = [article_id]
        
        # Add search conditions for each search term
        search_conditions = []
        for term in all_search_terms:
            search_conditions.append("(sub_articles.text_content LIKE ? OR articles.article_title LIKE ?)")
            search_term = f"%{term}%"
            params.extend([search_term, search_term])
        
        sql += " OR ".join(search_conditions) + ")"
        sql += " ORDER BY sub_articles.sub_article_label"
    else:
        # Show all sub-articles from this article (full article view)
        # Use a more intelligent ordering to group related sub-articles
        sql = """
            SELECT laws.id as law_id, laws.law_name, articles.article_number, articles.article_title,
                   sub_articles.sub_article_label, sub_articles.text_content,
                   sub_articles.id
            FROM articles
            JOIN laws ON articles.law_id = laws.id
            JOIN sub_articles ON articles.id = sub_articles.article_id
            WHERE articles.id = ?
            ORDER BY 
                CASE 
                    WHEN sub_articles.sub_article_label GLOB '[a-zA-Z]' THEN 0
                    ELSE 1
                END,
                sub_articles.sub_article_label,
                sub_articles.id
        """
        params = [article_id]
    
    cursor = db.execute(sql, params)
    sections = cursor.fetchall()

    # Process with optional highlighting and deduplication
    processed_sections = []
    seen_labels = set()
    
    for sec in sections:
        display_text = sec["text_content"]
        if highlight_flag and all_search_terms:
            display_text = highlight_text(display_text, all_search_terms)
        
        # Create a unique key for deduplication
        label_key = f"{sec['sub_article_label']}_{sec['text_content'][:50]}"
        
        # Only add if we haven't seen this combination before
        if label_key not in seen_labels:
            seen_labels.add(label_key)
            processed_sections.append({
                "law_id": sec["law_id"],
                "law_name": sec["law_name"],
                "article_number": sec["article_number"],
                "article_title": sec["article_title"],
                "sub_article_label": sec["sub_article_label"],
                "text_content": display_text
            })

    return render_template(
        "article.html",
        sections=processed_sections,
        query=search_query,
        highlight_flag=highlight_flag
    )


if __name__ == "__main__":
    app.run(debug=True, port=5002)
