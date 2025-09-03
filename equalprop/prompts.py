# Prompts estáticos usados nas chamadas ao modelo

pdcs_prompt = """
Extraia a descrição e a quantidade demandada de cada Produto Demandado (PDC) relacionado na Request For Proposal (RFP)
Atribua os codigos PDC1, PDC2, etc a cada um dos produtos demandados
As informações de cada PDC deve obedecer rigorosamente o formato abaixo

IMPORTANTE:
- Sua resposta deve ser APENAS o JSON válido, sem comentários adicionais
- Nunca use markdown (```json```) ou texto explicativo
- Se algum campo estiver ausente, use null conforme o schema

{
  "title": "Produto Demandado (PDC)",
  "description": "Um objeto contendo código e especificações técnicas variáveis",
  "type": "object",
  "properties": {
    "codigo": {
      "type": "string",
      "description": "Código identificador do produto. Ex: PDC1, PDC2"
    },
    "especificacoes_tecnicas": {
      "type": "object",
      "description": "Dicionário de especificações técnicas (a chave é o nome da especificação)",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "valor": {
            "type": ["string", "number"],
            "description": "Valor da especificação técnica (pode ser texto ou número)"
          },
          "unidade": {
            "type": "string",
            "description": "Unidade de medida da especificação (preencher com null se não existir)",
            "default": null
          }
        },
        "required": ["valor"],
        "additionalProperties": false
      }
    },
    "quantidade_demandada": {
      "type": "object",
      "description": "Quantidade demandada do produto",
      "properties": {
        "valor": {
          "type": ["string", "number"],
          "description": "Quantidade demandada ou solicitada (pode ser texto ou número)"
        },
        "unidade": {
          "type": "string",
          "description": "Unidade da quantidade demandada (preencher com null se não existir)",
          "default": null
        }
      },
      "required": ["valor"],
      "additionalProperties": false
    }
  },
  "required": ["codigo", "quantidade_demandada", "especificacoes_tecnicas"],
  "additionalProperties": false
}
"""

extraction_prompt = """
Extraia da proposta comercial as seguintes informacoes:
- informacoes de header (nome da empresa, telefone, etc)
- informações sobre os Produtos Oferecidos (POPs) associados aos Produtos Demandados (PDCs)

Forneça a resposta exatamente no formato json abaixo:

{
  "proposta": {
    "header": {
      "empresa": {"type": "str", "description": "Nome da empresa fornecedora"},
      "representante": {"type": "str", "description": "Nome do representante da empresa fornecedora"},
      "telefone": {"type": "str", "description": "telefone do representante"},
      "email": {"type": "str", "description": "email do representante"}
    },
    "pops": [
      {
        "codigo_pdc": {"type": "str", "description": "Código do PDC associado"},
        "quantidade": {"type": "float", "description": "Quantidade do Produto Oferecido"},
        "preco_unitario": {"type": "float", "description": "Preço unitário do Produto Oferecido"},
        "semelhanca": {
          "type": "str",
          "description": "Expressa em porcentagem (Exemplo: \"40%\", \"66%\"). Calculada pela fórmula 100*X/Y onde :\n                          - Y é a quantidade total de Especificações Técnicas do Produto Demandado\n                          - X é a quantidade de Especificações Tecnicas do Produto Oferecido que são iguais ou equivalentes às Especificações Técnicas do Produto Demandado.\n                          A Especificação Técnica \"quantidade\" também deve ser considerada na determinação da Semelhança\n                          Para Especificações Técnicas numéricas considere iguais valores cuja diferença <3%"
        },
        "descricao": {"type": "str", "description": "Descrição do Produto Oferecido"},
        "num_ordem": {"type": "int", "description": "Posição do produto na proposta"},
        "reasoning": {"type": "str", "description": "Raciocínio da extração"}
      }
    ]
  }
}
"""
