# Search Suggestions Feature

## Overview
The search suggestions feature automatically generates relevant search terms based on user queries and search results. This helps users discover related content and refine their searches more effectively.

## Features

### 1. Result-Based Suggestions
When search results are found, the system analyzes the content to suggest:
- **Law-specific searches**: "Search in [Law Name]"
- **Article title searches**: "Search for [Article Title]"
- **Frequent terms**: Common legal terms that appear multiple times in results
- **Combination searches**: Original terms combined with new relevant terms

### 2. No-Results Suggestions
When no results are found, the system provides:
- **Simplified searches**: Try searching with fewer terms
- **Related law suggestions**: Search within laws that might contain similar content
- **Alternative approaches**: Different search strategies

### 3. Smart Analysis
The suggestion engine:
- Extracts common terms from search results
- Identifies frequently occurring legal terminology
- Avoids suggesting terms already in the current query
- Limits suggestions to prevent overwhelming the user

## Implementation Details

### Backend (app.py)
- `generate_search_suggestions()` function analyzes results and generates suggestions
- Suggestions are categorized by type (law, article, term, combination)
- Each suggestion includes query text, description, and type

### Frontend (templates/index.html)
- Suggestions displayed as clickable buttons below search results
- Color-coded by suggestion type for better visual organization
- Hover effects and tooltips for better user experience
- Responsive design that works on different screen sizes

## Usage

1. **Perform a search** using the main search form
2. **View suggestions** that appear below the results
3. **Click any suggestion** to run a new search with those terms
4. **Refine your search** based on the suggestions

## Benefits

- **Discovery**: Users find content they might not have thought to search for
- **Efficiency**: Quick access to related searches without retyping
- **Learning**: Users learn about the scope and structure of the legal database
- **Engagement**: Interactive suggestions encourage exploration of the database

## Technical Notes

- Suggestions are generated in real-time based on current search results
- The system handles both successful searches and no-result scenarios
- Suggestions are limited to 8 items to avoid overwhelming the interface
- All suggestions maintain the current match type (any/all) setting
