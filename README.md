# LogOn: Terminal Work Logger

## Features
- Interactive vertical/project selection using fzf
- Multiline goal/task input
- Live timer with periodic prompts
- Per-vertical logging, auto-saved every minute
- Add new verticals via command
- Interrupt to re-select vertical
- Designed for Ubuntu/Linux

## Setup

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Install fzf (required)
Follow the official guide: [fzf Linux Packages](https://github.com/junegunn/fzf?tab=readme-ov-file#linux-packages)

#### Example for Ubuntu:
```bash
sudo apt-get install fzf
```

Or use the install script:
```bash
git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
~/.fzf/install
```

### 3. Auto-start on login
Create a `.desktop` file in `~/.config/autostart/`:

```
[Desktop Entry]
Type=Application
Exec=gnome-terminal -- bash -c 'python3 /home/ajay-dev/Documents/HangOn/LogOn/main.py'
Name=LogOn
```

## Usage
- On startup, select a vertical (project) via fzf
- Enter your current goal/task (multiline)
- Timer starts, logs are saved every minute
- Every 10 minutes, you are prompted to confirm or log progress
- Add new verticals: `LogOn: create -v "New Vertical"`

## Data
- Logs are saved in `logger_data/` as `<Vertical>.txt`
- Verticals are managed in `verticals.json`

## License
MIT
