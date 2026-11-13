"""Testes de /vagas/disponiveis, contadores por setor, /api/info e frontend."""


def por_setor(client, **params):
    corpo = client.get("/vagas/disponiveis", params=params).json()
    return {s["setor_nome"]: s for s in corpo["por_setor"]}


def test_setor_sem_vaga_do_tipo_aparece_com_livres_zero(client):
    setores = por_setor(client, tipo="pcd")
    assert len(setores) == 6
    assert setores["Amarelo"]["livres"] == 0 and setores["Amarelo"]["total"] == 0


def test_contagens_coerentes_por_tipo(client):
    for tipo in ["comum", "idoso", "pcd", "eletrico", "moto"]:
        corpo = client.get("/vagas/disponiveis", params={"tipo": tipo}).json()
        assert corpo["total"] == sum(s["livres"] for s in corpo["por_setor"])
        for s in corpo["por_setor"]:
            # sem vagas em manutenção no seed: livres + ocupadas == total do tipo
            assert s["livres"] + s["ocupadas"] == s["total"]


def test_moto_total_10(client):
    assert client.get("/vagas/disponiveis", params={"tipo": "moto"}).json()["total"] == 10


def test_todos_os_tipos_tem_vaga_livre(client):
    for tipo in ["comum", "idoso", "pcd", "neurodivergente", "eletrico", "moto", "gestante"]:
        assert client.get("/vagas/disponiveis", params={"tipo": tipo}).json()["total"] >= 1, tipo


def test_total_geral_356(client):
    corpo = client.get("/vagas/disponiveis").json()
    assert sum(s["total"] for s in corpo["por_setor"]) == 356


def test_setor_inexistente_200_vazio(client):
    r = client.get("/vagas/disponiveis", params={"setor_id": 9999})
    assert r.status_code == 200
    assert r.json()["total"] == 0 and r.json()["por_setor"] == []


def test_filtro_andar(client):
    assert set(por_setor(client, andar="Subsolo 2")) == {"Vermelho", "Roxo", "Laranja"}


def test_frontend_servido_na_raiz_e_info(client):
    r = client.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "Equipe 43" in client.get("/api/info").json()["team"]
    assert client.get("/health").json()["database"] == "connected"
    assert client.get("/docs").status_code == 200


# ---- A11: proximidade, exclusão repetível, vaga_id --------------------------

def proxima(client, setor=3, tipo="pcd", excluir=()):
    params = [("setor_desejado_id", setor), ("tipo_vaga", tipo)]
    params += [("excluir_vaga_id", i) for i in excluir]
    return client.get("/vagas/proximas", params=params)


def test_amarelo_pcd_sugere_verde(client):
    r = proxima(client)
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["vaga"]["setor"]["nome"] == "Verde"
    assert corpo["mesmo_andar"] is True
    assert corpo["distancia_metros"] > 0


def test_recusas_seguidas_devolvem_vagas_distintas_e_depois_404(client):
    total_pcd = client.get("/vagas/disponiveis", params={"tipo": "pcd"}).json()["total"]
    vistas = []
    for _ in range(total_pcd):
        r = proxima(client, excluir=vistas)
        assert r.status_code == 200
        vistas.append(r.json()["vaga"]["id"])
    assert len(set(vistas)) == total_pcd
    assert proxima(client, excluir=vistas).status_code == 404


def test_entrada_com_vaga_id_ocupa_exatamente_essa_vaga(client):
    sugerida = proxima(client).json()["vaga"]
    r = client.post("/tickets/entrada", json={
        "tipo_vaga": "pcd", "setor_id": 3, "vaga_id": sugerida["id"]})
    assert r.status_code == 201
    assert r.json()["vaga"]["id"] == sugerida["id"]


def test_vaga_id_ocupada_ou_de_outro_tipo_409(client):
    sugerida = proxima(client).json()["vaga"]
    corpo = {"tipo_vaga": "pcd", "vaga_id": sugerida["id"]}
    assert client.post("/tickets/entrada", json=corpo).status_code == 201
    assert client.post("/tickets/entrada", json=corpo).status_code == 409
    comum = client.get("/vagas/disponiveis", params={"tipo": "comum"}).json()["vagas"][0]
    r = client.post("/tickets/entrada", json={"tipo_vaga": "pcd", "vaga_id": comum["id"]})
    assert r.status_code == 409


def test_entrada_setor_cheio_usa_proximidade(client):
    r = client.post("/tickets/entrada", json={"tipo_vaga": "pcd", "setor_id": 3})
    assert r.status_code == 201
    assert r.json()["vaga"]["setor"]["nome"] == "Verde"


# ---- A12: /setores ------------------------------------------------------------

def test_setores_lista_seis_com_contagens(client):
    r = client.get("/setores")
    assert r.status_code == 200
    setores = r.json()
    assert [s["nome"] for s in setores] == ["Azul", "Verde", "Amarelo", "Vermelho", "Roxo", "Laranja"]
    assert sum(s["capacidade_total"] for s in setores) == 356
    for s in setores:
        assert s["vagas_livres"] + s["vagas_ocupadas"] == s["capacidade_total"]
