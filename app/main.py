"""
CapimParking - Main FastAPI Application.
Sistema de Estacionamento Inteligente para Capim Dourado Shopping.
Hackarun 2026 | Equipe 43 - Aerodactyle
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import get_db, init_db, lifespan as db_lifespan
from app.routers import vagas, tickets, config, admin
from app.services.config_service import ConfigService
from app.seed import seed_database
from app.models import Configuracao


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Initialize database
    init_db()

    # Seed database with demo data
    db = next(get_db())
    try:
        # Check if configs exist, if not seed
        config_count = db.query(Configuracao).count()
        if config_count == 0:
            seed_database()
        else:
            # Load configs into cache
            ConfigService.load_all(db)
    finally:
        db.close()

    yield

    # Cleanup (if needed)


app = FastAPI(
    title="CapimParking API",
    description="""
    ## Sistema de Estacionamento Inteligente - Capim Dourado Shopping

    API para gerenciamento de estacionamento com:
    - **Entrada/Saída sem login** - Fluxo direto para visitantes
    - **Tolerância de 15 min** - Passagem rápida gratuita
    - **Vagas por categoria** - Comum, Idoso, PCD, Neurodivergente, Elétrico, Moto, Gestante
    - **Algoritmo de proximidade** - Sugere vaga mais próxima quando setor cheio
    - **Carregadores EV** - Gestão de vagas com carregadores Tipo 2/CCS2
    - **Relatos colaborativos** - Estimativa de disponibilidade em tempo real
    - **Painel administrativo** - Métricas de ocupação, tickets e receita

    ### Hackarun 2026 | Equipe 43 - Aerodactyle
    **Integrantes:** Guilherme Abreu · Álvaro Franco · Flávio Antônio · Matheus Dassoler
    """,
    version="2.0.0",
    contact={
        "name": "Equipe 43 - Aerodactyle",
        "email": "hackarun2026@aerodactyle.dev",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS configuration for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


# Include routers
app.include_router(vagas.router)
app.include_router(tickets.router)
app.include_router(config.router)
app.include_router(admin.router)


# Health check endpoint
@app.get("/health", tags=["Sistema"], summary="Health check")
async def health_check(db: Session = Depends(get_db)):
    """
    Verifica saúde do sistema e conectividade com banco de dados.
    """
    try:
        # Test database connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        "database": db_status,
        "version": "2.0.0",
        "service": "CapimParking",
    }


# Root endpoint
@app.get("/api/info", tags=["Sistema"], summary="Informações da API")
async def root():
    """
    Informações básicas da API (a raiz "/" serve o frontend).
    """
    return {
        "service": "CapimParking",
        "description": "Sistema de Estacionamento Inteligente - Capim Dourado Shopping",
        "version": "2.0.0",
        "event": "Hackarun 2026",
        "team": "Equipe 43 - Aerodactyle",
        "members": [
            "Guilherme Abreu",
            "Álvaro Franco",
            "Flávio Antônio",
            "Matheus Dassoler",
        ],
        "docs": "/docs",
        "health": "/health",
        "config": "/config",
    }


# Frontend estático servido pela própria API (mesma origem, sem CORS) - DT5.
# Deve ser o ÚLTIMO mount/rota: "/" captura o que nenhuma rota da API atendeu.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# Run directly with: python -m app.main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)