#!/usr/bin/env python3
"""
Data Validation Script for Law Analysis Tool
Verifies the integrity and completeness of the populated database
"""

import sqlite3
import os
from datetime import datetime

DATABASE = "laws.db"

class DataValidator:
    def __init__(self, database_path: str = DATABASE):
        self.database_path = database_path
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Connect to the database"""
        self.conn = sqlite3.connect(self.database_path)
        self.cursor = self.conn.cursor()
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def validate_database_structure(self):
        """Validate that all required tables exist with correct schema"""
        
        print("🔍 Validating database structure...")
        
        required_tables = {
            'laws': ['id', 'law_name', 'file_name', 'category_name', 'created_at'],
            'parts': ['id', 'law_id', 'part_number', 'part_title'],
            'chapters': ['id', 'part_id', 'chapter_number', 'chapter_title'],
            'articles': ['id', 'law_id', 'article_number', 'article_title', 'created_at', 'chapter_id'],
            'sub_articles': ['id', 'article_id', 'sub_article_label', 'text_content', 'created_at'],
            'votes': ['id', 'article_id', 'user_id', 'vote', 'reasoning', 'voted_at']
        }
        
        # Check if tables exist
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in self.cursor.fetchall()]
        
        print("   📋 Checking table existence...")
        for table in required_tables:
            if table in existing_tables:
                print(f"      ✅ {table} table exists")
            else:
                print(f"      ❌ {table} table MISSING")
                return False
        
        # Check table schemas
        print("   🔧 Checking table schemas...")
        for table, expected_columns in required_tables.items():
            if table in existing_tables:
                self.cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in self.cursor.fetchall()]
                
                missing_columns = set(expected_columns) - set(columns)
                if missing_columns:
                    print(f"      ❌ {table}: Missing columns {missing_columns}")
                    return False
                else:
                    print(f"      ✅ {table}: Schema correct ({len(columns)} columns)")
        
        print("   ✅ Database structure validation passed")
        return True
    
    def validate_data_integrity(self):
        """Validate referential integrity and data consistency"""
        
        print("\n🔗 Validating data integrity...")
        
        # Check foreign key relationships
        print("   🔗 Checking foreign key relationships...")
        
        # Check parts -> laws
        self.cursor.execute("""
            SELECT COUNT(*) FROM parts p 
            LEFT JOIN laws l ON p.law_id = l.id 
            WHERE l.id IS NULL
        """)
        orphaned_parts = self.cursor.fetchone()[0]
        if orphaned_parts > 0:
            print(f"      ❌ Found {orphaned_parts} parts with invalid law_id")
            return False
        else:
            print("      ✅ Parts -> Laws: All references valid")
        
        # Check chapters -> parts
        self.cursor.execute("""
            SELECT COUNT(*) FROM chapters c 
            LEFT JOIN parts p ON c.part_id = p.id 
            WHERE p.id IS NULL
        """)
        orphaned_chapters = self.cursor.fetchone()[0]
        if orphaned_chapters > 0:
            print(f"      ❌ Found {orphaned_chapters} chapters with invalid part_id")
            return False
        else:
            print("      ✅ Chapters -> Parts: All references valid")
        
        # Check articles -> laws
        self.cursor.execute("""
            SELECT COUNT(*) FROM articles a 
            LEFT JOIN laws l ON a.law_id = l.id 
            WHERE l.id IS NULL
        """)
        orphaned_articles = self.cursor.fetchone()[0]
        if orphaned_articles > 0:
            print(f"      ❌ Found {orphaned_articles} articles with invalid law_id")
            return False
        else:
            print("      ✅ Articles -> Laws: All references valid")
        
        # Check sub_articles -> articles
        self.cursor.execute("""
            SELECT COUNT(*) FROM sub_articles sa 
            LEFT JOIN articles a ON sa.article_id = a.id 
            WHERE a.id IS NULL
        """)
        orphaned_sub_articles = self.cursor.fetchone()[0]
        if orphaned_sub_articles > 0:
            print(f"      ❌ Found {orphaned_sub_articles} sub_articles with invalid article_id")
            return False
        else:
            print("      ✅ Sub-articles -> Articles: All references valid")
        
        print("   ✅ Data integrity validation passed")
        return True
    
    def validate_data_completeness(self):
        """Validate that data is complete and meaningful"""
        
        print("\n📊 Validating data completeness...")
        
        # Get record counts
        tables = ['laws', 'parts', 'chapters', 'articles', 'sub_articles']
        counts = {}
        
        for table in tables:
            self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = self.cursor.fetchone()[0]
        
        print("   📈 Record counts:")
        for table, count in counts.items():
            print(f"      {table.capitalize()}: {count:,}")
        
        # Check for empty tables
        empty_tables = [table for table, count in counts.items() if count == 0]
        if empty_tables:
            print(f"      ❌ Empty tables: {empty_tables}")
            return False
        
        # Check for reasonable data distribution
        if counts['sub_articles'] < counts['articles']:
            print("      ⚠️  Warning: Fewer sub-articles than articles (unusual)")
        
        if counts['articles'] < counts['laws']:
            print("      ⚠️  Warning: Fewer articles than laws (unusual)")
        
        print("   ✅ Data completeness validation passed")
        return True
    
    def validate_search_functionality(self):
        """Validate that FTS5 search tables are working"""
        
        print("\n🔍 Validating search functionality...")
        
        # Check if FTS5 tables exist
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%fts%'")
        fts_tables = [row[0] for row in self.cursor.fetchall()]
        
        if not fts_tables:
            print("      ❌ No FTS5 tables found")
            return False
        
        print(f"      📋 Found FTS5 tables: {fts_tables}")
        
        # Test basic search functionality
        for table in fts_tables:
            try:
                # Test simple search
                self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = self.cursor.fetchone()[0]
                print(f"      ✅ {table}: {count:,} records")
                
                # Test MATCH query
                if 'law_search' in table:
                    self.cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE law_name MATCH 'penal'")
                    match_count = self.cursor.fetchone()[0]
                    print(f"         Search test: Found {match_count} matches for 'penal'")
                
            except Exception as e:
                print(f"      ❌ {table}: Error during validation - {e}")
                return False
        
        print("   ✅ Search functionality validation passed")
        return True
    
    def generate_validation_report(self):
        """Generate a comprehensive validation report"""
        
        print("\n📋 Generating validation report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'database': self.database_path,
            'structure_valid': False,
            'integrity_valid': False,
            'completeness_valid': False,
            'search_valid': False,
            'overall_valid': False
        }
        
        try:
            self.connect()
            
            # Run all validations
            report['structure_valid'] = self.validate_database_structure()
            report['integrity_valid'] = self.validate_data_integrity()
            report['completeness_valid'] = self.validate_data_completeness()
            report['search_valid'] = self.validate_search_functionality()
            
            # Overall validation
            report['overall_valid'] = all([
                report['structure_valid'],
                report['integrity_valid'],
                report['completeness_valid'],
                report['search_valid']
            ])
            
            # Print summary
            print("\n" + "="*60)
            print("📋 VALIDATION REPORT SUMMARY")
            print("="*60)
            print(f"   Database: {report['database']}")
            print(f"   Timestamp: {report['timestamp']}")
            print(f"   Structure: {'✅ PASS' if report['structure_valid'] else '❌ FAIL'}")
            print(f"   Integrity: {'✅ PASS' if report['integrity_valid'] else '❌ FAIL'}")
            print(f"   Completeness: {'✅ PASS' if report['completeness_valid'] else '❌ FAIL'}")
            print(f"   Search: {'✅ PASS' if report['search_valid'] else '❌ FAIL'}")
            print(f"   Overall: {'✅ PASS' if report['overall_valid'] else '❌ FAIL'}")
            print("="*60)
            
            if report['overall_valid']:
                print("\n🎉 All validations passed! Database is ready for use.")
            else:
                print("\n⚠️  Some validations failed. Please review the issues above.")
            
            return report
            
        except Exception as e:
            print(f"\n💥 Error during validation: {e}")
            import traceback
            traceback.print_exc()
            return report
        finally:
            self.close()

def main():
    """Main execution function"""
    
    print("🔍 Data Validation Script")
    print("=" * 50)
    
    # Check if database exists
    if not os.path.exists(DATABASE):
        print(f"❌ Database not found: {DATABASE}")
        print("💡 Please run the setup and population scripts first")
        return
    
    # Run validation
    validator = DataValidator()
    report = validator.generate_validation_report()
    
    # Save report to file
    try:
        import json
        report_file = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n💾 Validation report saved to: {report_file}")
    except Exception as e:
        print(f"\n⚠️  Could not save validation report: {e}")

if __name__ == "__main__":
    main()
