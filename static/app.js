const el = (id) => document.getElementById(id);

el("btnAnalyze").addEventListener("click", async () => {
    el("error").classList.add("hidden");
    el("loading").classList.remove("hidden");
    el("result").classList.add("hidden");
    el("highlightsBox").classList.add("hidden");
    el("highlightsList").innerHTML = "";

    const textoEmail = el("emailText").value || "";
    const tomResposta = el("tone").value;
    const arquivoEmail = el("fileInput").files[0];

    const form = new FormData();
    form.append("texto_email", textoEmail);
    form.append("tom_resposta", tomResposta);
    if (arquivoEmail) form.append("arquivo_email", arquivoEmail);

    try {
        const res = await fetch(`/analyze`, { method: "POST", body: form });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Erro ao processar.");

        el("badgeCategory").textContent = `Categoria: ${data.category}`;
        el("badgeConfidence").textContent = `Confiança: ${(data.confidence * 100).toFixed(0)}%`;
        el("replyText").textContent = data.reply || "";

        const reasonText = data.reason || "";
        el("reason").textContent = reasonText ? `Motivo: ${reasonText}` : "";

        // Badge de modo (fallback)
        const isFallback = reasonText.toLowerCase().includes("fallback");
        if (isFallback) {
            el("modeBadge").classList.remove("hidden");
        } else {
            el("modeBadge").classList.add("hidden");
        }

        if (Array.isArray(data.highlights) && data.highlights.length) {
            for (const h of data.highlights) {
                const li = document.createElement("li");
                li.textContent = h;
                el("highlightsList").appendChild(li);
            }
            el("highlightsBox").classList.remove("hidden");
        }

        el("result").classList.remove("hidden");
    } catch (err) {
        el("error").textContent = err.message;
        el("error").classList.remove("hidden");
    } finally {
        el("loading").classList.add("hidden");
    }
});

el("btnCopy").addEventListener("click", async () => {
    await navigator.clipboard.writeText(el("replyText").textContent || "");
    el("btnCopy").textContent = "Copiado!";
    setTimeout(() => (el("btnCopy").textContent = "Copiar resposta"), 1200);
});

el("btnClear").addEventListener("click", () => {
    el("emailText").value = "";
    el("fileInput").value = "";
    el("result").classList.add("hidden");
    el("highlightsBox").classList.add("hidden");
});

el("emailText").addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    el("btnAnalyze").click();
  }
});