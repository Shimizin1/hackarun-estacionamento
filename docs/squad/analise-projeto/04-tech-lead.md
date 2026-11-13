# 04 - Tech Lead: Plano técnico (Hackarun 2026, Equipe 43 Aerodactyle)

Rodada: SOMENTE ANÁLISE. Nenhum arquivo do repositório nem o banco `data/` foram alterados. As hipóteses foram validadas executando uma **cópia** do projeto e do `.db` no scratchpad, com um venv Python 3.13 e as versões exatas do `requirements.txt`, usando `fastapi.testclient`.
Fonte da verdade: `Downloads\DOCUMENTACAO_PROJETO.md`. Prazo: hoje 13/11, entrega 14/11 (~1 dia).
Entradas: `01-pm.md` (a Nota do Coordenador prevalece), `02-po.md` e `03-design.md`.

Convenção: linhas citadas como `arquivo:linha` referem-se ao estado atual do repositório.

---

## 1. Diagnóstico confirmado

Severidade: CRÍTICO (bloqueia a demo), ALTO (quebra um Must), MÉDIO (Must incorreto ou risco de demo), BAIXO.

| # | Achado | Veredito | Evidência | Sev. |
|---|---|---|---|---|
| D1 | `VagaResponse` não é importado em `ticket_service.py`, então a entrada retorna 500 | **CONFIRMADO** | `NameError: name 'VagaResponse' is not defined @ app/services/ticket_service.py:88`. `POST /tickets/entrada` retorna 500. | CRÍTICO |
| D2 | A entrada não é atômica: depois do 500, a vaga fica presa e sobra um ticket órfão | **CONFIRMADO** | Commit da vaga em `vaga_service.py:231` (`ocupar_vaga`) e commit do ticket em `ticket_service.py:77`, separados. Após o 500: tickets ativos 10→11, vaga 12 em `OCUPADA`, livres "comum" 296→295. | CRÍTICO |
| D3 | O frontend não funciona: `app.js` não existe e a API não serve o `frontend/` | **CONFIRMADO** | `frontend/index.html:371` tem `<script src="app.js">`, mas o arquivo não existe. `main.py` não monta `StaticFiles`: `GET /frontend/index.html` retorna 404 e `GET /app.js` retorna 404. | CRÍTICO |
| D4 | **(novo)** O `requirements.txt` não instala no Python padrão da máquina (3.14) | **CONFIRMADO** | `pip install --only-binary=:all: -r requirements.txt` no 3.14 falha com `No matching distribution found for pydantic-core==2.27.0`. No **Python 3.13** (`py -3.13`, já instalado) tudo instala e roda. | ALTO |
| D5 | O seed não cria vagas de moto | **CONFIRMADO** | No `.db` não há linha `MOTO`. `GET /vagas/disponiveis?tipo=moto` retorna `total=0` e a entrada "moto" retorna 400. Em `seed.py:56-89` não há `TipoVaga.MOTO`. | ALTO |
| D6 | Os minutos são truncados na saída (tolerância e cobrança) | **CONFIRMADO** | `ticket_service.py:124` usa `int(seconds/60)`. Medido: de 15min01s a 15min59s fica **isento**, e 75min59s cobra R$ 5,00 (pela regra do PO deveria cobrar R$ 10,00). Com tolerância 0, 1,2 s de permanência também fica isento, o que impede o Postman de demonstrar a cobrança. | MÉDIO |
| D7 | `/vagas/disponiveis` omite setor sem vaga livre, e **(novo)** `total`/`ocupadas` por setor ignoram o filtro de tipo | **CONFIRMADO** | `vaga_service.py:52-62` agrupa só as vagas livres, e `:66-69` conta o total e as ocupadas de **todos** os tipos. `?tipo=pcd` não traz o Amarelo. `?tipo=comum` traz o Azul com `livres=38, ocupadas=1, total=50`, e 38+1≠50. Os contadores do Designer (livres+ocupadas) ficam errados. | MÉDIO |
| D8 | A proximidade usa uma referência fixa (50,50) | **CONFIRMADO, com ajuste** | Os setores não são todos equivalentes: há +30 para setor diferente (`vaga_service.py:192`) e +50 para andar diferente (`:196`). Mas a distância entre setores é a mesma para qualquer par e mistura coordenadas locais de setores distintos (`:147`). Medido: Amarelo (bloco C) com PCD sugere **Azul (bloco A)**, e não Verde (bloco B, vizinho). | MÉDIO |
| D9 | **(novo)** "Outra opção" entra em loop | **CONFIRMADO** | `excluir_vaga_id` exclui só uma vaga (`vaga_service.py:126-127`). Recusas seguidas alternam Azul A-02 → A-01 → A-02 → A-01. O UC02 ("mostra próxima opção") fica quebrado. | MÉDIO |
| D10 | **(novo)** A entrada com setor cheio não usa a proximidade | **CONFIRMADO (leitura)** | `_encontrar_vaga` cai em `query.first()` de qualquer setor (`ticket_service.py:230-231`), que devolve a vaga de menor id (normalmente no Azul). O ramo de proximidade (`:45-52`) só roda quando não existe vaga do tipo em lugar nenhum, e aí também não acha. Na prática é código morto. | MÉDIO |
| D11 | `func.case` em `/admin/ocupacao` | **CONFIRMADO** | `TypeError: Function.__init__() got an unexpected keyword argument 'else_'` (`vaga_service.py:265-267, 291-292`). **Refuta** a extensão a `/admin/metricas`: ele responde 200, porque `admin_service.py` usa `case` importado corretamente. Admin é Could. | BAIXO |
| D12 | PATCH/DELETE em `vagas.py` com NameError | **REFUTADO** | `vagas.py:186-187` importa `datetime` e `VagaModel` no **fim** do módulo, e o Python resolve esses nomes na chamada. `PATCH /vagas/5` retornou 200. O mesmo padrão frágil existe em `config.py:71` e `admin_service.py:279` (fica como sugestão: mover para o topo). | BAIXO |
| D13 | `GET /vagas/relatos` é capturado por `/{vaga_id}` | **CONFIRMADO** | Retorna 422 `int_parsing` em `vaga_id="relatos"` (`vagas.py:65` vem antes de `:175`). Relatos estão fora do escopo. | BAIXO |
| D14 | A rota de saída da doc (`POST /tickets/{id}/saida`) não existe | **CONFIRMADO** | Retorna 404 `Not Found`. Só existe `POST /tickets/saida` com body (`tickets.py:33`). | MÉDIO |
| D15 | `/setores` não existe | **CONFIRMADO** | `GET /setores` retorna 404. O schema `SetorResponse` já existe (`schemas.py:34`). | BAIXO |
| D16 | Não há Postman nem testes | **CONFIRMADO, com ajuste** | A pasta `postman/` **existe, mas está vazia**. Não há `tests/`. `pytest` e `httpx` estão no requirements, e o `TestClient` funciona com as versões fixadas (validado). | ALTO (Must H09) |
| D17 | **(novo)** A normalização da placa não funciona | **CONFIRMADO** | O `pattern` roda antes do `field_validator` (`schemas.py:118-125`): `"abc1d23"` e `"ABC-1D23"` retornam 422. A placa está fora da UI (Design), então é Should só se a H10 entrar. | BAIXO |
| D18 | **(novo)** Saída repetida e ticket inexistente devolvem a mesma resposta | **CONFIRMADO** | Ambos retornam 404 "Ticket não encontrado ou já finalizado" (`tickets.py:42`). O Design exige mensagens distintas (E12/E13). | BAIXO |
| D19 | Uma única conexão SQLite é compartilhada entre threads | **RISCO (leitura)** | `database.py:28` usa `poolclass=StaticPool` com arquivo. Endpoints `def` rodam em threadpool, e as sessões compartilham uma conexão, então o commit ou o rollback de uma request afeta a outra. Baixo impacto numa demo com um usuário, mas invalida a atomicidade sob concorrência. | MÉDIO |
| D20 | O nome da equipe está errado | **CONFIRMADO** | "Equipe 44" em `main.py:4, 57, 62, 135` e `frontend/index.html:102`. "Gestante" aparece em `index.html:90, 343`. | BAIXO |
| D21 | **(novo)** O código do projeto não está versionado | **CONFIRMADO** | O repositório git do projeto tem 5 commits só de docs. `app/`, `data/`, `frontend/` e `requirements.txt` aparecem como `??`, e não há `.gitignore` (`__pycache__` e `.db` entrariam no commit). A revisão por `git diff` fica impossível sem um commit de baseline. | MÉDIO (processo) |
| D22 | Datas naive em UTC (`datetime.utcnow`) | **CONFIRMADO** | As respostas saem sem sufixo `Z`, por exemplo `"2026-11-13T19:23:28.301685"`. A UI precisa tratar como UTC. Gera DeprecationWarning, mas não quebra. | BAIXO |

Também conferido e funcionando: `/health`, `/config`, 422 para tipo inválido, 400 legível para tipo sem vaga, a regra "vaga restrita não vai para comum" (o filtro por tipo em `_encontrar_vaga`), `/vagas/proximas` 404 quando não há vaga, `PATCH /config/admin/tolerancia_minutos` (invalida o cache, e o novo ticket recebe a nova tolerância).

Estado do `data/capimparking.db` atual: 356 vagas (296+9 comum, 13 elétrico, 8 gestante, 19 idoso, 3 neuro, 8 pcd, 0 moto), 13 carregadores, 10 tickets ativos do seed e nenhum órfão. Amarelo não tem PCD nem neuro, o que serve para a demo de "setor cheio".

## 2. Arquitetura atual (resumo)

- **Stack:** Python + FastAPI 0.115 + SQLAlchemy 2.0.36 (API `Query` legada) + Pydantic 2.10 + SQLite em arquivo (`data/capimparking.db`, caminho fixo em `database.py:15`).
- **Camadas:** `app/routers/*` (HTTP, mapeia `ValueError` para 400/404) → `app/services/*` (classes com `@classmethod` que recebem `db: Session`) → `app/models.py` (ORM; os enums são gravados pelo **nome**, ex. `'LIVRE'`) e `app/schemas.py` (Pydantic, `from_attributes`).
- **Bootstrap:** o `lifespan` em `main.py:22-38` cria as tabelas e roda o seed **apenas se a tabela `configuracoes` estiver vazia**. Mudar o seed não altera um banco existente: é preciso apagar o `.db`.
- **Config:** a tabela chave/valor `Configuracao`, com cache em memória no nível da classe (`ConfigService._cache`).
- **Frontend:** HTML e CSS estáticos (`frontend/`), sem JS e sem servidor.
- **Padrões a seguir:** um service por domínio, routers finos, schemas de request/response em `schemas.py`, mensagens de erro em pt-BR em `detail`.

## 3. Decisões técnicas

| # | Decisão | Motivo |
|---|---|---|
| DT1 | **Cobrança calculada em segundos e arredondada para cima por hora** (`ceil`). `perm_s = saida - entrada`. Se `perm_s <= tol*60`, fica ISENTO. Senão, `horas = ceil((perm_s - tol*60) / 3600)` e `valor = horas * valor_hora`. `fracao_15min` continua opcional: `ceil(fat_s/900) * 0.25 * valor_hora`. A lógica fica numa **função pura** `calcular_cobranca`, testável sem relógio. | Corrige D6 e bate exatamente com a tabela do PO (seção 2 do `02-po.md`). |
| DT2 | Exibição: `tempo_total_minutos = floor(perm_s/60)`; `tempo_faturavel_minutos = ceil(fat_s/60)` (0 se isento). | Mantém o contrato atual (int) e o cenário do PO (76 min → total 76, faturável 61, R$ 10,00). |
| DT3 | **A entrada é uma transação única:** reserva condicional `UPDATE vagas SET status=OCUPADA WHERE id=:id AND status=LIVRE` (verifica `rowcount == 1`) + `INSERT ticket` + **um** `commit`. Qualquer exceção faz `db.rollback()` e propaga. | Corrige D1/D2 e a corrida de dupla ocupação, mesmo com várias conexões. |
| DT4 | `ocupar_vaga`/`liberar_vaga` ganham o parâmetro `commit: bool = True`. O ticket_service passa `commit=False`. | Mantém a compatibilidade com admin e simulação sem duplicar código. |
| DT5 | **O FastAPI serve o frontend:** `app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")` como **última** linha após os `include_router`. O JSON de `GET /` vai para `GET /api/info`. | Validado na cópia: `/` → index.html, `/styles.css` → 200, `/health`, `/docs` e `/vagas/*` continuam respondendo. Elimina CORS e porta extra (D7 do PO). Sem dependência nova. |
| DT6 | `DATABASE_URL` vem da variável de ambiente `CAPIM_DB_URL` (padrão: o arquivo atual). Usa `StaticPool` **só** quando a URL é `:memory:`. Para arquivo, usa o pool padrão. | Permite que pytest e Postman usem outro banco sem tocar em `data/`. Mitiga D19. |
| DT7 | Seed **determinístico** (`random.Random(43)`). Os tickets de exemplo ocupam só vagas `comum`. Inclui **10 vagas moto no setor Laranja** (Subsolo 2, bloco C), tiradas das comuns: o total continua 356. Mantém o Amarelo sem PCD (cenário de setor cheio). | Corrige D5 (D6 do PO), torna os testes reproduzíveis e não deixa o acaso esgotar os tipos especiais. |
| DT8 | Proximidade com distância entre setores por bloco: `inter = 30 * abs(idx(bloco_o) - idx(bloco_d))` (A=0, B=1, C=2), mais 50 se o andar for diferente, mais a distância local da vaga até o centro (50,50) do próprio setor. | Faz "mesmo andar → vizinho → mais longe" funcionar sem mudar o schema (o campo `bloco` já existe no seed). |
| DT9 | `excluir_vaga_id` passa a ser uma **lista** (`list[int] | None = Query(None)`), com o parâmetro repetido `?excluir_vaga_id=2&excluir_vaga_id=1`. | Corrige D9. Compatível com o envio de um único valor. |
| DT10 | A entrada aceita `vaga_id` opcional (aceite da sugestão). Se vier, a vaga precisa estar livre e ser do tipo pedido, senão retorna 409. Sem `vaga_id`, com setor preferido cheio, usa `sugerir_vaga_proxima` (corrige D10). Sem setor, usa a primeira livre do tipo. | Responde à pergunta 1 do Designer. A UI garante a vaga mostrada (UC02 passo 6). |
| DT11 | Erros de saída: 404 "Ticket não encontrado" e 409 "Este ticket já teve a saída registrada". Com exceções próprias no service (`TicketNaoEncontrado(LookupError)`, `TicketJaFinalizado(Exception)`) mapeadas no router. | D18, estados E12/E13 do Design. |
| DT12 | Datas continuam naive UTC no banco. A UI converte com `new Date(s.endsWith('Z') ? s : s + 'Z')` e formata em `America/Araguaina`. | Evita migração e mudança de tipo no SQLite com 1 dia de prazo. |
| DT13 | Ambiente: **Python 3.11 a 3.13** (validado no 3.13), sem mudar os pins. O README passa a documentar `py -3.13 -m venv .venv`. | Corrige D4 com risco zero. Subir os pins (pydantic ≥ 2.12) fica para depois do hackathon. |
| DT14 | Sem dependências novas. `StaticFiles` (Starlette), `TestClient` (httpx, já fixado) e `pytest` já estão disponíveis. Postman é JSON, e o Newman é opcional (Node), não uma dependência do projeto. | Regra do squad. |
| DT15 | Admin, relatos, simulação e export ficam no código, **mas fora da UI e do Postman**. Corrigir apenas o trivial (D11, D13). | Corte de escopo (Won't do PO). |

## 4. Contratos (estado alvo)

### 4.1 Função pura de cobrança (novo, em `app/services/ticket_service.py`, no nível do módulo)
```python
@dataclass(frozen=True)
class Cobranca:
    tempo_total_minutos: int      # floor
    tempo_faturavel_minutos: int  # ceil, 0 se isento
    valor: float                  # round(.., 2)
    isento: bool

def calcular_cobranca(entrada: datetime, saida: datetime, tolerancia_minutos: int,
                      valor_hora: float, regra: str = "hora_cheia") -> Cobranca: ...
```
Tabela de aceite (tol 15, R$ 5,00/h, `hora_cheia`): 10min → 0,00 isento; 15min00s → 0,00 isento; 15min01s → 5,00; 16min → 5,00; 75min → 5,00; 75min01s → 10,00; 76min → 10,00 (total 76, faturável 61); 135min → 10,00; 135min01s → 15,00. Com `fracao_15min`: 16min → 1,25.

### 4.2 Endpoints

| Método e rota | Request | Response | Erros |
|---|---|---|---|
| `GET /` | | `index.html` (StaticFiles) | |
| `GET /api/info` | | JSON que hoje está em `GET /` (Equipe 43) | |
| `GET /health`, `GET /config` | | sem mudança | |
| `GET /setores` (novo, Should) | | `list[SetorResumo]`: `{id, nome, cor, andar, bloco, capacidade_total, vagas_livres, vagas_ocupadas}` | |
| `GET /vagas/disponiveis` | `tipo?`, `setor_id?`, `andar?`, `apenas_com_carregador?` | igual ao atual. **`por_setor` traz todos os setores** que passam em `setor_id`/`andar`, inclusive com `livres=0`. `livres`/`ocupadas`/`total` por setor **filtrados por tipo** (e por `tem_carregador` quando pedido). | `setor_id` inexistente: 200 com `total=0` e `por_setor=[]` |
| `GET /vagas/proximas` | `setor_desejado_id`, `tipo_vaga`, `excluir_vaga_id` (repetível) | `VagaSugeridaResponse` sem mudança de campos | 404 quando não há candidata |
| `POST /tickets/entrada` | `{tipo_vaga, setor_id?, placa?, vaga_id?}` | `TicketEntradaResponse` atual (201) | 400 sem vaga do tipo; 409 se `vaga_id` não está livre ou é de outro tipo; 422 validação |
| `POST /tickets/saida` | `{identificador}` | `TicketSaidaResponse` atual com a cobrança da DT1 | 404 não encontrado; 409 já finalizado |
| `POST /tickets/{identificador}/saida` (alias da doc) | | idem | idem |
| `GET /tickets/{identificador}` | | sem mudança | 404 |

Os nomes de campo do Postman e da UI são os reais: `vaga` e `distancia_metros` no **mesmo nível**, `setor_desejado_id`, `tipo_vaga`, `setor_id`.

### 4.3 Assinaturas alteradas
```python
# vaga_service.py
VagaService.ocupar_vaga(db, vaga_id: int, commit: bool = True) -> Optional[Vaga]   # UPDATE condicional
VagaService.liberar_vaga(db, vaga_id: int, commit: bool = True) -> Optional[Vaga]
VagaService.sugerir_vaga_proxima(db, setor_desejado_id: int, tipo_vaga: TipoVaga,
                                 excluir_vaga_ids: Optional[list[int]] = None) -> Optional[VagaSugeridaResponse]
# ticket_service.py
TicketService._encontrar_vaga(db, tipo_vaga, setor_id, vaga_id=None) -> Optional[Vaga]
TicketService.registrar_saida(db, request, agora: Optional[datetime] = None)  # 'agora' injetável para teste
# database.py
DATABASE_URL = os.getenv("CAPIM_DB_URL", f"sqlite:///{DB_PATH}")
```

## 5. Tarefas para o Dev (ordem de execução)

Dois trilhos em paralelo. **A** = backend + testes (1 dev), **F** = frontend (1 dev, seguindo o `03-design.md` seção 7.1). A tarefa T0 vem antes de tudo. Total estimado: A ≈ 6h30 (Must ≈ 4h30), F ≈ 7h30 (Must ≈ 5h30).

### T0 - Preparação (15 min, bloqueante)
| ID | Arquivo | Mudança | Pronto quando | Est. |
|---|---|---|---|---|
| T0.1 | `.gitignore` (novo) + git | Ignorar `__pycache__/`, `*.pyc`, `.venv/`, `data/*.db`, `.omc/`. Fazer um **commit de baseline** do código atual antes de qualquer alteração (pedir ok ao usuário). | `git status` limpo; o `git diff` passa a mostrar só as mudanças da rodada | 10 min |
| T0.2 | Ambiente local | `py -3.13 -m venv .venv` e `pip install -r requirements.txt` | `python -c "import fastapi"` ok | 5 min |

### Trilho A - Backend (Must)
| ID | Arquivo(s) | Mudança | Pronto quando | Est. |
|---|---|---|---|---|
| A1 | `app/database.py` | DT6: `CAPIM_DB_URL` e `StaticPool` só para `:memory:` | A API sobe com e sem a variável; pytest usa banco temporário | 15 min |
| A2 | `app/services/ticket_service.py`, `app/services/vaga_service.py` | Importar `VagaResponse`; DT3/DT4 (transação única com rollback e `UPDATE` condicional) | `POST /tickets/entrada` retorna 201 com `vaga.setor.andar`. Com exceção forçada depois da reserva (monkeypatch), a vaga continua `LIVRE` e não há ticket | 40 min |
| A3 | `app/services/ticket_service.py` | DT1/DT2: `calcular_cobranca` pura; `registrar_saida` usa ela e aceita `agora` | Toda a tabela da 4.1 passa no pytest | 30 min |
| A4 | `app/services/ticket_service.py`, `app/routers/tickets.py` | DT11 (404/409) e alias `POST /tickets/{identificador}/saida` | Saída repetida retorna 409; código inexistente retorna 404; o alias responde igual | 20 min |
| A5 | `app/seed.py` | DT7: 10 motos no Laranja, `random.Random(43)`, tickets de exemplo só em `comum`. Depois **apagar `data/capimparking.db`** e subir a API para gerar de novo | Os 6 tipos têm ≥ 1 livre; `?tipo=moto` retorna `total=10`; continuam 356 vagas | 25 min |
| A6 | `app/services/vaga_service.py` (`get_vagas_disponiveis`) | Contrato 4.2: todos os setores (filtrados por `setor_id`/`andar`) e contagens filtradas por tipo/carregador | `?tipo=pcd` traz o Amarelo com `livres=0`; para todo setor, `livres+ocupadas+manutencao == total` do tipo | 35 min |
| A7 | `app/main.py` | DT5 (StaticFiles em `/`, info em `/api/info`); "Equipe 43" em `main.py:4,57,62,135` | `GET /` serve o HTML; `/docs` ok; nenhum "Equipe 44" no backend | 15 min |
| A8 | `tests/` (novo) | Seção 6.1 (conftest + 3 arquivos) | `pytest -q` verde | 60 min |
| A9 | `postman/collection.json`, `postman/environment.json` (novos) | Seção 6.2 | Collection Runner verde contra a API local com banco recém-criado | 45 min |
| A10 | `README.md` | Como rodar (Py 3.13, venv, `uvicorn app.main:app`, abrir `http://localhost:8000/`), como reiniciar o banco, como rodar pytest e Postman | Outra pessoa da equipe sobe a demo só lendo o README | 15 min |

### Trilho A - Should (só depois de A1 a A10 verdes)
| ID | Arquivo(s) | Mudança | Pronto quando | Est. |
|---|---|---|---|---|
| A11 | `app/services/vaga_service.py`, `app/routers/vagas.py`, `app/services/ticket_service.py`, `app/schemas.py` | DT8 (distância por bloco), DT9 (lista de exclusão), DT10 (`vaga_id` na entrada e proximidade na entrada com setor cheio) | Amarelo/PCD sugere **Verde**; 3 recusas seguidas devolvem 3 vagas distintas e depois 404 quando acabam; entrada com `vaga_id` ocupa exatamente essa vaga; `vaga_id` ocupada retorna 409 | 50 min |
| A12 | `app/routers/setores.py` (novo), `app/main.py` | `GET /setores` só leitura (contrato 4.2) | Retorna os 6 setores com contagens | 20 min |
| A13 | `app/services/vaga_service.py`, `ticket_service.py` | EV: o carregador vai para `EM_USO` ao ocupar e volta a `DISPONIVEL` ao liberar; entrada `eletrico` só em vaga com carregador `DISPONIVEL` | Teste: o status do carregador muda; carregador em `MANUTENCAO` não é oferecido | 30 min |
| A14 | `app/schemas.py` | Placa: `field_validator(mode="before")` que remove espaço e hífen e converte para maiúsculas | `"abc-1d23"` vira `ABC1D23` | 10 min |

### Trilho A - Could (higiene, 15 min no total, se sobrar)
- `vaga_service.py:265-267, 291-292`: trocar `func.case` por `case` (importado de `sqlalchemy`). Pronto quando `/admin/ocupacao` retornar 200.
- `vagas.py`: mover `GET /relatos` para antes de `GET /{vaga_id}` e os imports do fim (`:186-187`) para o topo. Fazer o mesmo em `config.py:71` e `admin_service.py:279`.

### Trilho F - Frontend (segue `03-design.md` seções 3 a 7; o Designer é a referência de UI)
| ID | Arquivo(s) | Mudança | Pronto quando | Est. |
|---|---|---|---|---|
| F1 | `frontend/index.html` | Reduzir a 1 página com blocos (Entrada, Ticket, Saída). Remover mapa, consulta separada, admin, `btn-admin-access` e "Gestante". Usar radios nativos para os tipos, `<select>` de setor e "Equipe 43 Aerodactyle" | HTML válido, um `<h1>`, nenhuma referência a admin ou mapa | 1h |
| F2 | `frontend/app.js` (novo) | `api()` (fetch relativo à mesma origem e tratamento de `detail` string ou lista), carga de `/config` e `/vagas/disponiveis`, render dos 6 tipos, setores (fallback fixo ids 1 a 6 + `por_setor`), contadores. Estados E0 a E3, E6, E7 | A tela mostra os contadores reais; API fora do ar mostra "Tentar de novo" | 2h |
| F3 | `frontend/app.js` | Entrada → ticket (E4) e saída → valor (E9 a E13); `sessionStorage` do código; conversão UTC → `America/Araguaina`; `window.print()` | Fluxo completo entrada → saída pela tela, só com teclado | 1h30 |
| F4 | `frontend/styles.css` | Patch de tokens (Design 2.1), `.alert` e `.suggestion-card`; toolbar estática; tirar `aria-live` dos contêineres extras | Contrastes da tabela C1 a C8 corrigidos | 1h |
| F5 | `frontend/app.js` | A11y: foco gerenciado, um `aria-live` só, alto contraste e fonte persistidos, TTS (Design 6.4) | Checklist 6.6 itens 1 a 5 | 1h |
| F6 (Should) | `frontend/app.js` | Setor cheio com Aceitar/Outra opção/Cancelar (E5), usando `vaga_id` e lista de exclusão. **Depende de A11.** Sem A11, aplicar a degradação 7.3 do Design | Demo Amarelo + PCD → sugestão no Verde → aceitar → ticket na vaga mostrada | 1h |
| F7 | | Teste manual e ensaio da demo | Roteiro da seção 8 executado 2 vezes sem erro | 30 min |

**Ponto de sincronização:** F2 e F3 dependem de A2, A5, A6 e A7. O Dev F pode começar F1, F4 e o esqueleto do F2 contra a API atual (os erros caem em E7), mas só valida o fluxo depois que A2 estiver pronto (meta: até 2h após o início).

## 6. Estratégia de testes

### 6.1 Pytest (Must, `tests/`)
- `tests/conftest.py`: antes de importar `app`, define `os.environ["CAPIM_DB_URL"] = f"sqlite:///{tmp_path_factory}/test.db"`. Uma fixture `client` usa `with TestClient(app) as c` (o lifespan roda o seed determinístico). Uma fixture `autouse` chama `ConfigService.invalidate_cache()`. Banco **novo por teste** quando o teste altera estado: apagar o arquivo e rodar `drop_db()` + `seed_database()`. **Nunca** usar `data/`.
- `tests/test_cobranca.py` (unitário, parametrizado): a tabela da 4.1 completa, mais `fracao_15min` e tolerância configurável (10 min).
- `tests/test_tickets.py` (integração):
  - entrada 201 com `vaga.setor.andar`, a vaga vai para `ocupada` e os livres caem 1 (H01, H04);
  - entrada para cada um dos 6 tipos, incluindo moto (H05);
  - tipo esgotado retorna 400 sem mudar nada; `"foguete"` retorna 422;
  - atomicidade: `monkeypatch` em `TicketService._gerar_mensagem_entrada` para lançar exceção, depois verificar que a vaga continua livre e não existe ticket (RN 9);
  - "comum" esgotado não recebe pcd, idoso nem elétrico;
  - saída: `registrar_saida(..., agora=entrada + timedelta(minutes=76))` retorna R$ 10,00 e a vaga fica livre; saída repetida retorna 409; inexistente retorna 404; o alias `/tickets/{id}/saida` responde igual.
- `tests/test_vagas.py`: setor cheio aparece com `livres=0`; contagens coerentes por tipo; `setor_id=9999` retorna 200 vazio. Should (A11): Amarelo/PCD → Verde; 3 recusas distintas; `vaga_id` aceito; 409 para `vaga_id` ocupada.
- Comando: `python -m pytest -q`. Meta: tudo verde antes de começar o Postman.

### 6.2 Coleção Postman (Must, H09)
`postman/collection.json` (formato v2.1) e `postman/environment.json` com `baseUrl=http://localhost:8000`. Pastas alinhadas à seção 9 da doc, só com o que existe:
1. **Setup & Health:** `GET /health` (200, `database=connected`); `GET /config` (tolerância 15, valor 5.0).
2. **Setores (Should):** `GET /setores`. Os itens `POST /setores` e `GET /setores/{id}/vagas` ficam **fora** (Won't), registrado na descrição da coleção.
3. **Vagas:** `GET /vagas/disponiveis?tipo=comum&setor_id=1`; `?tipo=pcd` (asserção: o Amarelo tem `livres=0`); `GET /vagas/proximas?setor_desejado_id=3&tipo_vaga=pcd` (asserção: `distancia_metros` no nível raiz; salva `vaga.id` em `vagaSugerida`); a mesma rota com `excluir_vaga_id={{vagaSugerida}}` (id diferente); `GET /vagas/{{vagaSugerida}}`.
4. **Tickets - Entrada:** comum + setor 1 (201, salva `ticketId`); idoso sem setor; eletrico (`vaga.tem_carregador=true`); moto; pcd + setor 3 (cheio → vaga em outro setor, ou `vaga_id={{vagaSugerida}}` se A11 entrar).
5. **Tickets - Saída:** `POST /tickets/{{ticketId}}/saida` imediata (isento, R$ 0); a mesma de novo (409); `XXXXXXXX` (404). **Cobrança sem esperar 15 min:** `PATCH /config/admin/tolerancia_minutos {"valor":"0"}`, depois entrada, pre-request com `setTimeout` de 2 s, depois saída (`valor = 5.0`, `status_pagamento = pendente`). Por fim, `PATCH` de volta para `"15"` (mecanismo validado na cópia; só fica correto depois de A3). O cenário de 76 min e R$ 10,00 é coberto pelo pytest (função pura).
6. **Erros/contrato:** tipo inválido (422); asserções de tempo `pm.response.responseTime < 200` nos GETs (evidência leve do RNF01).

Pré-condição documentada: banco recém-criado (apagar `data/capimparking.db` e subir a API). A coleção tem que ser executável em sequência no Collection Runner.

## 7. Riscos

| # | Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|---|
| R1 | Frontend (≈ 7h30) não termina a tempo | Alta | Alto | Corte e degradação conforme o Design 7.2/7.3. F6 é Should. Plano B da demo: Swagger `/docs` + Postman. |
| R2 | Alguém roda com Python 3.14 e não consegue instalar | Alta | Alto | DT13 + README (A10). Validado no 3.13. |
| R3 | Seed alterado sem apagar o `.db` (o lifespan só faz seed com o banco vazio) | Alta | Médio | Passo explícito em A5 e no README. O `.db` vai para o `.gitignore`. |
| R4 | Mudança em `_encontrar_vaga`/proximidade (A11) quebra a entrada básica | Média | Alto | A11 só depois dos testes de A8 verdes. Rodar o pytest de novo depois de A11. |
| R5 | Conflitos de merge entre os trilhos A e F | Média | Médio | Arquivos separados (`app/**` × `frontend/**`). O único ponto comum é o contrato da seção 4, que está congelado. |
| R6 | Concorrência no SQLite (D19) durante a demo | Baixa | Médio | A1 + DT3 (UPDATE condicional). 500 requisições simultâneas é Won't. |
| R7 | Sem commit de baseline, a revisão e o rollback das mudanças ficam inviáveis | Alta | Médio | T0.1. |
| R8 | Fuso horário errado no ticket (UTC vs. UTC-3) | Média | Baixo | DT12, com teste manual em F7. |
| R9 | A documentação e a coleção divergem da API (nomes de campo e rotas) | Média | Médio | Contrato 4.2. Alias da saída (A4). Itens Won't anotados na coleção. |

## 8. Roteiro mínimo da demo (para F7 e para a QA)
1. Banco recém-criado → abrir `http://localhost:8000/` e ver os contadores.
2. Comum + Azul → ticket com vaga, setor, andar, tolerância e R$ 5,00/h → imprimir.
3. Moto → ticket no Laranja.
4. PCD + Amarelo → sugestão no Verde → Outra opção → Aceitar (ou o aviso "vaga alocada em Y" se A11/F6 não entrarem).
5. Saída imediata do ticket 2 → isento. Saída repetida → mensagem de "já registrada".
6. Postman Runner verde. `pytest -q` verde. Mostrar alto contraste, A+ e TTS.

## Revisão

Revisão de código da v2.0 feita pelo Tech Lead em 13/11/2026. Escopo: `git diff v1.0..HEAD -- app frontend tests postman scripts README.md CHANGELOG.md requirements.txt` (26 arquivos, +4227/-1068), mais `05-dev.md`, `05-dev-frontend.md` e `06-qa.md`. Os números de linha citados são do `HEAD` (`642d5bb`).

### Verificação executada

| Comando | Resultado |
|---|---|
| `.venv\Scripts\python -m pytest -q` | **83 passed, 1 xfailed** em 12,9 s. O xfail estrito é o BUG-01 da QA. |
| Sonda de concorrência (scratchpad, banco temporário, `TestClient` + 10 threads, 8 rodadas) | 10 entradas `moto` simultâneas com 10 vagas livres: **12 × 201 e 68 × 400 "Falha ao ocupar a vaga"**. Duas saídas simultâneas do mesmo ticket: **8 de 8 rodadas com 200/200**. Ver R1 e R2. |
| `git ls-files` / `.gitignore` | Nenhum `.db`, `__pycache__` ou `.venv` versionado. `requirements.txt` sem mudança (DT14 ok). |

### Resumo

A v2.0 cumpre o plano. As decisões DT1 a DT15 e os contratos da seção 4.2 foram implementados como especificado:
- cobrança pura em microssegundos inteiros, mais rigorosa que os segundos do DT1;
- entrada numa transação única, com `UPDATE` condicional e rollback;
- `liberar_vaga`/`ocupar_vaga` com `commit=False`;
- `StaticFiles` montado por último e `/api/info`;
- `CAPIM_DB_URL`, com `StaticPool` só em memória;
- seed determinístico com 10 motos;
- proximidade por bloco e andar;
- exclusão repetível;
- `vaga_id` aceito na entrada, com 409;
- 404/409 na saída e o alias `/tickets/{id}/saida`;
- conversão UTC para `America/Araguaina` na UI;
- nenhuma dependência nova.

O padrão do projeto foi respeitado: routers finos, services com `@classmethod`, schemas em `schemas.py` e `detail` em pt-BR. O frontend não tem sink de XSS. O único `innerHTML` (`frontend/app.js:239`) usa a constante `ICONES`, e todo dado vindo da API entra por `textContent`/`createTextNode`. Os testes têm significado: a tabela de fronteira da cobrança, a atomicidade com falha forçada, a coerência dos contadores entre endpoints e o banco temporário isolado de `data/`.

Não há achado Bloqueante nem Alto. Os dois problemas mais relevantes (R1 e R2) são de concorrência. Não afetam a demo, que tem um único usuário e uma UI que bloqueia o duplo envio (`state.ocupado`), mas vale corrigir antes da tag porque a correção é barata.

### Achados

| # | Severidade | Arquivo:linha | Achado | Correção sugerida |
|---|---|---|---|---|
| R1 | **Média** | `app/services/ticket_service.py:98-108`, `:260-268` | **Falso "sem vaga" sob concorrência.** Todas as requisições escolhem a mesma vaga (`order_by(Vaga.id).first()`). O `UPDATE` condicional impede a dupla ocupação (DT3 correto), mas quem perde a corrida recebe **400 "Falha ao ocupar a vaga"** mesmo com vagas livres. Na sonda: 68 de 80 entradas recusadas indevidamente. A mensagem não é acionável para o usuário. | Tentar de novo até N vezes (ex.: 5) excluindo as vagas já disputadas quando `ocupar_vaga` devolve `None` e não veio `vaga_id`. Só depois disso responder 400 "Nenhuma vaga X disponível". |
| R2 | **Média** | `app/services/ticket_service.py:152-182` | **Saída sem compare-and-set.** A checagem `ticket.saida is not None` é feita num `SELECT` anterior. Duas saídas simultâneas do mesmo ticket devolvem 200/200 (8 de 8 rodadas), e a segunda sobrescreve `saida`/`valor`. Pior caso: entre as duas saídas, outra entrada ocupa a mesma vaga, e o `liberar_vaga` da segunda saída (condição `status=OCUPADA`) a marca como LIVRE com um ticket ativo nela, o que abre uma dupla ocupação. | `UPDATE tickets SET saida=:s, valor=:v, status_pagamento=:p WHERE id=:id AND saida IS NULL` com `rowcount == 1`. Se não for 1, levantar `TicketJaFinalizado` (409), mantendo o mesmo padrão do `_mudar_status`. |
| R3 | **Média** (Should H08) | `app/services/vaga_service.py:41-46` | **BUG-01 da QA confirmado.** `filtros()` ignora `Carregador.status`, então `/vagas/disponiveis?tipo=eletrico` lista e conta vaga com carregador em `manutencao` que a entrada recusa (`ticket_service.py:264-267`). O contador "Elétrico" da UI mente nesse cenário. | Nas vagas e na contagem de `LIVRE`, quando `tipo == ELETRICO` ou `apenas_com_carregador`, aplicar `outerjoin(Carregador)` e exigir `Carregador.status == DISPONIVEL`. Remover o `xfail` de `tests/test_qa_criterios.py:268`. |
| R4 | **Média** (pós-hackathon) | `app/main.py:78-84`, `:161`; `app/routers/admin.py:87`; `app/routers/config.py:44,53`; `app/routers/vagas.py:102-167` | **Superfície administrativa sem autenticação, com CORS `*` e `allow_credentials=True`.** Qualquer página aberta no navegador da máquina da demo pode chamar `POST /admin/reset` ou `PATCH /config/admin/*` via `fetch`. `python -m app.main` sobe em `0.0.0.0`. Fora do escopo pelo DT15 e já apontado como risco pela QA. | Antes do release, como ganho rápido opcional: remover o `CORSMiddleware`, que deixou de ser necessário porque o frontend é same-origin (DT5), ou restringir a `localhost`. Trocar `0.0.0.0` por `127.0.0.1`. Pós-hackathon: proteger `/admin`, `/config/admin` e a escrita em `/vagas` com token, ou removê-los. |
| R5 | Baixa | `scripts/run_newman.py:24-37` | Se a porta 8000 já estiver ocupada pela API de desenvolvimento, o uvicorn filho morre sem aviso (stderr em `DEVNULL`), o health check responde a partir da API **real** e o Newman roda contra `data/capimparking.db`: consome vagas e faz `PATCH` da tolerância, que fica em 0 se a coleção falhar no meio. Isso contradiz a promessa "não toca em data/". | No laço de espera, checar `api.poll() is None`, e abortar se o processo filho tiver saído. Outra opção é usar uma porta padrão diferente (ex.: 8765). |
| R6 | Baixa | `tests/test_qa_criterios.py:162` | O teste de concorrência aceita 400/409 como resultado válido, por isso não detectou o R1. Com 10 motos livres e 10 entradas, o esperado é 10 × 201. | Depois do R1, apertar para `all(c == 201 ...)`. Adicionar um teste de saída concorrente para o R2 (esperado: um 200 e um 409). |
| R7 | Baixa | `app/services/ticket_service.py:309`, `:325-333` | BUG-03 da QA: o texto de `mensagem` usa hora UTC. A UI não o exibe, mas o Swagger e o Postman sim. | Formatar em `America/Araguaina` (`zoneinfo`, stdlib) ou tirar a hora do texto. |
| R8 | Baixa | `README.md:58-65` | NOTA-04 da QA: no Windows, `scripts/reset_db.py` falha com `PermissionError` se a API estiver rodando. | Incluir "pare a API (Ctrl+C) antes" na seção. Opcional: capturar o `PermissionError` no script e mostrar essa mesma mensagem. |
| R9 | Baixa (escopo) | `app/routers/tickets.py` | BUG-02 da QA: não existe consulta por placa (H10, Should). A placa já é normalizada (A14), então a rota é simples. | Pós-hackathon: `GET /tickets/placa/{placa}`, com a placa normalizada e 404 claro. |
| R10 | Sugestão | `frontend/app.js:455-459` | A cada 30 s, o polling faz 2 ou 3 chamadas a `/vagas/disponiveis`, e cada uma devolve a lista completa de vagas com relacionamentos (cerca de 346 objetos) só para usar `por_setor`/`total`. | Pós-hackathon: parâmetro `resumo=true` que omite `vagas`, ou usar `/setores`. |
| R11 | Sugestão | `app/services/ticket_service.py:290-293` | Identificador de 32 bits (8 hex de um UUID4) com `unique=True` (`models.py:134`). Uma colisão gera `IntegrityError`, que vira 500 após o rollback. A probabilidade é desprezível no volume da demo. | Pós-hackathon: tentar de novo ao receber `IntegrityError`, ou usar um alfabeto maior (`secrets.token_hex`/base32). |
| R12 | Sugestão | `app/seed.py:7,11-12` | `import uuid` ficou sem uso, e `SEED = 43` está entre dois blocos de import. | Remover o import e mover a constante para depois dos imports. |
| R13 | Sugestão | `tests/conftest.py:11` | O diretório `capim_tests_*` criado por `mkdtemp` nunca é removido. | Fixture de sessão com `shutil.rmtree` no teardown. |
| R14 | Sugestão | `pytest.ini` | `PytestDeprecationWarning` do pytest-asyncio (`asyncio_default_fixture_loop_scope` não definido). | Acrescentar `asyncio_default_fixture_loop_scope = function`. |

Aderência ao plano: DT1 a DT15 **ok**. Os contratos da seção 4.2 e as assinaturas da 4.3 estão **ok**. A única diferença é o cálculo em microssegundos em vez de segundos, que é estritamente melhor e foi coberto pelos testes de fronteira `15min+1us` e `14:59.999999`. Os itens Could (D11, D12, D13) também entraram.

### Antes do release (tag v2.0.0) vs. pós-hackathon

- **Recomendado antes da tag** (cerca de 1h no total, nenhum item bloqueia):
  - R1 (retry na entrada), com o teste apertado do R6;
  - R2 (CAS na saída), com o teste de saída concorrente;
  - R3 (BUG-01, remover o `xfail`);
  - R5 (guarda do `run_newman.py`);
  - R8 (aviso no README);
  - parte rápida do R4 (tirar o CORS `*` e trocar `0.0.0.0` por `127.0.0.1`).

  Depois de cada item, rodar `pytest` e `run_newman.py` de novo.
- **Pós-hackathon:**
  - R4 completo (autenticação ou remoção dos endpoints admin);
  - R7, R9 e R10 a R14;
  - além do já registrado: subir os pins para Python 3.14 (DT13), datas com fuso no banco (DT12) e um teste de carga real para o RNF de concorrência.

Se o prazo não permitir as correções, a v2.0 pode ser demonstrada como está. O roteiro da seção 8 não exercita nenhum dos achados, e a QA o validou ponta a ponta.

**Veredito da revisão: APROVADO**

