import os
import json
import tempfile
import streamlit as st

from equalprop.io_utils import sanitize_filename, process_files
from equalprop.prompts import pdcs_prompt, extraction_prompt
from equalprop.gemini_service import upload_pdfs_to_gemini, process_all_proposals
from equalprop.reports.suppliers import generate_suppliers_report
from equalprop.reports.globals import generate_global_report
from equalprop.reports.comparison import generate_comparison_report
from equalprop.reports.consolidate import consolidate_reports


def main(model, gen_config):
    st.set_page_config(page_title="Processador de Propostas", page_icon="🧾", layout="wide")
    st.title("🧾 Processador de Propostas Comerciais")
    st.write("Faça upload dos arquivos RFP/RFQ e das propostas para gerar relatórios automatizados.")

    # Upload de arquivos
    st.header("1. Upload de Arquivos")
    rfp_files = st.file_uploader(
        "Selecione o arquivo RFP/RFQ (PDF ou Excel)",
        type=["pdf", "xlsx", "xls"],
        accept_multiple_files=False,
        key="rfp_uploader"
    )

    proposal_files = st.file_uploader(
        "Selecione os arquivos de Proposta (PDF ou Excel)",
        type=["pdf", "xlsx", "xls"],
        accept_multiple_files=True,
        key="proposal_uploader"
    )

    if st.button("Processar Arquivos") and rfp_files and proposal_files:
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                status_text.text("Processando arquivos...")

                # Processar RFP - ler conteúdo e salvar
                rfp_paths = []
                if rfp_files:
                    try:
                        safe_name = sanitize_filename(rfp_files.name)
                        rfp_path = os.path.join(temp_dir, safe_name)
                        file_content = rfp_files.getvalue()
                        with open(rfp_path, "wb") as f:
                            f.write(file_content)
                        rfp_paths.append(rfp_path)
                        st.success(f"OK. RFP salvo: {safe_name}")
                    except Exception as e:
                        st.error(f"Erro ao salvar RFP: {str(e)}")
                        return

                # Processar propostas - ler conteúdo e salvar
                proposal_paths = []
                if proposal_files:
                    for proposal_file in proposal_files:
                        try:
                            safe_name = sanitize_filename(proposal_file.name)
                            proposal_path = os.path.join(temp_dir, safe_name)
                            file_content = proposal_file.getvalue()
                            with open(proposal_path, "wb") as f:
                                f.write(file_content)
                            proposal_paths.append(proposal_path)
                            st.success(f"OK. Proposta salva: {safe_name}")
                        except Exception as e:
                            st.error(f"Erro ao salvar proposta {proposal_file.name}: {str(e)}")
                            continue

                progress_bar.progress(20)

                if not rfp_paths:
                    st.error("Nenhum arquivo RFP foi processado com sucesso.")
                    return

                if not proposal_paths:
                    st.error("Nenhum arquivo de proposta foi processado com sucesso.")
                    return

                # Processar arquivos (converter Excel para PDF se necessário)
                status_text.text("Convertendo arquivos para PDF...")
                rfp_pdfs = process_files(rfp_paths, temp_dir)
                proposal_pdfs = process_files(proposal_paths, temp_dir)

                if not rfp_pdfs or not proposal_pdfs:
                    st.error("Falha ao processar arquivos. Verifique os formatos.")
                    return

                status_text.text("Enviando arquivos para o Gemini...")
                progress_bar.progress(40)

                # Upload para Gemini
                rfp_gemini_files = upload_pdfs_to_gemini(rfp_pdfs)
                proposal_gemini_files = upload_pdfs_to_gemini(proposal_pdfs)

                if not rfp_gemini_files:
                    st.error("Falha no upload do RFP para o Gemini.")
                    return

                if not proposal_gemini_files:
                    st.error("Falha no upload das propostas para o Gemini.")
                    return

                status_text.text("Extraindo PDCs do RFP...")
                progress_bar.progress(60)

                # Extrair PDCs
                try:
                    response = model.generate_content(
                        contents=[pdcs_prompt, rfp_gemini_files[0]],
                        generation_config=gen_config
                    )
                    pdc_descriptions = json.loads(response.text)
                    st.success("OK. PDCs extraídos com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao processar RFP: {str(e)}")
                    return

                status_text.text("Processando propostas comerciais...")
                progress_bar.progress(80)

                # Processar propostas
                raw_results = process_all_proposals(
                    model, pdc_descriptions, proposal_gemini_files,
                    proposal_pdfs, extraction_prompt, gen_config
                )

                status_text.text("Gerando relatórios finais...")
                progress_bar.progress(95)

                # Gerar relatórios
                try:
                    suppliers_csv = generate_suppliers_report(raw_results)
                    global_csv = generate_global_report(pdc_descriptions, raw_results)
                    comparison_csv = generate_comparison_report(pdc_descriptions, raw_results)
                    relatorio_final_csv, relatorio_final_xlsx = consolidate_reports()
                except Exception as e:
                    st.error(f"Erro ao gerar relatórios: {str(e)}")
                    return

                progress_bar.progress(100)
                status_text.text("Processamento concluído!")

                # Botões de download
                st.success("OK. Processamento concluído com sucesso!")

                col1, col2 = st.columns(2)
                with col1:
                    try:
                        with open(relatorio_final_csv, "rb") as file:
                            st.download_button(
                                label="⬇️ Baixar Relatório CSV",
                                data=file,
                                file_name="relatorio_consolidado.csv",
                                mime="text/csv"
                            )
                    except Exception as e:
                        st.error(f"Erro ao carregar CSV: {str(e)}")

                with col2:
                    try:
                        with open(relatorio_final_xlsx, "rb") as file:
                            st.download_button(
                                label="⬇️ Baixar Relatório Excel",
                                data=file,
                                file_name="relatorio_consolidado.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    except Exception as e:
                        st.error(f"Erro ao carregar Excel: {str(e)}")

                # Mostrar resumo dos relatórios gerados
                st.info("📄 Relatórios gerados:")
                st.write(f"- Tabela 1: {suppliers_csv} - Informações dos fornecedores")
                st.write(f"- Tabela 2: {global_csv} - Valores globais por produto")
                st.write(f"- Tabela 3: {comparison_csv} - Comparação detalhada de produtos")
                st.write(f"- Consolidado: {relatorio_final_csv} e {relatorio_final_xlsx}")

        except Exception as e:
            st.error(f"Erro durante o processamento: {str(e)}")
            st.exception(e)
    else:
        if not rfp_files:
            st.warning("Selecione um arquivo RFP/RFQ")
        if not proposal_files:
            st.warning("Selecione pelo menos uma proposta")
