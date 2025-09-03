import json
import csv


def generate_suppliers_report(raw_results, filename="relatorio_fornecedores.csv"):
    """Gera relatório de fornecedores"""
    header = ["********** TABELA 1: FORNECEDORES **********", "", "", "", "", "", "", "", ""]
    subheader = ["Proposta", "Empresa", "Representante", "Telefone", "Email", "", "", "", ""]

    proposal_rows = []
    for i, (proposal_path, proposal_data) in enumerate(raw_results.items(), 1):
        if not proposal_data:
            continue
        try:
            data = json.loads(proposal_data)
            header_info = data["proposta"]["header"]
            proposal_rows.append([
                f"Proposta {i}",
                header_info["empresa"].capitalize(),
                header_info["representante"].capitalize(),
                header_info["telefone"],
                header_info["email"].lower() if header_info["email"] else "",
                "", "", "", ""
            ])
        except Exception as e:
            print(f"[ERRO] Erro ao processar {proposal_path}: {str(e)}")

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        writer.writerow(subheader)
        writer.writerow([])
        for row in proposal_rows:
            writer.writerow(row)

    return filename
