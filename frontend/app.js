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
        announcer: $('sr-announcer')
    };

    const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
    const formatarMoeda = (v) => brl.format(Number(v) || 0).replace(/ /g, ' ');

    function plural(n, um, varios) {
        return n === 1 ? um : varios;
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
        const sufixo = tipoSelecionado() ? ' ' + ROTULO_TIPO[tipoSelecionado()].toLowerCase() : '';
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
        const quem = tipo ? ' para vagas ' + ROTULO_TIPO[tipo].toLowerCase() : '';
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

    function tratarErroEntrada(err, tentarDeNovo) {
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
            tratarErroEntrada(err, () => emitirTicket(payload));
        } finally {
            carregarDisponibilidade({ silencioso: true });
        }
    }

    // Placeholder substituído na tarefa F3 (bloco de ticket).
    function mostrarTicket(ticket) {
        anunciar('Ticket emitido. Código ' + ticket.identificador + '.');
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
        emitirTicket(payload);
    }

    function aoMudarTipo() {
        limparErroTipo();
        limpar(el.entradaStatus);
        renderTipos();
        carregarDisponibilidade({ anunciar: true });
    }

    function aoMudarSetor() {
        limpar(el.entradaStatus);
        renderResumo();
        anunciar(textoResumoAnuncio());
    }

    function iniciar() {
        document.querySelectorAll('input[name="tipo"]').forEach((r) => r.addEventListener('change', aoMudarTipo));
        el.setor.addEventListener('change', aoMudarSetor);
        el.form.addEventListener('submit', aoGerar);
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
