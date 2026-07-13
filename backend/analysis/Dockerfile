# Render free web service (Docker) - replaces the AWS Lambda container image.
# Same model (all-MiniLM-L6-v2) via ONNX Runtime (fits 512MB free instance);
# handler.py unchanged; POST / == Lambda Event invoke. Build context: ./backend
FROM python:3.11-slim
WORKDIR /app
ENV HF_HOME=/app/hf_cache
COPY analysis/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Pre-download the model at build time (same weights as the torch pipeline)
RUN python -c "from huggingface_hub import hf_hub_download as d; r='sentence-transformers/all-MiniLM-L6-v2'; d(r,'onnx/model.onnx'); d(r,'tokenizer.json')"
ENV HF_HUB_OFFLINE=1
COPY shared/database.py analysis/handler.py analysis/analysis.py analysis/server.py ./
EXPOSE 7860
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-7860}
