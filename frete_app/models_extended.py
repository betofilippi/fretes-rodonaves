"""
Modelos estendidos para suportar cobertura completa de cidades Rodonaves
Baseado nos arquivos Excel oficiais da Rodonaves com 4,219 cidades
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime


class Estado(SQLModel, table=True):
    """Estado brasileiro com informações de cobertura"""
    __tablename__ = "estados"

    id: Optional[int] = Field(default=None, primary_key=True)
    sigla: str = Field(index=True, unique=True, max_length=2)
    nome: str
    regiao: str  # Sul, Sudeste, Centro-Oeste
    tem_cobertura: bool = True

    # Relacionamentos
    filiais: List["FilialRodonaves"] = Relationship(back_populates="estado")
    cidades: List["CidadeRodonaves"] = Relationship(back_populates="estado")


class FilialRodonaves(SQLModel, table=True):
    """Filiais/bases operacionais da Rodonaves"""
    __tablename__ = "filiais_rodonaves"

    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(index=True, unique=True)  # Ex: "SPO", "CWB", "POA"
    nome: str
    cidade: str
    estado_id: int = Field(foreign_key="estados.id")
    tipo: str  # "MATRIZ", "FILIAL", "BASE"
    ativa: bool = True

    # Relacionamentos
    estado: Estado = Relationship(back_populates="filiais")
    cidades_atendidas: List["CidadeRodonaves"] = Relationship(back_populates="filial_atendimento")


class CidadeRodonaves(SQLModel, table=True):
    """Todas as cidades atendidas pela Rodonaves com categorização completa"""
    __tablename__ = "cidades_rodonaves"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Identificação
    nome: str = Field(index=True)
    estado_id: int = Field(foreign_key="estados.id")
    filial_atendimento_id: int = Field(foreign_key="filiais_rodonaves.id")

    # Categorização para tarifas
    categoria_tarifa: str = Field(index=True)  # "CAPITAL", "INTERIOR_1", "INTERIOR_2", "FLUVIAL"
    zona_destino: Optional[str] = None  # Para agrupamento adicional

    # Distância e prazo
    distancia_km: Optional[float] = None  # Distância da filial de atendimento
    prazo_entrega_dias: Optional[int] = None  # Mantido para compatibilidade

    # Prazos específicos para CPF (pessoa física)
    prazo_cpf_min_dias: Optional[int] = None  # Prazo mínimo para entrega CPF
    prazo_cpf_max_dias: Optional[int] = None  # Prazo máximo para entrega CPF
    tipo_transporte: Optional[str] = None  # RODOVIARIO, FLUVIAL, AEREO

    # Flags especiais
    tem_restricao_entrega: bool = False  # Dias específicos, horários, etc
    tem_tda: bool = False  # Taxa Dificuldade Acesso
    tem_trt: bool = False  # Taxa Restrição Trânsito
    zona_risco: Optional[str] = None  # "BAIXO", "MEDIO", "ALTO"

    # Metadados
    ativo: bool = True
    observacoes: Optional[str] = None
    criado_em: datetime = Field(default_factory=datetime.now)
    atualizado_em: Optional[datetime] = None

    # Relacionamentos
    estado: Estado = Relationship(back_populates="cidades")
    filial_atendimento: FilialRodonaves = Relationship(back_populates="cidades_atendidas")
    taxas_especiais: List["TaxaEspecial"] = Relationship(back_populates="cidade")
    ceps_especiais: List["CEPEspecial"] = Relationship(back_populates="cidade")


class TaxaEspecial(SQLModel, table=True):
    """Taxas especiais (TDA/TRT) aplicadas a cidades específicas"""
    __tablename__ = "taxas_especiais"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Cidade e tipo
    cidade_id: int = Field(foreign_key="cidades_rodonaves.id", index=True)
    tipo_taxa: str  # "TDA", "TRT", "AMBAS"

    # Valores
    valor_tda: Optional[float] = None  # Valor fixo ou percentual
    tipo_tda: Optional[str] = None  # "FIXO", "PERCENTUAL"
    valor_trt: Optional[float] = None
    tipo_trt: Optional[str] = None  # "FIXO", "PERCENTUAL"

    # Regras de aplicação
    valor_minimo_nf: Optional[float] = None  # Aplica apenas se NF >= valor
    peso_minimo_kg: Optional[float] = None  # Aplica apenas se peso >= valor

    # Período de vigência
    valido_desde: datetime = Field(default_factory=datetime.now)
    valido_ate: Optional[datetime] = None

    # Detalhes
    descricao: Optional[str] = None
    justificativa: Optional[str] = None  # Ex: "Zona de risco", "Restrição municipal"

    # Relacionamentos
    cidade: CidadeRodonaves = Relationship(back_populates="taxas_especiais")


class CEPEspecial(SQLModel, table=True):
    """CEPs com regras ou taxas especiais diferentes da cidade"""
    __tablename__ = "ceps_especiais"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Identificação
    cep_inicio: str = Field(index=True)  # "01000000"
    cep_fim: str  # "01999999"
    cidade_id: int = Field(foreign_key="cidades_rodonaves.id")

    # Sobrescreve categoria da cidade
    categoria_tarifa_especial: Optional[str] = None

    # Taxas específicas do CEP
    tem_tda: bool = False
    tem_trt: bool = False
    valor_tda: Optional[float] = None
    valor_trt: Optional[float] = None

    # Restrições
    restricao_entrega: Optional[str] = None
    zona_risco: Optional[str] = None

    # Metadados
    ativo: bool = True
    motivo: Optional[str] = None

    # Relacionamentos
    cidade: CidadeRodonaves = Relationship(back_populates="ceps_especiais")


class TabelaTarifaCompleta(SQLModel, table=True):
    """Tabela de tarifas por categoria com todas as faixas de peso"""
    __tablename__ = "tabelas_tarifa_completa"

    id: Optional[int] = Field(default=None, primary_key=True)
    versao_id: int = Field(foreign_key="versaotabela.id", index=True)

    # Categoria (combinação estado + tipo)
    estado_sigla: str = Field(index=True)
    categoria: str = Field(index=True)  # "CAPITAL", "INTERIOR_1", etc
    categoria_completa: str  # Ex: "SP_CAPITAL", "MG_INTERIOR_2"

    # Faixas de peso (valores em R$)
    ate_10: float
    ate_20: float
    ate_40: float
    ate_60: float
    ate_100: float
    excedente_por_kg: float

    # Valores adicionais por estado/região
    pedagio_adicional: Optional[float] = None  # Além do padrão
    gris_percent_especial: Optional[float] = None  # Se diferente do padrão
    fvalor_percent_especial: Optional[float] = None  # Se diferente do padrão
    icms_percent: Optional[float] = None  # Se diferente de 12%

    # Metadados
    criado_em: datetime = Field(default_factory=datetime.now)
    data_atualizacao: Optional[datetime] = None
    importado_pdf: Optional[str] = None  # Nome do PDF de origem

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HistoricoImportacao(SQLModel, table=True):
    """Registro de importações de dados Excel/PDF"""
    __tablename__ = "historicos_importacao"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Informações da importação
    tipo_arquivo: str  # "EXCEL_CIDADES", "EXCEL_TAXAS", "PDF_TARIFAS"
    nome_arquivo: str
    data_importacao: datetime = Field(default_factory=datetime.now)

    # Estatísticas
    total_registros: int
    registros_importados: int
    registros_atualizados: int
    registros_erro: int

    # Status
    status: str  # "SUCESSO", "PARCIAL", "ERRO"
    mensagem_erro: Optional[str] = None
    detalhes_importacao: Optional[str] = None  # Detalhes resumidos
    log_completo: Optional[str] = None  # JSON com detalhes

    # Usuário/sistema
    importado_por: str = "sistema"