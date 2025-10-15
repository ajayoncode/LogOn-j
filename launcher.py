#!/usr/bin/env python3
"""
LogOn Launcher - Starts the session manager and Streamlit app
"""

import subprocess
import sys
import time
import threading
from session_manager import session_manager

def start_streamlit():
    """Start the Streamlit app"""
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "streamlit_app.py", "--server.port", "6001"])
    except KeyboardInterrupt:
        print("\nShutting down Streamlit...")
    except Exception as e:
        print(f"Error starting Streamlit: {e}")

def main():
    print("🚀 Starting LogOn System...")
    
    # Start session manager
    print("📊 Starting Session Manager...")
    session_manager.start_monitoring()
    
    # Start Streamlit in a separate thread
    print("🌐 Starting Streamlit Dashboard...")
    streamlit_thread = threading.Thread(target=start_streamlit, daemon=True)
    streamlit_thread.start()
    
    try:
        print("✅ LogOn System is running!")
        print("🌐 Dashboard available at: http://localhost:6001")
        print("📊 Session monitoring is active")
        print("\nPress Ctrl+C to stop...")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down LogOn System...")
        session_manager.stop_all_sessions()
        print("✅ LogOn System stopped.")

if __name__ == "__main__":
    main()
