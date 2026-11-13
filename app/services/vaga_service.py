"""
Vaga service for CapimParking.
Handles availability, proximity recommendations, and occupancy logic.
"""
import math
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from app.models import (
    Vaga, Setor, Carregador, RelatoColaborativo,
    TipoVaga, StatusVaga, StatusCarregador, OrigemDado
)
from app.schemas import (
    VagaResponse, VagaSugeridaResponse, VagasDisponiveisResponse,
    VagasPorSetor, VagasDisponiveisRequest
)
from app.services.config_service import ConfigService


class VagaService:
    """Service for managing parking spots and availability."""

    # Virtual coordinate scale: 1 unit = ~1 meter for distance calculation
    COORD_SCALE = 1.0

    @classmethod
    def get_vagas_disponiveis(
        cls,
        db: Session,
        request: VagasDisponiveisRequest
    ) -> VagasDisponiveisResponse:
        """Get available spots with filters."""
        query = db.query(Vaga).options(
            joinedload(Vaga.setor),
            joinedload(Vaga.carregador)
        ).filter(Vaga.status == StatusVaga.LIVRE)

        # Apply filters
        if request.tipo:
            query = query.filter(Vaga.tipo == request.tipo)
        if request.setor_id:
            query = query.filter(Vaga.setor_id == request.setor_id)
        if request.andar:
            query = query.join(Setor).filter(Setor.andar == request.andar)
        if request.apenas_com_carregador:
            query = query.filter(Vaga.tem_carregador == True)

        vagas = query.all()

        # Group by setor
        por_setor = {}
        for vaga in vagas:
            setor_id = vaga.setor_id
            if setor_id not in por_setor:
                por_setor[setor_id] = {
                    "setor": vaga.setor,
                    "livres": 0,
                    "ocupadas": 0,
                    "total": 0,
                }
            por_setor[setor_id]["livres"] += 1

        # Get totals per setor
        for setor_id, data in por_setor.items():
            total = db.query(func.count(Vaga.id)).filter(Vaga.setor_id == setor_id).scalar()
            ocupadas = db.query(func.count(Vaga.id)).filter(
                and_(Vaga.setor_id == setor_id, Vaga.status == StatusVaga.OCUPADA)
            ).scalar()
            data["total"] = total
            data["ocupadas"] = ocupadas

        vagas_por_setor = [
            VagasPorSetor(
                setor_id=sid,
                setor_nome=data["setor"].nome,
                setor_cor=data["setor"].cor,
                andar=data["setor"].andar,
                livres=data["livres"],
                ocupadas=data["ocupadas"],
                total=data["total"],
            )
            for sid, data in por_setor.items()
        ]

        # Determine reliability level
        # For now, all simulated
        nivel = "simulado"

        return VagasDisponiveisResponse(
            vagas=[VagaResponse.model_validate(v) for v in vagas],
            total=len(vagas),
            por_setor=vagas_por_setor,
            nivel_confiabilidade=nivel,
            atualizado_em=datetime.utcnow(),
        )

    @classmethod
    def sugerir_vaga_proxima(
        cls,
        db: Session,
        setor_desejado_id: int,
        tipo_vaga: TipoVaga,
        excluir_vaga_id: Optional[int] = None
    ) -> Optional[VagaSugeridaResponse]:
        """
        Find the closest available spot of the requested type.
        Uses Euclidean distance on virtual coordinates.
        """
        # Get desired sector
        setor_desejado = db.query(Setor).filter(Setor.id == setor_desejado_id).first()
        if not setor_desejado:
            return None

        # Query available spots of the same type
        query = db.query(Vaga).options(
            joinedload(Vaga.setor),
            joinedload(Vaga.carregador)
        ).filter(
            and_(
                Vaga.tipo == tipo_vaga,
                Vaga.status == StatusVaga.LIVRE,
            )
        )

        if excluir_vaga_id:
            query = query.filter(Vaga.id != excluir_vaga_id)

        vagas_candidatas = query.all()

        if not vagas_candidatas:
            return None

        # Calculate distances and find closest
        melhor_vaga = None
        menor_distancia = float('inf')

        for vaga in vagas_candidatas:
            if vaga.coordenada_x is None or vaga.coordenada_y is None:
                continue

            # For cross-sector distance, we need a reference point
            # Use sector center as reference (50, 50) for desired sector
            # and vaga's coordinates for candidate
            dist = cls._calcular_distancia_setores(
                setor_desejado, vaga.setor,
                (50.0, 50.0),  # center of desired sector
                (vaga.coordenada_x, vaga.coordenada_y)
            )

            if dist < menor_distancia:
                menor_distancia = dist
                melhor_vaga = vaga

        if not melhor_vaga:
            return None

        mesmo_andar = melhor_vaga.setor.andar == setor_desejado.andar
        motivo = cls._gerar_motivo(setor_desejado, melhor_vaga.setor, mesmo_andar, tipo_vaga)

        return VagaSugeridaResponse(
            vaga=VagaResponse.model_validate(melhor_vaga),
            distancia_metros=round(menor_distancia * cls.COORD_SCALE, 1),
            tempo_caminhada_minutos=max(1, round(menor_distancia * cls.COORD_SCALE / 80)),  # ~80m/min walking
            mesmo_andar=mesmo_andar,
            motivo=motivo,
        )

    @classmethod
    def _calcular_distancia_setores(
        cls,
        setor_origem: Setor,
        setor_destino: Setor,
        coord_origem: Tuple[float, float],
        coord_destino: Tuple[float, float]
    ) -> float:
        """
        Calculate distance between sectors.
        If same sector: direct Euclidean distance.
        If different sector same floor: add sector-to-sector base distance.
        If different floor: add floor transition penalty.
        """
        x1, y1 = coord_origem
        x2, y2 = coord_destino

        # Base Euclidean distance within coordinate system (0-100 scale)
        dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # If different sectors, add inter-sector distance
        if setor_origem.id != setor_destino.id:
            # Base distance between sector centers (arbitrary units)
            dist += 30.0  # ~30 units between sector centers

            # If different floors, add floor transition penalty
            if setor_origem.andar != setor_destino.andar:
                dist += 50.0  # ~50 units for ramp/elevator

        return dist

    @classmethod
    def _gerar_motivo(
        cls,
        setor_desejado: Setor,
        setor_sugerido: Setor,
        mesmo_andar: bool,
        tipo_vaga: TipoVaga
    ) -> str:
        """Generate human-readable reason for recommendation."""
        if setor_desejado.id == setor_sugerido.id:
            return f"Vaga {tipo_vaga.value} disponível no setor {setor_desejado.nome} ({setor_desejado.andar})"

        if mesmo_andar:
            return (
                f"Setor {setor_desejado.nome} sem vagas {tipo_vaga.value}. "
                f"Vaga mais próxima no setor {setor_sugerido.nome} (mesmo andar: {setor_sugerido.andar})"
            )
        else:
            return (
                f"Setor {setor_desejado.nome} sem vagas {tipo_vaga.value}. "
                f"Vaga mais próxima no setor {setor_sugerido.nome} ({setor_sugerido.andar}), "
                f"acesso por rampa/elevador"
            )

    @classmethod
    def ocupar_vaga(cls, db: Session, vaga_id: int) -> Optional[Vaga]:
        """Mark a spot as occupied."""
        vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
        if vaga and vaga.status == StatusVaga.LIVRE:
            vaga.status = StatusVaga.OCUPADA
            vaga.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(vaga)
            return vaga
        return None

    @classmethod
    def liberar_vaga(cls, db: Session, vaga_id: int) -> Optional[Vaga]:
        """Mark a spot as free."""
        vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
        if vaga and vaga.status == StatusVaga.OCUPADA:
            vaga.status = StatusVaga.LIVRE
            vaga.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(vaga)
            return vaga
        return None

    @classmethod
    def get_vaga_by_id(cls, db: Session, vaga_id: int) -> Optional[Vaga]:
        """Get vaga by ID with relationships."""
        return db.query(Vaga).options(
            joinedload(Vaga.setor),
            joinedload(Vaga.carregador)
        ).filter(Vaga.id == vaga_id).first()

    @classmethod
    def get_ocupacao_por_setor(cls, db: Session) -> List[dict]:
        """Get occupancy stats per sector."""
        result = db.query(
            Setor.id,
            Setor.nome,
            Setor.cor,
            Setor.andar,
            func.count(Vaga.id).label("total"),
            func.sum(func.case((Vaga.status == StatusVaga.LIVRE, 1), else_=0)).label("livres"),
            func.sum(func.case((Vaga.status == StatusVaga.OCUPADA, 1), else_=0)).label("ocupadas"),
            func.sum(func.case((Vaga.status == StatusVaga.MANUTENCAO, 1), else_=0)).label("manutencao"),
        ).join(Vaga).group_by(Setor.id).all()

        return [
            {
                "setor_id": r.id,
                "setor_nome": r.nome,
                "setor_cor": r.cor,
                "andar": r.andar,
                "total": r.total,
                "livres": r.livres or 0,
                "ocupadas": r.ocupadas or 0,
                "manutencao": r.manutencao or 0,
                "taxa_ocupacao": round((r.ocupadas or 0) / r.total * 100, 1) if r.total > 0 else 0,
            }
            for r in result
        ]

    @classmethod
    def get_ocupacao_por_tipo(cls, db: Session) -> List[dict]:
        """Get occupancy stats by spot type."""
        result = db.query(
            Vaga.tipo,
            func.count(Vaga.id).label("total"),
            func.sum(func.case((Vaga.status == StatusVaga.LIVRE, 1), else_=0)).label("livres"),
            func.sum(func.case((Vaga.status == StatusVaga.OCUPADA, 1), else_=0)).label("ocupadas"),
        ).group_by(Vaga.tipo).all()

        return [
            {
                "tipo": r.tipo.value,
                "total": r.total,
                "livres": r.livres or 0,
                "ocupadas": r.ocupadas or 0,
                "taxa_ocupacao": round((r.ocupadas or 0) / r.total * 100, 1) if r.total > 0 else 0,
            }
            for r in result
        ]

    @classmethod
    def registrar_relato_colaborativo(
        cls,
        db: Session,
        setor_id: int,
        tipo_vaga: TipoVaga,
        status: StatusVaga,
        confianca: float = 0.5,
        fonte: str = "usuario"
    ) -> RelatoColaborativo:
        """Register a collaborative availability report."""
        expiracao_min = ConfigService.get_int(db, "expiracao_relato_minutos", 30)

        relato = RelatoColaborativo(
            setor_id=setor_id,
            tipo_vaga=tipo_vaga,
            status_reportado=status,
            confianca=confianca,
            fonte=fonte,
            expira_em=datetime.utcnow() + timedelta(minutes=expiracao_min),
        )
        db.add(relato)
        db.commit()
        db.refresh(relato)
        return relato

    @classmethod
    def get_relatos_ativos(cls, db: Session, setor_id: Optional[int] = None) -> List[RelatoColaborativo]:
        """Get active (non-expired) collaborative reports."""
        query = db.query(RelatoColaborativo).filter(
            RelatoColaborativo.expira_em > datetime.utcnow()
        )
        if setor_id:
            query = query.filter(RelatoColaborativo.setor_id == setor_id)
        return query.order_by(RelatoColaborativo.created_at.desc()).all()

    @classmethod
    def limpar_relatos_expirados(cls, db: Session) -> int:
        """Remove expired reports."""
        result = db.query(RelatoColaborativo).filter(
            RelatoColaborativo.expira_em <= datetime.utcnow()
        ).delete()
        db.commit()
        return result