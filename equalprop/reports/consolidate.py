import csv
import openpyxl


def consolidate_reports():
    """Consolida todos os relatórios em CSV e Excel"""
    tabelas = ["relatorio_fornecedores.csv", "relatorio_valores_globais.csv", "comparacao_produtos.csv"]
    arquivo_csv = "relatorio_consolidado.csv"
    arquivo_xlsx = "relatorio_consolidado.xlsx"

    linhas_consolidadas = []
    for tabela in tabelas:
        try:
            with open(tabela, 'r', encoding='utf-8') as arquivo:
                linhas_consolidadas.extend(list(csv.reader(arquivo)))
            if tabela != tabelas[-1]:
                linhas_consolidadas.extend([[] for _ in range(4)])
        except FileNotFoundError:
            print(f"[AVISO] Arquivo não encontrado: {tabela}")

    with open(arquivo_csv, 'w', newline='', encoding='utf-8') as arquivo:
        csv.writer(arquivo).writerows(linhas_consolidadas)

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    for row in linhas_consolidadas:
        sheet.append(row)
    workbook.save(arquivo_xlsx)

    print(f"[OK] Relatório consolidado: {arquivo_csv} e {arquivo_xlsx}")
    return arquivo_csv, arquivo_xlsx
