# LogOn Streamlit Auto-Start Service Setup

This guide will help you set up an auto-start service for your LogOn Streamlit dashboard.

## Files Created

1. **`logon.service`** - Systemd service file
2. **`start_logon.sh`** - Startup script with virtual environment handling
3. **`SERVICE_SETUP.md`** - This setup guide

## Installation Steps

### 1. Copy the service file to systemd directory
```bash
sudo cp logon.service /etc/systemd/system/
```

### 2. Reload systemd to recognize the new service
```bash
sudo systemctl daemon-reload
```

### 3. Enable the service to start on boot
```bash
sudo systemctl enable logon.service
```

### 4. Start the service
```bash
sudo systemctl start logon.service
```

## Service Management Commands

### Check service status
```bash
sudo systemctl status logon.service
```

### View service logs
```bash
sudo journalctl -u logon.service -f
```

### Stop the service
```bash
sudo systemctl stop logon.service
```

### Restart the service
```bash
sudo systemctl restart logon.service
```

### Disable auto-start (if needed)
```bash
sudo systemctl disable logon.service
```

## Accessing the Dashboard

Once the service is running, you can access your LogOn dashboard at:
- **Local access**: http://localhost:8501
- **Network access**: http://YOUR_SERVER_IP:8501

## Configuration Notes

- The service runs on port 8501
- It's configured to listen on all interfaces (0.0.0.0)
- The service will automatically restart if it crashes
- Logs are sent to systemd journal
- The service runs under your user account (`ajay-dev`)

## Troubleshooting

### If the service fails to start:
1. Check the logs: `sudo journalctl -u logon.service -f`
2. Verify the virtual environment exists: `ls -la /home/ajay-dev/Documents/HangOn/LogOn/venv/`
3. Check file permissions: `ls -la /home/ajay-dev/Documents/HangOn/LogOn/start_logon.sh`

### If you need to modify the service:
1. Edit the service file: `sudo nano /etc/systemd/system/logon.service`
2. Reload systemd: `sudo systemctl daemon-reload`
3. Restart the service: `sudo systemctl restart logon.service`

## Manual Testing

Before setting up the service, you can test the startup script manually:
```bash
cd /home/ajay-dev/Documents/HangOn/LogOn
./start_logon.sh
```

This will create the virtual environment, install dependencies, and start the Streamlit app.
