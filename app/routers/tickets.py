"""
Tickets router - endpoints for vehicle entry/exit and ticket management.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.ticket_service import (
    TicketService, TicketNaoEncontrado, TicketJaFinalizado, VagaIndisponivel,
)
from app.schemas import (
    TicketEntradaRequest, TicketEntradaResponse,
    TicketSaidaRequest, TicketSaidaResponse,
    TicketResponse,
)
from app.models import TipoVaga

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("/entrada", response_model=TicketEntradaResponse, status_code=status.HTTP_201_CREATED)
def registrar_entrada(request: TicketEntradaRequest, db: Session = Depends(get_db)):
    """
    Registrar entrada de veículo e emitir ticket.
    Atribui vaga automaticamente baseada no tipo e setor preferido.
    Se setor cheio, usa algoritmo de proximidade.
    """
    try:
        return TicketService.registrar_entrada(db, request)
    except VagaIndisponivel as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def _saida(db: Session, identificador: str) -> TicketSaidaResponse:
    try:
        return TicketService.registrar_saida(
            db, TicketSaidaRequest(identificador=identificador)
        )
    except TicketNaoEncontrado as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except TicketJaFinalizado as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/saida", response_model=TicketSaidaResponse)
def registrar_saida(request: TicketSaidaRequest, db: Session = Depends(get_db)):
    """
    Registrar saída de veículo e calcular valor.
    Aplica tolerância (configurável).
    404 se o ticket não existe; 409 se a saída já foi registrada.
    """
    return _saida(db, request.identificador)


@router.post("/{identificador}/saida", response_model=TicketSaidaResponse)
def registrar_saida_por_id(identificador: str, db: Session = Depends(get_db)):
    """Alias da documentação: saída pelo identificador na URL."""
    return _saida(db, identificador)


@router.get("/{identificador}", response_model=TicketResponse)
def consultar_ticket(identificador: str, db: Session = Depends(get_db)):
    """Consultar ticket por identificador."""
    ticket = TicketService.consultar_ticket(db, identificador)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    return ticket


@router.get("", response_model=List[TicketResponse])
def listar_tickets_ativos(db: Session = Depends(get_db)):
    """Listar todos os tickets ativos (veículos no estacionamento)."""
    return TicketService.listar_tickets_ativos(db)


@router.post("/{identificador}/pagar", response_model=TicketResponse)
def confirmar_pagamento(identificador: str, db: Session = Depends(get_db)):
    """Confirmar pagamento de ticket pendente."""
    ticket = TicketService.confirmar_pagamento(db, identificador)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket não encontrado ou não está pendente de pagamento"
        )
    return ticket