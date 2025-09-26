"""
Vercel Serverless Function Entry Point
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the FastAPI app
from frete_app.main import app

# Vercel serverless handler
def handler(request, context):
    """Vercel serverless function handler"""
    return app