#!/usr/bin/env python3
"""
Dashboard Server - HTTP server for the recruiting dashboard.

This module provides a local HTTP server that serves the recruiting dashboard
with CORS support and automatically generates resume file paths for linking.

License: MIT License
Copyright (c) 2024 Scott White
See LICENSE file for full license text.
"""

import http.server
import socketserver
import os
import sys
import json
import argparse
from pathlib import Path

def find_resume_paths(search_dirs=None):
    """Find all resume files and their paths."""
    resume_paths = {}
    
    # Get directories to search
    current_dir = Path('.')
    if search_dirs:
        subdirs = [current_dir / dirname for dirname in search_dirs if (current_dir / dirname).is_dir()]
    else:
        subdirs = [d for d in current_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    print(f"🔍 Searching {len(subdirs)} directories for resume files...")
    
    for subdir in subdirs:
        # Look for PDF files
        for file_path in subdir.rglob('*.pdf'):
            filename = file_path.name
            resume_paths[filename] = str(file_path.relative_to(current_dir))
    
    print(f"📄 Found {len(resume_paths)} resume files")
    
    # Save to JSON file
    with open('resume_paths.json', 'w') as f:
        json.dump(resume_paths, f, indent=2)
    
    print("💾 Resume paths saved to resume_paths.json")
    return resume_paths

def main():
    parser = argparse.ArgumentParser(description='Serve the recruiting dashboard')
    parser.add_argument('csv_file', nargs='?', default='candidates.csv', 
                        help='CSV file with candidate data (default: candidates.csv)')
    parser.add_argument('--resume-dirs', nargs='*', 
                        help='Directories to search for resume files (default: all subdirectories)')
    parser.add_argument('--port', type=int, default=8003,
                        help='Port to serve on (default: 8003)')
    
    args = parser.parse_args()
    
    # Get the directory containing this script
    script_dir = Path(__file__).parent.absolute()
    
    # Change to the script directory
    os.chdir(script_dir)
    
    # Check if required files exist
    if not Path('recruiting_dashboard.html').exists():
        print("Error: recruiting_dashboard.html not found!")
        sys.exit(1)
    
    if not Path(args.csv_file).exists():
        print(f"Error: {args.csv_file} not found!")
        print(f"Please make sure {args.csv_file} exists in the same directory.")
        print("You can generate it by running: python resume_extractor.py")
        sys.exit(1)
    
    # Generate resume paths automatically
    print("🔄 Generating resume paths...")
    try:
        find_resume_paths(args.resume_dirs)
    except Exception as e:
        print(f"⚠️  Warning: Could not generate resume paths: {e}")
        print("   Resume links may not work, but dashboard will still function.")
    
    # Set up the server
    PORT = args.port
    
    # Create a custom handler to set CORS headers
    class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            super().end_headers()
        
        def do_OPTIONS(self):
            self.send_response(200)
            self.end_headers()
    
    try:
        with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
            print(f"🚀 Recruiting Dashboard server starting...")
            print(f"📊 Dashboard available at: http://localhost:{PORT}/recruiting_dashboard.html?csv={args.csv_file}")
            print(f"📁 Serving files from: {script_dir}")
            print(f"📋 CSV file: {Path(args.csv_file).absolute()}")
            print("\n" + "="*60)
            print("Press Ctrl+C to stop the server")
            print("="*60 + "\n")
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {PORT} is already in use!")
            print(f"Try using a different port or stop the process using port {PORT}")
        else:
            print(f"❌ Error starting server: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
