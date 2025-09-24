import csv
import json
import unicodedata
from typing import Any, Dict, Optional


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _norm_key(s: str) -> str:
    s = _strip_accents(s or "")
    s = s.lower().strip()
    # Remover espaços duplicados
    s = " ".join(s.split())
    return s


def _get_header_dict(rfp_json: Any) -> Dict[str, Any]:
    """Extrai o dicionário de header da RFP, considerando variações de chaves."""
    obj = rfp_json
    if isinstance(obj, dict):
        # Pode vir aninhado em "rfp json" ou "rfp_json"
        if 'rfp json' in obj:
            obj = obj.get('rfp json') or {}
        elif 'rfp_json' in obj:
            obj = obj.get('rfp_json') or {}
    if isinstance(obj, dict):
        header = obj.get('header')
        if isinstance(header, dict):
            return header
    # Caso não encontre, retornar dict vazio
    return {}


def _lookup(header: Dict[str, Any], *candidates: str) -> Optional[str]:
    """Procura por uma chave no header de forma robusta (case/acento-insensível)."""
    if not isinstance(header, dict):
        return None
    # Índice normalizado das chaves existentes
    idx = {_norm_key(k): k for k in header.keys() if isinstance(k, str)}
    for cand in candidates:
        norm = _norm_key(cand)
        if norm in idx:
            val = header.get(idx[norm])
            return None if val is None else str(val)
    return None


def generate_rfp_header_report(rfp_json: Dict[str, Any], filename: str = "relatorio_rfp_cabecalho.csv") -> str:
    """
    Gera o arquivo CSV do cabeçalho da RFP com o layout:

    Obra,<Obra>
    Solicitante,<Solicitante>
    Data da requisição,<Data da requisição>
    Data de necessidade,<Data de necessidade>
    Comprador,<Comprador>
    """
    header = _get_header_dict(rfp_json)

    obra = _lookup(header, 'Obra')
    solicitante = _lookup(header, 'Solicitante')
    data_req = _lookup(header, 'Data da Requisição', 'Data da Requisicao')
    data_nec = _lookup(header, 'Data da Necessidade')
    comprador = _lookup(header, 'Comprador')

    # Aplicar Title Case nos campos textuais
    def _title_case(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        try:
            return str(val).title()
        except Exception:
            return str(val)

    obra = _title_case(obra)
    solicitante = _title_case(solicitante)
    comprador = _title_case(comprador)

    rows = [
        ['Obra', obra or 'null'],
        ['Solicitante', solicitante or 'null'],
        ['Data da requisição', data_req or 'null'],
        ['Data de necessidade', data_nec or 'null'],
        ['Comprador', comprador or 'null'],
    ]

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        # Mover contefdo da coluna B para a coluna C, deixando B vazia
        rows3 = [[r[0], '', (r[1] if len(r) > 1 else '')] for r in rows]
        writer.writerows(rows3)

    return filename
