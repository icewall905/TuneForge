from flask import Flask
import os

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

    return app
