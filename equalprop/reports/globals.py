import re
import json
import pandas as pd


def extract_quantity(pdc_desc):
    """Extrai quantidade da descrição do PDC"""
    if isinstance(pdc_desc, dict) and 'quantidade_demandada' in pdc_desc:
        qtd_data = pdc_desc['quantidade_demandada']
        if isinstance(qtd_data, dict) and 'valor' in qtd_data:
            try:
                return float(str(qtd_data['valor']).replace(',', '.'))
            except (ValueError, TypeError):
                pass
    if isinstance(pdc_desc, str):
        qtd_match = re.search(r'(quantidade|qtd\s*[/\\]\s*vol)[:\s]*([\d,.]+)', pdc_desc, re.IGNORECASE)
        if qtd_match:
            try:
                return float(qtd_match.group(2).replace(',', '.'))
            except (ValueError, TypeError):
                pass
    return None


def generate_global_report(pdc_descriptions, raw_results, filename="relatorio_valores_globais.csv"):
    """Gera relatório de valores globais"""
    empresas = []
    propostas_processadas = []

    for proposta_json in raw_results.values():
        if not proposta_json:
            continue
        try:
            proposta_data = json.loads(proposta_json)['proposta']
            empresas.append(proposta_data['header']['empresa'].capitalize())
            propostas_processadas.append(proposta_data)
        except Exception:
            continue

    if isinstance(pdc_descriptions, list):
        pdc_descriptions = {f"PDC{i+1}": desc for i, desc in enumerate(pdc_descriptions)}

    linhas = [
        ["********** TABELA 2: VALORES GLOBAIS **********", "", "", "", ""],
        ["Produtos", "Descrição", "Quantidade demandada", *empresas]
    ]

    totais_fornecedores = {empresa: 0 for empresa in empresas}

    for pdc_codigo, pdc_desc in pdc_descriptions.items():
        qtd_demandada = extract_quantity(pdc_desc)
        if isinstance(pdc_desc, dict):
            descricao = " | ".join(f"{k}: {v}" for k, v in pdc_desc.items())
        else:
            descricao = str(pdc_desc).replace("\n", " | ").strip()

        linha = [pdc_codigo, descricao, f"{qtd_demandada:.2f}" if qtd_demandada else "null"]

        for empresa in empresas:
            valor_global = "null"
            if qtd_demandada:
                for proposta in propostas_processadas:
                    if proposta['header']['empresa'].capitalize() == empresa:
                        for pop in proposta.get('pops', []):
                            if pop.get('codigo_pdc') == pdc_codigo:
                                try:
                                    preco_unit = pop.get('preco_unitario')
                                    qtd = pop.get('quantidade')
                                    if preco_unit not in [None, 'null'] and qtd not in [None, 'null']:
                                        valor = float(preco_unit) * float(qtd)
                                        valor_global = f"{valor:.2f}"
                                        totais_fornecedores[empresa] += valor
                                        break
                                except (TypeError, ValueError):
                                    pass
            linha.append(valor_global)
        linhas.append(linha)

    linha_total = ["Total por fornecedor", "", ""] + [
        f"{totais_fornecedores.get(empresa, 0):.2f}" if totais_fornecedores.get(empresa, 0) != 0 else "null"
        for empresa in empresas
    ]
    linhas.append(linha_total)

    pd.DataFrame(linhas).to_csv(filename, index=False, header=False, encoding='utf-8-sig')
    return filename
