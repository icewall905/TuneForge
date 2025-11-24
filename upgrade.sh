#!/bin/bash
#
# TuneForge Upgrade Script
# This script safely upgrades TuneForge to the latest version
#

set -e  # Exit on any error

# Configuration
TUNEFORGE_DIR="/opt/tuneforge"
BACKUP_DIR="/opt/tuneforge/backups"
SERVICE_NAME="tuneforge"
REPO_URL="https://github.com/icewall905/TuneForge.git"
TEMP_DIR="/tmp/tuneforge-upgrade-$$"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
   exit 1
fi

# Function to create backup
create_backup() {
    log "Creating backup of current installation..."
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    # Create timestamped backup
    BACKUP_NAME="tuneforge-backup-$(date +%Y%m%d-%H%M%S)"
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
    
    # Stop the service
    log "Stopping TuneForge service..."
    systemctl stop "$SERVICE_NAME" || true
    
    # Create backup
    log "Creating backup at $BACKUP_PATH..."
    mkdir -p "$BACKUP_PATH"
    rsync -av --exclude='backups' --exclude='venv' "$TUNEFORGE_DIR/" "$BACKUP_PATH/"
    
    # Remove the venv from backup to save space (we'll recreate it)
    rm -rf "$BACKUP_PATH/venv"
    
    success "Backup created: $BACKUP_PATH"
    echo "$BACKUP_PATH" > "$TUNEFORGE_DIR/.last_backup"
}

# Function to restore from backup
restore_backup() {
    local backup_path="$1"
    if [[ -d "$backup_path" ]]; then
        error "Restoration from backup not implemented in this script"
        error "Manual restoration required from: $backup_path"
        return 1
    else
        error "Backup not found: $backup_path"
        return 1
    fi
}

# Function to check service status
check_service() {
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        return 0
    else
        return 1
    fi
}

# Function to start service
start_service() {
    log "Starting TuneForge service..."
    systemctl start "$SERVICE_NAME"
    sleep 5
    
    if check_service; then
        success "Service started successfully"
        return 0
    else
        error "Failed to start service"
        return 1
    fi
}

# Function to stop service
stop_service() {
    log "Stopping TuneForge service..."
    systemctl stop "$SERVICE_NAME" || true
    sleep 2
}

# Main upgrade function
upgrade() {
    log "Starting TuneForge upgrade process..."
    
    # Check if TuneForge is installed
    if [[ ! -d "$TUNEFORGE_DIR" ]]; then
        error "TuneForge not found at $TUNEFORGE_DIR"
        error "Please install TuneForge first"
        exit 1
    fi
    
    # Create backup
    create_backup
    
    # Create temporary directory for new version
    log "Downloading latest version..."
    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"
    
    # Clone the repository
    git clone "$REPO_URL" .
    
    # Get current and new versions
    CURRENT_VERSION=$(cd "$TUNEFORGE_DIR" && git rev-parse HEAD 2>/dev/null || echo "unknown")
    NEW_VERSION=$(git rev-parse HEAD)
    
    log "Current version: $CURRENT_VERSION"
    log "New version: $NEW_VERSION"
    
    if [[ "$CURRENT_VERSION" == "$NEW_VERSION" ]]; then
        warning "Already at latest version"
        rm -rf "$TEMP_DIR"
        start_service
        exit 0
    fi
    
    # Stop the service
    stop_service
    
    # Backup current config and data
    log "Backing up configuration and data..."
    cp "$TUNEFORGE_DIR/config.ini" "$TEMP_DIR/" 2>/dev/null || true
    cp -r "$TUNEFORGE_DIR/db" "$TEMP_DIR/" 2>/dev/null || true
    cp -r "$TUNEFORGE_DIR/logs" "$TEMP_DIR/" 2>/dev/null || true
    
    # Remove old installation (except venv and backups)
    log "Removing old installation..."
    cd "$TUNEFORGE_DIR"
    find . -maxdepth 1 -not -name 'venv' -not -name 'backups' -not -name '.last_backup' -exec rm -rf {} + 2>/dev/null || true
    
    # Copy new files
    log "Installing new version..."
    cp -r "$TEMP_DIR"/* "$TUNEFORGE_DIR/"
    
    # Restore config and data
    log "Restoring configuration and data..."
    cp "$TEMP_DIR/config.ini" "$TUNEFORGE_DIR/" 2>/dev/null || true
    cp -r "$TEMP_DIR/db" "$TUNEFORGE_DIR/" 2>/dev/null || true
    cp -r "$TEMP_DIR/logs" "$TUNEFORGE_DIR/" 2>/dev/null || true
    
    # Set proper ownership
    chown -R tuneforge:tuneforge "$TUNEFORGE_DIR"
    
    # Update dependencies
    log "Updating Python dependencies..."
    cd "$TUNEFORGE_DIR"
    sudo -u tuneforge venv/bin/pip install --upgrade pip
    sudo -u tuneforge venv/bin/pip install -r requirements.txt
    
    # Clean up temporary directory
    rm -rf "$TEMP_DIR"
    
    # Start the service
    if start_service; then
        success "Upgrade completed successfully!"
        log "TuneForge is now running at http://localhost:5395"
        
        # Show service status
        systemctl status "$SERVICE_NAME" --no-pager
    else
        error "Upgrade failed - service could not start"
        error "Check logs with: journalctl -u $SERVICE_NAME -f"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  upgrade     Upgrade to latest version (default)"
    echo "  status      Show service status"
    echo "  restart     Restart the service"
    echo "  stop        Stop the service"
    echo "  start       Start the service"
    echo "  logs        Show service logs"
    echo "  backup      Create a backup"
    echo "  help        Show this help message"
    echo ""
}

# Main script logic
case "${1:-upgrade}" in
    upgrade)
        upgrade
        ;;
    status)
        systemctl status "$SERVICE_NAME" --no-pager
        ;;
    restart)
        log "Restarting TuneForge service..."
        systemctl restart "$SERVICE_NAME"
        success "Service restarted"
        ;;
    stop)
        stop_service
        success "Service stopped"
        ;;
    start)
        start_service
        ;;
    logs)
        journalctl -u "$SERVICE_NAME" -f
        ;;
    backup)
        create_backup
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        error "Unknown option: $1"
        show_usage
        exit 1
        ;;
esac