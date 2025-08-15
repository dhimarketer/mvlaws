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

    return render_template("index.html", results=results, query=query, match_type=match_type)


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
            SELECT laws.law_name, articles.article_number, articles.article_title,
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
            SELECT laws.law_name, articles.article_number, articles.article_title,
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
    app.run(debug=True)
