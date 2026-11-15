import pytest
import pandas as pd
from decimal import Decimal

from src.data.preprocessing import converter_decimal, converter_valores_monetarios


def test_conversao_decimal():
    """Verifica a conversão de valores monetários válidos."""

    assert converter_decimal("5,7") == Decimal("5.70")
    assert converter_decimal("13,40") == Decimal("13.40")
    assert converter_decimal("0") == Decimal("0.00")


def test_decimal_nulo_como_zero():
    """Verifica a regra de conversão de valores ausentes."""

    assert converter_decimal(
        None,
        nulos_como_zero=True
    ) == Decimal("0.00")


def test_decimal_invalido():
    """Verifica se valores inválidos provocam exceções."""

    with pytest.raises(ValueError):
        converter_decimal("abc")

    with pytest.raises(ValueError):
        converter_decimal("5,123")

    with pytest.raises(ValueError):
        converter_decimal(None)


def test_be_nao_converte_outros_nulos_para_zero():
    df = pd.DataFrame({
        "valor_linha": ["4,30"],
        "valor_transacao": [None],
        "valor_subsidio": [None],
    })

    with pytest.raises(ValueError, match="ausente"):
        converter_valores_monetarios(df, "BE")

