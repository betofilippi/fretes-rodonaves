#!/bin/bash
# Start script for Railway

# Create data directory if it doesn't exist
mkdir -p /app/data

# Initialize database with all data
echo "[INFO] Initializing database..."
python initialize_database.py

# Check if initialization was successful
if [ $? -eq 0 ]; then
    echo "[OK] Database initialized successfully"
else
    echo "[WARNING] Database initialization had issues, continuing anyway..."
fi

# Start the application
echo "[INFO] Starting web server..."
exec uvicorn frete_app.main:app --host 0.0.0.0 --port ${PORT:-8000}