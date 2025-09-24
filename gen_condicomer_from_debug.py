import json
from equalprop.reports.relatorio_condicomer import generate_condicomer_report

with open('relatorio_condicomer_debug.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

out = generate_condicomer_report(data)
print(out)
