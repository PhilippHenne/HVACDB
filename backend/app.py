      
from flask import Flask
from .config import Config
from .database import db
from .api import api_bp

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app) # Initialize SQLAlchemy with the Flask app

app.register_blueprint(api_bp, url_prefix='/api') # Register API blueprint

@app.route('/')
def index():
    return "HVAC Database Backend is running. Access the frontend in the 'frontend' directory."

if __name__ == '__main__':
    with app.app_context(): # Create application context for database operations outside request context
        db.create_all() # Create database tables if they don't exist
    app.run(debug=True) # Run Flask development server