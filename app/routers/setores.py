"""
Setores router - listagem somente leitura dos setores com contagem de vagas.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Setor, Vaga, StatusVaga
from app.schemas import SetorResumo
from app.services.vaga_service import vaga_livre_utilizavel

router = APIRouter(prefix="/setores", tags=["Setores"])


@router.get("", response_model=List[SetorResumo])
def listar_setores(db: Session = Depends(get_db)):
    """Lista os setores com vagas livres e ocupadas (todos os tipos)."""
    contagem = {
        sid: (livres or 0, ocupadas or 0)
        for sid, livres, ocupadas in db.query(
            Vaga.setor_id,
            func.sum(case((vaga_livre_utilizavel(), 1), else_=0)),
            func.sum(case((Vaga.status == StatusVaga.OCUPADA, 1), else_=0)),
        ).group_by(Vaga.setor_id)
    }

    return [
        SetorResumo(
            id=s.id, nome=s.nome, cor=s.cor, andar=s.andar, bloco=s.bloco,
            capacidade_total=s.capacidade_total,
            vagas_livres=contagem.get(s.id, (0, 0))[0],
            vagas_ocupadas=contagem.get(s.id, (0, 0))[1],
        )
        for s in db.query(Setor).order_by(Setor.id).all()
    ]
