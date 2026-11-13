"""
Admin service for CapimParking.
Provides metrics, occupancy stats, and administrative operations.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, case
from app.models import (
    Vaga, Setor, Ticket, Carregador, Configuracao,
    TipoVaga, StatusVaga, StatusCarregador, StatusPagamento
)
from app.schemas import (
    AdminMetricasResponse, MetricasOcupacao, OcupacaoPorAndar, OcupacaoPorTipo,
    MetricasTickets, MetricasCarregadores
)
from app.services.vaga_service import VagaService


class AdminService:
    """Service for administrative metrics and operations."""

    @classmethod
    def get_metricas_completas(cls, db: Session) -> AdminMetricasResponse:
        """Get all administrative metrics."""
        ocupacao = cls.get_metricas_ocupacao(db)
        tickets = cls.get_metricas_tickets(db)
        carregadores = cls.get_metricas_carregadores(db)

        return AdminMetricasResponse(
            ocupacao=ocupacao,
            tickets=tickets,
            carregadores=carregadores,
            updated_at=datetime.utcnow(),
        )

    @classmethod
    def get_metricas_ocupacao(cls, db: Session) -> MetricasOcupacao:
        """Get occupancy metrics."""
        # Total counts
        total_vagas = db.query(func.count(Vaga.id)).scalar() or 0
        vagas_livres = db.query(func.count(Vaga.id)).filter(Vaga.status == StatusVaga.LIVRE).scalar() or 0
        vagas_ocupadas = db.query(func.count(Vaga.id)).filter(Vaga.status == StatusVaga.OCUPADA).scalar() or 0
        vagas_manutencao = db.query(func.count(Vaga.id)).filter(Vaga.status == StatusVaga.MANUTENCAO).scalar() or 0

        taxa_ocupacao = round(vagas_ocupadas / total_vagas * 100, 1) if total_vagas > 0 else 0

        # Por andar
        por_andar_result = db.query(
            Setor.andar,
            func.count(Vaga.id).label("total"),
            func.sum(case((Vaga.status == StatusVaga.LIVRE, 1), else_=0)).label("livres"),
            func.sum(case((Vaga.status == StatusVaga.OCUPADA, 1), else_=0)).label("ocupadas"),
        ).join(Vaga).group_by(Setor.andar).all()

        por_andar = [
            OcupacaoPorAndar(
                andar=r.andar,
                total=r.total,
                livres=r.livres or 0,
                ocupadas=r.ocupadas or 0,
                taxa_ocupacao=round((r.ocupadas or 0) / r.total * 100, 1) if r.total > 0 else 0,
            )
            for r in por_andar_result
        ]

        # Por tipo
        por_tipo_result = db.query(
            Vaga.tipo,
            func.count(Vaga.id).label("total"),
            func.sum(case((Vaga.status == StatusVaga.LIVRE, 1), else_=0)).label("livres"),
            func.sum(case((Vaga.status == StatusVaga.OCUPADA, 1), else_=0)).label("ocupadas"),
        ).group_by(Vaga.tipo).all()

        por_tipo = [
            OcupacaoPorTipo(
                tipo=r.tipo.value,
                total=r.total,
                livres=r.livres or 0,
                ocupadas=r.ocupadas or 0,
                taxa_ocupacao=round((r.ocupadas or 0) / r.total * 100, 1) if r.total > 0 else 0,
            )
            for r in por_tipo_result
        ]

        return MetricasOcupacao(
            total_vagas=total_vagas,
            vagas_livres=vagas_livres,
            vagas_ocupadas=vagas_ocupadas,
            vagas_manutencao=vagas_manutencao,
            taxa_ocupacao=taxa_ocupacao,
            por_andar=por_andar,
            por_tipo=por_tipo,
        )

    @classmethod
    def get_metricas_tickets(cls, db: Session) -> MetricasTickets:
        """Get ticket metrics."""
        hoje_inicio = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        amanha_inicio = hoje_inicio + timedelta(days=1)

        # Active tickets
        tickets_ativos = db.query(func.count(Ticket.id)).filter(Ticket.saida.is_(None)).scalar() or 0

        # Today's tickets
        tickets_hoje = db.query(func.count(Ticket.id)).filter(
            and_(Ticket.entrada >= hoje_inicio, Ticket.entrada < amanha_inicio)
        ).scalar() or 0

        # Today's exempt tickets
        tickets_isentos_hoje = db.query(func.count(Ticket.id)).filter(
            and_(
                Ticket.entrada >= hoje_inicio,
                Ticket.entrada < amanha_inicio,
                Ticket.status_pagamento == StatusPagamento.ISENTO
            )
        ).scalar() or 0

        # Today's paid tickets
        tickets_pagos_hoje = db.query(func.count(Ticket.id)).filter(
            and_(
                Ticket.entrada >= hoje_inicio,
                Ticket.entrada < amanha_inicio,
                Ticket.status_pagamento == StatusPagamento.PAGO
            )
        ).scalar() or 0

        # Today's revenue
        receita_hoje = db.query(func.coalesce(func.sum(Ticket.valor), 0)).filter(
            and_(
                Ticket.entrada >= hoje_inicio,
                Ticket.entrada < amanha_inicio,
                Ticket.status_pagamento == StatusPagamento.PAGO
            )
        ).scalar() or 0.0

        # Average stay time (completed tickets today)
        tempo_medio_result = db.query(
            func.avg(
                func.extract('epoch', Ticket.saida - Ticket.entrada) / 60
            )
        ).filter(
            and_(
                Ticket.entrada >= hoje_inicio,
                Ticket.entrada < amanha_inicio,
                Ticket.saida.isnot(None)
            )
        ).scalar()

        tempo_medio = round(tempo_medio_result, 1) if tempo_medio_result else 0.0

        # Peak hour (hour with most entries today)
        horario_pico_result = db.query(
            func.strftime('%H', Ticket.entrada).label('hora'),
            func.count(Ticket.id).label('count')
        ).filter(
            and_(Ticket.entrada >= hoje_inicio, Ticket.entrada < amanha_inicio)
        ).group_by('hora').order_by(func.count(Ticket.id).desc()).first()

        horario_pico = f"{horario_pico_result.hora}:00" if horario_pico_result else None

        return MetricasTickets(
            tickets_ativos=tickets_ativos,
            tickets_hoje=tickets_hoje,
            tickets_isentos_hoje=tickets_isentos_hoje,
            tickets_pagos_hoje=tickets_pagos_hoje,
            receita_hoje=round(receita_hoje, 2),
            tempo_medio_permanencia_minutos=tempo_medio,
            horario_pico=horario_pico,
        )

    @classmethod
    def get_metricas_carregadores(cls, db: Session) -> MetricasCarregadores:
        """Get EV charger metrics."""
        total = db.query(func.count(Carregador.id)).scalar() or 0
        disponiveis = db.query(func.count(Carregador.id)).filter(
            Carregador.status == StatusCarregador.DISPONIVEL
        ).scalar() or 0
        em_uso = db.query(func.count(Carregador.id)).filter(
            Carregador.status == StatusCarregador.EM_USO
        ).scalar() or 0
        manutencao = db.query(func.count(Carregador.id)).filter(
            Carregador.status == StatusCarregador.MANUTENCAO
        ).scalar() or 0

        # Average usage time (from completed EV tickets today)
        hoje_inicio = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        amanha_inicio = hoje_inicio + timedelta(days=1)

        tempo_medio_result = db.query(
            func.avg(
                func.extract('epoch', Ticket.saida - Ticket.entrada) / 60
            )
        ).join(Vaga).join(Carregador).filter(
            and_(
                Ticket.entrada >= hoje_inicio,
                Ticket.entrada < amanha_inicio,
                Ticket.saida.isnot(None),
                Vaga.tem_carregador == True
            )
        ).scalar()

        tempo_medio = round(tempo_medio_result, 1) if tempo_medio_result else 0.0

        return MetricasCarregadores(
            total=total,
            disponiveis=disponiveis,
            em_uso=em_uso,
            manutencao=manutencao,
            tempo_medio_uso_minutos=tempo_medio,
        )

    @classmethod
    def get_ocupacao_detalhada(cls, db: Session) -> List[dict]:
        """Get detailed occupancy per sector."""
        return VagaService.get_ocupacao_por_setor(db)

    @classmethod
    def get_tickets_recentes(cls, db: Session, limit: int = 50) -> List[Ticket]:
        """Get recent tickets."""
        return db.query(Ticket).options(
            joinedload(Ticket.vaga).joinedload(Vaga.setor)
        ).order_by(Ticket.entrada.desc()).limit(limit).all()

    @classmethod
    def simular_entrada(cls, db: Session, tipo_vaga: TipoVaga, setor_id: Optional[int] = None) -> Ticket:
        """Simulate a vehicle entry for demo purposes."""
        from app.services.ticket_service import TicketService
        from app.schemas import TicketEntradaRequest

        request = TicketEntradaRequest(tipo_vaga=tipo_vaga, setor_id=setor_id)
        response = TicketService.registrar_entrada(db, request)
        return db.query(Ticket).filter(Ticket.identificador == response.identificador).first()

    @classmethod
    def simular_saida(cls, db: Session, identificador: str) -> Ticket:
        """Simulate a vehicle exit for demo purposes."""
        from app.services.ticket_service import TicketService
        from app.schemas import TicketSaidaRequest

        request = TicketSaidaRequest(identificador=identificador)
        response = TicketService.registrar_saida(db, request)
        return db.query(Ticket).filter(Ticket.identificador == identificador).first()

    @classmethod
    def resetar_estacionamento(cls, db: Session) -> dict:
        """Reset all spots to free and clear active tickets (for demo reset)."""
        # Free all occupied spots
        db.query(Vaga).filter(Vaga.status == StatusVaga.OCUPADA).update(
            {Vaga.status: StatusVaga.LIVRE, Vaga.updated_at: datetime.utcnow()}
        )

        # Mark active tickets as cancelled
        db.query(Ticket).filter(Ticket.saida.is_(None)).update(
            {Ticket.status_pagamento: StatusPagamento.CANCELADO, Ticket.updated_at: datetime.utcnow()}
        )

        # Reset charger statuses
        db.query(Carregador).filter(Carregador.status == StatusCarregador.EM_USO).update(
            {Carregador.status: StatusCarregador.DISPONIVEL, Carregador.updated_at: datetime.utcnow()}
        )

        db.commit()

        return {"message": "Estacionamento resetado com sucesso", "timestamp": datetime.utcnow().isoformat()}

    @classmethod
    def exportar_dados(cls, db: Session) -> dict:
        """Export all data for backup/analysis."""
        return {
            "setores": [{"id": s.id, "nome": s.nome, "cor": s.cor, "andar": s.andar, "bloco": s.bloco, "capacidade": s.capacidade_total} for s in db.query(Setor).all()],
            "vagas": [{"id": v.id, "setor_id": v.setor_id, "numero": v.numero, "tipo": v.tipo.value, "status": v.status.value, "tem_carregador": v.tem_carregador} for v in db.query(Vaga).all()],
            "tickets": [{"id": t.id, "identificador": t.identificador, "vaga_id": t.vaga_id, "entrada": t.entrada.isoformat(), "saida": t.saida.isoformat() if t.saida else None, "valor": t.valor, "status": t.status_pagamento.value} for t in db.query(Ticket).all()],
            "configuracoes": [{"chave": c.chave, "valor": c.valor} for c in db.query(Configuracao).all()],
            "exportado_em": datetime.utcnow().isoformat(),
        }
