import json
import csv


def generate_comparison_report(pdc_descriptions, raw_results, filename="comparacao_produtos.csv"):
    """Gera relatório de comparação de produtos"""
    processed_proposals = []
    for proposal_json in raw_results.values():
        if proposal_json:
            try:
                processed_proposals.append(json.loads(proposal_json)["proposta"])
            except Exception:
                continue

    if isinstance(pdc_descriptions, list):
        pdc_descriptions = {f"PDC{i+1}": desc for i, desc in enumerate(pdc_descriptions)}

    from .globals import extract_quantity

    pdcs_data = {}
    for pdc_code, pdc_desc in pdc_descriptions.items():
        qtd_demandada = extract_quantity(pdc_desc)
        if isinstance(pdc_desc, dict):
            clean_desc = " | ".join(f"{k}: {v}" for k, v in pdc_desc.items())
        else:
            clean_desc = str(pdc_desc).replace("|", " | ").strip()
        pdcs_data[pdc_code] = {
            "rfp_data": {"quantidade": f"{qtd_demandada:.2f}" if qtd_demandada else "null", "descricao": clean_desc},
            "proposals": []
        }

    for proposal in processed_proposals:
        empresa = proposal["header"]["empresa"].capitalize()
        for pop in proposal.get("pops", []):
            if pop.get("codigo_pdc") and pop["codigo_pdc"] in pdcs_data:
                pdcs_data[pop["codigo_pdc"]]["proposals"].append({
                    "empresa": empresa,
                    "preco_unitario": pop.get("preco_unitario") if pop.get("preco_unitario") not in [None, "null"] else "null",
                    "quantidade": pop.get("quantidade") if pop.get("quantidade") not in [None, "null"] else "null",
                    "semelhanca": pop.get("semelhanca") if pop.get("semelhanca") not in [None, "null"] else "null",
                    "descricao": pop.get("descricao") if pop.get("descricao") not in [None, "null"] else "null",
                    "num_ordem": pop.get("num_ordem") if pop.get("num_ordem") not in [None, "null"] else "null",
                    "reasoning": pop.get("reasoning", "null")
                })

    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["********** TABELA 3: PRODUTOS **********", "", "", "", "", "", "", "", "", ""])
        writer.writerow(["Cod Produto", "Fornecedor", "Preço_unitario", "Quantidade", "Semelhança", "Descrição", "Num_ordem", "Reasoning", "", ""])
        writer.writerow([])

        for pdc_code, pdc_data in pdcs_data.items():
            writer.writerow([
                pdc_code, "RFP", "", pdc_data["rfp_data"]["quantidade"], "",
                pdc_data["rfp_data"]["descricao"], "", "", "", ""
            ])
            for proposal in pdc_data["proposals"]:
                writer.writerow([
                    pdc_code, proposal["empresa"], proposal["preco_unitario"],
                    proposal["quantidade"], proposal["semelhanca"], proposal["descricao"],
                    proposal["num_ordem"], proposal["reasoning"], "", ""
                ])
            writer.writerow([])

    return filename
