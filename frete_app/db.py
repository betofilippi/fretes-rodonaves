from sqlmodel import create_engine, Session
from typing import Generator
import os

# SQLite para começar - trocar por PostgreSQL quando necessário
# Para PostgreSQL: "postgresql://user:password@localhost/dbname"
# Use environment variable if available (for production)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///frete.db")

# Create data directory if using SQLite and it doesn't exist
if "sqlite" in DATABASE_URL:
    db_path = DATABASE_URL.split("///")[1] if "///" in DATABASE_URL else DATABASE_URL.split("//")[1]
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    echo=False,  # Alterar para True para debug SQL
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)


def get_session() -> Generator[Session, None, None]:
    """Dependência para obter sessão do banco de dados"""
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    """Cria tabelas no banco de dados"""
    try:
        from .models import SQLModel
        # Import extended models to register them with SQLModel.metadata
        from .models_extended import (
            Estado, FilialRodonaves, CidadeRodonaves,
            TaxaEspecial, CEPEspecial, TabelaTarifaCompleta,
            HistoricoImportacao
        )
    except ImportError:
        from models import SQLModel
        from models_extended import (
            Estado, FilialRodonaves, CidadeRodonaves,
            TaxaEspecial, CEPEspecial, TabelaTarifaCompleta,
            HistoricoImportacao
        )
    SQLModel.metadata.create_all(engine)