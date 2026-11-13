"""
SQLAlchemy models for CapimParking.
Defines all entities: Setor, Vaga, Ticket, Configuracao, Carregador, RelatoColaborativo.
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, validates
from app.database import Base


class TipoVaga(str, PyEnum):
    """Tipos de vaga disponíveis."""
    COMUM = "comum"
    IDOSO = "idoso"
    PCD = "pcd"
    NEURODIVERGENTE = "neurodivergente"
    ELETRICO = "eletrico"
    MOTO = "moto"
    GESTANTE = "gestante"


class StatusVaga(str, PyEnum):
    """Status de ocupação da vaga."""
    LIVRE = "livre"
    OCUPADA = "ocupada"
    MANUTENCAO = "manutencao"
    RESERVADA = "reservada"


class StatusCarregador(str, PyEnum):
    """Status do carregador de veículo elétrico."""
    DISPONIVEL = "disponivel"
    EM_USO = "em_uso"
    MANUTENCAO = "manutencao"


class StatusPagamento(str, PyEnum):
    """Status do pagamento do ticket."""
    ISENTO = "isento"           # Até 15 min
    PENDENTE = "pendente"       # Aguardando pagamento
    PAGO = "pago"               # Pago
    CANCELADO = "cancelado"     # Cancelado


class OrigemDado(str, PyEnum):
    """Origem do dado para transparência."""
    REAL = "real"               # Sensor/catraca oficial
    ESTIMADO = "estimado"       # Estimativa colaborativa
    SIMULADO = "simulado"       # Dados de demonstração


class Setor(Base):
    """Setor/área do estacionamento."""
    __tablename__ = "setores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(50), unique=True, nullable=False, index=True)
    cor = Column(String(20), nullable=False)  # Cor para identificação visual (ex: "Azul", "Verde")
    andar = Column(String(20), nullable=False)  # Ex: "Subsolo 1", "Subsolo 2"
    bloco = Column(String(20), nullable=True)   # Ex: "A", "B", "C"
    capacidade_total = Column(Integer, default=0, nullable=False)
    origem_dado = Column(Enum(OrigemDado), default=OrigemDado.SIMULADO, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    vagas = relationship("Vaga", back_populates="setor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Setor(id={self.id}, nome='{self.nome}', andar='{self.andar}', cor='{self.cor}')>"


class Vaga(Base):
    """Vaga individual de estacionamento."""
    __tablename__ = "vagas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    setor_id = Column(Integer, ForeignKey("setores.id", ondelete="CASCADE"), nullable=False, index=True)
    numero = Column(String(20), nullable=False)  # Ex: "A-12", "B-05"
    tipo = Column(Enum(TipoVaga), default=TipoVaga.COMUM, nullable=False, index=True)
    status = Column(Enum(StatusVaga), default=StatusVaga.LIVRE, nullable=False, index=True)
    tem_carregador = Column(Boolean, default=False, nullable=False)
    coordenada_x = Column(Float, nullable=True)  # Coordenada virtual para mapa (0-100%)
    coordenada_y = Column(Float, nullable=True)  # Coordenada virtual para mapa (0-100%)
    origem_dado = Column(Enum(OrigemDado), default=OrigemDado.SIMULADO, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    setor = relationship("Setor", back_populates="vagas")
    tickets = relationship("Ticket", back_populates="vaga")
    carregador = relationship("Carregador", back_populates="vaga", uselist=False, cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint("setor_id", "numero", name="uq_vaga_setor_numero"),
        Index("ix_vaga_tipo_status", "tipo", "status"),
    )

    def __repr__(self):
        return f"<Vaga(id={self.id}, numero='{self.numero}', tipo='{self.tipo}', status='{self.status}')>"


class Carregador(Base):
    """Carregador de veículo elétrico associado a uma vaga."""
    __tablename__ = "carregadores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vaga_id = Column(Integer, ForeignKey("vagas.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    tipo_conector = Column(String(20), nullable=False)  # Ex: "Tipo 2", "CCS2"
    potencia_kw = Column(Float, nullable=True)  # Ex: 7.4, 22, 50
    status = Column(Enum(StatusCarregador), default=StatusCarregador.DISPONIVEL, nullable=False)
    tempo_maximo_minutos = Column(Integer, default=120, nullable=False)  # Configurável
    origem_dado = Column(Enum(OrigemDado), default=OrigemDado.SIMULADO, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    vaga = relationship("Vaga", back_populates="carregador")

    def __repr__(self):
        return f"<Carregador(id={self.id}, vaga_id={self.vaga_id}, tipo='{self.tipo_conector}', status='{self.status}')>"


class Ticket(Base):
    """Ticket de estacionamento (entrada/saída)."""
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identificador = Column(String(36), unique=True, nullable=False, index=True)  # UUID v4
    vaga_id = Column(Integer, ForeignKey("vagas.id", ondelete="SET NULL"), nullable=True, index=True)
    entrada = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    saida = Column(DateTime, nullable=True)
    valor = Column(Float, default=0.0, nullable=False)
    status_pagamento = Column(Enum(StatusPagamento), default=StatusPagamento.PENDENTE, nullable=False)
    placa = Column(String(10), nullable=True)  # Opcional, não obrigatório
    categoria = Column(Enum(TipoVaga), nullable=True)  # Tipo de vaga usado
    tempo_tolerancia_minutos = Column(Integer, default=15, nullable=False)
    valor_hora = Column(Float, default=5.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    vaga = relationship("Vaga", back_populates="tickets")

    # Constraints
    __table_args__ = (
        Index("ix_ticket_entrada_saida", "entrada", "saida"),
        Index("ix_ticket_status_entrada", "status_pagamento", "entrada"),
    )

    def __repr__(self):
        return f"<Ticket(id={self.id}, identificador='{self.identificador}', status='{self.status_pagamento}')>"


class Configuracao(Base):
    """Configurações globais do sistema."""
    __tablename__ = "configuracoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chave = Column(String(50), unique=True, nullable=False, index=True)
    valor = Column(String(200), nullable=False)
    descricao = Column(String(500), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Configuracao(chave='{self.chave}', valor='{self.valor}')>"


class RelatoColaborativo(Base):
    """Relato colaborativo de disponibilidade por usuários."""
    __tablename__ = "relatos_colaborativos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    setor_id = Column(Integer, ForeignKey("setores.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo_vaga = Column(Enum(TipoVaga), nullable=False)
    status_reportado = Column(Enum(StatusVaga), nullable=False)
    confianca = Column(Float, default=0.5, nullable=False)  # 0.0 a 1.0
    fonte = Column(String(50), nullable=True)  # Ex: "usuario", "sensor_simulado"
    expira_em = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    setor = relationship("Setor")

    # Constraints
    __table_args__ = (
        Index("ix_relato_setor_tipo_expira", "setor_id", "tipo_vaga", "expira_em"),
    )

    def __repr__(self):
        return f"<RelatoColaborativo(setor_id={self.setor_id}, tipo={self.tipo_vaga}, status={self.status_reportado})>"


# Default configurations
DEFAULT_CONFIGS = {
    "tolerancia_minutos": ("15", "Tolerância em minutos para passagem rápida sem cobrança"),
    "valor_hora": ("5.0", "Valor por hora de estacionamento (R$)"),
    "tempo_maximo_recarga_ev": ("120", "Tempo máximo de ocupação de vaga elétrica durante recarga (minutos)"),
    "regra_arredondamento": ("hora_cheia", "Regra de arredondamento: 'hora_cheia' ou 'fracao_15min'"),
    "expiracao_relato_minutos": ("30", "Tempo de expiração de relatos colaborativos (minutos)"),
}