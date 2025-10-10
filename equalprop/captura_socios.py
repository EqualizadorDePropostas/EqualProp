# -*- coding: utf-8 -*-
"""
ObtǸm o quadro 'S��cios' (QSA) por CNPJ usando fontes que permitem automa��ǜo.
- Entrada: cnpjs_by_id -> dict {ID: CNPJ}
- Sa��da: quadros_societarios -> dict {ID: [linhas] | None}
Requer: pip install requests
"""

import re
import time
import requests
from typing import Dict, List, Optional

def _fetch_qsa_brasilapi(cnpj: str) -> Optional[List[str]]:
    """Tenta obter QSA via BrasilAPI. Retorna lista de linhas ou None."""
    cnpj_digits = re.sub(r"\D", "", str(cnpj or ""))
    if len(cnpj_digits) != 14:
        return None
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_digits}"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json()
        qsa = data.get("qsa") or []
        if not qsa:
            return None

        linhas = []
        for socio in qsa:
            nome = socio.get("nome_socio") or socio.get("nome")
            qualificacao = socio.get("qualificacao_socio") or socio.get("qual")
            campos = [valor for valor in (nome, qualificacao) if valor]
            if campos:
                linhas.append(", ".join(campos))
        return linhas or None
    except Exception:
        return None

def get_quadro_societario_for_list(cnpjs_by_id: Dict[str, str]) -> Dict[str, Optional[List[str]]]:
    """
    Para cada {id: cnpj}, retorna {id: [linhas_do_quadro_s��cios] | None}.
    Atualmente usa BrasilAPI. Dǭ para plugar outros provedores como fallback.
    """
    resultados: Dict[str, Optional[List[str]]] = {}
    for file_id, cnpj in cnpjs_by_id.items():
        linhas = _fetch_qsa_brasilapi(cnpj)
        resultados[file_id] = linhas  # mantǸm None quando nǜo dispon��vel
        time.sleep(0.15)  # gentileza p/ rate limit
    return resultados

# --------- exemplo de uso ----------
if __name__ == "__main__":
    cnpjs_by_id = {
        r"C:\Temp\001.pdf": "64919541000109",
        r"C:\Temp\002.pdf": "22401620000175",
        r"C:\Temp\003.pdf": "52067115000105",
    }
    quadros_societarios = get_quadro_societario_for_list(cnpjs_by_id)
    from pprint import pprint; pprint(quadros_societarios)
