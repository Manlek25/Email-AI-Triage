import re

STOPWORDS_PT_BR = {
    "a", "o", "os", "as", "de", "do", "da", "dos", "das", "e", "ou", "para", "por", "com", "em",
    "um", "uma", "uns", "umas", "que", "se", "na", "no", "nos", "nas", "ao", "aos", "à", "às",
    "mais", "menos", "muito", "pouco", "já", "ja", "também", "tambem"
}

def preprocessar_texto(texto: str) -> str:
    texto_normalizado = (texto or "").lower()
    texto_normalizado = re.sub(r"\s+", " ", texto_normalizado).strip()
    # remove pontuação pesada, mas mantém e-mail e separadores comuns
    texto_normalizado = re.sub(r"[^\w\s@.\-]", " ", texto_normalizado)

    tokens = [w for w in texto_normalizado.split() if w not in STOPWORDS_PT_BR]
    return " ".join(tokens)