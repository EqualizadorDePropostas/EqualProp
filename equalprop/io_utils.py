import os
import re
import io
import pandas as pd
from PyPDF2 import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


def sanitize_filename(filename: str) -> str:
    """Remove caracteres inválidos de nomes de arquivo"""
    import unicodedata
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    filename = re.sub(r'[<>:\"/\\|?*:]', '', filename)
    filename = re.sub(r'\s+', ' ', filename)
    return filename.strip()


def excel_to_pdf(excel_path: str, pdf_path: str) -> bool:
    """Converte Excel para PDF simples (texto tabular)"""
    try:
        df = pd.read_excel(excel_path)
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)

        text = df.to_string()
        text_lines = text.split('\n')
        y_position = 750

        for line in text_lines:
            if y_position < 40:
                can.showPage()
                y_position = 750
            can.drawString(30, y_position, line)
            y_position -= 12

        can.save()
        packet.seek(0)
        new_pdf = PdfReader(packet)

        with open(pdf_path, "wb") as f:
            output = PdfWriter()
            for page in new_pdf.pages:
                output.add_page(page)
            output.write(f)

        return True
    except Exception as e:
        print(f"[ERRO] Erro ao converter {excel_path} para PDF: {e}")
        return False


def process_files(file_paths, temp_dir):
    """Processa arquivos selecionados; converte Excel em PDF e copia PDFs"""
    pdf_files = []

    for file_path in file_paths:
        file_name = os.path.basename(file_path)

        if not file_name.lower().endswith(('.pdf', '.xlsx', '.xls')):
            print(f"[AVISO] Arquivo {file_name} rejeitado. Somente PDF ou Excel são aceitos.")
            continue

        if file_name.lower().endswith(('.xlsx', '.xls')):
            pdf_path = os.path.join(temp_dir, f"{os.path.splitext(file_name)[0]}.pdf")
            if excel_to_pdf(file_path, pdf_path):
                pdf_files.append(pdf_path)
                print(f"[OK] Arquivo {file_name} convertido para PDF com sucesso.")
        else:
            pdf_path = os.path.join(temp_dir, file_name)
            with open(file_path, 'rb') as src_file:
                file_content = src_file.read()
            with open(pdf_path, 'wb') as dst_file:
                dst_file.write(file_content)
            pdf_files.append(pdf_path)
            print(f"[OK] Arquivo {file_name} aceito.")

    return pdf_files
