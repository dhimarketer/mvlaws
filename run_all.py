#!/usr/bin/env python3
"""
Master Execution Script for Law Analysis Tool
Runs all setup and population steps in the correct order
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def run_script(script_name, description):
    """Run a Python script and return success status"""
    
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    
    try:
        # Run the script
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, text=True, check=True)
        
        # Print output
        if result.stdout:
            print(result.stdout)
        
        print(f"✅ {description} completed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        if e.stdout:
            print("STDOUT:")
            print(e.stdout)
        if e.stderr:
            print("STDERR:")
            print(e.stderr)
        return False
    except Exception as e:
        print(f"❌ Unexpected error running {script_name}: {e}")
        return False

def check_prerequisites():
    """Check if all required files and directories exist"""
    
    print("🔍 Checking prerequisites...")
    
    # Check if laws directory exists
    if not os.path.exists("laws"):
        print("❌ 'laws' directory not found")
        print("💡 Please ensure you're in the correct directory")
        return False
    
    # Check if required scripts exist
    required_scripts = [
        "setup_database.py",
        "parse_laws.py", 
        "populate_database.py",
        "setup_fts5.py",
        "validate_data.py"
    ]
    
    missing_scripts = []
    for script in required_scripts:
        if not os.path.exists(script):
            missing_scripts.append(script)
    
    if missing_scripts:
        print(f"❌ Missing required scripts: {missing_scripts}")
        return False
    
    print("✅ All prerequisites met")
    return True

def backup_existing_database():
    """Backup existing database if it exists"""
    
    if os.path.exists("laws.db"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"laws_backup_{timestamp}.db"
        
        try:
            os.rename("laws.db", backup_name)
            print(f"💾 Backed up existing database to: {backup_name}")
            return True
        except Exception as e:
            print(f"⚠️  Could not backup existing database: {e}")
            print("💡 Continuing anyway...")
            return False
    
    return True

def main():
    """Main execution function"""
    
    print("🎯 Law Analysis Tool - Complete Setup")
    print("=" * 60)
    print("This script will:")
    print("1. Setup database schema")
    print("2. Parse all law text files")
    print("3. Populate database with parsed data")
    print("4. Setup FTS5 full-text search")
    print("5. Validate the complete setup")
    print("=" * 60)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please fix the issues above and try again.")
        return False
    
    # Backup existing database
    backup_existing_database()
    
    # Track execution status
    execution_status = {}
    
    # Step 1: Setup Database
    execution_status['database_setup'] = run_script(
        "setup_database.py", 
        "Step 1: Setting up database schema"
    )
    
    if not execution_status['database_setup']:
        print("\n❌ Database setup failed. Cannot continue.")
        return False
    
    # Step 2: Parse Laws
    execution_status['law_parsing'] = run_script(
        "parse_laws.py",
        "Step 2: Parsing law text files"
    )
    
    if not execution_status['law_parsing']:
        print("\n❌ Law parsing failed. Cannot continue.")
        return False
    
    # Step 3: Populate Database
    execution_status['database_population'] = run_script(
        "populate_database.py",
        "Step 3: Populating database with parsed data"
    )
    
    if not execution_status['database_population']:
        print("\n❌ Database population failed. Cannot continue.")
        return False
    
    # Step 4: Setup FTS5
    execution_status['fts5_setup'] = run_script(
        "setup_fts5.py",
        "Step 4: Setting up FTS5 full-text search"
    )
    
    if not execution_status['fts5_setup']:
        print("\n❌ FTS5 setup failed. Search functionality may not work properly.")
    
    # Step 5: Validate Data
    execution_status['data_validation'] = run_script(
        "validate_data.py",
        "Step 5: Validating complete setup"
    )
    
    # Print final summary
    print("\n" + "="*60)
    print("📋 EXECUTION SUMMARY")
    print("="*60)
    
    steps = [
        ("Database Setup", "database_setup"),
        ("Law Parsing", "law_parsing"),
        ("Database Population", "database_population"),
        ("FTS5 Setup", "fts5_setup"),
        ("Data Validation", "data_validation")
    ]
    
    for step_name, step_key in steps:
        status = execution_status.get(step_key, False)
        print(f"   {step_name}: {'✅ PASS' if status else '❌ FAIL'}")
    
    # Overall success
    critical_steps = ['database_setup', 'law_parsing', 'database_population']
    overall_success = all(execution_status.get(step, False) for step in critical_steps)
    
    print(f"\n   Overall: {'✅ SUCCESS' if overall_success else '❌ FAILED'}")
    print("="*60)
    
    if overall_success:
        print("\n🎉 Setup completed successfully!")
        print("💡 Your law analysis tool is now ready to use.")
        print("🚀 You can now run: python app.py")
        
        # Show database info
        if os.path.exists("laws.db"):
            try:
                import sqlite3
                conn = sqlite3.connect("laws.db")
                cursor = conn.cursor()
                
                # Get record counts
                tables = ['laws', 'articles', 'sub_articles']
                print("\n📊 Database Statistics:")
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"   {table.capitalize()}: {count:,}")
                
                conn.close()
            except Exception as e:
                print(f"   Could not retrieve database stats: {e}")
    else:
        print("\n⚠️  Setup completed with some failures.")
        print("💡 Please review the errors above and fix any issues.")
        print("🔧 You may need to run individual scripts to resolve problems.")
    
    return overall_success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
