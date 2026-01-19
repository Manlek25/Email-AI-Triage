from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.pdf_reader import ler_pdf_bytes
from app.preprocess import preprocessar_texto
from app.ai import analisar_email

DIRETORIO_BASE = Path(__file__).resolve().parent.parent
DIRETORIO_STATIC = DIRETORIO_BASE / "static"

app = FastAPI(title="Email AI Triage")

# Servir arquivos estáticos (/static/*)
app.mount("/static", StaticFiles(directory=str(DIRETORIO_STATIC)), name="static")


@app.get("/")
def pagina_inicial():
    return FileResponse(str(DIRETORIO_STATIC / "index.html"))


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/analyze")
async def analisar(
    texto_email: str = Form(default=""),
    tom_resposta: str = Form(default="formal"),  # formal | curto
    arquivo_email: UploadFile | None = File(default=None),
):
    texto_bruto = (texto_email or "").strip()

    if arquivo_email is not None:
        nome_arquivo = (arquivo_email.filename or "").lower()
        conteudo_arquivo = await arquivo_email.read()

        if nome_arquivo.endswith(".txt"):
            texto_bruto = conteudo_arquivo.decode("utf-8", errors="ignore").strip()
        elif nome_arquivo.endswith(".pdf"):
            texto_bruto = ler_pdf_bytes(conteudo_arquivo).strip()
        else:
            return JSONResponse(
                status_code=400,
                content={"error": "Formato inválido. Envie .txt ou .pdf."},
            )

    if not texto_bruto:
        return JSONResponse(
            status_code=400,
            content={"error": "Envie um texto ou arquivo."},
        )

    texto_limpo = preprocessar_texto(texto_bruto)

    resultado = analisar_email(
    texto_bruto,
    texto_limpo,
    tom_resposta,
)
    return resultado