"""
Setores router - listagem somente leitura dos setores com contagem de vagas.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Setor, Vaga, StatusVaga
from app.schemas import SetorResumo

router = APIRouter(prefix="/setores", tags=["Setores"])


@router.get("", response_model=List[SetorResumo])
def listar_setores(db: Session = Depends(get_db)):
    """Lista os setores com vagas livres e ocupadas (todos os tipos)."""
    contagem = {}
    for sid, st, qtd in db.query(Vaga.setor_id, Vaga.status, func.count(Vaga.id)).group_by(
        Vaga.setor_id, Vaga.status
    ):
        contagem.setdefault(sid, {})[st] = qtd

    return [
        SetorResumo(
            id=s.id, nome=s.nome, cor=s.cor, andar=s.andar, bloco=s.bloco,
            capacidade_total=s.capacidade_total,
            vagas_livres=contagem.get(s.id, {}).get(StatusVaga.LIVRE, 0),
            vagas_ocupadas=contagem.get(s.id, {}).get(StatusVaga.OCUPADA, 0),
        )
        for s in db.query(Setor).order_by(Setor.id).all()
    ]
