#!/usr/bin/env python3
"""
Law Parsing Script for Law Analysis Tool
Parses law text files to extract structured data
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class LawParser:
    def __init__(self, laws_dir: str = "laws"):
        self.laws_dir = Path(laws_dir)
        self.parsed_laws = []
        
    def parse_law_file(self, file_path: Path) -> Dict:
        """Parse a single law file and extract structured data"""
        
        print(f"📖 Parsing: {file_path.name}")
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Extract basic law information
        law_info = self._extract_law_info(content, file_path.name)
        
        # Parse structure (parts, chapters, articles)
        structure = self._parse_structure(content)
        
        # Parse articles and sub-articles
        articles = self._parse_articles(content, structure)
        
        return {
            'file_name': file_path.name,
            'law_info': law_info,
            'structure': structure,
            'articles': articles
        }
    
    def _extract_law_info(self, content: str, filename: str) -> Dict:
        """Extract basic law information from header"""
        
        lines = content.split('\n')
        
        # Extract law name using multiple strategies
        law_name = None
        
        # Strategy 1: Look for markdown headers (### Title) and bold text (**Title**)
        for line in lines:
            line = line.strip()
            if line.startswith('###'):
                # Extract text from markdown header
                cleaned_line = line.replace('###', '').replace('*', '').replace('**', '').strip()
                if cleaned_line:
                    # Skip lines that are clearly not titles (parts, chapters, etc.)
                    if not any(prefix in cleaned_line.lower() for prefix in ['part ', 'chapter ', 'introduction', 'preliminary']):
                        law_name = cleaned_line
                        break
            elif line.startswith('**') and line.endswith('**'):
                # Extract text from bold markdown (**Title**)
                cleaned_line = line.replace('*', '').strip()
                if cleaned_line:
                    # Skip lines that are clearly not titles (parts, chapters, etc.)
                    if not any(prefix in cleaned_line.lower() for prefix in ['part ', 'chapter ', 'introduction', 'preliminary']):
                        law_name = cleaned_line
                        break
        
        # Strategy 2: Look for lines that contain law-related keywords
        if not law_name:
            for line in lines:
                line = line.strip()
                if line and not line.startswith('---') and not line.startswith('#'):
                    # Skip lines that are clearly not titles
                    if any(prefix in line.lower() for prefix in ['part ', 'chapter ', 'introduction', 'preliminary']):
                        continue
                    # Check if this looks like a law title
                    if any(word in line.lower() for word in ['act', 'law', 'code', 'regulation', 'decree']):
                        cleaned_line = line.replace('*', '').replace('**', '').strip()
                        if cleaned_line:
                            law_name = cleaned_line
                            break
                    # If no law-specific words, still use it if it's reasonable
                    elif len(line) < 100 and not any(prefix in line.lower() for prefix in ['part ', 'chapter ', 'introduction', 'preliminary']):
                        cleaned_line = line.replace('*', '').replace('**', '').strip()
                        if cleaned_line:
                            law_name = cleaned_line
                            break
        
        # Strategy 3: Look for the first meaningful line that's not a number or date
        if not law_name:
            for line in lines:
                line = line.strip()
                if line and not line.startswith('---') and not line.startswith('#'):
                    # Skip lines that are just numbers, dates, or structure
                    if re.match(r'^\d+\.?$', line):  # Just a number like "1." or "1"
                        continue
                    if re.match(r'^\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)', line):
                        continue
                    if any(prefix in line.lower() for prefix in ['part ', 'chapter ', 'introduction', 'preliminary']):
                        continue
                    
                    cleaned_line = line.replace('*', '').replace('**', '').strip()
                    if cleaned_line and len(cleaned_line) > 2:
                        law_name = cleaned_line
                        break
        
        # Strategy 4: Extract from filename as fallback
        if not law_name:
            # Clean up filename to get a reasonable law name
            base_name = filename.replace('.txt', '').replace('.md', '')
            # Remove common prefixes/suffixes
            base_name = re.sub(r'^(Law|Act|Code)\s+', '', base_name, flags=re.IGNORECASE)
            base_name = re.sub(r'\s+(Law|Act|Code)$', '', base_name, flags=re.IGNORECASE)
            # Clean up common suffixes
            base_name = re.sub(r'(English|Eng)$', '', base_name, flags=re.IGNORECASE)
            base_name = base_name.strip()
            law_name = base_name
        
        # Strategy 5: Look for specific law title patterns in the first few lines
        if not law_name or law_name == '':
            for line in lines[:10]:  # Check first 10 lines for specific patterns
                line = line.strip()
                # Look for patterns like "MALDIVES PENAL CODE" or "COMPANIES ACT"
                if line and ('PENAL CODE' in line.upper() or 'COMPANIES ACT' in line.upper() or 'ACT' in line.upper()):
                    cleaned_line = line.replace('*', '').replace('**', '').strip()
                    if cleaned_line:
                        law_name = cleaned_line
                        break
        
        # Strategy 6: If still no law name, use a generic approach
        if not law_name or law_name == '':
            # Look for any line that might be a title
            for line in lines[:20]:  # Only check first 20 lines
                line = line.strip()
                if line and len(line) > 3 and len(line) < 200:
                    # Skip obvious non-titles
                    if not re.match(r'^\d+\.?$', line) and not line.startswith('---'):
                        cleaned_line = line.replace('*', '').replace('**', '').strip()
                        if cleaned_line:
                            law_name = cleaned_line
                            break
        
        # Final fallback: use filename
        if not law_name or law_name == '':
            law_name = filename.replace('.txt', '').replace('.md', '')
        
        # Look for date patterns
        date_pattern = r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}'
        dates = re.findall(date_pattern, content, re.IGNORECASE)
        enactment_date = dates[0] if dates else None
        
        # Look for act number
        act_pattern = r'Act\s+(?:Number|No\.?)\s*(\d+/\d+)'
        act_match = re.search(act_pattern, content, re.IGNORECASE)
        act_number = act_match.group(1) if act_match else None
        
        # Determine category based on filename/content
        category = self._determine_category(filename, content)
        
        return {
            'law_name': law_name,
            'enactment_date': enactment_date,
            'act_number': act_number,
            'category_name': category
        }
    
    def _determine_category(self, filename: str, content: str) -> str:
        """Determine law category based on filename and content"""
        
        filename_lower = filename.lower()
        content_lower = content.lower()
        
        # Criminal law
        if 'penal' in filename_lower or 'criminal' in filename_lower:
            return 'Criminal Law'
        
        # Civil law
        if 'civil' in filename_lower or 'procedure' in filename_lower:
            return 'Civil Law'
        
        # Financial law
        if any(word in filename_lower for word in ['tax', 'finance', 'banking', 'customs']):
            return 'Financial Law'
        
        # Environmental law
        if any(word in filename_lower for word in ['environment', 'climate', 'fisheries', 'energy']):
            return 'Environmental Law'
        
        # Administrative law
        if any(word in filename_lower for word in ['public', 'government', 'election', 'commission']):
            return 'Administrative Law'
        
        # Commercial law
        if any(word in filename_lower for word in ['business', 'commercial', 'contract', 'property']):
            return 'Commercial Law'
        
        return 'General Law'
    
    def _parse_structure(self, content: str) -> Dict:
        """Parse the hierarchical structure (parts, chapters)"""
        
        structure = {
            'parts': [],
            'chapters': []
        }
        
        lines = content.split('\n')
        
        current_part = None
        current_chapter = None
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            
            # Look for PART markers
            part_match = re.match(r'^PART\s+(\d+|[IVX]+)\s*[:\-]?\s*(.+)?$', line, re.IGNORECASE)
            if part_match:
                part_num = part_match.group(1)
                part_title = part_match.group(2).strip() if part_match.group(2) else f"Part {part_num}"
                
                current_part = {
                    'part_number': part_num,
                    'part_title': part_title,
                    'line_number': line_num
                }
                structure['parts'].append(current_part)
                current_chapter = None
                continue
            
            # Look for CHAPTER markers
            chapter_match = re.match(r'^CHAPTER\s+(\d+|[IVX]+)\s*[:\-]?\s*(.+)?$', line, re.IGNORECASE)
            if chapter_match:
                chapter_num = chapter_match.group(1)
                chapter_title = chapter_match.group(2).strip() if chapter_match.group(2) else f"Chapter {chapter_num}"
                
                current_chapter = {
                    'chapter_number': chapter_num,
                    'chapter_title': chapter_title,
                    'line_number': line_num,
                    'part_number': current_part['part_number'] if current_part else None
                }
                structure['chapters'].append(current_chapter)
                continue
        
        return structure
    
    def _parse_articles(self, content: str, structure: Dict) -> List[Dict]:
        """Parse articles and sub-articles from content with improved formatting handling"""
        
        articles = []
        lines = content.split('\n')
        
        current_article = None
        current_sub_article = None
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            
            # Look for Article markers (various formats)
            article_patterns = [
                r'^Article\s+(\d+[-\d]*)\s*[:\-]?\s*(.+)?$',
                r'^(\d+[-\d]*)\s*[:\-]?\s*(.+)?$',  # 1., 2., 3. (with optional title)
                r'^(\d+[-\d]*)\s*[:\-]?\s*(.+)?$',
                r'^(\d+)\s*$',  # Just a number on its own line (common in Maldivian laws)
                r'^\*\*(\d+[-\d]*)\s*[:\-]?\s*(.+)?\*\*$'  # **110. Murder** format
            ]
            
            article_match = None
            for pattern in article_patterns:
                article_match = re.match(pattern, line, re.IGNORECASE)
                if article_match:
                    break
            
            # Special handling for penal code format - look for numbered sections
            if not article_match and line:
                # Check if this is a numbered section (common in penal codes)
                penal_section_match = re.match(r'^(\d+)\.\s*(.+)?$', line)
                if penal_section_match:
                    article_match = penal_section_match
            
            if article_match:
                article_num = article_match.group(1)
                
                # Get article title - handle different cases
                article_title = None
                if len(article_match.groups()) > 1 and article_match.group(2):
                    article_title = article_match.group(2).strip()
                
                # Handle bold markdown format - clean up the title
                if article_title and article_title.startswith('**') and article_title.endswith('**'):
                    article_title = article_title.replace('**', '').strip()
                
                # If no title in the same line, look for title in next line
                if not article_title:
                    # Look ahead to next non-empty line for potential title
                    for next_line_num in range(line_num + 1, min(line_num + 5, len(lines))):
                        next_line = lines[next_line_num].strip()
                        if next_line and not self._is_sub_article_marker(next_line):
                            # Check if this looks like a title (not too long, not just punctuation)
                            if len(next_line) < 200 and not re.match(r'^[^\w]*$', next_line):
                                article_title = next_line
                                break
                            else:
                                # If it's too long or just punctuation, it's probably content, not title
                                break
                
                # If still no title, generate a meaningful one
                if not article_title:
                    article_title = f"Section {article_num}"
                
                # Determine which chapter this article belongs to
                chapter_id = self._find_chapter_for_line(line_num, structure)
                
                current_article = {
                    'article_number': article_num,
                    'article_title': article_title,
                    'line_number': line_num,
                    'chapter_id': chapter_id,
                    'sub_articles': []
                }
                articles.append(current_article)
                current_sub_article = None
                continue
            
            # Look for sub-article markers (Maldivian law format)
            if current_article and line:
                if self._is_sub_article_marker(line):
                    sub_label = self._extract_sub_article_label(line)
                    
                    # Get sub-article content
                    sub_content = self._extract_sub_article_content(line, sub_label)
                    
                    # If no content in this line, look ahead for content
                    if not sub_content:
                        sub_content = self._look_ahead_for_sub_article_content(lines, line_num + 1)
                    
                    # Only create sub-article if it has meaningful content
                    if sub_content and len(sub_content.strip()) > 0:
                        current_sub_article = {
                            'sub_article_label': sub_label,
                            'text_content': sub_content.strip(),
                            'line_number': line_num
                        }
                        current_article['sub_articles'].append(current_sub_article)
                    else:
                        # If no content, skip this sub-article marker
                        current_sub_article = None
                elif current_sub_article and line:
                    # Continue previous sub-article content
                    if line.strip():  # Only add non-empty lines
                        current_sub_article['text_content'] += ' ' + line
                elif line and not line.startswith('CHAPTER') and not line.startswith('PART'):
                    # For penal code format, treat lines without markers as content of the current article
                    # This helps capture the full text of each section
                    if current_article and not current_article['sub_articles']:
                        # If no sub-articles yet, create a default one with the article content
                        current_sub_article = {
                            'sub_article_label': 'main',
                            'text_content': line,
                            'line_number': line_num
                        }
                        current_article['sub_articles'].append(current_sub_article)
                    elif current_sub_article:
                        # Add to existing sub-article
                        current_sub_article['text_content'] += ' ' + line
        
        return articles
    
    def _is_sub_article_marker(self, line: str) -> bool:
        """Check if a line contains a sub-article marker"""
        sub_article_patterns = [
            r'^\(([a-z0-9]+)\)',  # (a), (b), (c), (1), (2)
            r'^([a-z0-9]+\))',    # a), b), c), 1), 2)
            r'^([a-z0-9]+\.)',   # a., b., c., 1., 2.
            r'^([a-z0-9]+\.\s*$)',  # a., b., c., 1., 2. (just marker)
            r'^(\d+\.\s*[a-z])',  # 1. a, 2. b (penal code format)
            r'^([a-z]\.\s*\d+)',  # a. 1, b. 2 (penal code format)
        ]
        
        for pattern in sub_article_patterns:
            if re.match(pattern, line):
                return True
        return False
    
    def _extract_sub_article_label(self, line: str) -> str:
        """Extract the label from a sub-article marker line"""
        sub_article_patterns = [
            r'^\(([a-z0-9]+)\)',  # (a), (b), (c), (1), (2)
            r'^([a-z0-9]+\))',    # a), b), c), 1), 2)
            r'^([a-z0-9]+\.)',   # a., b., c., 1., 2.
        ]
        
        for pattern in sub_article_patterns:
            match = re.match(pattern, line)
            if match:
                return match.group(1)
        
        return "unknown"
    
    def _extract_sub_article_content(self, line: str, label: str) -> str:
        """Extract content from a line that contains a sub-article marker"""
        # Remove the marker and get content
        if line.startswith(f'({label})'):
            return line[len(f'({label})'):].strip()
        elif line.startswith(f'{label})'):
            return line[len(f'{label})'):].strip()
        elif line.startswith(f'{label}.'):
            return line[len(f'{label}.'):].strip()
        else:
            return line.strip()
    
    def _look_ahead_for_sub_article_content(self, lines: List[str], start_line: int) -> str:
        """Look ahead in lines to find content for a sub-article that has no content on its marker line"""
        content_lines = []
        
        for line_num in range(start_line, min(start_line + 10, len(lines))):
            line = lines[line_num].strip()
            
            # Stop if we hit another marker or article
            if not line:
                continue
            if self._is_sub_article_marker(line) or re.match(r'^\d+\.?\s*', line):
                break
            
            content_lines.append(line)
        
        return ' '.join(content_lines)
    
    def _find_chapter_for_line(self, line_num: int, structure: Dict) -> Optional[str]:
        """Find which chapter a line belongs to based on line number"""
        
        for chapter in structure['chapters']:
            if chapter['line_number'] <= line_num:
                # Find the next chapter to determine the boundary
                next_chapter_line = float('inf')
                for next_chapter in structure['chapters']:
                    if next_chapter['line_number'] > line_num:
                        next_chapter_line = next_chapter['line_number']
                        break
                
                if line_num < next_chapter_line:
                    return chapter['chapter_number']
        
        return None
    
    def parse_all_laws(self) -> List[Dict]:
        """Parse all law files in the laws directory"""
        
        if not self.laws_dir.exists():
            print(f"❌ Laws directory not found: {self.laws_dir}")
            return []
        
        # Get all .txt files (excluding TODO and dhivehi folders)
        law_files = []
        for file_path in self.laws_dir.rglob("*.txt"):
            if "TODO" not in str(file_path) and "dhivehi" not in str(file_path):
                law_files.append(file_path)
        
        print(f"📚 Found {len(law_files)} law files to parse")
        print("=" * 50)
        
        for file_path in law_files:
            try:
                parsed_law = self.parse_law_file(file_path)
                self.parsed_laws.append(parsed_law)
                print(f"✅ Parsed: {file_path.name}")
            except Exception as e:
                print(f"❌ Failed to parse {file_path.name}: {e}")
        
        print(f"\n🎯 Successfully parsed {len(self.parsed_laws)} laws")
        return self.parsed_laws
    
    def get_summary(self) -> Dict:
        """Get summary statistics of parsed laws"""
        
        total_articles = sum(len(law['articles']) for law in self.parsed_laws)
        total_sub_articles = sum(
            sum(len(article['sub_articles']) for article in law['articles'])
            for law in self.parsed_laws
        )
        
        # Count articles with meaningful titles vs generic titles
        meaningful_titles = 0
        generic_titles = 0
        
        for law in self.parsed_laws:
            for article in law['articles']:
                if article['article_title'].startswith('Article '):
                    generic_titles += 1
                else:
                    meaningful_titles += 1
        
        # Count sub-articles with content vs empty ones
        sub_articles_with_content = 0
        empty_sub_articles = 0
        
        for law in self.parsed_laws:
            for article in law['articles']:
                for sub_article in article['sub_articles']:
                    if sub_article['text_content'].strip():
                        sub_articles_with_content += 1
                    else:
                        empty_sub_articles += 1
        
        categories = {}
        for law in self.parsed_laws:
            category = law['law_info']['category_name']
            categories[category] = categories.get(category, 0) + 1
        
        return {
            'total_laws': len(self.parsed_laws),
            'total_articles': total_articles,
            'total_sub_articles': total_sub_articles,
            'meaningful_titles': meaningful_titles,
            'generic_titles': generic_titles,
            'sub_articles_with_content': sub_articles_with_content,
            'empty_sub_articles': empty_sub_articles,
            'categories': categories
        }

if __name__ == "__main__":
    print("🔍 Law Parsing Script - Enhanced Version")
    print("=" * 50)
    
    parser = LawParser()
    parsed_laws = parser.parse_all_laws()
    
    if parsed_laws:
        summary = parser.get_summary()
        print(f"\n📊 Parsing Summary:")
        print(f"   Total Laws: {summary['total_laws']}")
        print(f"   Total Articles: {summary['total_articles']}")
        print(f"   Total Sub-articles: {summary['total_sub_articles']}")
        print(f"\n📝 Article Title Quality:")
        print(f"   Meaningful Titles: {summary['meaningful_titles']}")
        print(f"   Generic Titles: {summary['generic_titles']}")
        print(f"\n📋 Sub-article Content Quality:")
        print(f"   With Content: {summary['sub_articles_with_content']}")
        print(f"   Empty: {summary['empty_sub_articles']}")
        print(f"\n📂 Categories:")
        for category, count in summary['categories'].items():
            print(f"   {category}: {count}")
        
        # Save parsed data for inspection
        import json
        with open('parsed_laws.json', 'w', encoding='utf-8') as f:
            json.dump(parsed_laws, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Parsed data saved to: parsed_laws.json")
    else:
        print("❌ No laws were parsed successfully")
