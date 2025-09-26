#!/bin/bash
# Start script for Railway

# Create data directory if it doesn't exist
mkdir -p /app/data

# Start the application
exec uvicorn frete_app.main:app --host 0.0.0.0 --port ${PORT:-8000}