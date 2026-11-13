# 05 - Dev Frontend: v2.0 (Trilho F, F1 a F6)

Escopo tocado: somente `frontend/` (`index.html`, `styles.css`, `app.js` novo). Sem dependências, sem CDN, sem build. A API é servida na mesma origem (A7), então todos os `fetch` usam caminhos relativos.

## 1. O que foi feito por tarefa

| Tarefa | Commit | Resultado |
|---|---|---|
| F1 | `bf09cfc` | `index.html` reduzido a 1 página: skip-link, toolbar estática, `<h1>` único, 3 blocos (`h2`): Entrada, Ticket, Saída. 6 radios nativos (sem gestante, D5), `<select>` de setor, resumo com rótulos. Removidos mapa, consulta separada, admin, `btn-admin-access` e toast container. Rodapé "Equipe 43 Aerodactyle". |
| F2 | `47f84a0` | `app.js`: `api()` (mesma origem, `detail` string ou lista, erros `rede`/`servidor`/`negocio`), `/config`, `/vagas/disponiveis`, tipos com selo, setores (fallback ids 1 a 6 + `por_setor`), contadores, polling de 30 s só com a aba visível. Estados E0, E1, E2, E3, E6, E7. |
| F3 | `d72ca4a` | Ticket (E4) em `dl`/`time`, datas naive UTC convertidas para `America/Araguaina`, código em `sessionStorage` (preenche o campo de saída), imprimir, nova entrada. Saída (E9 a E13) por `POST /tickets/saida`. |
| F4 | `83464ea` | Patch de tokens do Design 2.1 (C1 a C8), `.alert`, `.suggestion-card`, toolbar estática, radios com check visível e borda 3 px, foco com cor escura, impressão só do ticket. |
| F5 | `ede2e80` | Alto contraste e tamanho de fonte persistidos (`localStorage`, respeita `prefers-contrast`), TTS opt-in, Esc, foco gerenciado. |
| F6 | `b64924c` | Setor cheio com Aceitar vaga, Outra opção, Cancelar. A11 já estava no backend (`e0cc535`), então a UI envia `vaga_id`. |

## 2. Estados implementados

| Estado | Como aparece |
|---|---|
| E0 | Nenhum tipo marcado, setor "Sem preferência", botão habilitado (valida no clique). |
| E1 | `--` e "Carregando disponibilidade..."; `aria-busy` no resumo; polling silencioso (sem anúncio). Anúncio único após mudar tipo ou setor. |
| E2 | Mensagem "Erro: Escolha um tipo..." com `role="alert"`, legend em vermelho sublinhado, foco no primeiro radio. |
| E3 | Botão com spinner e "Gerando ticket...", `aria-busy` + `aria-disabled` (sem `disabled`, foco preservado), campos travados. |
| E4 | Cartão do ticket, foco em "Seu ticket" (`tabindex=-1`), anúncio com vaga, setor, andar, código e tolerância. |
| E5 / E5b / E5c | Alerta de atenção com cartão da sugestão (setor, andar, vaga, distância, a pé), "Opção N de 4", 3 recusas no máximo, depois "Não há mais vagas..." com [Escolher outro tipo]. 404 de `/vagas/proximas` também leva ao E5c. 409 no aceite busca nova opção. |
| E6 | Selo "Esgotado" no cartão; no clique, alerta "Nenhuma vaga deste tipo disponível agora" sem chamar a API. |
| E7 | Falha de rede ou 5xx: alerta com [Tentar de novo]; seleção preservada. Também na carga inicial, na sugestão e na saída. |
| E8 | 400 vira a microcopy de "sem vaga"; 422 vira "Algum dado está incorreto"; outros mostram `detail`. Nunca JSON cru. |
| E9 | "Calculando valor..." com spinner. |
| E10 / E11 | Cartão "Saída liberada" (isento) ou "Valor a pagar" com tempo total, tempo cobrado, valor, "Pagamento pendente" e aviso de pagamento simulado. |
| E12 | 404: "Ticket não encontrado. Confira o código de 8 caracteres.", `aria-invalid` + `aria-describedby`. Formato inválido tem mensagem própria. |
| E13 | 409 (e 400 por compatibilidade): "Este ticket já teve a saída registrada." |

## 3. Checklist de acessibilidade (6.1 a 6.5 do Design, revisão estática + teste em Chrome headless)

Legenda: OK = implementado e verificado; PARCIAL = implementado, falta verificação manual.

### 6.1 Contraste e visual
- [PARCIAL] Contrastes: tokens corrigidos por cálculo (muted #616161 ~6,2:1; foco #5C4A1E ~7,5:1; borda forte #757575 ~4,6:1; hover do primário marrom com texto branco; texto âmbar e verde com os `*-text`; contador EV em marrom). Não rodei Lighthouse/axe.
- [OK] Patch de tokens do Design 2.1 aplicado, incluindo `.high-contrast` e `prefers-contrast` (texto primário branco sobre #5C4A1E).
- [OK] Estado nunca só por cor: selecionado = borda 3 px + ícone de check + radio `:checked`; esgotado = texto "Esgotado"; erro/aviso = ícone + "Erro:"/"Atenção:".
- [OK] Alto contraste persistido em `localStorage`; respeita `prefers-contrast: more` na primeira visita. Fundo branco, bordas 2 px pretas, foco preto com halo branco.
- [OK] Fonte A+/A-: 4 níveis (87,5%, 100%, 112,5%, 125%) persistidos. Desvio: aplicado como `font-size` percentual no `<html>` em vez das classes `.font-size-*`, porque as classes só mudam `--font-size-base` e não escalam títulos nem espaçamentos. As classes continuam no CSS sem uso.

### 6.2 Teclado e foco
- [OK] Radios nativos `name="tipo"` dentro de `fieldset`/`legend`: um tab stop, setas mudam a seleção.
- [OK] `outline:none` removido de `.form-input:focus` e `.form-select:focus`; `:focus-visible` com 3 px, offset 2 px; cartões de tipo usam `:has(input:focus-visible)`.
- [OK] Foco gerenciado: ticket (h2), alerta/primeiro botão, resultado da saída (h3), campo de código em erro, primeiro radio após erro de tipo e após "Nova entrada".
- [OK] Esc: cancela a fala e fecha sugestão/alerta de entrada devolvendo o foco ao botão principal.
- [OK] Sem modal e sem armadilha de foco.
- [OK] Toolbar estática no início do DOM (sem `position: fixed`).
- [Não feito, opcional] Atalho `Alt+G`.
- [PARCIAL] Fluxo inteiro só com teclado: elementos todos nativos (button, input, select), validado por script que aciona os mesmos handlers; não testado com teclado físico.

### 6.3 Leitores de tela e aria-live
- [OK] Uma região `aria-live="polite"` (`#sr-announcer`). Removidos `aria-live` do resumo, mapa, consulta e toast.
- [OK] Erros em `role="alert"`, um por vez (`#entrada-status`, `#saida-status`, `#tipo-erro`, `#codigo-erro`); avisos informativos em `role="status"`.
- [OK] Botões ocupados: `aria-busy="true"` + `aria-disabled="true"`, sem `disabled`.
- [OK] Campos com `label` visível, `aria-describedby`, `aria-invalid`; `pattern` removido, código normalizado para maiúsculas e validado com `^[A-Z0-9]{8}$` no envio.
- [OK] Rótulos da toolbar com texto visível igual ao nome acessível (sem `aria-label` divergente), visíveis também no desktop.
- [OK] Ícones `aria-hidden`; logo apenas `aria-hidden` (sem `role="img"` junto); sem `role="main"` nem `radiogroup`.
- [OK] Um `<h1>`, blocos com `<h2>`, ticket em `<dl>`, datas em `<time datetime>`.
- [PARCIAL] Anúncios dos estados E4, E5, E7, E10, E11 por NVDA: não testado (ver "Como testar").

### 6.4 Leitura em voz
- [OK] Botão "Ler em voz" com `aria-pressed`, opt-in; `speechSynthesis.cancel()` antes de falar, `lang pt-BR`, voz pt-BR quando existe, `rate` 0,9, `voiceschanged` tratado.
- [OK] Lê ticket emitido, sugestão, saída e erros/avisos; não lê contadores nem a página. Texto montado a partir dos dados: PCD vira "pessoa com deficiência", valores viram "10 reais", código soletrado.
- [OK] Esc cancela. Desligar o botão cancela a fala.
- [OK] Sem suporte: botão com `aria-disabled` e texto "Leitura em voz indisponível neste navegador".
- [OK] Só fala após ação do usuário. Botão "Ouvir ticket" fala sob demanda.
- Desvio: não há botão "Parar" separado; o botão "Ler em voz" desliga e para a leitura, e Esc também.

### 6.5 Alvos e responsividade
- [OK] Alvos de 56 px (token existente), grid de tipos 6/3/2 colunas, impressão só do ticket.
- [PARCIAL] Reflow a 320 px e zoom 200%: não verificado visualmente; layout em grid/flex com `min-width: 0`.

## 4. Desvios da spec

1. Fonte A+/A-: percentual no `<html>` (ver 6.1).
2. A mensagem do servidor (`mensagem`) não é exibida no ticket nem na saída. Motivo: o backend escreve o limite de tolerância em UTC ("até 20:00") enquanto a UI mostra o horário de Palmas ("Grátis até 17:00"); exibir os dois confundiria. A UI monta o texto a partir dos campos estruturados.
3. Nenhuma fonte "Libras", mapa, admin ou placa (cortes do Design 7.2).
4. Contagem por tipo nos cartões usa `vagas[]` de `/vagas/disponiveis` agrupado por `tipo` (1 chamada). Tipos "poucas": menos de 5 livres.
5. CSS morto (mapa, admin, tabs, toast) foi mantido para não arriscar regressão em 1 dia; pode ser podado depois.
6. Vagas `gestante` do seed contam no total do resumo global (sem tipo), mas não têm cartão (D5).

## 5. Observações para o backend e a QA

- `TicketEntradaResponse.mensagem` e `TicketSaidaResponse.mensagem` usam horário UTC no texto (ex.: "até 20:00" com entrada às 16:45 em Palmas). Vale corrigir ou deixar como está, já que a UI não exibe.
- Seleção PCD + setor Amarelo (0 vagas PCD) dispara a sugestão; no seed atual, a primeira opção foi Verde ou Azul conforme o estado do banco.
- `vaga_id` é enviado ao aceitar sugestão; o 409 (vaga ocupada nesse meio tempo) é tratado buscando outra opção.

## 6. Como testar manualmente

```
set CAPIM_DB_URL=sqlite:///C:/caminho/qualquer/teste.db
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001
```
Abrir `http://127.0.0.1:8001/`.

1. Contadores carregam, 6 tipos com selo, 6 setores no select.
2. "Gerar ticket e entrar" sem tipo: erro e foco no primeiro radio.
3. Escolher Comum, gerar: ticket aparece com foco no título; o código vem preenchido na saída.
4. "Ver valor e sair": cartão "Saída liberada" (R$ 0,00). Repetir: erro 409. Código `ZZZZZZZZ`: 404.
5. PCD + Amarelo: sugestão; "Outra opção" até o limite (E5c); "Aceitar vaga" gera ticket na vaga mostrada.
6. Moto: 10 vagas no Laranja no seed atual.
7. Alto contraste e A+/A-: recarregar a página e conferir a persistência.
8. "Ler em voz": gerar um ticket e ouvir (Chrome/Edge com voz pt-BR).
9. Parar a API e recarregar: alerta com "Tentar de novo".
10. NVDA, zoom 200%, 320 px, Lighthouse/axe (item 6.6 do Design).

## 7. Validações executadas

- `node --check frontend/app.js` OK em cada commit.
- API real em porta 8001 com banco no scratchpad: `/`, `/app.js`, `/styles.css`, `/health`, `/config` retornam 200.
- Chrome headless (CDP) contra a API real: contadores (345 livres de 356; EV 13), selos por tipo, setores com "(cheio)", E2, sugestão com foco no "Aceitar vaga", Outra opção ("Opção 2 de 4"), aceite gerando ticket, foco no título do ticket, saída isenta, 404 com `aria-invalid`, formato inválido, alto contraste + fonte persistidos, TTS desligado por padrão. Sem exceções no console. E7 validado com a página servida sem API.

## 8. Pendências

- Verificação manual com NVDA, Lighthouse/axe, zoom 200% e 320 px (itens 6.6 do Design).
- F7 (ensaio da demo 2 vezes) é do coordenador/QA.
- Podar o CSS morto e remover `.font-size-*` não usadas.
- Atalho `Alt+G` não implementado (opcional).
- Aviso de EV com tempo máximo de recarga (H08) fora do escopo.
