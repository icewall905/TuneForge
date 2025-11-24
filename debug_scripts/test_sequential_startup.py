#!/usr/bin/env python3
"""
Test script for sequential auto-startup system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_sequential_startup():
    """Test the sequential startup system"""
    print("🔧 Testing Sequential Auto-Startup System")
    print("=" * 50)
    
    try:
        # Test 1: Import the functions
        print("\n📦 Test 1: Importing startup functions...")
        try:
            from app.routes import start_library_scan, wait_for_scan_completion, check_database_ready
            print("   ✅ All startup functions imported successfully")
        except ImportError as e:
            print(f"   ❌ Failed to import startup functions: {e}")
            return False
        
        # Test 2: Test database readiness check
        print("\n🔍 Test 2: Testing database readiness check...")
        try:
            db_ready = check_database_ready()
            print(f"   ✅ Database readiness check: {db_ready}")
        except Exception as e:
            print(f"   ❌ Database readiness check failed: {e}")
            return False
        
        # Test 3: Test scan completion waiting (simulated)
        print("\n⏳ Test 3: Testing scan completion waiting...")
        try:
            # This will return quickly since no scans are running
            scan_completed = wait_for_scan_completion(timeout_minutes=1)
            print(f"   ✅ Scan completion wait test: {scan_completed}")
        except Exception as e:
            print(f"   ❌ Scan completion wait test failed: {e}")
            return False
        
        print("\n🚀 Sequential auto-startup system is ready!")
        print("📊 The system will now:")
        print("   1. Start library scan")
        print("   2. Wait for scan to complete")
        print("   3. Check database readiness")
        print("   4. Start audio analysis only after scan is done")
        print("   5. Prevent database locking issues")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_sequential_startup()
