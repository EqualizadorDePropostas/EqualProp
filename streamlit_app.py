import os
import sys
import subprocess

from equalprop.config import setup_gemini_client, build_gen_config
from equalprop.ui.app import main


def _running_inside_streamlit() -> bool:
    """Best-effort check to determine if Streamlit is running this script."""
    try:
        # Streamlit >= 1.20 provides this API. Returns None when not running via Streamlit.
        from streamlit.runtime.scriptrunner import get_script_run_ctx  # type: ignore

        return get_script_run_ctx() is not None
    except Exception:
        # Fallback heuristics via env vars that are typically present when Streamlit runs
        return any(
            os.environ.get(var)
            for var in (
                "STREAMLIT_SERVER_PORT",
                "STREAMLIT_SERVER_ADDRESS",
                "STREAMLIT_RUNTIME",
            )
        )


if __name__ == "__main__":
    # If executed directly (e.g., VS Code "Run Python File"), spawn `streamlit run`.
    if not _running_inside_streamlit() and not os.environ.get("EQUALPROP_LAUNCHED_BY_WRAPPER"):
        cmd = [sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)]
        env = os.environ.copy()
        env["EQUALPROP_LAUNCHED_BY_WRAPPER"] = "1"
        print("[INFO] Iniciando Streamlit...", flush=True)
        try:
            subprocess.run(cmd, check=False, env=env)
        except FileNotFoundError:
            print(
                "[ERRO] Nao foi possivel encontrar o modulo 'streamlit'.\n"
                "Instale-o com: pip install streamlit",
                flush=True,
            )
        sys.exit(0)

    # Running under Streamlit: configure model and start the UI.
    print("[INFO] Configurando modelo Gemini...")
    model = setup_gemini_client()
    gen_config = build_gen_config(temperature=0.0, response_mime_type="application/json")
    print("[OK] Modelo configurado!\n")
    main(model, gen_config)
