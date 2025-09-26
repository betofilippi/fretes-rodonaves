#!/bin/bash
# Start script for Railway

# Create data directory if it doesn't exist
mkdir -p /app/data

# FORCE IMPORT ALL CITIES - NO FALLBACK!
echo "[INFO] IMPORTING ALL CITIES FROM EXCEL FILES..."
python force_import_all_cities.py

# Check if import was successful
if [ $? -eq 0 ]; then
    echo "[OK] ALL CITIES IMPORTED SUCCESSFULLY"
else
    echo "[ERROR] CITY IMPORT FAILED - TRYING BACKUP..."
    # Try the production initialization as backup
    python initialize_db_production.py
fi

# Initialize other data (products, states, etc)
echo "[INFO] Initializing remaining database data..."
python initialize_database.py

# Start the application
echo "[INFO] Starting web server..."
exec uvicorn frete_app.main:app --host 0.0.0.0 --port ${PORT:-8000}