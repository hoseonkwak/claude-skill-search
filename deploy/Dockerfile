# Hugging Face Space (Docker) — full Skill Finder app (page + semantic API)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HF_HOME=/app/.cache \
    HF_HUB_DISABLE_PROGRESS_BARS=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY scripts/ scripts/
COPY data/ data/

# bake the multilingual model into the image so cold start is fast
RUN python -c "from sentence_transformers import SentenceTransformer as S; \
    S('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

EXPOSE 7860
CMD ["python", "scripts/serve.py"]
