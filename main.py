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

def log_file_path(vertical):
    safe_name = vertical.replace('/', '_').replace(' ', '_')
    return os.path.join(LOGGER_DIR, f"{safe_name}.txt")

def write_log(vertical, line):
    ensure_logger_dir()
    path = log_file_path(vertical)
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
    import sys
    import termios
    import tty
    import select
    seconds = 0
    start_line = f"{start_time} [ {vertical} ] : Start logging Goal: {goal}"
    write_log(vertical, start_line)
    print(f"\rLogOn: Task [ {vertical} ] 00:00:00\033[K", end='', flush=True)
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            mins, secs = divmod(seconds, 60)
            hours, mins = divmod(mins, 60)
            time_str = f"{hours:02}:{mins:02}:{secs:02}"
            print(f"\rLogOn: Task [ {vertical} ] {time_str}\033[K", end='', flush=True)
            # Log in progress every 5 seconds
            if seconds != 0 and seconds % 5 == 0:
                write_log(vertical, f"[LogOn - {time_str}] in progress")
            # Non-blocking key check
            dr, _, _ = select.select([sys.stdin], [], [], 1)
            if dr:
                ch = sys.stdin.read(1)
                if ch == 'q':
                    write_log(vertical, f"[LogOn - {time_str}] closed")
                    print(f"\n[cyan]Session closed at {time_str}.[/]")
                    break
                elif ch == 'h':
                    print("\n[cyan]Hold: Add a note (type 'exit' on a new line to finish):[/]")
                    note = multiline_input('>')
                    write_log(vertical, f"[LogOn - {time_str}] NOTE: {note}")
            seconds += 1
    except KeyboardInterrupt:
        mins, secs = divmod(seconds, 60)
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
