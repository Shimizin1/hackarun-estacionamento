"""
Seed script for CapimParking database.
Populates database with data from the Capim Dourado Shopping floor plan.
Subsolo 1: 140 vagas | Subsolo 2: 216 vagas | Total: 356 vagas
"""
import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, init_db
SEED = 43  # seed fixo: dados de demonstração reproduzíveis (DT7)

from app.models import (
    Base, Setor, Vaga, Carregador, Ticket, Configuracao, RelatoColaborativo,
    TipoVaga, StatusVaga, StatusCarregador, StatusPagamento, OrigemDado, DEFAULT_CONFIGS
)


def create_setores(db: Session) -> list[Setor]:
    """Create setores based on floor plan."""
    setores_data = [
        # Subsolo 1 - 140 vagas
        {"nome": "Azul", "cor": "#3B82F6", "andar": "Subsolo 1", "bloco": "A", "capacidade_total": 50},
        {"nome": "Verde", "cor": "#22C55E", "andar": "Subsolo 1", "bloco": "B", "capacidade_total": 45},
        {"nome": "Amarelo", "cor": "#EAB308", "andar": "Subsolo 1", "bloco": "C", "capacidade_total": 45},
        # Subsolo 2 - 216 vagas
        {"nome": "Vermelho", "cor": "#EF4444", "andar": "Subsolo 2", "bloco": "A", "capacidade_total": 72},
        {"nome": "Roxo", "cor": "#A855F7", "andar": "Subsolo 2", "bloco": "B", "capacidade_total": 72},
        {"nome": "Laranja", "cor": "#F97316", "andar": "Subsolo 2", "bloco": "C", "capacidade_total": 72},
    ]

    setores = []
    for data in setores_data:
        setor = Setor(
            nome=data["nome"],
            cor=data["cor"],
            andar=data["andar"],
            bloco=data["bloco"],
            capacidade_total=data["capacidade_total"],
            origem_dado=OrigemDado.SIMULADO,
        )
        db.add(setor)
        setores.append(setor)

    db.flush()
    return setores


def create_vagas(db: Session, setores: list[Setor]) -> list[Vaga]:
    """Create vagas based on floor plan specifications."""
    vagas = []
    vaga_counter = 1

    # Special vacancies from floor plan
    # Subsolo 1: 3 PNE, 11 idosos, 2 neurodivergentes, 4 gestantes = 20 especiais
    # Subsolo 2: 5 PNE, 8 idosos, 1 neurodivergente, 4 gestantes = 18 especiais
    # Total special: 38 | Comum: 318

    special_counts = {
        "Azul": {  # Subsolo 1 - Bloco A
            TipoVaga.PCD: 2,
            TipoVaga.IDOSO: 4,
            TipoVaga.NEURODIVERGENTE: 1,
            TipoVaga.GESTANTE: 2,
        },
        "Verde": {  # Subsolo 1 - Bloco B
            TipoVaga.PCD: 1,
            TipoVaga.IDOSO: 4,
            TipoVaga.NEURODIVERGENTE: 1,
            TipoVaga.GESTANTE: 1,
        },
        "Amarelo": {  # Subsolo 1 - Bloco C
            TipoVaga.IDOSO: 3,
            TipoVaga.GESTANTE: 1,
        },
        "Vermelho": {  # Subsolo 2 - Bloco A
            TipoVaga.PCD: 2,
            TipoVaga.IDOSO: 3,
            TipoVaga.NEURODIVERGENTE: 1,
            TipoVaga.GESTANTE: 2,
        },
        "Roxo": {  # Subsolo 2 - Bloco B
            TipoVaga.PCD: 2,
            TipoVaga.IDOSO: 3,
            TipoVaga.GESTANTE: 1,
        },
        "Laranja": {  # Subsolo 2 - Bloco C
            TipoVaga.PCD: 1,
            TipoVaga.IDOSO: 2,
            TipoVaga.GESTANTE: 1,
            TipoVaga.MOTO: 10,  # única área de motos (Subsolo 2, bloco C)
        },
    }

    # EV charger counts per setor (simulated)
    ev_counts = {
        "Azul": 2,
        "Verde": 2,
        "Amarelo": 1,
        "Vermelho": 3,
        "Roxo": 3,
        "Laranja": 2,
    }

    for setor in setores:
        especiais = special_counts.get(setor.nome, {})
        ev_count = ev_counts.get(setor.nome, 0)
        comuns = setor.capacidade_total - sum(especiais.values()) - ev_count

        # Generate coordinates for map positioning (virtual coordinates 0-100%)
        # Distribute in a grid pattern within the sector
        rows = 10
        cols = max(1, (setor.capacidade_total + rows - 1) // rows)

        vaga_num = 0
        for row in range(rows):
            for col in range(cols):
                if vaga_num >= setor.capacidade_total:
                    break

                vaga_num += 1
                letra = chr(ord('A') + (vaga_num - 1) // 20) if vaga_num <= 100 else chr(ord('A') + (vaga_num - 1) // 30)
                numero = f"{letra}-{(vaga_num - 1) % 20 + 1:02d}" if vaga_num <= 100 else f"{letra}-{(vaga_num - 1) % 30 + 1:02d}"

                # Determine tipo
                tipo = TipoVaga.COMUM
                tem_carregador = False

                # Check special types
                for t, count in especiais.items():
                    if count > 0:
                        tipo = t
                        especiais[t] -= 1
                        break
                else:
                    # Check EV
                    if ev_count > 0:
                        tipo = TipoVaga.ELETRICO
                        tem_carregador = True
                        ev_count -= 1

                # Virtual coordinates for map (percentage within sector)
                x = 10 + (col / max(1, cols - 1)) * 80 if cols > 1 else 50
                y = 10 + (row / max(1, rows - 1)) * 80 if rows > 1 else 50

                vaga = Vaga(
                    setor_id=setor.id,
                    numero=numero,
                    tipo=tipo,
                    status=StatusVaga.LIVRE,
                    tem_carregador=tem_carregador,
                    coordenada_x=round(x, 1),
                    coordenada_y=round(y, 1),
                    origem_dado=OrigemDado.SIMULADO,
                )
                db.add(vaga)
                vagas.append(vaga)

    db.flush()
    return vagas


def create_carregadores(db: Session, vagas: list[Vaga]) -> list[Carregador]:
    """Create carregadores for EV vagas."""
    carregadores = []
    for vaga in vagas:
        if vaga.tem_carregador:
            # Alternate between Tipo 2 and CCS2
            tipo = "Tipo 2" if vaga.id % 2 == 0 else "CCS2"
            potencia = 22.0 if tipo == "Tipo 2" else 50.0

            carregador = Carregador(
                vaga_id=vaga.id,
                tipo_conector=tipo,
                potencia_kw=potencia,
                status=StatusCarregador.DISPONIVEL,
                tempo_maximo_minutos=120,
                origem_dado=OrigemDado.SIMULADO,
            )
            db.add(carregador)
            carregadores.append(carregador)

    db.flush()
    return carregadores


def create_configuracoes(db: Session) -> list[Configuracao]:
    """Create default configurations."""
    configs = []
    for chave, (valor, descricao) in DEFAULT_CONFIGS.items():
        config = Configuracao(
            chave=chave,
            valor=valor,
            descricao=descricao,
        )
        db.add(config)
        configs.append(config)

    db.flush()
    return configs


def create_sample_tickets(db: Session, vagas: list[Vaga]) -> list[Ticket]:
    """Create some sample tickets for demo (determinístico; ativos só em vagas comuns)."""
    rng = random.Random(SEED)
    tickets = []

    def novo_id() -> str:
        return f"{rng.getrandbits(32):08X}"

    # Create 10 active tickets (occupied vagas) - só 'comum', para não esgotar tipos especiais
    vagas_livres = [v for v in vagas if v.status == StatusVaga.LIVRE and v.tipo == TipoVaga.COMUM]
    rng.shuffle(vagas_livres)

    for i in range(min(10, len(vagas_livres))):
        vaga = vagas_livres[i]
        vaga.status = StatusVaga.OCUPADA

        entrada = datetime.utcnow() - timedelta(minutes=rng.randint(5, 180))
        ticket = Ticket(
            identificador=novo_id(),
            vaga_id=vaga.id,
            entrada=entrada,
            status_pagamento=StatusPagamento.PENDENTE,
            placa=f"ABC{rng.randint(1000, 9999)}" if rng.random() > 0.3 else None,
            categoria=vaga.tipo,
            tempo_tolerancia_minutos=15,
            valor_hora=5.0,
        )
        db.add(ticket)
        tickets.append(ticket)

    # Create 5 completed tickets (history)
    for i in range(5):
        vaga = rng.choice(vagas)
        entrada = datetime.utcnow() - timedelta(hours=rng.randint(1, 5))
        saida = entrada + timedelta(minutes=rng.randint(10, 240))
        tempo_minutos = (saida - entrada).total_seconds() / 60

        if tempo_minutos <= 15:
            valor = 0.0
            status = StatusPagamento.ISENTO
        else:
            horas = max(1, int((tempo_minutos - 15 + 59) // 60))  # Round up to hour
            valor = round(horas * 5.0, 2)
            status = StatusPagamento.PAGO

        ticket = Ticket(
            identificador=novo_id(),
            vaga_id=vaga.id,
            entrada=entrada,
            saida=saida,
            valor=valor,
            status_pagamento=status,
            placa=f"XYZ{rng.randint(1000, 9999)}" if rng.random() > 0.3 else None,
            categoria=vaga.tipo,
            tempo_tolerancia_minutos=15,
            valor_hora=5.0,
        )
        db.add(ticket)
        tickets.append(ticket)

    db.flush()
    return tickets


def create_sample_relatos(db: Session, setores: list[Setor]) -> list[RelatoColaborativo]:
    """Create sample collaborative reports."""
    rng = random.Random(SEED)
    choice, uniform = rng.choice, rng.uniform
    relatos = []

    for setor in setores:
        for tipo in [TipoVaga.COMUM, TipoVaga.IDOSO, TipoVaga.PCD, TipoVaga.ELETRICO]:
            # 70% chance of having a report
            if uniform(0, 1) < 0.7:
                status = choice([StatusVaga.LIVRE, StatusVaga.OCUPADA])
                relato = RelatoColaborativo(
                    setor_id=setor.id,
                    tipo_vaga=tipo,
                    status_reportado=status,
                    confianca=round(uniform(0.6, 0.9), 2),
                    fonte="usuario",
                    expira_em=datetime.utcnow() + timedelta(minutes=30),
                )
                db.add(relato)
                relatos.append(relato)

    db.flush()
    return relatos


def seed_database() -> None:
    """Main seed function."""
    print("[SEED] Iniciando seed do banco de dados...")

    # Initialize tables
    init_db()

    db = SessionLocal()
    try:
        # Check if already seeded
        existing_setores = db.query(Setor).count()
        if existing_setores > 0:
            print(f"⚠️  Banco já possui {existing_setores} setores. Pulando seed.")
            return

        # Create all data
        print("[SEED] Criando setores...")
        setores = create_setores(db)

        print("[SEED] Criando vagas...")
        vagas = create_vagas(db, setores)

        print("[SEED] Criando carregadores...")
        carregadores = create_carregadores(db, vagas)

        print("[SEED] Criando configurações...")
        configs = create_configuracoes(db)

        print("[SEED] Criando tickets de exemplo...")
        tickets = create_sample_tickets(db, vagas)

        print("[SEED] Criando relatos colaborativos...")
        relatos = create_sample_relatos(db, setores)

        db.commit()

        # Summary
        print("\n[SEED] Seed concluído com sucesso!")
        print(f"  Setores: {len(setores)}")
        print(f"  Vagas: {len(vagas)}")
        print(f"  Carregadores: {len(carregadores)}")
        print(f"  Configurações: {len(configs)}")
        print(f"  Tickets: {len(tickets)}")
        print(f"  Relatos: {len(relatos)}")

        # Count by tipo
        from sqlalchemy import func
        tipo_counts = db.query(Vaga.tipo, func.count(Vaga.id)).group_by(Vaga.tipo).all()
        print("\n  Vagas por tipo:")
        for tipo, count in tipo_counts:
            print(f"    {tipo.value}: {count}")

        # Count by andar
        andar_counts = db.query(Setor.andar, func.count(Vaga.id)).join(Vaga).group_by(Setor.andar).all()
        print("\n  Vagas por andar:")
        for andar, count in andar_counts:
            print(f"    {andar}: {count}")

    except Exception as e:
        db.rollback()
        print(f"❌ Erro no seed: {e}")
        raise
    finally:
        db.close()


def reset_database() -> None:
    """Reset and reseed database."""
    print("[SEED] Resetando banco de dados...")
    from app.database import drop_db
    drop_db()
    seed_database()


if __name__ == "__main__":
    seed_database()