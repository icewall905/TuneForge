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
            db_path = init_local_music_db()
            print(f"[Startup] Database initialized successfully at: {db_path}")
        except Exception as e:
            # Database initialization is critical - fail hard if it doesn't work
            print(f"[Startup] CRITICAL ERROR: Failed to initialize local music DB: {e}")
            import traceback
            traceback.print_exc()
            raise  # Re-raise to prevent app from starting with broken database

        # Check for auto-startup configuration
        try:
            from .routes import get_config_value
            enable_auto_scan = get_config_value('AUTO_STARTUP', 'EnableAutoScan', 'no').lower() in ('yes', 'true', '1')
            enable_auto_analysis = get_config_value('AUTO_STARTUP', 'EnableAutoAnalysis', 'no').lower() in ('yes', 'true', '1')
            startup_delay = int(get_config_value('AUTO_STARTUP', 'StartupDelaySeconds', '30'))
            
            if enable_auto_scan or enable_auto_analysis:
                print(f"[Startup] Auto-startup enabled - Scan: {enable_auto_scan}, Analysis: {enable_auto_analysis}, Delay: {startup_delay}s")
                
                # Start auto-startup in a background thread to avoid blocking app startup
                def auto_startup_worker():
                    time.sleep(startup_delay)  # Wait for app to fully initialize
                    
                    try:
                        if enable_auto_scan:
                            print("[Startup] Starting automatic library scan...")
                            # Import and start scan here
                            from .routes import start_library_scan
                            try:
                                result = start_library_scan()
                                if result:
                                    print("[Startup] Library scan started successfully")
                                    
                                    # Wait for library scan to complete before starting audio analysis
                                    if enable_auto_analysis:
                                        print("[Startup] Waiting for library scan to complete...")
                                        from .routes import wait_for_scan_completion
                                        
                                        # Wait up to 10 minutes for scan to complete
                                        scan_completed = wait_for_scan_completion(timeout_minutes=10)
                                        if scan_completed:
                                            print("[Startup] Library scan completed, starting audio analysis...")
                                            
                                            # Check if database is ready before proceeding
                                            from .routes import check_database_ready
                                            db_ready_attempts = 0
                                            max_db_attempts = 6  # Try for up to 30 seconds
                                            
                                            while not check_database_ready() and db_ready_attempts < max_db_attempts:
                                                print(f"[Startup] Database not ready, waiting 5 seconds... (attempt {db_ready_attempts + 1}/{max_db_attempts})")
                                                time.sleep(5)
                                                db_ready_attempts += 1
                                            
                                            if not check_database_ready():
                                                print("[Startup] Database still not ready after 30 seconds, skipping audio analysis")
                                                return
                                            
                                            print("[Startup] Database ready, starting audio analysis...")
                                            
                                            # Log database track counts for debugging
                                            from .routes import get_database_track_counts
                                            track_counts = get_database_track_counts()
                                            if 'error' not in track_counts:
                                                print(f"[Startup] Database track counts: {track_counts['total_tracks']} total, {track_counts['status_counts']}")
                                            else:
                                                print(f"[Startup] Error getting track counts: {track_counts['error']}")
                                            
                                            from .routes import start_audio_analysis
                                            try:
                                                result = start_audio_analysis()
                                                if result:
                                                    print("[Startup] Audio analysis started successfully")
                                                else:
                                                    print("[Startup] Audio analysis failed to start")
                                            except Exception as analysis_error:
                                                print(f"[Startup] Audio analysis error: {analysis_error}")
                                        else:
                                            print("[Startup] Library scan did not complete within timeout, skipping audio analysis")
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
                
                startup_thread = threading.Thread(target=auto_startup_worker, daemon=True)
                startup_thread.start()
                print(f"[Startup] Auto-startup thread started, will execute in {startup_delay} seconds")
                
        except Exception as e:
            print(f"[Startup] Warning: failed to check auto-startup configuration: {e}")
            import traceback
            traceback.print_exc()

    return app
