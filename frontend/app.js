/*
 * CapimParking - tela única (Hackarun 2026, Equipe 43 Aerodactyle)
 * JS vanilla, sem dependências. A API é servida na mesma origem (caminhos relativos).
 *
 * Seções:
 *   1. Constantes e utilitários
 *   2. Cliente da API
 *   3. Alertas, foco e anúncios
 *   4. Disponibilidade (contadores, tipos, setores)      [F2]
 *   5. Entrada                                           [F2]
 *   6. Ticket emitido                                    [F3]
 *   7. Saída                                             [F3]
 *   8. Acessibilidade (contraste, fonte, voz)            [F5]
 *   9. Setor cheio: sugerir, aceitar, outra opção        [F6]
 */
(function () {
    'use strict';

    /* ======================================================================
     * 1. Constantes e utilitários
     * ==================================================================== */
    const TIPOS = ['comum', 'idoso', 'pcd', 'neurodivergente', 'eletrico', 'moto'];
    const ROTULO_TIPO = {
        comum: 'Comum',
        idoso: 'Idoso',
        pcd: 'PCD',
        neurodivergente: 'Neurodivergente',
        eletrico: 'Elétrico',
        moto: 'Moto'
    };
    // Fallback fixo dos setores do seed (ordem Azul..Laranja). A API sobrepõe nome/andar.
    const SETORES_FALLBACK = [
        { id: 1, nome: 'Azul', andar: 'Subsolo 1' },
        { id: 2, nome: 'Verde', andar: 'Subsolo 1' },
        { id: 3, nome: 'Amarelo', andar: 'Subsolo 1' },
        { id: 4, nome: 'Vermelho', andar: 'Subsolo 2' },
        { id: 5, nome: 'Roxo', andar: 'Subsolo 2' },
        { id: 6, nome: 'Laranja', andar: 'Subsolo 2' }
    ];
    const POLL_MS = 30000;
    const POUCAS_VAGAS = 5;
    const MAX_RECUSAS = 3;
    const FUSO = 'America/Araguaina'; // UTC-3, horário de Palmas

    const MSG = {
        rede: 'Não foi possível falar com o estacionamento. Tente de novo em instantes.',
        semVaga: 'Não há vagas livres deste tipo agora. Escolha outro tipo ou tente mais tarde.',
        esgotado: 'Nenhuma vaga deste tipo disponível agora. Escolha outro tipo.',
        validacao: 'Algum dado está incorreto. Revise as opções e tente de novo.',
        escolhaTipo: 'Escolha um tipo de vaga para continuar.'
    };

    const $ = (id) => document.getElementById(id);

    const state = {
        config: null,
        glob: null,        // GET /vagas/disponiveis (sem filtro)
        ev: null,          // GET /vagas/disponiveis?tipo=eletrico&apenas_com_carregador=true
        selTipo: null,     // GET /vagas/disponiveis?tipo=<selecionado>
        setores: new Map(),// id -> {id, nome, andar}
        ocupado: false
    };
    let ultimoTicket = null;
    let sugestao = null; // {tipo, setorId, excluidas[], recusas, atual}

    const el = {
        form: $('form-entrada'),
        fsTipos: $('fs-tipos'),
        legendTipos: $('legend-tipos'),
        tipoErro: $('tipo-erro'),
        setor: $('setor-select'),
        statFree: $('stat-free'),
        statOcc: $('stat-occupied'),
        statEv: $('stat-ev'),
        resumo: $('availability-summary'),
        dispStatus: $('disp-status'),
        btnGerar: $('btn-gerar'),
        entradaStatus: $('entrada-status'),
        configInfo: $('config-info'),
        announcer: $('sr-announcer'),
        blocoTicket: $('bloco-ticket'),
        tituloTicket: $('h-ticket'),
        ticketCard: $('ticket-card'),
        btnImprimir: $('btn-imprimir'),
        btnNovaEntrada: $('btn-nova-entrada'),
        formSaida: $('form-saida'),
        codigo: $('codigo-input'),
        codigoErro: $('codigo-erro'),
        btnSaida: $('btn-saida'),
        saidaStatus: $('saida-status')
    };
    const CHAVE_CODIGO = 'capim.ultimoTicket';

    const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
    const formatarMoeda = (v) => brl.format(Number(v) || 0).replace(/ /g, ' ');

    function plural(n, um, varios) {
        return n === 1 ? um : varios;
    }

    // PCD é sigla e mantém caixa alta; os demais vão em minúsculas no meio da frase.
    function tipoTexto(tipo) {
        return tipo === 'pcd' ? 'PCD' : ROTULO_TIPO[tipo].toLowerCase();
    }

    function tipoSelecionado() {
        const r = document.querySelector('input[name="tipo"]:checked');
        return r ? r.value : '';
    }

    function setorSelecionado() {
        return el.setor.value ? Number(el.setor.value) : null;
    }

    function nomeSetor(id) {
        const s = state.setores.get(Number(id));
        return s ? s.nome : 'Setor ' + id;
    }

    /* ======================================================================
     * 2. Cliente da API
     * ==================================================================== */
    class ApiError extends Error {
        constructor(kind, status, detail) {
            super(detail || kind);
            this.kind = kind;     // 'rede' | 'servidor' | 'negocio'
            this.status = status;
            this.detail = detail || '';
        }
    }

    // detail pode ser string (400/404/409) ou lista [{loc,msg}] (422). Nunca JSON cru.
    function formatarDetail(detail) {
        if (typeof detail === 'string') return detail;
        if (Array.isArray(detail)) {
            return detail.map((d) => (d && d.msg) ? d.msg : '').filter(Boolean).join('; ');
        }
        return '';
    }

    async function api(path, options) {
        const opts = Object.assign({}, options);
        const headers = { Accept: 'application/json' };
        if (opts.json !== undefined) {
            headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(opts.json);
            delete opts.json;
        }
        opts.headers = headers;
        let resp;
        try {
            resp = await fetch(path, opts);
        } catch (e) {
            throw new ApiError('rede', 0, '');
        }
        let data = null;
        try {
            const txt = await resp.text();
            data = txt ? JSON.parse(txt) : null;
        } catch (e) {
            data = null;
        }
        if (!resp.ok) {
            throw new ApiError(resp.status >= 500 ? 'servidor' : 'negocio', resp.status,
                formatarDetail(data && data.detail));
        }
        return data;
    }

    function consulta(params) {
        const q = new URLSearchParams();
        Object.keys(params).forEach((k) => {
            const v = params[k];
            if (Array.isArray(v)) v.forEach((x) => q.append(k, x));
            else if (v !== undefined && v !== null && v !== '') q.append(k, v);
        });
        const s = q.toString();
        return s ? '?' + s : '';
    }

    // Datas da API são naive UTC (sem fuso): tratar como UTC.
    function paraData(iso) {
        if (!iso) return null;
        const s = String(iso);
        return new Date(/([zZ]|[+-]\d\d:?\d\d)$/.test(s) ? s : s + 'Z');
    }

    function formatarDataHora(iso) {
        const d = paraData(iso);
        if (!d || isNaN(d)) return '';
        return new Intl.DateTimeFormat('pt-BR', {
            timeZone: FUSO, day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
        }).format(d).replace(', ', ' ');
    }

    function formatarHora(iso) {
        const d = paraData(iso);
        if (!d || isNaN(d)) return '';
        return new Intl.DateTimeFormat('pt-BR', {
            timeZone: FUSO, hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
        }).format(d);
    }

    /* ======================================================================
     * 3. Alertas, foco e anúncios
     * ==================================================================== */
    const ICONES = {
        error: '<svg aria-hidden="true" focusable="false" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 7v6M12 16.5v.5"/></svg>',
        warning: '<svg aria-hidden="true" focusable="false" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.5"/></svg>',
        info: '<svg aria-hidden="true" focusable="false" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 11v6M12 7.5v.5"/></svg>',
        success: '<svg aria-hidden="true" focusable="false" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M7 12.5l3.5 3.5L17 9"/></svg>'
    };
    const PREFIXO = { error: 'Erro:', warning: 'Atenção:', info: 'Aviso:', success: 'Pronto:' };

    function criar(tag, classe, texto) {
        const n = document.createElement(tag);
        if (classe) n.className = classe;
        if (texto !== undefined) n.textContent = texto;
        return n;
    }

    function limpar(container) {
        while (container.firstChild) container.removeChild(container.firstChild);
    }

    /**
     * Renderiza um alerta persistente (nunca só cor: ícone + palavra).
     * opcoes: {tipo, titulo, texto, extra (Node), acoes [{rotulo, classe, onClick}], foco}
     * Retorna o elemento do alerta. Foco vai para o primeiro botão ou para o próprio alerta.
     */
    function mostrarAlerta(container, opcoes) {
        limpar(container);
        const tipo = opcoes.tipo || 'info';
        const box = criar('div', 'alert alert-' + tipo);
        box.setAttribute('role', tipo === 'info' || tipo === 'success' ? 'status' : 'alert');
        box.tabIndex = -1;
        const ic = criar('span', 'alert-icon');
        ic.innerHTML = ICONES[tipo];
        box.appendChild(ic);
        const corpo = criar('div', 'alert-body');
        const t = criar('p', 'alert-title');
        t.appendChild(criar('span', 'alert-prefix', PREFIXO[tipo] + ' '));
        t.appendChild(document.createTextNode(opcoes.titulo || ''));
        corpo.appendChild(t);
        if (opcoes.texto) corpo.appendChild(criar('p', 'alert-text', opcoes.texto));
        if (opcoes.extra) corpo.appendChild(opcoes.extra);
        if (opcoes.acoes && opcoes.acoes.length) {
            const linha = criar('div', 'alert-actions');
            opcoes.acoes.forEach((a) => {
                const b = criar('button', 'btn ' + (a.classe || 'btn-secondary'), a.rotulo);
                b.type = 'button';
                b.addEventListener('click', a.onClick);
                linha.appendChild(b);
            });
            corpo.appendChild(linha);
        }
        box.appendChild(corpo);
        container.appendChild(box);
        if (tipo === 'error' || tipo === 'warning') {
            falarSeAtivo(opcoes.fala || ((opcoes.titulo || '') + ' ' + (opcoes.texto || '')));
        }
        if (opcoes.foco !== false) {
            const alvo = box.querySelector('.alert-actions button') || box;
            alvo.focus({ preventScroll: false });
        }
        return box;
    }

    function anunciar(texto) {
        // Limpa e repõe para que mensagens repetidas sejam relidas.
        el.announcer.textContent = '';
        window.setTimeout(() => { el.announcer.textContent = texto; }, 50);
    }

    function setBusy(botao, ocupado, textoOcupado) {
        if (ocupado) {
            if (!botao.dataset.rotulo) botao.dataset.rotulo = botao.textContent;
            botao.setAttribute('aria-busy', 'true');
            botao.setAttribute('aria-disabled', 'true');
            limpar(botao);
            botao.appendChild(criar('span', 'spinner'));
            botao.appendChild(document.createTextNode(' ' + textoOcupado));
        } else {
            botao.removeAttribute('aria-busy');
            botao.removeAttribute('aria-disabled');
            if (botao.dataset.rotulo) {
                botao.textContent = botao.dataset.rotulo;
                delete botao.dataset.rotulo;
            }
        }
    }

    function bloquearEntrada(bloquear) {
        state.ocupado = bloquear;
        el.fsTipos.disabled = bloquear;
        el.setor.disabled = bloquear;
    }

    /* ======================================================================
     * 4. Disponibilidade  [F2]
     * ==================================================================== */
    function somarPorSetor(lista, setorId) {
        let livres = 0;
        let ocupadas = 0;
        (lista || []).forEach((s) => {
            if (setorId && s.setor_id !== setorId) return;
            livres += s.livres || 0;
            ocupadas += s.ocupadas || 0;
        });
        return { livres: livres, ocupadas: ocupadas, total: livres + ocupadas };
    }

    function livresPorTipo() {
        const mapa = {};
        TIPOS.forEach((t) => { mapa[t] = 0; });
        if (state.glob && Array.isArray(state.glob.vagas)) {
            state.glob.vagas.forEach((v) => {
                if (mapa[v.tipo] !== undefined) mapa[v.tipo] += 1;
            });
        }
        return mapa;
    }

    /** Livres do tipo selecionado em um setor (conforme a última carga). null se desconhecido. */
    function livresNoSetor(setorId) {
        if (!state.selTipo) return null;
        const lista = state.selTipo.por_setor || [];
        const s = lista.find((x) => x.setor_id === setorId);
        return s ? s.livres : 0;
    }

    function livresDoTipo(tipo) {
        if (!state.glob) return null;
        return livresPorTipo()[tipo];
    }

    function registrarSetores() {
        SETORES_FALLBACK.forEach((s) => {
            if (!state.setores.has(s.id)) state.setores.set(s.id, Object.assign({}, s));
        });
        [state.glob, state.selTipo].forEach((resp) => {
            if (!resp || !resp.por_setor) return;
            resp.por_setor.forEach((s) => {
                state.setores.set(s.setor_id, { id: s.setor_id, nome: s.setor_nome, andar: s.andar });
            });
        });
    }

    function renderSetores() {
        const atual = el.setor.value;
        limpar(el.setor);
        const padrao = criar('option', '', 'Sem preferência');
        padrao.value = '';
        el.setor.appendChild(padrao);
        Array.from(state.setores.values()).sort((a, b) => a.id - b.id).forEach((s) => {
            let rotulo = s.nome + ' - ' + s.andar;
            const livres = livresNoSetor(s.id);
            if (livres !== null) {
                rotulo += livres === 0 ? ' (cheio)' : ' (' + livres + ' ' + plural(livres, 'livre', 'livres') + ')';
            }
            const op = criar('option', '', rotulo);
            op.value = String(s.id);
            el.setor.appendChild(op);
        });
        el.setor.value = atual;
    }

    function renderTipos() {
        const mapa = livresPorTipo();
        TIPOS.forEach((tipo) => {
            const badge = document.querySelector('[data-disp="' + tipo + '"]');
            if (!badge) return;
            badge.classList.remove('low', 'none');
            if (!state.glob) {
                badge.textContent = '--';
                return;
            }
            const n = mapa[tipo];
            if (n === 0) {
                badge.textContent = 'Esgotado';
                badge.classList.add('none');
            } else if (n < POUCAS_VAGAS) {
                badge.textContent = 'Poucas (' + n + ')';
                badge.classList.add('low');
            } else {
                badge.textContent = n + ' livres';
            }
        });
        document.querySelectorAll('.spot-type-card').forEach((card) => {
            const radio = card.querySelector('input[type="radio"]');
            card.classList.toggle('selected', !!(radio && radio.checked));
        });
    }

    function resumoAtual() {
        const tipo = tipoSelecionado();
        const fonte = tipo ? state.selTipo : state.glob;
        if (!fonte) return null;
        return somarPorSetor(fonte.por_setor, setorSelecionado());
    }

    function renderResumo() {
        const r = resumoAtual();
        const sufixo = tipoSelecionado() ? ' ' + tipoTexto(tipoSelecionado()) : '';
        if (!r) {
            el.statFree.textContent = '--';
            el.statOcc.textContent = '--';
            el.statEv.textContent = '--';
        } else {
            el.statFree.textContent = String(r.livres);
            el.statOcc.textContent = String(r.ocupadas);
            el.statFree.nextElementSibling.textContent = 'livres de ' + r.total + sufixo;
            el.statOcc.nextElementSibling.textContent = 'ocupadas' + sufixo;
        }
        if (state.ev) {
            const e = somarPorSetor(state.ev.por_setor, null);
            const livres = typeof state.ev.total === 'number' ? state.ev.total : e.livres;
            const total = Math.max(e.total, livres);
            el.statEv.textContent = String(livres);
            el.statEv.nextElementSibling.textContent = total > livres
                ? 'elétrico livres de ' + total : 'elétrico livres';
        }
    }

    function textoResumoAnuncio() {
        const r = resumoAtual();
        if (!r) return '';
        const tipo = tipoSelecionado();
        const quem = tipo ? ' para vagas ' + tipoTexto(tipo) : '';
        const setor = setorSelecionado() ? ', setor ' + nomeSetor(setorSelecionado()) : '';
        return r.livres + ' ' + plural(r.livres, 'vaga livre', 'vagas livres') + ' de ' + r.total + quem + setor + '.';
    }

    function renderTudo() {
        registrarSetores();
        renderTipos();
        renderSetores();
        renderResumo();
    }

    function horaAgora() {
        return new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date());
    }

    /**
     * Carrega a disponibilidade. opcoes.anunciar: anuncia o resumo (só após ação do usuário).
     * Polling usa silencioso: falha só troca o texto de status, sem alerta.
     */
    async function carregarDisponibilidade(opcoes) {
        const o = opcoes || {};
        const tipo = tipoSelecionado();
        el.resumo.setAttribute('aria-busy', 'true');
        if (!state.glob) el.dispStatus.textContent = 'Carregando disponibilidade...';
        try {
            const reqs = [
                api('/vagas/disponiveis'),
                api('/vagas/disponiveis' + consulta({ tipo: 'eletrico', apenas_com_carregador: 'true' })),
                tipo ? api('/vagas/disponiveis' + consulta({ tipo: tipo })) : Promise.resolve(null)
            ];
            const res = await Promise.all(reqs);
            // Se o tipo mudou durante a carga, ignora o resultado (outra carga virá).
            if (tipo !== tipoSelecionado()) return;
            state.glob = res[0];
            state.ev = res[1];
            state.selTipo = res[2];
            renderTudo();
            el.dispStatus.textContent = 'Disponibilidade atualizada às ' + horaAgora() + '.';
            if (o.anunciar) anunciar(textoResumoAnuncio());
            limparErroDisponibilidade();
        } catch (err) {
            el.dispStatus.textContent = 'Não foi possível atualizar a disponibilidade.';
            if (!state.glob && !o.silencioso) {
                const alerta = mostrarAlerta(el.entradaStatus, {
                    tipo: 'error',
                    titulo: 'Não foi possível conectar ao estacionamento.',
                    texto: MSG.rede,
                    acoes: [{ rotulo: 'Tentar de novo', classe: 'btn-primary',
                        onClick: () => carregarDisponibilidade({ anunciar: true }) }]
                });
                alerta.dataset.origem = 'disp';
            }
        } finally {
            el.resumo.setAttribute('aria-busy', 'false');
        }
    }

    function limparErroDisponibilidade() {
        const a = el.entradaStatus.querySelector('[data-origem="disp"]');
        if (a) limpar(el.entradaStatus);
    }

    async function carregarConfig() {
        try {
            state.config = await api('/config');
            const tol = state.config.tolerancia_minutos;
            el.configInfo.textContent = 'Até ' + tol + ' minutos grátis. Depois, ' +
                formatarMoeda(state.config.valor_hora) + ' por hora.';
        } catch (e) {
            el.configInfo.textContent = '';
        }
    }

    /* ======================================================================
     * 5. Entrada  [F2]
     * ==================================================================== */
    function mostrarErroTipo(texto) {
        el.tipoErro.hidden = false;
        limpar(el.tipoErro);
        el.tipoErro.setAttribute('role', 'alert');
        el.tipoErro.appendChild(criar('strong', '', 'Erro: '));
        el.tipoErro.appendChild(document.createTextNode(texto));
        el.fsTipos.classList.add('invalid');
        const primeiro = document.querySelector('input[name="tipo"]');
        if (primeiro) primeiro.focus();
    }

    function limparErroTipo() {
        el.tipoErro.hidden = true;
        el.tipoErro.removeAttribute('role');
        limpar(el.tipoErro);
        el.fsTipos.classList.remove('invalid');
    }

    function mensagemErroEntrada(err) {
        if (err.status === 400) return MSG.semVaga;
        if (err.status === 422) return MSG.validacao;
        return err.detail || MSG.validacao;
    }

    function tratarErroEntrada(err, tentarDeNovo, payload) {
        if (err.status === 409 && payload && payload.vaga_id && sugestao) {
            // A vaga aceita foi ocupada por outra pessoa: busca outra opção.
            sugestao.excluidas.push(payload.vaga_id);
            buscarSugestao('A vaga sugerida acabou de ser ocupada. Buscando outra opção...');
            return;
        }
        if (err.kind === 'rede' || err.kind === 'servidor') {
            mostrarAlerta(el.entradaStatus, {
                tipo: 'error',
                titulo: 'Não foi possível conectar ao estacionamento.',
                texto: MSG.rede,
                acoes: [{ rotulo: 'Tentar de novo', classe: 'btn-primary', onClick: tentarDeNovo }]
            });
            return;
        }
        mostrarAlerta(el.entradaStatus, {
            tipo: 'error',
            titulo: mensagemErroEntrada(err)
        });
    }

    async function emitirTicket(payload) {
        if (state.ocupado) return;
        limpar(el.entradaStatus);
        bloquearEntrada(true);
        setBusy(el.btnGerar, true, 'Gerando ticket...');
        anunciar('Gerando ticket...');
        try {
            const ticket = await api('/tickets/entrada', { method: 'POST', json: payload });
            bloquearEntrada(false);
            setBusy(el.btnGerar, false);
            mostrarTicket(ticket);
        } catch (err) {
            bloquearEntrada(false);
            setBusy(el.btnGerar, false);
            tratarErroEntrada(err, () => emitirTicket(payload), payload);
        } finally {
            carregarDisponibilidade({ silencioso: true });
        }
    }

    /* ======================================================================
     * 6. Ticket emitido  [F3]
     * ==================================================================== */
    function formatarDuracao(min) {
        const m = Math.max(0, Math.round(min));
        if (m < 60) return m + ' min';
        const h = Math.floor(m / 60);
        const r = m % 60;
        return r ? h + ' h ' + r + ' min' : h + ' h';
    }

    function campo(rotulo, valor, larga) {
        const d = criar('div', 'ticket-field' + (larga ? ' full-width' : ''));
        d.appendChild(criar('dt', 'ticket-label', rotulo));
        d.appendChild(criar('dd', 'ticket-value', valor));
        return d;
    }

    function descricaoTicket(t) {
        const v = t.vaga || {};
        const setor = v.setor || {};
        return 'Ticket emitido. Vaga ' + v.numero + ', setor ' + (setor.nome || nomeSetor(v.setor_id)) +
            ', ' + (setor.andar || '') + '. Seu código é ' + t.identificador + '. Você tem ' +
            t.tolerancia_minutos + ' minutos grátis.';
    }

    function renderTicket(t) {
        const v = t.vaga || {};
        const setor = v.setor || {};
        limpar(el.ticketCard);

        const cab = criar('div', 'ticket-header');
        cab.appendChild(criar('h3', 'ticket-title', 'Ticket de estacionamento'));
        cab.appendChild(criar('span', 'ticket-status active', 'Ativo'));
        el.ticketCard.appendChild(cab);

        const cod = criar('p', 'ticket-code-line');
        cod.appendChild(criar('span', 'ticket-label', 'Código '));
        cod.appendChild(criar('span', 'ticket-code-display', t.identificador));
        el.ticketCard.appendChild(cod);

        const dl = criar('dl', 'ticket-body');
        dl.appendChild(campo('Vaga', v.numero || '-'));
        dl.appendChild(campo('Setor', setor.nome || nomeSetor(v.setor_id)));
        dl.appendChild(campo('Andar', setor.andar || '-'));
        dl.appendChild(campo('Tipo', ROTULO_TIPO[v.tipo] || v.tipo || '-'));
        if (v.carregador && v.carregador.tipo_conector) {
            dl.appendChild(campo('Carregador', v.carregador.tipo_conector));
        }
        const entrada = campo('Entrada', formatarDataHora(t.entrada));
        const dd = entrada.querySelector('dd');
        const dt = paraData(t.entrada);
        if (dt && !isNaN(dt)) {
            const tm = criar('time', '', dd.textContent);
            tm.dateTime = dt.toISOString();
            dd.textContent = '';
            dd.appendChild(tm);
        }
        dl.appendChild(entrada);
        dl.appendChild(campo('Valor por hora', formatarMoeda(t.valor_hora)));
        el.ticketCard.appendChild(dl);

        const tol = criar('div', 'ticket-tolerance');
        tol.appendChild(criar('p', 'ticket-tolerance-label', 'Tolerância de ' + t.tolerancia_minutos + ' minutos'));
        tol.appendChild(criar('p', 'ticket-tolerance-time', 'Grátis até ' + formatarHora(t.tempo_limite_tolerancia)));
        el.ticketCard.appendChild(tol);

    }

    function mostrarTicket(t) {
        ultimoTicket = t;
        sugestao = null;
        renderTicket(t);
        try { window.sessionStorage.setItem(CHAVE_CODIGO, t.identificador); } catch (e) { /* sem storage */ }
        el.codigo.value = t.identificador;
        limparErroCodigo();
        limpar(el.saidaStatus);
        el.blocoTicket.hidden = false;
        el.tituloTicket.focus();
        anunciar(descricaoTicket(t));
        falarSeAtivo(falaTicket(t));
    }

    function novaEntrada() {
        el.blocoTicket.hidden = true;
        limpar(el.ticketCard);
        limpar(el.entradaStatus);
        limparErroTipo();
        ultimoTicket = null;
        sugestao = null;
        document.querySelectorAll('input[name="tipo"]').forEach((r) => { r.checked = false; });
        el.setor.value = '';
        state.selTipo = null;
        renderTudo();
        carregarDisponibilidade({});
        const primeiro = document.querySelector('input[name="tipo"]');
        if (primeiro) primeiro.focus();
    }

    /* ======================================================================
     * 7. Saída  [F3]
     * ==================================================================== */
    function mostrarErroCodigo(texto) {
        el.codigoErro.hidden = false;
        limpar(el.codigoErro);
        el.codigoErro.setAttribute('role', 'alert');
        el.codigoErro.appendChild(criar('strong', '', 'Erro: '));
        el.codigoErro.appendChild(document.createTextNode(texto));
        el.codigo.setAttribute('aria-invalid', 'true');
        el.codigo.focus();
    }

    function limparErroCodigo() {
        el.codigoErro.hidden = true;
        el.codigoErro.removeAttribute('role');
        limpar(el.codigoErro);
        el.codigo.removeAttribute('aria-invalid');
    }

    function descricaoSaida(r) {
        if (r.isento) {
            return 'Saída liberada. Você ficou ' + formatarDuracao(r.tempo_total_minutos) +
                ', dentro da tolerância. Nada a pagar.';
        }
        return 'Você ficou ' + formatarDuracao(r.tempo_total_minutos) + '. Valor a pagar: ' +
            formatarMoeda(r.valor) + '. Pagamento simulado nesta demonstração.';
    }

    function renderSaida(r) {
        limpar(el.saidaStatus);
        const card = criar('div', 'ticket-card saida-card' + (r.isento ? ' isento' : ''));
        const cab = criar('div', 'ticket-header');
        const titulo = criar('h3', 'ticket-title', r.isento ? 'Saída liberada' : 'Valor a pagar');
        titulo.tabIndex = -1;
        cab.appendChild(titulo);
        cab.appendChild(criar('span', 'ticket-status ' + (r.isento ? 'exempt' : 'pending'),
            r.isento ? 'Isento' : 'Pagamento pendente'));
        card.appendChild(cab);

        const dl = criar('dl', 'ticket-body');
        dl.appendChild(campo('Tempo total', formatarDuracao(r.tempo_total_minutos)));
        dl.appendChild(campo('Tempo cobrado', formatarDuracao(r.tempo_faturavel_minutos)));
        dl.appendChild(campo('Entrada', formatarDataHora(r.entrada)));
        dl.appendChild(campo('Saída', formatarDataHora(r.saida)));
        card.appendChild(dl);

        const total = criar('div', 'ticket-tolerance');
        total.appendChild(criar('p', 'ticket-tolerance-label', r.isento ? 'Dentro da tolerância' : 'Valor a pagar'));
        total.appendChild(criar('p', 'ticket-tolerance-time', formatarMoeda(r.valor)));
        card.appendChild(total);

        card.appendChild(criar('p', 'ticket-message', r.isento
            ? 'Dentro da tolerância de ' + (state.config ? state.config.tolerancia_minutos : 15) + ' minutos.'
            : 'Pagamento simulado nesta demonstração.'));
        el.saidaStatus.appendChild(card);
        titulo.focus();
        anunciar(descricaoSaida(r));
        falarSeAtivo(falaSaida(r));
    }

    function normalizarCodigo() {
        return el.codigo.value.replace(/[\s-]/g, '').toUpperCase();
    }

    async function registrarSaida(identificador) {
        if (state.ocupado) return;
        state.ocupado = true;
        limpar(el.saidaStatus);
        setBusy(el.btnSaida, true, 'Calculando valor...');
        anunciar('Calculando valor...');
        try {
            const r = await api('/tickets/saida', { method: 'POST', json: { identificador: identificador } });
            state.ocupado = false;
            setBusy(el.btnSaida, false);
            renderSaida(r);
            if (ultimoTicket && ultimoTicket.identificador === identificador) {
                el.blocoTicket.hidden = true;
                ultimoTicket = null;
            }
            try { window.sessionStorage.removeItem(CHAVE_CODIGO); } catch (e) { /* sem storage */ }
        } catch (err) {
            state.ocupado = false;
            setBusy(el.btnSaida, false);
            tratarErroSaida(err, identificador);
        } finally {
            carregarDisponibilidade({ silencioso: true });
        }
    }

    function tratarErroSaida(err, identificador) {
        if (err.kind === 'rede' || err.kind === 'servidor') {
            mostrarAlerta(el.saidaStatus, {
                tipo: 'error',
                titulo: 'Não foi possível conectar ao estacionamento.',
                texto: MSG.rede,
                acoes: [{ rotulo: 'Tentar de novo', classe: 'btn-primary', onClick: () => registrarSaida(identificador) }]
            });
        } else if (err.status === 404) {
            mostrarErroCodigo('Ticket não encontrado. Confira o código de 8 caracteres.');
        } else if (err.status === 409 || err.status === 400) {
            mostrarErroCodigo('Este ticket já teve a saída registrada.');
        } else if (err.status === 422) {
            mostrarErroCodigo(MSG.validacao);
        } else {
            mostrarErroCodigo(err.detail || MSG.validacao);
        }
    }

    function aoSair(ev) {
        ev.preventDefault();
        if (state.ocupado) return;
        limparErroCodigo();
        limpar(el.saidaStatus);
        const codigo = normalizarCodigo();
        el.codigo.value = codigo;
        if (!/^[A-Z0-9]{8}$/.test(codigo)) {
            mostrarErroCodigo('Digite o código de 8 letras e números do seu ticket.');
            return;
        }
        registrarSaida(codigo);
    }

    function aoGerar(ev) {
        ev.preventDefault();
        if (state.ocupado) return;
        limpar(el.entradaStatus);
        const tipo = tipoSelecionado();
        if (!tipo) {
            mostrarErroTipo(MSG.escolhaTipo);
            return;
        }
        limparErroTipo();
        if (livresDoTipo(tipo) === 0) { // E6
            mostrarAlerta(el.entradaStatus, { tipo: 'error', titulo: MSG.esgotado });
            return;
        }
        const payload = { tipo_vaga: tipo };
        const setor = setorSelecionado();
        if (setor) payload.setor_id = setor;
        // E5: setor escolhido sem vagas do tipo -> sugestão antes de chamar a entrada.
        if (setor && livresNoSetor(setor) === 0) {
            sugestao = { tipo: tipo, setorId: setor, excluidas: [], recusas: 0, atual: null };
            buscarSugestao();
            return;
        }
        sugestao = null;
        emitirTicket(payload);
    }

    function aoMudarTipo() {
        limparErroTipo();
        sugestao = null;
        limpar(el.entradaStatus);
        renderTipos();
        carregarDisponibilidade({ anunciar: true });
    }

    function aoMudarSetor() {
        sugestao = null;
        limpar(el.entradaStatus);
        renderResumo();
        anunciar(textoResumoAnuncio());
    }

    /* ======================================================================
     * 8. Acessibilidade: contraste, fonte e leitura em voz  [F5]
     * ==================================================================== */
    const PREF_CONTRASTE = 'capim.contraste';
    const PREF_FONTE = 'capim.fonte';
    const NIVEIS_FONTE = [87.5, 100, 112.5, 125]; // % do tamanho base (16px)
    let nivelFonte = 1;

    function lerPref(chave) {
        try { return window.localStorage.getItem(chave); } catch (e) { return null; }
    }

    function gravarPref(chave, valor) {
        try { window.localStorage.setItem(chave, valor); } catch (e) { /* sem storage */ }
    }

    function aplicarContraste(ligado, persistir) {
        document.documentElement.classList.toggle('high-contrast', ligado);
        $('btn-high-contrast').setAttribute('aria-pressed', String(ligado));
        if (persistir) gravarPref(PREF_CONTRASTE, ligado ? '1' : '0');
    }

    function aplicarFonte(nivel, persistir) {
        nivelFonte = Math.min(NIVEIS_FONTE.length - 1, Math.max(0, nivel));
        document.documentElement.style.fontSize = NIVEIS_FONTE[nivelFonte] + '%';
        $('btn-increase-font').setAttribute('aria-disabled', String(nivelFonte === NIVEIS_FONTE.length - 1));
        $('btn-decrease-font').setAttribute('aria-disabled', String(nivelFonte === 0));
        if (persistir) gravarPref(PREF_FONTE, String(nivelFonte));
    }

    const tts = {
        suportado: 'speechSynthesis' in window && typeof window.SpeechSynthesisUtterance === 'function',
        ativo: false,
        voz: null
    };

    function escolherVoz() {
        if (!tts.suportado) return;
        const vozes = window.speechSynthesis.getVoices() || [];
        tts.voz = vozes.find((v) => /^pt[-_]BR$/i.test(v.lang)) ||
            vozes.find((v) => /^pt/i.test(v.lang)) || null;
    }

    // "R$ 10,00" vira "10 reais"; sem siglas nem símbolos para a voz.
    function moedaFala(v) {
        const total = Math.round((Number(v) || 0) * 100);
        const reais = Math.floor(total / 100);
        const cent = total % 100;
        let t = reais + ' ' + plural(reais, 'real', 'reais');
        if (cent) t += ' e ' + cent + ' ' + plural(cent, 'centavo', 'centavos');
        return t;
    }

    function limparFala(texto) {
        return String(texto)
            .replace(/R\$\s*(\d+)(?:,(\d{2}))?/g, (m, r, c) =>
                moedaFala(Number(r) + (c ? Number(c) / 100 : 0)))
            .replace(/\bPCD\b/g, 'pessoa com deficiência')
            .replace(/\bEV\b/g, 'elétrico')
            .replace(/\s+-\s+/g, ', ');
    }

    function soletrar(codigo) {
        return String(codigo).split('').join(', ');
    }

    function falar(texto) {
        if (!tts.suportado || !texto) return;
        const synth = window.speechSynthesis;
        synth.cancel();
        const u = new window.SpeechSynthesisUtterance(limparFala(texto));
        u.lang = 'pt-BR';
        u.rate = 0.9;
        if (tts.voz) u.voice = tts.voz;
        synth.speak(u);
    }

    function falarSeAtivo(texto) {
        if (tts.ativo) falar(texto);
    }

    function pararFala() {
        if (tts.suportado) window.speechSynthesis.cancel();
    }

    function falaTicket(t) {
        const v = t.vaga || {};
        const setor = v.setor || {};
        return 'Ticket emitido. Vaga ' + v.numero + ', setor ' + (setor.nome || nomeSetor(v.setor_id)) +
            ', ' + (setor.andar || '') + '. Seu código é ' + soletrar(t.identificador) +
            '. Você tem ' + t.tolerancia_minutos + ' minutos grátis. Valor por hora, ' +
            moedaFala(t.valor_hora) + '.';
    }

    function falaSaida(r) {
        if (r.isento) return descricaoSaida(r);
        return 'Você ficou ' + formatarDuracao(r.tempo_total_minutos) + '. Valor a pagar: ' +
            moedaFala(r.valor) + '. Pagamento simulado nesta demonstração.';
    }

    function iniciarAcessibilidade() {
        // Contraste: preferência salva; na primeira visita respeita prefers-contrast.
        const salvoC = lerPref(PREF_CONTRASTE);
        const prefereMais = window.matchMedia && window.matchMedia('(prefers-contrast: more)').matches;
        aplicarContraste(salvoC === null ? prefereMais : salvoC === '1', false);
        $('btn-high-contrast').addEventListener('click', () => {
            aplicarContraste(!document.documentElement.classList.contains('high-contrast'), true);
        });

        const salvoF = parseInt(lerPref(PREF_FONTE), 10);
        aplicarFonte(isNaN(salvoF) ? 1 : salvoF, false);
        $('btn-increase-font').addEventListener('click', () => {
            aplicarFonte(nivelFonte + 1, true);
            anunciar('Fonte maior.');
        });
        $('btn-decrease-font').addEventListener('click', () => {
            aplicarFonte(nivelFonte - 1, true);
            anunciar('Fonte menor.');
        });

        const btnTts = $('btn-tts');
        const btnOuvir = $('btn-ouvir-ticket');
        if (!tts.suportado) {
            btnTts.setAttribute('aria-disabled', 'true');
            btnTts.removeAttribute('aria-pressed');
            $('tts-label').textContent = 'Leitura em voz indisponível neste navegador';
            btnOuvir.setAttribute('aria-disabled', 'true');
        } else {
            escolherVoz();
            window.speechSynthesis.addEventListener('voiceschanged', escolherVoz);
            btnTts.addEventListener('click', () => {
                tts.ativo = !tts.ativo;
                btnTts.setAttribute('aria-pressed', String(tts.ativo));
                if (tts.ativo) {
                    falar('Leitura em voz ligada.');
                } else {
                    pararFala();
                    anunciar('Leitura em voz desligada.');
                }
            });
            btnOuvir.addEventListener('click', () => {
                if (ultimoTicket) falar(falaTicket(ultimoTicket));
            });
        }
        document.addEventListener('keydown', (ev) => {
            if (ev.key !== 'Escape') return;
            pararFala();
            aoEscape();
        });
    }

    // Esc: fecha a sugestão/alerta de entrada e devolve o foco ao botão principal.
    function aoEscape() {
        if (el.entradaStatus.contains(document.activeElement) && el.entradaStatus.firstChild) {
            cancelarSugestao();
            el.btnGerar.focus();
        }
    }

    /* ======================================================================
     * 9. Setor cheio: sugerir, aceitar, outra opção  [F6]
     * ==================================================================== */
    function cancelarSugestao() {
        sugestao = null;
        limpar(el.entradaStatus);
    }

    function escolherOutroTipo() {
        cancelarSugestao();
        const alvo = document.querySelector('input[name="tipo"]:checked') || document.querySelector('input[name="tipo"]');
        if (alvo) alvo.focus();
    }

    function fraseSugestao(sug) {
        const v = sug.vaga;
        const setor = (v.setor && v.setor.nome) || nomeSetor(v.setor_id);
        const andar = (v.setor && v.setor.andar) || '';
        const dist = Math.round(sug.distancia_metros);
        return 'Setor ' + setor + ', ' + andar + '. Vaga ' + v.numero + ', a cerca de ' + dist +
            ' metros, ' + sug.tempo_caminhada_minutos + ' ' + plural(sug.tempo_caminhada_minutos, 'minuto', 'minutos') + ' a pé.';
    }

    function renderSugestao(sug) {
        const v = sug.vaga;
        const setor = (v.setor && v.setor.nome) || nomeSetor(v.setor_id);
        const andar = (v.setor && v.setor.andar) || '';
        const dl = criar('dl', 'suggestion-card');
        dl.appendChild(campo('Setor', setor));
        dl.appendChild(campo('Andar', andar || '-'));
        dl.appendChild(campo('Vaga', v.numero));
        dl.appendChild(campo('Distância', 'cerca de ' + Math.round(sug.distancia_metros) + ' metros'));
        dl.appendChild(campo('A pé', sug.tempo_caminhada_minutos + ' ' + plural(sug.tempo_caminhada_minutos, 'minuto', 'minutos')));

        const n = sugestao.recusas + 1;
        const contagem = criar('p', 'suggestion-count', 'Opção ' + n + ' de ' + (MAX_RECUSAS + 1));
        const wrap = criar('div');
        wrap.appendChild(dl);
        wrap.appendChild(contagem);

        const tipoNome = tipoTexto(sugestao.tipo);
        const cheio = nomeSetor(sugestao.setorId);
        const acoes = [{ rotulo: 'Aceitar vaga', classe: 'btn-primary', onClick: aceitarSugestao }];
        acoes.push({ rotulo: 'Outra opção', classe: 'btn-secondary', onClick: recusarSugestao });
        acoes.push({ rotulo: 'Cancelar', classe: 'btn-secondary', onClick: () => {
            cancelarSugestao();
            el.btnGerar.focus();
        } });
        mostrarAlerta(el.entradaStatus, {
            tipo: 'warning',
            titulo: 'O setor ' + cheio + ' está cheio para vagas ' + tipoNome + '. Encontramos uma vaga perto de lá.',
            extra: wrap,
            acoes: acoes,
            fala: 'O setor ' + cheio + ' está cheio para vagas ' + tipoNome + '. Sugestão: ' + fraseSugestao(sug)
        });
        anunciar('Sugestão: ' + fraseSugestao(sug));
    }

    async function buscarSugestao(aviso) {
        if (!sugestao || state.ocupado) return;
        state.ocupado = true;
        el.btnGerar.setAttribute('aria-disabled', 'true');
        mostrarAlerta(el.entradaStatus, {
            tipo: 'info',
            titulo: aviso || 'Procurando uma vaga próxima...',
            foco: false
        });
        const atual = sugestao;
        try {
            const sug = await api('/vagas/proximas' + consulta({
                setor_desejado_id: atual.setorId,
                tipo_vaga: atual.tipo,
                excluir_vaga_id: atual.excluidas
            }));
            state.ocupado = false;
            el.btnGerar.removeAttribute('aria-disabled');
            // Backend antigo ignora exclusões repetidas: se voltou uma vaga já recusada, não há mais opções.
            if (!sug || !sug.vaga || atual.excluidas.indexOf(sug.vaga.id) !== -1) {
                semMaisOpcoes();
                return;
            }
            atual.atual = sug;
            renderSugestao(sug);
        } catch (err) {
            state.ocupado = false;
            el.btnGerar.removeAttribute('aria-disabled');
            if (err.status === 404) {
                semMaisOpcoes();
            } else if (err.kind === 'rede' || err.kind === 'servidor') {
                mostrarAlerta(el.entradaStatus, {
                    tipo: 'error',
                    titulo: 'Não foi possível conectar ao estacionamento.',
                    texto: MSG.rede,
                    acoes: [{ rotulo: 'Tentar de novo', classe: 'btn-primary', onClick: () => buscarSugestao() }]
                });
            } else {
                mostrarAlerta(el.entradaStatus, { tipo: 'error', titulo: err.detail || MSG.validacao });
            }
        }
    }

    function semMaisOpcoes() {
        sugestao = null;
        mostrarAlerta(el.entradaStatus, {
            tipo: 'error',
            titulo: 'Não há mais vagas livres deste tipo.',
            texto: 'Escolha outro tipo de vaga.',
            acoes: [{ rotulo: 'Escolher outro tipo', classe: 'btn-primary', onClick: escolherOutroTipo }]
        });
    }

    function aceitarSugestao() {
        if (!sugestao || !sugestao.atual) return;
        const v = sugestao.atual.vaga;
        emitirTicket({ tipo_vaga: sugestao.tipo, setor_id: v.setor_id, vaga_id: v.id });
    }

    function recusarSugestao() {
        if (!sugestao || !sugestao.atual) return;
        sugestao.excluidas.push(sugestao.atual.vaga.id);
        sugestao.recusas += 1;
        sugestao.atual = null;
        if (sugestao.recusas >= MAX_RECUSAS) {
            semMaisOpcoes();
            return;
        }
        buscarSugestao();
    }

    function iniciar() {
        document.querySelectorAll('input[name="tipo"]').forEach((r) => r.addEventListener('change', aoMudarTipo));
        el.setor.addEventListener('change', aoMudarSetor);
        el.form.addEventListener('submit', aoGerar);
        el.formSaida.addEventListener('submit', aoSair);
        el.btnImprimir.addEventListener('click', () => window.print());
        el.btnNovaEntrada.addEventListener('click', novaEntrada);
        el.codigo.addEventListener('input', () => { if (el.codigo.hasAttribute('aria-invalid')) limparErroCodigo(); });
        try {
            const salvo = window.sessionStorage.getItem(CHAVE_CODIGO);
            if (salvo) el.codigo.value = salvo;
        } catch (e) { /* sem storage */ }
        iniciarAcessibilidade();
        registrarSetores();
        renderSetores();
        carregarConfig();
        carregarDisponibilidade({});
        window.setInterval(() => {
            if (!document.hidden && !state.ocupado) carregarDisponibilidade({ silencioso: true });
        }, POLL_MS);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }
})();
