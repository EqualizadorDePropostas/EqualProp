import os
import sys
import google.generativeai as genai


def setup_gemini_client():
    """Initialize Gemini client"""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[ERRO] GOOGLE_API_KEY não encontrada nas variáveis de ambiente")
        print("Configure a variável de ambiente:")
        print("   Linux/Mac: export GOOGLE_API_KEY='sua_chave_aqui'")
        print("   Windows  : set GOOGLE_API_KEY=sua_chave_aqui")
        sys.exit(1)
    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-2.5-pro')
    except Exception as e:
        print(f"[ERRO] Falha ao configurar Gemini: {e}")
        sys.exit(1)


def build_gen_config(temperature: float = 0.0, response_mime_type: str = "application/json"):
    return genai.types.GenerationConfig(
        temperature=temperature,
        response_mime_type=response_mime_type,
    )
