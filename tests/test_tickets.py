"""Testes de integração: entrada, saída e atomicidade."""
from datetime import timedelta

import pytest
from sqlalchemy import func, update

from app.models import StatusVaga, Ticket, TipoVaga, Vaga
from app.schemas import TicketSaidaRequest
from app.services.ticket_service import TicketService

TIPOS = ["comum", "idoso", "pcd", "neurodivergente", "eletrico", "moto"]


def livres(client, tipo):
    return client.get("/vagas/disponiveis", params={"tipo": tipo}).json()["total"]


def _entrada(client, **extra):
    r = client.post("/tickets/entrada", json={"tipo_vaga": "comum", "setor_id": 1, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def test_entrada_201_com_andar_e_vaga_ocupada(client, db):
    antes = livres(client, "comum")
    r = client.post("/tickets/entrada", json={"tipo_vaga": "comum", "setor_id": 1})
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["vaga"]["setor"]["andar"] == "Subsolo 1"
    assert corpo["vaga"]["setor_id"] == 1
    assert corpo["vaga"]["status"] == "ocupada"
    assert corpo["tolerancia_minutos"] == 15 and corpo["valor_hora"] == 5.0
    assert livres(client, "comum") == antes - 1
    assert db.get(Vaga, corpo["vaga"]["id"]).status == StatusVaga.OCUPADA


@pytest.mark.parametrize("tipo", TIPOS)
def test_entrada_para_cada_tipo(client, tipo):
    r = client.post("/tickets/entrada", json={"tipo_vaga": tipo})
    assert r.status_code == 201, r.text
    assert r.json()["vaga"]["tipo"] == tipo


def test_moto_fica_no_laranja(client):
    r = client.post("/tickets/entrada", json={"tipo_vaga": "moto"})
    assert r.json()["vaga"]["setor"]["nome"] == "Laranja"


def test_eletrico_tem_carregador(client):
    r = client.post("/tickets/entrada", json={"tipo_vaga": "eletrico"})
    assert r.json()["vaga"]["tem_carregador"] is True


def test_tipo_invalido_422(client):
    assert client.post("/tickets/entrada", json={"tipo_vaga": "foguete"}).status_code == 422


def test_tipo_esgotado_400_sem_alterar_nada(client, db):
    while True:
        r = client.post("/tickets/entrada", json={"tipo_vaga": "pcd"})
        if r.status_code != 201:
            break
    assert r.status_code == 400
    assert "pcd" in r.json()["detail"]
    antes = db.query(func.count(Ticket.id)).scalar()
    assert client.post("/tickets/entrada", json={"tipo_vaga": "pcd"}).status_code == 400
    db.expire_all()
    assert db.query(func.count(Ticket.id)).scalar() == antes


def test_comum_esgotado_nao_recebe_restritas(client, db):
    db.execute(update(Vaga).where(Vaga.tipo == TipoVaga.COMUM).values(status=StatusVaga.OCUPADA))
    db.commit()
    assert client.post("/tickets/entrada", json={"tipo_vaga": "comum"}).status_code == 400
    r = client.post("/tickets/entrada", json={"tipo_vaga": "idoso"})
    assert r.status_code == 201 and r.json()["vaga"]["tipo"] == "idoso"


def test_entrada_atomica_rollback_em_falha(client, db, monkeypatch):
    """RN 9: falha depois da reserva não pode deixar vaga presa nem ticket órfão."""
    antes_livres = livres(client, "comum")
    antes_tickets = db.query(func.count(Ticket.id)).scalar()

    def falha(*args, **kwargs):
        raise RuntimeError("falha forçada")

    monkeypatch.setattr(TicketService, "_gerar_mensagem_entrada", falha)
    with pytest.raises(RuntimeError):
        client.post("/tickets/entrada", json={"tipo_vaga": "comum", "setor_id": 1})
    db.expire_all()
    assert db.query(func.count(Ticket.id)).scalar() == antes_tickets
    assert livres(client, "comum") == antes_livres


def test_saida_imediata_isenta_e_libera_vaga(client, db):
    t = _entrada(client)
    r = client.post("/tickets/saida", json={"identificador": t["identificador"]})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["isento"] is True and corpo["valor"] == 0.0
    assert corpo["status_pagamento"] == "isento"
    db.expire_all()
    assert db.get(Vaga, t["vaga"]["id"]).status == StatusVaga.LIVRE


def test_saida_76_minutos_cobra_10(client, db):
    t = _entrada(client)
    ticket = db.query(Ticket).filter(Ticket.identificador == t["identificador"]).one()
    resp = TicketService.registrar_saida(
        db, TicketSaidaRequest(identificador=t["identificador"]),
        agora=ticket.entrada + timedelta(minutes=76),
    )
    assert (resp.tempo_total_minutos, resp.tempo_faturavel_minutos, resp.valor) == (76, 61, 10.0)
    assert resp.status_pagamento.value == "pendente"
    db.expire_all()
    assert db.get(Vaga, t["vaga"]["id"]).status == StatusVaga.LIVRE


def test_saida_repetida_409_e_inexistente_404(client):
    t = _entrada(client)
    corpo = {"identificador": t["identificador"]}
    assert client.post("/tickets/saida", json=corpo).status_code == 200
    r = client.post("/tickets/saida", json=corpo)
    assert r.status_code == 409 and "já" in r.json()["detail"]
    r = client.post("/tickets/saida", json={"identificador": "XXXXXXXX"})
    assert r.status_code == 404 and "não encontrado" in r.json()["detail"]


def test_alias_saida_por_url(client):
    t = _entrada(client)
    url = f"/tickets/{t['identificador']}/saida"
    r = client.post(url)
    assert r.status_code == 200 and r.json()["isento"] is True
    assert client.post(url).status_code == 409
    assert client.post("/tickets/XXXXXXXX/saida").status_code == 404


def test_tolerancia_zero_cobra_pelo_menos_uma_hora(client):
    r = client.patch("/config/admin/tolerancia_minutos", json={"valor": "0"})
    assert r.status_code == 200, r.text
    t = _entrada(client)
    s = client.post(f"/tickets/{t['identificador']}/saida").json()
    assert s["valor"] == 5.0 and s["status_pagamento"] == "pendente"
