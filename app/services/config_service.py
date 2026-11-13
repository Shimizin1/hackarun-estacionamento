"""
Configuration service for CapimParking.
Manages system configurations with caching.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Configuracao
from app.schemas import ConfiguracaoPublicResponse


class ConfigService:
    """Service for managing system configurations."""

    # Cache for configs
    _cache: dict[str, str] = {}
    _loaded = False

    @classmethod
    def load_all(cls, db: Session) -> None:
        """Load all configurations into cache."""
        configs = db.query(Configuracao).all()
        cls._cache = {c.chave: c.valor for c in configs}
        cls._loaded = True

    @classmethod
    def get(cls, db: Session, chave: str, default: Optional[str] = None) -> Optional[str]:
        """Get a configuration value."""
        if not cls._loaded:
            cls.load_all(db)
        return cls._cache.get(chave, default)

    @classmethod
    def get_int(cls, db: Session, chave: str, default: int = 0) -> int:
        """Get configuration as integer."""
        val = cls.get(db, chave)
        try:
            return int(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    @classmethod
    def get_float(cls, db: Session, chave: str, default: float = 0.0) -> float:
        """Get configuration as float."""
        val = cls.get(db, chave)
        try:
            return float(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    @classmethod
    def set(cls, db: Session, chave: str, valor: str, descricao: Optional[str] = None) -> Configuracao:
        """Set a configuration value."""
        config = db.query(Configuracao).filter(Configuracao.chave == chave).first()
        if config:
            config.valor = valor
            if descricao:
                config.descricao = descricao
        else:
            config = Configuracao(chave=chave, valor=valor, descricao=descricao)
            db.add(config)
        db.commit()
        db.refresh(config)
        cls._cache[chave] = valor
        return config

    @classmethod
    def get_public_config(cls, db: Session) -> ConfiguracaoPublicResponse:
        """Get public configuration for frontend."""
        return ConfiguracaoPublicResponse(
            tolerancia_minutos=cls.get_int(db, "tolerancia_minutos", 15),
            valor_hora=cls.get_float(db, "valor_hora", 5.0),
            tempo_maximo_recarga_ev=cls.get_int(db, "tempo_maximo_recarga_ev", 120),
            regra_arredondamento=cls.get(db, "regra_arredondamento", "hora_cheia"),
        )

    @classmethod
    def invalidate_cache(cls) -> None:
        """Invalidate configuration cache."""
        cls._cache.clear()
        cls._loaded = False