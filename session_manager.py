import os
import json
import time
import threading
import subprocess
import csv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import signal
import sys

class SessionManager:
    def __init__(self):
        self.current_session = None
        self.session_lock = threading.Lock()
        base_dir = Path(__file__).parent.resolve()
        self.csv_file = str((base_dir / "logger_data" / "sessions.csv").resolve())
        self.verticals_file = str((base_dir / "verticals.json").resolve())
        self.auto_session_project = "systemOn"
        self.auto_session_goal = "auto start sessess"
        self.manual_timeout = 20 * 60  # 20 minutes
        self.running = False
        self.screen_monitor_thread = None
        
        # Ensure directories exist
        Path(self.csv_file).parent.mkdir(exist_ok=True)
        
        # Initialize CSV file if it doesn't exist
        self._init_csv_file()
        
        # Load verticals
        self.verticals = self._load_verticals()
        
        # Setup signal handlers for graceful shutdown (only in main thread)
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError:
            # Signal handlers can only be set in the main thread
            # This is expected when running in Streamlit or other contexts
            pass
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.stop_all_sessions()
        sys.exit(0)
    
    def _init_csv_file(self):
        """Initialize CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'session_id', 'start_time', 'end_time', 'duration_minutes', 
                    'project', 'goal', 'session_type', 'status', 'auto_closed'
                ])
    
    def _load_verticals(self) -> List[str]:
        """Load verticals from JSON file"""
        try:
            with open(self.verticals_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return ["systemOn"]
    
    def _save_verticals(self):
        """Save verticals to JSON file"""
        with open(self.verticals_file, 'w') as f:
            json.dump(self.verticals, f, indent=2)
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"session_{int(time.time())}_{os.getpid()}"
    
    def _detect_screen_lock(self) -> bool:
        """Detect if screen is locked (Linux specific)"""
        try:
            # Check if screensaver is active or screen is locked
            result = subprocess.run(['gnome-screensaver-command', '--query'], 
                                  capture_output=True, text=True, timeout=5)
            if 'is active' in result.stdout or 'is locked' in result.stdout:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        try:
            # Alternative method using loginctl
            result = subprocess.run(['loginctl', 'show-session', '$(loginctl | grep $(whoami) | awk "{print $1}")', '-p', 'Active'], 
                                  capture_output=True, text=True, timeout=5)
            if 'Active=no' in result.stdout:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return False
    
    def _monitor_screen_lock(self):
        """Monitor screen lock status in background thread"""
        last_lock_status = False
        
        while self.running:
            try:
                is_locked = self._detect_screen_lock()
                
                # Screen just got locked
                if is_locked and not last_lock_status:
                    self._on_screen_locked()
                
                # Screen just got unlocked
                elif not is_locked and last_lock_status:
                    self._on_screen_unlocked()
                
                last_lock_status = is_locked
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                print(f"Error monitoring screen lock: {e}")
                time.sleep(5)
    
    def _on_screen_locked(self):
        """Handle screen lock event"""
        with self.session_lock:
            if self.current_session:
                self._end_current_session("Screen locked")
                print("Screen locked - session ended")
    
    def _on_screen_unlocked(self):
        """Handle screen unlock event"""
        with self.session_lock:
            if not self.current_session:
                # Check if we should resume a previous session
                previous_session = self._get_last_incomplete_session()
                if previous_session:
                    self._resume_session(previous_session)
                    print("Screen unlocked - previous session resumed")
                else:
                    # Start auto session
                    self._start_auto_session()
                    print("Screen unlocked - auto session started")
    
    def _get_last_incomplete_session(self) -> Optional[Dict]:
        """Get the last incomplete session from CSV"""
        try:
            with open(self.csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                sessions = list(reader)
                
            # Find the last session that's not closed
            for session in reversed(sessions):
                if session['status'] == 'in_progress':
                    return session
        except Exception as e:
            print(f"Error reading sessions: {e}")
        
        return None
    
    def _resume_session(self, session_data: Dict):
        """Resume a previous session"""
        # Parse stored ISO time and ensure it's timezone-aware
        if session_data['start_time']:
            start_time = datetime.fromisoformat(session_data['start_time'])
            # If naive, localize to IST; if aware, convert to IST
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=ZoneInfo('Asia/Kolkata'))
            else:
                start_time = start_time.astimezone(ZoneInfo('Asia/Kolkata'))
        else:
            start_time = datetime.now(ZoneInfo('Asia/Kolkata'))
            
        self.current_session = {
            'id': session_data['session_id'],
            'start_time': start_time,
            'project': session_data['project'],
            'goal': session_data['goal'],
            'type': session_data['session_type'],
            'timeout_thread': None
        }
        
        # Start timeout thread if it's a manual session
        if session_data['session_type'] == 'manual':
            self._start_manual_timeout()
    
    def _start_auto_session(self):
        """Start automatic session with systemOn project"""
        self._start_session(self.auto_session_project, self.auto_session_goal, 'auto')
    
    def start_manual_session(self, project: str, goal: str) -> bool:
        """Start manual session (called from Streamlit UI)"""
        with self.session_lock:
            if self.current_session:
                if self.current_session['type'] == 'auto':
                    # End auto session and start manual
                    self._end_current_session("Manual session started")
                else:
                    # Already have manual session
                    return False
            
            return self._start_session(project, goal, 'manual')
    
    def _start_session(self, project: str, goal: str, session_type: str) -> bool:
        """Start a new session"""
        session_id = self._generate_session_id()
        # Use timezone-aware IST timestamps
        start_time = datetime.now(ZoneInfo('Asia/Kolkata'))
        
        self.current_session = {
            'id': session_id,
            'start_time': start_time,
            'project': project,
            'goal': goal,
            'type': session_type,
            'timeout_thread': None
        }
        
        # Write to CSV
        self._write_session_to_csv(session_id, start_time, None, 0, project, goal, session_type, 'in_progress', False)
        
        # Start timeout thread for manual sessions
        if session_type == 'manual':
            self._start_manual_timeout()
        
        return True
    
    def _start_manual_timeout(self):
        """Start timeout thread for manual sessions"""
        if self.current_session and self.current_session['timeout_thread'] is None:
            self.current_session['timeout_thread'] = threading.Timer(
                self.manual_timeout, 
                self._manual_timeout_callback
            )
            self.current_session['timeout_thread'].start()
    
    def _manual_timeout_callback(self):
        """Callback for manual session timeout"""
        with self.session_lock:
            if self.current_session and self.current_session['type'] == 'manual':
                self._end_current_session("Manual session timeout (20 minutes)")
                # Start auto session after manual timeout
                self._start_auto_session()
                print("Manual session ended after 20 minutes - auto session started")
    
    def _end_current_session(self, reason: str = "Manual stop"):
        """End the current session"""
        if not self.current_session:
            return
        
        # Cancel timeout thread if exists
        if self.current_session['timeout_thread']:
            self.current_session['timeout_thread'].cancel()
        
        # Calculate duration
        end_time = datetime.now(ZoneInfo('Asia/Kolkata'))
        duration = end_time - self.current_session['start_time']
        duration_minutes = duration.total_seconds() / 60
        
        # Update CSV
        self._update_session_in_csv(
            self.current_session['id'],
            end_time,
            duration_minutes,
            'closed',
            reason == "Manual session timeout (20 minutes)"
        )
        
        self.current_session = None
    
    def stop_current_session(self) -> bool:
        """Stop current session (called from Streamlit UI)"""
        with self.session_lock:
            if self.current_session:
                session_type = self.current_session['type']
                self._end_current_session("Manual stop")
                
                # If stopping auto session, don't start another one automatically
                if session_type == 'auto':
                    print("Auto session stopped manually")
                    return True
                else:
                    # If stopping manual session, start auto session
                    self._start_auto_session()
                    print("Manual session stopped - auto session started")
                    return True
            return False
    
    def stop_auto_session(self) -> bool:
        """Stop only auto session (called from Streamlit UI)"""
        with self.session_lock:
            if self.current_session and self.current_session['type'] == 'auto':
                self._end_current_session("Auto session stopped manually")
                print("Auto session stopped manually")
                return True
            return False
    
    def stop_all_sessions(self):
        """Stop all sessions and cleanup"""
        self.running = False
        with self.session_lock:
            if self.current_session:
                self._end_current_session("System shutdown")
        
        if self.screen_monitor_thread and self.screen_monitor_thread.is_alive():
            self.screen_monitor_thread.join(timeout=5)
    
    def get_current_session_status(self) -> Optional[Dict]:
        """Get current session status for UI"""
        with self.session_lock:
            if self.current_session:
                # Ensure both times are timezone-aware for calculation
                now = datetime.now(ZoneInfo('Asia/Kolkata'))
                start_time = self.current_session['start_time']
                duration = now - start_time
                return {
                    'id': self.current_session['id'],
                    'project': self.current_session['project'],
                    'goal': self.current_session['goal'],
                    'type': self.current_session['type'],
                    'start_time': start_time.strftime('%H:%M:%S'),
                    'duration_minutes': round(duration.total_seconds() / 60, 1),
                    'status': 'running'
                }
        return None
    
    def _write_session_to_csv(self, session_id: str, start_time: datetime, end_time: Optional[datetime], 
                            duration_minutes: float, project: str, goal: str, session_type: str, 
                            status: str, auto_closed: bool):
        """Write session data to CSV"""
        try:
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Enforce ISO format with timezone info in seconds precision
                start_str = (
                    start_time.replace(microsecond=0).isoformat()
                    if isinstance(start_time, datetime) else str(start_time)
                )
                end_str = (
                    end_time.replace(microsecond=0).isoformat()
                    if isinstance(end_time, datetime) and end_time is not None else ''
                )
                writer.writerow([
                    session_id,
                    start_str,
                    end_str,
                    round(duration_minutes, 2),
                    project,
                    goal,
                    session_type,
                    status,
                    auto_closed
                ])
        except Exception as e:
            print(f"Error writing to CSV: {e}")
    
    def _update_session_in_csv(self, session_id: str, end_time: datetime, 
                             duration_minutes: float, status: str, auto_closed: bool):
        """Update existing session in CSV"""
        try:
            # Read all rows
            rows = []
            with open(self.csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            # Update the matching row
            for i, row in enumerate(rows):
                if i == 0:  # Skip header
                    continue
                if row[0] == session_id:  # session_id is first column
                    # Enforce ISO format with timezone info in seconds precision
                    rows[i][2] = end_time.replace(microsecond=0).isoformat()  # end_time
                    rows[i][3] = round(duration_minutes, 2)  # duration_minutes
                    rows[i][7] = status  # status
                    rows[i][8] = auto_closed  # auto_closed
                    break
            
            # Write back to file
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
                
        except Exception as e:
            print(f"Error updating CSV: {e}")
    
    def get_session_history(self, limit: int = 100) -> List[Dict]:
        """Get session history for UI"""
        try:
            with open(self.csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                sessions = list(reader)
            
            # Sort by start_time descending and limit
            sessions.sort(key=lambda x: x['start_time'], reverse=True)
            return sessions[:limit]
            
        except Exception as e:
            print(f"Error reading session history: {e}")
            return []
    
    def start_monitoring(self):
        """Start the session manager and screen monitoring"""
        if not self.running:
            self.running = True
            self.screen_monitor_thread = threading.Thread(target=self._monitor_screen_lock, daemon=True)
            self.screen_monitor_thread.start()
            
            # Start auto session if screen is unlocked
            if not self._detect_screen_lock():
                self._on_screen_unlocked()
    
    def add_vertical(self, name: str) -> bool:
        """Add a new vertical/project"""
        if name not in self.verticals:
            self.verticals.append(name)
            self._save_verticals()
            return True
        return False
    
    def get_verticals(self) -> List[str]:
        """Get list of available verticals/projects"""
        return self.verticals.copy()


# Global session manager instance - lazy loaded
_session_manager_instance = None

def get_session_manager():
    """Get the global session manager instance (lazy loaded)"""
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = SessionManager()
    return _session_manager_instance

# For backward compatibility, create a property-like access
class SessionManagerProxy:
    def __getattr__(self, name):
        return getattr(get_session_manager(), name)

session_manager = SessionManagerProxy()
