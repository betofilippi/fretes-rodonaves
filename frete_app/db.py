from sqlmodel import create_engine, Session
from typing import Generator

# SQLite para começar - trocar por PostgreSQL quando necessário
# Para PostgreSQL: "postgresql://user:password@localhost/dbname"
DATABASE_URL = "sqlite:///frete.db"

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