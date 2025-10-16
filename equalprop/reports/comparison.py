import csv
import json
import re
from typing import Any, Dict, Iterable, List, Tuple

from .globals import _normalize_rfp

_PREFIX_RE = re.compile(r'^\s*descri(?:\u00e7\u00e3o|cao)\s+do\s+produto\s*[:\-]?\s*', re.IGNORECASE)


def _clean_description(text: Any) -> str:
    if not text:
        return ''
    return _PREFIX_RE.sub('', str(text)).strip()


def _stringify(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        if 'valor' in value:
            return _stringify(value.get('valor'))
        if 'descricao' in value:
            return _stringify(value.get('descricao'))
    return str(value)


def _rfp_entries(rfp_json: Any) -> List[Any]:
    obj = rfp_json
    if isinstance(obj, dict):
        if 'rfp json' in obj:
            obj = obj.get('rfp json') or {}
        elif 'rfp_json' in obj:
            obj = obj.get('rfp_json') or {}
    if isinstance(obj, dict):
        items = obj.get('produtos_demandados') or obj.get('produtos demandados')
    elif isinstance(obj, list):
        items = obj
    else:
        items = []
    return items if isinstance(items, list) else []


def _rfp_description(pdc: Any) -> str:
    if isinstance(pdc, str):
        return _clean_description(pdc)
    if isinstance(pdc, dict):
        for key in ('descricao', 'descricao_produto', 'descricao_produto_demandado', 'descricao_demandada'):
            val = pdc.get(key)
            if val:
                return _clean_description(_stringify(val))
        espec = pdc.get('especificacoes_tecnicas')
        if isinstance(espec, dict):
            parts = []
            for key, val in espec.items():
                if isinstance(val, dict):
                    valor = _stringify(val.get('valor'))
                    unidade = _stringify(val.get('unidade'))
                    if valor:
                        parts.append(f"{key}: {valor}{(' ' + unidade) if unidade else ''}")
                else:
                    sval = _stringify(val)
                    if sval:
                        parts.append(f"{key}: {sval}")
            if parts:
                return _clean_description('; '.join(parts))
    return ''


def _rfp_quantity(pdc: Dict[str, Any]) -> Tuple[str, str]:
    qtd = pdc.get('quantidade_demandada') if isinstance(pdc, dict) else None
    if isinstance(qtd, dict):
        return _stringify(qtd.get('valor')), _stringify(qtd.get('unidade'))
    return '', ''


def _pop_value(pop: Dict[str, Any], *keys: Iterable[str]) -> str:
    if not isinstance(pop, dict):
        return ''
    for key in keys:
        if isinstance(key, Iterable) and not isinstance(key, (str, bytes)):
            for sub in key:
                val = pop.get(sub)
                if val not in (None, '', [], {}):
                    return _stringify(val)
            continue
        val = pop.get(key)
        if val not in (None, '', [], {}):
            return _stringify(val)
    return ''


def _pop_quantity(pop: Dict[str, Any]) -> Tuple[str, str]:
    if not isinstance(pop, dict):
        return '', ''
    qtd = pop.get('quantidade_oferecida') or pop.get('quantidade')
    if isinstance(qtd, dict):
        return _stringify(qtd.get('valor')), _stringify(qtd.get('unidade'))
    return _stringify(qtd), ''


def _row(label: str, values: List[str]) -> List[str]:
    row = [label, '', '', '', '']
    for val in values:
        row.extend([val, '', ''])
    return row


def generate_comparison_report(rfp_json: Dict[str, Any], propostas_json: Dict[str, Any], filename: str = 'comparacao_produtos.csv') -> None:
    raw_pdcs = _rfp_entries(rfp_json)
    pdcs = _normalize_rfp(rfp_json) if rfp_json else []

    proposals: List[Dict[str, Any]] = []
    if isinstance(propostas_json, dict):
        for value in propostas_json.values():
            if not value:
                continue
            try:
                data = json.loads(value) if isinstance(value, str) else value
            except Exception:
                continue
            if isinstance(data, dict):
                proposta = data.get('proposta') if 'proposta' in data else data
                if isinstance(proposta, dict):
                    proposals.append(proposta)
    proposals = proposals[:20]

    associations: List[Tuple[Dict[str, Any], Dict[str, int]]] = []
    for proposta in proposals:
        mapping: Dict[str, Any] = {}
        positions: Dict[str, int] = {}
        pops = proposta.get('pops') if isinstance(proposta, dict) else []
        if isinstance(pops, list):
            for idx, pop in enumerate(pops, 1):
                if not isinstance(pop, dict):
                    continue
                codigo = pop.get('codigo_pdc') or pop.get('codigo')
                if codigo and codigo not in mapping:
                    mapping[codigo] = pop
                    positions[codigo] = pop.get('posicao') or idx
        associations.append((mapping, positions))

    total_cols = 1 + 4 + 3 * len(proposals)
    header_msg = '*******IGNORE ESTA PARTE DO RELATORIO (ela sera eventualmente consultada pelos desenvolvedores deste aplicativo para esclarecer duvidas sobre o comportamento da IA) '

    with open(filename, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow([header_msg] + [''] * (total_cols - 1))
        writer.writerow([''] * total_cols)

        for idx, pdc in enumerate(pdcs, 1):
            raw = raw_pdcs[idx - 1] if idx - 1 < len(raw_pdcs) else pdc
            codigo = pdc.get('codigo') if isinstance(pdc, dict) else ''
            desc_rfp = _rfp_description(raw) or _rfp_description(pdc)
            if not desc_rfp and not isinstance(raw, dict):
                desc_rfp = _clean_description(_stringify(raw))
            # Title-case the demanded product description
            if desc_rfp:
                desc_rfp = desc_rfp.title()
            qtd_val, qtd_unit = _rfp_quantity(pdc if isinstance(pdc, dict) else {})

            writer.writerow([f'Produto {idx}'] + [''] * (total_cols - 1))
            writer.writerow(_row('Descrição do produto demandado na requisição de compra', [desc_rfp] * len(proposals)))

            desc_oferta: List[str] = []
            raciocinio_vals: List[str] = []
            semelhanca_vals: List[str] = []
            qtd_oferecida_vals: List[str] = []
            preco_unitario_vals: List[str] = []
            pos_vals: List[str] = []

            for mapping, positions in associations:
                pop = mapping.get(codigo)
                oferta_descr = _pop_value(pop, 'descricao_produto_oferecido', 'descricao_produto', 'descricao', 'produto_oferecido', 'produto')
                # Title-case the offered product description (associated to this demanded product)
                if oferta_descr:
                    oferta_descr = oferta_descr.title()
                desc_oferta.append(oferta_descr)
                raciocinio_vals.append(_pop_value(pop, 'reasoning', 'raciocinio', 'explicacao', 'justificativa'))
                semelhanca_vals.append(_pop_value(pop, 'semelhanca', 'grau_semelhanca', 'similaridade'))
                qtd_val_of, qtd_unit_of = _pop_quantity(pop)
                qtd_oferecida_vals.append(qtd_val_of)
                preco_unitario_vals.append(_pop_value(pop, 'preco_unitario', 'valor_unitario', 'preco', 'preco_oferecido'))
                pos_val = _pop_value(pop, 'posicao')
                if not pos_val:
                    pos_val = _stringify(positions.get(codigo)) if positions.get(codigo) else ''
                pos_vals.append(pos_val)

            writer.writerow(_row('Descrição do produto oferecido na proposta (que a IA associou a este produto demandado)', desc_oferta))
            writer.writerow(_row('Raciocinio usado pela IA para associar este produto demandado com este produto oferecido', raciocinio_vals))
            writer.writerow(_row('Semelhança entre o produto demandado e o produto oferecido', semelhanca_vals))
            writer.writerow(_row('Quantidade demandada na requisicao de compra', [qtd_val] * len(proposals)))
            writer.writerow(_row('Quantidade oferecida na proposta', qtd_oferecida_vals))
            writer.writerow(_row('Unidade da quantidade demandada na requisicao de compra', [qtd_unit] * len(proposals)))
            writer.writerow(_row('Unidade da quantidade oferecida na proposta', [''] * len(proposals)))
            writer.writerow(_row('Preço unitario oferecido na proposta', preco_unitario_vals))
            writer.writerow(_row('Posição em que o produto aparece na proposta', pos_vals))
            writer.writerow([''] * total_cols)

        if not pdcs:
            writer.writerow([''] * total_cols)
