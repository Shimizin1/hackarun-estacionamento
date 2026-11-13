# 🏪 Estacionamento Inteligente - Hackarun 2026

**Equipe 44 - Aerodactyle**  
Guilherme Abreu • Álvaro Franco • Flávio Antônio • Matheus Dassoler

---

## 🚀 Quick Start

```bash
# 1. Clone e entre no diretório
cd hackarun-estacionamento

# 2. Suba com Docker (recomendado)
docker-compose up -d --build

# 3. Acesse a API
# Swagger UI: http://localhost:8000/docs
# ReDoc:      http://localhost:8000/redoc
# Health:     http://localhost:8000/health
```

---

## 📖 Documentação Completa

→ **[DOCUMENTACAO_PROJETO.md](DOCUMENTACAO_PROJETO.md)** - Especificação completa, arquitetura, API, casos de uso, cronograma

---

## 🛠️ Stack

| Camada | Tech |
|--------|------|
| Backend | Python 3.11 + FastAPI |
| DB (dev) | SQLite (arquivo único) |
| DB (prod) | PostgreSQL |
| ORM | SQLAlchemy 2.0 + Alembic |
| API Docs | Swagger UI (auto) |
| Testes | Postman Collection |
| Container | Docker + Compose |

---

## 📁 Estrutura

```
├── app/                 # Código fonte
│   ├── api/v1/         # Endpoints REST
│   ├── core/           # Config, DB
│   ├── models/         # SQLAlchemy Models
│   ├── schemas/        # Pydantic Schemas
│   ├── services/       # Business Logic
│   └── main.py         # Entry point
├── tests/              # Pytest
├── postman/            # Collection Postman
├── alembic/            # Migrations
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## 🧪 Testes com Postman

1. Importe `postman/Hackarun_Estacionamento.postman_collection.json`
2. Environment: `base_url = http://localhost:8000/api/v1`
3. **Run Collection** → veja todos os cenários validados

---

## 🎯 Funcionalidades Core

- ✅ **Passagem rápida** - 15 min grátis
- ✅ **Ticket impresso** - Vaga/Setor/Andar/Tipo
- ✅ **Vagas EV** - Com carregador, monitoramento
- ✅ **Smart Parking** - Vaga por proximidade automática
- ✅ **Acessibilidade total** - WCAG 2.1 AA, TTS, Libras, Alto Contraste
- ✅ **Zero Login** - Praticidade máxima

---

## 👥 Equipe Aerodactyle

| Membro | Foco |
|--------|------|
| Guilherme Abreu | Backend / Arquitetura |
| Álvaro Franco | Fullstack / API |
| Flávio Antônio | Backend / Database |
| Matheus Dassoler | Frontend / UX / Acessibilidade |

---

## 📄 Licença

Projeto educacional - Hackarun 2026