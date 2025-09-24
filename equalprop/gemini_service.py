import os
import json
import time
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential


def upload_pdfs_to_gemini(pdf_files):
    """Faz upload de PDFs para o Gemini"""
    uploaded_files = []
    for pdf_path in pdf_files:
        try:
            file_name = os.path.basename(pdf_path)
            print(f"[INFO] Enviando: {file_name}...")
            uploaded_file = genai.upload_file(
                path=pdf_path,
                mime_type='application/pdf'
            )
            uploaded_files.append(uploaded_file)
            print(f"[OK] {file_name} enviado! (ID: {uploaded_file.name})")
        except Exception as e:
            print(f"[ERRO] Erro ao enviar {pdf_path}: {str(e)}")
    return uploaded_files


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def process_proposal_with_retry(model, rfp_json, proposal_file, prompt, gen_config):
    """Processa proposta com retry"""
    try:
        rfp_json_str = json.dumps(rfp_json)
        response = model.generate_content(
            contents=[rfp_json_str, proposal_file, prompt],
            generation_config=gen_config,
            request_options={"timeout": 180}
        )
        return response
    except Exception as e:
        print(f"[ERRO] {str(e)}")
        raise


def process_all_proposals(model, rfp_json, proposal_files, proposal_paths, prompt, gen_config):
    """Processa todas as propostas"""
    results = {}
    for proposal_file, proposal_path in zip(proposal_files, proposal_paths):
        if proposal_file is None:
            continue
        print(f"\n[INFO] Processando: {os.path.basename(proposal_path)}")
        try:
            start_time = time.time()
            response = process_proposal_with_retry(model, rfp_json, proposal_file, prompt, gen_config)
            results[proposal_path] = response.text
            print(f"[OK] Concluído em {time.time() - start_time:.2f}s")
        except Exception as e:
            print(f"[ERRO] Falha ao processar {proposal_path}: {str(e)}")
            results[proposal_path] = None
    return results
