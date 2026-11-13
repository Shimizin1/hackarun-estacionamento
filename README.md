# CapimParking - Estacionamento Inteligente

[![CI](https://github.com/Shimizin1/hackarun-estacionamento/actions/workflows/ci.yml/badge.svg)](https://github.com/Shimizin1/hackarun-estacionamento/actions/workflows/ci.yml)

Hackarun 2026 | **Equipe 43 - Aerodactyle** | versão 2.0.0

Guilherme Abreu, Álvaro Franco, Flávio Antônio, Matheus Dassoler.

Sistema de estacionamento para o Capim Dourado Shopping: entrada e saída **sem login**, tolerância de 15 minutos sem cobrança, vagas por categoria (comum, idoso, PCD, neurodivergente, elétrico, moto, gestante), sugestão de vaga por proximidade quando o setor está cheio e interface única e acessível.

A especificação completa (fonte da verdade) está em [DOCUMENTACAO_PROJETO.md](DOCUMENTACAO_PROJETO.md). O histórico de mudanças está em [CHANGELOG.md](CHANGELOG.md).

## Stack

- Backend: Python + FastAPI 0.115, SQLAlchemy 2.0, Pydantic 2.10, SQLite
- Frontend: HTML, CSS e JavaScript estáticos (`frontend/`), servidos pela própria API
- Testes: pytest (`tests/`) e coleção Postman/Newman (`postman/`)

## Estrutura de pastas

```
app/                 Backend FastAPI
  main.py            App, rotas de sistema e montagem do frontend em "/"
  database.py        Engine SQLite (CAPIM_DB_URL)
  models.py          Modelos ORM
  schemas.py         Schemas Pydantic (requests/responses)
  seed.py            Dados de demonstração (determinístico)
  routers/           Camada HTTP (vagas, tickets, setores, config, admin)
  services/          Regras de negócio (cobrança, proximidade, ocupação)
frontend/            Interface (index.html, styles.css, app.js)
tests/               Testes pytest (banco temporário, nunca usa data/)
postman/             Coleção Postman v2.1 + ambiente local
scripts/             Utilitários (reset do banco, execução do Newman)
data/                Banco SQLite local (ignorado pelo git, recriado no startup)
docs/squad/          Artefatos do squad (PM, PO, Design, Tech Lead, Dev, QA)
```

## Como rodar

Requisito: **Python 3.11 a 3.13** (os pins do `requirements.txt` não instalam no Python 3.14).

```powershell
# 1. ambiente virtual (Windows)
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 2. subir a API (cria as tabelas e o seed no primeiro start)
uvicorn app.main:app --reload
```

Linux/macOS: `python3.13 -m venv .venv && source .venv/bin/activate`.

Depois abra:

- `http://localhost:8000/` - interface (frontend)
- `http://localhost:8000/docs` - Swagger da API
- `http://localhost:8000/api/info` - informações da API (a raiz `/` serve o frontend)

## Reiniciar o banco

**Pare a API (Ctrl+C) antes**: no Windows o arquivo do banco fica travado enquanto ela roda.

O seed só roda quando o banco está vazio. Para voltar ao estado inicial (356 vagas, 10 tickets de exemplo):

```powershell
python scripts/reset_db.py
uvicorn app.main:app --reload
```

Para usar outro arquivo de banco, defina `CAPIM_DB_URL` (ex.: `sqlite:///C:/temp/teste.db`).

## Testes

```powershell
python -m pytest -q
```

Os testes usam um banco temporário (via `CAPIM_DB_URL`) e recriam o seed a cada teste; o `data/` nunca é tocado.

## Postman

Arquivos em `postman/`:

- `hackarun-estacionamento.postman_collection.json`
- `local.postman_environment.json` (variável `baseUrl`, padrão `http://localhost:8000`)

**No app do Postman:** importe os dois arquivos, selecione o ambiente "Local" e rode a coleção no Collection Runner **em sequência**. Pré-condição: banco recém-criado (`python scripts/reset_db.py` e subir a API), pois as requisições encadeiam variáveis (`ticketId`, `vagaSugerida`...) e consomem vagas.

**Pelo Newman (linha de comando, requer Node.js):**

```powershell
# automático: sobe a API com banco temporário novo, roda a coleção e encerra
python scripts/run_newman.py

# ou manual, com a API já rodando em banco novo
npx -y newman run postman/hackarun-estacionamento.postman_collection.json -e postman/local.postman_environment.json
```

O Newman não é dependência do projeto (usa `npx`).

## Docker

Requer Docker. A imagem usa `python:3.13-slim`, roda como usuário não-root e escuta em `0.0.0.0:8000` dentro do container.

```bash
# com compose (banco persiste no volume "capim-data")
docker compose up --build

# ou direto
docker build -t capimparking .
docker run --rm -p 8000:8000 capimparking
```

Abra `http://localhost:8000/`. Para zerar o banco do compose: `docker compose down -v`. Para usar uma pasta local no lugar do volume: `-v ./data:/srv/data` (a pasta precisa aceitar escrita pelo uid 1000).

## CI

O workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) roda em push e pull request na `main`: `pytest` (Python 3.13), coleção Postman via `python scripts/run_newman.py` (relatório JSON publicado como artefato `newman-report`) e `docker build` com smoke test de `/health` e `/`.

## Documentação do squad

Análise e plano da v2.0 em [docs/squad/analise-projeto](docs/squad/analise-projeto) (diagnóstico D1-D22, decisões DT1-DT15, contratos de API) e registro do que foi implementado em [docs/squad/v2-0](docs/squad/v2-0).
