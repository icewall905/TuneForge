# TuneForge Service Installation

This document describes the TuneForge service installation on this server.

## Installation Summary

- **Installation Directory**: `/opt/tuneforge`
- **Service User**: `tuneforge`
- **Service Name**: `tuneforge`
- **Port**: `5395`
- **Web Interface**: `http://localhost:5395`

## Service Management

### Basic Commands

```bash
# Check service status
sudo systemctl status tuneforge

# Start the service
sudo systemctl start tuneforge

# Stop the service
sudo systemctl stop tuneforge

# Restart the service
sudo systemctl restart tuneforge

# Enable auto-start on boot
sudo systemctl enable tuneforge

# Disable auto-start on boot
sudo systemctl disable tuneforge
```

### View Logs

```bash
# View recent logs
sudo journalctl -u tuneforge

# Follow logs in real-time
sudo journalctl -u tuneforge -f

# View logs from today
sudo journalctl -u tuneforge --since today
```

## Upgrade Management

Use the built-in upgrade script for easy updates:

```bash
# Upgrade to latest version
sudo tuneforge-upgrade

# Or use the full path
sudo /opt/tuneforge/upgrade.sh

# Other upgrade script options
sudo tuneforge-upgrade status    # Show service status
sudo tuneforge-upgrade restart   # Restart service
sudo tuneforge-upgrade stop      # Stop service
sudo tuneforge-upgrade start     # Start service
sudo tuneforge-upgrade logs      # Show logs
sudo tuneforge-upgrade backup    # Create backup
sudo tuneforge-upgrade help      # Show help
```

## Configuration

The main configuration file is located at `/opt/tuneforge/config.ini`.

### Key Configuration Sections

1. **Database**: SQLite database settings
2. **Scanner**: Music library scanning settings
3. **Audio Analysis**: Audio feature extraction settings
4. **Auto Startup**: Automatic processes on startup
5. **Monitoring**: Health monitoring and recovery
6. **Logging**: Log file settings

### Important Directories

- **Application**: `/opt/tuneforge/`
- **Logs**: `/opt/tuneforge/logs/`
- **Database**: `/opt/tuneforge/db/`
- **Cache**: `/opt/tuneforge/.cache/`
- **Backups**: `/opt/tuneforge/backups/`

## Security Features

The service runs with the following security restrictions:

- Dedicated user account (`tuneforge`)
- No new privileges allowed
- Private temporary directory
- Limited filesystem access
- Resource limits (2GB memory max)
- Process isolation

## Troubleshooting

### Service Won't Start

1. Check service status: `sudo systemctl status tuneforge`
2. View logs: `sudo journalctl -u tuneforge -n 50`
3. Check file permissions: `ls -la /opt/tuneforge/`
4. Verify Python environment: `sudo -u tuneforge /opt/tuneforge/venv/bin/python --version`

### Permission Issues

```bash
# Fix ownership
sudo chown -R tuneforge:tuneforge /opt/tuneforge

# Fix cache directory
sudo mkdir -p /opt/tuneforge/.cache/art
sudo chown -R tuneforge:tuneforge /opt/tuneforge/.cache
```

### Port Already in Use

```bash
# Check what's using port 5395
sudo netstat -tlnp | grep 5395
sudo lsof -i :5395

# Kill process if needed
sudo kill -9 <PID>
```

### Database Issues

```bash
# Check database file
ls -la /opt/tuneforge/db/

# Backup database before troubleshooting
sudo cp /opt/tuneforge/db/local_music.db /opt/tuneforge/db/local_music.db.backup
```

## Performance Tuning

### Gunicorn Configuration

The service uses Gunicorn with the following settings:
- **Workers**: 2
- **Timeout**: 300 seconds
- **Max Requests**: 1000 per worker
- **Worker Class**: sync

To modify these settings, edit `/etc/systemd/system/tuneforge.service` and restart the service.

### Resource Limits

- **Memory Limit**: 2GB
- **File Descriptors**: 65536
- **CPU**: No specific limit

## Backup and Recovery

### Automatic Backups

The upgrade script automatically creates backups before upgrading:
- Location: `/opt/tuneforge/backups/`
- Format: `tuneforge-backup-YYYYMMDD-HHMMSS`

### Manual Backup

```bash
# Create manual backup
sudo tuneforge-upgrade backup

# Or manually
sudo systemctl stop tuneforge
sudo cp -r /opt/tuneforge /opt/tuneforge-backup-$(date +%Y%m%d-%H%M%S)
sudo systemctl start tuneforge
```

## Monitoring

The service includes built-in monitoring features:
- Health checks
- Stall detection
- Auto-recovery
- Progress tracking

Access monitoring through the web interface at `http://localhost:5395`.

## Support

For issues and support:
1. Check the logs first
2. Review this documentation
3. Check the original TuneForge repository: https://github.com/icewall905/TuneForge
4. Review the service configuration in `/etc/systemd/system/tuneforge.service`