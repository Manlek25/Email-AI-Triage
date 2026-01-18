import io
from pypdf import PdfReader

def ler_pdf_bytes(pdf_bytes: bytes) -> str:
    leitor = PdfReader(io.BytesIO(pdf_bytes))
    partes = []

    for pagina in leitor.pages:
        texto_pagina = pagina.extract_text() or ""
        texto_pagina = texto_pagina.strip()
        if texto_pagina:
            partes.append(texto_pagina)

    return "\n".join(partes).strip()
