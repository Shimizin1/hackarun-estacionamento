"""
Testes de QA da v2.0: lacunas de cobertura dos criterios de aceite do PO
(H01-H08). Ver docs/squad/v2-0/06-qa.md para a matriz de rastreabilidade.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, update

from app.models import (
    Carregador, StatusCarregador, StatusPagamento, StatusVaga, Ticket, TipoVaga, Vaga,
)
from app.schemas import TicketSaidaRequest
from app.services.ticket_service import TicketJaFinalizado, TicketService


def _entrar(client, **extra):
    r = client.post("/tickets/entrada", json={"tipo_vaga": "comum", "setor_id": 1, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def _sair_em(db, ident, delta):
    """Registra a saida `delta` apos a entrada real do ticket (relogio injetado)."""
    t = db.query(Ticket).filter(Ticket.identificador == ident).one()
    return TicketService.registrar_saida(
        db, TicketSaidaRequest(identificador=ident), agora=t.entrada + delta)


# ---- H03: fronteira da tolerancia pelo fluxo completo (servico + banco) ------

@pytest.mark.parametrize("delta, valor, status", [
    (timedelta(minutes=10), 0.0, StatusPagamento.ISENTO),
    (timedelta(minutes=15), 0.0, StatusPagamento.ISENTO),
    (timedelta(minutes=15, microseconds=1), 5.0, StatusPagamento.PENDENTE),
    (timedelta(minutes=15, seconds=1), 5.0, StatusPagamento.PENDENTE),
    (timedelta(minutes=14, seconds=59, microseconds=999999), 0.0, StatusPagamento.ISENTO),
])
def test_fronteira_tolerancia_no_fluxo_completo(client, db, delta, valor, status):
    t = _entrar(client)
    resp = _sair_em(db, t["identificador"], delta)
    assert resp.valor == valor and resp.status_pagamento == status
    assert resp.isento is (valor == 0.0)
    db.expire_all()
    assert db.get(Vaga, t["vaga"]["id"]).status == StatusVaga.LIVRE


def test_15min59s_nao_e_truncado_para_isento(client, db):
    """Regressao do bug original (int(minutos)): 15:59 nao pode virar isento."""
    t = _entrar(client)
    assert _sair_em(db, t["identificador"], timedelta(minutes=15, seconds=59)).valor == 5.0


def test_tolerancia_10_guardada_no_ticket_e_usada_na_saida(client, db):
    assert client.patch("/config/admin/tolerancia_minutos", json={"valor": "10"}).status_code == 200
    t = _entrar(client)
    assert t["tolerancia_minutos"] == 10
    assert client.get(f"/tickets/{t['identificador']}").json()["tempo_tolerancia_minutos"] == 10
    assert _sair_em(db, t["identificador"], timedelta(minutes=11)).valor == 5.0


def test_mudar_config_nao_altera_ticket_aberto(client, db):
    t = _entrar(client)  # tolerancia 15, R$ 5/h
    client.patch("/config/admin/tolerancia_minutos", json={"valor": "0"})
    client.patch("/config/admin/valor_hora", json={"valor": "20"})
    resp = _sair_em(db, t["identificador"], timedelta(minutes=10))
    assert resp.isento is True and resp.valor == 0.0
    t2 = _entrar(client)
    assert t2["tolerancia_minutos"] == 0 and t2["valor_hora"] == 20.0


def test_saida_cobrada_76_min_pelo_http_com_horario_retroativo(client, db):
    """Caminho HTTP real: recua a entrada no banco e sai pela API (76 min -> R$ 10)."""
    t = _entrar(client)
    tk = db.query(Ticket).filter(Ticket.identificador == t["identificador"]).one()
    tk.entrada = datetime.utcnow() - timedelta(minutes=76)
    db.commit()
    r = client.post(f"/tickets/{t['identificador']}/saida")
    assert r.status_code == 200
    c = r.json()
    # o relogio andou alguns ms desde o recuo, entao o faturavel (ceil) e 61 ou 62
    assert c["tempo_total_minutos"] == 76 and c["tempo_faturavel_minutos"] in (61, 62)
    assert c["valor"] == 10.0 and c["status_pagamento"] == "pendente" and c["isento"] is False


# ---- H02: ticket finalizado nao altera o valor original ----------------------

def test_saida_repetida_preserva_valor_e_saida_originais(client, db):
    t = _entrar(client)
    tk = db.query(Ticket).filter(Ticket.identificador == t["identificador"]).one()
    tk.entrada = datetime.utcnow() - timedelta(minutes=76)
    db.commit()
    primeira = client.post(f"/tickets/{t['identificador']}/saida").json()
    assert client.post("/tickets/saida", json={"identificador": t["identificador"]}).status_code == 409
    db.expire_all()
    tk = db.query(Ticket).filter(Ticket.identificador == t["identificador"]).one()
    assert float(tk.valor) == primeira["valor"] == 10.0
    assert tk.saida.isoformat() == primeira["saida"]


def test_saida_finalizada_levanta_excecao_de_servico(client, db):
    t = _entrar(client)
    client.post(f"/tickets/{t['identificador']}/saida")
    with pytest.raises(TicketJaFinalizado):
        TicketService.registrar_saida(db, TicketSaidaRequest(identificador=t["identificador"]))


def test_consultar_ticket_inexistente_404(client):
    r = client.get("/tickets/XXXXXXXX")
    assert r.status_code == 404 and "não encontrado" in r.json()["detail"]


def test_ticket_ativo_conta_uma_vaga_e_saida_devolve(client, db):
    ativos_antes = db.query(func.count(Ticket.id)).filter(Ticket.saida.is_(None)).scalar()
    t = _entrar(client)
    db.expire_all()
    assert db.query(func.count(Ticket.id)).filter(Ticket.saida.is_(None)).scalar() == ativos_antes + 1
    client.post(f"/tickets/{t['identificador']}/saida")
    db.expire_all()
    assert db.query(func.count(Ticket.id)).filter(Ticket.saida.is_(None)).scalar() == ativos_antes


# ---- H01: atomicidade para varios tipos, esgotamento, concorrencia -----------

def test_atomicidade_nao_deixa_vaga_presa_em_nenhum_tipo(client, db, monkeypatch):
    def falha(*a, **k):
        raise RuntimeError("falha forcada")
    monkeypatch.setattr(TicketService, "_gerar_mensagem_entrada", falha)
    ocupadas_antes = db.query(func.count(Vaga.id)).filter(Vaga.status == StatusVaga.OCUPADA).scalar()
    carregadores_antes = db.query(func.count(Carregador.id)).filter(
        Carregador.status == StatusCarregador.EM_USO).scalar()
    for tipo in ("comum", "pcd", "eletrico", "moto"):
        with pytest.raises(RuntimeError):
            client.post("/tickets/entrada", json={"tipo_vaga": tipo})
    db.expire_all()
    assert db.query(func.count(Vaga.id)).filter(Vaga.status == StatusVaga.OCUPADA).scalar() == ocupadas_antes
    assert db.query(func.count(Carregador.id)).filter(
        Carregador.status == StatusCarregador.EM_USO).scalar() == carregadores_antes


def test_entrada_sem_setor_para_idoso(client):
    r = client.post("/tickets/entrada", json={"tipo_vaga": "idoso"})
    assert r.status_code == 201 and r.json()["vaga"]["tipo"] == "idoso"


def test_esgotar_todas_as_motos_e_depois_400_legivel(client):
    for _ in range(10):
        assert client.post("/tickets/entrada", json={"tipo_vaga": "moto"}).status_code == 201
    r = client.post("/tickets/entrada", json={"tipo_vaga": "moto"})
    assert r.status_code == 400 and "moto" in r.json()["detail"]
    assert client.get("/vagas/disponiveis", params={"tipo": "moto"}).json()["total"] == 0


def test_entradas_concorrentes_nunca_dao_a_mesma_vaga(client):
    """10 entradas simultaneas de moto (10 vagas): ids distintos e nenhum 500."""
    def entrar(_):
        return client.post("/tickets/entrada", json={"tipo_vaga": "moto"})
    with ThreadPoolExecutor(max_workers=10) as ex:
        resps = list(ex.map(entrar, range(10)))
    codigos = [r.status_code for r in resps]
    assert all(c in (201, 400, 409) for c in codigos), codigos
    vagas = [r.json()["vaga"]["id"] for r in resps if r.status_code == 201]
    assert len(vagas) == len(set(vagas))


# ---- H04: contadores atualizam e batem entre endpoints ------------------------

def test_livres_por_setor_caem_apos_entrada_e_sobem_na_saida(client):
    def livres_azul():
        corpo = client.get("/vagas/disponiveis", params={"tipo": "comum"}).json()
        return next(s["livres"] for s in corpo["por_setor"] if s["setor_id"] == 1)
    antes = livres_azul()
    t = _entrar(client)
    assert livres_azul() == antes - 1
    client.post(f"/tickets/{t['identificador']}/saida")
    assert livres_azul() == antes


def test_setores_e_disponiveis_concordam(client):
    _entrar(client)
    setores = {s["id"]: s for s in client.get("/setores").json()}
    corpo = client.get("/vagas/disponiveis").json()
    assert corpo["total"] == sum(s["vagas_livres"] for s in setores.values())
    for s in corpo["por_setor"]:
        assert s["livres"] == setores[s["setor_id"]]["vagas_livres"]
        assert s["ocupadas"] == setores[s["setor_id"]]["vagas_ocupadas"]


def test_setor_cheio_continua_visivel_com_livres_zero_apos_esgotar(client):
    while client.post("/tickets/entrada", json={"tipo_vaga": "moto"}).status_code == 201:
        pass
    corpo = client.get("/vagas/disponiveis", params={"tipo": "moto"}).json()
    laranja = next(s for s in corpo["por_setor"] if s["setor_nome"] == "Laranja")
    assert laranja["livres"] == 0 and laranja["ocupadas"] == 10 and len(corpo["por_setor"]) == 6


# ---- H05: seis tipos, restricao ------------------------------------------------

def test_cada_um_dos_6_tipos_disponivel_e_entra_na_vaga_do_proprio_tipo(client):
    for tipo in ["comum", "idoso", "pcd", "neurodivergente", "eletrico", "moto"]:
        assert client.get("/vagas/disponiveis", params={"tipo": tipo}).json()["total"] >= 1
        r = client.post("/tickets/entrada", json={"tipo_vaga": tipo})
        assert r.status_code == 201 and r.json()["vaga"]["tipo"] == tipo


def test_comum_esgotado_nao_vaza_com_ou_sem_setor(client, db):
    db.execute(update(Vaga).where(Vaga.tipo == TipoVaga.COMUM).values(status=StatusVaga.OCUPADA))
    db.commit()
    for setor in (None, 1, 3):
        corpo = {"tipo_vaga": "comum"}
        if setor:
            corpo["setor_id"] = setor
        assert client.post("/tickets/entrada", json=corpo).status_code == 400


# ---- H07: proximidade ----------------------------------------------------------

def test_sugestao_prioriza_mesmo_andar(client):
    """Setor desejado Amarelo (Subsolo 1): a sugestao PCD deve ser do mesmo andar."""
    r = client.get("/vagas/proximas", params={"setor_desejado_id": 3, "tipo_vaga": "pcd"})
    corpo = r.json()
    assert corpo["mesmo_andar"] is True
    assert corpo["vaga"]["setor"]["andar"] == "Subsolo 1"
    assert corpo["tempo_caminhada_minutos"] >= 1 and corpo["distancia_metros"] > 0


def test_recusa_devolve_vaga_diferente_e_nao_mais_perto(client):
    a = client.get("/vagas/proximas", params={"setor_desejado_id": 3, "tipo_vaga": "pcd"}).json()
    b = client.get("/vagas/proximas", params=[
        ("setor_desejado_id", 3), ("tipo_vaga", "pcd"), ("excluir_vaga_id", a["vaga"]["id"])]).json()
    assert b["vaga"]["id"] != a["vaga"]["id"]
    assert b["distancia_metros"] >= a["distancia_metros"]


def test_sem_vaga_em_todo_o_estacionamento_404_claro(client, db):
    db.execute(update(Vaga).where(Vaga.tipo == TipoVaga.PCD).values(status=StatusVaga.OCUPADA))
    db.commit()
    r = client.get("/vagas/proximas", params={"setor_desejado_id": 3, "tipo_vaga": "pcd"})
    assert r.status_code == 404 and "pcd" in r.json()["detail"]
    assert client.post("/tickets/entrada", json={"tipo_vaga": "pcd", "setor_id": 3}).status_code == 400


def test_aceites_sucessivos_ocupam_vagas_distintas(client):
    vistas = []
    for _ in range(3):
        s = client.get("/vagas/proximas", params=[("setor_desejado_id", 3), ("tipo_vaga", "pcd")]).json()
        vid = s["vaga"]["id"]
        assert client.post("/tickets/entrada", json={
            "tipo_vaga": "pcd", "setor_id": 3, "vaga_id": vid}).status_code == 201
        vistas.append(vid)
    assert len(set(vistas)) == 3


def test_vaga_id_inexistente_409(client):
    r = client.post("/tickets/entrada", json={"tipo_vaga": "pcd", "vaga_id": 999999})
    assert r.status_code == 409


# ---- H08: EV com carregador -----------------------------------------------------

def test_listagem_eletrico_so_com_carregador_disponivel(client):
    corpo = client.get("/vagas/disponiveis", params={"tipo": "eletrico"}).json()
    assert corpo["total"] >= 1
    assert all(v["tem_carregador"] and v["carregador"]["status"] == "disponivel" for v in corpo["vagas"])


@pytest.mark.xfail(strict=True, reason="BUG-01 (QA v2.0): /vagas/disponiveis lista vaga EV com carregador em manutencao")
def test_eletrico_com_carregador_em_manutencao_nao_e_listado_nem_dado(client, db):
    """H08 cenario 3: vaga com carregador em manutencao nao e oferecida (nem listada)."""
    db.query(Carregador).update({Carregador.status: StatusCarregador.MANUTENCAO})
    db.commit()
    corpo = client.get("/vagas/disponiveis", params={"tipo": "eletrico"}).json()
    assert corpo["total"] == 0, "listagem oferece vaga EV com carregador em manutencao"
    assert client.post("/tickets/entrada", json={"tipo_vaga": "eletrico"}).status_code == 400


def test_ev_ocupado_some_da_listagem_e_volta_na_saida(client):
    antes = client.get("/vagas/disponiveis", params={"tipo": "eletrico"}).json()["total"]
    r = client.post("/tickets/entrada", json={"tipo_vaga": "eletrico"}).json()
    assert client.get("/vagas/disponiveis", params={"tipo": "eletrico"}).json()["total"] == antes - 1
    client.post(f"/tickets/{r['identificador']}/saida")
    assert client.get("/vagas/disponiveis", params={"tipo": "eletrico"}).json()["total"] == antes


def test_apenas_com_carregador_filtra(client):
    corpo = client.get("/vagas/disponiveis", params={"apenas_com_carregador": True}).json()
    assert corpo["total"] >= 1 and all(v["tem_carregador"] for v in corpo["vagas"])


# ---- formato de erro ---------------------------------------------------------------

def test_422_aponta_o_campo_invalido(client):
    r = client.post("/tickets/entrada", json={"tipo_vaga": "foguete"})
    assert r.status_code == 422
    assert any("tipo_vaga" in e["loc"] for e in r.json()["detail"])
