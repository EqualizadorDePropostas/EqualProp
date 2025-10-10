import csv
import re
from typing import Any, List

_MAX_PROPOSTAS = 20


def _capitaliza(texto: str) -> str:
    texto = str(texto).lower()
    return re.sub(r"\S+", lambda m: m.group(0)[0].upper() + m.group(0)[1:], texto)


def _socios_lista(valor: Any) -> List[str]:
    if valor is None:
        return []
    if isinstance(valor, str):
        valores = [valor]
    else:
        try:
            valores = list(valor)
        except TypeError:
            valores = [valor]
    socios = []
    for item in valores:
        if item is None:
            continue
        texto = str(item).strip()
        if not texto:
            continue
        socios.append(_capitaliza(texto))
    return socios


def _normalize_socios(valor: Any) -> List[str]:
    socios = _socios_lista(valor)
    return socios if socios else ['null']


def _flag(valor: Any) -> str:
    if valor is None:
        return ''
    if isinstance(valor, bool):
        return 'Sim' if valor else 'N\u00e3o'
    texto = str(valor).strip()
    if not texto or texto.lower() == 'null':
        return ''
    check = texto.lower()
    if check in ('sim', 'true', 'yes'):
        return 'Sim'
    if check in ('nao', 'n\u00e3o', 'false', 'no'):
        return 'N\u00e3o'
    return _capitaliza(texto)


def generate_socios_report(quadros_societarios, socio_comum):
    try:
        quadros = dict(quadros_societarios or {})
    except Exception:
        quadros = {}
    try:
        socio_map = dict(socio_comum or {})
    except Exception:
        socio_map = {}

    itens = list(quadros.items())[:_MAX_PROPOSTAS]
    base_cols = 5 + 3 * len(itens)
    socios_por_proposta = [_normalize_socios(val) for _, val in itens]

    linhas = [
        ['Quadro de sócios e administradores'] + [''] * (base_cols - 1)
    ]

    linha = ['Este CNPJ tem sócio em comum com outro CNPJ ?'] + [''] * 4
    for chave, _ in itens:
        linha.append(_flag(socio_map.get(chave)))
        linha.extend(['', ''])
    linha.extend([''] * (base_cols - len(linha)))
    linhas.append(linha)

    altura = max((len(lst) for lst in socios_por_proposta), default=0)
    for idx in range(altura):
        row = [''] * 5
        for lista in socios_por_proposta:
            value = lista[idx] if idx < len(lista) else ''
            row.append(value)
            row.extend(['', ''])
        row.extend([''] * (base_cols - len(row)))
        linhas.append(row)

    with open('relatorio_socios.csv', 'w', newline='', encoding='utf-8') as csvfile:
        csv.writer(csvfile).writerows(linhas)
    return 'relatorio_socios.csv'
