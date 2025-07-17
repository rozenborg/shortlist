#!/usr/bin/env python3
"""
Helper script to check server logs and test export with detailed error capture
"""

import subprocess
import threading
import time
import requests
import sys
from datetime import datetime

def start_server_with_logs():
    """Start the Flask server and capture its output"""
    print("🚀 Starting Flask server with log capture...")
    
    try:
        # Start the server process
        process = subprocess.Popen(
            [sys.executable, 'app.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        print("✅ Server process started")
        print("📋 Server logs will appear below:")
        print("-" * 50)
        
        # Read and print server output in real-time
        def print_logs():
            for line in process.stdout:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] {line.rstrip()}")
        
        # Start log printing in background thread
        log_thread = threading.Thread(target=print_logs, daemon=True)
        log_thread.start()
        
        # Wait for server to start
        time.sleep(3)
        
        # Test if server is responsive
        for attempt in range(5):
            try:
                response = requests.get("http://localhost:5001/", timeout=2)
                if response.status_code == 200:
                    print("\n✅ Server is ready for testing!")
                    break
            except:
                print(f"⏳ Waiting for server... (attempt {attempt + 1}/5)")
                time.sleep(2)
        else:
            print("❌ Server failed to start properly")
            return None
        
        return process
        
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return None

def test_export_with_logs():
    """Test export and capture any server-side errors"""
    print("\n" + "="*50)
    print("🧪 Testing Export with Server Log Monitoring")
    print("="*50)
    
    try:
        print("🔄 Sending export request...")
        response = requests.post(
            "http://localhost:5001/api/export",
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📊 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print(f"✅ Export successful! ({len(response.content)} bytes)")
            with open('test_with_logs.xlsx', 'wb') as f:
                f.write(response.content)
            print("💾 Saved as 'test_with_logs.xlsx'")
        else:
            print(f"❌ Export failed!")
            try:
                error_data = response.json()
                print(f"📄 Error response: {error_data}")
            except:
                print(f"📄 Raw response: {response.text}")
                
    except Exception as e:
        print(f"❌ Request failed: {e}")

def main():
    print("🔍 Server Log Monitor for Export Testing")
    print("This will start the server and show real-time logs")
    print("="*60)
    
    # Start server with log monitoring
    server_process = start_server_with_logs()
    
    if not server_process:
        print("❌ Could not start server")
        return
    
    try:
        # Wait a moment for server to fully initialize
        time.sleep(2)
        
        # Test the export
        test_export_with_logs()
        
        # Keep monitoring logs for a bit
        print("\n📋 Monitoring logs for 10 more seconds...")
        time.sleep(10)
        
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    finally:
        # Clean up
        print("\n🧹 Shutting down server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print("✅ Server stopped")

if __name__ == '__main__':
    main() 