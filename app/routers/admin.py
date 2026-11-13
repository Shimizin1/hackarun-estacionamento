"""
Admin router - endpoints for administrative dashboard and operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.admin_service import AdminService
from app.schemas import AdminMetricasResponse
from app.models import TipoVaga

router = APIRouter(prefix="/admin", tags=["Administração"])


@router.get("/metricas", response_model=AdminMetricasResponse)
def obter_metricas(db: Session = Depends(get_db)):
    """
    Obter métricas completas para painel administrativo.
    Inclui ocupação, tickets, carregadores e indicadores operacionais.
    """
    return AdminService.get_metricas_completas(db)


@router.get("/ocupacao")
def obter_ocupacao_detalhada(db: Session = Depends(get_db)):
    """Obter ocupação detalhada por setor."""
    return AdminService.get_ocupacao_detalhada(db)


@router.get("/tickets-recentes")
def obter_tickets_recentes(limit: int = 50, db: Session = Depends(get_db)):
    """Obter tickets recentes para monitoramento."""
    tickets = AdminService.get_tickets_recentes(db, limit)
    return [
        {
            "id": t.id,
            "identificador": t.identificador,
            "vaga": t.vaga.numero if t.vaga else None,
            "setor": t.vaga.setor.nome if t.vaga and t.vaga.setor else None,
            "entrada": t.entrada.isoformat(),
            "saida": t.saida.isoformat() if t.saida else None,
            "valor": t.valor,
            "status": t.status_pagamento.value,
            "placa": t.placa,
        }
        for t in tickets
    ]


@router.post("/simular/entrada")
def simular_entrada(tipo_vaga: TipoVaga, setor_id: int | None = None, db: Session = Depends(get_db)):
    """Simular entrada de veículo para demonstração."""
    try:
        ticket = AdminService.simular_entrada(db, tipo_vaga, setor_id)
        return {
            "message": "Entrada simulada com sucesso",
            "ticket": {
                "identificador": ticket.identificador,
                "vaga": ticket.vaga.numero if ticket.vaga else None,
                "setor": ticket.vaga.setor.nome if ticket.vaga and ticket.vaga.setor else None,
                "entrada": ticket.entrada.isoformat(),
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/simular/saida")
def simular_saida(identificador: str, db: Session = Depends(get_db)):
    """Simular saída de veículo para demonstração."""
    try:
        ticket = AdminService.simular_saida(db, identificador)
        return {
            "message": "Saída simulada com sucesso",
            "ticket": {
                "identificador": ticket.identificador,
                "entrada": ticket.entrada.isoformat(),
                "saida": ticket.saida.isoformat() if ticket.saida else None,
                "valor": ticket.valor,
                "status": ticket.status_pagamento.value,
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset")
def resetar_estacionamento(db: Session = Depends(get_db)):
    """Resetar todo o estacionamento (liberar vagas, cancelar tickets ativos)."""
    return AdminService.resetar_estacionamento(db)


@router.get("/exportar")
def exportar_dados(db: Session = Depends(get_db)):
    """Exportar todos os dados para backup/análise."""
    return AdminService.exportar_dados(db)