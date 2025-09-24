from equalprop.reports.relatorio_condicomer import generate_condicomer_report
import os
filename = os.path.abspath('equalprop/out/test_condicomer.csv')
os.makedirs(os.path.dirname(filename), exist_ok=True)
print('writing to', filename)
print(generate_condicomer_report({}, filename))
print('exists?', os.path.exists(filename))
