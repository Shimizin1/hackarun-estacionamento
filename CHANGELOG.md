# Changelog

Todas as mudanças relevantes deste projeto são documentadas aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto adota [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [2.0.0] - 2026-11-13 (Unreleased até o fim do hackathon)

### Corrigido
- `POST /tickets/entrada` retornava 500 por `VagaResponse` não importado (D1).
- Entrada não era atômica: após falha, a vaga ficava presa e sobrava ticket órfão. Agora é uma transação única com reserva condicional da vaga e rollback em qualquer erro (D2, DT3).
- Cobrança truncava minutos: 15min01s era isento e 75min01s cobrava R$ 5,00. Agora o cálculo é em segundos, com arredondamento para cima por hora após a tolerância (D6, DT1).
- Seed não criava vagas de moto; agora há 10 no setor Laranja, sem alterar o total de 356 vagas (D5).
- `/vagas/disponiveis` omitia setores sem vaga livre e os contadores ignoravam o filtro de tipo; agora retorna todos os setores com `livres`/`ocupadas`/`total` filtrados (D7).
- Proximidade usava referência fixa; agora considera a distância entre blocos (A, B, C) e andares: Amarelo com PCD sugere o Verde (D8, DT8).
- "Outra opção" entrava em loop; `excluir_vaga_id` agora é repetível (D9, DT9).
- Entrada com setor cheio não usava a proximidade (D10).
- Normalização da placa (`abc-1d23` vira `ABC1D23`) (D17).
- Saída repetida e ticket inexistente agora têm respostas distintas: 409 e 404 (D18, DT11).
- `/admin/ocupacao` (erro em `func.case`) e rota `/vagas/relatos` capturada por `/{vaga_id}` (D11, D13); imports movidos para o topo dos módulos.
- Nome da equipe: "Equipe 44" passou para "Equipe 43" no backend (D20).
- Entradas concorrentes não recebem mais 400 com vagas livres: nova tentativa (até 5) excluindo as vagas disputadas (R1).
- Saída atômica (`UPDATE ... WHERE saida IS NULL`): saídas simultâneas dão um 200 e um 409, sem sobrescrever o valor (R2).
- `/vagas/disponiveis` e `/setores` não contam nem listam vaga elétrica com carregador indisponível como livre (BUG-01, R3).
- Hora da mensagem de entrada em UTC-3 (BUG-03, R7).
- `scripts/run_newman.py` aborta com mensagem clara se a porta está ocupada ou o uvicorn morre (R5); `scripts/reset_db.py` trata `PermissionError` e o README avisa para parar a API (R8).
- CORS removido (frontend na mesma origem) e `python -m app.main` sobe em `127.0.0.1` (R4).

### Adicionado
- `GET /setores` (somente leitura) com contagem de vagas livres e ocupadas.
- `POST /tickets/{identificador}/saida` (alias da rota da documentação).
- `vaga_id` opcional em `POST /tickets/entrada` para aceitar a vaga sugerida (409 se indisponível).
- Carregador de veículo elétrico muda para `em_uso` ao ocupar e volta a `disponivel` ao liberar; vaga elétrica só é oferecida com carregador disponível.
- Função pura `calcular_cobranca` e `registrar_saida(agora=...)` injetável para testes.
- Suíte pytest em `tests/` (cobrança, tickets, vagas, contadores, proximidade) com banco temporário.
- Coleção Postman v2.1 e ambiente local em `postman/`, validada com Newman.
- Scripts em `scripts/`: `reset_db.py` e `run_newman.py`.
- `CHANGELOG.md` e `README.md` reescrito (como rodar, reset do banco, testes, Postman).

### Alterado
- A API serve o frontend em `/` via `StaticFiles` (mesma origem, sem CORS e sem servidor extra); o JSON que estava em `/` passou para `GET /api/info`.
- Ambiente: requer **Python 3.11 a 3.13** (os pins não instalam no 3.14); o README documenta `py -3.13 -m venv .venv`.
- Banco configurável pela variável de ambiente `CAPIM_DB_URL` (padrão `data/capimparking.db`); `StaticPool` só para banco em memória.
- Seed determinístico (`random.Random(43)`) e tickets de exemplo ativos apenas em vagas comuns.
- `ocupar_vaga`/`liberar_vaga` fazem `UPDATE` condicional e aceitam `commit=False`.
- Versão da API: 2.0.0.

### Frontend
- Tela única acessível servida em `/`: blocos Entrada, Ticket e Saída, sem mapa nem painel admin (F1).
- Seis tipos de vaga em radios nativos com contagem de livres, setor opcional, contadores de livres, ocupadas e elétrico, atualizados a cada 30 s (F2).
- Ticket emitido com vaga, setor, andar, tolerância e valor por hora, horários em Palmas (UTC-3); saída com valor, isenção na tolerância e erros 404 (código inválido) e 409 (saída já registrada) (F3).
- Tokens de cor revisados para WCAG 2.1 AA (texto, foco, bordas, alto contraste), alertas com ícone e texto, barra de acessibilidade estática (F4).
- Alto contraste e tamanho de fonte salvos no navegador; leitura em voz opcional em pt-BR; foco gerenciado e uma única região aria-live (F5).
- Setor cheio: sugestão de vaga próxima com Aceitar, Outra opção (até 3 recusas) e Cancelar; o aceite reserva a vaga mostrada (F6).
- Rodapé com Equipe 43 Aerodactyle; tipo "gestante" removido da interface.
