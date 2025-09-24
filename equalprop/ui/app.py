# equalprop/ui/app.py

import os
import json
import tempfile
import streamlit as st

from equalprop.io_utils import sanitize_filename, process_files
from equalprop.prompts import rfp_prompt, extraction_prompt_with_rules, padroniza_condicomer_prompt
from equalprop.gemini_service import upload_pdfs_to_gemini, process_all_proposals
from equalprop.reports.suppliers import generate_suppliers_report
from equalprop.reports.globals import generate_preco_report
from equalprop.reports.comparison import generate_comparison_report
from equalprop.reports.consolidate import consolidate_reports


# =========================
# ------ STYLES/CSS -------
# =========================
CSS = """
<style>
:root { --black:#000; --muted:#6b7280; --blue:#1e40ff; --red:#dc2626; --green:#16a34a; }
html, body, [class^="css"] { color: var(--black) !important; }
.block-container { padding-top: 0.75rem; padding-bottom: 0.75rem; }

/* Tipografia exigida */
h1.app-title { font-size:36px !important; font-weight:800 !important; margin:0 0 4px 0 !important; }
p.subtitle-18b { font-size:18px !important; font-weight:700 !important; margin:0 0 12px 0 !important; }
p.body-18 { font-size:18px !important; font-weight:400 !important; margin:0 0 12px 0 !important; }

/* Linhas compactas */
.row { display:flex; align-items:center; gap:10px; margin:6px 0; }
.row .label { font-size:18px; white-space:nowrap; }
.row .value { font-size:18px; }
.row .value.muted { color: var(--muted) !important; }

/* Uploader: esconder dropzone e deixar só "Browse files" pequeno */
div[data-testid="stFileUploader"] section { padding:0 !important; }
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]{
  padding:0 !important; border:none !important; background:transparent !important; min-height:auto !important;
}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > div:first-child { display:none !important; }
div[data-testid="stFileUploader"] small { display:none !important; }
.stFileUploader label { font-size:18px !important; }

/* Botões compactos */
.stButton > button { padding:6px 14px !important; border-radius:6px !important; font-size:18px !important; }
.btn-danger { border:1px solid var(--red) !important; }
.btn-danger:before { content:"\\1F534  "; }  /* bolinha vermelha */
.btn-download:before { content:"\\2B07\\FE0F  "; } /* seta para baixo */

/* Spinner inline */
.spinner-wrap { display:flex; align-items:center; gap:10px; margin-top: 6px; }
.spinner {
  width:24px; height:24px; border:3px solid #e5e7eb; border-top-color:#9ca3af;
  border-radius:50%; animation:spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Barra de progresso AZUL custom */
.progress-wrap { width:100%; height:10px; background:#e5e7eb; border-radius:6px; overflow:hidden; margin-top:6px; }
.progress-fill { height:100%; background: var(--blue); width:0%; transition:width .2s ease; }
</style>
"""

# =========================
# ------ STATE/UTIL -------
# =========================
def _ensure_state():
    st.session_state.setdefault("stage", "idle")  # idle | selected | running | done
    st.session_state.setdefault("rfp_file", None)
    st.session_state.setdefault("proposal_files", [])
    st.session_state.setdefault("report_xlsx", None)

def _reset_all():
    for k in list(st.session_state.keys()):
        if k.startswith(("_", "FormSubmitter")):
            continue
        del st.session_state[k]
    st.session_state["stage"] = "idle"
    st.rerun()

def _header():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown('<h1 class="app-title">Equalizador de Propostas</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle-18b">Perla Cabral Ferreira</p>', unsafe_allow_html=True)
    st.markdown(
#        '<p class="body-18">Clique nos botôes abaixo para subir a requisição de compra e as respectivas propostas '
#        'comercias. O sistema vai usar IA para gerar um relatório comparativo dos fornecedores.</p>',
         '<p class="body-18">Clique nos botões abaixo para subir a requisição de compra e as respectivas propostas comerciais.<br/>O sistema vai usar IA para gerar um relatório comparativo dos fornecedores.</p>',
        unsafe_allow_html=True
    )

def _uploader_line(label_text, key, multiple=False):
    c1, c2 = st.columns([0.75, 0.25], vertical_alignment="center")
    with c1:
        st.markdown(f'<div class="row"><span class="label">{label_text} :</span></div>', unsafe_allow_html=True)
    with c2:
        st.file_uploader(label_text, type=["pdf"], accept_multiple_files=multiple, key=key, label_visibility="collapsed")

def _selected_line(label_text, value_text, clear_key):
    c1, c2 = st.columns([0.92, 0.08], vertical_alignment="center")
    with c1:
        st.markdown(
            f'<div class="row"><span class="label">{label_text} :</span>'
            f'<span class="value">{value_text}</span></div>',
            unsafe_allow_html=True
        )
    with c2:
        if st.button("?", key=clear_key):
            if clear_key == "clear_rfp":
                st.session_state["rfp_file"] = None
            else:
                st.session_state["proposal_files"] = []
            st.session_state["stage"] = "idle"
            st.rerun()

def _selected_line_muted(label_text, value_text):
    st.markdown(
        f'<div class="row"><span class="label">{label_text} :</span>'
        f'<span class="value muted">{value_text}</span></div>',
        unsafe_allow_html=True
    )

def _join_names(files):
    if not files:
        return ""
    if isinstance(files, list):
        return "; ".join([f.name for f in files])
    return files.name

def _dangerize(button_label, key, width=True):
    clicked = st.button(button_label, key=key, use_container_width=width)
    st.markdown("""
    <script>
    const btns = window.parent.document.querySelectorAll('button');
    btns.forEach(b=>{ if (b.innerText.trim().startsWith('Interromper')) b.classList.add('btn-danger'); });
    </script>
    """, unsafe_allow_html=True)
    return clicked

def _render_blue_progress(ph, pct: int):
    pct = max(0, min(int(pct), 100))
    ph.markdown(
        f'<div class="progress-wrap"><div class="progress-fill" style="width:{pct}%"></div></div>',
        unsafe_allow_html=True
    )

def _merge_results(acc, part):
    """Tenta mesclar resultados parciais em um único objeto."""
    if acc is None:
        return part
    try:
        if isinstance(acc, dict) and isinstance(part, dict):
            acc.update(part)
            return acc
        if isinstance(acc, list) and isinstance(part, list):
            acc.extend(part)
            return acc
    except:
        pass
    return part  # fallback simples


# =========================
# --------- MAIN ----------
# =========================
def main(model, gen_config):
    st.set_page_config(page_title="Equalizador de Propostas", page_icon="??", layout="wide")
    _ensure_state()
    _header()

    # ---------- TELA 1 (IDLE) ----------
    if st.session_state["stage"] == "idle":
        _uploader_line("Requisição de compra (um PDF)", key="rfp_upl", multiple=False)
        _uploader_line("Propostas comerciais (de um a vinte PDFs)", key="prop_upl", multiple=True)

        rfp = st.session_state.get("rfp_upl")
        props = st.session_state.get("prop_upl", [])
        if rfp and props:
            st.session_state["rfp_file"] = rfp
            st.session_state["proposal_files"] = props
            st.session_state["stage"] = "selected"
            st.rerun()
        return

    # ---------- TELA 2 (SELECTED) ----------
    if st.session_state["stage"] == "selected":
        _selected_line("Requisição de compra (um PDF)", _join_names(st.session_state["rfp_file"]), "clear_rfp")
        _selected_line("Propostas comerciais (de um a vinte PDFs)", _join_names(st.session_state["proposal_files"]), "clear_props")

        c1, c2 = st.columns([0.18, 0.18])
        with c1:
            if st.button("Gerar relatório", key="btn_run", use_container_width=True):
                st.session_state["stage"] = "running"
                st.rerun()
        with c2:
            if _dangerize("Interromper", key="btn_abort_sel"):
                _reset_all()
        return

    # ---------- TELA 3 (RUNNING) ----------
    if st.session_state["stage"] == "running":
        # Linhas com nomes (cinza)
        _selected_line_muted("Requisição de compra (um PDF)", _join_names(st.session_state["rfp_file"]))
        _selected_line_muted("Propostas comerciais (de um a vinte PDFs)", _join_names(st.session_state["proposal_files"]))

        # Linha "Aguarde..." + Interromper
        c1, c2 = st.columns([0.7, 0.3], vertical_alignment="center")
        with c1:
            st.markdown('<div class="spinner-wrap"><div class="spinner"></div><div class="body-18">Aguarde...</div></div>',
                        unsafe_allow_html=True)
        with c2:
            if _dangerize("Interromper", key="btn_abort_run"):
                _reset_all()

        # Placeholders visíveis (linha de status + barra azul)
        status_ph = st.empty()      # linha da tarefa atual
        bar_ph = st.empty()         # barra de progresso AZUL

        # ========= PIPELINE =========
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # 1) Salvar arquivos
                status_ph.markdown('<p class="body-18">Processando arquivos...</p>', unsafe_allow_html=True)
                _render_blue_progress(bar_ph, 5)

                rfp = st.session_state["rfp_file"]
                rfp_paths = []
                safe_name = sanitize_filename(rfp.name)
                rfp_path = os.path.join(temp_dir, safe_name)
                with open(rfp_path, "wb") as f:
                    f.write(rfp.getvalue())
                rfp_paths.append(rfp_path)

                proposal_paths = []
                for p in st.session_state["proposal_files"]:
                    safe = sanitize_filename(p.name)
                    p_path = os.path.join(temp_dir, safe)
                    with open(p_path, "wb") as f:
                        f.write(p.getvalue())
                    proposal_paths.append(p_path)

                # 2) Converter p/ PDF
                status_ph.markdown('<p class="body-18">Convertendo arquivos para PDF...</p>', unsafe_allow_html=True)
                _render_blue_progress(bar_ph, 15)
                rfp_pdfs = process_files(rfp_paths, temp_dir)
                proposal_pdfs = process_files(proposal_paths, temp_dir)
                if not rfp_pdfs or not proposal_pdfs:
                    status_ph.markdown('<p class="body-18">Erro: falha ao processar arquivos.</p>', unsafe_allow_html=True)
                    _render_blue_progress(bar_ph, 0)
                    return

                # 3) Upload Gemini
                status_ph.markdown('<p class="body-18">Subindo arquivos para a Gemini...</p>', unsafe_allow_html=True)
                _render_blue_progress(bar_ph, 35)
                rfp_gemini_files = upload_pdfs_to_gemini(rfp_pdfs)
                proposal_gemini_files = upload_pdfs_to_gemini(proposal_pdfs)
                if not rfp_gemini_files or not proposal_gemini_files:
                    status_ph.markdown('<p class="body-18">Erro: falha no upload para a Gemini.</p>', unsafe_allow_html=True)
                    _render_blue_progress(bar_ph, 0)
                    return

                # 4) Extrair PDCs e Cabeçalho da RFP
                status_ph.markdown('<p class="body-18">Analisando a requisição de compra...</p>', unsafe_allow_html=True)
                _render_blue_progress(bar_ph, 55)

                response = model.generate_content(
                    contents=[rfp_prompt, rfp_gemini_files[0]],
                    generation_config=gen_config
                )

                # Processa a resposta mantendo compatibilidade
                rfp_json = json.loads(response.text)

                # Extrai as informações separadamente
                # rfp_json = rfp_json["rfp_json"]  # Novo: informações do cabeçalho
                # rfp_json = rfp_json["produtos_demandados"]  # Mantém compatibilidade: lista de PDCs

                # 5) Processar propostas **uma por vez** mostrando o nome do PDF
                n = len(proposal_pdfs)
                aggregated_results = None
                for i, (gfile, pdf_path) in enumerate(zip(proposal_gemini_files, proposal_pdfs), start=1):
                    fname = os.path.basename(pdf_path)
                    status_ph.markdown(
                        f'<p class="body-18">Processando proposta: <span class="value">{fname}</span></p>',
                        unsafe_allow_html=True
                    )
                    # Progresso dentro do intervalo 60?90
                    pct = 60 + int(30 * (i-1) / max(n, 1))
                    _render_blue_progress(bar_ph, pct)

                    partial = process_all_proposals(
                        model,
                        rfp_json,
                        [gfile],          # uma proposta por vez
                        [pdf_path],
                        extraction_prompt_with_rules,
                        gen_config
                    )
                    aggregated_results = _merge_results(aggregated_results, partial)

                proposta_json = aggregated_results


                # 6) Padronizar condições comerciais
                status_ph.markdown('<p class="body-18">Padronizando condições comerciais...</p>', unsafe_allow_html=True)
                _render_blue_progress(bar_ph, 90)

                condicomer_bruto = None
                try:
                    response = model.generate_content(
                        contents=[padroniza_condicomer_prompt, json.dumps(proposta_json, ensure_ascii=False)],
                        generation_config=gen_config
                    )
                    condicomer_bruto = response.text if response and hasattr(response, "text") else None
                    # Verifica se a resposta foi bem-sucedida e tem conteúdo
                    if response and hasattr(response, 'text') and response.text:
                        condicomer_padronizado = json.loads(response.text)
                    else:
                        raise ValueError("Resposta vazia ou inválida do modelo")
                        
                except json.JSONDecodeError as e:
                    print(f"Erro ao decodificar JSON: {e}")
                    print(f"Conteúdo recebido: {response.text if response else 'Nenhuma resposta'}")
                    condicomer_padronizado = {}  # Ou algum valor padrão
                except Exception as e:
                    print(f"Erro inesperado: {e}")
                    condicomer_padronizado = {}

                # (fallback removido por solicitação)

                # 7) Gerar relatório final (EXCEL apenas)
                status_ph.markdown('<p class="body-18">Gerando relatório final (Excel)...</p>', unsafe_allow_html=True)
                _render_blue_progress(bar_ph, 92)
                # Proteger o diretório de trabalho do Streamlit contra mudanças internas
                cwd_before = os.getcwd()
                try:
                    _, relatorio_final_xlsx = consolidate_reports(rfp_json, proposta_json, condicomer_padronizado)
                finally:
                    try:
                        os.chdir(cwd_before)
                    except Exception:
                        pass

                st.session_state["report_xlsx"] = relatorio_final_xlsx

                status_ph.markdown('<p class="body-18">Concluído.</p>', unsafe_allow_html=True)
                _render_blue_progress(bar_ph, 100)

                st.session_state["stage"] = "done"
                st.rerun()

        except Exception as e:
            status_ph.markdown(f'<p class="body-18">Erro: {e}</p>', unsafe_allow_html=True)
            _render_blue_progress(bar_ph, 0)
        return

    # ---------- TELA 4 (DONE) ----------
    if st.session_state["stage"] == "done":
        _selected_line_muted("Requisição de compra (um PDF)", _join_names(st.session_state["rfp_file"]))
        _selected_line_muted("Propostas comerciais (de um a vinte PDFs)", _join_names(st.session_state["proposal_files"]))

        xlsx_path = st.session_state.get("report_xlsx")
        if not xlsx_path or not os.path.exists(xlsx_path):
            _reset_all()
            return

        c1, c2 = st.columns([0.22, 0.18])
        with c1:
            with open(xlsx_path, "rb") as f:
                downloaded = st.download_button(
                    "Baixar relatório",
                    data=f.read(),
                    file_name="relatorio_consolidado.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_dl",
                    use_container_width=True
                )
            st.markdown("""
            <script>
            const btns = window.parent.document.querySelectorAll('button');
            btns.forEach(b=>{ if (b.innerText.trim().startsWith('Baixar relatório')) b.classList.add('btn-download'); });
            </script>
            """, unsafe_allow_html=True)
            if downloaded:
                _reset_all()
        with c2:
            if _dangerize("Interromper", key="btn_abort_done"):
                _reset_all()
        return

