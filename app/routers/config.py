"""
Config router - endpoints for system configuration.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.config_service import ConfigService
from app.schemas import (
    ConfiguracaoCreate, ConfiguracaoUpdate, ConfiguracaoResponse,
    ConfiguracaoPublicResponse,
)
from app.models import Configuracao

router = APIRouter(prefix="/config", tags=["Configuração"])


@router.get("", response_model=ConfiguracaoPublicResponse)
def obter_config_publica(db: Session = Depends(get_db)):
    """
    Obter configurações públicas do sistema.
    Não requer autenticação - usado pelo frontend.
    """
    return ConfigService.get_public_config(db)


@router.get("/admin", response_model=list[ConfiguracaoResponse])
def listar_configuracoes(db: Session = Depends(get_db)):
    """Listar todas as configurações (admin)."""
    return db.query(Configuracao).all()


@router.get("/admin/{chave}", response_model=ConfiguracaoResponse)
def obter_configuracao(chave: str, db: Session = Depends(get_db)):
    """Obter configuração específica (admin)."""
    config = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    return config


@router.post("/admin", response_model=ConfiguracaoResponse, status_code=status.HTTP_201_CREATED)
def criar_configuracao(config: ConfiguracaoCreate, db: Session = Depends(get_db)):
    """Criar nova configuração (admin)."""
    existing = db.query(Configuracao).filter(Configuracao.chave == config.chave).first()
    if existing:
        raise HTTPException(status_code=400, detail="Configuração já existe")
    return ConfigService.set(db, config.chave, config.valor, config.descricao)


@router.patch("/admin/{chave}", response_model=ConfiguracaoResponse)
def atualizar_configuracao(chave: str, config_update: ConfiguracaoUpdate, db: Session = Depends(get_db)):
    """Atualizar configuração (admin)."""
    config = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")

    update_data = config_update.model_dump(exclude_unset=True)
    if "valor" in update_data:
        config.valor = update_data["valor"]
    if "descricao" in update_data:
        config.descricao = update_data["descricao"]

    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    ConfigService.invalidate_cache()
    return config


# Add datetime import
from datetime import datetime