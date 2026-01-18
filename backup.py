# app/ai.py
import os
import json
import re
from typing import Dict, Any, List, Optional

# =========================================================
# OpenAI client (opcional) - com fallback automático
# =========================================================

_openai_error: Optional[str] = None
print("Modelo OpenAI em uso:", os.getenv("OPENAI_MODEL"))


def _get_client():
    """
    Tenta criar o client da OpenAI.
    Se falhar (sem chave, pacote não instalado, quota, etc), retorna None.
    """
    global _openai_error
    try:
        from openai import OpenAI
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            _openai_error = "OPENAI_API_KEY não encontrada no ambiente."
            return None
        return OpenAI(api_key=key)
    except Exception as e:
        _openai_error = f"Falha ao iniciar OpenAI client: {e}"
        return None


# =========================================================
# Heurística (modo demo)
# =========================================================

FELICITATIONS = [
    "feliz natal", "boas festas", "feliz ano novo",
    "parabéns", "parabens",
    "obrigado", "obrigada", "agradeço", "agradeco",
    "gratidão", "gratidao",
]

# Padrões que indicam pedido/ação
REQUEST_PATTERNS = [
    r"\bpor favor\b",
    r"\bpoderia(m)?\b",
    r"\bconsegue(m)?\b",
    r"\bpreciso\b",
    r"\bgostaria\b",
    r"\bsolicito\b",
    r"\bverificar\b",
    r"\batualizar\b",
    r"\bstatus\b",
    r"\bchamado\b",
    r"\bticket\b",
    r"\berro\b",
    r"\bfalha\b",
    r"\bacesso\b",
    r"\bsenha\b",
    r"\blogin\b",
    r"\breembolso\b",
    r"\bcobrança\b|\bcobranca\b",
    r"\bfatura\b",
    r"\banexo\b",
]


def _detect_felicitation_type(text: str) -> str:
    t = text.lower()
    if "feliz natal" in t:
        return "natal"
    if "feliz ano novo" in t:
        return "anonovo"
    if "boas festas" in t:
        return "boasfestas"
    if "parabéns" in t or "parabens" in t:
        return "parabens"
    if any(k in t for k in ["obrigado", "obrigada", "agradeço", "agradeco", "gratidão", "gratidao"]):
        return "agradecimento"
    return "cortesia"


def heuristic_classify(text: str) -> Dict[str, Any]:
    """
    Regra principal:
    - Improdutivo: cortesia/agradecimento/felicitação SEM pedido.
    - Produtivo: tem pedido explícito, pergunta ou termo de ação.
    """
    t = text.lower()
    has_felicitation = any(k in t for k in FELICITATIONS)
    has_request = any(re.search(p, t) for p in REQUEST_PATTERNS)
    has_question = "?" in t

    # Caso comum: "Obrigado pelo suporte" (cortesia) -> improdutivo
    # Só vira produtivo se tiver pedido/ação/pergunta.
    if has_felicitation and not has_request and not has_question:
        return {
            "category": "Improdutivo",
            "confidence": 0.85,
            "reason": "Mensagem de cortesia/agradecimento sem solicitação. (fallback)"
        }

    if has_request or has_question:
        return {
            "category": "Produtivo",
            "confidence": 0.78,
            "reason": "Há indícios de solicitação ou necessidade de ação. (fallback)"
        }

    # Default conservador
    return {
        "category": "Produtivo",
        "confidence": 0.65,
        "reason": "Classificação conservadora (pode exigir ação). (fallback)"
    }


# =========================================================
# Highlights (sem repetição + adaptado ao tipo)
# =========================================================

def extract_highlights(text: str, category_hint: Optional[str] = None, max_items: int = 2) -> List[str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    seen = set()
    picks: List[str] = []

    def add(line: str):
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            picks.append(line)

    t = text.lower()

    # 1) Para improdutivo: prioriza linha de cortesia (feliz natal/boas festas/etc)
    if category_hint == "Improdutivo":
        courtesy_signals = ["feliz natal", "boas festas", "feliz ano novo", "parabéns", "parabens", "obrigado", "obrigada"]
        for line in lines:
            low = line.lower()
            if any(s in low for s in courtesy_signals):
                add(line)
                break

    # 2) assunto
    for line in lines:
        if line.lower().startswith("assunto:"):
            add(line)
            break

    # 3) linha “forte” de pedido/problema
    signals = [
        "não consigo", "nao consigo", "erro", "falha", "status",
        "chamado", "ticket", "por favor", "verificar", "acesso",
        "senha", "login", "reembolso", "cobran"
    ]
    for line in lines:
        low = line.lower()
        if any(s in low for s in signals):
            add(line)
            if len(picks) >= max_items:
                return picks[:max_items]

    # 4) fallback: completa com primeiras linhas úteis
    for line in lines:
        add(line)
        if len(picks) >= max_items:
            break

    return picks[:max_items]


# =========================================================
# OpenAI JSON helper
# =========================================================

def safe_json_extract(s: str) -> Dict[str, Any]:
    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


# =========================================================
# Respostas do fallback (modo demo) + tom curto
# =========================================================

def _shorten(text: str) -> str:
    """
    Versão curta: 2-4 linhas úteis.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines[:4]).strip()


def fallback_reply(category: str, raw_text: str, tone: str = "formal") -> str:
    t = raw_text.lower()

    # --- IMPRODUTIVO: responder "na mesma" (empresarial) ---
    if category == "Improdutivo":
        kind = _detect_felicitation_type(raw_text)

        if kind == "natal":
            msg = (
                "Olá! Obrigado pela mensagem.\n\n"
                "Desejamos a você e sua equipe um Feliz Natal e boas festas.\n"
                "Permanecemos à disposição."
            )
        elif kind == "anonovo":
            msg = (
                "Olá! Obrigado pela mensagem.\n\n"
                "Desejamos um excelente Ano Novo, com muito sucesso.\n"
                "Conte conosco sempre que precisar."
            )
        elif kind == "boasfestas":
            msg = (
                "Olá! Obrigado pela mensagem.\n\n"
                "Desejamos boas festas e um ótimo encerramento de ano.\n"
                "Seguimos à disposição."
            )
        elif kind == "parabens":
            msg = (
                "Olá! Agradecemos a mensagem.\n\n"
                "Parabéns! Ficamos felizes pelo contato.\n"
                "Se precisar de algo, conte conosco."
            )
        else:
            # agradecimento/cortesia genérica
            msg = (
                "Olá! Obrigado pela mensagem.\n\n"
                "Ficamos à disposição caso precise de qualquer suporte."
            )

        return _shorten(msg) if tone == "curto" else msg

    # --- PRODUTIVO: respostas por intenção ---
    if any(k in t for k in ["acesso", "login", "senha", "credenciais", "inválidas", "invalidas"]):
        msg = (
            "Olá! Obrigado pelo contato.\n\n"
            "Entendi que você está com dificuldade de acesso. Para agilizar a verificação, por favor informe:\n"
            "• Horário aproximado em que o erro começou\n"
            "• Mensagem exata exibida (se possível, um print)\n"
            "• Se acontece em outro navegador ou aba anônima\n\n"
            "Com isso, seguimos com a análise e retorno."
        )
        return _shorten(msg) if tone == "curto" else msg

    if any(k in t for k in ["status", "chamado", "ticket", "prazo"]):
        msg = (
            "Olá! Obrigado pelo contato.\n\n"
            "Para consultar o status, por favor confirme:\n"
            "• Número do chamado/ticket (se houver)\n"
            "• Nome ou identificação do solicitante\n\n"
            "Assim que eu tiver esses dados, retorno com a atualização."
        )
        return _shorten(msg) if tone == "curto" else msg

    if any(k in t for k in ["cobran", "fatura", "pagamento", "reembolso"]):
        msg = (
            "Olá! Obrigado pelo contato.\n\n"
            "Para analisar a solicitação financeira, por favor informe:\n"
            "• CPF/CNPJ (ou identificador do cliente)\n"
            "• Número da fatura/transação (se houver)\n"
            "• Valor e data aproximada\n\n"
            "Com esses dados, conseguimos dar andamento."
        )
        return _shorten(msg) if tone == "curto" else msg

    # genérico produtivo
    msg = (
        "Olá! Recebemos sua mensagem e vamos analisar.\n\n"
        "Para agilizar o atendimento, por favor envie mais detalhes sobre a solicitação "
        "e, se possível, evidências (prints/anexos) e horário aproximado do ocorrido.\n\n"
        "Assim seguimos com a verificação."
    )
    return _shorten(msg) if tone == "curto" else msg


# =========================================================
# Função principal
# =========================================================

def analyze_email(raw_text: str, clean_text: str, tone: str = "formal") -> Dict[str, Any]:
    """
    Tenta usar OpenAI. Se falhar por qualquer motivo (quota, rede, etc),
    cai automaticamente no fallback heurístico.
    """
    client = _get_client()

    # 1) Se não tem client (sem chave / sem lib), fallback direto
    if client is None:
        h = heuristic_classify(raw_text)
        return {
            "category": h["category"],
            "confidence": h["confidence"],
            "reply": fallback_reply(h["category"], raw_text, tone=tone),
            "reason": f'{h["reason"]} {_openai_error or ""}'.strip(),
            "highlights": extract_highlights(raw_text, category_hint=h["category"]),
        }

    # 2) Tenta OpenAI, mas com try/except para nunca quebrar a API
    style = "objetiva e curta" if tone == "curto" else "formal e profissional"
    prompt = f"""
Você é um assistente de triagem de emails de uma empresa do setor financeiro.

Tarefa:
1) Classificar o email em "Produtivo" ou "Improdutivo".
2) Sugerir uma resposta automática em pt-BR no estilo {style}.

Regras:
- "Produtivo": existe pedido/ação necessária (status, dúvida, erro, solicitação, cobrança, anexo).
- "Improdutivo": apenas cortesia (felicitações, agradecimentos) sem solicitação.
- Não invente dados; se faltarem informações, peça o mínimo necessário.

Responda SOMENTE em JSON estrito:
{{
  "category": "Produtivo|Improdutivo",
  "confidence": 0.0,
  "reply": "texto",
  "reason": "frase curta",
  "highlights": ["trecho 1", "trecho 2"]
}}

EMAIL:
{raw_text}
""".strip()

    model = os.getenv("OPENAI_MODEL", "gpt-5-nano")

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
    except Exception:
        # OpenAI indisponível (quota, rede, etc) => fallback automático
        h = heuristic_classify(raw_text)
        return {
            "category": h["category"],
            "confidence": h["confidence"],
            "reply": fallback_reply(h["category"], raw_text, tone=tone),
            "reason": f'{h["reason"]} (fallback: OpenAI indisponível)',
            "highlights": extract_highlights(raw_text, category_hint=h["category"]),
        }

    content = resp.choices[0].message.content or ""
    data = safe_json_extract(content)

    # validação mínima
    category = data.get("category")
    if category not in ["Produtivo", "Improdutivo"]:
        h = heuristic_classify(raw_text)
        category = h["category"]

    try:
        confidence = float(data.get("confidence", 0.75))
    except Exception:
        confidence = 0.75

    highlights = data.get("highlights")
    if not isinstance(highlights, list) or not highlights:
        highlights = extract_highlights(raw_text, category_hint=category)

    reply = data.get("reply") or fallback_reply(category, raw_text, tone=tone)
    reason = data.get("reason", "")

    return {
        "category": category,
        "confidence": max(0.0, min(1.0, confidence)),
        "reply": reply,
        "reason": reason,
        "highlights": highlights[:2],
    }
