import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file if it exists

class Config:
    DEBUG = True  # Enable debug mode for development
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:password@localhost:5432/hvac_db' # Replace with your DB details
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Disable modification tracking for performance
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key_here' # Replace with a strong secret key in production