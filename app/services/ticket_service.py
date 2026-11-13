"""
Ticket service for CapimParking.
Handles vehicle entry, exit, pricing with 15-minute tolerance, and ticket management.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, update
from app.models import (
    Ticket, Vaga, Setor, Configuracao, Carregador,
    TipoVaga, StatusVaga, StatusPagamento, StatusCarregador
)
from app.schemas import (
    TicketEntradaRequest, TicketEntradaResponse,
    TicketSaidaRequest, TicketSaidaResponse,
    TicketResponse, VagaResponse
)
from app.services.vaga_service import VagaService
from app.services.config_service import ConfigService


class TicketNaoEncontrado(LookupError):
    """Nenhum ticket com o identificador informado."""


class VagaIndisponivel(Exception):
    """A vaga pedida (vaga_id) não está livre ou não é do tipo solicitado."""


class TicketJaFinalizado(Exception):
    """O ticket já teve a saída registrada."""


@dataclass(frozen=True)
class Cobranca:
    tempo_total_minutos: int      # floor da permanência
    tempo_faturavel_minutos: int  # ceil do que excede a tolerância (0 se isento)
    valor: float
    isento: bool


MAX_TENTATIVAS_VAGA = 5

_US_MINUTO = 60 * 1_000_000
_US_HORA = 3600 * 1_000_000


def _hora_local(dt: datetime) -> str:
    """Formata HH:MM em America/Araguaina (UTC-3, sem horário de verão); dt é UTC naive."""
    return (dt - timedelta(hours=3)).strftime("%H:%M")


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def calcular_cobranca(
    entrada: datetime,
    saida: datetime,
    tolerancia_minutos: int,
    valor_hora: float,
    regra: str = "hora_cheia",
) -> Cobranca:
    """
    Função pura de cobrança (DT1/DT2), calculada em microssegundos inteiros.
    Permanência <= tolerância: isento. Senão, o excedente é arredondado para
    cima por hora ('hora_cheia') ou por 15 min ('fracao_15min').
    """
    perm_us = max(0, (saida - entrada) // timedelta(microseconds=1))
    tol_us = tolerancia_minutos * _US_MINUTO
    total_min = perm_us // _US_MINUTO

    if perm_us <= tol_us:
        return Cobranca(total_min, 0, 0.0, True)

    fat_us = perm_us - tol_us
    faturavel_min = _ceil_div(fat_us, _US_MINUTO)
    if regra == "fracao_15min":
        horas = _ceil_div(fat_us, 15 * _US_MINUTO) * 0.25
    else:
        horas = _ceil_div(fat_us, _US_HORA)
    return Cobranca(total_min, faturavel_min, round(horas * valor_hora, 2), False)


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
        Transação única (DT3): reserva da vaga + ticket + um commit; qualquer
        falha faz rollback e a vaga continua livre.
        """
        tolerancia = ConfigService.get_int(db, "tolerancia_minutos", 15)
        valor_hora = ConfigService.get_float(db, "valor_hora", 5.0)

        try:
            # Reserva condicional (UPDATE ... WHERE status = LIVRE), sem commit.
            # Se uma entrada concorrente levou a vaga escolhida, tenta outra
            # (excluindo as já disputadas) em vez de falhar com vagas livres.
            vaga = None
            disputadas: set = set()
            for _ in range(MAX_TENTATIVAS_VAGA):
                candidata = cls._encontrar_vaga(
                    db, request.tipo_vaga, request.setor_id, request.vaga_id,
                    excluir=disputadas,
                )
                if not candidata:
                    break
                vaga = VagaService.ocupar_vaga(db, candidata.id, commit=False)
                if vaga:
                    break
                if request.vaga_id:
                    raise VagaIndisponivel("A vaga escolhida não está mais disponível")
                disputadas.add(candidata.id)

            if not vaga:
                raise ValueError(f"Nenhuma vaga {request.tipo_vaga.value} disponível")

            entrada = datetime.utcnow()
            tempo_limite = entrada + timedelta(minutes=tolerancia)

            ticket = Ticket(
                identificador=cls._gerar_identificador(),
                vaga_id=vaga.id,
                entrada=entrada,
                status_pagamento=StatusPagamento.PENDENTE,
                placa=request.placa,
                categoria=request.tipo_vaga,
                tempo_tolerancia_minutos=tolerancia,
                valor_hora=valor_hora,
            )
            db.add(ticket)
            db.flush()

            response = TicketEntradaResponse(
                identificador=ticket.identificador,
                vaga=VagaResponse.model_validate(vaga),
                entrada=ticket.entrada,
                tolerancia_minutos=tolerancia,
                valor_hora=valor_hora,
                tempo_limite_tolerancia=tempo_limite,
                mensagem=cls._gerar_mensagem_entrada(ticket, vaga, tolerancia),
            )
            db.commit()
            return response
        except Exception:
            db.rollback()
            raise

    @classmethod
    def registrar_saida(
        cls,
        db: Session,
        request: TicketSaidaRequest,
        agora: Optional[datetime] = None,
    ) -> TicketSaidaResponse:
        """
        Register vehicle exit and calculate pricing (tolerância + DT1).
        `agora` é injetável para testes.
        """
        ticket = db.query(Ticket).options(
            joinedload(Ticket.vaga).joinedload(Vaga.setor),
            joinedload(Ticket.vaga).joinedload(Vaga.carregador)
        ).filter(Ticket.identificador == request.identificador).first()

        if not ticket:
            raise TicketNaoEncontrado("Ticket não encontrado")
        if ticket.saida is not None:
            raise TicketJaFinalizado("Este ticket já teve a saída registrada")

        try:
            saida = agora or datetime.utcnow()
            regra = ConfigService.get(db, "regra_arredondamento", "hora_cheia")
            cobranca = calcular_cobranca(
                ticket.entrada, saida, ticket.tempo_tolerancia_minutos,
                ticket.valor_hora, regra,
            )
            status = StatusPagamento.ISENTO if cobranca.isento else StatusPagamento.PENDENTE

            # Saída atômica: só quem encontrar saida IS NULL fecha o ticket.
            res = db.execute(
                update(Ticket)
                .where(Ticket.id == ticket.id, Ticket.saida.is_(None))
                .values(saida=saida, valor=cobranca.valor,
                        status_pagamento=status, updated_at=saida)
            )
            if res.rowcount != 1:
                raise TicketJaFinalizado("Este ticket já teve a saída registrada")

            if ticket.vaga_id:
                VagaService.liberar_vaga(db, ticket.vaga_id, commit=False)

            db.commit()
            db.refresh(ticket)
        except Exception:
            db.rollback()
            raise

        return TicketSaidaResponse(
            identificador=ticket.identificador,
            entrada=ticket.entrada,
            saida=ticket.saida,
            tempo_total_minutos=cobranca.tempo_total_minutos,
            tempo_faturavel_minutos=cobranca.tempo_faturavel_minutos,
            valor=cobranca.valor,
            status_pagamento=status,
            isento=cobranca.isento,
            mensagem=cls._gerar_mensagem_saida(
                ticket, cobranca.tempo_total_minutos,
                cobranca.tempo_faturavel_minutos, cobranca.valor, cobranca.isento),
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
        setor_id: Optional[int],
        vaga_id: Optional[int] = None,
        excluir: Optional[set] = None,
    ) -> Optional[Vaga]:
        """
        Escolhe a vaga da entrada (DT10):
        - `vaga_id`: exatamente essa vaga, que precisa estar livre e ser do tipo (senão 409);
        - `setor_id`: primeira livre do tipo no setor; setor cheio -> mais próxima (proximidade);
        - sem setor: primeira livre do tipo.
        Vaga elétrica só com carregador DISPONIVEL (A13).
        """
        def livres_do_tipo():
            q = db.query(Vaga).filter(
                and_(Vaga.tipo == tipo_vaga, Vaga.status == StatusVaga.LIVRE)
            )
            if tipo_vaga == TipoVaga.ELETRICO:
                q = q.join(Carregador, Carregador.vaga_id == Vaga.id).filter(
                    Carregador.status == StatusCarregador.DISPONIVEL
                )
            if excluir:
                q = q.filter(Vaga.id.notin_(excluir))
            return q.order_by(Vaga.id)

        if vaga_id:
            vaga = livres_do_tipo().filter(Vaga.id == vaga_id).first()
            if not vaga:
                raise VagaIndisponivel(
                    "A vaga escolhida não está livre ou não é do tipo solicitado"
                )
            return vaga

        if setor_id:
            vaga = livres_do_tipo().filter(Vaga.setor_id == setor_id).first()
            if vaga:
                return vaga
            sugestao = VagaService.sugerir_vaga_proxima(
                db, setor_id, tipo_vaga, list(excluir) if excluir else None)
            if sugestao:
                return db.get(Vaga, sugestao.vaga.id)
            return None

        return livres_do_tipo().first()

    @classmethod
    def _gerar_identificador(cls) -> str:
        """Generate a short unique identifier for the ticket."""
        # Use first 8 chars of UUID, uppercase
        return str(uuid.uuid4())[:8].upper()

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
            f"Tolerância de {tolerancia} minutos até {_hora_local(ticket.entrada + timedelta(minutes=tolerancia))}. "
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
