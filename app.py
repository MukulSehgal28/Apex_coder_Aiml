from flask import Flask
from config import Config
from models import db, login_manager
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    with app.app_context():
        # Import routes here to avoid circular imports
        from routes import bp as main_bp
        app.register_blueprint(main_bp)
        
        # Create db tables if they don't exist
        db.create_all()
        
        # Ensure static/charts directory exists
        charts_dir = os.path.join(app.root_path, 'static', 'charts')
        if not os.path.exists(charts_dir):
            os.makedirs(charts_dir)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)


