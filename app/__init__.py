from flask import Flask
import os
import threading
import time

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    # Configurations (can be moved to a config.py file)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_change_in_production')
    app.config['OLLAMA_URL'] = 'http://localhost:11434'
    app.config['OLLAMA_MODEL'] = 'llama3'
    # Add other default configurations from your original script

    with app.app_context():
        from . import routes
        app.register_blueprint(routes.main_bp)

        # Ensure the local music database (tracks table) exists at startup
        try:
            from .routes import init_local_music_db
            init_local_music_db()
        except Exception as e:
            # Avoid hard failure at startup; routes that need DB will surface errors
            print(f"[Startup] Warning: failed to initialize local music DB: {e}")

        # Check for auto-startup configuration
        try:
            from .routes import get_config_value
            enable_auto_scan = get_config_value('AUTO_STARTUP', 'EnableAutoScan', 'no').lower() in ('yes', 'true', '1')
            enable_auto_analysis = get_config_value('AUTO_STARTUP', 'EnableAutoAnalysis', 'no').lower() in ('yes', 'true', '1')
            startup_delay = int(get_config_value('AUTO_STARTUP', 'StartupDelaySeconds', '30'))
            
            
            # Start auto-startup in a background thread to avoid blocking app startup
            def auto_startup_worker():
                # --- File Lock Mechanism for Gunicorn Workers ---
                # Ensure only ONE worker executes the startup tasks
                lock_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'startup.lock')
                
                # Check if lock exists and is valid (not stale)
                if os.path.exists(lock_file):
                    try:
                        with open(lock_file, 'r') as f:
                            pid, timestamp = f.read().split(',')
                        
                        # Check if process is still running
                        try:
                            os.kill(int(pid), 0)
                            # Process exists, so lock is valid. We are a secondary worker.
                            print(f"[Startup] Another worker (PID {pid}) is handling startup tasks. Skipping.")
                            return
                        except OSError:
                            # Process doesn't exist, lock is stale. We can take over.
                            print(f"[Startup] Found stale lock from PID {pid}. Taking over.")
                    except Exception:
                        # Lock file corrupted or unreadable, try to take over
                        print("[Startup] Found invalid lock file. Taking over.")
                
                # Create/Update lock file with our PID
                try:
                    with open(lock_file, 'w') as f:
                        f.write(f"{os.getpid()},{time.time()}")
                except Exception as e:
                    print(f"[Startup] Failed to create lock file: {e}. Proceeding anyway.")

                # Ensure lock file is removed on exit (best effort)
                import atexit
                def remove_lock():
                    try:
                        if os.path.exists(lock_file):
                            with open(lock_file, 'r') as f:
                                pid, _ = f.read().split(',')
                            if int(pid) == os.getpid():
                                os.remove(lock_file)
                    except Exception:
                        pass
                atexit.register(remove_lock)

                time.sleep(startup_delay)  # Wait for app to fully initialize
                
                # 1. Configured Auto-Startup
                try:
                    if enable_auto_scan:
                        print("[Startup] Starting automatic library scan...")
                        # Import and start scan here
                        from .routes import start_library_scan
                        try:
                            result = start_library_scan()
                            if result:
                                print("[Startup] Library scan started successfully")
                                
                                # Don't wait for scan - start audio analysis in background thread
                                # This allows the service to remain responsive during scans
                                if enable_auto_analysis:
                                    print("[Startup] Starting audio analysis in background (not waiting for scan)...")
                                    
                                    def start_analysis_after_delay():
                                        """Start audio analysis after a delay, checking for scan completion"""
                                        import time
                                        from .routes import is_database_busy, start_audio_analysis
                                        
                                        # Wait a bit for scan to make progress
                                        time.sleep(60)  # Wait 1 minute
                                        
                                        # Try to start analysis, but don't block if scan is still running
                                        max_attempts = 10
                                        for attempt in range(max_attempts):
                                            if not is_database_busy():
                                                print("[Startup] Database available, starting audio analysis...")
                                                start_audio_analysis()
                                                break
                                            else:
                                                print(f"[Startup] Database busy with scan, waiting... (attempt {attempt+1}/{max_attempts})")
                                                time.sleep(30)  # Wait 30 seconds between attempts
                                    
                                    # Start analysis in background thread - non-blocking
                                    analysis_thread = threading.Thread(target=start_analysis_after_delay, daemon=True)
                                    analysis_thread.start()
                                    
                                    # Continue startup without blocking
                                    print("[Startup] Audio analysis will start automatically when database is available")
                                else:
                                    print("[Startup] Audio analysis disabled, skipping")
                            else:
                                print("[Startup] Library scan failed to start")
                        except Exception as scan_error:
                            print(f"[Startup] Library scan error: {scan_error}")
                    elif enable_auto_analysis:
                        # If only audio analysis is enabled (no scan), start it directly
                        print("[Startup] Starting automatic audio analysis (no scan)...")
                        from .routes import start_audio_analysis
                        try:
                            result = start_audio_analysis()
                            if result:
                                print("[Startup] Audio analysis started successfully")
                            else:
                                print("[Startup] Audio analysis failed to start")
                        except Exception as analysis_error:
                            print(f"[Startup] Audio analysis error: {analysis_error}")
                        
                except Exception as e:
                    print(f"[Startup] Error during auto-startup: {e}")
                    import traceback
                    traceback.print_exc()
            
                # 2. Resume Pending Analysis (Always check)
                # Check for pending audio analysis tasks and start recovery if needed
                # This ensures analysis resumes after a restart even if auto-startup is disabled
                try:
                    # Only check if we didn't just start it above
                    # A simple way is to check if auto-analysis was enabled and ran.
                    # But simpler: just check if recovery is already active.
                    
                    from .routes import get_auto_recovery
                    auto_recovery = get_auto_recovery()
                    
                    # If auto-recovery is already monitoring, we don't need to do anything
                    if auto_recovery and auto_recovery.get_status().get('monitoring_active'):
                        return

                    from .routes import check_database_ready, get_audio_analysis_service
                    if check_database_ready():
                        try:
                            service = get_audio_analysis_service()
                            progress = service.get_analysis_progress()
                        except Exception as svc_err:
                            print(f"[Startup] Could not get analysis service: {svc_err}")
                            return
                        
                        if progress['pending_tracks'] > 0 or progress['status_counts'].get('analyzing', 0) > 0:
                            print(f"[Startup] Found {progress['pending_tracks']} pending and {progress['status_counts'].get('analyzing', 0)} analyzing tracks.")
                            print("[Startup] Initializing auto-recovery to resume analysis...")
                            
                            if auto_recovery:
                                auto_recovery.start_monitoring()
                                print("[Startup] Auto-recovery monitoring started to resume analysis")
                except Exception as e:
                    print(f"[Startup] Warning: Failed to check for pending analysis: {e}")

            startup_thread = threading.Thread(target=auto_startup_worker, daemon=True)
            startup_thread.start()
            print(f"[Startup] Auto-startup thread started, will execute in {startup_delay} seconds")
                
        except Exception as e:
            print(f"[Startup] Warning: failed to check auto-startup configuration: {e}")
            import traceback
            traceback.print_exc()

    return app
