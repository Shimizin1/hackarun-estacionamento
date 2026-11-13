"""
Vagas router - endpoints for parking spot management.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.vaga_service import VagaService
from app.schemas import (
    VagaResponse, VagaCreate, VagaUpdate,
    VagasDisponiveisRequest, VagasDisponiveisResponse,
    VagaSugeridaResponse, VagaProximidadeRequest,
    CarregadorResponse, CarregadorCreate, CarregadorUpdate,
    RelatoColaborativoRequest, RelatoColaborativoResponse,
)
from app.models import TipoVaga, StatusVaga, Vaga as VagaModel

router = APIRouter(prefix="/vagas", tags=["Vagas"])


@router.get("/disponiveis", response_model=VagasDisponiveisResponse)
def listar_vagas_disponiveis(
    tipo: Optional[TipoVaga] = Query(None, description="Filtrar por tipo de vaga"),
    setor_id: Optional[int] = Query(None, gt=0, description="Filtrar por setor"),
    andar: Optional[str] = Query(None, description="Filtrar por andar"),
    apenas_com_carregador: bool = Query(False, description="Apenas vagas com carregador EV"),
    db: Session = Depends(get_db),
):
    """
    Listar vagas livres com filtros opcionais.
    Retorna vagas disponíveis agrupadas por setor.
    """
    request = VagasDisponiveisRequest(
        tipo=tipo,
        setor_id=setor_id,
        andar=andar,
        apenas_com_carregador=apenas_com_carregador,
    )
    return VagaService.get_vagas_disponiveis(db, request)


@router.get("/proximas", response_model=VagaSugeridaResponse)
def sugerir_vaga_proxima(
    setor_desejado_id: int = Query(..., gt=0, description="ID do setor desejado"),
    tipo_vaga: TipoVaga = Query(..., description="Tipo de vaga necessário"),
    excluir_vaga_id: Optional[List[int]] = Query(None, description="Vagas a excluir (repita o parâmetro)"),
    db: Session = Depends(get_db),
):
    """
    Sugerir vaga mais próxima quando setor desejado está cheio.
    Usa algoritmo de proximidade baseado em coordenadas virtuais.
    """
    sugestao = VagaService.sugerir_vaga_proxima(
        db, setor_desejado_id, tipo_vaga, excluir_vaga_id or None
    )
    if not sugestao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhuma vaga {tipo_vaga.value} disponível em todo o estacionamento"
        )
    return sugestao


# Relatos colaborativos
@router.post("/relatos", response_model=RelatoColaborativoResponse, status_code=status.HTTP_201_CREATED)
def criar_relato(relato: RelatoColaborativoRequest, db: Session = Depends(get_db)):
    """Registrar relato colaborativo de disponibilidade."""
    relato_obj = VagaService.registrar_relato_colaborativo(
        db,
        setor_id=relato.setor_id,
        tipo_vaga=relato.tipo_vaga,
        status=relato.status,
        confianca=relato.confianca,
    )
    return RelatoColaborativoResponse.model_validate(relato_obj)


@router.get("/relatos", response_model=List[RelatoColaborativoResponse])
def listar_relatos(
    setor_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
):
    """Listar relatos colaborativos ativos."""
    relatos = VagaService.get_relatos_ativos(db, setor_id)
    return [RelatoColaborativoResponse.model_validate(r) for r in relatos]


@router.get("/{vaga_id}", response_model=VagaResponse)
def obter_vaga(vaga_id: int, db: Session = Depends(get_db)):
    """Obter detalhes de uma vaga específica."""
    vaga = VagaService.get_vaga_by_id(db, vaga_id)
    if not vaga:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaga não encontrada"
        )
    return VagaResponse.model_validate(vaga)


@router.post("", response_model=VagaResponse, status_code=status.HTTP_201_CREATED)
def criar_vaga(vaga: VagaCreate, db: Session = Depends(get_db)):
    """Criar nova vaga (admin)."""
    from app.models import Vaga as VagaModel
    nova_vaga = VagaModel(**vaga.model_dump())
    db.add(nova_vaga)
    db.commit()
    db.refresh(nova_vaga)
    return VagaResponse.model_validate(nova_vaga)


@router.patch("/{vaga_id}", response_model=VagaResponse)
def atualizar_vaga(vaga_id: int, vaga_update: VagaUpdate, db: Session = Depends(get_db)):
    """Atualizar vaga (admin)."""
    vaga = db.query(VagaModel).filter(VagaModel.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    update_data = vaga_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vaga, field, value)

    vaga.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(vaga)
    return VagaResponse.model_validate(vaga)


@router.delete("/{vaga_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_vaga(vaga_id: int, db: Session = Depends(get_db)):
    """Deletar vaga (admin)."""
    vaga = db.query(VagaModel).filter(VagaModel.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    db.delete(vaga)
    db.commit()


# Carregador endpoints
@router.post("/{vaga_id}/carregador", response_model=CarregadorResponse, status_code=status.HTTP_201_CREATED)
def criar_carregador(vaga_id: int, carregador: CarregadorCreate, db: Session = Depends(get_db)):
    """Adicionar carregador a uma vaga (admin)."""
    from app.models import Carregador as CarregadorModel, Vaga as VagaModel

    vaga = db.query(VagaModel).filter(VagaModel.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    if vaga.tem_carregador:
        raise HTTPException(status_code=400, detail="Vaga já possui carregador")

    carregador_data = carregador.model_dump()
    carregador_data["vaga_id"] = vaga_id
    novo_carregador = CarregadorModel(**carregador_data)
    db.add(novo_carregador)

    # Update vaga
    vaga.tem_carregador = True
    vaga.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(novo_carregador)
    return CarregadorResponse.model_validate(novo_carregador)


@router.patch("/carregador/{carregador_id}", response_model=CarregadorResponse)
def atualizar_carregador(carregador_id: int, carregador_update: CarregadorUpdate, db: Session = Depends(get_db)):
    """Atualizar carregador (admin)."""
    from app.models import Carregador as CarregadorModel

    carregador = db.query(CarregadorModel).filter(CarregadorModel.id == carregador_id).first()
    if not carregador:
        raise HTTPException(status_code=404, detail="Carregador não encontrado")

    update_data = carregador_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(carregador, field, value)

    carregador.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(carregador)
    return CarregadorResponse.model_validate(carregador)
