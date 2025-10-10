import json
import csv


def generate_comparison_report(rfp_json, propostas_json, filename="comparacao_produtos.csv"):
    """Gera relatório de comparação de produtos.

    Robusto para diferentes formatos de rfp_json e para propostas_json como
    dict de caminho->string JSON (com raiz 'proposta').
    """
    processed_proposals = []
    for proposal_json in propostas_json.values():
        if not proposal_json:
            continue
        try:
            data = json.loads(proposal_json) if isinstance(proposal_json, str) else proposal_json
            if isinstance(data, dict) and 'proposta' in data:
                processed_proposals.append(data['proposta'])
        except Exception:
            continue

    # Normalizar RFP: obter lista de PDCs
    pdcs = None
    if isinstance(rfp_json, dict):
        root = rfp_json
        if 'rfp json' in root:
            root = root.get('rfp json') or {}
        elif 'rfp_json' in root:
            root = root.get('rfp_json') or {}
        if isinstance(root, dict):
            pdcs = root.get('produtos_demandados') or root.get('produtos demandados')
    elif isinstance(rfp_json, list):
        pdcs = rfp_json
    if not isinstance(pdcs, list):
        pdcs = []

    from .globals import extract_quantity

    # Montar base por código do PDC
    pdcs_data = {}
    for idx, pdc in enumerate(pdcs, start=1):
        if isinstance(pdc, dict):
            pdc_code = pdc.get('codigo') or f'PDC{idx}'
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
                clean_desc = ' | '.join(parts)
            else:
                clean_desc = ''
            qtd_demandada = extract_quantity(pdc)
        else:
            pdc_code = f'PDC{idx}'
            clean_desc = str(pdc)
            qtd_demandada = extract_quantity(pdc)

        pdcs_data[pdc_code] = {
            'rfp_data': {
                'quantidade': f"{qtd_demandada:.2f}" if isinstance(qtd_demandada, (int, float)) else 'null',
                'descricao': clean_desc
            },
            'proposals': []
        }

    # Anexar propostas
    for proposal in processed_proposals:
        try:
            empresa = (proposal.get('header', {}) or {}).get('empresa')
            empresa_fmt = empresa.capitalize() if isinstance(empresa, str) else 'null'
        except Exception:
            empresa_fmt = 'null'
        for pop in proposal.get('pops', []) if isinstance(proposal, dict) else []:
            if not isinstance(pop, dict):
                continue
            codigo = pop.get('codigo_pdc')
            if codigo and codigo in pdcs_data:
                pdcs_data[codigo]['proposals'].append({
                    'empresa': empresa_fmt,
                    'preco_unitario': pop.get('preco_unitario') if pop.get('preco_unitario') not in [None, 'null'] else 'null',
                    'quantidade': pop.get('quantidade') if pop.get('quantidade') not in [None, 'null'] else 'null',
                    'semelhanca': pop.get('semelhanca') if pop.get('semelhanca') not in [None, 'null'] else 'null',
                    'descricao': pop.get('descricao') if pop.get('descricao') not in [None, 'null'] else 'null',
                    'num_ordem': pop.get('num_ordem') if pop.get('num_ordem') not in [None, 'null'] else 'null',
                    'reasoning': pop.get('reasoning', 'null'),
                })

    # Escrever CSV
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["*******IGNORE ESTA PARTE DO RELATORIO (ela será eventualmente consultada pelos desenvolvedores deste aplicativo para esclarecer duvidas sobre o comportamento da IA) ", "", "", "", "", "", "", "", "", ""])
        writer.writerow(["Cod Produto", "Fornecedor", "Preço_unitario", "Quantidade", "Semelhança", "Descrição", "Num_ordem", "Reasoning", "", ""])
        writer.writerow([])

        for pdc_code, pdc_data in pdcs_data.items():
            writer.writerow([
                pdc_code, 'RFP', '', pdc_data['rfp_data']['quantidade'], '',
                pdc_data['rfp_data']['descricao'], '', '', '', ''
            ])
            for proposal in pdc_data['proposals']:
                writer.writerow([
                    pdc_code, proposal['empresa'], proposal['preco_unitario'],
                    proposal['quantidade'], proposal['semelhanca'], proposal['descricao'],
                    proposal['num_ordem'], proposal['reasoning'], '', ''
                ])
            writer.writerow([])

    return filename

    return filename
