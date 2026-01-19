import os
import json
import re
from typing import Dict, Any, List, Optional

# =========================================================
# OpenAI client - com fallback automático
# =========================================================

erro_openai: Optional[str] = None
#print("Modelo OpenAI em uso:", os.getenv("OPENAI_MODEL"))
print("DEBUG: OPENAI_API_KEY env presente?", bool(os.getenv("OPENAI_API_KEY")))
print("DEBUG: existe /etc/secrets/openai_api_key ?", os.path.exists("/etc/secrets/openai_api_key"))


def obter_cliente_openai():
    """
    Tenta criar o client da OpenAI.
    Se falhar (sem chave, pacote não instalado, quota, etc), retorna None.
    """
    global erro_openai
    try:
        from openai import OpenAI

        chave_api = os.getenv("OPENAI_API_KEY")

        if not chave_api:
            try:
                with open("/etc/secrets/openai_api_key", "r", encoding="utf-8") as f:
                    chave_api = f.read().strip()
            except Exception:
                chave_api = None

        if not chave_api:
            erro_openai = (
                "OPENAI_API_KEY não encontrada (nem env var, nem /etc/secrets/openai_api_key)."
            )
            return None

        return OpenAI(api_key=chave_api)
    
    except Exception as excecao:
        print("Erro OpenAI (init):", excecao)
        erro_openai = str(excecao)
        return None


# =========================================================
# Heurística (definição de decisões fallback)
# =========================================================

PALAVRAS_CORTESIA = [
    "feliz natal", "boas festas", "feliz ano novo",
    "parabéns", "parabens",
    "obrigado", "obrigada", "agradeço", "agradeco",
    "gratidão", "gratidao",
]

PADROES_SOLICITACAO = [
    r"\bpor favor\b", r"\bpoderia(m)?\b", r"\bconsegue(m)?\b",
    r"\bpreciso\b", r"\bgostaria\b", r"\bsolicito\b",
    r"\bverificar\b", r"\batualizar\b", r"\bstatus\b",
    r"\bchamado\b", r"\bticket\b", r"\berro\b",
    r"\bfalha\b", r"\bacesso\b", r"\bsenha\b",
    r"\blogin\b", r"\breembolso\b", r"\bcobrança\b|\bcobranca\b",
    r"\bfatura\b", r"\banexo\b",
]


def identificar_tipo_cortesia(email_texto: str) -> str:
    email_texto = email_texto.lower()
    if "feliz natal" in email_texto:
        return "natal"
    if "feliz ano novo" in email_texto:
        return "anonovo"
    if "boas festas" in email_texto:
        return "boasfestas"
    if "parabéns" in email_texto or "parabens" in email_texto:
        return "parabens"
    if any(p in email_texto for p in [
        "obrigado", "obrigada", "agradeço", "agradeco", "gratidão", "gratidao"
    ]):
        return "agradecimento"
    return "cortesia"


def classificar_por_regras(email_texto: str) -> Dict[str, Any]:
    email_texto = email_texto.lower()
    tem_cortesia = any(p in email_texto for p in PALAVRAS_CORTESIA)
    tem_solicitacao = any(re.search(p, email_texto) for p in PADROES_SOLICITACAO)
    tem_pergunta = "?" in email_texto

    if tem_cortesia and not tem_solicitacao and not tem_pergunta:
        return {
            "category": "Improdutivo",
            "confidence": 0.85,
            "reason": "Mensagem de cortesia/agradecimento sem solicitação. (fallback)"
        }

    if tem_solicitacao or tem_pergunta:
        return {
            "category": "Produtivo",
            "confidence": 0.78,
            "reason": "Há indícios de solicitação ou necessidade de ação. (fallback)"
        }

    return {
        "category": "Produtivo",
        "confidence": 0.65,
        "reason": "Classificação conservadora (pode exigir ação). (fallback)"
    }


# =========================================================
# Trechos relevantes (highlights)
# =========================================================

def extrair_trechos_relevantes(
    email_texto: str,
    categoria_sugerida: Optional[str] = None,
    max_itens: int = 2
) -> List[str]:

    linhas = [l.strip() for l in email_texto.splitlines() if l.strip()]
    trechos: List[str] = []
    vistos = set()

    def adicionar(linha: str):
        if linha and linha not in vistos:
            vistos.add(linha)
            trechos.append(linha)

    # 1️⃣ Linhas com pedido / pressão / ação
    sinais_fortes = [
        "status", "prazo", "cobrando", "retorno",
        "erro", "falha", "não consigo", "nao consigo",
        "verificar", "atualizar", "resolver"
    ]
    for linha in linhas:
        if any(s in linha.lower() for s in sinais_fortes):
            adicionar(linha)
            if len(trechos) >= max_itens:
                return trechos[:max_itens]

    # 2️⃣ Identificadores importantes
    for linha in linhas:
        linha_lower = linha.lower()
        if linha_lower.startswith("assunto:") or "chamado" in linha_lower or "#" in linha:
            adicionar(linha)
            if len(trechos) >= max_itens:
                return trechos[:max_itens]

    # 3️⃣ Cortesia (somente se improdutivo)
    if categoria_sugerida == "Improdutivo":
        for linha in linhas:
            if any(p in linha.lower() for p in PALAVRAS_CORTESIA):
                adicionar(linha)
                break

    # 4️⃣ Fallback final
    for linha in linhas:
        adicionar(linha)
        if len(trechos) >= max_itens:
            break

    return trechos[:max_itens]


# =========================================================
# JSON helper
# =========================================================

def extrair_json_seguro(texto: str) -> Dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", texto)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except Exception:
        return {}


# =========================================================
# Respostas fallback
# =========================================================

def encurtar_texto(texto: str) -> str:
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    return "\n".join(linhas[:4])


def gerar_resposta_fallback(
    categoria: str,
    email_texto: str,
    tom: str = "formal"
) -> str:

    texto_lower = email_texto.lower()
    tipo_cortesia = identificar_tipo_cortesia(email_texto)

    # ---------- IMPRODUTIVO ----------
    if categoria == "Improdutivo":
        if tipo_cortesia == "natal":
            mensagem = (
                "Olá! Obrigado pela mensagem.\n\n"
                "Desejamos a você e sua equipe um Feliz Natal e boas festas.\n"
                "Permanecemos à disposição."
            )
        else:
            mensagem = (
                "Olá! Obrigado pela mensagem.\n\n"
                "Ficamos à disposição caso precise de qualquer suporte."
            )
        return encurtar_texto(mensagem) if tom == "curto" else mensagem

    # ---------- PRODUTIVO: STATUS ----------
    if "status" in texto_lower and ("chamado" in texto_lower or "#" in texto_lower):
        mensagem = (
            "Olá! Obrigado pelo contato.\n\n"
            "Recebemos a solicitação de atualização do chamado informado. "
            "Vamos verificar o status do atendimento e retornar com um posicionamento "
            "e prazo estimado para resolução assim que possível.\n\n"
            "Seguimos acompanhando."
        )
        return encurtar_texto(mensagem) if tom == "curto" else mensagem

    # ---------- PRODUTIVO: GENÉRICO ----------
    mensagem = (
        "Olá! Recebemos sua mensagem e vamos analisá-la.\n\n"
        "Caso seja necessário algum complemento, entraremos em contato.\n\n"
        "Seguimos à disposição."
    )
    return encurtar_texto(mensagem) if tom == "curto" else mensagem


# =========================================================
# Função principal
# =========================================================

def analisar_email(email_texto_bruto: str, email_texto_limpo: str, tom: str = "formal") -> Dict[str, Any]:

    cliente_openai = obter_cliente_openai()

    # Fallback direto
    if cliente_openai is None:
        resultado = classificar_por_regras(email_texto_bruto)
        return {
            "category": resultado["category"],
            "confidence": resultado["confidence"],
            "reply": gerar_resposta_fallback(resultado["category"], email_texto_bruto, tom),
            "reason": resultado["reason"],
            "highlights": extrair_trechos_relevantes(
                email_texto_bruto,
                categoria_sugerida=resultado["category"]
            ),
        }

    estilo = "objetiva e curta" if tom == "curto" else "formal e profissional"
    prompt = f"""
Classifique o email abaixo como "Produtivo" ou "Improdutivo"
e gere uma resposta automática profissional em português ({estilo}).

Responda SOMENTE em JSON:
{{
  "category": "Produtivo|Improdutivo",
  "confidence": 0.0,
  "reply": "texto",
  "reason": "motivo curto"
}}

EMAIL:
{email_texto_bruto}
""".strip()

    modelo = os.getenv("OPENAI_MODEL", "gpt-5-nano")

    try:
        if modelo.startswith("gpt-5"):
            resposta = cliente_openai.responses.create(
                model=modelo,
                input=prompt
            )
            conteudo = resposta.output_text
        else:
            resposta = cliente_openai.chat.completions.create(
                model=modelo,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            conteudo = resposta.choices[0].message.content or ""

        dados = extrair_json_seguro(conteudo)

        categoria = dados.get("category")
        if categoria not in ["Produtivo", "Improdutivo"]:
            raise ValueError("Categoria inválida")

        confianca = float(dados.get("confidence", 0.75))
        resposta_texto = dados.get("reply") or gerar_resposta_fallback(categoria, email_texto_bruto, tom)

        return {
            "category": categoria,
            "confidence": max(0.0, min(1.0, confianca)),
            "reply": encurtar_texto(resposta_texto) if tom == "curto" else resposta_texto,
            "reason": dados.get("reason", ""),
            "highlights": extrair_trechos_relevantes(
                email_texto_bruto,
                categoria_sugerida=categoria
            ),
        }

    except Exception as excecao:
        print("Erro OpenAI (runtime):", excecao)
        resultado = classificar_por_regras(email_texto_bruto)
        return {
            "category": resultado["category"],
            "confidence": resultado["confidence"],
            "reply": gerar_resposta_fallback(resultado["category"], email_texto_bruto, tom),
            "reason": resultado["reason"],
            "highlights": extrair_trechos_relevantes(
                email_texto_bruto,
                categoria_sugerida=resultado["category"]
            ),
        }