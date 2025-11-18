import os
import sys
import json
import time
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich.text import Text
import termios
import tty
import select

VERTICALS_FILE = 'verticals.json'
LOGGER_DIR = 'logger_data'
AUTO_END_SECONDS = 60*60  # 20 minutes

console = Console()

# Ensure logger_data directory exists
def ensure_logger_dir():
    Path(LOGGER_DIR).mkdir(exist_ok=True)

def load_verticals():
    if not os.path.exists(VERTICALS_FILE):
        with open(VERTICALS_FILE, 'w') as f:
            json.dump(["Project AI Data Agent"], f)
    with open(VERTICALS_FILE, 'r') as f:
        return json.load(f)

def save_verticals(verticals):
    with open(VERTICALS_FILE, 'w') as f:
        json.dump(verticals, f, indent=2)

def add_vertical(name):
    verticals = load_verticals()
    if name not in verticals:
        verticals.append(name)
        save_verticals(verticals)
        console.print(f"[green]Vertical added:[/] {name}")
    else:
        console.print(f"[yellow]Vertical already exists:[/] {name}")

def select_vertical(verticals):
    try:
        proc = subprocess.Popen(
            ['fzf', '--height', '40%', '--border', '--prompt=Select vertical: '],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )
        out, _ = proc.communicate(input='\n'.join(verticals).encode())
        return out.decode().strip()
    except FileNotFoundError:
        console.print("[red]fzf not found. Please install fzf as per README.md.")
        sys.exit(1)

def multiline_input(prompt):
    console.print(prompt + " (type 'exit' on a new line to finish):")
    lines = []
    while True:
        line = input()
        if line.strip().lower() == 'exit':
            break
        lines.append(line)
    return '\n'.join(lines)

def beep():
    print('\a', end='', flush=True)

def play_mp3(path):
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        # Wait for the music to finish
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        pygame.mixer.quit()
    except Exception as e:
        print(f"[ERROR] Could not play mp3: {e}")

def log_file_path(vertical):
    safe_name = vertical.replace('/', '_').replace(' ', '_')
    return os.path.join(LOGGER_DIR, f"{safe_name}.txt")

def write_log(vertical, line):
    ensure_logger_dir()
    path = log_file_path(vertical)
    # If 'in progress', replace previous 'in progress' line for this vertical
    if 'in progress' in line:
        if os.path.exists(path):
            with open(path, 'r') as f:
                lines = f.readlines()
            # Remove previous 'in progress' lines
            lines = [l for l in lines if 'in progress' not in l]
        else:
            lines = []
        lines.append(line + '\n')
        with open(path, 'w') as f:
            f.writelines(lines)
    else:
        with open(path, 'a') as f:
            f.write(line + '\n')

def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def timer_loop(vertical, goal, start_time):
    start_line = f"{start_time} [ {vertical} ] : Start logging Goal: {goal}"
    write_log(vertical, start_line)
    print(f"\rLogOn: Task [ {vertical} ] 00:00:00\033[K", end='', flush=True)
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    start_ts = time.time()
    last_logged_second = -1
    try:
        tty.setcbreak(fd)
        while True:
            elapsed = int(time.time() - start_ts)
            if elapsed != last_logged_second:
                mins, secs = divmod(elapsed, 60)
                hours, mins = divmod(mins, 60)
                time_str = f"{hours:02}:{mins:02}:{secs:02}"
                print(f"\rLogOn: Task [ {vertical} ] {time_str}\033[K", end='', flush=True)
                # Log in progress every 5 seconds
                if elapsed != 0 and elapsed % 5 == 0:
                    write_log(vertical, f"[LogOn - {time_str}] in progress")
                # Auto end after 20 minutes
                if elapsed >= AUTO_END_SECONDS:
                    write_log(vertical, f"[LogOn - {time_str}] auto-closed after 60 minutes")
                    print(f"\n[cyan]Session auto-closed at {time_str} (60 minutes reached).[/]")
                    play_mp3("/home/ajay-dev/Documents/HangOn/LogOn/beep.mp3")
                    break
                last_logged_second = elapsed
            # Non-blocking key check
            dr, _, _ = select.select([sys.stdin], [], [], 0.1)
            if dr:
                ch = sys.stdin.read(1)
                mins, secs = divmod(elapsed, 60)
                hours, mins = divmod(mins, 60)
                time_str = f"{hours:02}:{mins:02}:{secs:02}"
                if ch == 'q':
                    write_log(vertical, f"[LogOn - {time_str}] closed")
                    print(f"\n[cyan]Session closed at {time_str}.[/]")
                    break
                elif ch == 'h':
                    print("\n[cyan]Hold: Add a note (type 'exit' on a new line to finish):[/]")
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)  # Restore normal mode
                    hold_start = time.time()
                    note = multiline_input('>')
                    hold_end = time.time()
                    tty.setcbreak(fd)  # Set back to cbreak mode
                    # Adjust start_ts forward by hold duration to pause timer
                    start_ts += (hold_end - hold_start)
                    write_log(vertical, f"[LogOn - {time_str}] NOTE: {note}")
    except KeyboardInterrupt:
        elapsed = int(time.time() - start_ts)
        mins, secs = divmod(elapsed, 60)
        hours, mins = divmod(mins, 60)
        time_str = f"{hours:02}:{mins:02}:{secs:02}"
        write_log(vertical, f"[LogOn - {time_str}] closed")
        print(f"\n[cyan]Timer interrupted. Session closed at {time_str}.[/]")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def main():
    ensure_logger_dir()
    if len(sys.argv) > 1 and sys.argv[1] == 'create' and sys.argv[2] == '-v':
        name = ' '.join(sys.argv[3:]).strip('"')
        add_vertical(name)
        return
    while True:
        verticals = load_verticals()
        vertical = select_vertical(verticals)
        if not vertical:
            console.print("[red]No vertical selected. Exiting.")
            break
        goal = multiline_input(f"LogOn: target of action now:-")
        start_time = datetime.now().strftime('%H:%M %a %d %b %Y')
        timer_loop(vertical, goal, start_time)
        # After timer, loop back to selection

if __name__ == '__main__':
    main()
