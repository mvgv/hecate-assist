# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder

WORKDIR /build

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY pyproject.toml ./
COPY src/ src/
# torch e puxado transitivamente por sentence-transformers; instalar a wheel
# CPU-only primeiro evita ~5GB de bibliotecas CUDA desnecessarias na imagem
# (o deploy roda 100% em CPU - ver ESPECIFICACAO.md §1 e PLANO.md §5).
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir .

FROM python:3.11-slim AS runtime

ARG MEDASSIST_EMBEDDING_MODEL=intfloat/multilingual-e5-small
ENV PATH="/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    MEDASSIST_EMBEDDING_MODEL=${MEDASSIST_EMBEDDING_MODEL} \
    HF_HOME=/app/.cache/huggingface

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash medassist

WORKDIR /app

COPY --from=builder /venv /venv
COPY src/ src/
COPY data/synthetic/ data/synthetic/
COPY deploy/entrypoint.sh deploy/entrypoint.sh

# Pre-baixa o modelo de embeddings no build para o container subir offline/rapido.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${MEDASSIST_EMBEDDING_MODEL}')"

RUN chmod +x deploy/entrypoint.sh \
    && mkdir -p data logs \
    && chown -R medassist:medassist /app

USER medassist

EXPOSE 8501

ENTRYPOINT ["/app/deploy/entrypoint.sh"]
CMD ["streamlit", "run", "src/medassist/ui/app_streamlit.py", "--server.port=8501", "--server.address=0.0.0.0"]
