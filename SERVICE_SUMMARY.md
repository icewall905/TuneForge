# TuneForge Service Installation Summary

## ✅ Installation Complete

TuneForge has been successfully installed as a system service on this server.

## 📍 Installation Details

- **Service Name**: `tuneforge`
- **Installation Path**: `/opt/tuneforge`
- **Service User**: `tuneforge`
- **Web Interface**: `http://localhost:5395`
- **Port**: `5395`

## 🚀 Quick Start

### Service Management
```bash
# Check status
tuneforge status

# Start/stop/restart
sudo tuneforge start
sudo tuneforge stop
sudo tuneforge restart

# View logs
sudo tuneforge logs
```

### Upgrade Management
```bash
# Upgrade to latest version
sudo tuneforge-upgrade

# Create backup
sudo tuneforge backup
```

## 📁 Directory Structure

```
/opt/tuneforge/
├── app/                    # Flask application
├── templates/              # Web templates
├── static/                 # Static assets
├── logs/                   # Log files
├── db/                     # SQLite database
├── .cache/                 # Application cache
├── backups/                # Automatic backups
├── venv/                   # Python virtual environment
├── config.ini              # Configuration file
├── run_production.py       # Production runner
├── upgrade.sh              # Upgrade script
└── INSTALLATION.md         # Detailed documentation
```

## 🔧 Configuration

The main configuration file is at `/opt/tuneforge/config.ini`. Key sections:

- **Database**: SQLite settings
- **Scanner**: Music library scanning
- **Audio Analysis**: Feature extraction
- **Auto Startup**: Automatic processes
- **Monitoring**: Health monitoring

## 🔒 Security Features

- Dedicated service user (`tuneforge`)
- Process isolation
- Resource limits (2GB memory max)
- Limited filesystem access
- No privilege escalation

## 📊 Service Status

The service is currently **RUNNING** and accessible at:
- **Local**: http://localhost:5395
- **Network**: http://[server-ip]:5395

## 🛠️ Troubleshooting

### Common Commands
```bash
# Check service status
systemctl status tuneforge

# View recent logs
journalctl -u tuneforge -n 50

# Follow logs in real-time
journalctl -u tuneforge -f

# Restart service
systemctl restart tuneforge
```

### Log Locations
- **System Logs**: `journalctl -u tuneforge`
- **Application Logs**: `/opt/tuneforge/logs/`

## 📚 Documentation

- **Installation Guide**: `/opt/tuneforge/INSTALLATION.md`
- **Original Project**: https://github.com/icewall905/TuneForge
- **Service Config**: `/etc/systemd/system/tuneforge.service`

## 🎯 Next Steps

1. **Configure Music Library**: Edit `/opt/tuneforge/config.ini` to set your music library path
2. **Set up Ollama**: Ensure Ollama is running for AI features
3. **Access Web Interface**: Open http://localhost:5395 in your browser
4. **Configure Music Services**: Set up Navidrome/Plex integration if desired

## 📞 Support

For issues:
1. Check logs: `sudo tuneforge logs`
2. Review documentation: `/opt/tuneforge/INSTALLATION.md`
3. Check service status: `tuneforge status`
4. Restart if needed: `sudo tuneforge restart`

---

**Installation completed on**: $(date)
**TuneForge Version**: Latest from https://github.com/icewall905/TuneForge.git