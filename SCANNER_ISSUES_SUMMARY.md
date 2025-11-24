# TuneForge Scanner Issues Analysis

## 🔍 **Current Scanner Status**

### **Scanner is RUNNING** ✅
- **Progress**: Processing 80,100 out of 152,296 files (52.6% complete)
- **Status**: Actively scanning the NFS-mounted music directory
- **Database**: Currently empty (tables not created yet)

## 🚨 **Issues Identified**

### **1. Database Constraint Errors** ❌
**Error**: `UNIQUE constraint failed: tracks.file_path`

**Root Cause**: The scanner is trying to insert duplicate file paths into the database, but the database schema hasn't been properly initialized yet.

**Impact**: 
- Files are being processed but not saved to database
- Scanner continues running but data is lost
- No tracks are being stored

**Example Error**:
```
2025-10-15 06:17:49,420 - TuneForgeApp - ERROR - Error processing file /mnt/media/music/R.E.M/R.E.M. - Legendary FM Broadcasts - KCRW-FM Studio Acoustic Sessions 3rd April 1991/13 - Spooky (Live KCRW-FM Broadcast Remastered) (KCRW-FM Broadcast KCRW Studios, Santa Monica CA 3rd April 1991 Remastered).flac in batch: UNIQUE constraint failed: tracks.file_path
```

### **2. Mutagen Threading Warnings** ⚠️
**Warning**: `signal only works in main thread of the main interpreter`

**Root Cause**: The Mutagen library (used for reading audio metadata) is being called from a worker thread instead of the main thread.

**Impact**:
- Non-critical warnings
- Scanner continues working
- May cause some metadata to be missed

**Example Warning**:
```
2025-10-15 06:18:22,608 - TuneForgeApp - WARNING - Mutagen error reading /mnt/media/music/Various Artists/Various Artists - LHO_ DANCE_ELECTRONICA_TECHNO_HOUSE 80s-90s-2000s/060 - Bob Sinclair - World, Hold On.flac: signal only works in main thread of the main interpreter
```

## 📊 **Scanner Progress Details**

### **Current Statistics**
- **Total Files**: 152,296
- **Processed**: 80,100 (52.6%)
- **Remaining**: 72,196 files
- **Current Directory**: `/mnt/media/music/Various Artists/Various Artists - Lydbøger børn - Eventyr - fortællinger til børn -`

### **Processing Rate**
- **Files per second**: ~50-100 files/second
- **Estimated completion**: ~12-20 minutes remaining

## 🔧 **Recommended Fixes**

### **1. Fix Database Initialization** (CRITICAL)
The database needs to be properly initialized before scanning begins.

**Solution**:
```bash
# Stop the current scanner
sudo systemctl stop tuneforge

# Initialize the database schema
cd /opt/tuneforge
sudo -u tuneforge python3 -c "
from app import create_app
from app.database import init_db
app = create_app()
with app.app_context():
    init_db()
    print('Database initialized successfully')
"

# Restart TuneForge
sudo systemctl start tuneforge
```

### **2. Fix Mutagen Threading** (OPTIONAL)
The Mutagen warnings can be addressed by ensuring metadata reading happens in the main thread.

**Solution**: Modify the scanner to use a different approach for metadata extraction or handle the threading issue in the code.

### **3. Clear and Restart Scanner** (RECOMMENDED)
Since the database is empty and the scanner is already 52% complete, it's better to restart with a properly initialized database.

**Solution**:
```bash
# Stop TuneForge
sudo systemctl stop tuneforge

# Clear any partial data
sudo -u tuneforge rm -f /opt/tuneforge/db/tuneforge.db

# Initialize fresh database
cd /opt/tuneforge
sudo -u tuneforge python3 -c "
from app import create_app
from app.database import init_db
app = create_app()
with app.app_context():
    init_db()
    print('Fresh database initialized')
"

# Restart TuneForge
sudo systemctl start tuneforge

# Start a new scan
curl -X POST "http://localhost:5395/api/scan-music-folder" \
  -H "Content-Type: application/json" \
  -d '{"folder_path": "/mnt/media/music"}'
```

## 📈 **Current Performance**

### **Positive Aspects**
- ✅ Scanner is actively running
- ✅ NFS mount is working correctly
- ✅ Music files are accessible
- ✅ Processing rate is reasonable
- ✅ No critical crashes

### **Issues to Address**
- ❌ Database not initialized
- ❌ Data not being saved
- ⚠️ Threading warnings
- ⚠️ Duplicate file path errors

## 🎯 **Next Steps**

1. **Immediate**: Fix database initialization
2. **Short-term**: Restart scanner with proper database
3. **Long-term**: Address Mutagen threading issues
4. **Monitor**: Watch for any new errors during scanning

## 📝 **Technical Details**

### **Database Schema Issue**
The scanner expects a `tracks` table with a `file_path` column that has a UNIQUE constraint, but the table doesn't exist yet.

### **File Processing**
The scanner is successfully:
- Reading file metadata
- Processing audio files
- Handling various formats (FLAC, MP3)
- Accessing NFS-mounted files

### **Error Pattern**
The `UNIQUE constraint failed: tracks.file_path` error suggests the database schema is missing or the table structure is incorrect.

---

**Analysis completed**: October 15, 2025
**Scanner Status**: Running but not saving data
**Priority**: Fix database initialization immediately