import csv
import json


def generate_suppliers_report(propostas_json, filename: str = 'relatorio_fornecedores.csv'):
    def format_text(text):
        if text is None:
            return 'null'
        try:
            return str(text).title()
        except Exception:
            return 'null'

    def format_email(text):
        if text is None:
            return 'null'
        try:
            s = str(text).strip()
            if not s or s.lower() == 'null':
                return 'null'
            return s.lower()
        except Exception:
            return 'null'

    # Extrair headers das propostas (convertendo de JSON string quando necessário)
    headers = []
    for value in propostas_json.values():
        try:
            data = json.loads(value) if isinstance(value, str) else value
            header = data.get('proposta', {}).get('header', {})
            if header:
                headers.append(header)
        except Exception:
            continue

    # Limitar número de propostas (0 a 20)
    num_propostas = max(0, min(len(headers), 20))

    # Criar a estrutura de dados para o CSV
    rows = []

    # Cabeçalho principal dinâmico (somente propostas existentes)
    header_row = [''] * 5
    for i in range(num_propostas):
        header_row.extend([f'Fornecedor {i + 1}', '', ''])
    # Colunas extras após a última trinca
    header_row.extend(['Envoltório dos mínimos', '', '', 'Fornecedor vencedor'])
    rows.append(header_row)

    # Linha EMPRESA:
    empresa_row = ['Empresa'] + [''] * 4
    for i in range(num_propostas):
        empresa = headers[i].get('empresa') if i < len(headers) else None
        empresa_row.extend([format_text(empresa) if empresa is not None else 'null', '', ''])
    rows.append(empresa_row)

    # Linha CNPJ:
    cnpj_row = ['CNPJ'] + [''] * 4
    for i in range(num_propostas):
        cnpj = headers[i].get('cnpj') if i < len(headers) else None
        cnpj_row.extend([cnpj if cnpj is not None else 'null', '', ''])
    rows.append(cnpj_row)

    # Linha TEL:
    tel_row = ['Tel'] + [''] * 4
    for i in range(num_propostas):
        tel = headers[i].get('tel') if i < len(headers) else None
        tel_row.extend([tel if tel is not None else 'null', '', ''])
    rows.append(tel_row)

    # Linha CEL:
    cel_row = ['Cel'] + [''] * 4
    for i in range(num_propostas):
        cel = headers[i].get('cel') if i < len(headers) else None
        cel_row.extend([cel if cel is not None else 'null', '', ''])
    rows.append(cel_row)

    # Linha EMAIL (sempre em minúsculas):
    email_row = ['email'] + [''] * 4
    for i in range(num_propostas):
        email = headers[i].get('email') if i < len(headers) else None
        email_row.extend([format_email(email), '', ''])
    rows.append(email_row)

    # Linha CONTATO:
    contato_row = ['Contato'] + [''] * 4
    for i in range(num_propostas):
        representante = headers[i].get('representante') if i < len(headers) else None
        contato_row.extend([format_text(representante) if representante is not None else 'null', '', ''])
    rows.append(contato_row)

    # Escrever o arquivo CSV
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerows(rows)

    return filename

