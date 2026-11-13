# 03 - Design: Tela única do CapimParking (Hackarun 2026, Equipe 43)

Rodada: SOMENTE ANÁLISE/ESPECIFICAÇÃO. Nenhum arquivo do frontend foi alterado. Fonte da verdade: `Downloads\DOCUMENTACAO_PROJETO.md` (seção 3.6). Prazo: ~1 dia (13/11 para 14/11/2026). Contrastes abaixo foram calculados à mão (fórmula WCAG), com erro de até ~0,1.

## 1. Avaliação do frontend atual

Arquivos: `frontend/index.html` (373 linhas) e `frontend/styles.css` (1779 linhas). O HTML referencia `<script src="app.js">`, mas **`app.js` não existe** (404). Correção ao PM: há uma tag script, só que ela aponta para um arquivo ausente. O efeito é o mesmo: nada é operável.

### 1.1 Aderência à seção 3.6

| Item da 3.6 | Atual | Gap |
|---|---|---|
| Interface ÚNICA | 7 `<section>` em wizard (boas-vindas, tipo, setor, ticket, mapa, consulta, admin) | Contradiz a 3.6. Para a demo, colapsar em 1 página com 3 blocos. |
| 6 botões de tipo | Grade vazia ("Rendered by JS") | Sem JS, sem botões. |
| Setor opcional (select) | Grade de cards em tela separada | Trocar por `<select>` conforme wireframe, ou cards na mesma tela. |
| Contadores livres/ocupadas/EV | `.availability-summary` com `--` | Sem dados. Falta rótulo "livres" em `.stat-label` (CSS existe, HTML não usa). |
| Botão "Gerar ticket e entrar" + "Ver mapa" | Existem, em telas diferentes | Mapa é Could, cortar. |
| Alto contraste, Leitura de tela, Libras | Toolbar com contraste, A+, A-, TTS. Sem Libras | Sem JS. Libras é opcional, cortar. |
| Rodapé | Diz "Equipe 44" | Trocar para **Equipe 43 Aerodactyle**. |
| Tipos | O card de info cita "Gestante"; o select do admin tem `gestante` | Decisão D5 do PO: ocultar gestante. Remover do texto. |
| Admin | Tela 7 completa com botão "toque 3 vezes" e botão "Resetar Estacionamento" | Fora de escopo (Won't). Remover da demo: o reset destrutivo exposto sem auth é risco. |

### 1.2 Gaps concretos de WCAG 2.1 AA

Contraste (1.4.3 e 1.4.11), valores aproximados:

| # | Problema | Razão | Critério |
|---|---|---|---|
| C1 | `--color-gray-500` (#9E9E9E), usado em `--color-text-muted` (hints, rodapé, `.spot-type-desc`, `.sector-floor`, placeholder) sobre branco | ~2,7:1 (sobre sand ~2,4:1) | 1.4.3 falha (exige 4,5) |
| C2 | Foco e borda de campo em `--color-gold` (#B5934E) sobre branco/sand | ~2,9:1 e ~2,6:1 | 1.4.11 falha (exige 3:1). Pior: `.form-input:focus` e `select:focus` removem o outline e deixam só borda dourada e sombra 20% |
| C3 | Botão primário em hover (fundo #8B7338, texto #352B25) | ~3,0:1 | 1.4.3 falha |
| C4 | `.high-contrast` troca `--color-primary` para #8B7338 mas mantém `--color-text-on-primary` marrom escuro | ~3,0:1: o alto contraste **piora** o botão primário | 1.4.3 |
| C5 | `.high-contrast` não altera `--color-text-muted`, `--color-border-focus` nem `--color-gray-*` | Muted continua 2,7:1 | 1.4.3 |
| C6 | Bordas de card/tipo (`gray-200` #EEE) sobre branco | ~1,2:1 | 1.4.11: o estado "selecionado" só por cor da borda e fundo claro |
| C7 | `.metric-value.warning` e texto em âmbar (#D9A441) sobre branco | ~2,2:1 | 1.4.3 |
| C8 | `.ticket-status.active` verde (#39845A) sobre `green-bg` | ~4,0:1 | 1.4.3 |
| C9 | Branco sobre vermelho (#C94C4C) em `.btn-danger` | ~4,5:1 (no limite) | só relevante se o botão ficar |

Passam: texto marrom #352B25 sobre branco ou sand (~13:1 e ~12:1), marrom sobre ouro (~4,75:1 no estado normal), branco sobre olive #74715E (~4,9:1), labels do ticket em branco 60% sobre marrom (~6:1).

Semântica e teclado:

| # | Problema | Critério |
|---|---|---|
| S1 | `.spot-type-grid`/`.sector-grid` têm `role="radiogroup"`, mas os filhos (cards) serão criados por JS sem `role="radio"`, `aria-checked` e setas. Padrão simples: usar `<input type="radio">` real com `<label>` | 4.1.2, 2.1.1 |
| S2 | `.a11y-btn span` é `display:none` no desktop e o `aria-label` ("Aumentar tamanho da fonte") difere do texto visível ("A+") no mobile | 2.5.3 (rótulo no nome) |
| S3 | Toolbar `position: fixed` no topo direito (desktop) e embaixo (mobile) pode cobrir conteúdo e o botão de ação, e fica entre o foco e o conteúdo | 2.4.11 (foco não oculto, 2.2) e 1.4.10 (reflow) |
| S4 | `<svg aria-hidden="true" role="img" aria-label>` do logo: atributos contraditórios | 4.1.2 |
| S5 | `role="main"` redundante em `<main>`; `disabled` + `aria-disabled` duplicados nos botões | boas práticas |
| S6 | `.screen {display:none}` + `hidden` + `.active`: `.screen.active{display:flex}` anula o atributo `hidden` | quebra de navegação se JS só trocar um dos dois |
| S7 | Input do código: `pattern="[A-Z0-9]{8}"` com `text-transform: uppercase` só visual. Quem digita minúscula falha na validação nativa. O API gera `uuid4()[:8].upper()` (8 chars hexadecimais) | 3.3.1 |
| S8 | Três regiões `aria-live` concorrentes (`sr-announcer`, `availability-summary`, `toast-container`, `map-info`, `lookup-result`): risco de leitura dupla ou ruidosa | 4.1.3 |
| S9 | `aria-live` em `availability-summary` anuncia todos os contadores a cada atualização | 4.1.3 |
| S10 | Alvos de toque 52-56 px | OK (>=44 px) |
| S11 | `prefers-reduced-motion` já tratado; `:focus-visible` com outline 3 px existe (mas cor falha em C2) | OK |

O que já é bom e deve ser mantido: skip-link, `lang="pt-BR"`, tokens CSS completos, `.sr-only`, `.spinner`, `.empty-state`, `.toast`, `.badge`, `.status-badge`, tamanhos de fonte (`.font-size-*`), `@media print` do ticket, responsivo.

## 2. Decisão de reaproveitamento (tokens e componentes)

Reaproveitar integralmente o `styles.css`. Só criar o que falta. Mudanças em CSS ficam para a rodada de implementação, listadas aqui como "patch de tokens".

### 2.1 Patch de tokens (corrige C1 a C8)

| Token | Hoje | Proposto | Efeito |
|---|---|---|---|
| `--color-text-muted` | `gray-500` #9E9E9E | `gray-700` #616161 (~6,2:1) | C1 |
| `--color-border-focus` | gold #B5934E | **#5C4A1E** (marrom-ouro escuro, ~7,5:1 sobre branco) ou o próprio `--color-deep-brown` | C2 (foco visível) |
| `--color-border` (campos e cards interativos) | `gray-200` | novo `--color-border-strong: #757575` (~4,6:1) usado em `.spot-type-card`, `.form-input`, `.form-select` | C6 |
| `.btn-primary:hover` | fundo gold-dark | manter fundo ouro e escurecer o texto para #1A1A1A, ou hover = fundo marrom #352B25 com texto branco | C3 |
| `.high-contrast` | muda só alguns | adicionar `--color-text-on-primary:#fff` + `--color-primary:#5C4A1E`, `--color-text-muted:#333`, `--color-border-focus:#000`, `--color-border:#000`, `--color-background:#fff`, bordas de card 2px | C4, C5 |
| Texto âmbar | `--color-warning` em texto | usar sempre `--color-warning-text` #7B5B00 (~6:1) | C7 |
| `.ticket-status.active` | `--color-success` | `--color-success-text` #1B5E20 | C8 |

### 2.2 Componentes existentes que serão usados

| Componente (classe) | Uso na tela única |
|---|---|
| `.btn .btn-primary .btn-lg` / `.btn-secondary` / `.btn-full` | Gerar ticket, Registrar saída, Aceitar/Recusar, Tentar de novo |
| `.spot-type-grid` + `.spot-type-card` (+ `.spot-type-availability` com `.low`/`.none`) | 6 tipos de vaga, com contador de livres por tipo |
| `.form-select` | Setor preferencial (wireframe) |
| `.availability-summary .stat` | Livres, Ocupadas, EV |
| `.ticket-card` (+ `.ticket-field`, `.ticket-tolerance`, `.ticket-code-display`, `.ticket-status`) | Ticket emitido e resumo de saída |
| `.form-input` / `.ticket-code-input` | Código na saída |
| `.toast` | Só para erros não bloqueantes; mensagens críticas ficam em `role="alert"` inline |
| `.spinner`, `.empty-state`, `.badge`, `.status-badge` | Carregando, vazio, rótulos |
| `.a11y-toolbar` / `.a11y-btn` | Mantida, ver 5 |
| `@media print` | "Imprimir ticket" (`window.print()`) |

### 2.3 Componentes novos (mínimos)

Justificativa: nada existente cobre estas necessidades.

| Novo | Motivo | Spec |
|---|---|---|
| `.alert` (variantes `.alert-info`, `.alert-warning`, `.alert-error`) | Aviso persistente inline (setor cheio, erro) com ícone + texto + ação. O `.toast` desaparece e não serve para decisão aceitar/recusar | Caixa com borda 2 px (cor semântica), ícone SVG, título, texto, linha de botões. `role="alert"` (erro) ou `role="status"` (info). Nunca só cor: sempre ícone + palavra ("Atenção:", "Erro:") |
| `.suggestion-card` | Mostrar vaga sugerida (setor, andar, vaga, distância, caminhada) | Reusa `.ticket-field` em grade 2 colunas, dentro de `.alert-warning` |
| `.skeleton`/estado de carregando no botão | Evitar duplo envio | `aria-busy="true"` + `.spinner` dentro do botão e texto "Gerando ticket..." |

Sem novas cores nem tipografia. Fonte: Manrope declarada, **sem `@font-face` nem link** (cai para Segoe UI/Arial). Aceitável; não incluir fonte externa (offline/RNF03).

## 3. Spec da tela única

Rota: `/` servida pelo FastAPI (decisão D7 do PO, evita CORS e porta extra). Uma página, 4 blocos em ordem de leitura e de Tab. Sem navegação entre telas, apenas troca de conteúdo no bloco 2 e 3.

```
[skip-link]                                  [toolbar a11y: Contraste | A+ | A- | Ler em voz]
H1 CapimParking - Estacionamento Inteligente    (tagline)
-----------------------------------------------------------------
BLOCO 1  <section aria-labelledby="h-entrada">  "Entrar no estacionamento"
  Fieldset legend "1. Escolha o tipo de vaga"   [Comum][Idoso][PCD][Neuro][Elétrico][Moto]
  Label "2. Setor preferencial (opcional)"       [ Sem preferência v ]
  Resumo (aria-live off; ver 3.3):  47 livres / 120   73 ocupadas   EV 3/8
  [ Gerar ticket e entrar ]                      (Ver mapa: cortado)
  Região de status (aria-live polite)  <- sugestão / erro / ticket aparecem aqui
-----------------------------------------------------------------
BLOCO 2  Resultado da entrada (ticket)          (oculto até existir)
-----------------------------------------------------------------
BLOCO 3  <section> "Já estacionei? Registrar saída"
  Label "Código do ticket" [ ABC12345 ]  [ Ver valor e sair ]
  Resultado da saída (valor, tempo, status)
-----------------------------------------------------------------
Rodapé: Capim Dourado Shopping - Palmas, TO | Hackarun 2026 | Equipe 43 Aerodactyle
```

Ordem de Tab: skip-link, toolbar, tipos (um único tab stop, setas), setor, Gerar ticket, (conteúdo dinâmico), código, botão de saída.

### 3.1 Estados da tela (todos os critérios de aceite do PO)

| Estado | Gatilho | O que o usuário vê | Foco | Anúncio (leitor de tela) |
|---|---|---|---|---|
| E0 Inicial | Abrir página | Tipos sem seleção (nenhum `checked`), setor "Sem preferência", contadores globais, botão "Gerar ticket e entrar" **habilitado mas validando** (ver nota) | Início do documento | Nenhum anúncio de carga (evita ruído) |
| E1 Carregando disponibilidade | Início e a cada 30 s ou mudança de tipo/setor | Skeleton ou `--` nos contadores, texto "Carregando disponibilidade..." | Mantém | `aria-busy` no resumo; ao concluir, anúncio único: "47 vagas livres de 120" (só após ação do usuário, não no polling) |
| E2 Validação | Clicar em "Gerar" sem tipo | `.alert-error` "Escolha um tipo de vaga para continuar" + legend do fieldset em destaque (ícone + texto, não só cor) | Primeiro radio de tipo | `role="alert"` |
| E3 Gerando ticket | Clique válido | Botão desabilitado com `.spinner` e "Gerando ticket..."; campos travados | Permanece no botão (usar `aria-disabled`, não `disabled`, para não perder o foco) | "Gerando ticket..." |
| E4 Ticket emitido (vaga atribuída) | 201 | Bloco 2: `.ticket-card` com status "Ativo" | Foco vai para o título "Seu ticket" (`tabindex="-1"`) | "Ticket emitido. Vaga C-14, setor Azul, Subsolo 1. Código ABC12345." |
| E5 Setor cheio com sugestão | Setor escolhido tem 0 livres do tipo (ver 3.2) | `.alert-warning` + `.suggestion-card` com **[Aceitar vaga]** e **[Outra opção]** | Primeiro botão (Aceitar) | "O setor Azul está cheio para vagas PCD. Sugestão: setor Verde, vaga V-07, Subsolo 1, 40 metros, cerca de 1 minuto a pé." |
| E5b Recusou, nova sugestão | [Outra opção] | Mesmo cartão atualizado; contador "Opção 2" | Primeiro botão | Leitura da nova sugestão |
| E5c Sem mais opções | `/vagas/proximas` 404 | `.alert-error` "Não há mais vagas livres deste tipo" + [Escolher outro tipo] | Botão | `role="alert"` |
| E6 Vazio | Tipo com 0 livres em todo o estacionamento | Cartão do tipo mostra "0" com selo `.none`, rótulo "Esgotado". Ao clicar em Gerar: alert "Nenhuma vaga deste tipo disponível agora. Escolha outro tipo." | Radios | `role="alert"` |
| E7 Erro de API/rede | Falha de fetch ou 5xx | `.alert-error` "Não foi possível conectar ao estacionamento" + [Tentar de novo]. A seleção do usuário é preservada | Botão Tentar de novo | `role="alert"` |
| E8 Erro de negócio | 400/404/422 | Texto de `detail` da API mostrado em `.alert-error` (ver mapa 4.3) | Alert | `role="alert"` |
| E9 Saída: carregando | Enviar código | Botão "Calculando valor..." com spinner, bloqueado | Botão | "Calculando valor..." |
| E10 Saída isenta | `isento=true` | Cartão verde: "Saída liberada. Dentro da tolerância de 15 minutos. Valor: R$ 0,00" | Título do resultado | Leitura da `mensagem` |
| E11 Saída com valor | `isento=false` | Cartão: tempo total, tempo cobrado, **Valor a pagar R$ 10,00**, status "Pagamento pendente". Aviso: "Pagamento simulado nesta demonstração" | Título do resultado | "Permanência 1 h 16 min. Valor a pagar: 10 reais." |
| E12 Código inválido | 404 | "Ticket não encontrado. Confira o código de 8 caracteres." Campo marcado `aria-invalid="true"` + `aria-describedby` | Campo | `role="alert"` |
| E13 Ticket já finalizado | 4xx | "Este ticket já teve a saída registrada." | Campo | `role="alert"` |

Nota E0: não desabilitar "Gerar ticket" por padrão (botão desabilitado sem explicação é falha para leitor de tela). Validar no clique (E2).

### 3.2 Fluxo de setor cheio (H07, versão implementável em 1 dia)

Decisão: **aceita/recusa feita pela UI, antes de chamar `/tickets/entrada`**. Não depende de mudança no backend, só da rota `/vagas/proximas` que já existe com `excluir_vaga_id`.

1. Usuário escolhe tipo e setor X, clica "Gerar".
2. UI já tem `por_setor` de `GET /vagas/disponiveis?tipo=...` (ver 3.4). Se o setor X não aparece ou `livres == 0`, entra no fluxo de sugestão. Senão, vai direto a E3.
3. `GET /vagas/proximas?setor_desejado_id=X&tipo_vaga=T` (+ `excluir_vaga_id=Y` após cada recusa) retorna `vaga`, `distancia_metros`, `tempo_caminhada_minutos`, `mesmo_andar`, `motivo`.
4. **Aceitar** envia `POST /tickets/entrada` com `setor_id` = setor da vaga sugerida (`vaga.setor_id`). O backend atribui "uma vaga livre do tipo naquele setor". Ressalva: pode não ser exatamente a vaga mostrada (a API não aceita `vaga_id`). Para a demo, o ticket mostrado é o real; o cartão de sugestão fala em "setor e andar", e o número exato da vaga só aparece no ticket. Se o PO aprovar um campo `vaga_id` opcional na entrada, a UI passa a enviá-lo sem mudança de layout.
5. **Outra opção** repete o passo 3 com `excluir_vaga_id` = vaga recusada. Máximo de 3 recusas, depois mostra E5c com [Escolher outro tipo].
6. **Cancelar** (terceiro botão, `.btn-secondary`) volta ao E0 com a seleção mantida.

Observação de risco (R4 do PM): como a referência de proximidade é fixa (50,50), a distância pode ser a mesma para vários setores. A UI não deve prometer "o mais perto de você", e sim "uma vaga próxima disponível". Microcopy abaixo respeita isso.

### 3.3 Contadores (resumo)

- Livres e ocupadas: soma de `por_setor[].livres` / `ocupadas` da resposta de `/vagas/disponiveis` (filtrada pelo tipo e setor selecionados). Total = `livres + ocupadas`. Formato do wireframe: "47 livres de 120" e "73 ocupadas".
- EV: `GET /vagas/disponiveis?tipo=eletrico&apenas_com_carregador=true` para livres; total EV = livres + ocupadas por setor com `tipo=eletrico`. Se só houver livres, mostrar "EV: 3 livres".
- Cada ícone vem com texto ("Livres", "Ocupadas", "Elétrico"). Cor nunca é o único indicador.
- O resumo **não** é `aria-live`. Anúncio apenas em ação do usuário (mudar tipo ou setor), para evitar leitura a cada polling.

### 3.4 Lista de setores

Não existe `GET /setores`. Opções:
- **Recomendada (zero backend):** montar o `<select>` a partir de `por_setor` de `/vagas/disponiveis` **sem filtro de tipo**, mas isso omite setores 100% cheios. Por isso, manter no JS uma tabela fixa dos 6 setores do seed (id, nome, andar) como fallback e **sobrepor** os contadores vindos da API. Setor ausente em `por_setor` = 0 livres.
- Melhor (se sobrar tempo, D8 do PO): `GET /setores` somente leitura, já com `vagas_livres`/`vagas_ocupadas` (o schema `SetorResponse` já tem os campos).
- Ids dos setores: confirmar na execução (ordem do seed: Azul, Verde, Amarelo, Vermelho, Roxo, Laranja). Cores hex do seed (#3B82F6 etc.) são só decorativas: **nunca usar a cor como único identificador**; sempre "Azul - Subsolo 1".

### 3.5 Ticket (bloco 2) - campos

Cartão `.ticket-card` (marrom, texto branco; já passa contraste). Campos:

| Campo | Origem | Observação |
|---|---|---|
| Título "Ticket de estacionamento" + selo "Ativo" | fixo | |
| Código (grande, mono, espaçado) | `identificador` | Botão "Copiar código" (clipboard, opcional) |
| Data/hora de entrada | `entrada` | Formatar `dd/mm/aaaa HH:mm` em pt-BR. Atenção: a API usa `utcnow` sem fuso; tratar como UTC e converter para America/Araguaina (UTC-3) |
| Vaga (número) | `vaga.numero` | |
| Setor | `vaga.setor.nome` | |
| Andar | `vaga.setor.andar` | O D4 do PO: usa o andar do seed ("Subsolo 1"), não "Térreo" |
| Tipo | `vaga.tipo` | Rótulo em português |
| Carregador | `vaga.carregador.tipo_conector` | Só se EV |
| Tolerância | `tolerancia_minutos` + `tempo_limite_tolerancia` | "Grátis até 14:35" |
| Valor/hora | `valor_hora` | "R$ 5,00 por hora" |
| Placa (opcional) | `placa` | O campo de placa na entrada está **fora** da tela (cortado); só aparece se vier |
| Mensagem | `mensagem` | Texto auxiliar |

Ações: [Imprimir ticket] (`window.print()`, usa CSS `@media print`), [Nova entrada] (limpa e volta ao E0), [Ouvir ticket] (TTS). Persistir o código em `sessionStorage` para preencher o campo de saída (reduz erro de digitação).

## 4. Mapeamento elemento para endpoint real

Base: mesma origem (`/`). Rotas conferidas em `app/routers/*.py` e `app/schemas.py`.

### 4.1 Tabela

| Elemento de UI | Método e rota | Parâmetros / corpo | Campos usados da resposta |
|---|---|---|---|
| Valores de tolerância/valor-hora exibidos na tela (rodapé do bloco 1 e microcopy) | `GET /config` | nenhum | `tolerancia_minutos`, `valor_hora`, `tempo_maximo_recarga_ev`, `regra_arredondamento` |
| Contadores livres/ocupadas, selo por tipo, lista por setor | `GET /vagas/disponiveis` | `tipo` (valores `comum,idoso,pcd,neurodivergente,eletrico,moto`; verificar se o enum é minúsculo sem acento), `setor_id`, `andar`, `apenas_com_carregador` | `total`, `por_setor[]` (`setor_id`, `setor_nome`, `setor_cor`, `andar`, `livres`, `ocupadas`, `total`), `nivel_confiabilidade`, `atualizado_em` |
| Contador EV | `GET /vagas/disponiveis?tipo=eletrico&apenas_com_carregador=true` | idem | `total` |
| Selo "livres por tipo" nos 6 cartões | 6 chamadas `GET /vagas/disponiveis?tipo=X` (ou 1 sem filtro e agrupar por `vagas[].tipo` no cliente) | idem | `total` ou contagem em `vagas[]` |
| Select de setor | Fallback fixo no JS + `por_setor` | ver 3.4 | `setor_id`, `setor_nome`, `andar` |
| Gerar ticket e entrar | `POST /tickets/entrada` | `{tipo_vaga, setor_id?, placa?}` | `identificador`, `vaga`, `entrada`, `tolerancia_minutos`, `valor_hora`, `tempo_limite_tolerancia`, `mensagem` |
| Cartão de sugestão (setor cheio) | `GET /vagas/proximas` | `setor_desejado_id`, `tipo_vaga`, `excluir_vaga_id?` | `vaga`, `distancia_metros`, `tempo_caminhada_minutos`, `mesmo_andar`, `motivo` |
| Aceitar sugestão | `POST /tickets/entrada` | `{tipo_vaga, setor_id: vaga.setor_id}` | idem entrada |
| Outra opção | `GET /vagas/proximas` | acrescenta `excluir_vaga_id` | idem |
| Ver valor e sair | `POST /tickets/saida` | `{identificador}` (alias `/tickets/{id}/saida` se o PO aprovar D1; a UI deve usar a rota atual) | `tempo_total_minutos`, `tempo_faturavel_minutos`, `valor`, `status_pagamento`, `isento`, `mensagem`, `entrada`, `saida` |
| Consultar ticket (opcional, "Ver meu ticket" no bloco 3) | `GET /tickets/{identificador}` | | `vaga`, `entrada`, `valor_hora`, `tempo_tolerancia_minutos`, `status_pagamento` |
| Detectar API fora do ar | `GET /health` | | `status`, `database` |
| "Marcar como pago" (simulado) | `POST /tickets/{identificador}/pagar` | | só se sobrar tempo; senão texto "Pagamento simulado" |

### 4.2 Pontos de atenção que afetam a UI

- **Entrada hoje devolve 500** (NameError de `VagaResponse`, achado R1). A UI não pode ser validada até a correção. Tratar qualquer 5xx como E7.
- `GET /vagas/disponiveis` omite setor sem livre (H04). A UI deve tratar ausência como 0 e usar o fallback de 3.4.
- `GET /vagas/relatos` está sombreada por `/vagas/{id}`; não usar.
- Não há consulta por placa (H10); o campo de busca é só por código.
- Campo `placa` do schema exige `^[A-Z0-9]{1,10}$` **sem hífen**. O campo de placa (se existir) deve remover hífen e espaço e converter para maiúsculas antes de enviar. Recomendação: **não incluir placa na tela** (corte), reduz fricção e LGPD.
- Erros do FastAPI chegam em `{"detail": "..."}` (400/404) ou `{"detail":[{loc,msg}]}` (422). A UI deve tratar os dois formatos (string ou lista) e nunca exibir JSON cru.
- Datas sem fuso (naive UTC): converter na exibição.
- O seed não tem vagas de moto (H05); com o seed atual o cartão Moto fica "Esgotado" (E6) e a entrada falha 400.

### 4.3 Mensagens de erro da API para microcopy

| Origem | Mostrar |
|---|---|
| 400 na entrada (sem vaga do tipo) | "Não há vagas livres deste tipo agora. Escolha outro tipo ou tente mais tarde." |
| 404 em `/tickets/saida` | "Ticket não encontrado. Confira o código." |
| 4xx saída repetida | "Este ticket já teve a saída registrada." |
| 422 | "Algum dado está incorreto. Revise as opções e tente de novo." |
| 5xx / sem rede | "Não foi possível falar com o estacionamento. Tente de novo em instantes." |

## 5. Microcopy (pt-BR)

| Local | Texto |
|---|---|
| H1 | Estacionamento Inteligente - Capim Dourado Shopping |
| Tagline | Estacione com inteligência. Aproveite sem preocupação. |
| Legend dos tipos | 1. Escolha o tipo de vaga |
| Tipos (nome / descrição curta) | Comum / Uso geral. Idoso / Prioridade 60+. PCD / Pessoa com deficiência. Neurodivergente / Ambiente mais tranquilo. Elétrico / Com carregador. Moto / Vaga de moto |
| Label do setor | 2. Setor preferencial (opcional). Opção padrão: Sem preferência |
| Resumo | "47 livres de 120" / "73 ocupadas" / "Elétrico: 3 de 8 livres" |
| Selo no cartão | "47 livres" / "Poucas (3)" / "Esgotado" (poucas: menos de 5, ou 10% do total) |
| Botão principal | Gerar ticket e entrar |
| Botão ocupado | Gerando ticket... |
| Carregando contadores | Carregando disponibilidade... |
| Sucesso entrada (anúncio) | Ticket emitido. Vaga {numero}, setor {setor}, {andar}. Seu código é {codigo}. Você tem {tol} minutos grátis. |
| Aviso de setor cheio | O setor {X} está cheio para vagas {tipo}. Encontramos uma vaga perto de lá. |
| Sugestão | Setor {Y}, {andar}. A cerca de {d} metros ({m} min a pé). |
| Botões da sugestão | Aceitar vaga / Outra opção / Cancelar |
| Sem mais opções | Não há mais vagas livres deste tipo. Escolha outro tipo de vaga. |
| Saída: título | Já estacionei? Registrar saída |
| Saída: label | Código do ticket (8 letras e números) |
| Saída: botão | Ver valor e sair |
| Saída: ocupado | Calculando valor... |
| Isenta | Saída liberada. Você ficou {t} min, dentro da tolerância. Nada a pagar. |
| Com valor | Você ficou {t}. Valor a pagar: R$ {v}. Pagamento simulado nesta demonstração. |
| Erro de rede | Não foi possível falar com o estacionamento. [Tentar de novo] |
| Rodapé | Capim Dourado Shopping - Palmas, TO | Hackarun 2026 | Equipe 43 Aerodactyle |

Regras: frases curtas, voz ativa, sem jargão ("ticket" é aceito), valores monetários como "R$ 10,00" no texto e "10 reais" na fala (TTS).

## 6. Checklist de acessibilidade (para a implementação)

### 6.1 Contraste e visual
- [ ] Texto normal >= 4,5:1; texto grande (>=24 px ou >=19 px negrito) >= 3:1; componentes e foco >= 3:1 (1.4.11).
- [ ] Aplicar o patch de tokens (2.1). Verificar com um verificador de contraste nos dois temas.
- [ ] Estado nunca só por cor: selecionado = borda 3 px + ícone de check + `aria-checked`; esgotado = texto "Esgotado"; erro = ícone + palavra "Erro:".
- [ ] Alto contraste (botão "Contraste"): fundo #FFF, texto #000, bordas 2 px #000, foco #000 + halo branco; persistir em `localStorage` (a demo pode ser reaberta). Respeitar `prefers-contrast: more` na primeira visita.
- [ ] Fonte A+/A-: 3 níveis já existem (`.font-size-small/large/xlarge`); aplicar na `<html>`; persistir; layout sem rolagem horizontal até 200% de zoom.

### 6.2 Teclado e foco
- [ ] Tudo operável por Tab, Shift+Tab, Enter, Espaço, setas (radios) e Esc (fecha sugestão, volta ao botão principal).
- [ ] Tipos de vaga com `<input type="radio" name="tipo">` + `<label>`; um tab stop, setas mudam. `fieldset` + `legend`.
- [ ] Foco visível 3 px, cor com contraste (patch C2), `outline-offset: 2px`; remover `outline:none` de `.form-input:focus` e `.form-select:focus` sem substituto equivalente.
- [ ] Gestão de foco: ao surgir ticket, sugestão, erro ou resultado de saída, mover foco para o título/alert correspondente (`tabindex="-1"`). Após "Nova entrada", foco no primeiro tipo.
- [ ] Sem armadilha de foco. Sem modal (usar blocos inline).
- [ ] Atalhos opcionais (só com tempo): `Alt+G` gerar ticket. Documentar na página. Não conflitar com leitores de tela (preferir nenhum atalho a um atalho ruim).
- [ ] Ordem do DOM = ordem visual. Toolbar deve ficar no início do DOM e **não** `position: fixed` sobre conteúdo (S3); usar barra estática no topo.

### 6.3 Leitores de tela e `aria-live`
- [ ] **Uma** região `aria-live="polite"` global (`#sr-announcer`, já existe) para mensagens de progresso e sucesso. Remover `aria-live` de `availability-summary`, `map-info`, `lookup-result`, `toast-container` (evita leitura duplicada).
- [ ] Erros bloqueantes em `role="alert"` (assertivo), uma por vez.
- [ ] Mensagens a anunciar: carregando, ticket emitido, sugestão de setor cheio, recusa, valor da saída, erro. Texto completo vem dos campos `mensagem` da API ou da microcopy (seção 5).
- [ ] Botões em carregamento: `aria-busy="true"` e `aria-disabled="true"` (sem `disabled`).
- [ ] Campos: `label` visível associado, `aria-describedby` para a dica, `aria-invalid="true"` + mensagem de erro ligada. Corrigir `pattern` (S7): remover `pattern`, normalizar para maiúsculas via JS e validar `^[A-Z0-9]{8}$` no envio.
- [ ] Rótulo acessível contém o visível (2.5.3): usar texto visível ("Alto contraste", "Aumentar fonte", "Diminuir fonte", "Ler em voz") e remover `aria-label` divergente. Mostrar o texto também no desktop.
- [ ] Ícones decorativos `aria-hidden="true"`; logo: ou `role="img"` + `aria-label`, ou `aria-hidden`, nunca os dois.
- [ ] Remover `role="main"` e `role="radiogroup"` desnecessários.
- [ ] Um único `<h1>`; blocos com `<h2>`. Ticket usa `<dl>` (termos/valores) em vez de divs soltas.
- [ ] Valor e hora legíveis: `<time datetime>` para datas; "R$ 10,00" em texto, não imagem.

### 6.4 Leitura em voz (TTS, Web Speech API)
- [ ] Botão "Ler em voz" na toolbar (`aria-pressed`). Implementação: `speechSynthesis.cancel()` e `new SpeechSynthesisUtterance(texto)` com `lang = 'pt-BR'`; escolher voz `pt-BR` se existir; `rate` 0.9.
- [ ] O que lê: (a) resumo do ticket emitido, (b) sugestão de setor cheio, (c) resultado da saída, (d) erros. Não ler a página inteira nem os contadores a cada atualização.
- [ ] O texto falado é montado a partir de dados (não do DOM), sem emojis nem siglas: "PCD" vira "pessoa com deficiência", "EV" vira "elétrico", "R$ 10,00" vira "10 reais", códigos soletrados ("A, B, C, 1, 2, 3, 4, 5") com `aria-hidden`-safe.
- [ ] Botão "Parar" (cancelar leitura) acessível; `Esc` cancela.
- [ ] Detecção de suporte: se `!('speechSynthesis' in window)`, desabilitar o botão com `aria-disabled` e texto "Leitura em voz indisponível neste navegador" (nunca falha silenciosa).
- [ ] TTS não substitui `aria-live`: mensagens importantes continuam anunciadas ao leitor de tela. Cuidado com fala dupla quando um leitor de tela está ativo (por isso o TTS é opt-in).
- [ ] Browsers carregam vozes de forma assíncrona (`onvoiceschanged`): tratar.
- [ ] Autoplay: falar só após ação do usuário.

### 6.5 Alvo de toque e responsividade
- [ ] Alvos >= 44x44 px (já 52-56 px). Espaçamento entre alvos >= 8 px.
- [ ] Layout para totem (>=1024 px, fonte base 18 px), tablet e celular (>=320 px). `spot-type-grid`: 6 colunas no desktop, 3 no tablet, 2 no celular (já no CSS).
- [ ] Reflow 320 px sem rolagem horizontal (1.4.10), exceto o `.ticket-field` em coluna única (já no CSS).
- [ ] Respeitar `prefers-reduced-motion` (já existe).
- [ ] Sem timeout de sessão; se houver polling, não reiniciar o foco.

### 6.6 Teste manual mínimo (30 min)
1. Fluxo inteiro só com teclado (entrada, sugestão, saída).
2. NVDA (Windows) com Firefox/Chrome: ouvir os anúncios dos estados E4, E5, E7, E10, E11.
3. Zoom 200% e 320 px de largura.
4. Alto contraste ligado em cada estado.
5. TTS em Chrome e Edge (as vozes pt-BR existem no Windows).
6. Lighthouse (acessibilidade) e axe DevTools: meta >= 95 sem violações críticas.

## 7. Plano e corte por prazo (~1 dia)

Dependência crítica: o backend precisa emitir ticket (R1) e ter moto no seed. O frontend pode ser desenvolvido em paralelo contra a API; os estados de erro cobrem as falhas.

### 7.1 Entra (ordem sugerida, ~6 a 8 h de frontend)
1. (1 h) Reduzir `index.html` a uma página: remover telas 5 (mapa), 6 (consulta separada), 7 (admin), botão `btn-admin-access`; corrigir "Equipe 43"; remover "Gestante".
2. (2 h) `app.js` mínimo: `fetch` de `/vagas/disponiveis` e `/config`, render dos 6 tipos + select de setor + contadores, estados E0 a E3, E6, E7.
3. (1,5 h) Entrada e ticket (E4), saída e valor (E9 a E13) com o cartão de ticket.
4. (1 h) Patch de tokens (2.1) e `.alert`, `.suggestion-card`.
5. (1 h) Acessibilidade: radios nativos, foco gerenciado, `aria-live` único, rótulos da toolbar, alto contraste corrigido, TTS (6.4).
6. (1 h) Setor cheio com aceitar/recusar (E5) **somente se** a entrada estiver estável.
7. (0,5 h) Teste manual (6.6) e ensaio da demo.

### 7.2 Cortar (Won't/Could nesta rodada)
- Mapa interativo e botão "Ver mapa" (tela 5 inteira, 130+ linhas de CSS de mapa).
- Painel administrativo, gráficos, abas e "Resetar Estacionamento" (risco em demo pública).
- Consulta por placa, campo de placa na entrada, histórico de tickets, "Marcar como pago".
- Libras (avatar), tempo máximo de recarga EV com alerta (H08 além de "só vagas com carregador"), notificação.
- Animação/transições além das já existentes, ícones novos, fonte web.
- Tela de boas-vindas com cards informativos (o texto de tolerância passa a uma linha no bloco 1).

### 7.3 Se faltar tempo, degradar assim
- Sem E5 interativo: mostrar só o `.alert-info` "Setor cheio, vaga alocada em Y" depois do ticket (versão mínima da D3 do PO) e ensinar o aceitar/recusar via Swagger.
- Sem TTS completo: manter só "Ler ticket" (um botão no cartão).
- Sem polling: atualizar os contadores só ao carregar e após cada entrada ou saída.

## 8. Perguntas para o PO (não bloqueantes)
1. A entrada pode aceitar `vaga_id` opcional para respeitar a vaga aceita na sugestão? Hoje a UI só garante o setor.
2. O `GET /setores` somente leitura entra? Sem ele, a lista de setores vem de um fallback fixo.
3. Moto: confirmar a criação das vagas no seed (D6); sem isso, o cartão Moto fica esgotado na demo.
4. Fuso horário: confirmar exibição em horário de Palmas (UTC-3).
