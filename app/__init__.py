import os
from flask import Flask
from flask_migrate import Migrate
from .models import db, HVACDevice
from .routes import main
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Register blueprints
    app.register_blueprint(main)
    
    # Create database tables if they don't exist
    with app.app_context():
        print(Config.SQLALCHEMY_DATABASE_URI)
        db.create_all()
    
    return app