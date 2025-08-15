#!/usr/bin/env python3
"""
Database Duplicate Cleanup Script for Law Analysis Tool
Removes duplicate entries while maintaining referential integrity
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Tuple, Dict

DATABASE = "laws.db"
BACKUP_DB = f"laws_backup_before_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

class DuplicateCleaner:
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
            
    def backup_database(self):
        """Create a backup of the database before cleanup"""
        if os.path.exists(self.database_path):
            import shutil
            shutil.copy2(self.database_path, BACKUP_DB)
            print(f"✅ Database backed up to: {BACKUP_DB}")
            return True
        return False
    
    def get_duplicate_laws(self) -> List[Tuple]:
        """Get all duplicate laws with their IDs"""
        self.cursor.execute("""
            SELECT law_name, file_name, GROUP_CONCAT(id) as ids, COUNT(*) as count
            FROM laws 
            GROUP BY law_name, file_name 
            HAVING COUNT(*) > 1
            ORDER BY law_name
        """)
        return self.cursor.fetchall()
    
    def get_duplicate_articles(self) -> List[Tuple]:
        """Get all duplicate articles with their IDs"""
        self.cursor.execute("""
            SELECT law_id, article_number, article_title, GROUP_CONCAT(id) as ids, COUNT(*) as count
            FROM articles 
            GROUP BY law_id, article_number, article_title 
            HAVING COUNT(*) > 1
            ORDER BY law_id, article_number
        """)
        return self.cursor.fetchall()
    
    def get_duplicate_sub_articles(self) -> List[Tuple]:
        """Get all duplicate sub_articles with their IDs"""
        self.cursor.execute("""
            SELECT article_id, sub_article_label, text_content, GROUP_CONCAT(id) as ids, COUNT(*) as count
            FROM sub_articles 
            GROUP BY article_id, sub_article_label, text_content 
            HAVING COUNT(*) > 1
            ORDER BY article_id, sub_article_label
        """)
        return self.cursor.fetchall()
    
    def cleanup_sub_articles(self) -> int:
        """Remove duplicate sub_articles, keeping the one with the earliest created_at"""
        print("🧹 Cleaning up duplicate sub_articles...")
        
        duplicates = self.get_duplicate_sub_articles()
        removed_count = 0
        
        for duplicate in duplicates:
            article_id, sub_article_label, text_content, ids_str, count = duplicate
            ids = [int(id_str) for id_str in ids_str.split(',')]
            
            if len(ids) > 1:
                # Keep the one with earliest created_at, remove others
                self.cursor.execute("""
                    SELECT id, created_at FROM sub_articles 
                    WHERE id IN ({})
                    ORDER BY created_at ASC
                """.format(','.join('?' * len(ids))), ids)
                
                ordered_ids = [row[0] for row in self.cursor.fetchall()]
                keep_id = ordered_ids[0]  # Keep the earliest one
                remove_ids = ordered_ids[1:]  # Remove the rest
                
                # Delete duplicates
                for remove_id in remove_ids:
                    self.cursor.execute("DELETE FROM sub_articles WHERE id = ?", (remove_id,))
                    removed_count += 1
                
                print(f"   ✅ Removed {len(remove_ids)} duplicate sub_articles for article {article_id}, kept ID {keep_id}")
        
        self.conn.commit()
        print(f"✅ Removed {removed_count} duplicate sub_articles")
        return removed_count
    
    def cleanup_articles(self) -> int:
        """Remove duplicate articles, keeping the one with the earliest created_at"""
        print("🧹 Cleaning up duplicate articles...")
        
        duplicates = self.get_duplicate_articles()
        removed_count = 0
        
        for duplicate in duplicates:
            law_id, article_number, article_title, ids_str, count = duplicate
            ids = [int(id_str) for id_str in ids_str.split(',')]
            
            if len(ids) > 1:
                # Keep the one with earliest created_at, remove others
                self.cursor.execute("""
                    SELECT id, created_at FROM articles 
                    WHERE id IN ({})
                    ORDER BY created_at ASC
                """.format(','.join('?' * len(ids))), ids)
                
                ordered_ids = [row[0] for row in self.cursor.fetchall()]
                keep_id = ordered_ids[0]  # Keep the earliest one
                remove_ids = ordered_ids[1:]  # Remove the rest
                
                # For each article to remove, first move its sub_articles to the kept article
                for remove_id in remove_ids:
                    # Check if the article to be removed has sub_articles
                    self.cursor.execute("SELECT COUNT(*) FROM sub_articles WHERE article_id = ?", (remove_id,))
                    sub_article_count = self.cursor.fetchone()[0]
                    
                    if sub_article_count > 0:
                        # Move sub_articles to the kept article
                        self.cursor.execute("""
                            UPDATE sub_articles 
                            SET article_id = ? 
                            WHERE article_id = ?
                        """, (keep_id, remove_id))
                        print(f"      📝 Moved {sub_article_count} sub_articles from article {remove_id} to {keep_id}")
                    
                    # Now delete the article
                    self.cursor.execute("DELETE FROM articles WHERE id = ?", (remove_id,))
                    removed_count += 1
                
                print(f"   ✅ Removed {len(remove_ids)} duplicate articles for law {law_id}, kept ID {keep_id}")
        
        self.conn.commit()
        print(f"✅ Removed {removed_count} duplicate articles")
        return removed_count
    
    def cleanup_laws(self) -> int:
        """Remove duplicate laws, keeping the one with the earliest created_at"""
        print("🧹 Cleaning up duplicate laws...")
        
        duplicates = self.get_duplicate_laws()
        removed_count = 0
        
        for duplicate in duplicates:
            law_name, file_name, ids_str, count = duplicate
            ids = [int(id_str) for id_str in ids_str.split(',')]
            
            if len(ids) > 1:
                # Keep the one with earliest created_at, remove others
                self.cursor.execute("""
                    SELECT id, created_at FROM laws 
                    WHERE id IN ({})
                    ORDER BY created_at ASC
                """.format(','.join('?' * len(ids))), ids)
                
                ordered_ids = [row[0] for row in self.cursor.fetchall()]
                keep_id = ordered_ids[0]  # Keep the earliest one
                remove_ids = ordered_ids[1:]  # Remove the rest
                
                # For each law to remove, first move its articles to the kept law
                for remove_id in remove_ids:
                    # Check if the law to be removed has parts
                    self.cursor.execute("SELECT COUNT(*) FROM parts WHERE law_id = ?", (remove_id,))
                    part_count = self.cursor.fetchone()[0]
                    
                    if part_count > 0:
                        # Move parts to the kept law
                        self.cursor.execute("""
                            UPDATE parts 
                            SET law_id = ? 
                            WHERE law_id = ?
                        """, (keep_id, remove_id))
                        print(f"      📝 Moved {part_count} parts from law {remove_id} to {keep_id}")
                    
                    # Check if the law to be removed has articles
                    self.cursor.execute("SELECT COUNT(*) FROM articles WHERE law_id = ?", (remove_id,))
                    article_count = self.cursor.fetchone()[0]
                    
                    if article_count > 0:
                        # Move articles to the kept law
                        self.cursor.execute("""
                            UPDATE articles 
                            SET law_id = ? 
                            WHERE law_id = ?
                        """, (keep_id, remove_id))
                        print(f"      📝 Moved {article_count} articles from law {remove_id} to {keep_id}")
                    
                    # Now delete the law
                    self.cursor.execute("DELETE FROM laws WHERE id = ?", (remove_id,))
                    removed_count += 1
                
                print(f"   ✅ Removed {len(remove_ids)} duplicate laws: {law_name[:50]}..., kept ID {keep_id}")
        
        self.conn.commit()
        print(f"✅ Removed {removed_count} duplicate laws")
        return removed_count
    
    def verify_cleanup(self):
        """Verify that duplicates have been removed"""
        print("\n🔍 Verifying cleanup results...")
        
        # Check laws
        self.cursor.execute("""
            SELECT COUNT(*) as duplicate_count FROM (
                SELECT law_name, file_name, COUNT(*) as count 
                FROM laws 
                GROUP BY law_name, file_name 
                HAVING COUNT(*) > 1
            )
        """)
        law_duplicates = self.cursor.fetchone()[0]
        
        # Check articles
        self.cursor.execute("""
            SELECT COUNT(*) as duplicate_count FROM (
                SELECT law_id, article_number, article_title, COUNT(*) as count 
                FROM articles 
                GROUP BY law_id, article_number, article_title 
                HAVING COUNT(*) > 1
            )
        """)
        article_duplicates = self.cursor.fetchone()[0]
        
        # Check sub_articles
        self.cursor.execute("""
            SELECT COUNT(*) as duplicate_count FROM (
                SELECT article_id, sub_article_label, text_content, COUNT(*) as count 
                FROM sub_articles 
                GROUP BY article_id, sub_article_label, text_content 
                HAVING COUNT(*) > 1
            )
        """)
        sub_article_duplicates = self.cursor.fetchone()[0]
        
        print(f"📊 Remaining duplicates:")
        print(f"   Laws: {law_duplicates}")
        print(f"   Articles: {article_duplicates}")
        print(f"   Sub-articles: {sub_article_duplicates}")
        
        if law_duplicates == 0 and article_duplicates == 0 and sub_article_duplicates == 0:
            print("🎉 All duplicates have been successfully removed!")
        else:
            print("⚠️  Some duplicates remain. Manual review may be needed.")
    
    def get_final_counts(self):
        """Get final record counts after cleanup"""
        print("\n📊 Final database statistics:")
        
        self.cursor.execute("SELECT COUNT(*) FROM laws")
        law_count = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM articles")
        article_count = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM sub_articles")
        sub_article_count = self.cursor.fetchone()[0]
        
        print(f"   Laws: {law_count}")
        print(f"   Articles: {article_count}")
        print(f"   Sub-articles: {sub_article_count}")
        
        return law_count, article_count, sub_article_count
    
    def run_cleanup(self):
        """Run the complete cleanup process"""
        print("🚀 Starting database duplicate cleanup...")
        print("=" * 60)
        
        try:
            # Backup database
            self.backup_database()
            
            # Connect to database
            self.connect()
            
            # Get initial counts
            print("\n📊 Initial database statistics:")
            self.cursor.execute("SELECT COUNT(*) FROM laws")
            initial_laws = self.cursor.fetchone()[0]
            self.cursor.execute("SELECT COUNT(*) FROM articles")
            initial_articles = self.cursor.fetchone()[0]
            self.cursor.execute("SELECT COUNT(*) FROM sub_articles")
            initial_sub_articles = self.cursor.fetchone()[0]
            
            print(f"   Laws: {initial_laws}")
            print(f"   Articles: {initial_articles}")
            print(f"   Sub-articles: {initial_sub_articles}")
            
            # Cleanup in reverse dependency order
            removed_sub_articles = self.cleanup_sub_articles()
            removed_articles = self.cleanup_articles()
            removed_laws = self.cleanup_laws()
            
            # Verify cleanup
            self.verify_cleanup()
            
            # Get final counts
            final_laws, final_articles, final_sub_articles = self.get_final_counts()
            
            # Summary
            print("\n📋 Cleanup Summary:")
            print("=" * 30)
            print(f"Removed duplicate laws: {removed_laws}")
            print(f"Removed duplicate articles: {removed_articles}")
            print(f"Removed duplicate sub-articles: {removed_sub_articles}")
            print(f"Total records removed: {removed_laws + removed_articles + removed_sub_articles}")
            print(f"Database size reduced by: {((initial_laws + initial_articles + initial_sub_articles) - (final_laws + final_articles + final_sub_articles))} records")
            
            print(f"\n✅ Cleanup completed successfully!")
            print(f"💾 Backup saved to: {BACKUP_DB}")
            
        except Exception as e:
            print(f"\n❌ Error during cleanup: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.close()

if __name__ == "__main__":
    cleaner = DuplicateCleaner()
    cleaner.run_cleanup()
