from pathlib import Path
path = Path(r"equalprop/captura_socios.py")
text = path.read_text(encoding="utf-8")
old = """        linhas = []
        for s in qsa:
            partes = []
            if s.get("nome"):
                partes.append(s["nome"])
            if s.get("qual"):
                partes.append(s["qual"])
            rep = []
            if s.get("nome_rep_legal"):
                rep.append(s["nome_rep_legal"])
            if s.get("qual_rep_legal"):
                rep.append(s["qual_rep_legal"])
            if rep:
                partes.append("Representante: " + " - ".join(rep))
            if partes:
                linhas.append(" - ".join(partes))
        return linhas or None"""
new = """        linhas = []
        for socio in qsa:
            nome = socio.get("nome_socio") or socio.get("nome")
            qualificacao = socio.get("qualificacao_socio") or socio.get("qual")
            campos = [valor for valor in (nome, qualificacao) if valor]
            if campos:
                linhas.append(", ".join(campos))
        return linhas or None"""
normalized = text.replace("\r\n", "\n")
if old not in normalized:
    raise SystemExit("Trecho original nao encontrado")
normalized = normalized.replace(old, new, 1)
updated = normalized.replace("\n", "\r\n")
path.write_text(updated, encoding="utf-8")
