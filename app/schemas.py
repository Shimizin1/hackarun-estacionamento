"""
Pydantic schemas for request/response validation.
"""
import re
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.models import TipoVaga, StatusVaga, StatusCarregador, StatusPagamento, OrigemDado


# ==================== Base Schemas ====================

class SetorBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=50)
    cor: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    andar: str = Field(..., min_length=1, max_length=20)
    bloco: Optional[str] = Field(None, max_length=20)
    capacidade_total: int = Field(..., ge=0)
    origem_dado: OrigemDado = OrigemDado.SIMULADO


class SetorCreate(SetorBase):
    pass


class SetorUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=50)
    cor: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    andar: Optional[str] = Field(None, min_length=1, max_length=20)
    bloco: Optional[str] = Field(None, max_length=20)
    capacidade_total: Optional[int] = Field(None, ge=0)
    origem_dado: Optional[OrigemDado] = None


class SetorResponse(SetorBase):
    id: int
    created_at: datetime
    updated_at: datetime
    vagas_livres: int = 0
    vagas_ocupadas: int = 0
    vagas_manutencao: int = 0

    model_config = ConfigDict(from_attributes=True)


class SetorResumo(BaseModel):
    """Setor com contagens de ocupação (GET /setores)."""
    id: int
    nome: str
    cor: str
    andar: str
    bloco: Optional[str] = None
    capacidade_total: int
    vagas_livres: int
    vagas_ocupadas: int


# ==================== Vaga Schemas ====================

class VagaBase(BaseModel):
    setor_id: int = Field(..., gt=0)
    numero: str = Field(..., min_length=1, max_length=20)
    tipo: TipoVaga = TipoVaga.COMUM
    tem_carregador: bool = False
    coordenada_x: Optional[float] = Field(None, ge=0, le=100)
    coordenada_y: Optional[float] = Field(None, ge=0, le=100)
    origem_dado: OrigemDado = OrigemDado.SIMULADO


class VagaCreate(VagaBase):
    pass


class VagaUpdate(BaseModel):
    tipo: Optional[TipoVaga] = None
    status: Optional[StatusVaga] = None
    tem_carregador: Optional[bool] = None
    coordenada_x: Optional[float] = Field(None, ge=0, le=100)
    coordenada_y: Optional[float] = Field(None, ge=0, le=100)
    origem_dado: Optional[OrigemDado] = None


class VagaResponse(VagaBase):
    id: int
    status: StatusVaga
    created_at: datetime
    updated_at: datetime
    setor: Optional[SetorResponse] = None
    carregador: Optional["CarregadorResponse"] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== Carregador Schemas ====================

class CarregadorBase(BaseModel):
    vaga_id: int = Field(..., gt=0)
    tipo_conector: str = Field(..., min_length=1, max_length=20)
    potencia_kw: Optional[float] = Field(None, gt=0)
    tempo_maximo_minutos: int = Field(120, gt=0)
    origem_dado: OrigemDado = OrigemDado.SIMULADO


class CarregadorCreate(CarregadorBase):
    pass


class CarregadorUpdate(BaseModel):
    tipo_conector: Optional[str] = Field(None, min_length=1, max_length=20)
    potencia_kw: Optional[float] = Field(None, gt=0)
    status: Optional[StatusCarregador] = None
    tempo_maximo_minutos: Optional[int] = Field(None, gt=0)
    origem_dado: Optional[OrigemDado] = None


class CarregadorResponse(CarregadorBase):
    id: int
    status: StatusCarregador
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Ticket Schemas ====================

class TicketEntradaRequest(BaseModel):
    """Request para registrar entrada de veículo."""
    tipo_vaga: TipoVaga = Field(..., description="Tipo de vaga desejada")
    setor_id: Optional[int] = Field(None, gt=0, description="Setor preferido (opcional)")
    vaga_id: Optional[int] = Field(None, gt=0, description="Vaga específica (ex.: sugestão aceita); 409 se não estiver livre")
    placa: Optional[str] = Field(None, max_length=10, pattern=r"^[A-Z0-9]{1,10}$", description="Placa do veículo (opcional)")

    @field_validator("placa", mode="before")
    @classmethod
    def normalize_placa(cls, v):
        """Remove espaços/hífens e converte para maiúsculas ANTES do pattern."""
        if isinstance(v, str):
            v = re.sub(r"[\s-]", "", v).upper()
            return v or None
        return v


class TicketEntradaResponse(BaseModel):
    """Response ao criar ticket de entrada."""
    identificador: str
    vaga: VagaResponse
    entrada: datetime
    tolerancia_minutos: int
    valor_hora: float
    tempo_limite_tolerancia: datetime
    mensagem: str


class TicketSaidaRequest(BaseModel):
    """Request para registrar saída."""
    identificador: str = Field(..., min_length=1, max_length=36)


class TicketSaidaResponse(BaseModel):
    """Response ao registrar saída."""
    identificador: str
    entrada: datetime
    saida: datetime
    tempo_total_minutos: int
    tempo_faturavel_minutos: int
    valor: float
    status_pagamento: StatusPagamento
    isento: bool
    mensagem: str


class TicketResponse(BaseModel):
    """Schema completo do ticket."""
    id: int
    identificador: str
    vaga_id: Optional[int]
    entrada: datetime
    saida: Optional[datetime]
    valor: float
    status_pagamento: StatusPagamento
    placa: Optional[str]
    categoria: Optional[TipoVaga]
    tempo_tolerancia_minutos: int
    valor_hora: float
    created_at: datetime
    updated_at: datetime
    vaga: Optional[VagaResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== Config Schemas ====================

class ConfiguracaoBase(BaseModel):
    chave: str = Field(..., min_length=1, max_length=50)
    valor: str = Field(..., min_length=1, max_length=200)
    descricao: Optional[str] = Field(None, max_length=500)


class ConfiguracaoCreate(ConfiguracaoBase):
    pass


class ConfiguracaoUpdate(BaseModel):
    valor: Optional[str] = Field(None, min_length=1, max_length=200)
    descricao: Optional[str] = Field(None, max_length=500)


class ConfiguracaoResponse(ConfiguracaoBase):
    id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConfiguracaoPublicResponse(BaseModel):
    """Configurações públicas (não sensíveis)."""
    tolerancia_minutos: int
    valor_hora: float
    tempo_maximo_recarga_ev: int
    regra_arredondamento: str


# ==================== Admin/Metrics Schemas ====================

class MetricasOcupacao(BaseModel):
    total_vagas: int
    vagas_livres: int
    vagas_ocupadas: int
    vagas_manutencao: int
    taxa_ocupacao: float
    por_andar: List["OcupacaoPorAndar"]
    por_tipo: List["OcupacaoPorTipo"]


class OcupacaoPorAndar(BaseModel):
    andar: str
    total: int
    livres: int
    ocupadas: int
    taxa_ocupacao: float


class OcupacaoPorTipo(BaseModel):
    tipo: str
    total: int
    livres: int
    ocupadas: int
    taxa_ocupacao: float


class MetricasTickets(BaseModel):
    tickets_ativos: int
    tickets_hoje: int
    tickets_isentos_hoje: int
    tickets_pagos_hoje: int
    receita_hoje: float
    tempo_medio_permanencia_minutos: float
    horario_pico: Optional[str]


class MetricasCarregadores(BaseModel):
    total: int
    disponiveis: int
    em_uso: int
    manutencao: int
    tempo_medio_uso_minutos: float


class AdminMetricasResponse(BaseModel):
    ocupacao: MetricasOcupacao
    tickets: MetricasTickets
    carregadores: MetricasCarregadores
    updated_at: datetime


# ==================== Proximidade Schemas ====================

class VagaProximidadeRequest(BaseModel):
    setor_desejado_id: int = Field(..., gt=0)
    tipo_vaga: TipoVaga
    excluir_vaga_id: Optional[int] = None


class VagaSugeridaResponse(BaseModel):
    vaga: VagaResponse
    distancia_metros: float
    tempo_caminhada_minutos: int
    mesmo_andar: bool
    motivo: str


class VagasDisponiveisRequest(BaseModel):
    tipo: Optional[TipoVaga] = None
    setor_id: Optional[int] = Field(None, gt=0)
    andar: Optional[str] = None
    apenas_com_carregador: bool = False


class VagasDisponiveisResponse(BaseModel):
    vagas: List[VagaResponse]
    total: int
    por_setor: List["VagasPorSetor"]
    nivel_confiabilidade: Literal["real", "estimado", "simulado"]
    atualizado_em: datetime


class VagasPorSetor(BaseModel):
    setor_id: int
    setor_nome: str
    setor_cor: str
    andar: str
    livres: int
    ocupadas: int
    total: int


# ==================== Relato Colaborativo Schemas ====================

class RelatoColaborativoRequest(BaseModel):
    setor_id: int = Field(..., gt=0)
    tipo_vaga: TipoVaga
    status: StatusVaga
    confianca: float = Field(0.5, ge=0.0, le=1.0)


class RelatoColaborativoResponse(BaseModel):
    id: int
    setor_id: int
    tipo_vaga: TipoVaga
    status_reportado: StatusVaga
    confianca: float
    fonte: Optional[str]
    expira_em: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Health/Info Schemas ====================

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database: str
    version: str


# Forward references resolution
SetorResponse.model_rebuild()
VagaResponse.model_rebuild()
CarregadorResponse.model_rebuild()
MetricasOcupacao.model_rebuild()
OcupacaoPorAndar.model_rebuild()
OcupacaoPorTipo.model_rebuild()
VagasDisponiveisResponse.model_rebuild()
VagasPorSetor.model_rebuild()