import pathlib
lines = pathlib.Path('equalprop/reports/consolidate.py').read_text().splitlines()
for i,line in enumerate(lines,1):
    if '_safe_generate' in line:
        print(i, line)
