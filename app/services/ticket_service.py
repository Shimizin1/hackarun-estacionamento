"""
Ticket service for CapimParking.
Handles vehicle entry, exit, pricing with 15-minute tolerance, and ticket management.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from app.models import (
    Ticket, Vaga, Setor, Configuracao,
    TipoVaga, StatusVaga, StatusPagamento
)
from app.schemas import (
    TicketEntradaRequest, TicketEntradaResponse,
    TicketSaidaRequest, TicketSaidaResponse,
    TicketResponse
)
from app.services.vaga_service import VagaService
from app.services.config_service import ConfigService


class TicketService:
    """Service for managing parking tickets and pricing."""

    @classmethod
    def registrar_entrada(
        cls,
        db: Session,
        request: TicketEntradaRequest
    ) -> TicketEntradaResponse:
        """
        Register vehicle entry and assign a spot.
        Implements proximity algorithm if preferred sector is full.
        """
        # Get configuration
        tolerancia = ConfigService.get_int(db, "tolerancia_minutos", 15)
        valor_hora = ConfigService.get_float(db, "valor_hora", 5.0)

        # Find available spot
        vaga = cls._encontrar_vaga(db, request.tipo_vaga, request.setor_id)

        if not vaga:
            # Try proximity recommendation
            if request.setor_id:
                sugestao = VagaService.sugerir_vaga_proxima(
                    db, request.setor_id, request.tipo_vaga
                )
                if sugestao:
                    vaga = sugestao.vaga
                else:
                    raise ValueError(f"Nenhuma vaga {request.tipo_vaga.value} disponível em todo o estacionamento")
            else:
                raise ValueError(f"Nenhuma vaga {request.tipo_vaga.value} disponível")

        # Occupy the spot
        vaga = VagaService.ocupar_vaga(db, vaga.id)
        if not vaga:
            raise ValueError("Falha ao ocupar a vaga")

        # Create ticket
        identificador = cls._gerar_identificador()
        entrada = datetime.utcnow()
        tempo_limite = entrada + timedelta(minutes=tolerancia)

        ticket = Ticket(
            identificador=identificador,
            vaga_id=vaga.id,
            entrada=entrada,
            status_pagamento=StatusPagamento.PENDENTE,
            placa=request.placa,
            categoria=request.tipo_vaga,
            tempo_tolerancia_minutos=tolerancia,
            valor_hora=valor_hora,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        # Load relationships for response
        ticket = db.query(Ticket).options(
            joinedload(Ticket.vaga).joinedload(Vaga.setor),
            joinedload(Ticket.vaga).joinedload(Vaga.carregador)
        ).filter(Ticket.id == ticket.id).first()

        return TicketEntradaResponse(
            identificador=ticket.identificador,
            vaga=VagaResponse.model_validate(ticket.vaga),
            entrada=ticket.entrada,
            tolerancia_minutos=tolerancia,
            valor_hora=valor_hora,
            tempo_limite_tolerancia=tempo_limite,
            mensagem=cls._gerar_mensagem_entrada(ticket, vaga, tolerancia),
        )

    @classmethod
    def registrar_saida(
        cls,
        db: Session,
        request: TicketSaidaRequest
    ) -> TicketSaidaResponse:
        """
        Register vehicle exit and calculate pricing.
        Applies 15-minute tolerance rule.
        """
        # Find active ticket
        ticket = db.query(Ticket).options(
            joinedload(Ticket.vaga).joinedload(Vaga.setor),
            joinedload(Ticket.vaga).joinedload(Vaga.carregador)
        ).filter(
            and_(
                Ticket.identificador == request.identificador,
                Ticket.saida.is_(None)
            )
        ).first()

        if not ticket:
            raise ValueError("Ticket não encontrado ou já finalizado")

        saida = datetime.utcnow()
        ticket.saida = saida

        # Calculate pricing
        tempo_total_minutos = int((saida - ticket.entrada).total_seconds() / 60)
        tempo_faturavel = max(0, tempo_total_minutos - ticket.tempo_tolerancia_minutos)

        if tempo_faturavel <= 0:
            # Within tolerance - free
            valor = 0.0
            status = StatusPagamento.ISENTO
            isento = True
        else:
            # Calculate charge based on rounding rule
            regra = ConfigService.get(db, "regra_arredondamento", "hora_cheia")
            valor = cls._calcular_valor(tempo_faturavel, ticket.valor_hora, regra)
            status = StatusPagamento.PENDENTE
            isento = False

        ticket.valor = valor
        ticket.status_pagamento = status
        ticket.updated_at = saida

        # Free the spot
        if ticket.vaga_id:
            VagaService.liberar_vaga(db, ticket.vaga_id)

        db.commit()
        db.refresh(ticket)

        return TicketSaidaResponse(
            identificador=ticket.identificador,
            entrada=ticket.entrada,
            saida=ticket.saida,
            tempo_total_minutos=tempo_total_minutos,
            tempo_faturavel_minutos=tempo_faturavel,
            valor=valor,
            status_pagamento=status,
            isento=isento,
            mensagem=cls._gerar_mensagem_saida(ticket, tempo_total_minutos, tempo_faturavel, valor, isento),
        )

    @classmethod
    def consultar_ticket(
        cls,
        db: Session,
        identificador: str
    ) -> Optional[TicketResponse]:
        """Query ticket by identifier."""
        ticket = db.query(Ticket).options(
            joinedload(Ticket.vaga).joinedload(Vaga.setor),
            joinedload(Ticket.vaga).joinedload(Vaga.carregador)
        ).filter(Ticket.identificador == identificador).first()

        if not ticket:
            return None

        return TicketResponse.model_validate(ticket)

    @classmethod
    def listar_tickets_ativos(cls, db: Session) -> List[TicketResponse]:
        """List all active (not exited) tickets."""
        tickets = db.query(Ticket).options(
            joinedload(Ticket.vaga).joinedload(Vaga.setor),
            joinedload(Ticket.vaga).joinedload(Vaga.carregador)
        ).filter(Ticket.saida.is_(None)).order_by(Ticket.entrada.desc()).all()

        return [TicketResponse.model_validate(t) for t in tickets]

    @classmethod
    def confirmar_pagamento(cls, db: Session, identificador: str) -> Optional[TicketResponse]:
        """Confirm payment for a ticket."""
        ticket = db.query(Ticket).filter(
            and_(
                Ticket.identificador == identificador,
                Ticket.status_pagamento == StatusPagamento.PENDENTE
            )
        ).first()

        if not ticket:
            return None

        ticket.status_pagamento = StatusPagamento.PAGO
        ticket.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ticket)

        return cls.consultar_ticket(db, identificador)

    @classmethod
    def _encontrar_vaga(
        cls,
        db: Session,
        tipo_vaga: TipoVaga,
        setor_id: Optional[int]
    ) -> Optional[Vaga]:
        """Find an available spot, preferring the requested sector."""
        query = db.query(Vaga).filter(
            and_(
                Vaga.tipo == tipo_vaga,
                Vaga.status == StatusVaga.LIVRE
            )
        )

        if setor_id:
            # First try preferred sector
            vaga = query.filter(Vaga.setor_id == setor_id).first()
            if vaga:
                return vaga

        # Fallback: any sector
        return query.first()

    @classmethod
    def _gerar_identificador(cls) -> str:
        """Generate a short unique identifier for the ticket."""
        # Use first 8 chars of UUID, uppercase
        return str(uuid.uuid4())[:8].upper()

    @classmethod
    def _calcular_valor(
        cls,
        minutos_faturaveis: int,
        valor_hora: float,
        regra: str
    ) -> float:
        """
        Calculate charge based on rounding rule.
        Rules:
        - 'hora_cheia': Round up to full hours
        - 'fracao_15min': Round up to 15-minute fractions
        """
        if regra == "fracao_15min":
            # Round up to 15-minute blocks
            fracoes = (minutos_faturaveis + 14) // 15
            horas = fracoes * 0.25
        else:
            # Default: round up to full hours
            horas = (minutos_faturaveis + 59) // 60

        return round(horas * valor_hora, 2)

    @classmethod
    def _gerar_mensagem_entrada(
        cls,
        ticket: Ticket,
        vaga: Vaga,
        tolerancia: int
    ) -> str:
        """Generate entry confirmation message."""
        setor_nome = vaga.setor.nome if vaga.setor else "Desconhecido"
        andar = vaga.setor.andar if vaga.setor else ""
        carregador = " com carregador" if vaga.tem_carregador else ""

        return (
            f"Entrada registrada! Vaga {vaga.numero} no setor {setor_nome} ({andar}){carregador}. "
            f"Tolerância de {tolerancia} minutos até {ticket.entrada + timedelta(minutes=tolerancia):%H:%M}. "
            f"Guarde seu código: {ticket.identificador}"
        )

    @classmethod
    def _gerar_mensagem_saida(
        cls,
        ticket: Ticket,
        tempo_total: int,
        tempo_faturavel: int,
        valor: float,
        isento: bool
    ) -> str:
        """Generate exit message with pricing details."""
        if isento:
            return (
                f"Saída registrada. Tempo de permanência: {tempo_total} min. "
                f"Dentro da tolerância de {ticket.tempo_tolerancia_minutos} min — ISENTO. Valor: R$ 0,00"
            )
        else:
            horas = tempo_faturavel / 60
            return (
                f"Saída registrada. Tempo total: {tempo_total} min. "
                f"Tempo faturável (após {ticket.tempo_tolerancia_minutos} min tolerância): {tempo_faturavel} min "
                f"({horas:.1f}h). Valor: R$ {valor:.2f}"
            )

    @classmethod
    def get_tickets_por_periodo(
        cls,
        db: Session,
        inicio: datetime,
        fim: datetime
    ) -> List[TicketResponse]:
        """Get tickets within a time range."""
        tickets = db.query(Ticket).options(
            joinedload(Ticket.vaga).joinedload(Vaga.setor),
            joinedload(Ticket.vaga).joinedload(Vaga.carregador)
        ).filter(
            and_(
                Ticket.entrada >= inicio,
                Ticket.entrada <= fim
            )
        ).order_by(Ticket.entrada.desc()).all()

        return [TicketResponse.model_validate(t) for t in tickets]