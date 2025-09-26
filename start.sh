#!/bin/bash
# Start script for Railway

# Create data directory if it doesn't exist
mkdir -p /app/data

# Initialize database with production script
echo "[INFO] Initializing database for production..."
python initialize_db_production.py

# Check if initialization was successful
if [ $? -eq 0 ]; then
    echo "[OK] Database initialized successfully"
else
    echo "[WARNING] Database initialization had issues, trying fallback..."
    # Try the simpler initialization as fallback
    python initialize_database.py
fi

# Start the application
echo "[INFO] Starting web server..."
exec uvicorn frete_app.main:app --host 0.0.0.0 --port ${PORT:-8000}