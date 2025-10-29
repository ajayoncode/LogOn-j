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
        # Auto session removed; manual sessions only
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
    
    def _fmt_dt(self, dt: Optional[datetime]) -> str:
        """Format datetime as ISO without microseconds and without timezone offset, in IST."""
        if dt is None:
            return ''
        if dt.tzinfo is None:
            # Assume naive is already local time; just drop microseconds
            return dt.replace(microsecond=0).isoformat()
        # Convert to IST, strip tzinfo
        ist = dt.astimezone(ZoneInfo('Asia/Kolkata')).replace(microsecond=0)
        return ist.replace(tzinfo=None).isoformat()
    
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
        """Screen lock handling disabled"""
        return
    
    def _on_screen_unlocked(self):
        """Handle screen unlock event (auto sessions disabled)"""
        return
    
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
    
    # Auto session capability removed
    
    def start_manual_session(self, project: str, goal: str) -> bool:
        """Start manual session (called from Streamlit UI)"""
        with self.session_lock:
            if self.current_session:
                # Already have a session running; do not start another
                return False
            
            return self._start_session(project, goal, 'manual')
    
    def _start_session(self, project: str, goal: str, session_type: str) -> bool:
        """Start a new session"""
        session_id = self._generate_session_id()
        # Use timezone-aware IST timestamps for both memory and CSV
        start_time = datetime.now(ZoneInfo('Asia/Kolkata'))
        
        self.current_session = {
            'id': session_id,
            'start_time': start_time,
            'project': project,
            'goal': goal,
            'type': session_type,
            'timeout_thread': None,
            'paused': False,
            'paused_start': None,
            'total_paused_duration': timedelta(0)  # Track total time paused
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
    
    def _end_current_session(self, reason: str = "Manual stop"):
        """End the current session"""
        if not self.current_session:
            return
        
        # Cancel timeout thread if exists
        if self.current_session['timeout_thread']:
            self.current_session['timeout_thread'].cancel()
        
        # Calculate duration excluding paused time
        end_time = datetime.now(ZoneInfo('Asia/Kolkata'))
        total_duration = end_time - self.current_session['start_time']
        paused_total = self.current_session.get('total_paused_duration', timedelta(0))
        # If currently paused, include the ongoing paused period
        if self.current_session.get('paused') and self.current_session.get('paused_start'):
            paused_total += (end_time - self.current_session['paused_start'])
        active_duration = total_duration - paused_total
        if active_duration.total_seconds() < 0:
            active_duration = timedelta(0)
        duration_minutes = active_duration.total_seconds() / 60
        
        # Update CSV
        self._update_session_in_csv(
            self.current_session['id'],
            end_time,
            duration_minutes,
            'closed',
            reason == "Manual session timeout (20 minutes)"
        )
        
        self.current_session = None
    
    def pause_session(self) -> bool:
        """Pause current session"""
        with self.session_lock:
            if self.current_session and not self.current_session['paused']:
                self.current_session['paused'] = True
                self.current_session['paused_start'] = datetime.now(ZoneInfo('Asia/Kolkata'))
                # Cancel timeout when paused
                if self.current_session['timeout_thread']:
                    self.current_session['timeout_thread'].cancel()
                return True
            return False
    
    def resume_session(self) -> bool:
        """Resume paused session"""
        with self.session_lock:
            if self.current_session and self.current_session['paused']:
                # Calculate paused duration and add to total
                if self.current_session['paused_start']:
                    pause_end = datetime.now(ZoneInfo('Asia/Kolkata'))
                    paused_duration = pause_end - self.current_session['paused_start']
                    self.current_session['total_paused_duration'] += paused_duration
                
                self.current_session['paused'] = False
                self.current_session['paused_start'] = None
                
                # Restart timeout for manual sessions
                if self.current_session['type'] == 'manual':
                    self._start_manual_timeout()
                
                return True
            return False
    
    def stop_current_session(self) -> bool:
        """Stop current session (called from Streamlit UI)"""
        with self.session_lock:
            if self.current_session:
                self._end_current_session("Manual stop")
                return True
            return False
    
    def stop_auto_session(self) -> bool:
        """Auto sessions disabled"""
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
                total_duration = now - start_time
                paused_total = self.current_session.get('total_paused_duration', timedelta(0))
                # If paused, include current paused span in paused_total for display
                if self.current_session.get('paused') and self.current_session.get('paused_start'):
                    paused_total += (now - self.current_session['paused_start'])
                active_duration = total_duration - paused_total
                if active_duration.total_seconds() < 0:
                    active_duration = timedelta(0)
                effective_elapsed_seconds = int(active_duration.total_seconds())
                return {
                    'id': self.current_session['id'],
                    'project': self.current_session['project'],
                    'goal': self.current_session['goal'],
                    'type': self.current_session['type'],
                    'start_time': start_time.strftime('%H:%M:%S'),
                    'duration_minutes': round(active_duration.total_seconds() / 60, 1),
                    'start_epoch': int(start_time.timestamp()),
                    'paused': bool(self.current_session.get('paused', False)),
                    'effective_elapsed': effective_elapsed_seconds,
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
                start_str = self._fmt_dt(start_time) if isinstance(start_time, datetime) else str(start_time)
                end_str = self._fmt_dt(end_time) if isinstance(end_time, datetime) else ''
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
            # Read all rows as dicts
            with open(self.csv_file, 'r', newline='', encoding='utf-8') as f:
                dict_reader = csv.DictReader(f)
                fieldnames = dict_reader.fieldnames or [
                    'session_id', 'start_time', 'end_time', 'duration_minutes', 
                    'project', 'goal', 'session_type', 'status', 'auto_closed'
                ]
                rows = list(dict_reader)

            # Update the matching row by session_id (trimmed)
            target_id = str(session_id).strip()
            iso_end = self._fmt_dt(end_time)
            updated = False
            for row in rows:
                if str(row.get('session_id', '')).strip() == target_id:
                    row['end_time'] = iso_end
                    row['duration_minutes'] = str(round(duration_minutes, 2))
                    row['status'] = status
                    # Store auto_closed as literal True/False (not stringified boolean text accidentally)
                    row['auto_closed'] = True if auto_closed else False
                    updated = True
                    break

            # Write back to file via DictWriter to preserve headers and order
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                # Ensure auto_closed is written as a boolean-compatible value
                for r in rows:
                    # Normalize types
                    if isinstance(r.get('duration_minutes'), float):
                        r['duration_minutes'] = str(round(r['duration_minutes'], 2))
                    # Ensure auto_closed is either True/False or 'True'/'False'
                    ac = r.get('auto_closed')
                    if isinstance(ac, str):
                        r['auto_closed'] = True if ac.lower() == 'true' else False
                    writer.writerow(r)

            if not updated:
                print(f"Warning: session_id not found for update: {session_id}")
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
        """Screen lock monitoring disabled (no-op)"""
        return
    
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
