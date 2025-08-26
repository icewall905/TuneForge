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
                            result = start_library_scan()
                            if result:
                                print("[Startup] Library scan started successfully")
                            else:
                                print("[Startup] Library scan failed to start")
                        
                        if enable_auto_analysis:
                            print("[Startup] Starting automatic audio analysis...")
                            # Import and start analysis here
                            from .routes import start_audio_analysis
                            result = start_audio_analysis()
                            if result:
                                print("[Startup] Audio analysis started successfully")
                            else:
                                print("[Startup] Audio analysis failed to start")
                            
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
