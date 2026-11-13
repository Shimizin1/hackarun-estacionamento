# 05 - Dev Backend (Trilho A): v2.0

Equipe 43 Aerodactyle. Plano seguido: `docs/squad/analise-projeto/04-tech-lead.md`. O frontend (Trilho F) não foi tocado por este trilho.

## Resultado

- pytest: **52 passed** (`python -m pytest -q`, ~7 s, banco temporário).
- Newman: **29 requests, 0 falhas; 58 test-scripts, 109 asserções, 0 falhas**; tempo médio de resposta 14 ms (máx. 105 ms em `GET /`, que serve o HTML).
- Todos os itens D1-D13, D15, D17, D18, D20 tratados. D4 (Python), D19 (pool) e D21 (versionamento) endereçados por A1, README e T0.

## Por tarefa

| ID | Feito | Arquivos |
|---|---|---|
| T0.2 | venv Python 3.13 com os pins do `requirements.txt` | `.venv/` (ignorado) |
| A1 | `CAPIM_DB_URL`; `StaticPool` só para `:memory:` | `app/database.py` |
| A2 | Import de `VagaResponse`; entrada em transação única (reserva `UPDATE` condicional + ticket + 1 commit, rollback em qualquer erro); `ocupar_vaga`/`liberar_vaga(commit=)` | `app/services/ticket_service.py`, `app/services/vaga_service.py` |
| A3 | `calcular_cobranca` pura (microssegundos inteiros, sem erro de ponto flutuante); `registrar_saida(agora=)` | `app/services/ticket_service.py` |
| A4 | `TicketNaoEncontrado` (404), `TicketJaFinalizado` (409), alias `POST /tickets/{id}/saida` | `app/services/ticket_service.py`, `app/routers/tickets.py` |
| A5 | 10 motos no Laranja, `random.Random(43)`, tickets ativos só em `comum`; banco local apagado | `app/seed.py` |
| A6 | `por_setor` com todos os setores e contagens filtradas por tipo/carregador | `app/services/vaga_service.py` |
| A7 | `StaticFiles` em `/` (último mount), info em `/api/info`, Equipe 43, versão 2.0.0 | `app/main.py` |
| A8 | Suíte pytest | `tests/`, `pytest.ini` |
| A9 | Coleção Postman v2.1 + ambiente, validada no Newman | `postman/` |
| A10 | README e CHANGELOG | `README.md`, `CHANGELOG.md` |
| A11 | Distância por bloco/andar (DT8), `excluir_vaga_id` repetível (DT9), `vaga_id` na entrada e proximidade com setor cheio (DT10) | `vaga_service.py`, `ticket_service.py`, `routers/vagas.py`, `routers/tickets.py`, `schemas.py` |
| A12 | `GET /setores` | `app/routers/setores.py`, `app/main.py`, `app/schemas.py` (`SetorResumo`) |
| A13 | Carregador `em_uso`/`disponivel` acompanha a vaga; elétrico só com carregador disponível | `vaga_service.py`, `ticket_service.py` |
| A14 | Placa normalizada antes do `pattern` | `app/schemas.py` |
| Could | `func.case` -> `case` (`/admin/ocupacao` 200); `/vagas/relatos` antes de `/{vaga_id}`; imports no topo em `vagas.py`, `config.py`, `admin_service.py` | idem |
| Extra | `scripts/reset_db.py` e `scripts/run_newman.py` (sobe a API com banco temporário, roda o Newman, encerra) | `scripts/` |

## Decisões e desvios do plano

1. **Entrada sem sugestão duplicada:** a proximidade foi movida para dentro de `_encontrar_vaga` (que agora recebe `vaga_id`), em vez de ficar num ramo separado de `registrar_entrada`. O comportamento segue DT10: `vaga_id` exato (409 se não estiver livre, for de outro tipo ou, na corrida, perdida); setor preferido; setor cheio -> `sugerir_vaga_proxima`; sem setor -> primeira livre do tipo.
2. **409 também para `vaga_id` inexistente** (o contrato diz "não livre ou de outro tipo"; tratamos igual para simplificar a UI).
3. **A13 e a proximidade:** `sugerir_vaga_proxima` também filtra o carregador `DISPONIVEL` quando o tipo é elétrico, para a sugestão e a entrada serem coerentes.
4. **Carregador em `manutencao`** não é alterado por ocupar/liberar (a troca só ocorre entre `disponivel` e `em_uso`).
5. **Banco de testes:** o `conftest.py` faz `drop_db()` + lifespan (seed) por teste, em vez de apagar o arquivo; equivalente ao plano e mais simples no Windows.
6. **Postman:** a coleção usa uma variável de coleção (não de ambiente) para o encadeamento, então o ambiente só tem `baseUrl`. O teste de tempo (< 200 ms) é um teste de nível de coleção aplicado a todos os GETs. A pasta "06 - Cenários de Carga" da doc (Won't) não existe e isso está na descrição da coleção. O atraso de 1,5 s da cobrança é um `setTimeout` no pre-request; a validação real do valor de R$ 10,00 (76 min) fica no pytest.
7. **README:** o README anterior era uma cópia do `DOCUMENTACAO_PROJETO.md`, que continua íntegro; foi substituído pelo README operacional pedido em A10.
8. **Não alterado:** D19 aprofundado (concorrência real), D22 (datas UTC naive, DT12 resolve na UI), `requirements.txt`, CI/infra.

## Como validar

```powershell
py -3.13 -m venv .venv; .venv\Scripts\activate; pip install -r requirements.txt
python -m pytest -q                     # 52 passed
python scripts/run_newman.py            # 29 requests / 109 asserções / 0 falhas
python scripts/reset_db.py; uvicorn app.main:app   # abrir http://localhost:8000/
```

## Pendências

- O `CHANGELOG.md` mantém a seção `### Frontend` vazia para o Trilho F.
- A seção `[2.0.0]` continua "Unreleased" até o fim do hackathon (14/11); não foi criada tag.
- Newman precisa de banco recém-criado; uma segunda execução sobre o mesmo banco falha (ex.: a vaga PCD sugerida já ocupada). `scripts/run_newman.py` evita isso.
- Datas continuam naive em UTC (D22); a UI converte (DT12).
- Fica como dívida após o hackathon: subir os pins para suportar o Python 3.14.

## Ciclo de correção 1

Correções da revisão de código (bloco "Antes da tag"), um commit por item.

| Item | Mudança | Arquivos |
|---|---|---|
| R1 | Entrada tenta até 5 vezes excluindo vagas já disputadas (transação única e UPDATE condicional mantidos); `vaga_id` explícito continua 409. Teste de concorrência exige 10 x 201 e ids distintos | `app/services/ticket_service.py`, `tests/test_qa_criterios.py` |
| R2 | Saída com `UPDATE ... WHERE id=? AND saida IS NULL`; rowcount != 1 vira 409 (`TicketJaFinalizado`); vaga liberada na mesma transação. Teste com 2 threads: um 200 e um 409 | idem |
| R3/BUG-01 | `vaga_livre_utilizavel()` (livre e, se elétrica, carregador `disponivel`) usada em `/vagas/disponiveis` (lista e contadores) e `/setores`; `xfail` removido | `app/services/vaga_service.py`, `app/routers/setores.py` |
| R5 | `run_newman.py` checa porta ocupada, `api.poll()` durante a espera e usa 127.0.0.1 | `scripts/run_newman.py` |
| R8 | README avisa para parar a API; `reset_db.py` trata `PermissionError` | `README.md`, `scripts/reset_db.py` |
| R4 | CORS removido; `python -m app.main` em 127.0.0.1 | `app/main.py` |
| R7/BUG-03 | `mensagem` com hora UTC-3 (deslocamento fixo; Araguaína não tem horário de verão e evita depender de `tzdata` no Windows) | `ticket_service.py` |
| R12, R14 | `import uuid` removido e `SEED` reposicionado; `asyncio_default_fixture_loop_scope = function` | `app/seed.py`, `pytest.ini` |

Validação: `pytest -q` 85 passed (sem xfail); Newman 29 requests / 109 asserções / 0 falhas; testes de concorrência repetidos 5 vezes sem flakiness.

Pós-hackathon: R9 (consulta por placa), R10 (resumo em /vagas/disponiveis), R11, R13, pins Python 3.14, datas com fuso no banco, teste de carga real.
