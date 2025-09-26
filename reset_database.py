#!/usr/bin/env python3
"""
Database Reset Script
Properly resets the database with updated schema
"""

import sys
from pathlib import Path
import os
import sqlite3
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def reset_database():
    """Reset database with proper schema"""

    db_files = [
        "frete.db",
        "frete_system.db"
    ]

    print("Resetting database...")

    # Step 1: Try to close all connections and delete files
    for db_file in db_files:
        if os.path.exists(db_file):
            try:
                # Try to connect and close properly
                conn = sqlite3.connect(db_file)
                conn.close()
                os.remove(db_file)
                print(f"Deleted {db_file}")
            except Exception as e:
                print(f"Could not delete {db_file}: {e}")

    # Step 2: Create new database with updated schema
    print("Creating new database with updated schema...")

    try:
        from frete_app.db import create_db_and_tables
        create_db_and_tables()
        print("Database created successfully with new schema!")

        # Step 3: Test the new schema
        print("Testing new schema...")
        from sqlmodel import Session, select
        from frete_app.db import engine
        from frete_app.models import VersaoTabela, ParametrosGerais

        with Session(engine) as session:
            # Test creating a version record
            test_version = VersaoTabela(
                nome="Test Version",
                descricao="Schema test",
                ativa=True,
                data_importacao=datetime.now()
            )
            session.add(test_version)
            session.commit()
            session.refresh(test_version)

            print(f"✓ Successfully created test version with ID: {test_version.id}")

            # Test creating parameters
            test_params = ParametrosGerais(
                versao_id=test_version.id,
                importado_em=datetime.now()
            )
            session.add(test_params)
            session.commit()

            print("✓ Successfully created test parameters")

            # Clean up test records
            session.delete(test_params)
            session.delete(test_version)
            session.commit()

            print("✓ Schema validation completed successfully!")

    except Exception as e:
        print(f"ERROR: Failed to create database: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    if reset_database():
        print("SUCCESS: Database reset completed!")
        exit(0)
    else:
        print("FAILED: Database reset failed!")
        exit(1)