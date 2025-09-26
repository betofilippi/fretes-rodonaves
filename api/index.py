"""
Vercel entry point for FastAPI application
"""
import sys
import os

# Add the parent directory to the path so we can import frete_app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frete_app.main import app

# Export the FastAPI app for Vercel
handler = app