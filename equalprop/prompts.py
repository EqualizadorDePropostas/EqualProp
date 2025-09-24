# import json; print(json.dumps(dados_completos, ensure_ascii=False, indent=2))

# Prompts estáticos usados nas chamadas ao modelo

rfp_prompt = """
Extraia as seguintes informações da Request For Proposal (RFP):

1. Informações do Cabeçalho da RFP
2. Descrição e quantidade demandada de cada Produto Demandado (PDC). Atribua os codigos PDC1, PDC2, etc a cada um dos produtos demandados.

IMPORTANTE:
- Sua resposta deve ser APENAS o JSON válido, sem comentários adicionais
- Nunca use markdown (```json```) ou texto explicativo
- Se algum campo estiver ausente, use null conforme o schema

Siga rigorosamente o formato JSON abaixo:

{
  "rfp_json": {
    "type": "object",
    "description": "Request For Proposal completa",
    "properties": {
      "header": {
        "type": "object",
        "description": "Cabeçalho da RFP",
        "properties": {
          "Obra": {
            "type": "string",
            "description": "Nome/tipo da obra para a qual estes produtos serão destinados"
          },
          "Solicitante": {
            "type": "string", 
            "description": "Nome do funcionário que solicitou a compra do produto"
          },
          "Data da Requisição": {
            "type": "string",
            "format": "date",
            "description": "Data em que a requisição foi feita (formato YYYY-MM-DD)"
          },
          "Data da Necessidade": {
            "type": "string",
            "format": "date", 
            "description": "Data limite em que os produtos devem ser recebidos (formato YYYY-MM-DD)"
          }
          "Comprador": {
            "type": "string",
            "description": "Nome do comprador responsável pela compra"
          }
        },
        "additionalProperties": false
      },
      "produtos_demandados": {
        "type": "array",
        "description": "Lista de produtos demandados",
        "items": {
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
      }
    },
    "required": ["header", "produtos_demandados"],
    "additionalProperties": false
  }
}
"""


extraction_prompt = """
Execute as seguintes tarefas :
1) Extraia informacoes do cabeclho da proposta (nome da empresa, telefone, etc)
2) Associa cada Produto Demandado (PDC) com um dos Ptrodutos Oferecidos (POP) na proposta
3) Extraia especificações técnicas de cada Produto Oferecido (POP) que foi associado a um dos Produtos Demandados (PDC)
4) Extraia informações sobre condições comerciais descritas na proposta (prazo de validade, custo de frete, etc)

Siga os passos abaixo para fazer a associação entre Produtos Demandados (PDCs) e Produtos Oferecidos (POPs) na proposta :
- Tome um Produto Demandado de cada vez
- Calcule a "Semelhança" do Produto Demandado com cada um dos Produtos Oferecidos na proposta (veja mais adiante a definição de Semelhança)
- Associe este Produto Demandado ao Produto Oferecido com maior Semelhança
- Não é proibido que um Produto Oferecido seja associado a mais de um Produto Demandado
- Caso mais de um Produto Oferecido tenham Semelhanças igualmente altas com determinado Produto Demandado, associar àquele cuja "quantidade" seja igual à do Produto Demandado. Se ainda assim o empate persistir associe aleatoriamente a qualquer um deles
- Para que haja associação o valor da Semelhança deve ser >39%
- Se este mínimo não for alcançado com nenhum Produto Oferecido, não associe nenhum Produto Oferecido a este Produto Demandado e preencha com "null" os campos respectivos (veja estrutura de dados mais abaixo)
- Se a proposta não tiver informação sobre nenhum Produto Oferecido, não associe nenhum Produto Oferecido a este Produto Demandado e preencha com "null" os campos respectivos (veja estrutura de dados mais abaixo)

Forneça a resposta exatamente no formato json abaixo:

{
  "proposta": {
    "header": {
      "empresa": {"type": "str", "description": "Nome da empresa fornecedora"},
      "cnpj": {"type": "str", "description": CNPJ da empresa fornecedora"},
      "representante": {"type": "str", "description": "Nome do representante da empresa fornecedora"},
      "tel": {"type": "str", "description": "telefone da empresa fornecedora"},
      "cel": {"type": "str", "description": "telefone do representante da empresa fornecedora"},
      "email": {"type": "str", "description": "email do representante da empresa fornecedora"}
    },
    "pops": [
      {
        "codigo_pdc": {"type": "str", "description": "Código do PDC associado"},
        "quantidade": {"type": "float", "description": "Quantidade do Produto Oferecido"},
        "preco_unitario": {"type": "float", "description": "Preço unitário do Produto Oferecido"},
        "semelhanca": {
          "type": "str",
          "description": "Expressa em porcentagem (Exemplo: \"40%\", \"66%\"). Calculada pela fórmula 100*X/Y onde :\n
          - Y é a quantidade total de Especificações Técnicas do Produto Demandado\n
          - X é a quantidade de Especificações Tecnicas do Produto Oferecido que são iguais ou equivalentes às Especificações Técnicas do Produto Demandado.\n
          A Especificação Técnica \"quantidade\" também deve ser considerada na determinação da Semelhança\n
          Para Especificações Técnicas numéricas considere iguais valores cuja diferença <3%"
        },
        "descricao": {"type": "str", "description": "Descrição do Produto Oferecido"},
        "num_ordem": {"type": "int", "description": "Posição do produto na proposta"},
        "reasoning": {"type": "str", "description": "Raciocínio da extração"}
      }
    ],
    "condicoes_comerciais": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "chave": {
            "type": "string",
            "description": "Termo que identifica a condição comercial (ex: validade, condições de pagamento, frete, etc.)"
          },
          "valor": {
            "type": "string",
            "description": "Valor ou descrição correspondente à condição comercial"
          }
        },
        "required": ["chave", "valor"]
      }
    }    
  }
}
"""

extraction_prompt_rules = """
IMPORTANTE:
- Sua resposta deve ser APENAS o JSON valido, sem comentarios adicionais
- Nunca use markdown (```json```) ou texto explicativo
- Se algum campo estiver ausente, use null conforme o schema
"""

extraction_prompt_with_rules = extraction_prompt_rules + "\n" + extraction_prompt


padroniza_condicomer_prompt = """
Você receberá várias propostas comerciais (como JSON). Sua tarefa é:

Descobrir todas as condições comerciais existentes em qualquer proposta.
Unificar nomes equivalentes (ex.: “prazo de validade”, “validade da proposta” → “Validade da proposta”; “condições de pagamento”, “pagamento” → “Condições de pagamento”; “frete”, “custo de transporte” → “Frete”; “reajuste” → “Reajuste”; “garantia” → “Garantia”).
Produzir um superconjunto de condições e, para cada condição, informar o valor de cada proposta. Use null quando a proposta não trouxer aquela condição.
IMPORTANTE:

Responda APENAS com JSON válido (sem markdown, sem comentários, sem texto fora do JSON).
Use exatamente o formato abaixo.
Use chaves de proposta contínuas: proposta_1, proposta_2, … até o total de propostas do input, seguindo a ordem dos documentos de entrada.
Valores devem ser strings ou null. Não use objetos aninhados.
Padronize o nome da condição em Title Case, apenas a primeira letra maiúscula (ex.: “Prazo de entrega”, “Condições de pagamento”, “Frete”, “Reajuste”, “Validade da proposta”, “Garantia”).
FORMATO DE SAÍDA (exato):
{
"condicoes_comerciais": [
{
"chave": "Prazo de entrega",
"proposta_1": "15 dias úteis",
"proposta_2": null,
"proposta_3": "25 dias úteis"
},
{
"chave": "Condições de pagamento",
"proposta_1": "À vista",
"proposta_2": "28 dias",
"proposta_3": null
}
// Outras condições...
]
}
"""


