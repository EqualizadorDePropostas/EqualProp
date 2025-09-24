import re
import csv
import json
from typing import Dict, Any, List, Optional


def extract_quantity(pdc_desc) -> Optional[float]:
    """Extrai quantidade da descrição do PDC.

    Aceita tanto um dicionário com a chave 'quantidade_demandada' quanto uma string
    com algum padrão textual contendo números.
    """
    if isinstance(pdc_desc, dict) and 'quantidade_demandada' in pdc_desc:
        qtd_data = pdc_desc['quantidade_demandada']
        if isinstance(qtd_data, dict) and 'valor' in qtd_data:
            try:
                return float(str(qtd_data['valor']).replace(',', '.'))
            except (ValueError, TypeError):
                return None
    if isinstance(pdc_desc, str):
        qtd_match = re.search(r'(quantidade|qtd\s*[/\\]?\s*vol)?[:\s]*([\d,.]+)', pdc_desc, re.IGNORECASE)
        if qtd_match:
            try:
                return float(qtd_match.group(2).replace(',', '.'))
            except (ValueError, TypeError):
                return None
    return None


def _normalize_rfp(rfp_json: Any) -> List[Dict[str, Any]]:
    """Normaliza o JSON da RFP para a forma:
    [{ 'codigo': str, 'especificacoes_tecnicas': {k:{valor,unidade}}, 'quantidade_demandada': {valor,unidade} }, ...]
    """
    obj = rfp_json
    if isinstance(obj, dict):
        # Alguns modelos podem retornar "rfp json" ou "rfp_json"
        if 'rfp json' in obj:
            obj = obj.get('rfp json') or {}
        elif 'rfp_json' in obj:
            obj = obj.get('rfp_json') or {}

    # Capturar lista de PDCs em possíveis variações de chave
    pdcs = None
    if isinstance(obj, dict):
        if 'produtos_demandados' in obj:
            pdcs = obj['produtos_demandados']
        elif 'produtos demandados' in obj:
            pdcs = obj['produtos demandados']
    elif isinstance(obj, list):
        pdcs = obj

    if not isinstance(pdcs, list):
        return []

    norm = []
    for idx, pdc in enumerate(pdcs, start=1):
        if isinstance(pdc, dict):
            codigo = pdc.get('codigo') or f'PDC{idx}'
            espec = pdc.get('especificacoes_tecnicas') or pdc.get('especificacoes tecnicas') or {}
            qtd = pdc.get('quantidade_demandada') or {}
            if not isinstance(espec, dict):
                espec = {}
            if not isinstance(qtd, dict):
                qtd = {}
            norm.append({
                'codigo': codigo,
                'especificacoes_tecnicas': espec,
                'quantidade_demandada': qtd,
            })
        else:
            # Caso a entrada seja uma string/descrição simples
            norm.append({
                'codigo': f'PDC{idx}',
                'especificacoes_tecnicas': {},
                'quantidade_demandada': {'valor': extract_quantity(pdc) or 'null', 'unidade': 'null'},
            })
    return norm


# def _collect_pops_by_pdc(proposta_json: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
#     """Agrupa POPs por código PDC, lendo cada valor de proposta_json
#     que pode ser uma string JSON com a chave raiz 'proposta'.
#     """
#     by_pdc: Dict[str, List[Dict[str, Any]]] = {}
#     for value in proposta_json.values():
#         try:
#             data = json.loads(value) if isinstance(value, str) else value
#         except Exception:
#             continue
#         if not isinstance(data, dict):
#             continue
#         proposta = data.get('proposta', {})
#         pops = proposta.get('pops', []) if isinstance(proposta, dict) else []
#         if not isinstance(pops, list):
#             continue
#         for pop in pops:
#             try:
#                 codigo_pdc = pop.get('codigo_pdc')
#                 if not codigo_pdc:
#                     continue
#                 by_pdc.setdefault(codigo_pdc, []).append(pop)
#             except AttributeError:
#                 continue
#     return by_pdc


def generate_preco_report(rfp_json: Dict[str, Any], proposta_json: Dict[str, Any], filename: str = 'relatorio_preco.csv') -> None:
    """Gera relatorio_preco.csv exatamente no modelo solicitado.

    - Não realiza cálculos; apenas preenche os campos e insere os textos
      'excel formula 1/2/3' onde indicado.
    - Cada linha possui exatamente 25 colunas.
    """
    # Normalizar PDCs
    pdcs = _normalize_rfp(rfp_json)

    # Processar propostas preservando ordem (até 5)
    processed_proposals: List[Dict[str, Any]] = []
    for value in proposta_json.values():
        if not value:
            continue
        try:
            data = json.loads(value) if isinstance(value, str) else value
            if isinstance(data, dict) and 'proposta' in data:
                processed_proposals.append(data['proposta'])
        except Exception:
            continue
    processed_proposals = processed_proposals[:20]

    # Mapeamento por proposta: {codigo_pdc -> pop}
    pops_by_proposal: List[Dict[str, Any]] = []
    for prop in processed_proposals:
        mapping: Dict[str, Any] = {}
        try:
            for pop in prop.get('pops', []) or []:
                codigo = pop.get('codigo_pdc')
                if codigo and codigo not in mapping:
                    mapping[codigo] = pop
        except Exception:
            pass
        pops_by_proposal.append(mapping)

    # Cabeçalho conforme modelo
    header = ['Item', 'ASTREIN', 'Descrição', 'qtd', 'und']
    for _ in range(len(processed_proposals)):
        header.extend(['R$ unit', 'R$ total', 'Semelhança'])
    header.extend(['R$ unit', 'R$ total', '', 'R$ unit', 'R$ total'])

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        # Cabeçalho de duas linhas: preencher apenas acima dos dois últimos 'R$ unit'
        top_header = [''] * len(header)
        try:
            unit_positions = [i for i, v in enumerate(header) if v == 'R$ unit']
            if len(unit_positions) >= 2:
                top_header[unit_positions[-2]] = 'Envoltorio dos mínimos'
                top_header[unit_positions[-1]] = 'Fornecedor vencedor'
        except Exception:
            pass
        # Primeira linha do cabeçalho removida conforme solicitação
        # writer.writerow(top_header)
        writer.writerow(header)

        # Linhas por PDC
        for idx, pdc in enumerate(pdcs, start=1):
            if isinstance(pdc, dict):
                codigo = pdc.get('codigo') or f'PDC{idx}'
                espec = pdc.get('especificacoes_tecnicas') or pdc.get('especificacoes tecnicas') or {}
                if isinstance(espec, dict):
                    parts = []
                    for k, v in espec.items():
                        if isinstance(v, dict):
                            val = v.get('valor')
                            uni = v.get('unidade', 'null')
                            parts.append(f"{k}: {val} {uni}" if uni and uni != 'null' else f"{k}: {val}")
                        else:
                            parts.append(f"{k}: {v}")
                    # Remover prefixos tipo "Descrição:"/"Descricao:" com variações de acento e espaçamento
                    descricao = re.sub(r'^\s*descri[çc][aã]o\s*[:\-]\s*', '', '; '.join(parts), flags=re.IGNORECASE).lower()
                else:
                    descricao = ''
                qtd_data = pdc.get('quantidade_demandada') or {}
                quant_val = (qtd_data.get('valor') if isinstance(qtd_data, dict) else 'null')
                quant_und = (qtd_data.get('unidade', 'null') if isinstance(qtd_data, dict) else 'null')
            else:
                codigo = f'PDC{idx}'
                # Remover prefixos tipo "Descrição:"/"Descricao:" com variações de acento e espaçamento
                descricao = re.sub(r'^\s*descri[çc][aã]o\s*[:\-]\s*', '', str(pdc), flags=re.IGNORECASE).lower()
                quant_val = 'null'
                quant_und = 'null'

            # As duas primeiras colunas vazias conforme modelo; depois descrição/quant/und
            row: List[Any] = ['', '', descricao, quant_val, quant_und]

            # Preencher blocos das 5 propostas
            for p_i in range(len(pops_by_proposal)):
                
                    # Proposta inexistente: mantenha células vazias para valores da proposta
                    
                    
                pop = pops_by_proposal[p_i].get(codigo)
                if isinstance(pop, dict):
                    pu = pop.get('preco_unitario')
                    se = pop.get('semelhanca')
                    unit_val = pu if pu not in [None, ''] else 'null'
                    sim_val = se if se not in [None, ''] else 'null'
                else:
                    # Proposta existe, mas não trouxe POP correspondente: usar 'null'
                    unit_val = 'null'
                    sim_val = 'null'
                row.extend([unit_val, 'excel formula 1', sim_val])

            # Colunas finais: 21='excel formula 3', 22='excel formula 1', 23-25 vazias
            row.extend(['excel formula 3', 'excel formula 1', '', '', ''])

            writer.writerow(row)

        # Linha de Totais
        total_row: List[Any] = ['', '', 'Total', '', '']
        for _ in range(len(processed_proposals)):
            total_row.extend(['', 'excel formula 2', ''])
        total_row.extend(['', 'excel formula 2', '', '', ''])
        writer.writerow(total_row)
