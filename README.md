## 🧩 Decisões Técnicas

### 1. Arquitetura Backend
Foi utilizada uma arquitetura simples baseada em **FastAPI**, separando:
- Camada de entrada (API e upload)
- Camada de processamento e classificação
- Camada de fallback heurístico

Essa separação facilita manutenção, testes e futuras evoluções do sistema.

---

### 2. Classificação com IA + Fallback Heurístico
A classificação principal é feita utilizando a **OpenAI API**, que retorna:
- Categoria (Produtivo / Improdutivo)
- Confiança
- Resposta sugerida
- Motivo da classificação

Para garantir **resiliência**, foi implementado um **fallback heurístico** que:
- Classifica emails mesmo sem IA
- Gera respostas automáticas coerentes
- Evita indisponibilidade da aplicação por quota ou falhas externas

Essa abordagem garante funcionamento contínuo da solução.

---

### 3. Escolha do Modelo de IA
O modelo foi configurado via variável de ambiente (`OPENAI_MODEL`), permitindo:
- Fácil troca de modelos
- Testes com modelos mais econômicos (ex: `gpt-5-nano`)
- Ajuste sem alteração de código

Também foi tratado o uso correto da API de acordo com o modelo (ex: `responses.create` para GPT-5).

---

### 4. Extração de Trechos Relevantes
Foi implementada uma lógica própria para destacar os **trechos mais importantes do email**, priorizando:
1. Linhas com solicitação, pressão ou ação (status, prazo, erro)
2. Identificadores importantes (assunto, número de chamado)
3. Cortesias apenas quando relevantes

Isso melhora a legibilidade e a tomada de decisão pela equipe.

---

### 5. Experiência do Usuário
A interface foi mantida simples e objetiva:
- Campo para colar texto ou enviar arquivo
- Escolha do tom da resposta
- Resultado claro e imediato

O foco foi facilitar o uso por **usuários não técnicos**.