#!/usr/bin/env python3
"""
Dashboard Test Suite - Verification script for the recruiting dashboard.

This module provides comprehensive testing functionality to verify that
the dashboard files exist, CSV data is properly formatted, and resume
directories are accessible.

License: MIT License
Copyright (c) 2024 Scott White
See LICENSE file for full license text.
"""

import csv
import json
import argparse
from pathlib import Path

def test_csv_parsing(csv_filename='candidates.csv'):
    """Test that the CSV file can be parsed correctly."""
    csv_file = Path(csv_filename)
    
    if not csv_file.exists():
        print(f"❌ {csv_filename} not found!")
        return False
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        print(f"✅ Successfully parsed {len(rows)} candidate records")
        
        # Check required columns
        required_columns = [
            'candidate_name', 'email', 'overall_score', 'bachelors_university',
            'github_link', 'linkedin_link', 'estimated_job_level'
        ]
        
        missing_columns = []
        for col in required_columns:
            if col not in reader.fieldnames:
                missing_columns.append(col)
        
        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
            return False
        
        print("✅ All required columns present")
        
        # Check data quality
        valid_scores = 0
        valid_emails = 0
        valid_names = 0
        
        for row in rows:
            try:
                score = float(row.get('overall_score', 0))
                if score > 0:
                    valid_scores += 1
            except (ValueError, TypeError):
                pass
            
            if row.get('email', '').strip():
                valid_emails += 1
                
            if row.get('candidate_name', '').strip():
                valid_names += 1
        
        print(f"📊 Data quality check:")
        print(f"   - Valid scores: {valid_scores}/{len(rows)}")
        print(f"   - Valid emails: {valid_emails}/{len(rows)}")
        print(f"   - Valid names: {valid_names}/{len(rows)}")
        
        # Show top 5 candidates
        sorted_rows = sorted(rows, key=lambda x: float(x.get('overall_score', 0)), reverse=True)
        print(f"\n🏆 Top 5 candidates by score:")
        for i, row in enumerate(sorted_rows[:5], 1):
            name = row.get('candidate_name', 'Unknown')
            score = row.get('overall_score', '0')
            university = row.get('bachelors_university', row.get('graduate_university', 'Unknown'))
            print(f"   {i}. {name} - Score: {score} - {university}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error parsing CSV: {e}")
        return False

def test_dashboard_files(csv_filename='candidates.csv'):
    """Test that all required dashboard files exist."""
    required_files = [
        'recruiting_dashboard.html',
        'serve_dashboard.py',
        csv_filename
    ]
    
    optional_files = [
        'resume_extractor.py',
        'requirements.txt',
        '.gitignore'
    ]
    
    print("📁 Checking required files:")
    all_exist = True
    
    for file in required_files:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} (missing)")
            all_exist = False
    
    print("\n📋 Checking optional files:")
    for file in optional_files:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ⚪ {file} (optional)")
    
    return all_exist

def generate_sample_data(csv_filename='candidates.csv'):
    """Generate a small sample of the data for testing."""
    csv_file = Path(csv_filename)
    
    if not csv_file.exists():
        print(f"❌ {csv_filename} not found!")
        return
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Take first 5 rows for sample
        sample_rows = rows[:5]
        
        print(f"\n📋 Sample data (first 5 candidates):")
        for i, row in enumerate(sample_rows, 1):
            print(f"\n{i}. {row.get('candidate_name', 'Unknown')}")
            print(f"   Email: {row.get('email', 'N/A')}")
            print(f"   Score: {row.get('overall_score', 'N/A')}")
            print(f"   University: {row.get('bachelors_university', row.get('graduate_university', 'N/A'))}")
            print(f"   Job Level: {row.get('estimated_job_level', 'N/A')}")
            print(f"   GitHub: {row.get('github_link', 'N/A')}")
            print(f"   LinkedIn: {row.get('linkedin_link', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error reading sample data: {e}")

def test_resume_directories():
    """Test for resume directories and files."""
    current_dir = Path('.')
    subdirs = [d for d in current_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    print(f"📂 Checking resume directories ({len(subdirs)} found):")
    
    total_resumes = 0
    for subdir in subdirs[:5]:  # Show first 5 directories
        pdf_files = list(subdir.rglob('*.pdf'))
        dir_total = len(pdf_files)
        total_resumes += dir_total
        
        if dir_total > 0:
            print(f"   📁 {subdir.name}: {dir_total} resume files")
        
    if len(subdirs) > 5:
        # Count remaining directories
        for subdir in subdirs[5:]:
            pdf_files = list(subdir.rglob('*.pdf'))
            total_resumes += len(pdf_files)
        
        print(f"   ... and {len(subdirs) - 5} more directories")
    
    print(f"📄 Total resume files found: {total_resumes}")
    
    if total_resumes == 0:
        print("⚠️  No resume files found. Resume links will not work.")
        
    return total_resumes > 0

def main():
    """Run all tests."""
    parser = argparse.ArgumentParser(description='Test the recruiting dashboard')
    parser.add_argument('csv_file', nargs='?', default='candidates.csv',
                        help='CSV file with candidate data (default: candidates.csv)')
    
    args = parser.parse_args()
    
    print("🧪 Testing Recruiting Dashboard")
    print("=" * 50)
    
    # Test file existence
    files_ok = test_dashboard_files(args.csv_file)
    print()
    
    if not files_ok:
        print("❌ Missing required files. Please ensure all files are present.")
        return
    
    # Test CSV parsing
    csv_ok = test_csv_parsing(args.csv_file)
    print()
    
    # Test resume directories
    resumes_ok = test_resume_directories()
    print()
    
    if csv_ok:
        # Generate sample data
        generate_sample_data(args.csv_file)
        print()
        
        if resumes_ok:
            print("✅ Dashboard is fully ready to use!")
        else:
            print("⚠️  Dashboard ready, but resume links may not work")
            
        print(f"🚀 Run 'python serve_dashboard.py {args.csv_file}' to start the server")
        print("   (Server will automatically generate resume paths)")
        print(f"🌐 Open http://localhost:8003/recruiting_dashboard.html?csv={args.csv_file} in your browser")
    else:
        print(f"❌ CSV parsing failed. Please check the {args.csv_file} file.")

if __name__ == "__main__":
    main()
