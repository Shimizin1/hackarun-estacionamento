# 07 - DevOps (v2.0)

## O que foi feito
- `.github/workflows/ci.yml`: jobs `testes` (pytest, Python 3.13, cache pip), `postman` (setup-node 22 + `scripts/run_newman.py`, artefato `newman-report`) e `docker` (build + smoke `/health` e `/`). Gatilho: push e PR na `main`.
- `scripts/run_newman.py`: variável opcional `NEWMAN_JSON` exporta o relatório JSON. O script já era portável (usa `sys.executable`, `shutil.which("npx")`, caminhos `pathlib`).
- `Dockerfile` (python:3.13-slim, uid 1000 não-root, `0.0.0.0:8000`), `.dockerignore`, `docker-compose.yml` (volume nomeado `capim-data` em `/srv/data`).
- README: badge de CI e seções Docker e CI. CHANGELOG: `[2.0.0] - 2026-11-13` com seção Infraestrutura. Tag NAO criada.

## Como rodar
- Local: `uvicorn app.main:app --reload` (Python 3.13).
- Docker: `docker compose up --build` e abrir `http://localhost:8000/`; zerar banco: `docker compose down -v`.
- CI: automático no push/PR.

## Testado de fato
- `python -m pytest -q`: 85 passed (local, Windows).
- `python scripts/run_newman.py 8011` com `NEWMAN_JSON`: 29 requests, 109 assertions, 0 falhas; relatório gerado.
## NAO testado
- Docker: o cliente existe (29.4.0) mas o daemon (Docker Desktop) estava parado; `docker build`/`run` NAO foram executados. Dockerfile validado só por leitura. O job `docker` do CI fará o primeiro build real.
- O workflow não foi executado no GitHub (só validado por leitura); conferir a aba Actions após o push. Sem `gh` CLI para consultar.
- Execução em Linux não testada localmente (leitura indica compatibilidade).

## Checklist de release
- [ ] Veredito do QA aprovado e CI verde na `main`.
- [ ] Python 3.13 no ambiente da demo.
- [ ] Parar a API e rodar `python scripts/reset_db.py` (ou `docker compose down -v`) antes da demo; subir e conferir 356 vagas e `/health`.
- [ ] Coordenador cria a tag `v2.0` (não criada pelo DevOps).

## Pendências pós-hackathon
- Pinar imagens/Actions por digest/SHA e adicionar lint (ruff).
- Healthcheck no Dockerfile/compose; publicar imagem em registry; deploy.
- Suportar Python 3.14 (atualizar pins).
- Commits `ci:` e `build:` ficaram sem linha em branco antes do `Co-Authored-By` (já enviados; sem force push).
