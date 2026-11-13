"""Testes unitários da função pura de cobrança (DT1/DT2, tabela do PO)."""
from datetime import datetime, timedelta

import pytest

from app.services.ticket_service import calcular_cobranca

ENTRADA = datetime(2026, 11, 13, 10, 0, 0)


def _cobrar(delta, tol=15, regra="hora_cheia", valor_hora=5.0):
    return calcular_cobranca(ENTRADA, ENTRADA + delta, tol, valor_hora, regra)


@pytest.mark.parametrize(
    "delta, valor, isento",
    [
        (timedelta(minutes=10), 0.0, True),
        (timedelta(minutes=15), 0.0, True),
        (timedelta(minutes=15, seconds=1), 5.0, False),
        (timedelta(minutes=16), 5.0, False),
        (timedelta(minutes=75), 5.0, False),
        (timedelta(minutes=75, seconds=1), 10.0, False),
        (timedelta(minutes=76), 10.0, False),
        (timedelta(minutes=135), 10.0, False),
        (timedelta(minutes=135, seconds=1), 15.0, False),
    ],
)
def test_tabela_hora_cheia(delta, valor, isento):
    c = _cobrar(delta)
    assert c.valor == valor
    assert c.isento is isento


def test_cenario_76_minutos():
    c = _cobrar(timedelta(minutes=76))
    assert (c.tempo_total_minutos, c.tempo_faturavel_minutos, c.valor) == (76, 61, 10.0)


def test_isento_zera_faturavel():
    c = _cobrar(timedelta(minutes=5))
    assert c.tempo_faturavel_minutos == 0 and c.tempo_total_minutos == 5


def test_fracao_15min():
    assert _cobrar(timedelta(minutes=16), regra="fracao_15min").valor == 1.25
    assert _cobrar(timedelta(minutes=30), regra="fracao_15min").valor == 1.25
    assert _cobrar(timedelta(minutes=30, seconds=1), regra="fracao_15min").valor == 2.5


def test_tolerancia_configuravel():
    assert _cobrar(timedelta(minutes=10), tol=10).isento is True
    assert _cobrar(timedelta(minutes=11), tol=10).valor == 5.0


def test_tolerancia_zero_cobra_qualquer_permanencia():
    assert _cobrar(timedelta(seconds=2), tol=0).valor == 5.0
