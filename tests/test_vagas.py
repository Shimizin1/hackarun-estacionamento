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
