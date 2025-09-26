from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

class Produto(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str  # CIF, FOB, EXW, etc.
    nome: str
    fator_ajuste: float = 1.0  # Fator de ajuste do preço
    taxa_adicional: float = 0.0  # Taxa adicional fixa
    ativo: bool = Field(default=True)
    criado_em: datetime = Field(default_factory=datetime.utcnow)

class VersaoTabela(SQLModel, table=True):
    __tablename__ = "versaotabela"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    descricao: str
    vigente_desde: datetime = Field(default_factory=datetime.utcnow)
    arquivo_pdf: Optional[str] = None
    ativa: bool = Field(default=True)
    data_importacao: datetime = Field(default_factory=datetime.utcnow)

class ParametrosGerais(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    versao_id: int = Field(foreign_key="versaotabela.id")
    cubagem_kg_por_m3: float = 300.0
    fvalor_percent_padrao: float = 0.005
    fvalor_min: float = 4.78
    gris_percent_ate_10k: float = 0.001
    gris_percent_acima_10k: float = 0.0023
    gris_min: float = 1.10
    pedagio_por_100kg: float = 3.80
    icms_percent: float = 0.12
    importado_em: datetime = Field(default_factory=datetime.utcnow)

class Destino(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    uf: str
    cidade: str
    categoria: str

class TarifaPeso(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    versao_id: int = Field(foreign_key="versaotabela.id")
    categoria: str
    ate_10: float
    ate_20: float
    ate_40: float
    ate_60: float
    ate_100: float
    excedente_por_kg: float

class CorredorKM(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    versao_id: int = Field(foreign_key="versaotabela.id")
    codigo: str
    km: float
    fator_multiplicador: float
    pedagio_pracas: int = 0
    fvalor_percent_override: Optional[float] = None

class MapDestinoCorredor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    destino_id: int = Field(foreign_key="destino.id")
    corredor_id: int = Field(foreign_key="corredorkm.id")